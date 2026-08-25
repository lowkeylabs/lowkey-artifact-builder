"""
End-to-end acceptance tests for artifact production.
"""
# File: tests/acceptance/test_png_to_3mf.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import shutil
import zipfile
from pathlib import Path

import pytest
from click.testing import CliRunner

from lowkey_artifact_builder.cli._main import cli
from lowkey_artifact_builder.engine import (
    create_build_plans,
)

# =========================================================
# Acceptance tests
# =========================================================


@pytest.mark.slow
def test_png_builds_complete_3mf(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """
    A PNG artwork input can be interactively configured and built into
    a complete 3MF artifact through the public CLI.

    The repository supplies only the source test artwork. Configuration,
    artifact-owned inputs, intermediate products, and the final 3MF are
    all created beneath an isolated temporary project root.
    """

    # -----------------------------------------------------
    # Arrange temporary project
    # -----------------------------------------------------

    repository_root = Path(__file__).resolve().parents[2]

    fixture_source = repository_root / "projects" / "nydeli-clean.png"

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

    #
    # Interactive responses:
    #
    #   1  -> artwork model
    #   1  -> nydeli-clean.png
    #   70 -> artwork size in millimeters
    #
    # setup_artifact() asks only for parameters that cannot
    # already be resolved through the configuration stack.
    #

    config_result = runner.invoke(
        cli,
        [
            "config",
            "nydeli",
        ],
        input=("1\n1\n70\n"),
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

    assert plan.artifact_dir.is_relative_to(project_root)

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
    # Locate final product
    # -----------------------------------------------------

    package_stage = next(stage for stage in plan.stages if stage.spec.name == "package")

    artifact_product = next(
        product for product in package_stage.products if product.spec.name == "artifact"
    )

    output = artifact_product.path

    # -----------------------------------------------------
    # Verify final product
    # -----------------------------------------------------

    assert output.is_relative_to(project_root)

    assert output.is_file(), f"Build did not produce the expected 3MF: {output}"

    assert output.stat().st_size > 0

    # 3MF is an OPC/ZIP package. Verify that the result is
    # structurally a 3MF rather than merely a file carrying
    # the .3mf extension.

    assert zipfile.is_zipfile(output)

    with zipfile.ZipFile(output) as archive:
        names = set(archive.namelist())

    assert "[Content_Types].xml" in names

    assert any(name.startswith("3D/") and name.endswith(".model") for name in names)
