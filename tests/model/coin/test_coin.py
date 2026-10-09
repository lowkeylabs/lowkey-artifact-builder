"""Tests for the coin model."""
# File: tests/model/coin/test_coin.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from lowkey_artifact_builder.model import (
    build_model_registry,
)
from lowkey_artifact_builder.model.models.coin import MODEL


def test_coin_declares_physical_composition_model() -> None:
    """
    Coin declares the reusable physical-composition contract.

    Coin consumes exactly two complete packaged Shape Products through
    independent Face roles and exposes its physical composition independently
    of final packaging.
    """

    registry = build_model_registry()

    assert registry.get_model("coin") is MODEL

    assert tuple(variant.name for variant in MODEL.variants) == ("default",)

    assert "coin_orientation" in MODEL.parameters

    product_dependencies = tuple(
        dependency for stage in MODEL.stages for dependency in stage.product_dependencies
    )

    assert tuple(dependency.name for dependency in product_dependencies) == (
        "faceA",
        "faceB",
    )

    assert {
        (
            dependency.model,
            dependency.stage,
            dependency.product,
        )
        for dependency in product_dependencies
    } == {
        (
            "shape",
            "package",
            "artifact",
        ),
    }

    products = {product.name for stage in MODEL.stages for product in stage.products}

    assert "physical" in products
    assert "artifact" in products
