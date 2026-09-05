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

from pathlib import Path

from lowkey_artifact_builder.config import (
    get_resolver,
    write_artifact_config,
)
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


def test_shape_default_resolves_ordinary_model_configuration(
    tmp_path: Path,
) -> None:
    """
    The Shape default Variant preserves ordinary Model behavior.
    """

    write_artifact_config(
        "example",
        {
            "model": "shape",
        },
        project_root=tmp_path,
    )

    resolver = get_resolver(
        "example",
        project_root=tmp_path,
    )

    assert resolver("variant") == "default"

    assert resolver("shape_size") == 100.0
    assert resolver("shape_outer_ridge_width") == 0.0
    assert resolver("shape_outer_ridge_raise") == 1.0
    assert resolver("shape_outer_ridge_style") == "integrated"

    assert resolver.source("shape_size") == "model"
    assert resolver.source("shape_outer_ridge_width") == "model"
    assert resolver.source("shape_outer_ridge_raise") == "model"
    assert resolver.source("shape_outer_ridge_style") == "model"


def test_shape_ornament_resolves_sparse_override_over_model_defaults(
    tmp_path: Path,
) -> None:
    """
    The Shape ornament Variant changes only its declared override.

    Other effective Shape configuration continues to come from Model
    defaults without Artifact-specific customization.
    """

    write_artifact_config(
        "example",
        {
            "model": "shape",
            "variant": "ornament",
        },
        project_root=tmp_path,
    )

    resolver = get_resolver(
        "example",
        project_root=tmp_path,
    )

    assert resolver("variant") == "ornament"

    assert resolver("shape_size") == 100.0
    assert resolver("shape_outer_ridge_width") == 2.0
    assert resolver("shape_outer_ridge_raise") == 1.0
    assert resolver("shape_outer_ridge_style") == "integrated"

    assert resolver.source("shape_size") == "model"
    assert resolver.source("shape_outer_ridge_width") == "variant 'ornament'"
    assert resolver.source("shape_outer_ridge_raise") == "model"
    assert resolver.source("shape_outer_ridge_style") == "model"
