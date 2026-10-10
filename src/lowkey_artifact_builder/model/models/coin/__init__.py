"""
Coin model definition.

The coin model composes exactly two complete packaged Shape Products as
opposite Faces of one physical object.

The current declaration establishes the packaged Face dependency contract,
physical Coin composition, and final Coin packaging.
"""
# File: src/lowkey_artifact_builder/model/models/coin/__init__.py
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
    name="coin",
    title="Coin",
    description=("Two-sided physical object composed from two complete packaged Shape Products."),
    stages=(
        StageSpec(
            id=10,
            name="compose",
            description=(
                "Compose two complete packaged Shape Products as opposite "
                "Faces of one physical Coin."
            ),
            product_dependencies=(
                ProductDependencySpec(
                    name="faceA",
                    model="shape",
                    variant="default",
                    stage="package",
                    product="artifact",
                ),
                ProductDependencySpec(
                    name="faceB",
                    model="shape",
                    variant="inlaid",
                    stage="package",
                    product="artifact",
                ),
            ),
            parameters=("coin_orientation",),
            products=(
                ProductSpec(
                    name="physical",
                    path="products.json",
                    description=(
                        "Manifest describing the complete physical Coin component collection."
                    ),
                ),
            ),
        ),
        StageSpec(
            id=20,
            name="package",
            description=(
                "Package the complete physical Coin component collection into the final artifact."
            ),
            dependencies=("compose",),
            products=(
                ProductSpec(
                    name="artifact",
                    path="artifact.3mf",
                    description=("Final packaged Coin artifact."),
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
