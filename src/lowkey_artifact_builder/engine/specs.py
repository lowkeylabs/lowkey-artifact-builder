"""
Artifact build engine specifications.

This module defines the data structures used by the artifact build
engine.

Engine specifications describe concrete artifact build plans and stage
execution contexts. They are distinct from declarative model
specifications, which describe what may be built independently of any
particular artifact.

Planning constructs BuildPlan instances from configured artifacts and
their declarative models. Execution consumes those plans and constructs
StageContext instances for individual stage invocations.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from lowkey_artifact_builder.model import (
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

    Planning constructs the plan without modifying filesystem products.
    Execution consumes the completed plan without resolving artifact
    configuration again.
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

    The context provides the resolved parameters consumed by the stage,
    persistent products produced by direct dependency stages, declared
    outputs of the current stage, and filesystem locations associated
    with the artifact build.

    Input names are qualified by dependency stage name so products with
    identical names remain unambiguous. For example:

        prepare.trace
        raster.manifest
        vector.manifest

    Output names are the declarative product names of the current stage.

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
        Return the path of a dependency product.

        Input names are qualified by dependency stage name, such as
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
    "PlannedProduct",
    "PlannedStage",
    "ResolvedParameter",
    "StageContext",
    "StageContextError",
]
