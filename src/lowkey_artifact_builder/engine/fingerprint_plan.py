"""
Build-plan fingerprint resolution.

Build-plan fingerprint resolution derives the fingerprint required by each
realized stage from its operation identity, resolved parameter values,
external input contents, cross-artifact product dependency contents, and
the required fingerprints of its realized dependency stages.

Stage parameters are declared by StageSpec and resolved through the
BuildPlan's authoritative realization Resolver.

External filesystem inputs and cross-artifact product dependencies
contribute content fingerprints rather than filesystem paths or timestamps,
so equivalent content has equivalent provenance across workspaces.

Dependency fingerprints propagate required build context through the
realized stage graph without inspecting persistent products or completion
metadata.
"""
# File: src/lowkey_artifact_builder/engine/fingerprint_plan.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import hashlib
from collections.abc import Callable
from pathlib import Path

from .freshness import (
    ProductFingerprint,
    create_product_fingerprint,
)
from .specs import (
    BuildPlan,
    PlannedProductDependency,
    PlannedStage,
)

# =========================================================
# Constants
# =========================================================


_CONTENT_FINGERPRINT_ALGORITHM = "sha256"

type ProductDependencyFingerprintResolver = Callable[
    [PlannedProductDependency],
    ProductFingerprint,
]

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
        cross-artifact product dependencies, plus required fingerprints
        of declared dependency stages.

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


def create_product_dependency_fingerprint_resolver(
    build_plan: BuildPlan,
) -> ProductDependencyFingerprintResolver:
    """
    Create a required-fingerprint resolver for products of one producer plan.

    The resolver maps a bound cross-artifact product dependency to the
    required build-context fingerprint of the realized stage that produces
    that product.

    The supplied BuildPlan is authoritative for producer artifact, model,
    realization, realized stages, declared products, and required stage
    fingerprints.

    Resolving an intermediate product selects its producing stage directly.
    Downstream producer stages therefore do not participate in the resolved
    fingerprint except insofar as they are independently present in the
    producer BuildPlan.

    The dependency must identify the same artifact, model, and realization
    as the supplied producer BuildPlan. Its declared stage must exist in the
    realized plan and must declare the requested product.
    """

    fingerprints = create_required_fingerprints(
        build_plan,
    )

    def resolve(
        dependency: PlannedProductDependency,
        /,
    ) -> ProductFingerprint:
        binding = dependency.binding
        required = binding.dependency

        if binding.artifact != build_plan.artifact_id:
            raise ValueError(
                f"Product dependency artifact {binding.artifact!r} "
                f"does not match producer build plan artifact "
                f"{build_plan.artifact_id!r}"
            )

        if required.model != build_plan.model_name:
            raise ValueError(
                f"Product dependency model {required.model!r} "
                f"does not match producer build plan model "
                f"{build_plan.model_name!r}"
            )

        if binding.realization != build_plan.realization_name:
            raise ValueError(
                f"Product dependency realization "
                f"{binding.realization!r} does not match producer "
                f"build plan realization "
                f"{build_plan.realization_name!r}"
            )

        stage = next(
            (stage for stage in build_plan.stages if stage.name == required.stage),
            None,
        )

        if stage is None:
            raise ValueError(
                f"Producer stage {required.stage!r} required by "
                f"product dependency is not realized by build plan"
            )

        if not any(product.name == required.product for product in stage.products):
            raise ValueError(
                f"Product {required.product!r} is not declared by producer stage {required.stage!r}"
            )

        try:
            return fingerprints[stage.name]
        except KeyError as exc:
            raise ValueError(
                f"Required fingerprint for producer stage {stage.name!r} is unavailable"
            ) from exc

    return resolve


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

    inputs.update(
        _resolve_product_dependency_fingerprints(
            build_plan=build_plan,
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
# Product dependency resolution
# =========================================================


def _resolve_product_dependency_fingerprints(
    *,
    build_plan: BuildPlan,
    stage: PlannedStage,
) -> dict[str, str]:
    """
    Resolve content fingerprints of cross-artifact product dependencies.

    Only product dependencies explicitly declared by the realized stage
    participate in its fingerprint.

    Planned dependency paths identify persistent producer products, but
    the paths themselves do not participate in provenance. Product
    contents are hashed directly so equivalent producer products have
    equivalent provenance across workspaces.

    A required dependency that is not present in the BuildPlan fails
    rather than silently producing incomplete provenance.
    """

    inputs: dict[str, str] = {}

    for dependency in stage.spec.product_dependencies:
        planned_dependency = next(
            (
                planned
                for planned in build_plan.planned_product_dependencies
                if planned.binding.dependency == dependency
            ),
            None,
        )

        if planned_dependency is None:
            identity = f"{dependency.model}/{dependency.stage}/{dependency.product}"

            raise ValueError(
                f"Planned product dependency {identity!r} "
                f"required by stage {stage.name!r} is unavailable"
            )

        identity = f"{dependency.model}.{dependency.stage}.{dependency.product}"

        inputs[f"product:{identity}"] = _format_fingerprint(
            _fingerprint_file(
                planned_dependency.path,
            )
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
    "ProductDependencyFingerprintResolver",
    "create_product_dependency_fingerprint_resolver",
    "create_required_fingerprints",
]
