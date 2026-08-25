"""
Tests for incremental recovery from missing persistent products.

A successful stage may later lose one of its persistent products while its
completion metadata remains present.

The missing materialization invalidates the producing stage. Dependent
descendants must also execute because their required provenance depends on
that stage, while unaffected upstream stages remain reusable.

Successful rebuilding restores a fully reusable realization.

These tests exercise persistent-state-aware incremental execution of an
already-realized BuildPlan. They do not test CLI behavior or real
model-specific stage implementations.
"""
# File: tests/engine/test_incremental_missing_product.py
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
                b"missing-product-input",
            )


def _materialize_stage_products(
    stage: PlannedStage,
) -> None:
    """
    Materialize every declared persistent product of one stage.
    """

    for product in stage.products:
        product.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        product.path.write_bytes(
            b"persistent-product",
        )


def _build_current(
    build_plan: BuildPlan,
) -> None:
    """
    Execute the realization and establish current persistent state.
    """

    execute_incremental_build(
        build_plan,
        execute_stage=_materialize_stage_products,
    )

    assert (
        _required_stage_names(
            build_plan,
        )
        == ()
    )


def _required_stage_names(
    build_plan: BuildPlan,
) -> tuple[str, ...]:
    """
    Return stages currently requiring incremental execution.
    """

    execution_plan = plan_incremental_execution(
        build_plan,
    )

    return tuple(execution.stage_name for execution in execution_plan.required_stages)


def _affected_stage(
    build_plan: BuildPlan,
) -> PlannedStage:
    """
    Return an interior persistent stage suitable for invalidation.

    The selected stage must have both realized upstream work and at least
    one realized descendant.
    """

    for index, stage in enumerate(
        build_plan.stages,
    ):
        if index > 0 and stage.products and index < len(build_plan.stages) - 1:
            return stage

    raise AssertionError("Build plan contains no interior persistent stage.")


def _descendant_stage_names(
    build_plan: BuildPlan,
    stage_name: str,
) -> tuple[str, ...]:
    """
    Return realized stages transitively depending on stage_name.
    """

    descendants: list[str] = []

    reached = {
        stage_name,
    }

    for stage in build_plan.stages:
        if any(dependency in reached for dependency in stage.spec.dependencies):
            reached.add(
                stage.name,
            )

            descendants.append(
                stage.name,
            )

    return tuple(
        descendants,
    )


def _upstream_stage_names(
    build_plan: BuildPlan,
    stage: PlannedStage,
) -> tuple[str, ...]:
    """
    Return realized stages preceding stage in build order.
    """

    index = build_plan.stages.index(
        stage,
    )

    return tuple(candidate.name for candidate in build_plan.stages[:index])


# =========================================================
# Missing persistent product
# =========================================================


def test_missing_completed_product_requires_its_producer(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Lost persistent materialization initially requires its producer.

    Existing descendants remain reusable during the initial planning
    snapshot because their persisted products and completion provenance
    are still intact.

    Rebuilding the missing producer may subsequently invalidate dependent
    stages when their required upstream provenance changes.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    _materialize_external_inputs(
        build_plan,
    )

    _build_current(
        build_plan,
    )

    affected = _affected_stage(
        build_plan,
    )

    affected.products[0].path.unlink()

    required = _required_stage_names(
        build_plan,
    )

    assert required == (affected.name,)


def test_missing_completed_product_preserves_upstream_reuse(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Missing downstream materialization does not invalidate upstream stages.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    _materialize_external_inputs(
        build_plan,
    )

    _build_current(
        build_plan,
    )

    affected = _affected_stage(
        build_plan,
    )

    upstream = _upstream_stage_names(
        build_plan,
        affected,
    )

    assert upstream

    affected.products[0].path.unlink()

    required = set(
        _required_stage_names(
            build_plan,
        )
    )

    for stage_name in upstream:
        assert stage_name not in required


# =========================================================
# Recovery
# =========================================================


def test_missing_completed_product_rebuild_executes_invalidated_chain(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Recovery executes exactly the producer and its invalidated descendants.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    _materialize_external_inputs(
        build_plan,
    )

    _build_current(
        build_plan,
    )

    affected = _affected_stage(
        build_plan,
    )

    affected.products[0].path.unlink()

    required_before = _required_stage_names(
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

    execution_plan = execute_incremental_build(
        build_plan,
        execute_stage=execute,
    )

    planned = tuple(execution.stage_name for execution in execution_plan.required_stages)

    assert planned == required_before
    assert tuple(executed) == required_before


def test_missing_completed_product_recovery_reconverges(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Successful recovery restores complete persistent reuse.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    _materialize_external_inputs(
        build_plan,
    )

    _build_current(
        build_plan,
    )

    affected = _affected_stage(
        build_plan,
    )

    affected.products[0].path.unlink()

    assert _required_stage_names(
        build_plan,
    )

    execute_incremental_build(
        build_plan,
        execute_stage=_materialize_stage_products,
    )

    assert (
        _required_stage_names(
            build_plan,
        )
        == ()
    )

    executed_again: list[str] = []

    execute_incremental_build(
        build_plan,
        execute_stage=lambda stage: executed_again.append(
            stage.name,
        ),
    )

    assert executed_again == []
