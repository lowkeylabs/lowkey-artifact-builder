"""
Persistent-state-aware incremental planning and execution.

Incremental planning composes cross-artifact product dependency state
resolution, required build-context fingerprint generation, persistent
local product-state resolution, and execution-plan construction.

Cross-artifact product dependencies are evaluated before consumer-stage
fingerprints are generated. A producer product that is not reusable is
therefore represented as required producer work without attempting to
fingerprint consumer stages against unavailable or unusable producer
content.

Incremental execution applies that planning policy to an already-realized
BuildPlan. Only local stages whose persistent products cannot be reused are
executed. Successful execution records completion metadata using the
fingerprint required by the current build context.

Incremental execution may optionally expose semantic product-state and
stage lifecycle observations through the engine event contract.
Observation does not participate in execution decisions.

Incremental artifact execution connects that orchestration to the
established planned StageContext construction and stage-dispatch
boundaries.

This module coordinates existing planning, execution, persistence, and
observation boundaries. It does not implement model-specific stage
behavior, gather product evidence directly, evaluate ProductState
directly, or recursively construct producer build plans.
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
from .context import (
    create_planned_stage_context,
)
from .events import (
    EventSink,
    ExecutionEvent,
    ProductStateEvent,
    emit_event,
)
from .execution import (
    ExecutionPlan,
    PlannedProductDependencyExecution,
    create_execution_plan,
)
from .execution_state import (
    ProductState,
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
    StageContext,
)
from .stage import (
    execute_stage as dispatch_stage,
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

    Bound cross-artifact product dependencies are evaluated before
    consumer-stage fingerprints are generated.

    If any producer product is not currently reusable, the returned
    ExecutionPlan identifies that required producer work without
    attempting to fingerprint the consumer workflow against producer
    content that is unavailable or already known to require production.

    Once every bound producer product is reusable, required consumer-stage
    fingerprints are derived from the complete realized BuildPlan,
    including declared parameters, external input contents, local
    dependency fingerprints, and cross-artifact product contents.

    Persistent local product state is then evaluated against those
    fingerprints.

    Producer build-plan construction and recursive producer execution are
    intentionally outside this boundary.
    """

    product_dependencies = _plan_product_dependencies(
        build_plan,
    )

    if any(dependency.requires_production for dependency in product_dependencies):
        return _create_blocked_execution_plan(
            build_plan=build_plan,
            product_dependencies=product_dependencies,
        )

    fingerprints = create_required_fingerprints(
        build_plan,
    )

    return _create_incremental_execution_plan(
        build_plan=build_plan,
        fingerprints=fingerprints,
        product_dependencies=product_dependencies,
    )


# =========================================================
# Incremental build execution
# =========================================================


def execute_incremental_build(
    build_plan: BuildPlan,
    *,
    execute_stage: IncrementalStageExecutor,
    event_sink: EventSink | None = None,
) -> ExecutionPlan:
    """
    Execute local stages required by the current persistent build state.

    A build.started event is emitted before incremental product-state
    resolution begins.

    Bound cross-artifact product dependencies are evaluated before
    consumer-stage fingerprint generation.

    Required producer work is represented in the returned ExecutionPlan.
    This function does not recursively execute producer artifacts.

    Consumer execution cannot proceed while a required producer product
    requires production.

    Once all producer products are reusable, required fingerprints are
    calculated once before local execution planning. This provides one
    coherent build-context snapshot for both execution planning and
    subsequently persisted completion metadata.

    Product-state observations are emitted while local execution state is
    resolved.

    Realized local stages are observed in build-plan order.

    Reusable stages emit a stage.skipped event and are not executed.

    Required stages emit stage.started immediately before execution.

    If stage execution fails, stage.failed is emitted before the enclosing
    build.failed event.

    Completion metadata is persisted only after the supplied stage
    executor returns successfully. A stage.completed event is emitted
    only after successful completion metadata has been persisted.

    A build.completed event is emitted after all realized local stages
    have been successfully processed, including builds requiring no local
    stage execution.

    Observation is optional and does not participate in execution
    decisions.

    Return the ExecutionPlan used for this execution.
    """

    _emit_build_event(
        event_sink,
        build_plan=build_plan,
        kind="build.started",
    )

    try:
        product_dependencies = _plan_product_dependencies(
            build_plan,
        )

        if any(dependency.requires_production for dependency in product_dependencies):
            return _create_blocked_execution_plan(
                build_plan=build_plan,
                product_dependencies=product_dependencies,
            )

        fingerprints = create_required_fingerprints(
            build_plan,
        )

        execution_plan = _create_incremental_execution_plan(
            build_plan=build_plan,
            fingerprints=fingerprints,
            product_dependencies=product_dependencies,
            event_sink=event_sink,
        )

        required_stage_names = {
            planned_execution.stage_name for planned_execution in execution_plan.required_stages
        }

        for stage in build_plan.stages:
            if stage.name not in required_stage_names:
                _emit_stage_event(
                    event_sink,
                    build_plan=build_plan,
                    stage=stage,
                    kind="stage.skipped",
                )

                continue

            _emit_stage_event(
                event_sink,
                build_plan=build_plan,
                stage=stage,
                kind="stage.started",
            )

            try:
                execute_stage(
                    stage,
                )
            except Exception:
                _emit_stage_event(
                    event_sink,
                    build_plan=build_plan,
                    stage=stage,
                    kind="stage.failed",
                )

                raise

            if stage.products:
                _write_successful_completion(
                    build_plan=build_plan,
                    stage=stage,
                    fingerprint=fingerprints[stage.name],
                )

            _emit_stage_event(
                event_sink,
                build_plan=build_plan,
                stage=stage,
                kind="stage.completed",
            )

    except Exception:
        _emit_build_event(
            event_sink,
            build_plan=build_plan,
            kind="build.failed",
        )

        raise

    _emit_build_event(
        event_sink,
        build_plan=build_plan,
        kind="build.completed",
    )

    return execution_plan


# =========================================================
# Engine-integrated incremental execution
# =========================================================


def execute_incremental_artifact_build(
    build_plan: BuildPlan,
    *,
    event_sink: EventSink | None = None,
) -> ExecutionPlan:
    """
    Execute an incremental build through the engine dispatch boundary.

    Persistent-state-aware planning determines which realized local stages
    require execution.

    Bound cross-artifact producer products must already be reusable.
    Recursive producer planning and execution belong to a higher-level
    orchestration boundary.

    Each required PlannedStage is adapted directly to the established
    engine execution boundary using the same BuildPlan and PlannedStage
    already participating in incremental planning.

    This preserves the realized plan as the authoritative execution
    description and avoids independently re-resolving artifact
    configuration while dispatching the plan.

    Completion persistence remains owned by execute_incremental_build, so
    successful engine dispatch records the required build-context
    fingerprint while failed dispatch records no successful completion.

    Structured product-state and lifecycle observation is forwarded to
    incremental execution.
    """

    def execute_planned_stage(
        stage: PlannedStage,
    ) -> None:
        context = create_planned_stage_context(
            build_plan,
            stage,
        )

        context.working_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        execute_stage(
            context,
        )

    return execute_incremental_build(
        build_plan,
        execute_stage=execute_planned_stage,
        event_sink=event_sink,
    )


def execute_stage(
    context: StageContext,
) -> None:
    """
    Dispatch one resolved StageContext.

    This module-level boundary keeps engine dispatch replaceable for
    orchestration tests while delegating production behavior to the
    established stage executor.
    """

    dispatch_stage(
        context,
    )


# =========================================================
# Product dependency planning
# =========================================================


def _plan_product_dependencies(
    build_plan: BuildPlan,
) -> tuple[
    PlannedProductDependencyExecution,
    ...,
]:
    """
    Evaluate persistent state for bound cross-artifact products.

    Producer-product state is resolved before consumer-stage fingerprints
    are generated.

    No producer BuildPlan is constructed here. A producer product that is
    not reusable is represented only as required producer work.
    """

    if not build_plan.planned_product_dependencies:
        return ()

    def unavailable_stage_fingerprint(
        stage: PlannedStage,
    ) -> ProductFingerprint | None:
        """
        Local stage fingerprints are not required while resolving producer
        product state.
        """

        return None

    product_state = create_execution_state_resolver(
        build_plan,
        required_fingerprint=unavailable_stage_fingerprint,
    )

    dependencies: list[PlannedProductDependencyExecution] = []

    for dependency in build_plan.planned_product_dependencies:
        state = product_state.product_dependency(
            dependency,
            required_fingerprint=None,
        )

        dependencies.append(
            PlannedProductDependencyExecution(
                product_ref=dependency.product_ref,
                state=state,
            )
        )

    return tuple(
        dependencies,
    )


# =========================================================
# Blocked consumer planning
# =========================================================


def _create_blocked_execution_plan(
    *,
    build_plan: BuildPlan,
    product_dependencies: tuple[
        PlannedProductDependencyExecution,
        ...,
    ],
) -> ExecutionPlan:
    """
    Create an execution plan blocked by required producer work.

    Consumer-stage persistent state cannot be evaluated authoritatively
    until all required producer products are reusable, because consumer
    fingerprints include producer-product contents.

    The complete local workflow is nevertheless retained in the execution
    plan. Local product states are represented as requiring production so
    no consumer stage can be mistaken for reusable while its build context
    is incomplete.
    """

    def unresolved_product_state(
        stage: PlannedStage,
        product_name: str,
    ) -> ProductState:
        return ProductState.ABSENT

    return create_execution_plan(
        build_plan,
        product_state=unresolved_product_state,
        product_dependencies=product_dependencies,
    )


# =========================================================
# Execution events
# =========================================================


def _emit_stage_event(
    event_sink: EventSink | None,
    *,
    build_plan: BuildPlan,
    stage: PlannedStage,
    kind: str,
) -> None:
    """
    Emit one semantic stage lifecycle event.
    """

    emit_event(
        event_sink,
        ExecutionEvent(
            kind=kind,
            artifact_id=build_plan.artifact_id,
            model_name=build_plan.model_name,
            realization=build_plan.realization_name,
            stage_name=stage.name,
        ),
    )


def _emit_build_event(
    event_sink: EventSink | None,
    *,
    build_plan: BuildPlan,
    kind: str,
) -> None:
    """
    Emit one semantic build lifecycle event.
    """

    emit_event(
        event_sink,
        ExecutionEvent(
            kind=kind,
            artifact_id=build_plan.artifact_id,
            model_name=build_plan.model_name,
            realization=build_plan.realization_name,
        ),
    )


def _emit_product_state_event(
    event_sink: EventSink | None,
    *,
    build_plan: BuildPlan,
    stage: PlannedStage,
    product_name: str,
    state: ProductState,
) -> None:
    """
    Emit one semantic persistent product-state observation.
    """

    emit_event(
        event_sink,
        ProductStateEvent(
            artifact_id=build_plan.artifact_id,
            model_name=build_plan.model_name,
            realization=build_plan.realization_name,
            stage_name=stage.name,
            product_name=product_name,
            state=state,
        ),
    )


# =========================================================
# Execution-plan composition
# =========================================================


def _create_incremental_execution_plan(
    *,
    build_plan: BuildPlan,
    fingerprints: dict[str, ProductFingerprint],
    product_dependencies: tuple[
        PlannedProductDependencyExecution,
        ...,
    ] = (),
    event_sink: EventSink | None = None,
) -> ExecutionPlan:
    """
    Construct an execution plan using precomputed required fingerprints.

    Cross-artifact product dependencies have already been evaluated before
    this boundary.

    When an event sink is supplied, each persistent local product-state
    resolution is exposed through a ProductStateEvent without changing
    the resolved state or execution decision.
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

    resolve_product_state = create_execution_state_resolver(
        build_plan,
        required_fingerprint=required_fingerprint,
    )

    def observed_product_state(
        stage: PlannedStage,
        product_name: str,
    ) -> ProductState:
        state = resolve_product_state(
            stage,
            product_name,
        )

        _emit_product_state_event(
            event_sink,
            build_plan=build_plan,
            stage=stage,
            product_name=product_name,
            state=state,
        )

        return state

    return create_execution_plan(
        build_plan,
        product_state=observed_product_state,
        product_dependencies=product_dependencies,
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
    "execute_incremental_artifact_build",
    "execute_incremental_build",
    "plan_incremental_execution",
]
