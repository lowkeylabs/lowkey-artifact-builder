"""
Tests for incremental build completion-persistence failure observation.

Successful stage execution is not sufficient to complete a persistent
incremental stage. Completion metadata must also be persisted successfully.

Failure while persisting completion metadata terminates the enclosing build
as failed without reporting successful stage or build completion.
"""
# File: tests/engine/test_incremental_build_completion_failure_events.py
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
                b"incremental-completion-failure-input",
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


def _fail_completion(
    **kwargs,
) -> None:
    """
    Fail completion persistence deterministically.
    """

    raise RuntimeError("completion persistence failure")


# =========================================================
# Completion-persistence failure
# =========================================================


def test_completion_persistence_failure_emits_build_failed(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Failure to persist stage completion fails the enclosing build.
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
        "_write_successful_completion",
        _fail_completion,
    )

    events: list[ExecutionEvent] = []

    with pytest.raises(
        RuntimeError,
        match="completion persistence failure",
    ):
        execute_incremental_build(
            build_plan,
            execute_stage=_materialize_stage_products,
            event_sink=events.append,
        )

    failed = tuple(event for event in events if event.kind == "build.failed")

    assert len(failed) == 1


def test_completion_persistence_failure_does_not_emit_stage_completed(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    A stage is not completed until its completion metadata is persistent.
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
        "_write_successful_completion",
        _fail_completion,
    )

    events: list[ExecutionEvent] = []

    with pytest.raises(
        RuntimeError,
        match="completion persistence failure",
    ):
        execute_incremental_build(
            build_plan,
            execute_stage=_materialize_stage_products,
            event_sink=events.append,
        )

    assert not any(event.kind == "stage.completed" for event in events)


def test_completion_persistence_failure_does_not_emit_stage_failed(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Completion persistence failure is not stage execution failure.
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
        "_write_successful_completion",
        _fail_completion,
    )

    events: list[ExecutionEvent] = []

    with pytest.raises(
        RuntimeError,
        match="completion persistence failure",
    ):
        execute_incremental_build(
            build_plan,
            execute_stage=_materialize_stage_products,
            event_sink=events.append,
        )

    assert not any(event.kind == "stage.failed" for event in events)


def test_completion_persistence_failure_does_not_emit_build_completed(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Completion persistence failure prevents successful build completion.
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
        "_write_successful_completion",
        _fail_completion,
    )

    events: list[ExecutionEvent] = []

    with pytest.raises(
        RuntimeError,
        match="completion persistence failure",
    ):
        execute_incremental_build(
            build_plan,
            execute_stage=_materialize_stage_products,
            event_sink=events.append,
        )

    assert not any(event.kind == "build.completed" for event in events)


def test_completion_persistence_failure_event_order(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Build failure follows stage start when completion persistence fails.
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
        "_write_successful_completion",
        _fail_completion,
    )

    events: list[ExecutionEvent] = []

    with pytest.raises(
        RuntimeError,
        match="completion persistence failure",
    ):
        execute_incremental_build(
            build_plan,
            execute_stage=_materialize_stage_products,
            event_sink=events.append,
        )

    lifecycle = tuple(
        event.kind
        for event in events
        if event.kind
        in {
            "build.started",
            "stage.started",
            "stage.completed",
            "stage.failed",
            "build.failed",
            "build.completed",
        }
    )

    assert lifecycle == (
        "build.started",
        "stage.started",
        "build.failed",
    )


def test_completion_failure_preserves_original_exception(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Completion failure observation preserves the original exception.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    _materialize_external_inputs(
        build_plan,
    )

    expected = RuntimeError("original completion failure")

    def fail_completion(
        **kwargs,
    ) -> None:
        raise expected

    monkeypatch.setattr(
        incremental,
        "_write_successful_completion",
        fail_completion,
    )

    with pytest.raises(RuntimeError) as caught:
        execute_incremental_build(
            build_plan,
            execute_stage=_materialize_stage_products,
            event_sink=lambda event: None,
        )

    assert caught.value is expected
