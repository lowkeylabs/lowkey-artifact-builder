"""
Acceptance tests for artifact builds through the public CLI.

The CLI is intentionally thin. A caller identifies the configured artifact
to build; the engine owns planning, dependency resolution, incremental
execution, and production of the requested artifact.
"""
# File: tests/acceptance/test_cli_dependency_build.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
import shutil
import zipfile
from pathlib import Path

import pytest
from click.testing import CliRunner

from lowkey_artifact_builder.cli._main import cli
from lowkey_artifact_builder.config import (
    write_artifact_config,
)

# =========================================================
# CLI artifact-build acceptance
# =========================================================


@pytest.mark.slow
def test_cli_builds_artifact_with_cross_artifact_dependency(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    The public CLI builds a configured artifact with external dependencies.

    The caller requests only the consumer artifact. The CLI does not require
    the producer to be built separately and does not require the caller to
    select an execution strategy.

    The engine must satisfy the configured artifact graph and produce the
    requested artifact.
    """

    project_root = tmp_path

    monkeypatch.chdir(
        project_root,
    )

    runner = CliRunner()

    # -----------------------------------------------------
    # Create canonical Artwork source
    # -----------------------------------------------------

    repository_root = Path(__file__).resolve().parents[2]

    fixture_source = repository_root / "tests" / "assets" / "nydeli-clean.png"

    assert fixture_source.is_file(), f"Acceptance artwork does not exist: {fixture_source}"

    artwork_directory = project_root / "artifacts" / "source-artwork"

    artwork_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    artwork_input = artwork_directory / "artifact.png"

    shutil.copy2(
        fixture_source,
        artwork_input,
    )

    # -----------------------------------------------------
    # Configure producer artifact
    # -----------------------------------------------------

    write_artifact_config(
        "source-artwork",
        {
            "model": "artwork",
            "source": str(
                artwork_input,
            ),
        },
        project_root=project_root,
    )

    # -----------------------------------------------------
    # Configure consumer artifact
    # -----------------------------------------------------

    write_artifact_config(
        "artwork-shape",
        {
            "model": "shape",
            "product_dependencies": {
                "manifest": {
                    "model": "artwork",
                    "stage": "vector",
                    "product": "manifest",
                    "artifact": "source-artwork",
                    "realization": "default",
                },
            },
        },
        project_root=project_root,
    )

    # -----------------------------------------------------
    # Verify nothing has been built
    # -----------------------------------------------------

    artwork_root = project_root / "artifacts" / "source-artwork" / "artwork" / "default"

    shape_root = project_root / "artifacts" / "artwork-shape" / "shape" / "default"

    assert not artwork_root.exists()
    assert not shape_root.exists()

    # -----------------------------------------------------
    # Request only the consumer through the public CLI
    # -----------------------------------------------------

    result = runner.invoke(
        cli,
        [
            "build",
            "artwork-shape",
        ],
    )

    assert result.exit_code == 0, f"Artifact build failed:\n{result.output}\n{result.exception!r}"

    # -----------------------------------------------------
    # Verify required upstream production
    # -----------------------------------------------------

    assert (artwork_root / "10-prepare" / "trace.svg").is_file()

    assert (artwork_root / "20-raster" / "products.json").is_file()

    artwork_vector_manifest = artwork_root / "30-vector" / "products.json"

    assert artwork_vector_manifest.is_file()

    # -----------------------------------------------------
    # Verify unrequired upstream production did not occur
    # -----------------------------------------------------

    assert not (artwork_root / "40-extrude" / "products.json").exists()

    assert not (artwork_root / "50-package" / "artifact.3mf").exists()

    # -----------------------------------------------------
    # Verify consumer workflow completed
    # -----------------------------------------------------

    assert (shape_root / "10-structure" / "structure.svg").is_file()

    composition_manifest = shape_root / "20-compose" / "products.json"

    assert composition_manifest.is_file()

    assert (shape_root / "30-extrude" / "products.json").is_file()

    # -----------------------------------------------------
    # Verify configured dependency was incorporated
    # -----------------------------------------------------

    composition_data = json.loads(
        composition_manifest.read_text(
            encoding="utf-8",
        )
    )

    assert composition_data["artwork"] is not None

    # -----------------------------------------------------
    # Verify requested artifact was produced
    # -----------------------------------------------------

    output = shape_root / "40-package" / "artifact.3mf"

    assert output.is_file()
    assert output.stat().st_size > 0
    assert zipfile.is_zipfile(
        output,
    )
