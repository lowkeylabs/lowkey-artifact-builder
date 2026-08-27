"""
Shape model definition.

The shape model defines parameterized geometric bodies that may consume
registered Artwork geometry.

The current declaration establishes registered structural Shape production,
registered composition, and the physical dimensionalization boundary without
prematurely declaring later ridge or packaging behavior.
"""
# File: src/lowkey_artifact_builder/model/models/shape/__init__.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from lowkey_artifact_builder.model.registry import ModelRegistry
from lowkey_artifact_builder.model.specs import (
    ModelSpec,
    ProductDependencySpec,
    ProductSpec,
    StageSpec,
)

from .stages import register_stage_implementations

# =========================================================
# Model definition
# =========================================================


MODEL = ModelSpec(
    name="shape",
    title="Shape",
    description=("Parameterized geometric body that may consume registered Artwork geometry."),
    stages=(
        StageSpec(
            id=10,
            name="structure",
            description=("Produce registered structural Shape geometry."),
            parameters=("shape_geometry",),
            products=(
                ProductSpec(
                    name="structure",
                    path="structure.svg",
                    description=("Registered structural Shape geometry."),
                ),
            ),
        ),
        StageSpec(
            id=20,
            name="compose",
            description=("Compose registered structural Shape and Artwork geometry."),
            dependencies=("structure",),
            product_dependencies=(
                ProductDependencySpec(
                    model="artwork",
                    stage="vector",
                    product="manifest",
                ),
            ),
            products=(
                ProductSpec(
                    name="composition",
                    path="composition.svg",
                    description=("Registered composed Shape geometry."),
                ),
            ),
        ),
        StageSpec(
            id=30,
            name="extrude",
            description=("Dimensionalize and extrude registered Shape geometry."),
            dependencies=("compose",),
            parameters=(
                "shape_size",
                "shape_base_raise",
            ),
            products=(
                ProductSpec(
                    name="base",
                    path="base.3mf",
                    description=("Physical structural Shape base geometry."),
                ),
            ),
        ),
    ),
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


__all__ = [
    "register_models",
    "register_stage_implementations",
]
