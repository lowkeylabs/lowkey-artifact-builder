"""
Artifact build planning.

This module converts configured artifacts and declarative model
definitions into concrete BuildPlan instances.

Planning resolves artifact configuration and filesystem locations but
does not modify filesystem products or materialize external inputs.

The artifact-specific Resolver created during planning is retained by
the BuildPlan and is the authoritative configuration source throughout
execution.
"""

from __future__ import annotations

from pathlib import Path

from lowkey_artifact_builder.config import (
    Resolver,
    get_resolver,
)
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
    project_root: Path | None = None,
) -> BuildPlan:
    """
    Construct the build plan for one configured artifact.

    Configuration is resolved once for the artifact. The resulting
    Resolver is retained by the BuildPlan and later supplied unchanged
    to every StageContext created during execution.
    """

    root = project_root if project_root is not None else Path.cwd()

    resolver = get_resolver(
        artifact_id,
        project_root=root,
    )

    model_name = resolver("model")

    if not isinstance(
        model_name,
        str,
    ):
        raise BuildPlanError("Artifact model must resolve to a string.")

    registry = build_model_registry()

    try:
        model = registry.get_model(model_name)

    except ModelNotFoundError as exc:
        raise BuildPlanError(f"unknown model {model_name!r}") from exc

    artifact_dir = root / "artifacts" / artifact_id

    stages = _plan_stages(
        artifact_id,
        model,
        resolver,
        root,
        artifact_dir,
    )

    return BuildPlan(
        artifact_id=artifact_id,
        model=model,
        resolver=resolver,
        project_root=root,
        artifact_dir=artifact_dir,
        stages=stages,
    )


# =========================================================
# Stage planning
# =========================================================


def _plan_stages(
    artifact_id: str,
    model: ModelSpec,
    resolver: Resolver,
    project_root: Path,
    artifact_dir: Path,
) -> tuple[PlannedStage, ...]:
    """
    Materialize participating model stages for an artifact.

    Stage parameter values are intentionally not copied into the plan.
    StageSpec declares which parameters a stage normally consumes, and
    the BuildPlan retains the authoritative artifact Resolver.
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
            stage,
            resolver,
            project_root,
            artifact_dir,
        )
        for stage in participating
    )


def _plan_stage(
    artifact_id: str,
    stage: StageSpec,
    resolver: Resolver,
    project_root: Path,
    artifact_dir: Path,
) -> PlannedStage:
    """
    Materialize one declarative stage.

    Filesystem inputs and products are resolved to concrete paths.
    Configuration parameter values remain in the artifact Resolver.
    """

    inputs = _plan_stage_inputs(
        artifact_id,
        stage,
        resolver,
        project_root,
        artifact_dir,
    )

    products = _plan_stage_products(
        stage,
        artifact_dir,
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
    stage: StageSpec,
    artifact_dir: Path,
) -> tuple[PlannedProduct, ...]:
    """
    Materialize persistent product locations for one stage.

    Product paths declared by StageSpec are relative to the artifact
    directory.
    """

    return tuple(
        PlannedProduct(
            spec=product,
            path=(artifact_dir / product.path),
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
