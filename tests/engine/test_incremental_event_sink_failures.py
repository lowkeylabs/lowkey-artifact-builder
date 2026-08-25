"""
Tests for incremental event observer isolation.

Execution observation is optional infrastructure. Failure of an event sink
must not alter incremental planning, stage execution, persistence, or the
successful result of a build.
"""
# File: tests/engine/test_incremental_event_sink_failures.py
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
    plan_incremental_execution,
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
                b"incremental-event-sink-failure-input",
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


class ObserverFailure(Exception):
    """
    Failure raised only by the test event observer.
    """


def _failing_sink(
    event: ExecutionEvent,
) -> None:
    """
    Fail whenever an execution event is observed.
    """

    raise ObserverFailure(
        event.kind,
    )


# =========================================================
# Observer isolation
# =========================================================


def test_failing_event_sink_does_not_fail_build(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Observer failure does not become build failure.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    _materialize_external_inputs(
        build_plan,
    )

    execution_plan = execute_incremental_build(
        build_plan,
        execute_stage=_materialize_stage_products,
        event_sink=_failing_sink,
    )

    assert execution_plan.required_stages


def test_failing_event_sink_does_not_prevent_stage_execution(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Observer failure cannot prevent required stage execution.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    _materialize_external_inputs(
        build_plan,
    )

    executed: list[str] = []

    def execute(
        stage: PlannedStage,
    ) -> None:
        executed.append(
            stage.name,
        )

        _materialize_stage_products(
            stage,
        )

    execute_incremental_build(
        build_plan,
        execute_stage=execute,
        event_sink=_failing_sink,
    )

    assert executed == [stage.name for stage in build_plan.stages if stage.products]


def test_failing_event_sink_does_not_prevent_completion_persistence(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Observer failure cannot prevent persistent incremental convergence.
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
        event_sink=_failing_sink,
    )

    execution_plan = plan_incremental_execution(
        build_plan,
    )

    assert execution_plan.required_stages == ()


def test_failing_event_sink_does_not_change_reusable_build(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Observer failure cannot turn a no-work incremental build into work.
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

    executed: list[str] = []

    execution_plan = execute_incremental_build(
        build_plan,
        execute_stage=lambda stage: executed.append(
            stage.name,
        ),
        event_sink=_failing_sink,
    )

    assert execution_plan.required_stages == ()
    assert executed == []
