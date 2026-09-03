"""
End-to-end acceptance tests for demand-driven color analysis.
"""
# File: tests/acceptance/test_color_analysis.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from click.testing import CliRunner

from lowkey_artifact_builder.cli._main import cli
from lowkey_artifact_builder.engine import create_build_plans

# =========================================================
# Acceptance tests
# =========================================================


@pytest.mark.slow
def test_colors_realizes_never_built_registered_artwork_without_standalone_build(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """
    Color analysis rebuilds stale registered Artwork on demand.

    Changing artifact-owned input bytes invalidates previously realized
    registered Artwork. A subsequent colors command rebuilds the required
    registered workflow through normal dependency-aware orchestration without
    requiring standalone Artwork extrusion or packaging.
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
    # Locate planned products without building
    # -----------------------------------------------------

    plans = create_build_plans(
        "nydeli",
        project_root=project_root,
    )

    assert len(plans) == 1

    plan = plans[0]

    vector_stage = next(stage for stage in plan.stages if stage.spec.name == "vector")

    vector_manifest_product = next(
        product for product in vector_stage.products if product.spec.name == "manifest"
    )

    extrude_stage = next(stage for stage in plan.stages if stage.spec.name == "extrude")

    extrude_manifest_product = next(
        product for product in extrude_stage.products if product.spec.name == "manifest"
    )

    package_stage = next(stage for stage in plan.stages if stage.spec.name == "package")

    artifact_product = next(
        product for product in package_stage.products if product.spec.name == "artifact"
    )

    vector_manifest = vector_manifest_product.path
    extrude_manifest = extrude_manifest_product.path
    artifact = artifact_product.path

    # -----------------------------------------------------
    # Establish never-built precondition
    # -----------------------------------------------------

    assert not vector_manifest.exists()
    assert not extrude_manifest.exists()
    assert not artifact.exists()

    # -----------------------------------------------------
    # Analyze through the public CLI
    # -----------------------------------------------------

    colors_result = runner.invoke(
        cli,
        [
            "colors",
            "nydeli",
        ],
    )

    assert colors_result.exit_code == 0, (
        f"Color analysis failed:\n{colors_result.output}\n{colors_result.exception!r}"
    )

    # -----------------------------------------------------
    # Registered Artwork was realized
    # -----------------------------------------------------

    assert vector_manifest.is_file()

    # -----------------------------------------------------
    # Standalone manufacturing was not performed
    # -----------------------------------------------------

    assert not extrude_manifest.exists()
    assert not artifact.exists()

    # -----------------------------------------------------
    # Analysis produced user-visible results
    # -----------------------------------------------------

    assert "Printer" in colors_result.output
    assert "Library" in colors_result.output
    assert "Catalog" in colors_result.output


@pytest.mark.slow
def test_colors_rebuilds_stale_registered_artwork_without_standalone_build(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """
    Color analysis rebuilds stale registered Artwork on demand.

    Changing artifact-owned source bytes invalidates previously realized
    registered Artwork. A subsequent colors command rebuilds the required
    registered workflow through normal dependency-aware orchestration without
    requiring standalone Artwork extrusion or packaging.
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
    # Locate relevant products
    # -----------------------------------------------------

    plans = create_build_plans(
        "nydeli",
        project_root=project_root,
    )

    assert len(plans) == 1

    plan = plans[0]

    vector_stage = next(stage for stage in plan.stages if stage.spec.name == "vector")

    vector_manifest_product = next(
        product for product in vector_stage.products if product.spec.name == "manifest"
    )

    extrude_stage = next(stage for stage in plan.stages if stage.spec.name == "extrude")

    extrude_manifest_product = next(
        product for product in extrude_stage.products if product.spec.name == "manifest"
    )

    package_stage = next(stage for stage in plan.stages if stage.spec.name == "package")

    artifact_product = next(
        product for product in package_stage.products if product.spec.name == "artifact"
    )

    vector_manifest = vector_manifest_product.path
    extrude_manifest = extrude_manifest_product.path
    artifact = artifact_product.path

    assert not vector_manifest.exists()
    assert not extrude_manifest.exists()
    assert not artifact.exists()

    # -----------------------------------------------------
    # Initially realize registered Artwork through colors
    # -----------------------------------------------------

    first_result = runner.invoke(
        cli,
        [
            "colors",
            "nydeli",
        ],
    )

    assert first_result.exit_code == 0, (
        f"Initial color analysis failed:\n{first_result.output}\n{first_result.exception!r}"
    )

    assert vector_manifest.is_file()
    assert not extrude_manifest.exists()
    assert not artifact.exists()

    # -----------------------------------------------------
    # Capture realized registered Artwork
    # -----------------------------------------------------

    before_manifest = vector_manifest.read_bytes()

    vector_products = tuple(product for product in vector_stage.products if product.path.is_file())

    assert vector_products

    before_mtimes = {product.path: product.path.stat().st_mtime_ns for product in vector_products}

    # -----------------------------------------------------
    # Invalidate artifact-owned input provenance
    # -----------------------------------------------------

    input_stage = next(stage for stage in plan.stages if stage.inputs)

    assert input_stage.inputs

    artwork_input = input_stage.inputs[0]

    original_input = artwork_input.path.read_bytes()

    artwork_input.path.write_bytes(
        original_input + b"\n",
    )

    # -----------------------------------------------------
    # Analyze stale registered Artwork
    # -----------------------------------------------------

    second_result = runner.invoke(
        cli,
        [
            "colors",
            "nydeli",
        ],
    )

    assert second_result.exit_code == 0, (
        "Color analysis after source invalidation failed:\n"
        f"{second_result.output}\n"
        f"{second_result.exception!r}"
    )

    # -----------------------------------------------------
    # Registered Artwork was rebuilt
    # -----------------------------------------------------

    assert vector_manifest.is_file()

    rebuilt_vector_products = [
        product
        for product in vector_products
        if product.path.stat().st_mtime_ns != before_mtimes[product.path]
    ]

    assert rebuilt_vector_products

    # The manifest may be semantically identical because the appended
    # source byte does not change decoded image content. Its persistence
    # remains valid after rebuilding.
    assert vector_manifest.read_bytes() == before_manifest

    # -----------------------------------------------------
    # Standalone manufacturing was still not performed
    # -----------------------------------------------------

    assert not extrude_manifest.exists()
    assert not artifact.exists()

    # -----------------------------------------------------
    # Analysis still produced user-visible results
    # -----------------------------------------------------

    assert "Printer" in second_result.output
    assert "Library" in second_result.output
    assert "Catalog" in second_result.output
