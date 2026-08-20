"""
Artifact build engine specifications.

This module defines the data structures used by the artifact build
engine.

Engine specifications describe concrete artifact build plans and stage
execution contexts. They are distinct from declarative model
specifications, which describe what may be built independently of any
particular artifact.

Planning constructs BuildPlan instances from configured artifacts and
their declarative models. Execution consumes those plans, materializes
external filesystem inputs into the artifact workspace, and constructs
StageContext instances for individual stage invocations.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from lowkey_artifact_builder.model import (
    InputSpec,
    ModelSpec,
    ProductSpec,
    StageSpec,
)

# =========================================================
# Errors
# =========================================================


class StageContextError(RuntimeError):
    """
    Raised when a stage execution value cannot be obtained.
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
# Planned inputs
# =========================================================


@dataclass(
    frozen=True,
    slots=True,
)
class PlannedInput:
    """
    An external filesystem input materialized for an artifact build.

    Source_path is the concrete external filesystem resource identified
    by resolved artifact configuration.

    Path is the artifact-owned location at which the build engine
    materializes that resource before stage execution.

    For example:

        source_path
            projects/new-york-deli-blimp.png

        path
            projects/artifacts/nydeli/artifact.png

    The original InputSpec is retained so callers still have access to
    the input's declarative name, artifact-local path, and description.

    Planning resolves both filesystem locations but does not copy or
    otherwise modify the resource.

    Execution materializes source_path at path before any stage that
    consumes the input executes.

    Model-specific stage implementations receive only path through
    StageContext. They therefore consume artifact-owned resources
    without needing to understand project layout, configuration path
    semantics, or the location of the original external resource.
    """

    spec: InputSpec

    source_path: Path

    path: Path

    @property
    def name(
        self,
    ) -> str:
        """
        Return the declarative input name.
        """

        return self.spec.name

    @property
    def description(
        self,
    ) -> str:
        """
        Return the declarative input description.
        """

        return self.spec.description


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

    Inputs contain external filesystem resources and their
    artifact-owned materialization locations.

    Parameters contain artifact-specific resolved non-filesystem values
    consumed by the stage.

    Products contain the concrete filesystem locations at which the
    stage is expected to create its declared persistent outputs.

    Products from dependency stages are not duplicated in inputs here.
    The build engine exposes those dependency products through the
    StageContext when the stage executes.
    """

    spec: StageSpec

    inputs: tuple[PlannedInput, ...] = ()

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
# Build plans
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

    Planning constructs the plan without modifying filesystem products
    or materializing external inputs.

    Execution consumes the completed plan without resolving artifact
    configuration or filesystem locations again.
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
# Stage execution contexts
# =========================================================


@dataclass(
    frozen=True,
    slots=True,
)
class StageContext:
    """
    Execution context for one planned artifact stage.

    A StageContext is constructed by the build engine immediately
    before executing a model-specific stage implementation.

    The context provides:

        parameters
            Resolved non-filesystem values consumed by the stage.

        inputs
            Artifact-owned filesystem resources available to the stage.
            These include explicitly declared stage inputs materialized
            by the engine and products supplied by direct dependency
            stages.

        outputs
            Concrete filesystem paths for the current stage's declared
            products.

    Explicit stage inputs use their declarative names, for example:

        source

    Products supplied by dependency stages use qualified names so
    products with identical names remain unambiguous, for example:

        prepare.trace
        raster.manifest
        vector.manifest

    The engine resolves and materializes external filesystem resources
    before constructing this context. Model-specific stage
    implementations therefore use StageContext paths directly rather
    than interpret project layout, configuration path semantics,
    external source locations, or dependency structure themselves.

    Model-specific stage implementations should consume StageContext
    rather than inspect BuildPlan or PlannedStage directly.
    """

    artifact_id: str

    model_name: str

    stage_name: str

    project_root: Path

    artifact_dir: Path

    working_dir: Path

    parameters: Mapping[str, Any]

    inputs: Mapping[str, Path]

    outputs: Mapping[str, Path]

    def parameter(
        self,
        name: str,
    ) -> Any:
        """
        Return a resolved parameter consumed by this stage.
        """

        try:
            return self.parameters[name]

        except KeyError as exc:
            raise StageContextError(
                f"Stage {self.stage_name!r} has no parameter {name!r}."
            ) from exc

    def input(
        self,
        name: str,
    ) -> Path:
        """
        Return the path of an input filesystem resource.

        Explicit stage inputs use their declarative names. Products
        supplied by dependency stages use qualified names such as
        'prepare.trace'.
        """

        try:
            return self.inputs[name]

        except KeyError as exc:
            raise StageContextError(f"Stage {self.stage_name!r} has no input {name!r}.") from exc

    def output(
        self,
        name: str,
    ) -> Path:
        """
        Return the path of a declared output product.
        """

        try:
            return self.outputs[name]

        except KeyError as exc:
            raise StageContextError(f"Stage {self.stage_name!r} has no output {name!r}.") from exc


__all__ = [
    "BuildPlan",
    "PlannedInput",
    "PlannedProduct",
    "PlannedStage",
    "ResolvedParameter",
    "StageContext",
    "StageContextError",
]
