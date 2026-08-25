"""
Tests for incremental recovery from missing completion metadata.

Persistent product files alone do not establish successful stage completion.
If completion metadata is lost while the products remain materialized, the
producing stage must execute again.

Unaffected upstream work remains reusable. Successful reexecution restores
completion evidence and returns the realization to fully reusable state.

These tests exercise persistent-state-aware incremental execution of an
already-realized BuildPlan. They do not test CLI behavior or real
model-specific stage implementations.
"""
# File: tests/engine/test_incremental_missing_completion.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from lowkey_artifact_builder.engine import (
    BuildPlan,
    PlannedStage,
    completion_path,
    execute_incremental_build,
    plan_incremental_execution,
    read_stage_completion,
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
                b"missing-completion-input",
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


def _affected_stage(
    build_plan: BuildPlan,
) -> PlannedStage:
    """
    Return an interior persistent stage suitable for invalidation.
    """

    for index, stage in enumerate(
        build_plan.stages,
    ):
        if index > 0 and stage.products and index < len(build_plan.stages) - 1:
            return stage

    raise AssertionError("Build plan contains no interior persistent stage.")


def _stage_working_dir(
    stage: PlannedStage,
) -> Path:
    """
    Return the common persistent-product directory of one stage.
    """

    assert stage.products

    working_dirs = {product.path.parent for product in stage.products}

    assert len(working_dirs) == 1

    return next(
        iter(
            working_dirs,
        )
    )


def _remove_completion(
    stage: PlannedStage,
) -> Path:
    """
    Remove successful completion metadata while preserving products.
    """

    working_dir = _stage_working_dir(
        stage,
    )

    path = completion_path(
        working_dir,
    )

    assert path.is_file()

    path.unlink()

    assert not path.exists()

    for product in stage.products:
        assert product.path.is_file()

    return path


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
# Missing completion
# =========================================================


def test_missing_completion_requires_its_producer(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Products without completion metadata require producer execution.
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

    _remove_completion(
        affected,
    )

    assert _required_stage_names(
        build_plan,
    ) == (affected.name,)


def test_missing_completion_preserves_upstream_reuse(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Lost downstream completion does not invalidate upstream stages.
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

    _remove_completion(
        affected,
    )

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


def test_missing_completion_rebuild_restores_completion(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Reexecution restores successful completion metadata.
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

    completion = _remove_completion(
        affected,
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

    assert planned == (affected.name,)

    assert tuple(executed) == (affected.name,)

    assert completion.is_file()

    restored = read_stage_completion(
        _stage_working_dir(
            affected,
        ),
    )

    assert restored is not None
    assert restored.stage_name == affected.name


def test_missing_completion_recovery_reconverges(
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

    _remove_completion(
        affected,
    )

    assert _required_stage_names(
        build_plan,
    ) == (affected.name,)

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
