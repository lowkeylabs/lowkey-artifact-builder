"""
Build-plan fingerprint resolution.

Build-plan fingerprint resolution derives the fingerprint required by each
realized stage from its operation identity, resolved parameter values, and
the required fingerprints of its realized dependency stages.

Stage parameters are declared by StageSpec and resolved through the
BuildPlan's authoritative realization Resolver.

Dependency fingerprints propagate required build context through the
realized stage graph without inspecting persistent products or completion
metadata.

External filesystem input content provenance is intentionally outside this
module's current responsibility and is introduced separately.
"""
# File: src/lowkey_artifact_builder/engine/fingerprint_plan.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from .freshness import (
    ProductFingerprint,
    create_product_fingerprint,
)
from .specs import (
    BuildPlan,
    PlannedStage,
)

# =========================================================
# Required fingerprint construction
# =========================================================


def create_required_fingerprints(
    build_plan: BuildPlan,
) -> dict[str, ProductFingerprint]:
    """
    Create required fingerprints for every realized stage.

    Stages are processed in realized build-plan order. The BuildPlan is
    expected to preserve dependency order, so fingerprints required by a
    stage's declared dependencies must already have been calculated.

    Each stage fingerprint contains:

    operation
        The realized stage identity.

    parameters
        Values of parameters explicitly declared by the StageSpec,
        resolved through the BuildPlan's authoritative Resolver.

    inputs
        Required fingerprints of declared dependency stages.

    Filesystem destinations do not participate in fingerprint generation,
    so equivalent build contexts remain portable across workspaces.

    External filesystem input content is not yet represented in the
    fingerprint. That provenance is introduced separately.
    """

    fingerprints: dict[str, ProductFingerprint] = {}

    for stage in build_plan.stages:
        fingerprints[stage.name] = _create_stage_fingerprint(
            build_plan=build_plan,
            stage=stage,
            fingerprints=fingerprints,
        )

    return fingerprints


# =========================================================
# Stage fingerprint construction
# =========================================================


def _create_stage_fingerprint(
    *,
    build_plan: BuildPlan,
    stage: PlannedStage,
    fingerprints: dict[str, ProductFingerprint],
) -> ProductFingerprint:
    """
    Create the required fingerprint for one realized stage.
    """

    parameters = _resolve_stage_parameters(
        build_plan=build_plan,
        stage=stage,
    )

    inputs = _resolve_dependency_fingerprints(
        stage=stage,
        fingerprints=fingerprints,
    )

    return create_product_fingerprint(
        operation=stage.name,
        parameters=parameters,
        inputs=inputs,
    )


# =========================================================
# Parameter resolution
# =========================================================


def _resolve_stage_parameters(
    *,
    build_plan: BuildPlan,
    stage: PlannedStage,
) -> dict[str, object]:
    """
    Resolve values of parameters declared by one realized stage.

    Only parameters explicitly declared by StageSpec participate in the
    stage fingerprint. Unrelated realization configuration therefore
    cannot invalidate the stage.
    """

    return {
        parameter: build_plan.resolver(
            parameter,
        )
        for parameter in stage.spec.parameters
    }


# =========================================================
# Dependency resolution
# =========================================================


def _resolve_dependency_fingerprints(
    *,
    stage: PlannedStage,
    fingerprints: dict[str, ProductFingerprint],
) -> dict[str, str]:
    """
    Resolve required fingerprints of one stage's dependencies.

    Dependency identity and complete fingerprint identity are represented
    deterministically in the input namespace.

    Missing dependency fingerprints indicate that the realized BuildPlan
    is not ordered consistently with its dependency graph and therefore
    fail rather than silently producing incomplete provenance.
    """

    inputs: dict[str, str] = {}

    for dependency in stage.spec.dependencies:
        try:
            fingerprint = fingerprints[dependency]
        except KeyError as exc:
            raise ValueError(
                f"Required fingerprint for dependency "
                f"{dependency!r} of stage {stage.name!r} "
                f"is unavailable"
            ) from exc

        inputs[dependency] = f"{fingerprint.algorithm}:{fingerprint.value}"

    return inputs


# =========================================================
# Exports
# =========================================================


__all__ = [
    "create_required_fingerprints",
]
