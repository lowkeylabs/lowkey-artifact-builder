"""
Artifact build planning.

This module converts configured artifact realizations and declarative
model definitions into concrete BuildPlan instances.

Planning resolves realization configuration and filesystem locations but
does not modify filesystem products or materialize external inputs.

The realization-specific Resolver created during planning is retained by
the BuildPlan and is the authoritative configuration source throughout
execution.
"""
# File: src/lowkey_artifact_builder/engine/plan.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path

from lowkey_artifact_builder.config import (
    Resolver,
    get_realization_names,
    get_resolver,
)
from lowkey_artifact_builder.engine.product_resolver import ProductResolver
from lowkey_artifact_builder.engine.specs import (
    BuildPlan,
    PlannedInput,
    PlannedProduct,
    PlannedStage,
)
from lowkey_artifact_builder.model import (
    ModelNotFoundError,
    ModelSpec,
    StageSpec,
    build_model_registry,
)

# =========================================================
# Errors
# =========================================================


class BuildPlanError(RuntimeError):
    """
    Raised when an artifact build plan cannot be constructed.
    """


# =========================================================
# Public interface
# =========================================================


def create_build_plan(
    artifact_id: str,
    *,
    realization: str | None = None,
    project_root: Path | None = None,
) -> BuildPlan:
    """
    Construct the build plan for one configured artifact realization.

    Configuration is resolved once for the selected realization. The
    resulting Resolver is retained by the BuildPlan and later supplied
    unchanged to every StageContext created during execution.

    When realization is omitted, configuration resolution determines
    the realization. Legacy single-realization artifact configuration
    resolves to the implicit realization named "default".
    """

    root = project_root if project_root is not None else Path.cwd()

    resolver = get_resolver(
        artifact_id,
        realization=realization,
        project_root=root,
    )

    model_name = resolver("model")

    if not isinstance(
        model_name,
        str,
    ):
        raise BuildPlanError("Artifact model must resolve to a string.")

    realization_name = resolver("realization")

    if not isinstance(
        realization_name,
        str,
    ):
        raise BuildPlanError("Artifact realization must resolve to a string.")

    registry = build_model_registry()

    try:
        model = registry.get_model(model_name)

    except ModelNotFoundError as exc:
        raise BuildPlanError(f"unknown model {model_name!r}") from exc

    product_resolver = ProductResolver(
        project_root=root,
    )

    artifact_dir = product_resolver.artifact_dir(
        artifact_id,
    )

    stages = _plan_stages(
        artifact_id,
        model,
        realization_name,
        resolver,
        root,
        product_resolver,
    )

    return BuildPlan(
        artifact_id=artifact_id,
        model=model,
        realization_name=realization_name,
        resolver=resolver,
        project_root=root,
        artifact_dir=artifact_dir,
        stages=stages,
    )


def create_build_plans(
    artifact_id: str,
    *,
    project_root: Path | None = None,
) -> tuple[BuildPlan, ...]:
    """
    Construct build plans for every realization of one artifact.

    Explicitly configured realizations are planned in artifact.toml
    declaration order.

    Legacy single-realization artifact configuration produces exactly
    one plan for the implicit realization named "default".

    Individual realization planning remains owned by
    create_build_plan().
    """

    root = project_root if project_root is not None else Path.cwd()

    realization_names = get_realization_names(
        artifact_id,
        project_root=root,
    )

    return tuple(
        create_build_plan(
            artifact_id,
            realization=realization_name,
            project_root=root,
        )
        for realization_name in realization_names
    )


# =========================================================
# Stage planning
# =========================================================


def _plan_stages(
    artifact_id: str,
    model: ModelSpec,
    realization_name: str,
    resolver: Resolver,
    project_root: Path,
    product_resolver: ProductResolver,
) -> tuple[PlannedStage, ...]:
    """
    Materialize participating model stages for one artifact realization.

    Stage parameter values are intentionally not copied into the plan.
    StageSpec declares which parameters a stage normally consumes, and
    the BuildPlan retains the authoritative realization Resolver.
    """

    participating = tuple(
        stage
        for stage in model.stages
        if _stage_participates(
            stage,
            resolver,
        )
    )

    participating_names = {stage.name for stage in participating}

    for stage in participating:
        _validate_stage_dependencies(
            stage,
            participating_names,
        )

    return tuple(
        _plan_stage(
            artifact_id,
            model.name,
            realization_name,
            stage,
            resolver,
            project_root,
            product_resolver,
        )
        for stage in participating
    )


def _plan_stage(
    artifact_id: str,
    model_name: str,
    realization_name: str,
    stage: StageSpec,
    resolver: Resolver,
    project_root: Path,
    product_resolver: ProductResolver,
) -> PlannedStage:
    """
    Materialize one declarative stage for an artifact realization.

    Filesystem inputs and products are resolved to concrete paths.
    Configuration parameter values remain in the realization Resolver.
    """

    artifact_dir = product_resolver.artifact_dir(
        artifact_id,
    )

    inputs = _plan_stage_inputs(
        artifact_id,
        stage,
        resolver,
        project_root,
        artifact_dir,
    )

    products = _plan_stage_products(
        artifact_id=artifact_id,
        model_name=model_name,
        realization_name=realization_name,
        stage=stage,
        product_resolver=product_resolver,
    )

    return PlannedStage(
        spec=stage,
        inputs=inputs,
        products=products,
    )


# =========================================================
# Stage participation
# =========================================================


def _stage_participates(
    stage: StageSpec,
    resolver: Resolver,
) -> bool:
    """
    Return whether a stage participates in the artifact build.

    Stages without feature requirements always participate.

    A stage with feature requirements participates only when every
    required feature resolves to a truthy value.
    """

    for feature in stage.requires_features:
        if not resolver(feature):
            return False

    return True


# =========================================================
# Dependency validation
# =========================================================


def _validate_stage_dependencies(
    stage: StageSpec,
    participating_names: set[str],
) -> None:
    """
    Validate that all dependencies of a participating stage also
    participate.
    """

    missing = tuple(
        dependency for dependency in stage.dependencies if dependency not in participating_names
    )

    if not missing:
        return

    names = ", ".join(repr(name) for name in missing)

    raise BuildPlanError(f"Stage {stage.name!r} depends on non-participating stage(s): {names}.")


# =========================================================
# External inputs
# =========================================================


def _plan_stage_inputs(
    artifact_id: str,
    stage: StageSpec,
    resolver: Resolver,
    project_root: Path,
    artifact_dir: Path,
) -> tuple[PlannedInput, ...]:
    """
    Materialize external filesystem input locations for one stage.

    Source paths are resolved relative to the project root.

    Artifact-owned paths are resolved relative to the artifact
    directory.

    Planning does not copy or modify the external resources.
    """

    return tuple(
        _plan_input(
            artifact_id,
            input_spec,
            resolver,
            project_root,
            artifact_dir,
        )
        for input_spec in stage.inputs
    )


def _plan_input(
    artifact_id: str,
    input_spec,
    resolver: Resolver,
    project_root: Path,
    artifact_dir: Path,
) -> PlannedInput:
    """
    Materialize one external filesystem input.
    """

    value = resolver(input_spec.parameter)

    if not isinstance(
        value,
        str,
    ):
        raise BuildPlanError(
            f"Input parameter "
            f"{input_spec.parameter!r} "
            f"for artifact {artifact_id!r} "
            "must resolve to a string path."
        )

    source_path = Path(value)

    if not source_path.is_absolute():
        source_path = project_root / source_path

    path = artifact_dir / input_spec.path

    return PlannedInput(
        spec=input_spec,
        source_path=source_path,
        path=path,
    )


# =========================================================
# Products
# =========================================================


def _plan_stage_products(
    *,
    artifact_id: str,
    model_name: str,
    realization_name: str,
    stage: StageSpec,
    product_resolver: ProductResolver,
) -> tuple[PlannedProduct, ...]:
    """
    Materialize persistent product locations for one stage.

    Product paths declared by ProductSpec are relative to their
    producing stage. ProductResolver owns the canonical filesystem
    hierarchy containing those stage-relative paths.
    """

    return tuple(
        PlannedProduct(
            spec=product,
            path=product_resolver.product_path(
                artifact=artifact_id,
                model=model_name,
                realization=realization_name,
                stage=stage,
                product=product,
            ),
        )
        for product in stage.products
    )


# =========================================================
# Exports
# =========================================================


__all__ = [
    "BuildPlanError",
    "create_build_plan",
]
