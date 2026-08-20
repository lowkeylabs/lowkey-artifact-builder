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

from typing import Protocol

from lowkey_artifact_builder.model.registry import (
    ModelRegistry,
)
from lowkey_artifact_builder.model.specs import (
    InputSpec,
    ModelSpec,
    ProductSpec,
    StageSpec,
)

# =========================================================
# Stage implementation registration protocol
# =========================================================


class StageImplementationRegistry(
    Protocol,
):
    """
    Minimal registry interface required by this model package.

    The concrete stage registry belongs to the build engine. The model
    package depends only on the registration operation needed to
    contribute its executable stage implementations.
    """

    def register(
        self,
        model_name: str,
        stage_name: str,
        implementation,
    ) -> None:
        """
        Register an executable implementation for a model stage.
        """

        ...


# =========================================================
# Stages
# =========================================================


STAGES = (
    StageSpec(
        name="prepare",
        description=("Trace the source artwork using the configured artwork palette."),
        inputs=(
            InputSpec(
                name="source",
                parameter="source",
                path="artifact.png",
                description=(
                    "Source raster artwork materialized into the artifact workspace for tracing."
                ),
            ),
        ),
        parameters=("artwork_colors",),
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
            "artwork_size",
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
# Model registration
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


# =========================================================
# Stage implementation registration
# =========================================================


def register_stage_implementations(
    registry: StageImplementationRegistry,
) -> None:
    """
    Register executable stage implementations for the artwork model.

    Implementation discovery is delegated to the artwork stages
    package so this module remains primarily the declarative model
    definition and public registration surface.
    """

    from .stages import (
        register_stage_implementations as register,
    )

    register(
        registry,
    )


__all__ = [
    "MODEL",
    "STAGES",
    "register_models",
    "register_stage_implementations",
]
