"""
Tests for incremental build failure lifecycle observation.

A build failure describes unsuccessful termination of an incremental build
after its build.started event has been emitted.

Failure observation does not replace or transform the original exception.
"""
# File: tests/engine/test_incremental_build_failure_events.py
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
# Test support
# =========================================================


class ExpectedBuildFailure(Exception):
    """
    Stable failure type for expected build execution failures.
    """


def _raise_expected_error() -> None:
    """
    Raise the failure expected by compact test executors.
    """

    raise ExpectedBuildFailure("expected failure")


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
                b"incremental-build-failure-input",
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
# Build failure lifecycle
# =========================================================


def test_failed_incremental_build_emits_build_failed(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Stage execution failure terminates the enclosing build as failed.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    _materialize_external_inputs(
        build_plan,
    )

    events: list[ExecutionEvent] = []

    def execute(
        stage: PlannedStage,
    ) -> None:
        raise ExpectedBuildFailure("expected failure")

    with pytest.raises(
        ExpectedBuildFailure,
        match="expected failure",
    ):
        execute_incremental_build(
            build_plan,
            execute_stage=execute,
            event_sink=events.append,
        )

    failed = tuple(event for event in events if event.kind == "build.failed")

    assert len(failed) == 1


def test_failed_incremental_build_does_not_emit_build_completed(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Failed builds never emit successful build completion.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    _materialize_external_inputs(
        build_plan,
    )

    events: list[ExecutionEvent] = []

    with pytest.raises(
        ExpectedBuildFailure,
        match="expected failure",
    ):
        execute_incremental_build(
            build_plan,
            execute_stage=lambda stage: (_raise_expected_error()),
            event_sink=events.append,
        )

    assert not any(event.kind == "build.completed" for event in events)


def test_build_failed_follows_stage_failed(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Stage failure is observed before enclosing build failure.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    _materialize_external_inputs(
        build_plan,
    )

    events: list[ExecutionEvent] = []

    def execute(
        stage: PlannedStage,
    ) -> None:
        raise ExpectedBuildFailure("expected failure")

    with pytest.raises(
        ExpectedBuildFailure,
        match="expected failure",
    ):
        execute_incremental_build(
            build_plan,
            execute_stage=execute,
            event_sink=events.append,
        )

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


def test_build_failed_event_includes_realized_identity(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Build failure identifies the realized artifact build.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    _materialize_external_inputs(
        build_plan,
    )

    events: list[ExecutionEvent] = []

    with pytest.raises(
        ExpectedBuildFailure,
        match="expected failure",
    ):
        execute_incremental_build(
            build_plan,
            execute_stage=lambda stage: (_raise_expected_error()),
            event_sink=events.append,
        )

    failed = tuple(event for event in events if event.kind == "build.failed")

    assert len(failed) == 1

    event = failed[0]

    assert event.artifact_id == build_plan.artifact_id
    assert event.model_name == build_plan.model_name
    assert event.realization == build_plan.realization_name
    assert event.stage_name is None


# =========================================================
# Exception preservation
# =========================================================


def test_build_failure_preserves_original_exception(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Build failure observation does not transform execution exceptions.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    _materialize_external_inputs(
        build_plan,
    )

    expected = RuntimeError("original execution failure")

    def execute(
        stage: PlannedStage,
    ) -> None:
        raise expected

    with pytest.raises(
        RuntimeError,
        match="original execution failure",
    ) as caught:
        execute_incremental_build(
            build_plan,
            execute_stage=execute,
            event_sink=lambda event: None,
        )

    assert caught.value is expected
