"""
Execution product-state resolution.

Execution product-state resolution adapts realized build-plan stages,
products, and bound cross-artifact product dependencies to persistent
product-state evaluation.

The resolver validates that requested stages, products, and product
dependencies belong to the realized BuildPlan, determines their producing
stage working directories, resolves the fingerprints required by the
current build context, and delegates persistent evidence gathering and
ProductState evaluation to the persistent product-state resolver.

Expected completion identity for realized stage products is derived from
the authoritative BuildPlan and PlannedStage.

Expected completion identity for cross-artifact product dependencies is
derived from the dependency's concrete producer binding. Completion
metadata therefore cannot prove reuse unless it belongs to the artifact,
model, realization, stage, and product whose persistent state is being
evaluated.

Cross-artifact dependency resolution evaluates only the bound producer
product. It does not require the producer artifact's complete build plan,
downstream stages, or final artifact to exist.

This module provides orchestration only. It does not gather filesystem
evidence directly, evaluate ProductState directly, construct execution
plans, emit execution events, resolve artifact configuration, or execute
stages.
"""
# File: src/lowkey_artifact_builder/engine/execution_state.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path

from .evidence import (
    create_product_state_resolver,
)
from .freshness import (
    ProductFingerprint,
)
from .specs import (
    BuildPlan,
    PlannedProduct,
    PlannedProductDependency,
    PlannedStage,
)
from .state import (
    ProductState,
)

# =========================================================
# Fingerprint resolution
# =========================================================


type RequiredFingerprintResolver = Callable[
    [PlannedStage],
    ProductFingerprint | None,
]


# =========================================================
# Execution product-state resolution
# =========================================================


class ExecutionProductStateResolver:
    """
    Resolve persistent product state for one realized BuildPlan.

    The resolver remains callable for products owned directly by realized
    stages:

        resolver(stage, product_name)

    Bound cross-artifact products are resolved explicitly through:

        resolver.product_dependency(
            dependency,
            required_fingerprint=...,
        )

    Keeping these operations distinct preserves the existing execution
    planning interface while allowing producer products outside the
    consumer's realized stage graph to participate in persistent-state
    evaluation.
    """

    def __init__(
        self,
        build_plan: BuildPlan,
        *,
        required_fingerprint: RequiredFingerprintResolver,
    ) -> None:
        """
        Initialize one execution product-state resolver.
        """

        self._build_plan = build_plan
        self._required_fingerprint = required_fingerprint
        self._stages = tuple(
            build_plan.stages,
        )
        self._product_dependencies = tuple(
            build_plan.planned_product_dependencies,
        )

    def __call__(
        self,
        stage: PlannedStage,
        product_name: str,
    ) -> ProductState:
        """
        Resolve persistent state for a product owned by a realized stage.
        """

        _validate_stage(
            self._stages,
            stage,
        )

        product = _find_product(
            stage,
            product_name,
        )

        working_dir = _stage_working_directory(
            artifact_dir=self._build_plan.artifact_dir,
            stage=stage,
        )

        fingerprint = self._required_fingerprint(
            stage,
        )

        persistent_resolver = create_product_state_resolver(
            working_dir=working_dir,
            artifact_id=self._build_plan.artifact_id,
            model_name=self._build_plan.model_name,
            realization=self._build_plan.realization_name,
            stage_name=stage.name,
            required_fingerprints=(
                {
                    product_name: fingerprint,
                }
                if fingerprint is not None
                else {}
            ),
        )

        return persistent_resolver(
            product_name,
            _relative_product_path(
                working_dir=working_dir,
                product=product,
            ),
        )

    def product_dependency(
        self,
        dependency: PlannedProductDependency,
        *,
        required_fingerprint: ProductFingerprint | None,
    ) -> ProductState:
        """
        Resolve persistent state for one bound cross-artifact product.

        The dependency must belong by identity to the supplied BuildPlan.

        Producer identity is taken from the dependency's ProductRef rather
        than from the consumer BuildPlan. The already-planned dependency
        path determines the producer stage working directory.

        Only the requested producer product is evaluated. No producer
        BuildPlan is constructed and no downstream producer product is
        inspected.
        """

        _validate_product_dependency(
            self._product_dependencies,
            dependency,
        )

        product_ref = dependency.product_ref
        working_dir = dependency.path.parent

        persistent_resolver = create_product_state_resolver(
            working_dir=working_dir,
            artifact_id=product_ref.artifact,
            model_name=product_ref.model,
            realization=product_ref.realization,
            stage_name=product_ref.stage,
            required_fingerprints=(
                {
                    product_ref.product: required_fingerprint,
                }
                if required_fingerprint is not None
                else {}
            ),
        )

        return persistent_resolver(
            product_ref.product,
            _relative_dependency_path(
                working_dir=working_dir,
                dependency=dependency,
            ),
        )


# =========================================================
# Resolver construction
# =========================================================


def create_execution_state_resolver(
    build_plan: BuildPlan,
    *,
    required_fingerprint: RequiredFingerprintResolver,
) -> ExecutionProductStateResolver:
    """
    Create a product-state resolver for one realized build plan.

    The returned resolver remains callable with a PlannedStage and logical
    product identity for existing execution planning.

    Requested stages must belong to the supplied BuildPlan. Requested
    products must be declared by the requested stage.

    Bound cross-artifact product dependencies may additionally be resolved
    through ExecutionProductStateResolver.product_dependency. Such
    dependencies must belong to the supplied BuildPlan.

    Stage working-directory semantics match StageContext construction:
    stages with products use the common parent directory of their realized
    product paths, while stages without products use the artifact directory.

    Cross-artifact dependencies use the parent directory of their
    already-planned persistent product path.

    Expected completion identity for stage products is derived from the
    supplied BuildPlan and requested PlannedStage. Expected completion
    identity for cross-artifact dependencies is derived from the concrete
    producer ProductRef retained by the planned dependency.

    Persistent evidence gathering and semantic ProductState evaluation
    are delegated to create_product_state_resolver.
    """

    return ExecutionProductStateResolver(
        build_plan,
        required_fingerprint=required_fingerprint,
    )


# =========================================================
# Stage validation
# =========================================================


def _validate_stage(
    stages: tuple[PlannedStage, ...],
    stage: PlannedStage,
) -> None:
    """
    Require the requested stage to belong to the realized build plan.

    Identity rather than value equality is used deliberately. A
    structurally equivalent stage originating from another BuildPlan is
    not part of this realized workflow.
    """

    if not any(candidate is stage for candidate in stages):
        raise ValueError(f"Stage does not belong to build plan: {stage.name!r}")


# =========================================================
# Product dependency validation
# =========================================================


def _validate_product_dependency(
    dependencies: tuple[PlannedProductDependency, ...],
    dependency: PlannedProductDependency,
) -> None:
    """
    Require a product dependency to belong to the realized build plan.

    Identity rather than value equality is used deliberately. A
    structurally equivalent dependency originating from another BuildPlan
    is not part of this realized workflow.
    """

    if not any(candidate is dependency for candidate in dependencies):
        raise ValueError(
            "Product dependency does not belong to build plan: "
            f"{dependency.product_ref.model}."
            f"{dependency.product_ref.stage}."
            f"{dependency.product_ref.product}"
        )


# =========================================================
# Product resolution
# =========================================================


def _find_product(
    stage: PlannedStage,
    product_name: str,
) -> PlannedProduct:
    """
    Return one product declared by the requested realized stage.
    """

    for product in stage.products:
        if product.name == product_name:
            return product

    raise ValueError(f"Product {product_name!r} is not declared by stage {stage.name!r}")


# =========================================================
# Filesystem resolution
# =========================================================


def _stage_working_directory(
    *,
    artifact_dir: Path,
    stage: PlannedStage,
) -> Path:
    """
    Determine the working directory for one realized stage.

    These semantics intentionally match StageContext construction.

    A stage with declared products executes from the common parent
    directory containing those products.

    A stage without declared products executes from the artifact
    directory.
    """

    if not stage.products:
        return artifact_dir

    parents = [product.path.parent for product in stage.products]

    return Path(
        os.path.commonpath(
            parents,
        )
    )


def _relative_product_path(
    *,
    working_dir: Path,
    product: PlannedProduct,
) -> Path:
    """
    Return a realized product path relative to its stage working directory.

    Persistent evidence gathering interprets product_path relative to the
    supplied stage working directory.
    """

    try:
        return product.path.relative_to(
            working_dir,
        )

    except ValueError as exc:
        raise ValueError(
            f"Product {product.name!r} at "
            f"{product.path} "
            f"is not contained by stage working directory "
            f"{working_dir}"
        ) from exc


def _relative_dependency_path(
    *,
    working_dir: Path,
    dependency: PlannedProductDependency,
) -> Path:
    """
    Return a bound producer product path relative to its working directory.

    Persistent evidence gathering interprets product_path relative to the
    supplied producer stage working directory.
    """

    try:
        return dependency.path.relative_to(
            working_dir,
        )

    except ValueError as exc:
        product_ref = dependency.product_ref

        raise ValueError(
            f"Product dependency "
            f"{product_ref.model}."
            f"{product_ref.stage}."
            f"{product_ref.product} at "
            f"{dependency.path} "
            f"is not contained by producer stage working directory "
            f"{working_dir}"
        ) from exc


# =========================================================
# Exports
# =========================================================


__all__ = [
    "ExecutionProductStateResolver",
    "RequiredFingerprintResolver",
    "create_execution_state_resolver",
]
