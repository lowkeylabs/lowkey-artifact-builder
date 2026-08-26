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

    The consumer is first planned without executing local stages.

    If every bound producer product is already reusable, the consumer is
    executed directly using the same producer-product fingerprint
    resolution supplied by the caller.

    If producer products require production, targeted producer BuildPlans
    are constructed from the consumer's execution requirements and
    executed before the consumer.

    After producer execution, required producer fingerprints are derived
    from the producer BuildPlans. The consumer is then replanned so its
    persistent state and required stage fingerprints are evaluated against
    the newly produced producer products.

    Only after that replan may the consumer execute.

    This operation intentionally supports one producer dependency level.
    Producer BuildPlans are executed through incremental artifact
    execution directly rather than recursively through this function.
    """

    initial_plan = plan_incremental_execution(
        build_plan,
        product_dependency_fingerprint=product_dependency_fingerprint,
    )

    producer_plans = create_required_product_dependency_build_plans(
        build_plan,
        initial_plan,
    )

    if not producer_plans:
        return execute_incremental_artifact_build(
            build_plan,
            product_dependency_fingerprint=product_dependency_fingerprint,
            event_sink=event_sink,
        )

    producer_fingerprints: dict[
        tuple[
            str,
            str,
            str,
            str,
            str,
        ],
        ProductFingerprint,
    ] = {}

    for producer_plan in producer_plans:
        execute_incremental_artifact_build(
            producer_plan,
            event_sink=event_sink,
        )

        _record_producer_fingerprints(
            producer_plan=producer_plan,
            fingerprints=producer_fingerprints,
        )

    required_product_dependency_fingerprint = _create_product_dependency_fingerprint_resolver(
        supplied=product_dependency_fingerprint,
        produced=producer_fingerprints,
    )

    replanned = plan_incremental_execution(
        build_plan,
        product_dependency_fingerprint=(required_product_dependency_fingerprint),
    )

    if replanned.required_product_dependencies:
        raise ValueError("Producer execution did not satisfy all required product dependencies")

    return execute_incremental_artifact_build(
        build_plan,
        product_dependency_fingerprint=(required_product_dependency_fingerprint),
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

    Required stage fingerprints are derived from the same producer
    BuildPlan used for execution.

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
    "execute_dependency_build",
]
