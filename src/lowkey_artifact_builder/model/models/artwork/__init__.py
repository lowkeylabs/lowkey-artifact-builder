"""
Artwork vector stage.

The vector stage converts registered raster color layers into
registered vector geometry without assigning physical manufacturing
dimensions.

The raster manifest identifies the dynamically generated raster layers
that participate in this stage. One common square crop is calculated
from the union of all raster layers and applied to every layer so that
registration is preserved.

Each cropped raster layer is traced by Inkscape. All resulting SVG
documents retain the common coordinate system established by the
registered raster crop.

Physical dimensionalization is the responsibility of a downstream
consumer.

Filesystem layout, dependency resolution, and configuration resolution
are responsibilities of the build engine. This implementation consumes
only the paths and values supplied through StageContext.
"""
# File: src/lowkey_artifact_builder/model/models/artwork/__init__.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

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
        id=10,
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
                path="trace.svg",
                description=("Multicolor vector trace of the source artwork."),
            ),
            ProductSpec(
                name="envelope",
                path="envelope.svg",
                description=("Envelope surrounding outside of image."),
            ),
        ),
    ),
    StageSpec(
        id=20,
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
                path="products.json",
                description=(
                    "Manifest describing the generated raster color "
                    "layers and their artwork color assignments."
                ),
            ),
        ),
    ),
    StageSpec(
        id=30,
        name="vector",
        description=("Convert registered raster color layers into registered vector geometry."),
        dependencies=(
            "prepare",
            "raster",
        ),
        parameters=(),
        products=(
            ProductSpec(
                name="manifest",
                path="products.json",
                description=("Manifest describing the generated vector color layers."),
            ),
        ),
    ),
    StageSpec(
        id=40,
        name="extrude",
        description=("Extrude vector color layers into printable STL components."),
        dependencies=("vector",),
        parameters=(
            "artwork_colors",
            "artwork_size",
            "artwork_raise",
        ),
        products=(
            ProductSpec(
                name="manifest",
                path="products.json",
                description=(
                    "Manifest describing the generated artwork STL "
                    "components and their artwork colors."
                ),
            ),
        ),
    ),
    StageSpec(
        id=50,
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
