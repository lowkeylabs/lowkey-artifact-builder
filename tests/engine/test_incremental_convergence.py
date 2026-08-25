"""
Tests for incremental build convergence.

Successful incremental execution persists sufficient product and
completion evidence for an unchanged subsequent build to reuse completed
persistent stages.

These tests exercise the closed incremental-build loop:

    plan -> execute -> persist -> re-plan

They verify convergence of persistent stage state without executing
model-specific stage implementations.
"""
# File: tests/engine/test_incremental_convergence.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from lowkey_artifact_builder.engine import (
    BuildPlan,
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
    *,
    content: bytes = b"incremental-convergence-input",
) -> None:
    """
    Materialize deterministic content for every external input.
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
            f"product:{stage.name}:{product.name}".encode(),
        )


# =========================================================
# Initial convergence
# =========================================================


def test_successful_incremental_build_converges_to_no_required_stages(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    An unchanged successful build is completely reusable afterward.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    _materialize_external_inputs(
        build_plan,
    )

    executed: list[str] = []

    def execute_stage(
        stage: PlannedStage,
    ) -> None:
        executed.append(
            stage.name,
        )

        _materialize_stage_products(
            stage,
        )

    first = execute_incremental_build(
        build_plan,
        execute_stage=execute_stage,
    )

    assert tuple(
        executed,
    ) == tuple(stage.stage_name for stage in first.required_stages)

    second = plan_incremental_execution(
        build_plan,
    )

    assert second.required_stages == ()


def test_second_incremental_build_executes_no_persistent_stages(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Re-executing an unchanged completed build performs no persistent work.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    _materialize_external_inputs(
        build_plan,
    )

    first_execution: list[str] = []

    def execute_first(
        stage: PlannedStage,
    ) -> None:
        first_execution.append(
            stage.name,
        )

        _materialize_stage_products(
            stage,
        )

    execute_incremental_build(
        build_plan,
        execute_stage=execute_first,
    )

    second_execution: list[str] = []

    def execute_second(
        stage: PlannedStage,
    ) -> None:
        second_execution.append(
            stage.name,
        )

        _materialize_stage_products(
            stage,
        )

    second = execute_incremental_build(
        build_plan,
        execute_stage=execute_second,
    )

    assert second.required_stages == ()
    assert second_execution == []


# =========================================================
# Product loss
# =========================================================


def test_removed_product_breaks_convergence(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Removing a completed product makes its producing stage non-reusable.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    _materialize_external_inputs(
        build_plan,
    )

    def execute_stage(
        stage: PlannedStage,
    ) -> None:
        _materialize_stage_products(
            stage,
        )

    execute_incremental_build(
        build_plan,
        execute_stage=execute_stage,
    )

    completed = plan_incremental_execution(
        build_plan,
    )

    assert completed.required_stages == ()

    stage = next(stage for stage in build_plan.stages if stage.products)

    product = stage.products[0]

    product.path.unlink()

    changed = plan_incremental_execution(
        build_plan,
    )

    required_names = tuple(planned.stage_name for planned in changed.required_stages)

    assert stage.name in required_names


# =========================================================
# External input invalidation
# =========================================================


def test_changed_external_input_breaks_convergence(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Changing external input content invalidates the completed realization.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    _materialize_external_inputs(
        build_plan,
        content=b"original-input",
    )

    def execute_stage(
        stage: PlannedStage,
    ) -> None:
        _materialize_stage_products(
            stage,
        )

    execute_incremental_build(
        build_plan,
        execute_stage=execute_stage,
    )

    completed = plan_incremental_execution(
        build_plan,
    )

    assert completed.required_stages == ()

    consuming_stage = next(stage for stage in build_plan.stages if stage.inputs)

    for planned_input in consuming_stage.inputs:
        planned_input.path.write_bytes(
            b"changed-input",
        )

    changed = plan_incremental_execution(
        build_plan,
    )

    required_names = tuple(stage.stage_name for stage in changed.required_stages)

    assert consuming_stage.name in required_names


def test_changed_external_input_invalidates_descendants(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Input invalidation propagates through the completed dependency chain.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    _materialize_external_inputs(
        build_plan,
        content=b"original-input",
    )

    def execute_stage(
        stage: PlannedStage,
    ) -> None:
        _materialize_stage_products(
            stage,
        )

    execute_incremental_build(
        build_plan,
        execute_stage=execute_stage,
    )

    consuming_stage = next(stage for stage in build_plan.stages if stage.inputs)

    for planned_input in consuming_stage.inputs:
        planned_input.path.write_bytes(
            b"changed-input",
        )

    execution_plan = plan_incremental_execution(
        build_plan,
    )

    required_names = {stage.stage_name for stage in execution_plan.required_stages}

    reached = {
        consuming_stage.name,
    }

    descendants: list[str] = []

    for stage in build_plan.stages:
        if any(dependency in reached for dependency in stage.spec.dependencies):
            reached.add(
                stage.name,
            )

            descendants.append(
                stage.name,
            )

    assert descendants

    assert consuming_stage.name in required_names

    for descendant in descendants:
        assert descendant in required_names


# =========================================================
# Reconvergence
# =========================================================


def test_invalidated_build_reconverges_after_successful_execution(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Successful rebuilding of invalidated stages restores full reuse.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    _materialize_external_inputs(
        build_plan,
        content=b"original-input",
    )

    def execute_stage(
        stage: PlannedStage,
    ) -> None:
        _materialize_stage_products(
            stage,
        )

    execute_incremental_build(
        build_plan,
        execute_stage=execute_stage,
    )

    initial = plan_incremental_execution(
        build_plan,
    )

    assert initial.required_stages == ()

    consuming_stage = next(stage for stage in build_plan.stages if stage.inputs)

    for planned_input in consuming_stage.inputs:
        planned_input.path.write_bytes(
            b"changed-input",
        )

    invalidated = plan_incremental_execution(
        build_plan,
    )

    assert invalidated.required_stages

    rebuilt: list[str] = []

    def rebuild_stage(
        stage: PlannedStage,
    ) -> None:
        rebuilt.append(
            stage.name,
        )

        _materialize_stage_products(
            stage,
        )

    rebuilt_plan = execute_incremental_build(
        build_plan,
        execute_stage=rebuild_stage,
    )

    assert tuple(
        rebuilt,
    ) == tuple(stage.stage_name for stage in rebuilt_plan.required_stages)

    converged = plan_incremental_execution(
        build_plan,
    )

    assert converged.required_stages == ()
