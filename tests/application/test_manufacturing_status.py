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

import lowkey_artifact_builder.application.manufacturing as manufacturing
from lowkey_artifact_builder.application.manufacturing import (
    ArtifactManufacturingStatus,
    ManufacturingState,
    RealizationManufacturingStatus,
    RealizationType,
    WorkspaceArtifactManufacturingStatus,
    WorkspaceManufacturingStatus,
    inspect_artifact_manufacturing,
    inspect_workspace_manufacturing,
)
from lowkey_artifact_builder.config import (
    ConfigError,
    configure_artifact,
    get_realization_names,
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


# =========================================================
# Workspace manufacturing inspection
# =========================================================


def test_workspace_inspection_discovers_artifacts(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    Workspace manufacturing inspection discovers Artifact identity through
    the reusable Artifact discovery boundary.
    """

    from lowkey_artifact_builder.config import ArtifactState

    discovery_roots: list[Path] = []

    def discover(
        *,
        project_root: Path,
    ) -> tuple[ArtifactState, ...]:
        discovery_roots.append(
            project_root,
        )

        return (
            ArtifactState(
                artifact_id="alpha",
                original_path=tmp_path / "originals" / "alpha.png",
                materialized=False,
            ),
            ArtifactState(
                artifact_id="beta",
                original_path=None,
                materialized=False,
            ),
        )

    monkeypatch.setattr(
        manufacturing,
        "discover_artifacts",
        discover,
    )

    monkeypatch.setattr(
        manufacturing,
        "inspect_artifact_manufacturing",
        lambda artifact_id, *, project_root: ArtifactManufacturingStatus(
            artifact_id=artifact_id,
            realizations=(),
        ),
    )

    result = inspect_workspace_manufacturing(
        project_root=tmp_path,
    )

    assert discovery_roots == [
        tmp_path,
    ]

    assert tuple(artifact.artifact_id for artifact in result.artifacts) == (
        "alpha",
        "beta",
    )


def test_workspace_inspection_reports_unmaterialized_png_artifact_not_built(
    tmp_path: Path,
) -> None:
    """
    A preserved PNG establishes an Artifact whose canonical Realizations
    remain visible to manufacturing inspection before materialization.

    Inspection is read-only. Missing materialized build inputs mean the
    Realizations have not been built; they do not make the Artifact
    undiscoverable or cause inspection to fail.
    """

    originals = tmp_path / "originals"
    originals.mkdir(
        parents=True,
    )

    source_fixture = Path(__file__).resolve().parents[1] / "assets" / "nydeli-clean.png"

    shutil.copyfile(
        source_fixture,
        originals / "skippy.png",
    )

    config_path = tmp_path / "artifacts" / "skippy" / "artifact.toml"

    assert not config_path.exists()

    result = inspect_workspace_manufacturing(
        project_root=tmp_path,
    )

    assert len(result.artifacts) == 1

    artifact = result.artifacts[0]

    assert artifact.artifact_id == "skippy"
    assert artifact.materialized is False
    assert artifact.manufacturing is not None

    realizations = _by_name(
        artifact.manufacturing,
    )

    assert "artwork_default" in realizations
    assert "shape_default" in realizations
    assert "shape_ornament" in realizations

    assert all(
        realization.state is ManufacturingState.NOT_BUILT for realization in realizations.values()
    )

    assert all(realization.product is None for realization in realizations.values())

    assert not config_path.exists()


def test_manufacturing_status_rejects_unknown_artifact(
    tmp_path: Path,
) -> None:
    """
    Manufacturing inspection requires a discovered Artifact identity.

    Canonical Model Realizations do not independently establish an Artifact.
    """

    with pytest.raises(
        ConfigError,
        match="Artifact 'missing' is not defined",
    ):
        inspect_artifact_manufacturing(
            "missing",
            project_root=tmp_path,
        )


def test_unmaterialized_artifact_has_canonical_realizations(
    tmp_path: Path,
) -> None:
    """
    Canonical Realization existence does not depend on Artifact
    materialization or complete manufacturing inputs.
    """

    originals = tmp_path / "originals"
    originals.mkdir(
        parents=True,
    )

    (originals / "skippy.artifact").touch()

    config_path = tmp_path / "artifacts" / "skippy" / "artifact.toml"

    assert not config_path.exists()

    realization_names = get_realization_names(
        "skippy",
        project_root=tmp_path,
    )

    assert "artwork_default" in realization_names
    assert "shape_default" in realization_names
    assert "shape_ornament" in realization_names

    assert not config_path.exists()


def test_workspace_inspection_inspects_artifacts_independent_of_materialization(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    Every discovered Artifact receives manufacturing inspection regardless
    of whether persistent Artifact configuration has been materialized.

    Materialization remains an independent property of workspace state.
    """

    from lowkey_artifact_builder.config import ArtifactState

    monkeypatch.setattr(
        manufacturing,
        "discover_artifacts",
        lambda *, project_root: (
            ArtifactState(
                artifact_id="registered",
                original_path=tmp_path / "originals" / "registered.png",
                materialized=False,
            ),
            ArtifactState(
                artifact_id="materialized",
                original_path=None,
                materialized=True,
            ),
        ),
    )

    inspected: list[
        tuple[
            str,
            Path,
        ]
    ] = []

    def inspect(
        artifact_id: str,
        *,
        project_root: Path,
    ) -> ArtifactManufacturingStatus:
        inspected.append(
            (
                artifact_id,
                project_root,
            )
        )

        return ArtifactManufacturingStatus(
            artifact_id=artifact_id,
            realizations=(),
        )

    monkeypatch.setattr(
        manufacturing,
        "inspect_artifact_manufacturing",
        inspect,
    )

    result = inspect_workspace_manufacturing(
        project_root=tmp_path,
    )

    assert inspected == [
        (
            "registered",
            tmp_path,
        ),
        (
            "materialized",
            tmp_path,
        ),
    ]

    assert result.artifacts == (
        WorkspaceArtifactManufacturingStatus(
            artifact_id="registered",
            materialized=False,
            manufacturing=ArtifactManufacturingStatus(
                artifact_id="registered",
                realizations=(),
            ),
        ),
        WorkspaceArtifactManufacturingStatus(
            artifact_id="materialized",
            materialized=True,
            manufacturing=ArtifactManufacturingStatus(
                artifact_id="materialized",
                realizations=(),
            ),
        ),
    )


def test_workspace_inspection_preserves_artifact_manufacturing_status(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    Workspace inspection composes existing Artifact manufacturing
    inspection rather than reconstructing Realization state.
    """

    from lowkey_artifact_builder.config import ArtifactState

    artifact_status = ArtifactManufacturingStatus(
        artifact_id="dog",
        realizations=(
            RealizationManufacturingStatus(
                realization="shape_ornament",
                realization_type=RealizationType.BUILT_IN,
                state=ManufacturingState.STALE,
                product=tmp_path / "artifacts" / "dog" / "shape_ornament.3mf",
            ),
        ),
    )

    monkeypatch.setattr(
        manufacturing,
        "discover_artifacts",
        lambda *, project_root: (
            ArtifactState(
                artifact_id="dog",
                original_path=None,
                materialized=True,
            ),
        ),
    )

    monkeypatch.setattr(
        manufacturing,
        "inspect_artifact_manufacturing",
        lambda artifact_id, *, project_root: artifact_status,
    )

    result = inspect_workspace_manufacturing(
        project_root=tmp_path,
    )

    assert result == WorkspaceManufacturingStatus(
        artifacts=(
            WorkspaceArtifactManufacturingStatus(
                artifact_id="dog",
                materialized=True,
                manufacturing=artifact_status,
            ),
        ),
    )
