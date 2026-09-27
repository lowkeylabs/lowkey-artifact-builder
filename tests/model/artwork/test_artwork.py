"""Tests for the artwork model."""
# File: tests/model/artwork/test_artwork.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from lowkey_artifact_builder.model.models.artwork import MODEL


def test_artwork_model_identity() -> None:
    """The artwork model has the expected identity."""

    assert MODEL.name == "artwork"
    assert MODEL.title == "Artwork"


def test_artwork_model_has_no_features() -> None:
    """Standalone artwork requires no optional model features."""

    assert MODEL.features == ()


def test_artwork_stages() -> None:
    """
    The artwork workflow declares the expected stages with stable
    numeric identifiers.
    """

    assert tuple((stage.id, stage.name) for stage in MODEL.stages) == (
        (10, "prepare"),
        (20, "raster"),
        (30, "vector"),
        (40, "extrude"),
        (50, "package"),
    )


def test_artwork_stage_dependencies() -> None:
    """
    Artwork stages declare every upstream stage whose products they consume.

    Vector consumes both the registered raster manifest and the prepared
    envelope, so it depends directly on both raster and prepare.
    """

    stages = {stage.name: stage for stage in MODEL.stages}

    assert stages["prepare"].dependencies == ()
    assert stages["raster"].dependencies == ("prepare",)
    assert stages["vector"].dependencies == (
        "prepare",
        "raster",
    )
    assert stages["extrude"].dependencies == ("vector",)
    assert stages["package"].dependencies == ("extrude",)


def test_artwork_prepare_external_input() -> None:
    """Artwork preparation consumes a materialized source image."""

    stages = {stage.name: stage for stage in MODEL.stages}

    prepare = stages["prepare"]

    assert len(prepare.inputs) == 1

    source = prepare.inputs[0]

    assert source.name == "source"
    assert source.parameter == "source"
    assert source.path == "artifact.png"


def test_artwork_prepare_parameters() -> None:
    """
    Artwork preparation depends on trace cardinality and envelope policy.

    Artifact colors are discovered by preparation rather than supplied
    as configured physical colors.
    """

    stages = {stage.name: stage for stage in MODEL.stages}

    assert stages["prepare"].parameters == (
        "artifact_color_count",
        "artwork_envelope_mode",
    )


def test_artwork_raster_parameters() -> None:
    """
    Raster generation establishes registered Artifact-color geometry.

    Rasterization depends on raster resolution and cleanup policy, but not
    on physical printer-color assignment. Printer colors do not change
    registered Artwork geometry and are resolved downstream during
    packaging.
    """

    stages = {stage.name: stage for stage in MODEL.stages}

    assert stages["raster"].parameters == (
        "artwork_pixels",
        "artwork_min_island_area",
        "artwork_island_connectivity",
    )


def test_artwork_vector_is_independent_of_physical_size() -> None:
    """
    Vector generation preserves registered artwork geometry without
    assigning physical manufacturing dimensions.

    Physical artwork size must not participate in vector generation.
    """

    stages = {stage.name: stage for stage in MODEL.stages}

    assert stages["vector"].parameters == ()


def test_artwork_extrude_introduces_physical_dimensions() -> None:
    """
    Extrusion is the Artwork model's physical geometry boundary.

    Extrusion owns dimensional and attachment configuration that changes
    printable geometry. Physical printer-color assignment and explicit
    feature-color overrides do not change geometry and are owned downstream
    by packaging.
    """

    stages = {stage.name: stage for stage in MODEL.stages}

    parameters = set(stages["extrude"].parameters)

    assert {
        "artwork_size",
        "artwork_raise",
    }.issubset(parameters)

    assert {
        "printer_colors",
        "loop_color",
        "artwork_base_color",
        "artwork_outer_ridge_color",
    }.isdisjoint(parameters)


def test_artwork_stage_products() -> None:
    """
    Artwork product paths are local to their producing stages.

    Product specifications identify paths within a stage rather than
    encoding the stage directory itself.
    """

    stages = {stage.name: stage for stage in MODEL.stages}

    assert tuple(product.path for product in stages["prepare"].products) == (
        "trace.svg",
        "envelope.svg",
    )

    assert stages["raster"].products[0].path == "products.json"

    assert stages["vector"].products[0].path == "products.json"

    assert stages["extrude"].products[0].path == "products.json"

    assert stages["package"].products[0].path == "artifact.3mf"


def test_artwork_model_parameters() -> None:
    """
    Artwork model parameters include configuration consumed by its declared
    stages and external inputs.

    Derived Artifact colors are product information rather than model
    configuration.
    """

    parameters = set(MODEL.parameters)

    assert {
        "source",
        "artifact_color_count",
        "artwork_envelope_mode",
        "printer_colors",
        "artwork_pixels",
        "artwork_min_island_area",
        "artwork_island_connectivity",
        "artwork_size",
        "artwork_raise",
    }.issubset(parameters)


def test_artwork_package_parameters() -> None:
    """
    Packaging owns physical printer-color assignment.

    Printer colors and explicit physical feature-color overrides affect the
    final printable 3MF representation without changing prepared, rasterized,
    vectorized, or extruded Artwork geometry.
    """

    stages = {stage.name: stage for stage in MODEL.stages}

    assert stages["package"].parameters == (
        "printer_colors",
        "loop_color",
        "artwork_base_color",
        "artwork_outer_ridge_color",
    )
