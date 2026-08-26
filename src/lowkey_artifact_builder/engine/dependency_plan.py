"""
Cross-artifact product-dependency planning.

Product-dependency planning composes a consumer BuildPlan with its
ExecutionPlan to construct targeted producer BuildPlans for cross-artifact
products that require production.

The consumer BuildPlan owns the concrete PlannedProductDependency objects
resolved during build planning. The ExecutionPlan identifies which of
those producer products require production for the current build context.

Only required producer products receive producer BuildPlans. Products
whose persistent state is already reusable do not create producer work.

Producer BuildPlan construction is delegated to
create_product_dependency_build_plan so producer configuration resolution,
target selection, prerequisite closure, feature participation, and
filesystem materialization retain one authoritative implementation.

This module performs planning composition only. It does not inspect
persistent product state, gather filesystem evidence, calculate
fingerprints, execute producer or consumer stages, or recursively
orchestrate producer dependencies.
"""
# File: src/lowkey_artifact_builder/engine/dependency_plan.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from lowkey_artifact_builder.model import (
    ProductRef,
)

from .execution import (
    ExecutionPlan,
)
from .plan import (
    create_product_dependency_build_plan,
)
from .specs import (
    BuildPlan,
    PlannedProductDependency,
)

# =========================================================
# Required producer planning
# =========================================================


def create_required_product_dependency_build_plans(
    build_plan: BuildPlan,
    execution_plan: ExecutionPlan,
) -> tuple[BuildPlan, ...]:
    """
    Construct targeted producer BuildPlans for required product dependencies.

    The supplied BuildPlan is authoritative for the concrete
    PlannedProductDependency objects bound to the consumer realization.

    The supplied ExecutionPlan is authoritative for determining which
    producer products require production. Producer products absent from
    required_product_dependencies are reusable and therefore do not create
    producer work.

    Each required ProductRef is matched to its corresponding planned
    dependency in the consumer BuildPlan. Producer planning is then
    delegated to create_product_dependency_build_plan, targeting exactly
    the required producer product and its prerequisite closure.

    Producer plans preserve the order of required_product_dependencies in
    the ExecutionPlan.

    A required producer product that cannot be matched to a concrete
    dependency in the BuildPlan indicates inconsistent planning state and
    fails rather than silently omitting required producer work.
    """

    _validate_plan_identity(
        build_plan=build_plan,
        execution_plan=execution_plan,
    )

    plans: list[BuildPlan] = []

    for required in execution_plan.required_product_dependencies:
        product_ref = _require_product_ref(
            required.product_ref,
        )

        dependency = _find_planned_product_dependency(
            build_plan=build_plan,
            required=product_ref,
        )

        plans.append(
            create_product_dependency_build_plan(
                dependency,
                project_root=build_plan.project_root,
            )
        )

    return tuple(
        plans,
    )


# =========================================================
# Plan validation
# =========================================================


def _validate_plan_identity(
    *,
    build_plan: BuildPlan,
    execution_plan: ExecutionPlan,
) -> None:
    """
    Require the execution plan to describe the supplied BuildPlan.

    Product-dependency execution decisions belong to one concrete artifact,
    model, and realization. Combining decisions from another realized build
    with this BuildPlan could otherwise cause unrelated producer work to be
    scheduled.
    """

    if execution_plan.artifact_id != build_plan.artifact_id:
        raise ValueError(
            f"Execution plan artifact "
            f"{execution_plan.artifact_id!r} does not match "
            f"build plan artifact {build_plan.artifact_id!r}"
        )

    if execution_plan.model_name != build_plan.model_name:
        raise ValueError(
            f"Execution plan model "
            f"{execution_plan.model_name!r} does not match "
            f"build plan model {build_plan.model_name!r}"
        )

    if execution_plan.realization != build_plan.realization_name:
        raise ValueError(
            f"Execution plan realization "
            f"{execution_plan.realization!r} does not match "
            f"build plan realization "
            f"{build_plan.realization_name!r}"
        )


# =========================================================
# Dependency resolution
# =========================================================


def _require_product_ref(
    value: object,
) -> ProductRef:
    """
    Return a validated ProductRef.

    Execution-plan product dependency identity is represented generically
    at the execution boundary. Cross-artifact dependency planning requires
    the canonical ProductRef identity used by BuildPlan dependencies.
    """

    if not isinstance(
        value,
        ProductRef,
    ):
        raise TypeError(
            f"Required product dependency identity must be ProductRef, got {type(value).__name__}"
        )

    return value


def _find_planned_product_dependency(
    *,
    build_plan: BuildPlan,
    required: ProductRef,
) -> PlannedProductDependency:
    """
    Return the concrete planned dependency matching one required ProductRef.

    ProductRef is the canonical cross-artifact product identity. Matching
    therefore does not depend on filesystem paths or object identity.

    A required product absent from the consumer BuildPlan indicates
    inconsistent planning state and fails rather than silently omitting
    producer work.
    """

    for dependency in build_plan.planned_product_dependencies:
        if dependency.product_ref == required:
            return dependency

    raise ValueError(
        f"Required product dependency "
        f"{required.artifact}/"
        f"{required.model}/"
        f"{required.realization}/"
        f"{required.stage}/"
        f"{required.product} "
        f"is not present in build plan "
        f"{build_plan.artifact_id!r}"
    )


# =========================================================
# Exports
# =========================================================


__all__ = [
    "create_required_product_dependency_build_plans",
]
