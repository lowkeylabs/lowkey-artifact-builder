"""
Tests for Shape color analysis.
"""
# File: tests/model/shape/test_color_analysis.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from lowkey_artifact_builder.model.models.shape.color_analysis import (
    analyze_shape_colors,
)


class StubResolver:
    """
    Minimal resolved Shape configuration for color analysis.
    """

    def __init__(
        self,
        values: dict[str, object],
    ) -> None:
        self._values = values

    def __call__(
        self,
        name: str,
    ) -> object:
        return self._values[name]


def test_shape_color_analysis_exposes_base_semantic_color() -> None:
    """
    The Shape base retains its Model-owned semantic printing color.

    Structural Shape colors are already semantic physical colors and are not
    reassigned through Artwork physical-color assignment policy.
    """

    resolver = StubResolver(
        {
            "shape_base_color": "white",
            "shape_outer_ridge_width": 0.0,
            "shape_artwork_fill_color": "none",
        }
    )

    analysis = analyze_shape_colors(
        resolver=resolver,
    )

    assert len(analysis.colors) == 1

    color = analysis.colors[0]

    assert color.color == "white"
    assert color.used_by == ("base",)


def test_shape_color_analysis_groups_components_using_same_color() -> None:
    """
    Independently printable components sharing one semantic physical color
    occupy one color row.

    Component identity is preserved through used_by rather than by creating
    duplicate rows for the same color.
    """

    resolver = StubResolver(
        {
            "shape_base_color": "white",
            "shape_outer_ridge_width": 2.0,
            "shape_outer_ridge_color": "white",
            "shape_artwork_fill_color": "none",
        }
    )

    analysis = analyze_shape_colors(
        resolver=resolver,
    )

    assert len(analysis.colors) == 1

    color = analysis.colors[0]

    assert color.color == "white"
    assert color.used_by == (
        "base",
        "outer-ridge",
    )


def test_shape_color_analysis_separates_distinct_semantic_colors() -> None:
    """
    Participating Shape components with different semantic physical colors
    occupy separate color rows.
    """

    resolver = StubResolver(
        {
            "shape_base_color": "white",
            "shape_outer_ridge_width": 2.0,
            "shape_outer_ridge_color": "red",
            "shape_artwork_fill_color": "none",
        }
    )

    analysis = analyze_shape_colors(
        resolver=resolver,
    )

    assert len(analysis.colors) == 2

    base_color = analysis.colors[0]
    ridge_color = analysis.colors[1]

    assert base_color.color == "white"
    assert base_color.used_by == ("base",)

    assert ridge_color.color == "red"
    assert ridge_color.used_by == ("outer-ridge",)


def test_shape_color_analysis_includes_artwork_fill_semantic_color() -> None:
    """
    A participating Shape-owned Artwork fill contributes its semantic
    physical color to the color analysis.
    """

    resolver = StubResolver(
        {
            "shape_base_color": "white",
            "shape_outer_ridge_width": 0.0,
            "shape_artwork_fill_color": "black",
        }
    )

    analysis = analyze_shape_colors(
        resolver=resolver,
    )

    assert len(analysis.colors) == 2

    base_color = analysis.colors[0]
    fill_color = analysis.colors[1]

    assert base_color.color == "white"
    assert base_color.used_by == ("base",)

    assert fill_color.color == "black"
    assert fill_color.used_by == ("artwork-fill",)


def test_shape_color_analysis_groups_all_components_using_same_color() -> None:
    """
    All participating Shape-owned components sharing one semantic physical
    color occupy one color row.
    """

    resolver = StubResolver(
        {
            "shape_base_color": "white",
            "shape_outer_ridge_width": 2.0,
            "shape_outer_ridge_color": "white",
            "shape_artwork_fill_color": "white",
        }
    )

    analysis = analyze_shape_colors(
        resolver=resolver,
    )

    assert len(analysis.colors) == 1

    color = analysis.colors[0]

    assert color.color == "white"
    assert color.used_by == (
        "base",
        "outer-ridge",
        "artwork-fill",
    )
