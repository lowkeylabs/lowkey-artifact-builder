"""
Tests for incremental execution through engine stage dispatch.

Incremental artifact execution connects persistent-state-aware build
selection to the established planned StageContext and execute_stage
boundaries.

Only stages requiring execution are dispatched. Each dispatched stage
receives a StageContext adapted directly from the same BuildPlan and
PlannedStage used for incremental planning.

These tests exercise orchestration between incremental execution and
engine stage dispatch. They do not execute model-specific stage
implementations.
"""
# File: tests/engine/test_incremental_dispatch.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

import lowkey_artifact_builder.engine.incremental as incremental_module
from lowkey_artifact_builder.engine import (
    BuildPlan,
    PlannedStage,
    ProductFingerprint,
    StageCompletion,
    StageContext,
    create_required_fingerprints,
    execute_incremental_artifact_build,
    write_stage_completion,
)

type ArtworkPlanFactory = Callable[..., BuildPlan]


# =========================================================
# Helpers
# =========================================================


def _materialize_external_inputs(
    build_plan: BuildPlan,
    *,
    content: bytes = b"incremental-dispatch-input",
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
                content,
            )


def _stage_working_dir(
    stage: PlannedStage,
) -> Path:
    """
    Return the realized working directory of one persistent stage.
    """

    if not stage.products:
        raise AssertionError(f"Stage {stage.name!r} declares no persistent products.")

    working_dirs = {product.path.parent for product in stage.products}

    if len(working_dirs) != 1:
        raise AssertionError(f"Stage {stage.name!r} products do not share one working directory.")

    return next(
        iter(
            working_dirs,
        )
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


def _record_stage_current(
    build_plan: BuildPlan,
    stage: PlannedStage,
    fingerprint: ProductFingerprint,
) -> None:
    """
    Materialize one stage and record current completion metadata.
    """

    _materialize_stage_products(
        stage,
    )

    write_stage_completion(
        _stage_working_dir(
            stage,
        ),
        StageCompletion(
            artifact_id=build_plan.artifact_id,
            model_name=build_plan.model_name,
            realization=build_plan.realization_name,
            stage_name=stage.name,
            products=tuple(product.name for product in stage.products),
            fingerprint=fingerprint,
        ),
    )


def _record_all_stages_current(
    build_plan: BuildPlan,
) -> None:
    """
    Record every persistent stage as current.
    """

    fingerprints = create_required_fingerprints(
        build_plan,
    )

    for stage in build_plan.stages:
        if not stage.products:
            continue

        _record_stage_current(
            build_plan,
            stage,
            fingerprints[stage.name],
        )


def _stage_by_name(
    build_plan: BuildPlan,
    stage_name: str,
) -> PlannedStage:
    """
    Return one realized stage by name.
    """

    return next(stage for stage in build_plan.stages if stage.name == stage_name)


# =========================================================
# Dispatch
# =========================================================


def test_incremental_artifact_build_dispatches_all_absent_stages(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Every stage is dispatched when no persistent products are reusable.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    _materialize_external_inputs(
        build_plan,
    )

    dispatched: list[str] = []

    def dispatch(
        context: StageContext,
    ) -> None:
        dispatched.append(
            context.stage_name,
        )

        stage = _stage_by_name(
            build_plan,
            context.stage_name,
        )

        _materialize_stage_products(
            stage,
        )

    monkeypatch.setattr(
        incremental_module,
        "execute_stage",
        dispatch,
    )

    execute_incremental_artifact_build(
        build_plan,
    )

    assert tuple(
        dispatched,
    ) == tuple(stage.name for stage in build_plan.stages)


def test_incremental_artifact_build_dispatches_in_build_order(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Engine dispatch preserves realized build-plan order.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    _materialize_external_inputs(
        build_plan,
    )

    dispatched: list[str] = []

    def dispatch(
        context: StageContext,
    ) -> None:
        dispatched.append(
            context.stage_name,
        )

        stage = _stage_by_name(
            build_plan,
            context.stage_name,
        )

        _materialize_stage_products(
            stage,
        )

    monkeypatch.setattr(
        incremental_module,
        "execute_stage",
        dispatch,
    )

    execute_incremental_artifact_build(
        build_plan,
    )

    assert tuple(
        dispatched,
    ) == tuple(stage.name for stage in build_plan.stages)


# =========================================================
# Planned context construction
# =========================================================


def test_incremental_artifact_build_creates_context_for_required_stages(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Every required stage is adapted from the supplied BuildPlan.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    _materialize_external_inputs(
        build_plan,
    )

    requested: list[
        tuple[
            BuildPlan,
            PlannedStage,
        ]
    ] = []

    real_create_planned_stage_context = incremental_module.create_planned_stage_context

    def create_context(
        plan: BuildPlan,
        stage: PlannedStage,
    ) -> StageContext:
        requested.append(
            (
                plan,
                stage,
            )
        )

        return real_create_planned_stage_context(
            plan,
            stage,
        )

    def dispatch(
        context: StageContext,
    ) -> None:
        stage = _stage_by_name(
            build_plan,
            context.stage_name,
        )

        _materialize_stage_products(
            stage,
        )

    monkeypatch.setattr(
        incremental_module,
        "create_planned_stage_context",
        create_context,
    )

    monkeypatch.setattr(
        incremental_module,
        "execute_stage",
        dispatch,
    )

    execute_incremental_artifact_build(
        build_plan,
    )

    assert tuple(stage.name for _, stage in requested) == tuple(
        stage.name for stage in build_plan.stages
    )

    assert all(plan is build_plan for plan, _ in requested)

    assert all(
        requested_stage is planned_stage
        for (_, requested_stage), planned_stage in zip(
            requested,
            build_plan.stages,
            strict=True,
        )
    )


# =========================================================
# Current realization
# =========================================================


def test_incremental_artifact_build_does_not_dispatch_current_stages(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    A fully reusable realization reaches neither context nor dispatch.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    _materialize_external_inputs(
        build_plan,
    )

    _record_all_stages_current(
        build_plan,
    )

    context_calls: list[str] = []
    dispatch_calls: list[str] = []

    real_create_planned_stage_context = incremental_module.create_planned_stage_context

    def create_context(
        plan: BuildPlan,
        stage: PlannedStage,
    ) -> StageContext:
        context_calls.append(
            stage.name,
        )

        return real_create_planned_stage_context(
            plan,
            stage,
        )

    def dispatch(
        context: StageContext,
    ) -> None:
        dispatch_calls.append(
            context.stage_name,
        )

    monkeypatch.setattr(
        incremental_module,
        "create_planned_stage_context",
        create_context,
    )

    monkeypatch.setattr(
        incremental_module,
        "execute_stage",
        dispatch,
    )

    execute_incremental_artifact_build(
        build_plan,
    )

    assert context_calls == []
    assert dispatch_calls == []


# =========================================================
# Selective dispatch
# =========================================================


def test_incremental_artifact_build_dispatches_only_invalidated_chain(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Changed external provenance dispatches only invalidated stages.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    _materialize_external_inputs(
        build_plan,
        content=b"original-input",
    )

    _record_all_stages_current(
        build_plan,
    )

    consuming_stage = next(stage for stage in build_plan.stages if stage.inputs)

    for planned_input in consuming_stage.inputs:
        planned_input.path.write_bytes(
            b"changed-input",
        )

    dispatched: list[str] = []

    def dispatch(
        context: StageContext,
    ) -> None:
        dispatched.append(
            context.stage_name,
        )

        stage = _stage_by_name(
            build_plan,
            context.stage_name,
        )

        _materialize_stage_products(
            stage,
        )

    monkeypatch.setattr(
        incremental_module,
        "execute_stage",
        dispatch,
    )

    execution_plan = execute_incremental_artifact_build(
        build_plan,
    )

    assert tuple(
        dispatched,
    ) == tuple(stage.stage_name for stage in execution_plan.required_stages)


# =========================================================
# Failure propagation
# =========================================================


def test_dispatch_failure_propagates(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Failure from the established stage-dispatch boundary propagates.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    _materialize_external_inputs(
        build_plan,
    )

    failing_stage = build_plan.stages[0]

    class ExpectedError(Exception):
        """
        Expected dispatch failure.
        """

    def dispatch(
        context: StageContext,
    ) -> None:
        if context.stage_name == failing_stage.name:
            raise ExpectedError

        stage = _stage_by_name(
            build_plan,
            context.stage_name,
        )

        _materialize_stage_products(
            stage,
        )

    monkeypatch.setattr(
        incremental_module,
        "execute_stage",
        dispatch,
    )

    with pytest.raises(
        ExpectedError,
    ):
        execute_incremental_artifact_build(
            build_plan,
        )


def test_dispatch_failure_stops_later_context_creation(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    No later stage is adapted or dispatched after stage failure.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    _materialize_external_inputs(
        build_plan,
    )

    failing_stage = build_plan.stages[0]

    requested: list[str] = []

    real_create_planned_stage_context = incremental_module.create_planned_stage_context

    def create_context(
        plan: BuildPlan,
        stage: PlannedStage,
    ) -> StageContext:
        requested.append(
            stage.name,
        )

        return real_create_planned_stage_context(
            plan,
            stage,
        )

    class ExpectedError(Exception):
        """
        Expected dispatch failure.
        """

    def dispatch(
        context: StageContext,
    ) -> None:
        if context.stage_name == failing_stage.name:
            raise ExpectedError

    monkeypatch.setattr(
        incremental_module,
        "create_planned_stage_context",
        create_context,
    )

    monkeypatch.setattr(
        incremental_module,
        "execute_stage",
        dispatch,
    )

    with pytest.raises(
        ExpectedError,
    ):
        execute_incremental_artifact_build(
            build_plan,
        )

    assert requested == [
        failing_stage.name,
    ]
