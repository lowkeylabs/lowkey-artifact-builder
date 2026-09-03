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
    Color analysis realizes registered Artwork on demand.

    Starting from persistent configuration and source input with no generated
    products, the colors command realizes the registered Artwork required for
    analysis through normal build orchestration.

    Standalone Artwork extrusion and packaging are not required merely to
    perform color analysis.
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
