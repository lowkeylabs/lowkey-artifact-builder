"""
Tests for restart after interrupted incremental execution.

A failed incremental build may leave successfully completed upstream stages
persisted while the failing stage and later stages remain incomplete.

A subsequent incremental build must reuse those successfully completed
upstream stages, resume execution at the failed stage, execute the remaining
required stages in build order, and converge to a fully reusable realization.

These tests exercise restart semantics for an already-realized BuildPlan.
They do not test CLI behavior or real model-specific stage implementations.
"""
# File: tests/engine/test_incremental_restart.py
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
                b"incremental-restart-input",
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


# =========================================================
# Interrupted execution
# =========================================================


def test_interrupted_build_preserves_successful_upstream_completion(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Successful stages preceding a failure retain completion metadata.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    _materialize_external_inputs(
        build_plan,
    )

    persistent = _persistent_stages(
        build_plan,
    )

    assert len(persistent) >= 3

    failing_stage = persistent[1]

    class ExpectedError(Exception):
        """
        Expected interruption.
        """

    def execute(
        stage: PlannedStage,
    ) -> None:
        if stage.name == failing_stage.name:
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

    failing_index = build_plan.stages.index(
        failing_stage,
    )

    upstream = build_plan.stages[:failing_index]

    assert upstream

    for stage in upstream:
        if not stage.products:
            continue

        completion = read_stage_completion(
            _stage_working_dir(
                stage,
            ),
        )

        assert completion is not None
        assert completion.stage_name == stage.name

    assert (
        read_stage_completion(
            _stage_working_dir(
                failing_stage,
            ),
        )
        is None
    )


def test_restart_requires_failed_stage_and_remaining_stages(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Restart reuses completed upstream work and resumes at the failure.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    _materialize_external_inputs(
        build_plan,
    )

    persistent = _persistent_stages(
        build_plan,
    )

    assert len(persistent) >= 3

    failing_stage = persistent[1]

    class ExpectedError(Exception):
        """
        Expected interruption.
        """

    def fail_once(
        stage: PlannedStage,
    ) -> None:
        if stage.name == failing_stage.name:
            raise ExpectedError

        _materialize_stage_products(
            stage,
        )

    with pytest.raises(
        ExpectedError,
    ):
        execute_incremental_build(
            build_plan,
            execute_stage=fail_once,
        )

    required = _required_stage_names(
        build_plan,
    )

    failing_index = build_plan.stages.index(
        failing_stage,
    )

    expected = tuple(stage.name for stage in build_plan.stages[failing_index:])

    assert required == expected


# =========================================================
# Restart execution
# =========================================================


def test_restart_executes_only_unfinished_suffix(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Restart executes the failed stage and later required stages only.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    _materialize_external_inputs(
        build_plan,
    )

    persistent = _persistent_stages(
        build_plan,
    )

    assert len(persistent) >= 3

    failing_stage = persistent[1]

    class ExpectedError(Exception):
        """
        Expected interruption.
        """

    def fail_once(
        stage: PlannedStage,
    ) -> None:
        if stage.name == failing_stage.name:
            raise ExpectedError

        _materialize_stage_products(
            stage,
        )

    with pytest.raises(
        ExpectedError,
    ):
        execute_incremental_build(
            build_plan,
            execute_stage=fail_once,
        )

    required_before_restart = _required_stage_names(
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

    assert planned == required_before_restart
    assert tuple(executed) == required_before_restart


def test_successful_restart_reconverges(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Successful restart restores a fully reusable realization.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    _materialize_external_inputs(
        build_plan,
    )

    persistent = _persistent_stages(
        build_plan,
    )

    assert len(persistent) >= 3

    failing_stage = persistent[1]

    class ExpectedError(Exception):
        """
        Expected interruption.
        """

    def fail_once(
        stage: PlannedStage,
    ) -> None:
        if stage.name == failing_stage.name:
            raise ExpectedError

        _materialize_stage_products(
            stage,
        )

    with pytest.raises(
        ExpectedError,
    ):
        execute_incremental_build(
            build_plan,
            execute_stage=fail_once,
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
