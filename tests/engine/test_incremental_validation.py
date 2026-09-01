"""
Tests for configuration validation during incremental execution.

Incremental validation occurs after persistent-state-aware execution planning
has determined which stages require execution and before any required stage is
executed.

These tests exercise validation lifecycle integration for an already-realized
BuildPlan. Generic validation policy is tested separately.
"""
# File: tests/engine/test_incremental_validation.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from lowkey_artifact_builder.config import ConfigError
from lowkey_artifact_builder.engine import (
    BuildPlan,
    ExecutionPlan,
    PlannedStage,
    ProductFingerprint,
    StageCompletion,
    create_required_fingerprints,
    execute_incremental_build,
    prepare_incremental_build,
    write_stage_completion,
)

type ArtworkPlanFactory = Callable[..., BuildPlan]


# =========================================================
# Test support
# =========================================================


def _materialize_external_inputs(
    build_plan: BuildPlan,
    *,
    content: bytes = b"incremental-validation-input",
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


# =========================================================
# Incremental preparation
# =========================================================


def test_prepare_incremental_build_validates_planned_execution(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Incremental preparation validates the execution plan produced from
    current persistent state.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    _materialize_external_inputs(
        build_plan,
    )

    validated: list[ExecutionPlan] = []

    def validate_execution(
        planned_build: BuildPlan,
        execution_plan: ExecutionPlan,
    ) -> None:
        assert planned_build is build_plan

        validated.append(
            execution_plan,
        )

    monkeypatch.setattr(
        "lowkey_artifact_builder.engine.incremental.validate_execution",
        validate_execution,
    )

    execution_plan = prepare_incremental_build(
        build_plan,
    )

    assert validated == [
        execution_plan,
    ]


def test_prepare_incremental_build_validates_current_execution_scope(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Incremental preparation validates against execution scope determined
    from current persistent product state.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    _materialize_external_inputs(
        build_plan,
    )

    fingerprints = create_required_fingerprints(
        build_plan,
    )

    first_stage = build_plan.stages[0]

    _record_stage_current(
        build_plan,
        first_stage,
        fingerprints[first_stage.name],
    )

    validated_required_stages: list[tuple[str, ...]] = []

    def validate_execution(
        planned_build: BuildPlan,
        execution_plan: ExecutionPlan,
    ) -> None:
        assert planned_build is build_plan

        validated_required_stages.append(
            tuple(stage.stage_name for stage in execution_plan.required_stages)
        )

    monkeypatch.setattr(
        "lowkey_artifact_builder.engine.incremental.validate_execution",
        validate_execution,
    )

    execution_plan = prepare_incremental_build(
        build_plan,
    )

    expected_required = tuple(
        stage.name for stage in build_plan.stages if stage.name != first_stage.name
    )

    assert validated_required_stages == [
        expected_required,
    ]

    assert tuple(stage.stage_name for stage in execution_plan.required_stages) == expected_required


def test_prepare_incremental_build_propagates_validation_failure(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Invalid execution-relevant configuration prevents incremental
    preparation from succeeding.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    _materialize_external_inputs(
        build_plan,
    )

    validated: list[str] = []

    def validate_execution(
        planned_build: BuildPlan,
        execution_plan: ExecutionPlan,
    ) -> None:
        assert planned_build is build_plan
        assert execution_plan.required_stages

        validated.append(
            "validated",
        )

        raise ConfigError(
            "required configuration is invalid",
        )

    monkeypatch.setattr(
        "lowkey_artifact_builder.engine.incremental.validate_execution",
        validate_execution,
    )

    with pytest.raises(
        ConfigError,
        match="required configuration is invalid",
    ):
        prepare_incremental_build(
            build_plan,
        )

    assert validated == [
        "validated",
    ]


# =========================================================
# Incremental execution
# =========================================================


def test_incremental_build_validates_before_required_stage_execution(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Invalid execution-relevant configuration fails before any required
    stage executes.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    _materialize_external_inputs(
        build_plan,
    )

    executed: list[str] = []
    validated: list[str] = []

    def validate_execution(
        planned_build: BuildPlan,
        execution_plan: ExecutionPlan,
    ) -> None:
        assert planned_build is build_plan
        assert execution_plan.required_stages

        validated.append(
            "validated",
        )

        raise ConfigError(
            "required configuration is invalid",
        )

    monkeypatch.setattr(
        "lowkey_artifact_builder.engine.incremental.validate_execution",
        validate_execution,
    )

    def execute(
        stage: PlannedStage,
    ) -> None:
        executed.append(
            stage.name,
        )

        _materialize_stage_products(
            stage,
        )

    with pytest.raises(
        ConfigError,
        match="required configuration is invalid",
    ):
        execute_incremental_build(
            build_plan,
            execute_stage=execute,
        )

    assert validated == [
        "validated",
    ]

    assert executed == []


def test_incremental_build_validates_planned_execution_before_processing_stages(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Incremental validation receives the execution plan produced from current
    persistent state before stage processing begins.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    _materialize_external_inputs(
        build_plan,
    )

    fingerprints = create_required_fingerprints(
        build_plan,
    )

    first_stage = build_plan.stages[0]

    _record_stage_current(
        build_plan,
        first_stage,
        fingerprints[first_stage.name],
    )

    validated_required_stages: list[tuple[str, ...]] = []

    executed: list[str] = []

    def validate_execution(
        planned_build: BuildPlan,
        execution_plan: ExecutionPlan,
    ) -> None:
        assert planned_build is build_plan

        validated_required_stages.append(
            tuple(stage.stage_name for stage in execution_plan.required_stages)
        )

    monkeypatch.setattr(
        "lowkey_artifact_builder.engine.incremental.validate_execution",
        validate_execution,
    )

    def execute(
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
        execute_stage=execute,
    )

    expected_required = tuple(
        stage.name for stage in build_plan.stages if stage.name != first_stage.name
    )

    assert validated_required_stages == [
        expected_required,
    ]

    assert tuple(executed) == expected_required


def test_prepare_incremental_build_does_not_execute_stages(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Incremental preparation performs planning and validation without
    executing required stages.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    _materialize_external_inputs(
        build_plan,
    )

    monkeypatch.setattr(
        "lowkey_artifact_builder.engine.incremental.validate_execution",
        lambda planned_build, execution_plan: None,
    )

    execution_plan = prepare_incremental_build(
        build_plan,
    )

    assert execution_plan.required_stages

    for stage in build_plan.stages:
        for product in stage.products:
            assert not product.path.exists()


def test_prepare_incremental_build_does_not_persist_stage_completion(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Incremental preparation does not record successful stage completion.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    _materialize_external_inputs(
        build_plan,
    )

    persisted: list[tuple[object, object]] = []

    monkeypatch.setattr(
        "lowkey_artifact_builder.engine.incremental.write_stage_completion",
        lambda working_dir, completion: persisted.append(
            (
                working_dir,
                completion,
            )
        ),
    )

    monkeypatch.setattr(
        "lowkey_artifact_builder.engine.incremental.validate_execution",
        lambda planned_build, execution_plan: None,
    )

    execution_plan = prepare_incremental_build(
        build_plan,
    )

    assert execution_plan.required_stages
    assert persisted == []


def test_prepare_incremental_build_returns_persistent_state_execution_plan(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Incremental preparation preserves persistent-state execution decisions
    made by incremental planning.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    _materialize_external_inputs(
        build_plan,
    )

    fingerprints = create_required_fingerprints(
        build_plan,
    )

    first_stage = build_plan.stages[0]

    _record_stage_current(
        build_plan,
        first_stage,
        fingerprints[first_stage.name],
    )

    monkeypatch.setattr(
        "lowkey_artifact_builder.engine.incremental.validate_execution",
        lambda planned_build, execution_plan: None,
    )

    execution_plan = prepare_incremental_build(
        build_plan,
    )

    assert tuple(stage.stage_name for stage in execution_plan.required_stages) == tuple(
        stage.name for stage in build_plan.stages if stage.name != first_stage.name
    )
