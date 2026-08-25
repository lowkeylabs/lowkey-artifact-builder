"""
Tests for incremental stage execution events.

Incremental execution exposes semantic stage lifecycle observations through
the engine event contract.

A required stage emits a started event immediately before execution and a
completed event only after successful execution and completion persistence.

Observation is optional and does not alter execution semantics.
"""
# File: tests/engine/test_incremental_events.py
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
                b"incremental-event-input",
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


def _persistent_stage_names(
    build_plan: BuildPlan,
) -> tuple[str, ...]:
    """
    Return realized stages declaring persistent products.
    """

    return tuple(stage.name for stage in build_plan.stages if stage.products)


# =========================================================
# Successful stage lifecycle
# =========================================================


def test_incremental_build_emits_started_event_before_each_required_stage(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Every required stage emits stage.started immediately before execution.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    _materialize_external_inputs(
        build_plan,
    )

    observations: list[tuple[str, str]] = []

    def observe(
        event: ExecutionEvent,
    ) -> None:
        if event.kind == "stage.started":
            assert event.stage_name is not None

            observations.append(
                (
                    "event",
                    event.stage_name,
                )
            )

    def execute(
        stage: PlannedStage,
    ) -> None:
        observations.append(
            (
                "execute",
                stage.name,
            )
        )

        _materialize_stage_products(
            stage,
        )

    execute_incremental_build(
        build_plan,
        execute_stage=execute,
        event_sink=observe,
    )

    expected: list[tuple[str, str]] = []

    for stage_name in _persistent_stage_names(
        build_plan,
    ):
        expected.extend(
            [
                (
                    "event",
                    stage_name,
                ),
                (
                    "execute",
                    stage_name,
                ),
            ]
        )

    assert observations == expected


def test_incremental_build_emits_completed_event_after_successful_stage(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Successful required stages emit stage.completed after execution.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    _materialize_external_inputs(
        build_plan,
    )

    observations: list[tuple[str, str]] = []

    def observe(
        event: ExecutionEvent,
    ) -> None:
        if event.kind in {
            "stage.started",
            "stage.completed",
        }:
            assert event.stage_name is not None

            observations.append(
                (
                    event.kind,
                    event.stage_name,
                )
            )

    def execute(
        stage: PlannedStage,
    ) -> None:
        _materialize_stage_products(
            stage,
        )

    execute_incremental_build(
        build_plan,
        execute_stage=execute,
        event_sink=observe,
    )

    expected: list[tuple[str, str]] = []

    for stage_name in _persistent_stage_names(
        build_plan,
    ):
        expected.extend(
            [
                (
                    "stage.started",
                    stage_name,
                ),
                (
                    "stage.completed",
                    stage_name,
                ),
            ]
        )

    assert observations == expected


def test_incremental_stage_events_include_realized_identity(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Stage lifecycle events identify their realized execution scope.
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

    lifecycle = tuple(
        event
        for event in events
        if event.kind
        in {
            "stage.started",
            "stage.completed",
        }
    )

    assert lifecycle

    for event in lifecycle:
        assert event.artifact_id == build_plan.artifact_id
        assert event.model_name == build_plan.model_name
        assert event.realization == build_plan.realization_name
        assert event.stage_name is not None


# =========================================================
# Optional observation
# =========================================================


def test_incremental_build_without_event_sink_preserves_execution(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Incremental execution does not require an observer.
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
    )

    assert tuple(
        executed,
    ) == _persistent_stage_names(
        build_plan,
    )
