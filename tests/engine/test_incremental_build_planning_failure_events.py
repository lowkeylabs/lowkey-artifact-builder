"""
Tests for incremental build planning failure observation.

Once incremental execution has emitted build.started, failure while
constructing the required build context or execution plan terminates the
enclosing build as failed.

Failure observation does not replace or transform the original exception.
"""
# File: tests/engine/test_incremental_build_planning_failure_events.py
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
                b"incremental-planning-failure-input",
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


# =========================================================
# Fingerprint failure
# =========================================================


def test_fingerprint_failure_emits_build_failed(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Failure while deriving required fingerprints fails the build.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    _materialize_external_inputs(
        build_plan,
    )

    events: list[ExecutionEvent] = []

    expected = RuntimeError("fingerprint failure")

    def fail_fingerprints(
        build_plan: BuildPlan,
    ) -> dict:
        raise expected

    monkeypatch.setattr(
        incremental,
        "create_required_fingerprints",
        fail_fingerprints,
    )

    with pytest.raises(RuntimeError) as caught:
        execute_incremental_build(
            build_plan,
            execute_stage=_materialize_stage_products,
            event_sink=events.append,
        )

    assert caught.value is expected

    assert tuple(event.kind for event in events) == (
        "build.started",
        "build.failed",
    )


def test_fingerprint_failure_does_not_emit_build_completed(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Fingerprint failure cannot produce successful build completion.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    _materialize_external_inputs(
        build_plan,
    )

    def fail_fingerprints(
        build_plan: BuildPlan,
    ) -> dict:
        raise RuntimeError("fingerprint failure")

    monkeypatch.setattr(
        incremental,
        "create_required_fingerprints",
        fail_fingerprints,
    )

    events: list[ExecutionEvent] = []

    with pytest.raises(
        RuntimeError,
        match="fingerprint failure",
    ):
        execute_incremental_build(
            build_plan,
            execute_stage=_materialize_stage_products,
            event_sink=events.append,
        )

    assert not any(event.kind == "build.completed" for event in events)


# =========================================================
# Execution-plan failure
# =========================================================


def test_execution_plan_failure_emits_build_failed(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Failure while constructing the execution plan fails the build.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    _materialize_external_inputs(
        build_plan,
    )

    events: list[ExecutionEvent] = []

    expected = RuntimeError("execution plan failure")

    def fail_execution_plan(
        **kwargs,
    ):
        raise expected

    monkeypatch.setattr(
        incremental,
        "_create_incremental_execution_plan",
        fail_execution_plan,
    )

    with pytest.raises(RuntimeError) as caught:
        execute_incremental_build(
            build_plan,
            execute_stage=_materialize_stage_products,
            event_sink=events.append,
        )

    assert caught.value is expected

    assert tuple(event.kind for event in events) == (
        "build.started",
        "build.failed",
    )


def test_planning_failure_executes_no_stage(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Failure before execution-plan completion executes no realized stage.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    _materialize_external_inputs(
        build_plan,
    )

    executed: list[str] = []

    def fail_execution_plan(
        **kwargs,
    ):
        raise RuntimeError("execution plan failure")

    monkeypatch.setattr(
        incremental,
        "_create_incremental_execution_plan",
        fail_execution_plan,
    )

    with pytest.raises(
        RuntimeError,
        match="execution plan failure",
    ):
        execute_incremental_build(
            build_plan,
            execute_stage=lambda stage: executed.append(
                stage.name,
            ),
        )

    assert executed == []


# =========================================================
# Failure identity
# =========================================================


def test_planning_build_failed_event_includes_realized_identity(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Planning failure identifies the realized artifact build.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    _materialize_external_inputs(
        build_plan,
    )

    def fail_fingerprints(
        build_plan: BuildPlan,
    ) -> dict:
        raise RuntimeError("fingerprint failure")

    monkeypatch.setattr(
        incremental,
        "create_required_fingerprints",
        fail_fingerprints,
    )

    events: list[ExecutionEvent] = []

    with pytest.raises(
        RuntimeError,
        match="fingerprint failure",
    ):
        execute_incremental_build(
            build_plan,
            execute_stage=_materialize_stage_products,
            event_sink=events.append,
        )

    failed = tuple(event for event in events if event.kind == "build.failed")

    assert len(failed) == 1

    event = failed[0]

    assert event.artifact_id == build_plan.artifact_id
    assert event.model_name == build_plan.model_name
    assert event.realization == build_plan.realization_name
    assert event.stage_name is None
