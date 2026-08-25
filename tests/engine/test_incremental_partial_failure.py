"""
Tests for incremental recovery from partially materialized failed stages.

A stage may materialize some or all of its declared products before
execution fails. Product materialization alone does not establish successful
completion.

A subsequent incremental build must therefore reexecute the failed stage,
reuse successfully completed upstream stages, execute required descendants,
and converge after successful recovery.

These tests exercise restart semantics for an already-realized BuildPlan.
They do not test CLI behavior or real model-specific stage implementations.
"""
# File: tests/engine/test_incremental_partial_failure.py
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
                b"partial-failure-input",
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


def _materialize_first_stage_product(
    stage: PlannedStage,
) -> None:
    """
    Materialize only the first persistent product of one stage.
    """

    assert stage.products

    product = stage.products[0]

    product.path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    product.path.write_bytes(
        b"partial-product",
    )


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


def _persistent_stages(
    build_plan: BuildPlan,
) -> tuple[PlannedStage, ...]:
    """
    Return realized stages declaring persistent products.
    """

    return tuple(stage for stage in build_plan.stages if stage.products)


def _failure_stage(
    build_plan: BuildPlan,
) -> PlannedStage:
    """
    Return a persistent stage with completed upstream work and descendants.
    """

    persistent = _persistent_stages(
        build_plan,
    )

    assert len(persistent) >= 3

    return persistent[1]


def _unfinished_suffix(
    build_plan: BuildPlan,
    stage: PlannedStage,
) -> tuple[str, ...]:
    """
    Return the realized suffix beginning with stage.
    """

    index = build_plan.stages.index(
        stage,
    )

    return tuple(candidate.name for candidate in build_plan.stages[index:])


# =========================================================
# Partial failure
# =========================================================


def test_failed_stage_products_without_completion_are_not_reusable(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Materialized outputs from a failed stage do not establish completion.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    _materialize_external_inputs(
        build_plan,
    )

    failing_stage = _failure_stage(
        build_plan,
    )

    class ExpectedError(Exception):
        """
        Expected execution failure.
        """

    def execute(
        stage: PlannedStage,
    ) -> None:
        if stage.name == failing_stage.name:
            _materialize_stage_products(
                stage,
            )

            raise ExpectedError

        _materialize_stage_products(
            stage,
        )

    with pytest.raises(
        ExpectedError,
    ):
        execute_incremental_build(
            build_plan,
            execute_stage=execute,
        )

    assert all(product.path.is_file() for product in failing_stage.products)

    assert (
        read_stage_completion(
            _stage_working_dir(
                failing_stage,
            ),
        )
        is None
    )

    required = _required_stage_names(
        build_plan,
    )

    assert failing_stage.name in required


def test_partial_failed_stage_requires_restart_from_failure(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    A partially materialized failed stage and its suffix require execution.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    _materialize_external_inputs(
        build_plan,
    )

    failing_stage = _failure_stage(
        build_plan,
    )

    class ExpectedError(Exception):
        """
        Expected execution failure.
        """

    def execute(
        stage: PlannedStage,
    ) -> None:
        if stage.name == failing_stage.name:
            _materialize_first_stage_product(
                stage,
            )

            raise ExpectedError

        _materialize_stage_products(
            stage,
        )

    with pytest.raises(
        ExpectedError,
    ):
        execute_incremental_build(
            build_plan,
            execute_stage=execute,
        )

    assert _required_stage_names(
        build_plan,
    ) == _unfinished_suffix(
        build_plan,
        failing_stage,
    )


def test_restart_reexecutes_stage_with_failed_materialization(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Restart overwrites failed-stage materialization through reexecution.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    _materialize_external_inputs(
        build_plan,
    )

    failing_stage = _failure_stage(
        build_plan,
    )

    class ExpectedError(Exception):
        """
        Expected execution failure.
        """

    def fail(
        stage: PlannedStage,
    ) -> None:
        if stage.name == failing_stage.name:
            _materialize_stage_products(
                stage,
            )

            raise ExpectedError

        _materialize_stage_products(
            stage,
        )

    with pytest.raises(
        ExpectedError,
    ):
        execute_incremental_build(
            build_plan,
            execute_stage=fail,
        )

    executed: list[str] = []

    def recover(
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
        execute_stage=recover,
    )

    assert tuple(
        executed,
    ) == _unfinished_suffix(
        build_plan,
        failing_stage,
    )


# =========================================================
# Recovery convergence
# =========================================================


def test_partial_failure_recovery_reconverges(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Successful recovery makes the realization fully reusable again.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    _materialize_external_inputs(
        build_plan,
    )

    failing_stage = _failure_stage(
        build_plan,
    )

    class ExpectedError(Exception):
        """
        Expected execution failure.
        """

    def fail(
        stage: PlannedStage,
    ) -> None:
        if stage.name == failing_stage.name:
            _materialize_stage_products(
                stage,
            )

            raise ExpectedError

        _materialize_stage_products(
            stage,
        )

    with pytest.raises(
        ExpectedError,
    ):
        execute_incremental_build(
            build_plan,
            execute_stage=fail,
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
