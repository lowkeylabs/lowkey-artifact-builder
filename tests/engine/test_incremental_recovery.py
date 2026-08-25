"""
Tests for incremental build failure recovery.

Incremental execution persists successful completion one stage at a time.
A failure therefore preserves reusable work completed before the failure
without falsely completing the failed stage or any later stage.

A subsequent incremental build resumes from the failed portion of the
realized workflow and successful recovery converges to a fully reusable
build.

These tests exercise persistent incremental recovery without executing
model-specific stage implementations.
"""
# File: tests/engine/test_incremental_recovery.py
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
    *,
    content: bytes = b"incremental-recovery-input",
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


def _stage_working_dir(
    stage: PlannedStage,
) -> Path:
    """
    Return the common persistent-product directory for one stage.
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


def _persistent_stages(
    build_plan: BuildPlan,
) -> tuple[PlannedStage, ...]:
    """
    Return realized stages having persistent products.
    """

    return tuple(stage for stage in build_plan.stages if stage.products)


def _required_stage_names(
    build_plan: BuildPlan,
) -> tuple[str, ...]:
    """
    Return stage names currently requiring incremental execution.
    """

    execution_plan = plan_incremental_execution(
        build_plan,
    )

    return tuple(stage.stage_name for stage in execution_plan.required_stages)


# =========================================================
# Failure persistence
# =========================================================


def test_failed_stage_receives_no_successful_completion(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    A failed stage is not persisted as successfully completed.
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

    assert len(persistent) >= 2

    failing_stage = persistent[1]

    class ExpectedError(Exception):
        """
        Expected execution failure.
        """

    def execute_stage(
        stage: PlannedStage,
    ) -> None:
        if stage is failing_stage:
            raise ExpectedError

        _materialize_stage_products(
            stage,
        )

    with pytest.raises(
        ExpectedError,
    ):
        execute_incremental_build(
            build_plan,
            execute_stage=execute_stage,
        )

    completion = read_stage_completion(
        _stage_working_dir(
            failing_stage,
        )
    )

    assert completion is None


def test_successful_prefix_is_persisted_before_failure(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Successful persistent stages before failure remain completed.
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

    assert len(persistent) >= 2

    failing_stage = persistent[1]
    successful_stage = persistent[0]

    class ExpectedError(Exception):
        """
        Expected execution failure.
        """

    def execute_stage(
        stage: PlannedStage,
    ) -> None:
        if stage is failing_stage:
            raise ExpectedError

        _materialize_stage_products(
            stage,
        )

    with pytest.raises(
        ExpectedError,
    ):
        execute_incremental_build(
            build_plan,
            execute_stage=execute_stage,
        )

    completion = read_stage_completion(
        _stage_working_dir(
            successful_stage,
        )
    )

    assert completion is not None
    assert completion.stage_name == successful_stage.name


def test_stages_after_failure_receive_no_completion(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Persistent stages after a failure are never marked completed.
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
    later_stages = persistent[2:]

    class ExpectedError(Exception):
        """
        Expected execution failure.
        """

    def execute_stage(
        stage: PlannedStage,
    ) -> None:
        if stage is failing_stage:
            raise ExpectedError

        _materialize_stage_products(
            stage,
        )

    with pytest.raises(
        ExpectedError,
    ):
        execute_incremental_build(
            build_plan,
            execute_stage=execute_stage,
        )

    for stage in later_stages:
        completion = read_stage_completion(
            _stage_working_dir(
                stage,
            )
        )

        assert completion is None


# =========================================================
# Replanning after failure
# =========================================================


def test_replanning_after_failure_reuses_successful_prefix(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Replanning does not rebuild successfully completed prefix stages.
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

    assert len(persistent) >= 2

    successful_stage = persistent[0]
    failing_stage = persistent[1]

    class ExpectedError(Exception):
        """
        Expected execution failure.
        """

    def execute_stage(
        stage: PlannedStage,
    ) -> None:
        if stage is failing_stage:
            raise ExpectedError

        _materialize_stage_products(
            stage,
        )

    with pytest.raises(
        ExpectedError,
    ):
        execute_incremental_build(
            build_plan,
            execute_stage=execute_stage,
        )

    required = _required_stage_names(
        build_plan,
    )

    assert successful_stage.name not in required
    assert failing_stage.name in required


def test_replanning_after_failure_requires_unfinished_suffix(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    The failed stage and unfinished downstream stages remain required.
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
        Expected execution failure.
        """

    def execute_stage(
        stage: PlannedStage,
    ) -> None:
        if stage is failing_stage:
            raise ExpectedError

        _materialize_stage_products(
            stage,
        )

    with pytest.raises(
        ExpectedError,
    ):
        execute_incremental_build(
            build_plan,
            execute_stage=execute_stage,
        )

    required = _required_stage_names(
        build_plan,
    )

    failure_index = build_plan.stages.index(
        failing_stage,
    )

    expected_suffix = tuple(stage.name for stage in build_plan.stages[failure_index:])

    assert required == expected_suffix


# =========================================================
# Recovery
# =========================================================


def test_retry_resumes_at_failed_stage(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Successful retry begins with the previously failed stage.
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

    assert len(persistent) >= 2

    successful_stage = persistent[0]
    failing_stage = persistent[1]

    class ExpectedError(Exception):
        """
        Expected execution failure.
        """

    def fail_once(
        stage: PlannedStage,
    ) -> None:
        if stage is failing_stage:
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

    retried: list[str] = []

    def retry(
        stage: PlannedStage,
    ) -> None:
        retried.append(
            stage.name,
        )

        _materialize_stage_products(
            stage,
        )

    execution_plan = execute_incremental_build(
        build_plan,
        execute_stage=retry,
    )

    assert retried
    assert retried[0] == failing_stage.name
    assert successful_stage.name not in retried

    assert tuple(
        retried,
    ) == tuple(stage.stage_name for stage in execution_plan.required_stages)


def test_successful_retry_reconverges(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Successful recovery restores a fully reusable realization.
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

    assert len(persistent) >= 2

    failing_stage = persistent[1]

    class ExpectedError(Exception):
        """
        Expected execution failure.
        """

    def fail_once(
        stage: PlannedStage,
    ) -> None:
        if stage is failing_stage:
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

    assert _required_stage_names(
        build_plan,
    )

    def retry(
        stage: PlannedStage,
    ) -> None:
        _materialize_stage_products(
            stage,
        )

    execute_incremental_build(
        build_plan,
        execute_stage=retry,
    )

    assert (
        _required_stage_names(
            build_plan,
        )
        == ()
    )
