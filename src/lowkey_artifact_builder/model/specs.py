"""
Model subsystem specifications.

The model subsystem defines the declarative structure of an artifact
model.

Models describe what may be built. They do not perform builds.

A model consists of:

    Model
        A complete artifact model definition.

    Feature
        An optional capability supported by a model.

    Stage
        One step in the model workflow.

    Product
        A filesystem work product produced by a stage.

Execution, configuration resolution, and artifact materialization belong
to other subsystems.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# =========================================================
# Products
# =========================================================


@dataclass(
    frozen=True,
    slots=True,
)
class ProductSpec:
    """
    Define a filesystem work product produced by a stage.

    The path is relative to the artifact working directory.

    Product filenames are intentionally artifact-independent because
    every artifact receives its own working directory.
    """

    name: str

    path: str

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
    Define one stage in a model workflow.

    Dependencies identify other stages that must be complete before this
    stage may execute.

    Products describe the persistent filesystem outputs produced by the
    stage.
    """

    name: str

    description: str = ""

    dependencies: tuple[str, ...] = ()

    products: tuple[ProductSpec, ...] = ()


# =========================================================
# Features
# =========================================================


@dataclass(
    frozen=True,
    slots=True,
)
class FeatureSpec:
    """
    Define an optional capability supported by a model.

    Features may later influence configuration, geometry, stage
    applicability, or generated products.
    """

    name: str

    description: str = ""


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

    A model describes the capabilities and workflow used to transform an
    artifact definition into a final printable 3MF file.

    ModelSpec is declarative. It does not execute stages or manipulate
    artifact files.
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
