"""Tests for the shape model."""
# File: tests/model/shape/test_shape.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from lowkey_artifact_builder.model import (
    ProductDependencySpec,
    build_model_registry,
)
from lowkey_artifact_builder.model.models.shape import MODEL

# =========================================================
# Helpers
# =========================================================


def _compose_stage():
    """Return the Shape stage that consumes registered Artwork."""

    return next(stage for stage in MODEL.stages if stage.name == "compose")


def _structure_stage():
    """Return the Shape stage that produces structural geometry."""

    return next(stage for stage in MODEL.stages if stage.name == "structure")


# =========================================================
# Model identity
# =========================================================


def test_shape_model_identity() -> None:
    """The shape model has the expected identity."""

    assert MODEL.name == "shape"
    assert MODEL.title == "Shape"


def test_shape_model_is_discovered() -> None:
    """The shape model participates in normal model discovery."""

    registry = build_model_registry()

    names = [model.name for model in registry.all_models()]

    assert "shape" in names


# =========================================================
# Registered Artwork consumer
# =========================================================


def test_shape_declares_registered_artwork_consumer_stage() -> None:
    """
    Shape retains the stage that consumes registered Artwork.

    Introducing independent structural production must preserve the
    registered-geometry consumer boundary established by earlier slices.
    """

    compose_stage = _compose_stage()

    assert compose_stage.name == "compose"


def test_shape_consumes_artwork_vector_manifest_by_logical_identity() -> None:
    """
    Shape depends logically on the registered Artwork vector manifest.

    The model-level dependency identifies only the producing model, stage,
    and product. Artifact identity, realization identity, and filesystem
    location are runtime concerns and do not belong in the Shape model
    declaration.
    """

    compose_stage = _compose_stage()

    assert compose_stage.product_dependencies == (
        ProductDependencySpec(
            model="artwork",
            stage="vector",
            product="manifest",
        ),
    )


def test_shape_registered_artwork_dependency_contains_only_logical_identity() -> None:
    """
    Shape's registered Artwork dependency contains only logical identity.

    Artifact binding, realization binding, and canonical filesystem resolution
    belong to runtime planning rather than the consuming model declaration.
    """

    compose_stage = _compose_stage()

    dependency = compose_stage.product_dependencies[0]

    assert dependency.model == "artwork"
    assert dependency.stage == "vector"
    assert dependency.product == "manifest"

    assert not hasattr(
        dependency,
        "artifact",
    )

    assert not hasattr(
        dependency,
        "realization",
    )

    assert not hasattr(
        dependency,
        "path",
    )


def test_shape_registered_artwork_consumer_declares_no_physical_parameters() -> None:
    """
    Consuming registered Artwork does not itself dimensionalize it.

    Physical Shape sizing belongs to structural Shape production rather than
    to the registered-Artwork dependency declaration.
    """

    compose_stage = _compose_stage()

    assert compose_stage.parameters == ()


# =========================================================
# Structural Shape declaration
# =========================================================


def test_shape_declares_structural_stage() -> None:
    """
    Shape declares an independently executable structural stage.

    Structural Shape production does not depend on registered Artwork.
    """

    structure_stage = _structure_stage()

    assert structure_stage.product_dependencies == ()


def test_shape_structure_consumes_registered_geometry_parameters() -> None:
    """
    Structural production consumes only policy required to construct the
    registered Shape geometry.

    Physical X/Y size and Z dimensions belong to downstream physical
    dimensionalization rather than registered structural production.
    """

    structure_stage = _structure_stage()

    assert structure_stage.parameters == ("shape_geometry",)


def test_shape_structure_produces_persistent_structure() -> None:
    """
    Structural production declares one independently verifiable product.

    The product participates in the normal resumable-build and canonical
    product-resolution contracts.
    """

    structure_stage = _structure_stage()

    assert tuple(product.name for product in structure_stage.products) == ("structure",)


def test_shape_structure_has_canonical_relative_product_path() -> None:
    """
    Registered Shape structural geometry has a model-declared relative
    vector-product path.

    The structure stage persists registered two-dimensional geometry rather
    than dimensionalized manufacturing geometry or a packaged 3MF.

    Generated filesystem placement remains the responsibility of planning
    and product resolution rather than artifact configuration.
    """

    structure_stage = _structure_stage()

    product = next(product for product in structure_stage.products if product.name == "structure")

    assert product.path == "structure.svg"
