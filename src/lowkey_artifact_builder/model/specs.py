"""
Model subsystem specifications.

The model subsystem defines the declarative structure of an artifact
model.

Models describe what may be built. They do not describe a particular
artifact and they do not perform builds.

A model consists of:

    Model
        A complete artifact model definition.

    Feature
        An optional capability or behavior supported by a model.

    Stage
        One resumable step in the model workflow.

    Input
        An external filesystem resource consumed by a stage.

    Product
        A persistent filesystem work product produced by a stage.

Artifact content and configuration are separate from model
specifications.

For example, an artifact may contain zero, one, or many artwork
instances. Each artwork instance may have its own source, size,
position, and rotation. Those instances belong to artifact
configuration rather than ModelSpec or FeatureSpec.

Features describe optional model behavior. For example, a circular
model might support features such as:

    ridge
        Adds raised ridge geometry to the artifact.

    labels
        Adds printable lettering to the artifact.

    hanger
        Adds hanger geometry to the artifact.

    magnet
        Adds an internal magnet cavity to the artifact.

    fill
        Adds background geometry around artwork.

A feature may enable a stage, modify the behavior of an existing stage,
or do both.

Execution, artifact configuration, configuration resolution, filesystem
path resolution, feature interpretation, dependency resolution, stage
validity, and artifact materialization belong to other subsystems.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# =========================================================
# Inputs
# =========================================================


@dataclass(
    frozen=True,
    slots=True,
)
class InputSpec:
    """
    Define an external filesystem resource consumed by a stage.

    An input identifies a filesystem resource whose location originates
    from resolved artifact configuration rather than from a product of
    another stage.

    Name is the execution-facing name by which the stage accesses the
    materialized resource.

    Parameter identifies the resolved artifact configuration value from
    which the build system obtains the external source location.

    Path identifies the location, relative to the artifact working
    directory, at which the build engine materializes the external
    resource for stage execution.

    For example:

        InputSpec(
            name="source",
            parameter="source",
            path="artifact.png",
        )

    declares that the stage consumes an input named "source". Its
    external filesystem location originates from the resolved
    configuration value named "source", and the build engine
    materializes that resource as "artifact.png" in the artifact
    working directory.

    InputSpec is declarative. It does not interpret the configuration
    value, resolve relative paths, determine project layout, verify
    filesystem existence, copy files, or otherwise materialize the
    input.

    Those responsibilities belong to planning and execution.

    Products of dependency stages are not declared as InputSpec
    instances. Dependencies already establish those relationships, and
    the build engine makes dependency products available to the
    executing stage through its StageContext.
    """

    name: str

    parameter: str

    path: str

    description: str = ""


# =========================================================
# Products
# =========================================================


@dataclass(
    frozen=True,
    slots=True,
)
class ProductSpec:
    """
    Define a persistent filesystem work product produced by a stage.

    The path is relative to the artifact working directory.

    Product filenames are intentionally artifact-independent because
    every artifact receives its own working directory.

    Products describe persistent filesystem outputs that participate in
    determining whether a stage has completed successfully.

    A stage may create additional temporary or diagnostic files that are
    not declared as products.

    Products may include intermediate build results as well as final
    printable geometry. The important distinction is that a declared
    product participates in the resumable build contract of its stage.

    ProductSpec is declarative. The concrete product path for a
    particular artifact is materialized by the build planning
    subsystem.
    """

    name: str

    path: str

    description: str = ""


# =========================================================
# Features
# =========================================================


@dataclass(
    frozen=True,
    slots=True,
)
class FeatureSpec:
    """
    Define an optional capability or behavior supported by a model.

    Features are declarative capabilities. Enabling a feature may alter
    model geometry, enable one or more workflow stages, affect generated
    products, or otherwise change model-specific behavior.

    Features describe model behavior rather than artifact content.

    For example, an artifact containing four artwork instances does not
    contain four artwork features. The artwork instances are artifact
    configuration. Features instead describe optional behaviors such as
    adding a ridge, hanger, magnet cavity, labels, or background fill.

    FeatureSpec does not define how a feature is implemented. That
    behavior belongs to the model implementation.

    A model may be valid with none of its optional features enabled.

    Feature discovery and registration are intentionally outside this
    specification. This allows model implementations to acquire
    additional features through future extension or plugin mechanisms
    without changing the declarative meaning of FeatureSpec.
    """

    name: str

    description: str = ""


# =========================================================
# Stages
# =========================================================


@dataclass(
    frozen=True,
    slots=True,
)
class StageSpec:
    """
    Define one resumable stage in a model workflow.

    A stage is the smallest unit of work that the build system may
    independently determine to be current, stale, or incomplete.

    Dependencies identify other stages that must be satisfied before
    this stage may execute.

    Products produced by direct dependency stages are made available to
    the executing stage by the build engine. They are therefore not
    repeated as explicit InputSpec declarations.

    Required features identify optional model features that must be
    enabled for this stage to participate in an artifact workflow.

    An empty required-features tuple means that the stage participates
    regardless of which optional features are enabled.

    A feature does not need to appear in requires_features merely
    because it affects the behavior of a stage. For example, a hanger
    feature may modify geometry produced by an always-present base stage
    without being required for that stage.

    Inputs identify external filesystem resources consumed by the stage.
    Their source locations originate from resolved artifact
    configuration. The build engine materializes those resources at
    their declared artifact-local paths before execution.

    Parameters identify resolved non-filesystem values consumed by the
    stage whose values materially affect the products generated by that
    stage.

    Resolved values may be configured directly or derived from other
    configuration values, model geometry, enabled features, or artifact
    content.

    Parameter names refer to the resolved artifact configuration rather
    than to a particular configuration tier or TOML location. A resolved
    value may originate from master defaults, workspace overrides,
    artifact-specific overrides, or derivation performed during
    configuration resolution.

    Stage validity should therefore depend on the resolved inputs and
    values consumed by the stage rather than on where those values
    originated.

    Products describe persistent filesystem outputs whose existence and
    validity participate in determining whether the stage is satisfied.
    """

    name: str

    description: str = ""

    dependencies: tuple[str, ...] = ()

    requires_features: tuple[str, ...] = ()

    inputs: tuple[InputSpec, ...] = ()

    parameters: tuple[str, ...] = ()

    products: tuple[ProductSpec, ...] = ()


# =========================================================
# Models
# =========================================================


@dataclass(
    frozen=True,
    slots=True,
)
class ModelSpec:
    """
    Define an artifact model.

    A model describes the capabilities and workflow used to transform
    an artifact definition into a final printable 3MF file.

    A model describes a kind of artifact rather than a particular
    artifact instance.

    Artifact-specific content belongs to artifact configuration. For
    example, configuration may describe zero, one, or many artwork
    instances and the placement, size, and rotation of each instance.

    Features identify optional capabilities or behaviors supported by
    the model.

    Stages define the model's complete potential workflow. Individual
    artifact workflows may contain only a subset of those stages when
    stages depend on optional features that are not enabled.

    ModelSpec is declarative. It does not execute stages, describe
    individual artwork instances, interpret feature behavior, resolve
    configuration, resolve filesystem paths, determine stage validity,
    or manipulate artifact files.

    Model construction and feature discovery are separate concerns.
    This permits future model extension mechanisms to contribute
    features and stages while preserving ModelSpec as the completed
    declarative representation consumed by the rest of the system.
    """

    name: str

    title: str

    description: str = ""

    features: tuple[FeatureSpec, ...] = field(
        default_factory=tuple,
    )

    stages: tuple[StageSpec, ...] = field(
        default_factory=tuple,
    )

    defined_in: str | None = None

    @property
    def parameters(
        self,
    ) -> tuple[str, ...]:
        """
        Return all resolved configuration values consumed by this model.

        Values are collected from both stage inputs and stage parameters
        in stage order.

        For an input, its parameter identifies the resolved
        configuration value from which its external filesystem resource
        is located.

        Duplicate names are removed while preserving the position of
        their first occurrence.

        This represents the complete set of resolved configuration
        values consumed by the model's potential workflow. Whether a
        particular value is needed by an artifact depends on which
        stages participate in that artifact's workflow.

        Whether a value is configured directly, inherited from a
        configuration tier, or derived is the responsibility of the
        configuration subsystem.
        """

        seen: set[str] = set()
        parameters: list[str] = []

        for stage in self.stages:
            for input_spec in stage.inputs:
                parameter = input_spec.parameter

                if parameter in seen:
                    continue

                seen.add(parameter)

                parameters.append(parameter)

            for parameter in stage.parameters:
                if parameter in seen:
                    continue

                seen.add(parameter)

                parameters.append(parameter)

        return tuple(parameters)


__all__ = [
    "FeatureSpec",
    "InputSpec",
    "ModelSpec",
    "ProductSpec",
    "StageSpec",
]
