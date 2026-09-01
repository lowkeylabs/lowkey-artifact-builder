"""
Artwork color-match analysis.
"""
# File: src/lowkey_artifact_builder/model/models/artwork/color_analysis.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
from collections.abc import (
    Collection,
    Sequence,
)
from dataclasses import dataclass
from pathlib import Path
from typing import Any

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


def load_registered_artwork_colors(
    manifest: Path,
) -> tuple[PaletteColor, ...]:
    """
    Load semantic colors from a registered Artwork vector manifest.
    """

    data = json.loads(
        manifest.read_text(
            encoding="utf-8",
        )
    )

    products = data.get("products")

    if not isinstance(
        products,
        list,
    ):
        raise ValueError("Registered Artwork manifest does not contain a products list.")

    colors: list[PaletteColor] = []

    for product in products:
        if not isinstance(
            product,
            dict,
        ):
            raise ValueError("Registered Artwork manifest contains an invalid product.")

        name = product.get("name")
        color = product.get("color")

        if not isinstance(name, str) or not name.strip():
            raise ValueError("Registered Artwork product has no valid color name.")

        if not isinstance(
            color,
            dict,
        ):
            raise ValueError(f"Registered Artwork color {name!r} has no valid RGB value.")

        colors.append(
            PaletteColor(
                name=name.strip(),
                rgb=(
                    _rgb_component(
                        color,
                        "red",
                        name,
                    ),
                    _rgb_component(
                        color,
                        "green",
                        name,
                    ),
                    _rgb_component(
                        color,
                        "blue",
                        name,
                    ),
                ),
            )
        )

    return tuple(colors)


def _rgb_component(
    color: dict[str, Any],
    component: str,
    name: str,
) -> int:
    """
    Return one validated RGB component.
    """

    value = color.get(component)

    if isinstance(value, bool) or not isinstance(value, int) or value < 0 or value > 255:
        raise ValueError(f"Registered Artwork color {name!r} has invalid {component} component.")

    return value


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
    "load_registered_artwork_colors",
]
