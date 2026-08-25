"""
Tests for concrete execution-plan representation.

An ExecutionPlan describes which stages of an already-resolved BuildPlan
must execute for the current build context.

These tests establish the representation independently of filesystem
evidence gathering, product-state evaluation, dependency invalidation,
event emission, and stage execution.
"""
# File: tests/engine/test_execution_plan.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from lowkey_artifact_builder.engine import (
    ExecutionPlan,
    PlannedStageExecution,
    ProductState,
    stage_requires_execution,
)

# =========================================================
# Helpers
# =========================================================


def _stage_execution(
    *states: ProductState,
) -> PlannedStageExecution:
    """
    Create representative execution planning for one realized stage.
    """

    return PlannedStageExecution(
        stage_name="vector",
        product_states=states,
    )


# =========================================================
# Planned stage execution
# =========================================================


def test_planned_stage_execution_carries_stage_identity() -> None:
    """
    Stage execution planning identifies the realized stage.
    """

    execution = _stage_execution(
        ProductState.CURRENT,
    )

    assert execution.stage_name == "vector"


def test_planned_stage_execution_carries_product_states() -> None:
    """
    Stage execution planning retains the evaluated product states.
    """

    execution = _stage_execution(
        ProductState.CURRENT,
        ProductState.STALE,
    )

    assert execution.product_states == (
        ProductState.CURRENT,
        ProductState.STALE,
    )


def test_planned_stage_execution_derives_execution_decision() -> None:
    """
    Execution requirement is derived from product states.
    """

    execution = _stage_execution(
        ProductState.CURRENT,
        ProductState.STALE,
    )

    assert execution.requires_execution is stage_requires_execution(
        execution.product_states,
    )


def test_all_current_products_skip_stage() -> None:
    """
    A stage whose persistent products are all current need not execute.
    """

    execution = _stage_execution(
        ProductState.CURRENT,
        ProductState.CURRENT,
    )

    assert not execution.requires_execution


@pytest.mark.parametrize(
    "state",
    (
        ProductState.ABSENT,
        ProductState.INCOMPLETE,
        ProductState.INVALID,
        ProductState.STALE,
    ),
)
def test_noncurrent_product_requires_stage_execution(
    state: ProductState,
) -> None:
    """
    Any product requiring production requires the whole stage to execute.
    """

    execution = _stage_execution(
        ProductState.CURRENT,
        state,
    )

    assert execution.requires_execution


def test_stage_without_persistent_products_requires_execution() -> None:
    """
    A realized stage without reusable persistent state must execute.
    """

    execution = _stage_execution()

    assert execution.requires_execution


def test_planned_stage_execution_is_immutable() -> None:
    """
    Execution decisions cannot change after the plan is constructed.
    """

    execution = _stage_execution(
        ProductState.CURRENT,
    )

    with pytest.raises(
        FrozenInstanceError,
    ):
        execution.stage_name = "raster"  # type: ignore[misc]


def test_planned_stage_executions_compare_by_value() -> None:
    """
    Stage execution plans support deterministic value comparison.
    """

    assert _stage_execution(
        ProductState.CURRENT,
    ) == _stage_execution(
        ProductState.CURRENT,
    )


# =========================================================
# Execution plan
# =========================================================


def test_execution_plan_carries_artifact_identity() -> None:
    """
    An execution plan identifies the artifact realization it describes.
    """

    plan = ExecutionPlan(
        artifact_id="example",
        model_name="artwork",
        realization="default",
        stages=(),
    )

    assert plan.artifact_id == "example"
    assert plan.model_name == "artwork"
    assert plan.realization == "default"


def test_execution_plan_retains_all_realized_stages() -> None:
    """
    Current stages remain visible in the execution plan even when skipped.
    """

    prepare = PlannedStageExecution(
        stage_name="prepare",
        product_states=(ProductState.CURRENT,),
    )

    raster = PlannedStageExecution(
        stage_name="raster",
        product_states=(ProductState.STALE,),
    )

    vector = PlannedStageExecution(
        stage_name="vector",
        product_states=(ProductState.CURRENT,),
    )

    plan = ExecutionPlan(
        artifact_id="example",
        model_name="artwork",
        realization="default",
        stages=(
            prepare,
            raster,
            vector,
        ),
    )

    assert plan.stages == (
        prepare,
        raster,
        vector,
    )


def test_execution_plan_preserves_stage_order() -> None:
    """
    Execution planning preserves realized stage ordering.
    """

    plan = ExecutionPlan(
        artifact_id="example",
        model_name="artwork",
        realization="default",
        stages=(
            PlannedStageExecution(
                stage_name="prepare",
                product_states=(ProductState.CURRENT,),
            ),
            PlannedStageExecution(
                stage_name="raster",
                product_states=(ProductState.STALE,),
            ),
            PlannedStageExecution(
                stage_name="vector",
                product_states=(ProductState.ABSENT,),
            ),
        ),
    )

    assert tuple(stage.stage_name for stage in plan.stages) == (
        "prepare",
        "raster",
        "vector",
    )


def test_execution_plan_exposes_stages_requiring_execution() -> None:
    """
    Execution work can be selected without losing skipped stages.
    """

    prepare = PlannedStageExecution(
        stage_name="prepare",
        product_states=(ProductState.CURRENT,),
    )

    raster = PlannedStageExecution(
        stage_name="raster",
        product_states=(ProductState.STALE,),
    )

    vector = PlannedStageExecution(
        stage_name="vector",
        product_states=(ProductState.ABSENT,),
    )

    plan = ExecutionPlan(
        artifact_id="example",
        model_name="artwork",
        realization="default",
        stages=(
            prepare,
            raster,
            vector,
        ),
    )

    assert plan.required_stages == (
        raster,
        vector,
    )


def test_execution_plan_with_all_current_products_has_no_required_stages() -> None:
    """
    A fully reusable realization may require no stage execution.
    """

    plan = ExecutionPlan(
        artifact_id="example",
        model_name="artwork",
        realization="default",
        stages=(
            PlannedStageExecution(
                stage_name="prepare",
                product_states=(ProductState.CURRENT,),
            ),
            PlannedStageExecution(
                stage_name="raster",
                product_states=(ProductState.CURRENT,),
            ),
        ),
    )

    assert plan.required_stages == ()


def test_execution_plan_is_immutable() -> None:
    """
    An execution plan is a stable description of one execution decision.
    """

    plan = ExecutionPlan(
        artifact_id="example",
        model_name="artwork",
        realization="default",
        stages=(),
    )

    with pytest.raises(
        FrozenInstanceError,
    ):
        plan.artifact_id = "other"  # type: ignore[misc]


def test_execution_plans_compare_by_value() -> None:
    """
    Execution plans support deterministic value comparison.
    """

    left = ExecutionPlan(
        artifact_id="example",
        model_name="artwork",
        realization="default",
        stages=(
            _stage_execution(
                ProductState.CURRENT,
            ),
        ),
    )

    right = ExecutionPlan(
        artifact_id="example",
        model_name="artwork",
        realization="default",
        stages=(
            _stage_execution(
                ProductState.CURRENT,
            ),
        ),
    )

    assert left == right
