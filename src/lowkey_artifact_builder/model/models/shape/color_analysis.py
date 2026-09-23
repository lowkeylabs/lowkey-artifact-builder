"""
Color analysis for Shape Realizations.

Shape-owned structural colors are semantic physical colors. They are
reported directly rather than reassigned through Artwork color-assignment
policy.
"""
# File: src/lowkey_artifact_builder/model/models/shape/color_analysis.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class ShapeColorResolver(Protocol):
    """
    Configuration resolver required by Shape color analysis.
    """

    def __call__(
        self,
        name: str,
    ) -> object:
        """
        Resolve one Shape configuration value.
        """
        ...


@dataclass(frozen=True)
class ShapeColor:
    """
    One independently printable semantic Shape color.
    """

    color: str
    used_by: tuple[str, ...]


@dataclass(frozen=True)
class ShapeColorAnalysis:
    """
    Color analysis for one Shape Realization.
    """

    colors: tuple[ShapeColor, ...]


def analyze_shape_colors(
    *,
    resolver: ShapeColorResolver,
) -> ShapeColorAnalysis:
    """
    Analyze semantic colors for one Shape Realization.

    Model-owned Shape colors already identify intended physical colors and
    therefore are not reassigned through Artwork color-assignment policy.

    Components sharing one semantic physical color occupy one color row.
    Component identity is preserved through that row's used_by membership.
    """

    base_color = resolver(
        "shape_base_color",
    )

    if not isinstance(
        base_color,
        str,
    ):
        raise TypeError("shape_base_color must resolve to a color name.")

    usage: dict[str, list[str]] = {
        base_color: [
            "base",
        ],
    }

    ridge_width = resolver(
        "shape_outer_ridge_width",
    )

    if not isinstance(
        ridge_width,
        int | float,
    ) or isinstance(
        ridge_width,
        bool,
    ):
        raise TypeError("shape_outer_ridge_width must resolve to a number.")

    if ridge_width > 0.0:
        ridge_color = resolver(
            "shape_outer_ridge_color",
        )

        if not isinstance(
            ridge_color,
            str,
        ):
            raise TypeError("shape_outer_ridge_color must resolve to a color name.")

        usage.setdefault(
            ridge_color,
            [],
        ).append(
            "outer-ridge",
        )

    artwork_fill_color = resolver(
        "shape_artwork_fill_color",
    )

    if artwork_fill_color is not None and artwork_fill_color != "none":
        if not isinstance(
            artwork_fill_color,
            str,
        ):
            raise TypeError("shape_artwork_fill_color must resolve to a color name or none.")

        usage.setdefault(
            artwork_fill_color,
            [],
        ).append(
            "artwork-fill",
        )

    return ShapeColorAnalysis(
        colors=tuple(
            ShapeColor(
                color=color,
                used_by=tuple(
                    used_by,
                ),
            )
            for color, used_by in usage.items()
        ),
    )


__all__ = [
    "ShapeColor",
    "ShapeColorAnalysis",
    "ShapeColorResolver",
    "analyze_shape_colors",
]
