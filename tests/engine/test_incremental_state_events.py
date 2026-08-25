"""
Tests for product-state observation during incremental execution.

Incremental execution exposes the persistent product-state decisions used
to determine whether realized stages require execution.

Product-state observation is semantic and presentation-independent.
Observation does not alter planning or execution decisions.
"""
# File: tests/engine/test_incremental_state_events.py
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
    ProductState,
    ProductStateEvent,
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
                b"incremental-state-event-input",
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


def _persistent_product_count(
    build_plan: BuildPlan,
) -> int:
    """
    Return the number of realized persistent products.
    """

    return sum(len(stage.products) for stage in build_plan.stages)


# =========================================================
# Product-state observation
# =========================================================


def test_incremental_build_emits_product_state_for_each_realized_product(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Incremental planning exposes every persistent product-state decision.
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

    state_events = tuple(
        event
        for event in events
        if isinstance(
            event,
            ProductStateEvent,
        )
    )

    assert len(state_events) == _persistent_product_count(
        build_plan,
    )


def test_initial_incremental_build_reports_absent_products(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Products missing before initial execution are observed as ABSENT.
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

    state_events = tuple(
        event
        for event in events
        if isinstance(
            event,
            ProductStateEvent,
        )
    )

    assert state_events

    assert all(event.state is ProductState.ABSENT for event in state_events)


def test_unchanged_incremental_build_reports_current_products(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Reusable persistent products are observed as CURRENT.
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

    execute_incremental_build(
        build_plan,
        execute_stage=_materialize_stage_products,
        event_sink=events.append,
    )

    state_events = tuple(
        event
        for event in events
        if isinstance(
            event,
            ProductStateEvent,
        )
    )

    assert state_events

    assert all(event.state is ProductState.CURRENT for event in state_events)


def test_incremental_product_state_events_include_product_identity(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    State observations identify their realized persistent products.
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

    state_events = tuple(
        event
        for event in events
        if isinstance(
            event,
            ProductStateEvent,
        )
    )

    observed = {
        (
            event.stage_name,
            event.product_name,
        )
        for event in state_events
    }

    expected = {
        (
            stage.name,
            product.name,
        )
        for stage in build_plan.stages
        for product in stage.products
    }

    assert observed == expected

    for event in state_events:
        assert event.artifact_id == build_plan.artifact_id
        assert event.model_name == build_plan.model_name
        assert event.realization == build_plan.realization_name


# =========================================================
# Observation independence
# =========================================================


def test_product_state_observer_return_value_does_not_change_execution(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Product-state observation cannot suppress required execution.
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
        event_sink=lambda event: False,
    )

    assert tuple(
        executed,
    ) == tuple(stage.name for stage in build_plan.stages if stage.products)


# =========================================================
# Product-state event ordering
# =========================================================


def test_product_state_events_precede_stage_started_events(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Product-state decisions are observed before required stage execution.
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

    state_indexes = tuple(
        index
        for index, event in enumerate(events)
        if isinstance(
            event,
            ProductStateEvent,
        )
    )

    started_indexes = tuple(
        index
        for index, event in enumerate(events)
        if (
            isinstance(event, ExecutionEvent)
            and not isinstance(event, ProductStateEvent)
            and event.kind == "stage.started"
        )
    )

    assert state_indexes
    assert started_indexes

    assert max(state_indexes) < min(started_indexes)


def test_product_state_events_precede_stage_skipped_events(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Product-state decisions are observed before reusable stages are skipped.
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

    execute_incremental_build(
        build_plan,
        execute_stage=_materialize_stage_products,
        event_sink=events.append,
    )

    state_indexes = tuple(
        index
        for index, event in enumerate(events)
        if isinstance(
            event,
            ProductStateEvent,
        )
    )

    skipped_indexes = tuple(
        index
        for index, event in enumerate(events)
        if (
            isinstance(event, ExecutionEvent)
            and not isinstance(event, ProductStateEvent)
            and event.kind == "stage.skipped"
        )
    )

    assert state_indexes
    assert skipped_indexes

    assert max(state_indexes) < min(skipped_indexes)


def test_product_state_events_preserve_realized_product_order(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Product-state observations preserve realized stage and product order.
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

    observed = tuple(
        (
            event.stage_name,
            event.product_name,
        )
        for event in events
        if isinstance(
            event,
            ProductStateEvent,
        )
    )

    expected = tuple(
        (
            stage.name,
            product.name,
        )
        for stage in build_plan.stages
        for product in stage.products
    )

    assert observed == expected
