"""
Artwork model definition.

The Artwork model converts source raster artwork into registered
multicolor geometry and, when required, physically dimensionalized
printable components.

Artifact colors are discovered from the source artwork during
preparation. Physical printer-color assignments are established during
rasterization and preserved as product information downstream.

Filesystem layout, dependency resolution, configuration resolution,
and execution planning are responsibilities of the build engine.
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
        description=(
            "Trace the source artwork using the configured Artifact "
            "color count and derive its envelope."
        ),
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
        parameters=(
            "artifact_color_count",
            "artwork_envelope_mode",
        ),
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
        description=(
            "Build registered, mutually exclusive raster color layers "
            "and establish printer-color assignments."
        ),
        dependencies=("prepare",),
        parameters=(
            "printer_colors",
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
                    "layers and their Artifact and printer color "
                    "assignments."
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
                description=("Manifest describing the generated registered vector color layers."),
            ),
        ),
    ),
    StageSpec(
        id=40,
        name="extrude",
        description=("Extrude registered vector color layers into printable STL components."),
        dependencies=("vector",),
        parameters=(
            "artwork_size",
            "artwork_raise",
        ),
        products=(
            ProductSpec(
                name="manifest",
                path="products.json",
                description=(
                    "Manifest describing the generated artwork STL "
                    "components and their preserved color assignments."
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
    Register executable stage implementations for the Artwork model.

    Implementation discovery is delegated to the Artwork stages
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
