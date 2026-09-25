"""
Tests for reusable Artifact manufacturing inspection.

Manufacturing inspection answers what an operator can manufacture from an
Artifact, whether each Realization's manufacturing Product is current, and
whether an operator-accessible 3MF already exists.

This behavior belongs below the CLI so alternate interfaces can inspect the
same manufacturing state without reconstructing it from configuration,
planning, or filesystem details.
"""

# File: tests/application/test_manufacturing_status.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from lowkey_artifact_builder.application.manufacturing import (
    ManufacturingState,
    RealizationType,
    inspect_artifact_manufacturing,
)
from lowkey_artifact_builder.config import (
    configure_artifact,
)
from lowkey_artifact_builder.engine import (
    execute_artifact_build,
)

# =========================================================
# Helpers
# =========================================================


def _define_artifact(
    project_root: Path,
    *,
    artifact_id: str = "skippy",
    values: dict | None = None,
) -> Path:
    """
    Define a materialized Artwork-backed Artifact suitable for planning
    and real manufacturing execution.
    """

    artifact_dir = project_root / "artifacts" / artifact_id

    artifact_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    source_fixture = Path(__file__).resolve().parents[1] / "assets" / "nydeli-clean.png"

    source = artifact_dir / "artifact.png"

    shutil.copyfile(
        source_fixture,
        source,
    )

    configuration: dict = {
        "source": f"artifacts/{artifact_id}/artifact.png",
    }

    if values:
        configuration.update(values)

    configure_artifact(
        artifact_id,
        values=configuration,
        project_root=project_root,
    )

    return artifact_dir


def _by_name(
    result,
) -> dict:
    """
    Index inspected Realizations by Realization identity.
    """

    return {realization.realization: realization for realization in result.realizations}


# =========================================================
# Canonical Realization discovery
# =========================================================


def test_manufacturing_status_discovers_canonical_realizations(
    tmp_path: Path,
) -> None:
    """
    Inspection includes canonical Realizations available from registered
    Model Variants even when the Artifact has not built those Realizations.
    """

    _define_artifact(
        tmp_path,
    )

    result = inspect_artifact_manufacturing(
        "skippy",
        project_root=tmp_path,
    )

    realizations = _by_name(
        result,
    )

    assert result.artifact_id == "skippy"

    assert "artwork_default" in realizations
    assert "shape_default" in realizations
    assert "shape_ornament" in realizations

    assert realizations["artwork_default"].realization_type is RealizationType.BUILT_IN
    assert realizations["shape_default"].realization_type is RealizationType.BUILT_IN
    assert realizations["shape_ornament"].realization_type is RealizationType.BUILT_IN


# =========================================================
# Custom Realizations
# =========================================================


def test_manufacturing_status_includes_custom_realizations(
    tmp_path: Path,
) -> None:
    """
    Inspection combines canonical Realizations with additional
    Artifact-authored Realizations.
    """

    _define_artifact(
        tmp_path,
        values={
            "realizations": {
                "large-ornament": {
                    "variant": "shape.ornament",
                    "parameters": {
                        "shape_size": 120.0,
                    },
                },
            },
        },
    )

    result = inspect_artifact_manufacturing(
        "skippy",
        project_root=tmp_path,
    )

    realizations = _by_name(
        result,
    )

    assert "shape_ornament" in realizations
    assert "large-ornament" in realizations

    assert realizations["shape_ornament"].realization_type is RealizationType.BUILT_IN

    assert realizations["large-ornament"].realization_type is RealizationType.CUSTOM


# =========================================================
# Manufacturing state
# =========================================================


@pytest.mark.slow
def test_unbuilt_realization_reports_not_built_without_3mf(
    tmp_path: Path,
) -> None:
    """
    A Realization whose manufacturing Product has never been produced is
    reported as not built and has no accessible 3MF.
    """

    _define_artifact(
        tmp_path,
    )

    result = inspect_artifact_manufacturing(
        "skippy",
        realization="shape_ornament",
        project_root=tmp_path,
    )

    assert len(result.realizations) == 1

    realization = result.realizations[0]

    assert realization.realization == "shape_ornament"
    assert realization.state is ManufacturingState.NOT_BUILT
    assert realization.product is None


@pytest.mark.slow
def test_current_realization_reports_current_accessible_3mf(
    tmp_path: Path,
) -> None:
    """
    A current manufacturing Product with an accessible published 3MF is
    reported as current and identifies that publication.
    """

    _define_artifact(
        tmp_path,
    )

    execute_artifact_build(
        "skippy",
        realization="shape_ornament",
        project_root=tmp_path,
    )

    result = inspect_artifact_manufacturing(
        "skippy",
        realization="shape_ornament",
        project_root=tmp_path,
    )

    assert len(result.realizations) == 1

    realization = result.realizations[0]

    assert realization.realization == "shape_ornament"
    assert realization.state is ManufacturingState.CURRENT

    assert realization.product == (tmp_path / "artifacts" / "skippy" / "shape_ornament.3mf")

    assert realization.product is not None
    assert realization.product.is_file()


@pytest.mark.slow
def test_stale_realization_reports_stale_existing_3mf(
    tmp_path: Path,
) -> None:
    """
    An existing published 3MF remains visible when its canonical
    manufacturing Product is stale.

    State and Product availability are separate operator concerns.
    """

    artifact_dir = _define_artifact(
        tmp_path,
    )

    execute_artifact_build(
        "skippy",
        realization="shape_ornament",
        project_root=tmp_path,
    )

    published = artifact_dir / "shape_ornament.3mf"

    assert published.is_file()

    config_path = artifact_dir / "artifact.toml"

    original = config_path.read_text(
        encoding="utf-8",
    )

    config_path.write_text(
        original + "\n" + "[realizations.shape_ornament.parameters]\n" + "shape_size = 110.0\n",
        encoding="utf-8",
    )

    result = inspect_artifact_manufacturing(
        "skippy",
        realization="shape_ornament",
        project_root=tmp_path,
    )

    assert len(result.realizations) == 1

    realization = result.realizations[0]

    assert realization.realization == "shape_ornament"
    assert realization.state is ManufacturingState.STALE
    assert realization.product == published
    assert realization.product is not None
    assert realization.product.is_file()


@pytest.mark.slow
def test_current_realization_without_publication_remains_current(
    tmp_path: Path,
) -> None:
    """
    Missing convenience publication does not make the canonical
    manufacturing Product stale.

    Inspection is read-only and does not restore the publication.
    """

    artifact_dir = _define_artifact(
        tmp_path,
    )

    execute_artifact_build(
        "skippy",
        realization="shape_ornament",
        project_root=tmp_path,
    )

    published = artifact_dir / "shape_ornament.3mf"

    assert published.is_file()

    published.unlink()

    result = inspect_artifact_manufacturing(
        "skippy",
        realization="shape_ornament",
        project_root=tmp_path,
    )

    realization = result.realizations[0]

    assert realization.state is ManufacturingState.CURRENT
    assert realization.product is None

    assert not published.exists()


# =========================================================
# Selected Realization
# =========================================================


def test_manufacturing_status_can_select_one_realization(
    tmp_path: Path,
) -> None:
    """
    A caller can inspect one Realization without UI-side filtering.
    """

    _define_artifact(
        tmp_path,
    )

    result = inspect_artifact_manufacturing(
        "skippy",
        realization="shape_ornament",
        project_root=tmp_path,
    )

    assert tuple(item.realization for item in result.realizations) == ("shape_ornament",)


def test_manufacturing_status_rejects_unknown_realization(
    tmp_path: Path,
) -> None:
    """
    Explicit Realization selection asserts that the Realization exists.
    """

    _define_artifact(
        tmp_path,
    )

    with pytest.raises(
        Exception,
        match="does-not-exist",
    ):
        inspect_artifact_manufacturing(
            "skippy",
            realization="does-not-exist",
            project_root=tmp_path,
        )


# =========================================================
# Read-only inspection
# =========================================================


def test_manufacturing_status_does_not_build_unbuilt_realization(
    tmp_path: Path,
) -> None:
    """
    Manufacturing inspection may plan work but does not execute it.
    """

    artifact_dir = _define_artifact(
        tmp_path,
    )

    result = inspect_artifact_manufacturing(
        "skippy",
        realization="shape_ornament",
        project_root=tmp_path,
    )

    realization = result.realizations[0]

    assert realization.state is ManufacturingState.NOT_BUILT

    assert not (artifact_dir / "shape" / "shape_ornament").exists()

    assert not (artifact_dir / "shape_ornament.3mf").exists()
