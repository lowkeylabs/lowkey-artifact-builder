"""
Tests for incremental recovery from invalid persistent products.

A successfully completed product may later cease to be a valid regular
file while something still occupies its expected filesystem path.

Invalid materialization cannot establish reusable persistent state.
Incremental execution must require the producing stage, preserve reusable
upstream work, recover the invalid product through stage execution, and
converge to a fully reusable realization.

These tests exercise persistent-state-aware incremental execution of an
already-realized BuildPlan. They do not test CLI behavior or real
model-specific stage implementations.
"""
# File: tests/engine/test_incremental_invalid_product.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import shutil
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
                b"invalid-product-input",
            )


def _materialize_stage_products(
    stage: PlannedStage,
) -> None:
    """
    Materialize every declared persistent product as a regular file.

    Existing invalid materializations are removed before the successful
    replacement is written.
    """

    for product in stage.products:
        if product.path.is_dir():
            shutil.rmtree(
                product.path,
            )
        elif product.path.exists():
            product.path.unlink()

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
    """

    for index, stage in enumerate(
        build_plan.stages,
    ):
        if index > 0 and stage.products and index < len(build_plan.stages) - 1:
            return stage

    raise AssertionError("Build plan contains no interior persistent stage.")


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


def _replace_product_with_directory(
    stage: PlannedStage,
) -> Path:
    """
    Replace one completed regular-file product with a directory.

    The expected path therefore continues to exist but no longer
    represents a valid persistent product.
    """

    assert stage.products

    path = stage.products[0].path

    assert path.is_file()

    path.unlink()

    path.mkdir()

    assert path.exists()
    assert not path.is_file()

    return path


# =========================================================
# Invalid persistent product
# =========================================================


def test_invalid_completed_product_requires_its_producer(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Existing but invalid materialization requires producer execution.
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

    _replace_product_with_directory(
        affected,
    )

    assert _required_stage_names(
        build_plan,
    ) == (affected.name,)


def test_invalid_completed_product_preserves_upstream_reuse(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Invalid downstream materialization does not invalidate upstream work.
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

    _replace_product_with_directory(
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


def test_invalid_completed_product_is_replaced_by_rebuild(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Reexecution replaces invalid materialization with a valid product.
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

    path = _replace_product_with_directory(
        affected,
    )

    required_before = _required_stage_names(
        build_plan,
    )

    assert required_before == (affected.name,)

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

    assert path.is_file()


def test_invalid_completed_product_recovery_reconverges(
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

    _replace_product_with_directory(
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
