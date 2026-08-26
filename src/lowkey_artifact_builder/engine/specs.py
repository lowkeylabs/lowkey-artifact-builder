"""
Artifact build engine specifications.

This module defines the data structures used by the artifact build
engine.

Engine specifications describe concrete artifact build plans and stage
execution contexts. They are distinct from declarative model
specifications, which describe what may be built independently of any
particular artifact.

Planning constructs BuildPlan instances from configured artifacts,
requested products, and their declarative models. Execution consumes
those plans, materializes external filesystem inputs into the artifact
workspace, and constructs StageContext instances for individual stage
invocations.

A BuildPlan may represent either a normal complete realization build or
an explicitly product-targeted build. Product-targeted plans retain the
logical ProductRef targets that caused their stage dependency closure to
be selected.

The artifact-specific configuration Resolver is the single runtime
authority for resolved configuration. Model stages declare the
parameters they normally consume through StageSpec, but all stages have
access to the complete artifact configuration through the Resolver.
"""
# File: src/lowkey_artifact_builder/engine/specs.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from lowkey_artifact_builder.config import (
    Resolver,
)
from lowkey_artifact_builder.model import (
    InputSpec,
    ModelSpec,
    ProductDependencyBinding,
    ProductDependencySpec,
    ProductRef,
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

    StageSpec.parameters declares the configuration parameters normally
    consumed by the stage. Parameter values are not copied into the
    planned stage. The artifact Resolver retained by BuildPlan is the
    authoritative source for all resolved configuration values and
    provenance.

    Inputs contain external filesystem resources and their
    artifact-owned materialization locations.

    Products contain the concrete filesystem locations at which the
    stage is expected to create its declared persistent outputs.

    Products from dependency stages are not duplicated in inputs here.
    The build engine exposes those dependency products through the
    StageContext when the stage executes.
    """

    spec: StageSpec

    inputs: tuple[PlannedInput, ...] = ()

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
    Concrete execution plan for one configured artifact realization.

    A BuildPlan contains everything needed to describe and execute the
    work for one artifact realization.

    The resolver is the artifact-specific configuration authority
    created during planning. It contains the complete effective
    configuration view for the artifact, including configured values,
    derived values, provenance, and shared reference configuration such
    as the color catalog.

    Targets records the logical products explicitly requested for a
    product-targeted build.

    When targets is None, the plan represents the normal complete build
    of all stages participating in the configured realization.

    When targets contains ProductRef values, stages contains only the
    producers of those products and the transitive dependency closure
    required to produce them. ProductRef remains a logical identity and
    contains no filesystem location.

    Product_dependencies records definition-level products required by the
    planned realization but produced outside its model-local stage
    dependency closure.

    Product_dependencies records definition-level products required by the
    planned realization but produced outside its model-local stage
    dependency closure.

    These dependencies identify producer model, stage, and product
    independently of any particular producer artifact.

    Product_dependency_bindings records the concrete producer artifact and
    realization selected by artifact configuration for each declarative
    product dependency.

    The bindings retain logical ProductRef identity. Filesystem locations
    and producer build planning remain separate concerns.

    Stage parameter declarations remain on StageSpec and describe which
    configuration values a stage normally consumes. Parameter values
    themselves are obtained directly from resolver and are not copied
    into PlannedStage.

    Planning constructs the plan without modifying filesystem products
    or materializing external inputs.

    Execution consumes the completed plan without creating another
    configuration resolver, recomputing target dependency closure, or
    resolving filesystem locations again.
    """

    artifact_id: str

    model: ModelSpec

    realization_name: str

    resolver: Resolver

    project_root: Path

    artifact_dir: Path

    stages: tuple[PlannedStage, ...]

    targets: tuple[ProductRef, ...] | None = None

    product_dependencies: tuple[ProductDependencySpec, ...] = ()

    product_dependency_bindings: tuple[ProductDependencyBinding, ...] = ()

    @property
    def model_name(
        self,
    ) -> str:
        """
        Return the artifact model name.
        """

        return self.model.name

    @property
    def targeted(
        self,
    ) -> bool:
        """
        Return whether this is an explicitly product-targeted build.
        """

        return self.targets is not None


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

        resolver
            The same artifact-specific configuration Resolver retained
            by BuildPlan. It is the authoritative source for all
            resolved configuration values, provenance, derivations, and
            shared reference configuration.

        inputs
            Artifact-owned filesystem resources available to the stage.
            These include explicitly declared stage inputs materialized
            by the engine and products supplied by direct dependency
            stages.

        outputs
            Concrete filesystem paths for the current stage's declared
            products.

    StageSpec.parameters declares the parameters a stage normally
    consumes, but it is not an access-control boundary. Every stage has
    visibility to the complete artifact configuration through resolver.

    For example:

        context.resolver("artwork_colors")
        context.resolver("printer_colors")
        context.resolver.source("artwork_colors")
        context.resolver.colors

    Explicit stage inputs use their declarative names, for example:

        source

    Products supplied by dependency stages use qualified names so
    products with identical names remain unambiguous, for example:

        prepare.trace
        raster.manifest
        vector.manifest

    The engine resolves configuration and materializes external
    filesystem resources before constructing this context.
    Model-specific stage implementations therefore use StageContext
    rather than interpret project layout, configuration path semantics,
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

    resolver: Resolver

    inputs: Mapping[str, Path]

    outputs: Mapping[str, Path]

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


# =========================================================
# Exports
# =========================================================


__all__ = [
    "BuildPlan",
    "PlannedInput",
    "PlannedProduct",
    "PlannedStage",
    "StageContext",
    "StageContextError",
]
