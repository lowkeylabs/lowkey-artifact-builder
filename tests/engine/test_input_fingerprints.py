"""
Tests for external-input fingerprint propagation.

External filesystem inputs participate in required stage provenance by
content rather than by pathname, modification time, or workspace location.

Changing external input content invalidates the consuming stage and all
downstream stages whose provenance depends on it.

These tests exercise required fingerprint construction only. They do not
inspect persistent product state, completion metadata, execution events,
or stage execution.
"""
# File: tests/engine/test_input_fingerprints.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from lowkey_artifact_builder.engine import (
    BuildPlan,
    PlannedStage,
    create_required_fingerprints,
)

type ArtworkPlanFactory = Callable[..., BuildPlan]


# =========================================================
# Helpers
# =========================================================


def _input_stage(
    build_plan: BuildPlan,
) -> PlannedStage:
    """
    Return the first realized stage consuming an external input.
    """

    for stage in build_plan.stages:
        if stage.inputs:
            return stage

    raise AssertionError("Artwork build plan contains no stage with external inputs.")


def _descendant_stage_names(
    build_plan: BuildPlan,
    stage_name: str,
) -> tuple[str, ...]:
    """
    Return realized stages transitively depending on stage_name.
    """

    descendants: list[str] = []
    reached = {stage_name}

    for stage in build_plan.stages:
        if any(dependency in reached for dependency in stage.spec.dependencies):
            reached.add(
                stage.name,
            )
            descendants.append(
                stage.name,
            )

    return tuple(
        descendants,
    )


def _write_input_sources(
    stage: PlannedStage,
    *,
    content: bytes,
) -> None:
    """
    Write deterministic content to every configured external input source.
    """

    for planned_input in stage.inputs:
        planned_input.source_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        planned_input.source_path.write_bytes(
            content,
        )


# =========================================================
# External-input content
# =========================================================


def test_required_fingerprint_accepts_external_input_source(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Required provenance can be derived from a configured external input source.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    stage = _input_stage(
        build_plan,
    )

    _write_input_sources(
        stage,
        content=b"input-content",
    )

    fingerprints = create_required_fingerprints(
        build_plan,
    )

    assert stage.name in fingerprints


def test_required_fingerprint_uses_external_source_before_materialization(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Required provenance comes from the configured external source.

    Planning preserves both the configured external source path and the
    artifact-owned path at which that input will later be materialized.

    Required fingerprint construction occurs before stage execution may have
    materialized the artifact-owned input. It therefore derives external-input
    provenance from source_path rather than requiring path to exist.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    stage = _input_stage(
        build_plan,
    )

    assert stage.inputs

    for index, planned_input in enumerate(
        stage.inputs,
    ):
        planned_input.source_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        planned_input.source_path.write_bytes(
            f"source-{index}".encode(),
        )

        assert planned_input.source_path.is_file()
        assert not planned_input.path.exists()

    fingerprints = create_required_fingerprints(
        build_plan,
    )

    assert stage.name in fingerprints


def test_changing_external_input_content_changes_stage_fingerprint(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Changing input bytes changes provenance of the consuming stage.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    stage = _input_stage(
        build_plan,
    )

    _write_input_sources(
        stage,
        content=b"first-content",
    )

    first = create_required_fingerprints(
        build_plan,
    )

    _write_input_sources(
        stage,
        content=b"second-content",
    )

    second = create_required_fingerprints(
        build_plan,
    )

    assert first[stage.name] != second[stage.name]


def test_identical_external_input_content_is_deterministic(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Unchanged input bytes produce unchanged required provenance.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    stage = _input_stage(
        build_plan,
    )

    _write_input_sources(
        stage,
        content=b"same-content",
    )

    first = create_required_fingerprints(
        build_plan,
    )

    second = create_required_fingerprints(
        build_plan,
    )

    assert first == second


def test_external_input_mtime_does_not_change_fingerprint(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Filesystem timestamps are not semantic build provenance.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    stage = _input_stage(
        build_plan,
    )

    _write_input_sources(
        stage,
        content=b"same-content",
    )

    first = create_required_fingerprints(
        build_plan,
    )

    for planned_input in stage.inputs:
        stat = planned_input.source_path.stat()

        planned_input.source_path.touch()

        assert planned_input.source_path.stat().st_mtime_ns >= stat.st_mtime_ns

    second = create_required_fingerprints(
        build_plan,
    )

    assert first == second


# =========================================================
# Dependency propagation
# =========================================================


def test_external_input_change_propagates_to_descendants(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Changed external input provenance reaches dependent descendants.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    stage = _input_stage(
        build_plan,
    )

    descendants = _descendant_stage_names(
        build_plan,
        stage.name,
    )

    assert descendants

    _write_input_sources(
        stage,
        content=b"first-content",
    )

    first = create_required_fingerprints(
        build_plan,
    )

    _write_input_sources(
        stage,
        content=b"changed-content",
    )

    second = create_required_fingerprints(
        build_plan,
    )

    assert first[stage.name] != second[stage.name]

    for descendant in descendants:
        assert first[descendant] != second[descendant]


# =========================================================
# Location independence
# =========================================================


def test_identical_input_content_at_different_paths_has_same_provenance(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Equivalent input bytes have equivalent provenance across workspaces.
    """

    first_plan = artwork_plan(
        tmp_path / "first",
        monkeypatch,
    )

    first_stage = _input_stage(
        first_plan,
    )

    _write_input_sources(
        first_stage,
        content=b"identical-content",
    )

    first = create_required_fingerprints(
        first_plan,
    )

    second_plan = artwork_plan(
        tmp_path / "second",
        monkeypatch,
    )

    second_stage = _input_stage(
        second_plan,
    )

    _write_input_sources(
        second_stage,
        content=b"identical-content",
    )

    second = create_required_fingerprints(
        second_plan,
    )

    assert first[first_stage.name] == second[second_stage.name]


# =========================================================
# Multiple external inputs
# =========================================================


def test_each_external_input_contributes_to_stage_fingerprint(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Changing each declared external input changes consuming-stage provenance.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    stage = _input_stage(
        build_plan,
    )

    assert stage.inputs

    for index, planned_input in enumerate(
        stage.inputs,
    ):
        planned_input.source_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        planned_input.source_path.write_bytes(
            f"input-{index}".encode(),
        )

    baseline = create_required_fingerprints(
        build_plan,
    )

    for planned_input in stage.inputs:
        original = planned_input.source_path.read_bytes()

        planned_input.source_path.write_bytes(
            original + b"-changed",
        )

        changed = create_required_fingerprints(
            build_plan,
        )

        assert baseline[stage.name] != changed[stage.name]

        planned_input.source_path.write_bytes(
            original,
        )
