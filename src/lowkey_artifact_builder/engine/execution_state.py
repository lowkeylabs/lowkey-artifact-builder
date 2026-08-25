"""
Execution product-state resolution.

Execution product-state resolution adapts realized build-plan stages and
products to persistent product-state evaluation.

The resolver validates that requested stages and products belong to the
realized BuildPlan, determines the producing stage working directory using
the same semantics as stage-context construction, resolves the fingerprint
required by the current build context, and delegates persistent evidence
gathering and ProductState evaluation to the persistent product-state
resolver.

Expected completion identity is derived from the authoritative BuildPlan
and realized PlannedStage and supplied to persistent evidence resolution.
Completion metadata therefore cannot prove reuse unless it belongs to the
artifact, model, realization, and stage whose persistent products are being
evaluated.

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


type ExecutionProductStateResolver = Callable[
    [
        PlannedStage,
        str,
    ],
    ProductState,
]


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

    The returned resolver accepts the PlannedStage and logical product
    identity expected by execution planning.

    Requested stages must belong to the supplied BuildPlan. Requested
    products must be declared by the requested stage.

    Stage working-directory semantics match StageContext construction:
    stages with products use the common parent directory of their
    realized product paths, while stages without products use the
    artifact directory.

    The required build-context fingerprint is resolved independently for
    each requested stage.

    Expected completion identity is derived from the supplied BuildPlan
    and requested PlannedStage. Persistent completion metadata must
    identify the same artifact, model, realization, and stage before it
    can prove successful completion for the requested product.

    Persistent evidence gathering and semantic ProductState evaluation
    are delegated to create_product_state_resolver.
    """

    stages = tuple(
        build_plan.stages,
    )

    def resolve(
        stage: PlannedStage,
        product_name: str,
    ) -> ProductState:
        _validate_stage(
            stages,
            stage,
        )

        product = _find_product(
            stage,
            product_name,
        )

        working_dir = _stage_working_directory(
            artifact_dir=build_plan.artifact_dir,
            stage=stage,
        )

        fingerprint = required_fingerprint(
            stage,
        )

        persistent_resolver = create_product_state_resolver(
            working_dir=working_dir,
            artifact_id=build_plan.artifact_id,
            model_name=build_plan.model_name,
            realization=build_plan.realization_name,
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

    return resolve


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


# =========================================================
# Exports
# =========================================================


__all__ = [
    "ExecutionProductStateResolver",
    "RequiredFingerprintResolver",
    "create_execution_state_resolver",
]
