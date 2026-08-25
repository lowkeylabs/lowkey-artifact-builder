"""
Build-plan fingerprint resolution.

Build-plan fingerprint resolution derives the fingerprint required by each
realized stage from its operation identity, resolved parameter values,
external input contents, and the required fingerprints of its realized
dependency stages.

Stage parameters are declared by StageSpec and resolved through the
BuildPlan's authoritative realization Resolver.

External filesystem inputs contribute content fingerprints rather than
filesystem paths or timestamps, so equivalent content has equivalent
provenance across workspaces.

Dependency fingerprints propagate required build context through the
realized stage graph without inspecting persistent products or completion
metadata.
"""
# File: src/lowkey_artifact_builder/engine/fingerprint_plan.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import hashlib
from pathlib import Path

from .freshness import (
    ProductFingerprint,
    create_product_fingerprint,
)
from .specs import (
    BuildPlan,
    PlannedStage,
)

# =========================================================
# Constants
# =========================================================


_CONTENT_FINGERPRINT_ALGORITHM = "sha256"


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
        Content fingerprints of declared external filesystem inputs and
        required fingerprints of declared dependency stages.

    Filesystem destinations and timestamps do not participate in
    fingerprint generation, so equivalent build contexts remain portable
    across workspaces.
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

    inputs.update(
        _resolve_external_input_fingerprints(
            stage=stage,
        )
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

    Dependency identities occupy an explicit namespace so they cannot
    collide with logical external-input identities.

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

        inputs[f"dependency:{dependency}"] = _format_fingerprint(
            fingerprint,
        )

    return inputs


# =========================================================
# External input resolution
# =========================================================


def _resolve_external_input_fingerprints(
    *,
    stage: PlannedStage,
) -> dict[str, str]:
    """
    Resolve content fingerprints of one stage's external inputs.

    External inputs are identified by their logical input names rather
    than filesystem paths. Their contents are hashed directly so moving
    equivalent input data between workspaces does not change provenance.

    Missing or unreadable input files fail rather than producing synthetic
    provenance.
    """

    return {
        f"external:{planned_input.name}": _format_fingerprint(
            _fingerprint_file(
                planned_input.path,
            )
        )
        for planned_input in stage.inputs
    }


def _fingerprint_file(
    path: Path,
) -> ProductFingerprint:
    """
    Create a deterministic content fingerprint for one external file.

    File contents are streamed into SHA-256 so fingerprint calculation does
    not require loading the complete input into memory.

    Filesystem metadata such as path, modification time, ownership, and
    permissions does not participate in the fingerprint.
    """

    digest = hashlib.sha256()

    with path.open(
        "rb",
    ) as stream:
        while chunk := stream.read(
            1024 * 1024,
        ):
            digest.update(
                chunk,
            )

    return ProductFingerprint(
        algorithm=_CONTENT_FINGERPRINT_ALGORITHM,
        value=digest.hexdigest(),
    )


# =========================================================
# Fingerprint representation
# =========================================================


def _format_fingerprint(
    fingerprint: ProductFingerprint,
) -> str:
    """
    Return the stable serialized identity of one fingerprint.
    """

    return f"{fingerprint.algorithm}:{fingerprint.value}"


# =========================================================
# Exports
# =========================================================


__all__ = [
    "create_required_fingerprints",
]
