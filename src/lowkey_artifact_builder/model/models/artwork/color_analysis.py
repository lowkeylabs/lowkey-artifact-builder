"""
Artwork color-match analysis.
"""
# File: src/lowkey_artifact_builder/model/models/artwork/color_analysis.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from collections.abc import (
    Collection,
    Sequence,
)
from dataclasses import dataclass

from lowkey_artifact_builder.colors import (
    ColorMatch,
    PaletteColor,
    match_color,
)


@dataclass(
    frozen=True,
    slots=True,
)
class ArtworkColorMatch:
    """
    Color-match analysis for one prepared Artwork semantic color.
    """

    artwork: PaletteColor

    printer: ColorMatch

    library: ColorMatch

    catalog: ColorMatch


def analyze_color_matches(
    *,
    artwork_colors: Sequence[PaletteColor],
    printer_colors: Sequence[PaletteColor],
    library_colors: Sequence[PaletteColor],
    catalog_colors: Sequence[PaletteColor],
    synthetic_catalog_colors: Collection[str] = (),
) -> tuple[ArtworkColorMatch, ...]:
    """
    Analyze prepared Artwork colors against available color scopes.

    Each prepared Artwork semantic color is independently matched
    against printer, library, and physical-catalog candidates.
    """

    physical_catalog_colors = tuple(
        color for color in catalog_colors if color.name not in synthetic_catalog_colors
    )

    return tuple(
        ArtworkColorMatch(
            artwork=artwork,
            printer=match_color(
                artwork,
                printer_colors,
            ),
            library=match_color(
                artwork,
                library_colors,
            ),
            catalog=match_color(
                artwork,
                physical_catalog_colors,
            ),
        )
        for artwork in artwork_colors
    )


__all__ = [
    "ArtworkColorMatch",
    "analyze_color_matches",
]
