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
    Mapping,
    Sequence,
)
from dataclasses import dataclass
from pathlib import Path
from typing import (
    Any,
    Protocol,
)

from lowkey_artifact_builder.colors import (
    ColorMatch,
    PaletteColor,
    match_color,
)

# =========================================================
# Resolver contract
# =========================================================


class ColorAnalysisResolver(Protocol):
    """
    Resolver capabilities required by Artwork color analysis.
    """

    def __call__(
        self,
        name: str,
    ) -> object: ...

    @property
    def colors(
        self,
    ) -> Mapping[str, Any]: ...


# =========================================================
# Analysis results
# =========================================================


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


# =========================================================
# Registered Artwork
# =========================================================


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
    Return one validated registered-Artwork RGB component.
    """

    value = color.get(component)

    if isinstance(value, bool) or not isinstance(value, int) or value < 0 or value > 255:
        raise ValueError(f"Registered Artwork color {name!r} has invalid {component} component.")

    return value


# =========================================================
# Registered Artwork analysis
# =========================================================


def analyze_registered_artwork_colors(
    *,
    manifest: Path,
    resolver: ColorAnalysisResolver,
) -> tuple[ArtworkColorMatch, ...]:
    """
    Analyze registered Artwork against resolved color availability.

    Artwork semantic colors are read from the persistent registered
    Artwork manifest.

    Printer and library candidates are selected by their resolved
    configuration values.

    Catalog-wide candidates are physical filament entries from the
    complete color catalog. Synthetic test entries remain available
    when explicitly selected by printer or library configuration but
    are excluded from physical catalog-wide matching.
    """

    artwork_colors = load_registered_artwork_colors(
        manifest,
    )

    printer_colors = _resolve_catalog_colors(
        resolver,
        "printer_colors",
    )

    library_colors = _resolve_catalog_colors(
        resolver,
        "library_colors",
    )

    catalog_colors = tuple(
        _palette_color(
            name,
            entry,
        )
        for name, entry in resolver.colors.items()
        if _is_physical_catalog_color(entry)
    )

    return analyze_color_matches(
        artwork_colors=artwork_colors,
        printer_colors=printer_colors,
        library_colors=library_colors,
        catalog_colors=catalog_colors,
    )


def _resolve_catalog_colors(
    resolver: ColorAnalysisResolver,
    parameter: str,
) -> tuple[PaletteColor, ...]:
    """
    Resolve catalog colors selected by an availability parameter.
    """

    names = resolver(parameter)

    if not isinstance(
        names,
        list | tuple,
    ):
        raise ValueError(f"{parameter} must be a list or tuple of color names.")

    colors: list[PaletteColor] = []

    for name in names:
        if not isinstance(
            name,
            str,
        ):
            raise ValueError(f"{parameter} must contain color names.")

        try:
            entry = resolver.colors[name]

        except KeyError as exc:
            raise ValueError(f"{parameter} references unknown color {name!r}.") from exc

        colors.append(
            _palette_color(
                name,
                entry,
            )
        )

    return tuple(colors)


# =========================================================
# Catalog conversion
# =========================================================


def _palette_color(
    name: str,
    entry: object,
) -> PaletteColor:
    """
    Convert one color-catalog entry to a generic palette color.
    """

    if not isinstance(
        entry,
        Mapping,
    ):
        raise ValueError(f"Color catalog entry {name!r} is invalid.")

    rgb = entry.get("rgb")

    if not isinstance(rgb, list | tuple) or len(rgb) != 3:
        raise ValueError(f"Color catalog entry {name!r} has invalid RGB.")

    return PaletteColor(
        name=name,
        rgb=(
            _catalog_rgb_component(
                rgb[0],
                name,
            ),
            _catalog_rgb_component(
                rgb[1],
                name,
            ),
            _catalog_rgb_component(
                rgb[2],
                name,
            ),
        ),
    )


def _catalog_rgb_component(
    value: object,
    name: str,
) -> int:
    """
    Return one validated catalog RGB component.
    """

    if isinstance(value, bool) or not isinstance(value, int) or value < 0 or value > 255:
        raise ValueError(f"Color catalog entry {name!r} has invalid RGB.")

    return value


def _is_physical_catalog_color(
    entry: object,
) -> bool:
    """
    Return whether a catalog entry represents physical filament.
    """

    return isinstance(entry, Mapping) and entry.get("manufacturer") != "test"


# =========================================================
# Color matching
# =========================================================


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

    synthetic_catalog_colors is retained temporarily for callers that
    supply generic candidate sets directly. Resolver-backed registered
    Artwork analysis derives physical catalog membership from catalog
    metadata instead.
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
    "ColorAnalysisResolver",
    "analyze_color_matches",
    "analyze_registered_artwork_colors",
    "load_registered_artwork_colors",
]
