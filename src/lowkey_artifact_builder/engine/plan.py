"""
Artifact build planning.

This module converts a configured artifact and its declarative model
definition into a concrete build plan.

Planning is read-only. It resolves configuration, determines the model
workflow, validates stage dependencies, resolves stage parameters, and
materializes product paths.

Planning does not create directories, execute stages, or modify build
products.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from lowkey_artifact_builder.config import (
    ConfigError,
    get_resolver,
)
from lowkey_artifact_builder.model import (
    ModelSpec,
    ProductSpec,
    StageSpec,
    build_model_registry,
)

# =========================================================
# Errors
# =========================================================


class BuildPlanError(RuntimeError):
    """
    Raised when a valid build plan cannot be constructed.
    """


# =========================================================
# Resolved parameters
# =========================================================


@dataclass(
    frozen=True,
    slots=True,
)
class ResolvedParameter:
    """
    A resolved parameter consumed by a planned stage.

    Source identifies the configuration provenance reported by the
    resolver, such as master, model, workspace, artifact, or derived.
    """

    name: str

    value: Any

    source: str


# =========================================================
# Planned products
# =========================================================


@dataclass(
    frozen=True,
    slots=True,
)
class PlannedProduct:
    """
    A filesystem product materialized for an artifact build.

    Path is the concrete path at which the stage product is expected to
    exist.

    The original ProductSpec is retained so callers still have access
    to the product's declarative name and description.
    """

    spec: ProductSpec

    path: Path

    @property
    def name(
        self,
    ) -> str:
        """
        Return the declarative product name.
        """

        return self.spec.name

    @property
    def description(
        self,
    ) -> str:
        """
        Return the declarative product description.
        """

        return self.spec.description


# =========================================================
# Planned stages
# =========================================================


@dataclass(
    frozen=True,
    slots=True,
)
class PlannedStage:
    """
    One stage materialized for an artifact build.

    The original StageSpec is retained as the declarative definition.
    Parameters and products contain the artifact-specific resolved
    values needed to execute that stage.
    """

    spec: StageSpec

    parameters: tuple[ResolvedParameter, ...] = ()

    products: tuple[PlannedProduct, ...] = ()

    @property
    def name(
        self,
    ) -> str:
        """
        Return the stage name.
        """

        return self.spec.name

    @property
    def dependencies(
        self,
    ) -> tuple[str, ...]:
        """
        Return stage dependency names.
        """

        return self.spec.dependencies

    @property
    def requires_features(
        self,
    ) -> tuple[str, ...]:
        """
        Return features required by this stage.
        """

        return self.spec.requires_features


# =========================================================
# Build plan
# =========================================================


@dataclass(
    frozen=True,
    slots=True,
)
class BuildPlan:
    """
    Concrete execution plan for one configured artifact.

    A BuildPlan contains everything needed to describe the work that
    would be performed for an artifact without actually performing it.
    """

    artifact_id: str

    model: ModelSpec

    project_root: Path

    artifact_dir: Path

    stages: tuple[PlannedStage, ...]

    @property
    def model_name(
        self,
    ) -> str:
        """
        Return the artifact model name.
        """

        return self.model.name


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

    No filesystem products are created and no stages are executed.
    """

    root = project_root if project_root is not None else Path.cwd()

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

    except (KeyError, ValueError) as exc:
        raise BuildPlanError(
            f"Artifact {artifact_id!r} references unknown model {model_name!r}."
        ) from exc

    artifact_dir = root / "artifacts" / artifact_id

    stages = _plan_stages(
        artifact_id,
        model,
        resolver,
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
    artifact_dir: Path,
) -> PlannedStage:
    """
    Materialize one stage.
    """

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
        parameters=parameters,
        products=products,
    )


# =========================================================
# Parameter resolution
# =========================================================


def _resolve_stage_parameters(
    artifact_id: str,
    stage: StageSpec,
    resolver,
) -> tuple[ResolvedParameter, ...]:
    """
    Resolve all parameters consumed by a stage.

    Failure to resolve any declared stage parameter makes the artifact
    unbuildable and therefore prevents construction of the build plan.
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
    "BuildPlan",
    "BuildPlanError",
    "PlannedProduct",
    "PlannedStage",
    "ResolvedParameter",
    "create_build_plan",
]
