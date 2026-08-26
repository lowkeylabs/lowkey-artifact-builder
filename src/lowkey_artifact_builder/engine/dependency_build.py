"""
Cross-artifact dependency build orchestration.

Dependency build orchestration connects persistent-state-aware consumer
planning, targeted producer planning, producer execution, and subsequent
consumer execution.

A consumer whose required cross-artifact producer product is not reusable
cannot execute immediately. Required producer work is first converted into
targeted producer BuildPlans and executed. The consumer is then replanned
against the newly produced persistent products before its own stages are
executed.

Producer products already reusable for their required build-context
fingerprints do not create producer work.

This module intentionally orchestrates one level of cross-artifact
dependencies. Recursive producer dependency traversal and dependency-cycle
handling remain outside this boundary.
"""
# File: src/lowkey_artifact_builder/engine/dependency_build.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from .dependency_plan import (
    create_required_product_dependency_build_plans,
)
from .events import (
    EventSink,
)
from .execution import (
    ExecutionPlan,
)
from .fingerprint_plan import (
    create_required_fingerprints,
)
from .freshness import (
    ProductFingerprint,
)
from .incremental import (
    ProductDependencyFingerprintResolver,
    execute_incremental_artifact_build,
    plan_incremental_execution,
)
from .specs import (
    BuildPlan,
    PlannedProductDependency,
)

# =========================================================
# Errors
# =========================================================


class DependencyBuildError(Exception):
    """
    Base error for cross-artifact dependency build orchestration.
    """


class DependencyCycleError(DependencyBuildError):
    """
    Cross-artifact dependency traversal contains a cycle.
    """


# =========================================================
# Dependency-aware build execution
# =========================================================


def execute_dependency_build(
    build_plan: BuildPlan,
    *,
    product_dependency_fingerprint: (ProductDependencyFingerprintResolver | None) = None,
    event_sink: EventSink | None = None,
) -> ExecutionPlan:
    """
    Execute one dependency-aware artifact build.

    Required cross-artifact producer products are resolved recursively.

    Producer fingerprints discovered during recursive execution are retained
    across the complete orchestration so each dependent artifact can be
    replanned against products produced earlier in the traversal.

    The active dependency path is tracked independently of completed work.
    Re-entering an artifact realization already present on that path is a
    dependency cycle and fails explicitly.
    """

    produced: dict[
        tuple[
            str,
            str,
            str,
            str,
            str,
        ],
        ProductFingerprint,
    ] = {}

    return _execute_dependency_build(
        build_plan,
        supplied_fingerprint=product_dependency_fingerprint,
        produced=produced,
        active=(),
        event_sink=event_sink,
    )


def _execute_dependency_build(
    build_plan: BuildPlan,
    *,
    supplied_fingerprint: (ProductDependencyFingerprintResolver | None),
    produced: dict[
        tuple[
            str,
            str,
            str,
            str,
            str,
        ],
        ProductFingerprint,
    ],
    active: tuple[
        tuple[
            str,
            str,
            str,
        ],
        ...,
    ],
    event_sink: EventSink | None,
) -> ExecutionPlan:
    """
    Execute one node of a dependency-aware build traversal.

    produced is shared by every recursive invocation.

    active contains only artifact realizations on the current recursive
    traversal path. A repeated identity therefore represents a dependency
    cycle rather than merely a producer encountered previously elsewhere
    in the dependency graph.
    """

    identity = (
        build_plan.artifact_id,
        build_plan.model_name,
        build_plan.realization_name,
    )

    if identity in active:
        cycle_start = active.index(
            identity,
        )

        cycle = (
            *active[cycle_start:],
            identity,
        )

        path = " -> ".join(
            f"{artifact}/{model}/{realization}" for artifact, model, realization in cycle
        )

        raise DependencyCycleError(f"Cross-artifact dependency cycle detected: {path}")

    active = (
        *active,
        identity,
    )

    product_dependency_fingerprint = _create_product_dependency_fingerprint_resolver(
        supplied=supplied_fingerprint,
        produced=produced,
    )

    initial_plan = plan_incremental_execution(
        build_plan,
        product_dependency_fingerprint=(product_dependency_fingerprint),
    )

    producer_plans = create_required_product_dependency_build_plans(
        build_plan,
        initial_plan,
    )

    for producer_plan in producer_plans:
        _execute_dependency_build(
            producer_plan,
            supplied_fingerprint=supplied_fingerprint,
            produced=produced,
            active=active,
            event_sink=event_sink,
        )

        _record_producer_fingerprints(
            producer_plan=producer_plan,
            fingerprints=produced,
        )

    product_dependency_fingerprint = _create_product_dependency_fingerprint_resolver(
        supplied=supplied_fingerprint,
        produced=produced,
    )

    replanned = plan_incremental_execution(
        build_plan,
        product_dependency_fingerprint=(product_dependency_fingerprint),
    )

    if replanned.required_product_dependencies:
        raise DependencyBuildError(
            "Producer execution did not satisfy all required product dependencies"
        )

    return execute_incremental_artifact_build(
        build_plan,
        product_dependency_fingerprint=(product_dependency_fingerprint),
        event_sink=event_sink,
    )


# =========================================================
# Producer fingerprint collection
# =========================================================


def _record_producer_fingerprints(
    *,
    producer_plan: BuildPlan,
    fingerprints: dict[
        tuple[
            str,
            str,
            str,
            str,
            str,
        ],
        ProductFingerprint,
    ],
) -> None:
    """
    Record required fingerprints for products realized by one producer.

    Required stage fingerprints are derived after all transitive producer
    dependencies required by this BuildPlan have completed.

    Every persistent product produced by a realized stage therefore maps
    to the fingerprint required for that producing stage.
    """

    required = create_required_fingerprints(
        producer_plan,
    )

    for stage in producer_plan.stages:
        fingerprint = required[stage.name]

        for product in stage.products:
            identity = (
                producer_plan.artifact_id,
                producer_plan.model_name,
                producer_plan.realization_name,
                stage.name,
                product.name,
            )

            fingerprints[identity] = fingerprint


# =========================================================
# Consumer dependency fingerprint resolution
# =========================================================


def _create_product_dependency_fingerprint_resolver(
    *,
    supplied: ProductDependencyFingerprintResolver | None,
    produced: dict[
        tuple[
            str,
            str,
            str,
            str,
            str,
        ],
        ProductFingerprint,
    ],
) -> ProductDependencyFingerprintResolver:
    """
    Create producer-product fingerprint resolution after producer execution.

    Fingerprints derived from producer BuildPlans are authoritative for
    products produced during this orchestration.

    Dependencies not produced during this operation fall back to the
    resolver supplied by the caller. If no supplied resolver exists, no
    authoritative fingerprint is available for those dependencies.
    """

    def resolve(
        dependency: PlannedProductDependency,
    ) -> ProductFingerprint | None:
        product_ref = dependency.product_ref

        identity = (
            product_ref.artifact,
            product_ref.model,
            product_ref.realization,
            product_ref.stage,
            product_ref.product,
        )

        fingerprint = produced.get(
            identity,
        )

        if fingerprint is not None:
            return fingerprint

        if supplied is not None:
            return supplied(
                dependency,
            )

        return None

    return resolve


# =========================================================
# Exports
# =========================================================


__all__ = [
    "DependencyBuildError",
    "DependencyCycleError",
    "execute_dependency_build",
]
