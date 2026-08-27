"""
Shape model definition.

The shape model defines parameterized geometric bodies that may consume
registered Artwork geometry.

The model is intentionally introduced incrementally. Its current declaration
establishes the registered-geometry consumer boundary without prematurely
declaring later structural, extrusion, or packaging behavior.
"""
# File: src/lowkey_artifact_builder/model/models/shape/__init__.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from lowkey_artifact_builder.model.registry import ModelRegistry
from lowkey_artifact_builder.model.specs import (
    ModelSpec,
    ProductDependencySpec,
    StageSpec,
)

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
            name="compose",
            description=("Consume registered Artwork geometry for Shape composition."),
            product_dependencies=(
                ProductDependencySpec(
                    model="artwork",
                    stage="vector",
                    product="manifest",
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
