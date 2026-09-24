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

from collections.abc import Mapping
from dataclasses import dataclass
from typing import (
    Any,
    Protocol,
)

from lowkey_artifact_builder.colors import (
    PaletteColor,
    color_distance,
    resolve_palette,
    resolve_palette_color,
)


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

    @property
    def colors(
        self,
    ) -> Mapping[str, Any]:
        """
        Return the configured physical-color catalog.
        """
        ...


@dataclass(frozen=True)
class ShapeColorCandidate:
    """
    Advisory comparison of a semantic Shape color with one candidate color.
    """

    name: str
    distance: float


@dataclass(frozen=True)
class ShapeColor:
    """
    One independently printable semantic Shape color.
    """

    color: str
    used_by: tuple[str, ...]
    printer_candidate: ShapeColorCandidate


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

    The effective Printer palette is compared independently with each
    semantic Shape color. The nearest Printer color is advisory and does
    not replace the semantic color identity.
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

    printer_colors = _resolve_printer_colors(
        resolver,
    )

    return ShapeColorAnalysis(
        colors=tuple(
            ShapeColor(
                color=color,
                used_by=tuple(
                    used_by,
                ),
                printer_candidate=_nearest_candidate(
                    semantic_color=color,
                    candidates=printer_colors,
                    resolver=resolver,
                ),
            )
            for color, used_by in usage.items()
        ),
    )


def _resolve_printer_colors(
    resolver: ShapeColorResolver,
) -> tuple[PaletteColor, ...]:
    """
    Resolve the effective Printer palette used for advisory comparison.
    """

    names = resolver(
        "printer_colors",
    )

    if isinstance(
        names,
        str | bytes,
    ) or not isinstance(
        names,
        list | tuple,
    ):
        raise ValueError("printer_colors must be a list or tuple of color names.")

    return resolve_palette(
        names,
        resolver.colors,
    )


def _nearest_candidate(
    *,
    semantic_color: str,
    candidates: tuple[PaletteColor, ...],
    resolver: ShapeColorResolver,
) -> ShapeColorCandidate:
    """
    Return the nearest advisory candidate for one semantic Shape color.

    This is an independent comparison, not a one-to-one Artwork-style
    physical-color assignment.
    """

    semantic = resolve_palette_color(
        semantic_color,
        resolver.colors,
    )

    candidate = min(
        candidates,
        key=lambda color: color_distance(
            semantic.rgb,
            color.rgb,
        ),
    )

    return ShapeColorCandidate(
        name=candidate.name,
        distance=color_distance(
            semantic.rgb,
            candidate.rgb,
        ),
    )


__all__ = [
    "ShapeColor",
    "ShapeColorAnalysis",
    "ShapeColorCandidate",
    "ShapeColorResolver",
    "analyze_shape_colors",
]
