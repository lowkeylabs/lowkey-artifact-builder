"""
Tests for reusable Shape Variants.

Shape Variants are sparse parameter overrides over Shape Model defaults.
Feature participation remains determined by Shape-owned parameter
semantics.
"""
# File: tests/model/shape/test_variants.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from lowkey_artifact_builder.model.models.shape import MODEL


def test_shape_exposes_default_and_ornament_variants() -> None:
    """
    Shape exposes ordinary behavior as default and a reusable ornament
    configuration.
    """

    assert tuple(variant.name for variant in MODEL.variants) == (
        "default",
        "ornament",
    )


def test_shape_ornament_variant_is_sparse() -> None:
    """
    The ornament Variant enables its outer ridge by overriding only the
    parameter that distinguishes it from ordinary Shape behavior.

    Ridge participation is determined by Shape's existing
    shape_outer_ridge_width semantics rather than by Variant-owned Feature
    selection.
    """

    default = next(variant for variant in MODEL.variants if variant.name == "default")

    ornament = next(variant for variant in MODEL.variants if variant.name == "ornament")

    assert default.parameters == {}

    assert ornament.parameters == {
        "shape_outer_ridge_width": 2.0,
    }
