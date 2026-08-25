"""
Tests for incremental build lifecycle observation.

Build lifecycle events describe the outer incremental execution boundary.
They complement product-state and stage lifecycle observations without
participating in execution decisions.
"""
# File: tests/engine/test_incremental_build_events.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from lowkey_artifact_builder.engine import (
    BuildPlan,
    ExecutionEvent,
    PlannedStage,
    execute_incremental_build,
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
                b"incremental-build-event-input",
            )


def _materialize_stage_products(
    stage: PlannedStage,
) -> None:
    """
    Materialize every persistent product declared by one stage.
    """

    for product in stage.products:
        product.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        product.path.write_bytes(
            b"persistent-product",
        )


def _build_events(
    events: list[ExecutionEvent],
) -> tuple[ExecutionEvent, ...]:
    """
    Return build lifecycle events from an observation stream.
    """

    return tuple(
        event
        for event in events
        if event.kind
        in {
            "build.started",
            "build.completed",
        }
    )


# =========================================================
# Build lifecycle
# =========================================================


def test_incremental_build_emits_started_event(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Incremental execution emits build.started once per invocation.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    _materialize_external_inputs(
        build_plan,
    )

    events: list[ExecutionEvent] = []

    execute_incremental_build(
        build_plan,
        execute_stage=_materialize_stage_products,
        event_sink=events.append,
    )

    started = tuple(event for event in events if event.kind == "build.started")

    assert len(started) == 1


def test_successful_incremental_build_emits_completed_event(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Successful incremental execution emits build.completed once.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    _materialize_external_inputs(
        build_plan,
    )

    events: list[ExecutionEvent] = []

    execute_incremental_build(
        build_plan,
        execute_stage=_materialize_stage_products,
        event_sink=events.append,
    )

    completed = tuple(event for event in events if event.kind == "build.completed")

    assert len(completed) == 1


def test_incremental_build_events_include_realized_identity(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Build lifecycle events identify the realized artifact build.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    _materialize_external_inputs(
        build_plan,
    )

    events: list[ExecutionEvent] = []

    execute_incremental_build(
        build_plan,
        execute_stage=_materialize_stage_products,
        event_sink=events.append,
    )

    build_events = _build_events(
        events,
    )

    assert len(build_events) == 2

    for event in build_events:
        assert event.artifact_id == build_plan.artifact_id
        assert event.model_name == build_plan.model_name
        assert event.realization == build_plan.realization_name
        assert event.stage_name is None


# =========================================================
# Build lifecycle ordering
# =========================================================


def test_build_started_precedes_product_and_stage_events(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    build.started is the first semantic event for incremental execution.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    _materialize_external_inputs(
        build_plan,
    )

    events: list[ExecutionEvent] = []

    execute_incremental_build(
        build_plan,
        execute_stage=_materialize_stage_products,
        event_sink=events.append,
    )

    assert events

    assert events[0].kind == "build.started"


def test_build_completed_follows_all_product_and_stage_events(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    build.completed is the final semantic event after successful execution.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    _materialize_external_inputs(
        build_plan,
    )

    events: list[ExecutionEvent] = []

    execute_incremental_build(
        build_plan,
        execute_stage=_materialize_stage_products,
        event_sink=events.append,
    )

    assert events

    assert events[-1].kind == "build.completed"


def test_fully_reusable_build_still_emits_build_lifecycle(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    A no-work incremental invocation remains an observed build operation.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    _materialize_external_inputs(
        build_plan,
    )

    execute_incremental_build(
        build_plan,
        execute_stage=_materialize_stage_products,
    )

    events: list[ExecutionEvent] = []
    executed: list[str] = []

    execute_incremental_build(
        build_plan,
        execute_stage=lambda stage: executed.append(
            stage.name,
        ),
        event_sink=events.append,
    )

    assert executed == []

    build_events = _build_events(
        events,
    )

    assert tuple(event.kind for event in build_events) == (
        "build.started",
        "build.completed",
    )

    assert events[0].kind == "build.started"
    assert events[-1].kind == "build.completed"
