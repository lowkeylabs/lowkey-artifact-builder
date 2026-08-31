"""
Tests for the public artifact-build engine boundary.

A caller identifies the configured artifact it wants built. The engine owns
planning, dependency resolution, incremental execution, and production of
the requested artifact.

Callers of this boundary do not construct BuildPlans or select an execution
strategy.
"""
# File: tests/engine/test_artifact_build.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import shutil
import zipfile
from pathlib import Path

import pytest

from lowkey_artifact_builder.config import (
    write_artifact_config,
)
from lowkey_artifact_builder.engine import (
    execute_artifact_build,
)

# =========================================================
# Public artifact-build boundary
# =========================================================


def test_artifact_build_accepts_configured_artifact_identity(
    tmp_path: Path,
) -> None:
    """
    The public engine build boundary accepts an artifact identity.

    Callers do not construct a BuildPlan or select an execution strategy.
    """

    write_artifact_config(
        "shape-artifact",
        {
            "model": "shape",
        },
        project_root=tmp_path,
    )

    execute_artifact_build(
        "shape-artifact",
        project_root=tmp_path,
    )

    output = (
        tmp_path
        / "artifacts"
        / "shape-artifact"
        / "shape"
        / "default"
        / "40-package"
        / "artifact.3mf"
    )

    assert output.is_file()
    assert output.stat().st_size > 0
    assert zipfile.is_zipfile(
        output,
    )


@pytest.mark.slow
def test_artifact_build_satisfies_cross_artifact_dependencies(
    tmp_path: Path,
) -> None:
    """
    The public engine build boundary satisfies configured dependencies.

    The caller requests only the consumer artifact. The engine determines
    and executes the required producer closure before completing the
    requested artifact.

    Producer stages outside the required dependency closure do not execute.
    """

    # -----------------------------------------------------
    # Create canonical Artwork source
    # -----------------------------------------------------

    repository_root = Path(__file__).resolve().parents[2]

    fixture_source = repository_root / "projects" / "nydeli-clean.png"

    assert fixture_source.is_file(), f"Test artwork does not exist: {fixture_source}"

    artwork_directory = tmp_path / "artifacts" / "source-artwork"

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
        project_root=tmp_path,
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
        project_root=tmp_path,
    )

    artwork_root = tmp_path / "artifacts" / "source-artwork" / "artwork" / "default"

    shape_root = tmp_path / "artifacts" / "artwork-shape" / "shape" / "default"

    assert not artwork_root.exists()
    assert not shape_root.exists()

    # -----------------------------------------------------
    # Request only the consumer artifact
    # -----------------------------------------------------

    execute_artifact_build(
        "artwork-shape",
        project_root=tmp_path,
    )

    # -----------------------------------------------------
    # Required producer closure exists
    # -----------------------------------------------------

    assert (artwork_root / "10-prepare" / "trace.svg").is_file()

    assert (artwork_root / "20-raster" / "products.json").is_file()

    assert (artwork_root / "30-vector" / "products.json").is_file()

    # -----------------------------------------------------
    # Unrequired producer stages remain absent
    # -----------------------------------------------------

    assert not (artwork_root / "40-extrude" / "products.json").exists()

    assert not (artwork_root / "50-package" / "artifact.3mf").exists()

    # -----------------------------------------------------
    # Requested consumer artifact exists
    # -----------------------------------------------------

    output = shape_root / "40-package" / "artifact.3mf"

    assert output.is_file()
    assert output.stat().st_size > 0
    assert zipfile.is_zipfile(
        output,
    )
