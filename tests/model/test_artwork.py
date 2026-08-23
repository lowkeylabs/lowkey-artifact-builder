"""Tests for the artwork model."""

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
    Artwork stages form a linear dependency chain using semantic stage
    names rather than numeric stage identifiers.
    """

    stages = {stage.name: stage for stage in MODEL.stages}

    assert stages["prepare"].dependencies == ()
    assert stages["raster"].dependencies == ("prepare",)
    assert stages["vector"].dependencies == ("raster",)
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
    """Artwork preparation consumes the artwork palette."""

    stages = {stage.name: stage for stage in MODEL.stages}

    assert stages["prepare"].parameters == ("artwork_colors",)


def test_artwork_raster_inputs() -> None:
    """Raster generation depends on artwork processing parameters."""

    stages = {stage.name: stage for stage in MODEL.stages}

    assert stages["raster"].parameters == (
        "artwork_colors",
        "artwork_pixels",
        "artwork_size",
        "artwork_min_island_area",
        "artwork_island_connectivity",
    )


def test_artwork_vector_inputs() -> None:
    """Vector generation depends on physical artwork size."""

    stages = {stage.name: stage for stage in MODEL.stages}

    assert stages["vector"].parameters == ("artwork_size",)


def test_artwork_extrude_inputs() -> None:
    """Extrusion depends on artwork palette and raise."""

    stages = {stage.name: stage for stage in MODEL.stages}

    assert stages["extrude"].parameters == (
        "artwork_colors",
        "artwork_raise",
    )


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
    Model parameters include configuration consumed through inputs.

    External input parameters participate in the model's complete
    configuration requirements even though they are not ordinary stage
    parameters.

    Parameters consumed by multiple stages appear once, ordered by
    their first occurrence in the model workflow.
    """

    assert MODEL.parameters == (
        "source",
        "artwork_colors",
        "artwork_pixels",
        "artwork_size",
        "artwork_min_island_area",
        "artwork_island_connectivity",
        "artwork_raise",
    )
