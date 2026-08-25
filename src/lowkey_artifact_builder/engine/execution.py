"""
Execution planning policy.

Execution planning determines whether realized stages require execution
for the current build context.

This module contains pure execution-decision policy, execution-plan
representation, composition of realized build plans with resolved
persistent product states, and the high-level composition boundary that
constructs execution plans from persistent state.

It does not inspect the filesystem directly, gather product evidence
directly, evaluate product freshness directly, emit execution events,
construct stage contexts, or execute stages.

Persistent-state-aware planning delegates product-state resolution to the
execution-state boundary and then applies the same pure execution-plan
construction used by callers supplying their own ProductState resolver.
"""
# File: src/lowkey_artifact_builder/engine/execution.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from .execution_state import (
    RequiredFingerprintResolver,
    create_execution_state_resolver,
)
from .specs import (
    BuildPlan,
    PlannedStage,
)
from .state import (
    ProductState,
)

# =========================================================
# Product-state resolution
# =========================================================


type ProductStateResolver = Callable[
    [
        PlannedStage,
        str,
    ],
    ProductState,
]


# =========================================================
# Stage execution decisions
# =========================================================


def stage_requires_execution(
    states: tuple[ProductState, ...],
) -> bool:
    """
    Return whether a realized stage requires execution.

    A stage without persistent products requires execution because no
    persistent product state exists that can prove its previous work
    reusable.

    A stage with persistent products may be skipped only when every
    declared product is CURRENT.

    Any product state requiring production therefore requires execution
    of the whole producing stage.
    """

    if not states:
        return True

    return any(state.requires_build for state in states)


# =========================================================
# Planned stage execution
# =========================================================


@dataclass(
    frozen=True,
    slots=True,
)
class PlannedStageExecution:
    """
    Execution decision for one realized stage.

    stage_name identifies the realized stage.

    product_states contains the evaluated persistent state of the stage's
    declared products in declaration order.

    requires_execution is derived from those states so the execution
    decision cannot contradict the underlying product-state evidence.
    """

    stage_name: str
    product_states: tuple[ProductState, ...]

    @property
    def requires_execution(
        self,
    ) -> bool:
        """
        Return whether this realized stage must execute.
        """

        return stage_requires_execution(
            self.product_states,
        )


# =========================================================
# Execution plan
# =========================================================


@dataclass(
    frozen=True,
    slots=True,
)
class ExecutionPlan:
    """
    Concrete execution decisions for one artifact realization.

    stages preserves the complete ordered realized workflow, including
    stages whose persistent products are already reusable.

    required_stages exposes the ordered subset that must actually execute
    for the current build context.
    """

    artifact_id: str
    model_name: str
    realization: str
    stages: tuple[PlannedStageExecution, ...]

    @property
    def required_stages(
        self,
    ) -> tuple[PlannedStageExecution, ...]:
        """
        Return the ordered stages that require execution.
        """

        return tuple(stage for stage in self.stages if stage.requires_execution)


# =========================================================
# Execution-plan construction
# =========================================================


def create_execution_plan(
    build_plan: BuildPlan,
    *,
    product_state: ProductStateResolver,
) -> ExecutionPlan:
    """
    Construct execution decisions for one realized build plan.

    Persistent product state is resolved independently for every declared
    product of every realized stage.

    Product states remain ordered consistently with the stage's declared
    products. Stage execution policy is derived from those states by
    PlannedStageExecution.

    The resulting execution plan retains the identity and ordered stage
    structure of the realized build plan without retaining the BuildPlan
    or PlannedStage objects themselves.

    This operation is pure with respect to execution planning. The supplied
    product-state resolver owns whatever mechanism determines ProductState.
    """

    stages: list[PlannedStageExecution] = []

    for stage in build_plan.stages:
        product_states = tuple(
            product_state(
                stage,
                product.name,
            )
            for product in stage.products
        )

        stages.append(
            PlannedStageExecution(
                stage_name=stage.name,
                product_states=product_states,
            )
        )

    return ExecutionPlan(
        artifact_id=build_plan.artifact_id,
        model_name=build_plan.model_name,
        realization=build_plan.realization_name,
        stages=tuple(
            stages,
        ),
    )


# =========================================================
# Persistent-state-aware planning
# =========================================================


def plan_execution(
    build_plan: BuildPlan,
    *,
    required_fingerprint: RequiredFingerprintResolver,
) -> ExecutionPlan:
    """
    Construct an execution plan from current persistent product state.

    Product-state resolution is adapted from the realized BuildPlan through
    create_execution_state_resolver. The resulting resolver gathers and
    evaluates persistent state using the established evidence and freshness
    boundaries.

    Execution-plan construction remains delegated to create_execution_plan
    so stage execution policy has a single implementation.

    This operation performs persistent-state inspection but does not execute
    stages or modify build products.
    """

    product_state = create_execution_state_resolver(
        build_plan,
        required_fingerprint=required_fingerprint,
    )

    return create_execution_plan(
        build_plan,
        product_state=product_state,
    )


# =========================================================
# Exports
# =========================================================


__all__ = [
    "ExecutionPlan",
    "PlannedStageExecution",
    "ProductStateResolver",
    "create_execution_plan",
    "plan_execution",
    "stage_requires_execution",
]
