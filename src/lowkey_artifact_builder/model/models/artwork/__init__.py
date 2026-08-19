"""
Artwork artifact model.

The artwork model converts source raster artwork into registered,
independently printable color components and packages those components
into a final 3MF file.

Artwork is treated as 2.5D geometry. Source artwork is reduced to a
configured artwork palette, separated into mutually exclusive
registered layers, converted to vector geometry, and extruded to a
configured height.

Artwork colors are properties of the artwork itself. They are distinct
from printer colors associated with an artifact that may later consume
the artwork.

The artwork model has no underlying base. Its final 3MF contains only
the generated artwork components.
"""

from __future__ import annotations

from lowkey_artifact_builder.model.registry import (
    ModelRegistry,
)
from lowkey_artifact_builder.model.specs import (
    ModelSpec,
    ProductSpec,
    StageSpec,
)

# =========================================================
# Stages
# =========================================================


STAGES = (
    StageSpec(
        name="prepare",
        description=("Trace the source artwork using the configured artwork palette."),
        parameters=(
            "source",
            "artwork_colors",
        ),
        products=(
            ProductSpec(
                name="trace",
                path="prepare/trace.svg",
                description=("Multicolor vector trace of the source artwork."),
            ),
        ),
    ),
    StageSpec(
        name="raster",
        description=("Build registered, mutually exclusive raster color layers."),
        dependencies=("prepare",),
        parameters=(
            "artwork_colors",
            "artwork_pixels",
            "artwork_min_island_area",
            "artwork_island_connectivity",
        ),
        products=(
            ProductSpec(
                name="manifest",
                path="raster/products.json",
                description=(
                    "Manifest describing the generated raster color "
                    "layers and their artwork color assignments."
                ),
            ),
        ),
    ),
    StageSpec(
        name="vector",
        description=("Convert registered raster color layers into registered vector geometry."),
        dependencies=("raster",),
        parameters=("artwork_size",),
        products=(
            ProductSpec(
                name="manifest",
                path="vector/products.json",
                description=("Manifest describing the generated vector color layers."),
            ),
        ),
    ),
    StageSpec(
        name="extrude",
        description=("Extrude vector color layers into printable STL components."),
        dependencies=("vector",),
        parameters=(
            "artwork_colors",
            "artwork_raise",
        ),
        products=(
            ProductSpec(
                name="manifest",
                path="extrude/products.json",
                description=(
                    "Manifest describing the generated artwork STL "
                    "components and their artwork colors."
                ),
            ),
        ),
    ),
    StageSpec(
        name="package",
        description=("Package the artwork STL components into the final 3MF."),
        dependencies=("extrude",),
        products=(
            ProductSpec(
                name="artifact",
                path="artifact.3mf",
                description=("Final printable multicomponent 3MF artifact."),
            ),
        ),
    ),
)


# =========================================================
# Model
# =========================================================


MODEL = ModelSpec(
    name="artwork",
    title="Artwork",
    description=(
        "Multicolor 2.5D artwork consisting of independently printable "
        "color components with no underlying base."
    ),
    stages=STAGES,
    defined_in=__name__,
)


# =========================================================
# Registration
# =========================================================


def register_models(
    registry: ModelRegistry,
) -> None:
    """
    Register models defined by this package.
    """

    registry.register_model(
        MODEL,
    )
