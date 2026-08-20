"""
Artifact build planning.

This module converts a configured artifact and its declarative model
definition into a concrete build plan.

Planning is read-only. It resolves configuration, determines the model
workflow, validates stage dependencies, resolves stage parameters,
materializes external filesystem input paths, and materializes product
paths.

Planning does not create directories, copy inputs, execute stages, or
modify build products.
"""

from __future__ import annotations

from pathlib import Path

from lowkey_artifact_builder.config import (
    ConfigError,
    get_resolver,
)
from lowkey_artifact_builder.model import (
    InputSpec,
    ModelNotFoundError,
    ModelSpec,
    ProductSpec,
    StageSpec,
    build_model_registry,
)

from .specs import (
    BuildPlan,
    PlannedInput,
    PlannedProduct,
    PlannedStage,
    ResolvedParameter,
)

# =========================================================
# Errors
# =========================================================


class BuildPlanError(RuntimeError):
    """
    Raised when a valid build plan cannot be constructed.
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
    Construct a concrete build plan for an artifact.

    Configuration is resolved using the normal configuration stack.
    The artifact model is then obtained from the model registry and its
    stages are materialized in declared stage order.

    External filesystem inputs are resolved to both their external
    source locations and their artifact-owned materialization
    locations.

    No filesystem resources are created, copied, or modified and no
    stages are executed.
    """

    root = project_root if project_root is not None else Path.cwd()

    root = root.resolve()

    try:
        resolver = get_resolver(
            artifact_id,
            project_root=root,
        )

        model_name = resolver("model")

    except ConfigError as exc:
        raise BuildPlanError(f"Cannot plan artifact {artifact_id!r}: {exc}") from exc

    registry = build_model_registry()

    try:
        model = registry.get_model(model_name)

    except ModelNotFoundError as exc:
        raise BuildPlanError(
            f"Artifact {artifact_id!r} references unknown model {model_name!r}."
        ) from exc

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
    resolver,
    project_root: Path,
    artifact_dir: Path,
) -> tuple[PlannedStage, ...]:
    """
    Materialize the stages participating in an artifact build.

    For the current model system, stages without required features
    always participate.

    Feature-dependent stage selection is intentionally isolated here so
    feature resolution can be added without changing the public build
    planning interface.
    """

    participating = tuple(
        stage
        for stage in model.stages
        if _stage_participates(
            stage,
            resolver,
        )
    )

    _validate_dependencies(
        artifact_id,
        participating,
    )

    planned: list[PlannedStage] = []

    for stage in participating:
        planned.append(
            _plan_stage(
                artifact_id,
                stage,
                resolver,
                project_root,
                artifact_dir,
            )
        )

    return tuple(planned)


def _stage_participates(
    stage: StageSpec,
    resolver,
) -> bool:
    """
    Determine whether a stage participates in the artifact workflow.

    Stages without required features always participate.

    Feature resolution has not yet been introduced into the artifact
    configuration subsystem. A feature-dependent stage therefore does
    not currently participate unless all of its required feature names
    resolve to truthy configuration values.
    """

    if not stage.requires_features:
        return True

    for feature in stage.requires_features:
        try:
            enabled = resolver(feature)

        except ConfigError:
            return False

        if not enabled:
            return False

    return True


def _plan_stage(
    artifact_id: str,
    stage: StageSpec,
    resolver,
    project_root: Path,
    artifact_dir: Path,
) -> PlannedStage:
    """
    Materialize one stage.

    External inputs, non-filesystem parameters, and declared products
    are materialized independently so execution receives a complete
    description of the resources required by the stage.
    """

    inputs = _resolve_stage_inputs(
        artifact_id,
        stage,
        resolver,
        project_root,
        artifact_dir,
    )

    parameters = _resolve_stage_parameters(
        artifact_id,
        stage,
        resolver,
    )

    products = tuple(
        _plan_product(
            product,
            artifact_dir,
        )
        for product in stage.products
    )

    return PlannedStage(
        spec=stage,
        inputs=inputs,
        parameters=parameters,
        products=products,
    )


# =========================================================
# Input resolution
# =========================================================


def _resolve_stage_inputs(
    artifact_id: str,
    stage: StageSpec,
    resolver,
    project_root: Path,
    artifact_dir: Path,
) -> tuple[PlannedInput, ...]:
    """
    Resolve all external filesystem inputs consumed by a stage.

    Each InputSpec identifies:

        parameter
            The resolved configuration value containing the external
            source location.

        path
            The artifact-local location at which execution will
            materialize that external resource.

    Relative external source paths are interpreted relative to the
    project root. Absolute external source paths are preserved.

    Artifact-local paths are interpreted relative to the artifact
    working directory.

    Planning computes these locations but does not require the external
    resource to exist and does not copy or otherwise materialize it.
    """

    inputs: list[PlannedInput] = []

    for input_spec in stage.inputs:
        try:
            value = resolver(input_spec.parameter)

        except ConfigError as exc:
            raise BuildPlanError(
                f"Artifact {artifact_id!r} cannot be built: "
                f"input {input_spec.name!r} required by stage "
                f"{stage.name!r} cannot be resolved from "
                f"parameter {input_spec.parameter!r}."
            ) from exc

        source_path = _resolve_input_source_path(
            artifact_id,
            stage,
            input_spec,
            value,
            project_root,
        )

        path = _resolve_input_materialization_path(
            artifact_id,
            stage,
            input_spec,
            artifact_dir,
        )

        inputs.append(
            PlannedInput(
                spec=input_spec,
                source_path=source_path,
                path=path,
            )
        )

    return tuple(inputs)


def _resolve_input_source_path(
    artifact_id: str,
    stage: StageSpec,
    input_spec: InputSpec,
    value,
    project_root: Path,
) -> Path:
    """
    Materialize one configured external input source path.

    Relative configured paths are resolved from the project root.
    Absolute configured paths are preserved.

    The path is normalized to an absolute Path without requiring the
    resource to exist.
    """

    if not isinstance(
        value,
        str | Path,
    ):
        raise BuildPlanError(
            f"Artifact {artifact_id!r} cannot be built: "
            f"input {input_spec.name!r} required by stage "
            f"{stage.name!r} must resolve from parameter "
            f"{input_spec.parameter!r} to a filesystem path, "
            f"not {type(value).__name__}."
        )

    path = Path(value).expanduser()

    if not path.is_absolute():
        path = project_root / path

    return path.resolve()


def _resolve_input_materialization_path(
    artifact_id: str,
    stage: StageSpec,
    input_spec: InputSpec,
    artifact_dir: Path,
) -> Path:
    """
    Materialize the artifact-owned path for an external input.

    InputSpec.path must be relative to the artifact working directory.
    Absolute artifact-local paths are rejected because model
    declarations must not escape or redefine artifact workspace layout.
    """

    path = Path(input_spec.path)

    if path.is_absolute():
        raise BuildPlanError(
            f"Artifact {artifact_id!r} cannot be built: "
            f"input {input_spec.name!r} required by stage "
            f"{stage.name!r} declares absolute artifact path "
            f"{input_spec.path!r}."
        )

    return (artifact_dir / path).resolve()


# =========================================================
# Parameter resolution
# =========================================================


def _resolve_stage_parameters(
    artifact_id: str,
    stage: StageSpec,
    resolver,
) -> tuple[ResolvedParameter, ...]:
    """
    Resolve all non-filesystem parameters consumed by a stage.

    Failure to resolve any declared stage parameter makes the artifact
    unbuildable and therefore prevents construction of the build plan.

    Filesystem inputs are resolved separately from StageSpec.inputs.
    """

    parameters: list[ResolvedParameter] = []

    for name in stage.parameters:
        try:
            value = resolver(name)

            source = resolver.source(name)

        except ConfigError as exc:
            raise BuildPlanError(
                f"Artifact {artifact_id!r} cannot be built: "
                f"parameter {name!r} required by stage "
                f"{stage.name!r} cannot be resolved."
            ) from exc

        parameters.append(
            ResolvedParameter(
                name=name,
                value=value,
                source=source,
            )
        )

    return tuple(parameters)


# =========================================================
# Product planning
# =========================================================


def _plan_product(
    product: ProductSpec,
    artifact_dir: Path,
) -> PlannedProduct:
    """
    Materialize a declared product path for an artifact.

    Product paths are interpreted relative to the artifact working
    directory.
    """

    path = artifact_dir / product.path

    return PlannedProduct(
        spec=product,
        path=path,
    )


# =========================================================
# Dependency validation
# =========================================================


def _validate_dependencies(
    artifact_id: str,
    stages: tuple[StageSpec, ...],
) -> None:
    """
    Validate dependencies among participating stages.

    Every dependency must refer to another participating stage and must
    occur earlier in declared stage order.
    """

    names = {stage.name for stage in stages}

    completed: set[str] = set()

    for stage in stages:
        for dependency in stage.dependencies:
            if dependency not in names:
                raise BuildPlanError(
                    f"Artifact {artifact_id!r} cannot be planned: "
                    f"stage {stage.name!r} depends on "
                    f"non-participating stage {dependency!r}."
                )

            if dependency not in completed:
                raise BuildPlanError(
                    f"Artifact {artifact_id!r} cannot be planned: "
                    f"stage {stage.name!r} depends on "
                    f"{dependency!r}, which does not precede it "
                    "in the model workflow."
                )

        completed.add(stage.name)


__all__ = [
    "BuildPlanError",
    "create_build_plan",
]
