"""
Persistent-state-aware incremental planning and execution.

Incremental planning composes required build-context fingerprint
generation, persistent product-state resolution, and execution-plan
construction.

Incremental execution applies that planning policy to an already-realized
BuildPlan. Only stages whose persistent products cannot be reused are
executed. Successful execution records completion metadata using the
fingerprint required by the current build context.

This module coordinates existing planning, execution, and persistence
boundaries. It does not implement model-specific stage behavior, gather
product evidence directly, or evaluate ProductState directly.
"""
# File: src/lowkey_artifact_builder/engine/incremental.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from .completion import (
    StageCompletion,
    write_stage_completion,
)
from .execution import (
    ExecutionPlan,
    create_execution_plan,
)
from .execution_state import (
    create_execution_state_resolver,
)
from .fingerprint_plan import (
    create_required_fingerprints,
)
from .freshness import (
    ProductFingerprint,
)
from .specs import (
    BuildPlan,
    PlannedStage,
)

# =========================================================
# Stage execution
# =========================================================


type IncrementalStageExecutor = Callable[
    [
        PlannedStage,
    ],
    None,
]


# =========================================================
# Incremental execution planning
# =========================================================


def plan_incremental_execution(
    build_plan: BuildPlan,
) -> ExecutionPlan:
    """
    Construct a persistent-state-aware execution plan.

    Required fingerprints are derived from the realized BuildPlan,
    including declared parameters, external input contents, and upstream
    dependency fingerprints.

    Persistent product state is then evaluated against those required
    fingerprints. The resulting ExecutionPlan preserves every realized
    stage while identifying the subset whose products cannot be reused.

    Fingerprints are calculated once for the complete realized plan and
    subsequently resolved by stage identity.
    """

    fingerprints = create_required_fingerprints(
        build_plan,
    )

    return _create_incremental_execution_plan(
        build_plan=build_plan,
        fingerprints=fingerprints,
    )


# =========================================================
# Incremental build execution
# =========================================================


def execute_incremental_build(
    build_plan: BuildPlan,
    *,
    execute_stage: IncrementalStageExecutor,
) -> ExecutionPlan:
    """
    Execute only stages required by the current persistent build state.

    Required fingerprints are calculated once before execution begins.
    This provides one coherent build-context snapshot for both execution
    planning and subsequently persisted completion metadata.

    Required stages execute in realized build-plan order.

    Completion metadata is persisted only after the supplied stage
    executor returns successfully. A failed stage therefore receives no
    successful completion record from this operation, and the failure
    propagates immediately without executing later stages.

    Return the ExecutionPlan used for this execution.
    """

    fingerprints = create_required_fingerprints(
        build_plan,
    )

    execution_plan = _create_incremental_execution_plan(
        build_plan=build_plan,
        fingerprints=fingerprints,
    )

    stages = {stage.name: stage for stage in build_plan.stages}

    for planned_execution in execution_plan.required_stages:
        try:
            stage = stages[planned_execution.stage_name]
        except KeyError as exc:
            raise ValueError(
                f"Execution stage "
                f"{planned_execution.stage_name!r} "
                f"is unavailable from the build plan"
            ) from exc

        execute_stage(
            stage,
        )

        if stage.products:
            _write_successful_completion(
                build_plan=build_plan,
                stage=stage,
                fingerprint=fingerprints[stage.name],
            )

    return execution_plan


# =========================================================
# Execution-plan composition
# =========================================================


def _create_incremental_execution_plan(
    *,
    build_plan: BuildPlan,
    fingerprints: dict[str, ProductFingerprint],
) -> ExecutionPlan:
    """
    Construct an execution plan using precomputed required fingerprints.
    """

    def required_fingerprint(
        stage: PlannedStage,
    ) -> ProductFingerprint:
        try:
            return fingerprints[stage.name]
        except KeyError as exc:
            raise ValueError(
                f"Required fingerprint for stage {stage.name!r} is unavailable"
            ) from exc

    product_state = create_execution_state_resolver(
        build_plan,
        required_fingerprint=required_fingerprint,
    )

    return create_execution_plan(
        build_plan,
        product_state=product_state,
    )


# =========================================================
# Completion persistence
# =========================================================


def _write_successful_completion(
    *,
    build_plan: BuildPlan,
    stage: PlannedStage,
    fingerprint: ProductFingerprint,
) -> None:
    """
    Persist successful completion metadata for one executed stage.
    """

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


def _stage_working_dir(
    stage: PlannedStage,
) -> Path:
    """
    Return the common working directory of a stage's persistent products.

    Planned product paths are fully realized filesystem paths. Persistent
    products belonging to one realized stage must therefore share one
    parent directory.
    """

    if not stage.products:
        raise ValueError(f"Stage {stage.name!r} declares no persistent products")

    working_dirs = {product.path.parent for product in stage.products}

    if len(working_dirs) != 1:
        raise ValueError(
            f"Persistent products for stage {stage.name!r} do not share one working directory"
        )

    return next(
        iter(
            working_dirs,
        )
    )


# =========================================================
# Exports
# =========================================================


__all__ = [
    "IncrementalStageExecutor",
    "execute_incremental_build",
    "plan_incremental_execution",
]
