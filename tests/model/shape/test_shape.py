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
    Shape declares the first stage that consumes registered Artwork.

    The initial Shape declaration grows only far enough to establish the
    registered-geometry consumer boundary. Structural geometry and later
    manufacturing stages are introduced by subsequent slices.
    """

    assert tuple(stage.name for stage in MODEL.stages) == ("compose",)


def test_shape_consumes_artwork_vector_manifest_by_logical_identity() -> None:
    """
    Shape depends logically on the registered Artwork vector manifest.

    The model-level dependency identifies only the producing model, stage,
    and product. Artifact identity, realization identity, and filesystem
    location are runtime concerns and do not belong in the Shape model
    declaration.
    """

    stage = MODEL.stages[0]

    assert stage.product_dependencies == (
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

    dependency = MODEL.stages[0].product_dependencies[0]

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
    Consuming registered Artwork does not yet dimensionalize it.

    Physical Shape sizing, fitting, extrusion, and packaging belong to later
    Shape behavior and must not be introduced merely to establish the logical
    registered-geometry dependency.
    """

    stage = MODEL.stages[0]

    assert stage.parameters == ()
