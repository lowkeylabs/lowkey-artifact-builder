"""
Tests for execution-scoped configuration validation.

Configuration validation follows required execution rather than the complete
realized build plan.

These tests establish the engine-level boundary that determines which resolved
configuration participates in validation. Model-specific validation policy is
tested separately.
"""
# File: tests/engine/test_validation.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path

from lowkey_artifact_builder.engine import (
    BuildPlan,
    ExecutionPlan,
    PlannedProduct,
    PlannedStage,
    PlannedStageExecution,
    ProductState,
)
from lowkey_artifact_builder.engine.validation import (
    required_configuration_parameters,
)
from lowkey_artifact_builder.model import (
    ModelSpec,
    ProductSpec,
    StageSpec,
)

# =========================================================
# Test support
# =========================================================


def _planned_stage(
    *,
    stage_id: int,
    name: str,
    parameters: tuple[str, ...] = (),
) -> PlannedStage:
    """
    Create one representative planned stage.
    """

    product_spec = ProductSpec(
        name="artifact",
        path="artifact.dat",
    )

    stage_spec = StageSpec(
        id=stage_id,
        name=name,
        parameters=parameters,
        products=(product_spec,),
    )

    return PlannedStage(
        spec=stage_spec,
        inputs=(),
        products=(
            PlannedProduct(
                spec=product_spec,
                path=Path(
                    f"/project/artifacts/example/"
                    f"example-model/default/"
                    f"{stage_id:02d}-{name}/artifact.dat"
                ),
            ),
        ),
    )


def _build_plan(
    *,
    stages: tuple[PlannedStage, ...],
) -> BuildPlan:
    """
    Create one representative realized build plan.
    """

    return BuildPlan(
        artifact_id="example",
        model=ModelSpec(
            name="example-model",
            title="Example Model",
        ),
        realization_name="default",
        resolver=None,  # type: ignore[arg-type]
        project_root=Path("/project"),
        artifact_dir=Path("/project/artifacts/example"),
        stages=stages,
    )


def _stage_execution(
    *,
    name: str,
    state: ProductState,
) -> PlannedStageExecution:
    """
    Create one execution decision for a persistent stage product.
    """

    return PlannedStageExecution(
        stage_name=name,
        product_states=(state,),
    )


def _execution_plan(
    *,
    stages: tuple[PlannedStageExecution, ...],
) -> ExecutionPlan:
    """
    Create one representative execution plan.
    """

    return ExecutionPlan(
        artifact_id="example",
        model_name="example-model",
        realization="default",
        stages=stages,
    )


# =========================================================
# Required configuration
# =========================================================


def test_required_configuration_includes_executing_stage_parameters() -> None:
    """
    Configuration consumed by a stage requiring execution participates
    in execution-scoped validation.
    """

    prepare = _planned_stage(
        stage_id=10,
        name="prepare",
        parameters=(
            "palette",
            "fill_color",
        ),
    )

    build_plan = _build_plan(
        stages=(prepare,),
    )

    execution_plan = _execution_plan(
        stages=(
            _stage_execution(
                name="prepare",
                state=ProductState.ABSENT,
            ),
        ),
    )

    parameters = required_configuration_parameters(
        build_plan,
        execution_plan,
    )

    assert parameters == (
        "palette",
        "fill_color",
    )


def test_required_configuration_excludes_current_stage_parameters() -> None:
    """
    Configuration consumed only by an already-current stage does not
    participate in execution-scoped validation.
    """

    prepare = _planned_stage(
        stage_id=10,
        name="prepare",
        parameters=(
            "palette",
            "fill_color",
        ),
    )

    build_plan = _build_plan(
        stages=(prepare,),
    )

    execution_plan = _execution_plan(
        stages=(
            _stage_execution(
                name="prepare",
                state=ProductState.CURRENT,
            ),
        ),
    )

    parameters = required_configuration_parameters(
        build_plan,
        execution_plan,
    )

    assert parameters == ()


def test_required_configuration_follows_mixed_stage_execution() -> None:
    """
    Validation scope follows required execution rather than all stages
    selected into the realized build plan.
    """

    prepare = _planned_stage(
        stage_id=10,
        name="prepare",
        parameters=(
            "source_policy",
            "palette",
        ),
    )

    transform = _planned_stage(
        stage_id=20,
        name="transform",
        parameters=(
            "scale",
            "rotation",
        ),
    )

    package = _planned_stage(
        stage_id=30,
        name="package",
        parameters=("package_format",),
    )

    build_plan = _build_plan(
        stages=(
            prepare,
            transform,
            package,
        ),
    )

    execution_plan = _execution_plan(
        stages=(
            _stage_execution(
                name="prepare",
                state=ProductState.CURRENT,
            ),
            _stage_execution(
                name="transform",
                state=ProductState.STALE,
            ),
            _stage_execution(
                name="package",
                state=ProductState.CURRENT,
            ),
        ),
    )

    parameters = required_configuration_parameters(
        build_plan,
        execution_plan,
    )

    assert parameters == (
        "scale",
        "rotation",
    )


def test_required_configuration_preserves_parameter_declaration_order() -> None:
    """
    Execution-scoped configuration preserves deterministic model declaration
    order while removing duplicate parameter requirements.
    """

    first = _planned_stage(
        stage_id=10,
        name="first",
        parameters=(
            "shared",
            "first_only",
        ),
    )

    second = _planned_stage(
        stage_id=20,
        name="second",
        parameters=(
            "shared",
            "second_only",
        ),
    )

    build_plan = _build_plan(
        stages=(
            first,
            second,
        ),
    )

    execution_plan = _execution_plan(
        stages=(
            _stage_execution(
                name="first",
                state=ProductState.STALE,
            ),
            _stage_execution(
                name="second",
                state=ProductState.ABSENT,
            ),
        ),
    )

    parameters = required_configuration_parameters(
        build_plan,
        execution_plan,
    )

    assert parameters == (
        "shared",
        "first_only",
        "second_only",
    )


def test_required_configuration_does_not_change_execution_plan() -> None:
    """
    Determining validation scope observes rather than alters execution
    decisions.
    """

    current = _planned_stage(
        stage_id=10,
        name="current",
        parameters=("historical_parameter",),
    )

    required = _planned_stage(
        stage_id=20,
        name="required",
        parameters=("current_parameter",),
    )

    build_plan = _build_plan(
        stages=(
            current,
            required,
        ),
    )

    current_execution = _stage_execution(
        name="current",
        state=ProductState.CURRENT,
    )

    required_execution = _stage_execution(
        name="required",
        state=ProductState.STALE,
    )

    execution_plan = _execution_plan(
        stages=(
            current_execution,
            required_execution,
        ),
    )

    before = execution_plan.required_stages

    parameters = required_configuration_parameters(
        build_plan,
        execution_plan,
    )

    after = execution_plan.required_stages

    assert parameters == ("current_parameter",)

    assert before == (required_execution,)

    assert after == before
