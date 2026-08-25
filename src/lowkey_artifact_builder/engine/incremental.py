"""
Persistent-state-aware incremental planning and execution.

Incremental planning composes required build-context fingerprint
generation, persistent product-state resolution, and execution-plan
construction.

Incremental execution applies that planning policy to an already-realized
BuildPlan. Only stages whose persistent products cannot be reused are
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
behavior, gather product evidence directly, or evaluate ProductState
directly.
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
    event_sink: EventSink | None = None,
) -> ExecutionPlan:
    """
    Execute only stages required by the current persistent build state.

    A build.started event is emitted before incremental product-state
    resolution begins.

    Required fingerprints are calculated once before execution planning.
    This provides one coherent build-context snapshot for both execution
    planning and subsequently persisted completion metadata.

    Product-state observations are emitted while the execution plan is
    constructed.

    Realized stages are observed in build-plan order.

    Reusable stages emit a stage.skipped event and are not executed.

    Required stages emit stage.started immediately before execution.

    If stage execution fails, a stage.failed event is emitted and the
    original exception propagates immediately without observing or
    executing later stages.

    Completion metadata is persisted only after the supplied stage
    executor returns successfully. A stage.completed event is emitted
    only after successful completion metadata has been persisted.

    A build.completed event is emitted after all realized stages have
    been successfully processed, including builds requiring no stage
    execution.

    Observation is optional and does not participate in execution
    decisions.

    Return the ExecutionPlan used for this execution.
    """

    _emit_build_event(
        event_sink,
        build_plan=build_plan,
        kind="build.started",
    )

    fingerprints = create_required_fingerprints(
        build_plan,
    )

    execution_plan = _create_incremental_execution_plan(
        build_plan=build_plan,
        fingerprints=fingerprints,
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

    Persistent-state-aware planning determines which realized stages
    require execution.

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
    event_sink: EventSink | None = None,
) -> ExecutionPlan:
    """
    Construct an execution plan using precomputed required fingerprints.

    When an event sink is supplied, each persistent product-state
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
