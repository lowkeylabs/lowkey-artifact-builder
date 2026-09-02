"""
End-to-end acceptance tests for artifact production.
"""
# File: tests/acceptance/test_png_to_3mf.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
import shutil
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import pytest
from click.testing import CliRunner

from lowkey_artifact_builder.cli._main import cli
from lowkey_artifact_builder.engine import (
    create_build_plans,
)
from lowkey_artifact_builder.formats.threemf import CORE_NS

# =========================================================
# Acceptance tests
# =========================================================


@pytest.mark.slow
def test_png_builds_complete_3mf(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """
    A PNG Artwork input builds into a semantically colored standalone 3MF.

    Raster and vector processing preserve registered Artwork independently of
    manufacturing dimensions. Extrusion introduces physical dimensions, and
    packaging preserves each independently printable Artwork component's
    semantic color identity and RGB representation.
    """

    # -----------------------------------------------------
    # Arrange temporary project
    # -----------------------------------------------------

    repository_root = Path(__file__).resolve().parents[2]

    fixture_source = repository_root / "tests" / "assets" / "nydeli-clean.png"

    assert fixture_source.is_file(), f"Acceptance artwork does not exist: {fixture_source}"

    project_root = tmp_path

    source = project_root / "nydeli-clean.png"

    shutil.copy2(
        fixture_source,
        source,
    )

    monkeypatch.chdir(
        project_root,
    )

    runner = CliRunner()

    # -----------------------------------------------------
    # Configure through the public CLI
    # -----------------------------------------------------

    config_result = runner.invoke(
        cli,
        [
            "config",
            "nydeli",
        ],
        input="1\n1\n70\n",
    )

    assert config_result.exit_code == 0, (
        f"Artifact configuration failed:\n{config_result.output}\n{config_result.exception!r}"
    )

    # -----------------------------------------------------
    # Verify configuration can be inspected
    # -----------------------------------------------------

    inspect_result = runner.invoke(
        cli,
        [
            "config",
            "nydeli",
        ],
    )

    assert inspect_result.exit_code == 0, (
        "Artifact configuration could not be read:\n"
        f"{inspect_result.output}\n"
        f"{inspect_result.exception!r}"
    )

    # -----------------------------------------------------
    # Plan
    # -----------------------------------------------------

    plans = create_build_plans(
        "nydeli",
        project_root=project_root,
    )

    assert len(plans) == 1

    plan = plans[0]

    assert plan.artifact_id == "nydeli"
    assert plan.model_name == "artwork"
    assert plan.realization_name == "default"

    # -----------------------------------------------------
    # Verify backward-compatible envelope configuration
    # -----------------------------------------------------

    assert plan.resolver("artwork_envelope_mode") == "shrink-wrap"

    assert (
        plan.resolver.source(
            "artwork_envelope_mode",
        )
        == "model"
    )

    assert plan.artifact_dir.is_relative_to(
        project_root,
    )

    # -----------------------------------------------------
    # Build through the public CLI
    # -----------------------------------------------------

    build_result = runner.invoke(
        cli,
        [
            "build",
            "nydeli",
        ],
    )

    assert build_result.exit_code == 0, (
        f"Artifact build failed:\n{build_result.output}\n{build_result.exception!r}"
    )

    # -----------------------------------------------------
    # Locate extrusion and package products
    # -----------------------------------------------------

    extrude_stage = next(stage for stage in plan.stages if stage.spec.name == "extrude")

    extrude_manifest_product = next(
        product for product in extrude_stage.products if product.spec.name == "manifest"
    )

    package_stage = next(stage for stage in plan.stages if stage.spec.name == "package")

    artifact_product = next(
        product for product in package_stage.products if product.spec.name == "artifact"
    )

    extrude_manifest = extrude_manifest_product.path
    output = artifact_product.path

    # -----------------------------------------------------
    # Verify physical component contract
    # -----------------------------------------------------

    assert extrude_manifest.is_file()

    extrusion_data = json.loads(
        extrude_manifest.read_text(
            encoding="utf-8",
        )
    )

    products = extrusion_data["products"]

    assert isinstance(
        products,
        list,
    )

    assert products

    # -----------------------------------------------------
    # Verify final product
    # -----------------------------------------------------

    assert output.is_relative_to(
        project_root,
    )

    assert output.is_file(), f"Build did not produce the expected 3MF: {output}"

    assert output.stat().st_size > 0

    assert zipfile.is_zipfile(
        output,
    )

    with zipfile.ZipFile(
        output,
    ) as archive:
        names = set(
            archive.namelist(),
        )

        assert "[Content_Types].xml" in names

        model_name = next(
            name for name in names if name.startswith("3D/") and name.endswith(".model")
        )

        model = ET.fromstring(
            archive.read(
                model_name,
            ),
        )

    # -----------------------------------------------------
    # Verify independently printable Artwork components
    # -----------------------------------------------------

    objects = model.findall(
        f".//{{{CORE_NS}}}object",
    )

    materials = model.findall(
        f".//{{{CORE_NS}}}basematerials",
    )

    objects_by_name = {object_.get("name"): object_ for object_ in objects}

    expected_names = {f"nydeli-{product['name']}" for product in products}

    assert (
        set(
            objects_by_name,
        )
        == expected_names
    )

    assert len(materials) == len(products)

    materials_by_id = {material.get("id"): material for material in materials}

    # -----------------------------------------------------
    # Verify semantic color identity survives packaging
    # -----------------------------------------------------

    for product in products:
        semantic_name = product["name"]
        rgb = product["color"]

        object_ = objects_by_name[f"nydeli-{semantic_name}"]

        material = materials_by_id[object_.get("pid")]

        color = material.find(
            f"{{{CORE_NS}}}base",
        )

        assert color is not None

        assert color.get("name") == semantic_name

        assert color.get("displaycolor") == (
            f"#{rgb['red']:02X}{rgb['green']:02X}{rgb['blue']:02X}"
        )

        assert object_.get("pindex") == "0"
