"""
Tests for execution-plan representation and construction.

Execution plans preserve the complete ordered realized workflow while
identifying which stages require execution for the current build context.

Execution-plan construction combines a realized BuildPlan with persistent
product states supplied by an independent resolver.

These tests exercise pure execution-planning policy. They do not inspect
the filesystem, gather product evidence, calculate fingerprints, emit
execution events, construct stage contexts, or execute stages.
"""
# File: tests/engine/test_execution_plan.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from lowkey_artifact_builder.engine import (
    BuildPlan,
    ExecutionPlan,
    PlannedStage,
    PlannedStageExecution,
    ProductState,
    create_execution_plan,
)

type ArtworkPlanFactory = Callable[..., BuildPlan]


# =========================================================
# Helpers
# =========================================================


def _stage(
    *,
    name: str = "vector",
    states: tuple[ProductState, ...] = (ProductState.CURRENT,),
) -> PlannedStageExecution:
    """
    Create one representative planned stage execution.
    """

    return PlannedStageExecution(
        stage_name=name,
        product_states=states,
    )


def _execution_plan(
    *,
    stages: tuple[PlannedStageExecution, ...] = (),
) -> ExecutionPlan:
    """
    Create one representative execution plan.
    """

    return ExecutionPlan(
        artifact_id="example",
        model_name="artwork",
        realization="default",
        stages=stages,
    )


def _constant_state(
    state: ProductState,
) -> Callable[
    [
        PlannedStage,
        str,
    ],
    ProductState,
]:
    """
    Create a resolver returning one ProductState for every product.
    """

    def resolve(
        stage: PlannedStage,
        product_name: str,
    ) -> ProductState:
        del stage
        del product_name

        return state

    return resolve


# =========================================================
# Planned stage execution
# =========================================================


def test_planned_stage_execution_preserves_stage_name() -> None:
    """
    A stage execution decision preserves its realized stage identity.
    """

    stage = _stage(
        name="raster",
    )

    assert stage.stage_name == "raster"


def test_planned_stage_execution_preserves_product_states() -> None:
    """
    A stage execution decision preserves product states in order.
    """

    states = (
        ProductState.CURRENT,
        ProductState.STALE,
    )

    stage = _stage(
        states=states,
    )

    assert stage.product_states == states


def test_planned_stage_execution_is_immutable() -> None:
    """
    Stage execution decisions are immutable value objects.
    """

    stage = _stage()

    with pytest.raises(
        AttributeError,
    ):
        stage.stage_name = "changed"  # type: ignore[misc]


def test_planned_stage_execution_compares_by_value() -> None:
    """
    Equivalent stage execution decisions compare deterministically.
    """

    assert _stage() == _stage()


def test_current_stage_does_not_require_execution() -> None:
    """
    A stage whose persistent products are CURRENT may be reused.
    """

    stage = _stage(
        states=(ProductState.CURRENT,),
    )

    assert not stage.requires_execution


def test_multiple_current_products_do_not_require_execution() -> None:
    """
    A stage may be reused when every declared product is CURRENT.
    """

    stage = _stage(
        states=(
            ProductState.CURRENT,
            ProductState.CURRENT,
        ),
    )

    assert not stage.requires_execution


@pytest.mark.parametrize(
    "state",
    [
        ProductState.ABSENT,
        ProductState.INCOMPLETE,
        ProductState.INVALID,
        ProductState.STALE,
    ],
)
def test_noncurrent_product_requires_execution(
    state: ProductState,
) -> None:
    """
    Any product requiring production requires its producing stage.
    """

    stage = _stage(
        states=(state,),
    )

    assert stage.requires_execution


def test_one_noncurrent_product_requires_whole_stage() -> None:
    """
    Persistent products are rebuilt through their producing stage.
    """

    stage = _stage(
        states=(
            ProductState.CURRENT,
            ProductState.STALE,
        ),
    )

    assert stage.requires_execution


def test_stage_without_products_requires_execution() -> None:
    """
    A stage without persistent products cannot prove previous work reusable.
    """

    stage = _stage(
        states=(),
    )

    assert stage.requires_execution


# =========================================================
# Execution plan
# =========================================================


def test_execution_plan_preserves_identity() -> None:
    """
    An execution plan identifies one artifact realization.
    """

    plan = _execution_plan()

    assert plan.artifact_id == "example"
    assert plan.model_name == "artwork"
    assert plan.realization == "default"


def test_execution_plan_preserves_stage_order() -> None:
    """
    Execution plans preserve realized workflow order.
    """

    prepare = _stage(
        name="prepare",
    )
    raster = _stage(
        name="raster",
    )
    vector = _stage(
        name="vector",
    )

    plan = _execution_plan(
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


def test_execution_plan_preserves_reusable_stages() -> None:
    """
    Reusable stages remain represented in the complete execution plan.
    """

    current = _stage(
        name="prepare",
        states=(ProductState.CURRENT,),
    )

    stale = _stage(
        name="raster",
        states=(ProductState.STALE,),
    )

    plan = _execution_plan(
        stages=(
            current,
            stale,
        ),
    )

    assert plan.stages == (
        current,
        stale,
    )


def test_required_stages_returns_only_executable_stages() -> None:
    """
    required_stages filters stages that may reuse persistent products.
    """

    prepare = _stage(
        name="prepare",
        states=(ProductState.CURRENT,),
    )

    raster = _stage(
        name="raster",
        states=(ProductState.STALE,),
    )

    vector = _stage(
        name="vector",
        states=(ProductState.ABSENT,),
    )

    plan = _execution_plan(
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


def test_required_stages_preserves_order() -> None:
    """
    Filtering executable stages does not alter dependency order.
    """

    first = _stage(
        name="first",
        states=(ProductState.STALE,),
    )

    skipped = _stage(
        name="skipped",
        states=(ProductState.CURRENT,),
    )

    last = _stage(
        name="last",
        states=(ProductState.ABSENT,),
    )

    plan = _execution_plan(
        stages=(
            first,
            skipped,
            last,
        ),
    )

    assert plan.required_stages == (
        first,
        last,
    )


def test_empty_execution_plan_has_no_required_stages() -> None:
    """
    An empty realized workflow has no execution work.
    """

    plan = _execution_plan(
        stages=(),
    )

    assert plan.required_stages == ()


# =========================================================
# Execution-plan construction
# =========================================================


def test_create_execution_plan_preserves_build_identity(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Execution-plan construction preserves artifact realization identity.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    execution_plan = create_execution_plan(
        build_plan,
        product_state=_constant_state(
            ProductState.CURRENT,
        ),
    )

    assert execution_plan.artifact_id == build_plan.artifact_id
    assert execution_plan.model_name == build_plan.model_name
    assert execution_plan.realization == build_plan.realization_name


def test_create_execution_plan_preserves_stage_order(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Execution-plan construction preserves realized stage order.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    execution_plan = create_execution_plan(
        build_plan,
        product_state=_constant_state(
            ProductState.CURRENT,
        ),
    )

    assert tuple(stage.stage_name for stage in execution_plan.stages) == tuple(
        stage.name for stage in build_plan.stages
    )


def test_create_execution_plan_resolves_each_declared_product(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Every declared persistent product is resolved in realized plan order.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    calls: list[
        tuple[
            PlannedStage,
            str,
        ]
    ] = []

    def product_state(
        stage: PlannedStage,
        product_name: str,
    ) -> ProductState:
        calls.append(
            (
                stage,
                product_name,
            )
        )

        return ProductState.CURRENT

    create_execution_plan(
        build_plan,
        product_state=product_state,
    )

    expected = [
        (
            stage,
            product.name,
        )
        for stage in build_plan.stages
        for product in stage.products
    ]

    assert calls == expected


def test_create_execution_plan_preserves_product_state_order(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Product states correspond to declared products in declaration order.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    expected_states: dict[
        tuple[str, str],
        ProductState,
    ] = {}

    values = (
        ProductState.CURRENT,
        ProductState.STALE,
        ProductState.ABSENT,
        ProductState.INVALID,
        ProductState.INCOMPLETE,
    )

    index = 0

    for stage in build_plan.stages:
        for product in stage.products:
            expected_states[
                (
                    stage.name,
                    product.name,
                )
            ] = values[index % len(values)]

            index += 1

    def product_state(
        stage: PlannedStage,
        product_name: str,
    ) -> ProductState:
        return expected_states[
            (
                stage.name,
                product_name,
            )
        ]

    execution_plan = create_execution_plan(
        build_plan,
        product_state=product_state,
    )

    for planned_stage, stage in zip(
        execution_plan.stages,
        build_plan.stages,
        strict=True,
    ):
        assert planned_stage.product_states == tuple(
            expected_states[
                (
                    stage.name,
                    product.name,
                )
            ]
            for product in stage.products
        )


def test_create_execution_plan_derives_stage_execution_decisions(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Resolved product states determine whether each stage must execute.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    stale_stage_name = build_plan.stages[0].name

    def product_state(
        stage: PlannedStage,
        product_name: str,
    ) -> ProductState:
        del product_name

        if stage.name == stale_stage_name:
            return ProductState.STALE

        return ProductState.CURRENT

    execution_plan = create_execution_plan(
        build_plan,
        product_state=product_state,
    )

    assert execution_plan.stages[0].requires_execution

    for stage in execution_plan.stages[1:]:
        if stage.product_states:
            assert not stage.requires_execution
