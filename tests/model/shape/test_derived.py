"""
Tests for Shape derived configuration.
"""
# File: tests/model/shape/test_derived.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path

import pytest

from lowkey_artifact_builder.colors import (
    ColorError,
    PaletteColor,
    resolve_palette_color,
)
from lowkey_artifact_builder.config import (
    get_resolver,
    write_artifact_config,
)

# =========================================================
# Color resolution
# =========================================================


def test_shape_base_color_resolves_through_shared_color_mechanism(
    tmp_path: Path,
) -> None:
    """
    A Shape base color uses the shared semantic color mechanism.
    """

    resolver = get_resolver(
        "shape-example",
        model="shape",
        project_root=tmp_path,
    )

    color = resolve_palette_color(
        resolver("shape_base_color"),
        resolver.colors,
    )

    assert color == PaletteColor(
        name="white",
        rgb=(227, 228, 212),
    )


def test_shape_derived_ridge_color_resolves_through_shared_color_mechanism(
    tmp_path: Path,
) -> None:
    """
    A derived Shape ridge color uses the shared semantic color mechanism.

    Configured catalog colors take precedence over CSS fallback colors.
    """

    write_artifact_config(
        "shape-example",
        {
            "model": "shape",
            "parameters": {
                "shape_base_color": "red",
            },
        },
        project_root=tmp_path,
    )

    resolver = get_resolver(
        "shape-example",
        project_root=tmp_path,
    )

    color = resolve_palette_color(
        resolver("shape_outer_ridge_color"),
        resolver.colors,
    )

    assert color == PaletteColor(
        name="red",
        rgb=(180, 2, 0),
    )


def test_shape_explicit_ridge_color_resolves_independently(
    tmp_path: Path,
) -> None:
    """
    An explicit Shape ridge color resolves independently of the base color.
    """

    write_artifact_config(
        "shape-example",
        {
            "model": "shape",
            "parameters": {
                "shape_base_color": "white",
                "shape_outer_ridge_color": "black",
            },
        },
        project_root=tmp_path,
    )

    resolver = get_resolver(
        "shape-example",
        project_root=tmp_path,
    )

    base = resolve_palette_color(
        resolver("shape_base_color"),
        resolver.colors,
    )

    ridge = resolve_palette_color(
        resolver("shape_outer_ridge_color"),
        resolver.colors,
    )

    assert base.name == "white"
    assert ridge.name == "black"
    assert base.rgb != ridge.rgb


def test_invalid_shape_color_fails_through_shared_color_mechanism(
    tmp_path: Path,
) -> None:
    """
    An unknown Shape color is rejected by shared color resolution.
    """

    write_artifact_config(
        "shape-example",
        {
            "model": "shape",
            "parameters": {
                "shape_base_color": "not-a-real-color",
            },
        },
        project_root=tmp_path,
    )

    resolver = get_resolver(
        "shape-example",
        project_root=tmp_path,
    )

    with pytest.raises(
        ColorError,
        match="not configured and is not a recognized CSS color",
    ):
        resolve_palette_color(
            resolver("shape_base_color"),
            resolver.colors,
        )
