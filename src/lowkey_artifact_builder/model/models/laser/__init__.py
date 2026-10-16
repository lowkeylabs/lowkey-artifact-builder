"""
Laser model declaration.

Laser packages registered Shape composition into two-dimensional
manufacturing Products without Shape extrusion or 3MF packaging.
"""
# File: src/lowkey_artifact_builder/model/models/laser/__init__.py
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

MODEL = ModelSpec(
    name="laser",
    title="Laser",
    description="Two-dimensional manufacturing from registered Shape composition.",
    stages=(
        StageSpec(
            id=10,
            name="package",
            description="Package registered Shape geometry into a laser-ready SVG.",
            product_dependencies=(
                ProductDependencySpec(
                    model="shape",
                    stage="compose",
                    product="manifest",
                ),
            ),
            parameters=("shape_size",),
            products=(
                ProductSpec(
                    name="artifact",
                    path="artifact.svg",
                    description="Manufacturing-ready SVG.",
                ),
            ),
        ),
    ),
)


def register_models(registry: ModelRegistry) -> None:
    registry.register_model(MODEL)


__all__ = [
    "register_models",
    "register_stage_implementations",
]
