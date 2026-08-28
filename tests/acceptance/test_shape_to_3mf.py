"""
End-to-end acceptance tests for Shape artifact production.
"""
# File: tests/acceptance/test_shape_to_3mf.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

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
def test_shape_builds_complete_3mf_without_artwork(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """
    A Shape without Artwork can be interactively configured and built
    into a complete 3MF artifact through the public CLI.

    Shape structural geometry begins in registered nonphysical space.
    Physical X/Y size and base thickness are introduced by extrusion,
    and the resulting physical component is packaged into the final
    artifact.3mf.

    The default Shape base retains its semantic color identity through
    dimensionalization and packaging.

    No Artwork source or completed Artwork artifact is required.
    """

    # -----------------------------------------------------
    # Arrange temporary project
    # -----------------------------------------------------

    project_root = tmp_path

    monkeypatch.chdir(
        project_root,
    )

    runner = CliRunner()

    # -----------------------------------------------------
    # Configure through the public CLI
    # -----------------------------------------------------

    #
    # Interactive response:
    #
    #   2 -> shape model
    #
    # Shape's initial structural parameters are supplied by
    # model defaults, so no additional parameter prompts are
    # required.
    #

    config_result = runner.invoke(
        cli,
        [
            "config",
            "testshape",
        ],
        input="2\n",
    )

    assert config_result.exit_code == 0, (
        f"Shape configuration failed:\n{config_result.output}\n{config_result.exception!r}"
    )

    # -----------------------------------------------------
    # Verify configuration can be inspected
    # -----------------------------------------------------

    inspect_result = runner.invoke(
        cli,
        [
            "config",
            "testshape",
        ],
    )

    assert inspect_result.exit_code == 0, (
        "Shape configuration could not be read:\n"
        f"{inspect_result.output}\n"
        f"{inspect_result.exception!r}"
    )

    # -----------------------------------------------------
    # Plan
    # -----------------------------------------------------

    plans = create_build_plans(
        "testshape",
        project_root=project_root,
    )

    assert len(plans) == 1

    plan = plans[0]

    assert plan.artifact_id == "testshape"
    assert plan.model_name == "shape"
    assert plan.realization_name == "default"

    assert plan.artifact_dir.is_relative_to(
        project_root,
    )

    stage_names = tuple(stage.spec.name for stage in plan.stages)

    assert stage_names == (
        "structure",
        "compose",
        "extrude",
        "package",
    )

    # -----------------------------------------------------
    # Build through the public CLI
    # -----------------------------------------------------

    build_result = runner.invoke(
        cli,
        [
            "build",
            "testshape",
        ],
    )

    assert build_result.exit_code == 0, (
        f"Shape build failed:\n{build_result.output}\n{build_result.exception!r}"
    )

    # -----------------------------------------------------
    # Locate final product through the build plan
    # -----------------------------------------------------

    package_stage = next(stage for stage in plan.stages if stage.spec.name == "package")

    artifact_product = next(
        product for product in package_stage.products if product.spec.name == "artifact"
    )

    output = artifact_product.path

    # -----------------------------------------------------
    # Verify final product
    # -----------------------------------------------------

    assert output.is_relative_to(
        project_root,
    )

    assert output.is_file(), f"Build did not produce the expected Shape 3MF: {output}"

    assert output.stat().st_size > 0

    # 3MF is an OPC/ZIP package. Verify that the result is
    # structurally a 3MF rather than merely a file carrying
    # the .3mf extension.

    assert zipfile.is_zipfile(
        output,
    )

    with zipfile.ZipFile(
        output,
    ) as archive:
        names = set(
            archive.namelist(),
        )

        model_name = next(
            name for name in names if name.startswith("3D/") and name.endswith(".model")
        )

        model_data = archive.read(
            model_name,
        )

    assert "[Content_Types].xml" in names

    # -----------------------------------------------------
    # Verify packaged component identity and color
    # -----------------------------------------------------

    model = ET.fromstring(
        model_data,
    )

    objects = model.findall(
        f".//{{{CORE_NS}}}object",
    )

    materials = model.findall(
        f".//{{{CORE_NS}}}basematerials",
    )

    assert len(objects) == 1

    base_object = objects[0]

    assert base_object.get("name") == "testshape-base"

    assert len(materials) == 1

    base_material = materials[0]

    base_color = base_material.find(
        f"{{{CORE_NS}}}base",
    )

    assert base_color is not None

    assert base_color.get("name") == "white"
    assert base_color.get("displaycolor") == "#FFFFFF"

    assert base_object.get("pid") == base_material.get("id")
    assert base_object.get("pindex") == "0"
