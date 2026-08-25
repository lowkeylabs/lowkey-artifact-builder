"""
Tests for event-sink isolation during incremental build failure.

A genuine engine failure remains authoritative even when the optional
event observer also fails. Observer failure must not replace, mask, or
otherwise alter the original build exception.
"""
# File: tests/engine/test_incremental_failure_sink_isolation.py
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
                b"incremental-failure-sink-input",
            )


# =========================================================
# Failure isolation
# =========================================================


def test_failing_sink_does_not_replace_stage_execution_failure(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    The original stage exception remains authoritative.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    _materialize_external_inputs(
        build_plan,
    )

    expected = RuntimeError("original stage failure")

    def execute(
        stage: PlannedStage,
    ) -> None:
        raise expected

    def observe(
        event: ExecutionEvent,
    ) -> None:
        raise ValueError(f"observer failed on {event.kind}")

    with pytest.raises(RuntimeError) as caught:
        execute_incremental_build(
            build_plan,
            execute_stage=execute,
            event_sink=observe,
        )

    assert caught.value is expected


def test_sink_failure_while_observing_stage_failed_is_suppressed(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Failure observing stage.failed cannot mask the stage exception.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    _materialize_external_inputs(
        build_plan,
    )

    expected = RuntimeError("original stage failure")

    observed: list[str] = []

    def execute(
        stage: PlannedStage,
    ) -> None:
        raise expected

    def observe(
        event: ExecutionEvent,
    ) -> None:
        observed.append(
            event.kind,
        )

        if event.kind == "stage.failed":
            raise ValueError("stage.failed observer failure")

    with pytest.raises(RuntimeError) as caught:
        execute_incremental_build(
            build_plan,
            execute_stage=execute,
            event_sink=observe,
        )

    assert caught.value is expected
    assert "stage.failed" in observed
    assert "build.failed" in observed


def test_sink_failure_while_observing_build_failed_is_suppressed(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Failure observing build.failed cannot mask the build exception.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    _materialize_external_inputs(
        build_plan,
    )

    expected = RuntimeError("original stage failure")

    observed: list[str] = []

    def execute(
        stage: PlannedStage,
    ) -> None:
        raise expected

    def observe(
        event: ExecutionEvent,
    ) -> None:
        observed.append(
            event.kind,
        )

        if event.kind == "build.failed":
            raise ValueError("build.failed observer failure")

    with pytest.raises(RuntimeError) as caught:
        execute_incremental_build(
            build_plan,
            execute_stage=execute,
            event_sink=observe,
        )

    assert caught.value is expected
    assert "stage.failed" in observed
    assert "build.failed" in observed


def test_failure_observation_attempts_each_lifecycle_event_once(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Failure lifecycle events are not retried after observer failure.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    _materialize_external_inputs(
        build_plan,
    )

    observed: list[str] = []

    def execute(
        stage: PlannedStage,
    ) -> None:
        raise RuntimeError("original stage failure")

    def observe(
        event: ExecutionEvent,
    ) -> None:
        observed.append(
            event.kind,
        )

        if event.kind in {
            "stage.failed",
            "build.failed",
        }:
            raise ValueError("observer failure")

    with pytest.raises(
        RuntimeError,
        match="original stage failure",
    ):
        execute_incremental_build(
            build_plan,
            execute_stage=execute,
            event_sink=observe,
        )

    assert (
        observed.count(
            "stage.failed",
        )
        == 1
    )

    assert (
        observed.count(
            "build.failed",
        )
        == 1
    )
