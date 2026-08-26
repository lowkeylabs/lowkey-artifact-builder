"""
Shape artifact model.

Defines and registers the Shape model.
"""
# File: src/lowkey_artifact_builder/model/models/shape/__init__.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from lowkey_artifact_builder.model.registry import ModelRegistry
from lowkey_artifact_builder.model.specs import ModelSpec

# =========================================================
# Model specification
# =========================================================


MODEL = ModelSpec(
    name="shape",
    title="Shape",
    description=(
        "Parameterized two-dimensional structural geometry for printable physical objects."
    ),
    stages=(),
    defined_in=__name__,
)


# =========================================================
# Registration
# =========================================================


def register_models(
    registry: ModelRegistry,
) -> None:
    """Register models defined by this package."""

    registry.register_model(
        MODEL,
    )


__all__ = [
    "MODEL",
    "register_models",
]
