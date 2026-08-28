"""
Shape model definition.

The shape model defines parameterized geometric bodies that may consume
registered Artwork geometry.

The current declaration establishes registered structural Shape production,
registered composition, physical dimensionalization, optional outer-ridge
policy, physical-component discovery, and final artifact packaging.
"""
# File: src/lowkey_artifact_builder/model/models/shape/__init__.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from lowkey_artifact_builder.model.registry import ModelRegistry
from lowkey_artifact_builder.model.specs import (
    ModelSpec,
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
            product_dependencies=(),
            parameters=(
                "shape_size",
                "shape_outer_ridge_width",
                "shape_outer_ridge_style",
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
            description=(
                "Dimensionalize registered Shape geometry and produce "
                "independently printable physical components."
            ),
            dependencies=("compose",),
            parameters=(
                "shape_size",
                "shape_base_raise",
                "shape_base_color",
                "shape_outer_ridge_raise",
                "shape_outer_ridge_style",
                "shape_outer_ridge_color",
            ),
            products=(
                ProductSpec(
                    name="manifest",
                    path="products.json",
                    description=(
                        "Manifest describing independently printable physical Shape components."
                    ),
                ),
            ),
        ),
        StageSpec(
            id=40,
            name="package",
            description=("Package physical Shape components into the final artifact."),
            dependencies=("extrude",),
            products=(
                ProductSpec(
                    name="artifact",
                    path="artifact.3mf",
                    description=("Final packaged Shape artifact."),
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
