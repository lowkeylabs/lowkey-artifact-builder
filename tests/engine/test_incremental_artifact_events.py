"""
Tests for artifact-level incremental execution observation.

Artifact-level incremental execution adapts realized PlannedStage objects
to StageContext execution while preserving the execution-event contract
provided by the lower-level incremental build orchestrator.
"""
# File: tests/engine/test_incremental_artifact_events.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

import lowkey_artifact_builder.engine.incremental as incremental
from lowkey_artifact_builder.engine import (
    BuildPlan,
    ExecutionEvent,
    StageContext,
    execute_incremental_artifact_build,
)

type ArtworkPlanFactory = Callable[..., BuildPlan]


# =========================================================
# Helpers
# =========================================================


def _materialize_external_inputs(
    build_plan: BuildPlan,
) -> None:
    """
    Materialize deterministic content for all external inputs.
    """

    for stage in build_plan.stages:
        for planned_input in stage.inputs:
            planned_input.path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            planned_input.path.write_bytes(
                b"incremental-artifact-event-input",
            )


def _materialize_context_products(
    context: StageContext,
) -> None:
    """
    Materialize every persistent output resolved for one stage context.
    """

    for path in context.outputs.values():
        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        path.write_bytes(
            b"persistent-product",
        )


# =========================================================
# Artifact lifecycle observation
# =========================================================


def test_artifact_build_emits_build_lifecycle_events(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Artifact execution exposes enclosing build lifecycle events.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    _materialize_external_inputs(
        build_plan,
    )

    monkeypatch.setattr(
        incremental,
        "execute_stage",
        _materialize_context_products,
    )

    events: list[ExecutionEvent] = []

    execute_incremental_artifact_build(
        build_plan,
        event_sink=events.append,
    )

    lifecycle = tuple(
        event.kind
        for event in events
        if event.kind
        in {
            "build.started",
            "build.completed",
            "build.failed",
        }
    )

    assert lifecycle == (
        "build.started",
        "build.completed",
    )


def test_artifact_build_emits_stage_lifecycle_events(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Artifact execution exposes lifecycle events for required stages.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    _materialize_external_inputs(
        build_plan,
    )

    monkeypatch.setattr(
        incremental,
        "execute_stage",
        _materialize_context_products,
    )

    events: list[ExecutionEvent] = []

    execute_incremental_artifact_build(
        build_plan,
        event_sink=events.append,
    )

    started = tuple(event.stage_name for event in events if event.kind == "stage.started")

    completed = tuple(event.stage_name for event in events if event.kind == "stage.completed")

    expected = tuple(stage.name for stage in build_plan.stages if stage.products)

    assert started == expected
    assert completed == expected


def test_reusable_artifact_build_emits_skipped_events(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Artifact execution exposes reuse observations on a converged build.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    _materialize_external_inputs(
        build_plan,
    )

    monkeypatch.setattr(
        incremental,
        "execute_stage",
        _materialize_context_products,
    )

    execute_incremental_artifact_build(
        build_plan,
    )

    events: list[ExecutionEvent] = []

    execution_plan = execute_incremental_artifact_build(
        build_plan,
        event_sink=events.append,
    )

    assert execution_plan.required_stages == ()

    skipped = tuple(event.stage_name for event in events if event.kind == "stage.skipped")

    assert skipped == tuple(stage.name for stage in build_plan.stages if stage.products)


# =========================================================
# Artifact failure observation
# =========================================================


def test_artifact_stage_failure_emits_failure_lifecycle(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Artifact dispatch failure exposes stage and build failure events.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    _materialize_external_inputs(
        build_plan,
    )

    expected = RuntimeError("artifact stage failure")

    def fail(
        context: StageContext,
    ) -> None:
        raise expected

    monkeypatch.setattr(
        incremental,
        "execute_stage",
        fail,
    )

    events: list[ExecutionEvent] = []

    with pytest.raises(RuntimeError) as caught:
        execute_incremental_artifact_build(
            build_plan,
            event_sink=events.append,
        )

    assert caught.value is expected

    lifecycle = tuple(
        event.kind
        for event in events
        if event.kind
        in {
            "build.started",
            "stage.started",
            "stage.failed",
            "build.failed",
            "build.completed",
        }
    )

    assert lifecycle == (
        "build.started",
        "stage.started",
        "stage.failed",
        "build.failed",
    )


def test_artifact_events_include_realized_identity(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Artifact-level events retain the realized build identity.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    _materialize_external_inputs(
        build_plan,
    )

    monkeypatch.setattr(
        incremental,
        "execute_stage",
        _materialize_context_products,
    )

    events: list[ExecutionEvent] = []

    execute_incremental_artifact_build(
        build_plan,
        event_sink=events.append,
    )

    assert events

    for event in events:
        assert event.artifact_id == build_plan.artifact_id
        assert event.model_name == build_plan.model_name
        assert event.realization == build_plan.realization_name
