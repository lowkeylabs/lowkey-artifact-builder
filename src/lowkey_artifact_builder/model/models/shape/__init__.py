"""
Shape model definition.

The shape model defines parameterized geometric bodies that may consume
registered Artwork geometry.

The current declaration establishes registered structural Shape production,
registered composition, physical dimensionalization, optional outer-
and inner-ridge policy, physical-component discovery, and final artifact
packaging.

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
    VariantSpec,
)

from .stages import register_stage_implementations

# =========================================================
# Model definition
# =========================================================


MODEL = ModelSpec(
    name="shape",
    title="Shape",
    description=("Parameterized geometric body that may consume registered Artwork geometry."),
    variants=(
        VariantSpec(
            name="ornament",
            description=("Shape with an enabled outer ridge suitable for an ornament."),
            parameters={
                "shape_outer_ridge_width": 2.0,
            },
        ),
        VariantSpec(
            name="coaster",
            description=("Shape with an enabled outer ridge suitable for an ornament."),
            parameters={
                "shape_outer_ridge_width": 2.0,
            },
        ),
    ),
    stages=(
        StageSpec(
            id=10,
            name="structure",
            description=("Produce registered structural Shape geometry."),
            parameters=(
                "shape_geometry",
                "shape_sides",
                "shape_rotation",
            ),
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
            parameters=(
                "shape_size",
                "shape_outer_ridge_width",
                "shape_outer_ridge_style",
                "shape_inner_ridge_width",
                "shape_inner_to_outer_ridge_dist",
                "shape_border_label_width",
                "shape_border_label_max_glyph_height",
                "shape_border_label_arc_degrees",
                "shape_border_label_end_margin",
                "shape_border_label_font_family",
                "shape_top_border_label_text",
                "shape_bottom_border_label_text",
            ),
            products=(
                ProductSpec(
                    name="composition",
                    path="composition.svg",
                    description=("Registered composed Shape geometry."),
                ),
                ProductSpec(
                    name="manifest",
                    path="products.json",
                    description=("Manifest describing persistent registered Shape composition."),
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
                "shape_raise_style",
                "shape_outer_ridge_raise",
                "shape_outer_ridge_style",
                "shape_inner_ridge_raise",
                "shape_top_border_label_raise",
                "shape_bottom_border_label_raise",
                "shape_artwork_raise",
                "shape_artwork_fill_raise",
                "shape_hole_diameter",
                "shape_hole_position",
                "shape_hole_edge_distance",
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
            description=(
                "Assign physical colors and package physical Shape components "
                "into the final artifact."
            ),
            dependencies=("extrude",),
            parameters=(
                "printer_colors",
                "shape_base_color",
                "shape_outer_ridge_color",
                "shape_inner_ridge_color",
                "shape_top_border_label_color",
                "shape_bottom_border_label_color",
                "shape_artwork_fill_color",
                "shape_loop_color",
            ),
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
