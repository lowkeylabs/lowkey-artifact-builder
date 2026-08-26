"""
Execution planning policy.

Execution planning determines whether realized stages and bound
cross-artifact product dependencies require production for the current
build context.

This module contains pure execution-decision policy, execution-plan
representation, composition of realized build plans with resolved
persistent product states, and the high-level composition boundary that
constructs execution plans from persistent state.

It does not inspect the filesystem directly, gather product evidence
directly, evaluate product freshness directly, emit execution events,
construct stage contexts, construct producer build plans, or execute
stages.

Persistent-state-aware planning delegates product-state resolution to the
execution-state boundary and then applies the same pure execution-plan
construction used by callers supplying their own ProductState resolver.

Cross-artifact product dependencies are represented as producer-product
requirements. Planning determines whether each bound producer product is
already reusable or requires production, but does not decide how required
producer work is recursively planned or executed.
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
from .freshness import (
    ProductFingerprint,
)
from .specs import (
    BuildPlan,
    PlannedProductDependency,
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


type RequiredProductDependencyFingerprintResolver = Callable[
    [PlannedProductDependency],
    ProductFingerprint | None,
]


type ProductDependencyStateResolver = Callable[
    [
        PlannedProductDependency,
        ProductFingerprint | None,
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
# Planned product dependency execution
# =========================================================


@dataclass(
    frozen=True,
    slots=True,
)
class PlannedProductDependencyExecution:
    """
    Production decision for one bound cross-artifact product.

    product_ref identifies the concrete producer artifact, model,
    realization, stage, and product required by the consumer.

    state is the evaluated persistent state of that producer product.

    requires_production is derived from ProductState so the planning
    decision cannot contradict the underlying persistent-state evidence.

    This representation deliberately identifies required producer work
    without constructing or retaining a producer BuildPlan.
    """

    product_ref: object
    state: ProductState

    @property
    def requires_production(
        self,
    ) -> bool:
        """
        Return whether the bound producer product requires production.
        """

        return self.state.requires_build


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

    product_dependencies preserves the bound cross-artifact producer
    products required by the realized build plan and their evaluated
    persistent states.

    required_stages exposes the ordered subset of local realized stages
    that must actually execute for the current build context.

    required_product_dependencies exposes the bound producer products
    that are not currently reusable and therefore require production
    before their consumers can execute.
    """

    artifact_id: str
    model_name: str
    realization: str
    stages: tuple[PlannedStageExecution, ...]
    product_dependencies: tuple[
        PlannedProductDependencyExecution,
        ...,
    ] = ()

    @property
    def required_stages(
        self,
    ) -> tuple[PlannedStageExecution, ...]:
        """
        Return the ordered local stages that require execution.
        """

        return tuple(stage for stage in self.stages if stage.requires_execution)

    @property
    def required_product_dependencies(
        self,
    ) -> tuple[PlannedProductDependencyExecution, ...]:
        """
        Return bound producer products that require production.
        """

        return tuple(
            dependency for dependency in self.product_dependencies if dependency.requires_production
        )


# =========================================================
# Execution-plan construction
# =========================================================


def create_execution_plan(
    build_plan: BuildPlan,
    *,
    product_state: ProductStateResolver,
    product_dependencies: tuple[
        PlannedProductDependencyExecution,
        ...,
    ] = (),
) -> ExecutionPlan:
    """
    Construct execution decisions for one realized build plan.

    Persistent product state is resolved independently for every declared
    product of every realized stage.

    Product states remain ordered consistently with the stage's declared
    products. Stage execution policy is derived from those states by
    PlannedStageExecution.

    Already-resolved cross-artifact product dependency decisions may be
    supplied independently. This keeps persistent-state resolution outside
    the pure execution-plan construction boundary.

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
        product_dependencies=product_dependencies,
    )


# =========================================================
# Product dependency planning
# =========================================================


def _plan_product_dependencies(
    build_plan: BuildPlan,
    *,
    product_state,
    required_fingerprint: RequiredProductDependencyFingerprintResolver,
) -> tuple[PlannedProductDependencyExecution, ...]:
    """
    Resolve execution decisions for bound cross-artifact products.

    Each planned dependency already contains its concrete producer identity
    and persistent product path. Required provenance is resolved for that
    product and persistent state is delegated to the execution-state
    resolver.

    No producer BuildPlan is constructed here. A non-CURRENT product is
    represented only as requiring production; recursive producer planning
    belongs to a later orchestration boundary.
    """

    dependencies: list[PlannedProductDependencyExecution] = []

    for dependency in build_plan.planned_product_dependencies:
        fingerprint = required_fingerprint(
            dependency,
        )

        state = product_state.product_dependency(
            dependency,
            required_fingerprint=fingerprint,
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
# Persistent-state-aware planning
# =========================================================


def plan_execution(
    build_plan: BuildPlan,
    *,
    required_fingerprint: RequiredFingerprintResolver,
    required_product_dependency_fingerprint: (
        RequiredProductDependencyFingerprintResolver | None
    ) = None,
) -> ExecutionPlan:
    """
    Construct an execution plan from current persistent product state.

    Local product-state resolution is adapted from the realized BuildPlan
    through create_execution_state_resolver. The resulting resolver gathers
    and evaluates persistent state using the established evidence and
    freshness boundaries.

    When the BuildPlan contains bound cross-artifact product dependencies,
    required_product_dependency_fingerprint supplies the provenance required
    for each producer product. Persistent state for each dependency is
    resolved independently through the same execution-state boundary.

    Execution-plan construction remains delegated to create_execution_plan
    so local stage execution policy has a single implementation.

    This operation determines whether bound producer products require
    production but does not construct producer build plans or recursively
    schedule producer execution.

    This operation performs persistent-state inspection but does not execute
    stages or modify build products.
    """

    product_state = create_execution_state_resolver(
        build_plan,
        required_fingerprint=required_fingerprint,
    )

    product_dependencies: tuple[
        PlannedProductDependencyExecution,
        ...,
    ] = ()

    if build_plan.planned_product_dependencies:
        if required_product_dependency_fingerprint is None:
            raise ValueError(
                "Product dependency fingerprint resolution is required "
                "when the build plan contains product dependencies"
            )

        product_dependencies = _plan_product_dependencies(
            build_plan,
            product_state=product_state,
            required_fingerprint=(required_product_dependency_fingerprint),
        )

    return create_execution_plan(
        build_plan,
        product_state=product_state,
        product_dependencies=product_dependencies,
    )


# =========================================================
# Exports
# =========================================================


__all__ = [
    "ExecutionPlan",
    "PlannedProductDependencyExecution",
    "PlannedStageExecution",
    "ProductDependencyStateResolver",
    "ProductStateResolver",
    "RequiredProductDependencyFingerprintResolver",
    "create_execution_plan",
    "plan_execution",
    "stage_requires_execution",
]
