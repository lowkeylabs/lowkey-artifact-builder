"""
Artwork color-assignment analysis.
"""
# File: src/lowkey_artifact_builder/model/models/artwork/color_analysis.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import (
    Any,
    Protocol,
)

from lowkey_artifact_builder.colors import (
    ColorAssignmentResult,
    MeasuredColor,
    PaletteColor,
    assign_colors,
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
class ArtworkColorAnalysis:
    """
    Color-assignment analysis for registered Artwork.

    printer_assignments:
        Optimal one-to-one assignment from persistent Artifact colors
        to the colors configured for the printer.

    library_assignments:
        Optimal one-to-one assignment from persistent Artifact colors
        to the colors configured for the user's filament library.

    catalog_assignments:
        Optimal one-to-one assignment from persistent Artifact colors
        to all physical colors in the color catalog.
    """

    printer_assignments: ColorAssignmentResult

    library_assignments: ColorAssignmentResult

    catalog_assignments: ColorAssignmentResult


# =========================================================
# Registered Artwork
# =========================================================


def load_registered_artwork_colors(
    manifest: Path,
) -> tuple[MeasuredColor, ...]:
    """
    Load persistent Artifact colors from a registered Artwork manifest.

    Artifact color identity and RGB are persistent Artwork semantics.
    Persisted printer assignments describe one physical realization and
    do not redefine the Artifact colors used for alternative assignment
    analysis.
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

    colors: list[MeasuredColor] = []

    for product in products:
        if not isinstance(
            product,
            dict,
        ):
            raise ValueError("Registered Artwork manifest contains an invalid product.")

        artifact_color = product.get(
            "artifact_color",
        )

        if not isinstance(
            artifact_color,
            dict,
        ):
            raise ValueError("Registered Artwork product has no valid Artifact color.")

        index = artifact_color.get(
            "index",
        )

        if (
            isinstance(
                index,
                bool,
            )
            or not isinstance(
                index,
                int,
            )
            or index < 1
        ):
            raise ValueError("Registered Artwork product has no valid Artifact color index.")

        rgb = artifact_color.get(
            "rgb",
        )

        if not isinstance(
            rgb,
            dict,
        ):
            raise ValueError(f"Registered Artwork Artifact color {index!r} has no valid RGB value.")

        colors.append(
            MeasuredColor(
                index=index,
                rgb=(
                    _rgb_component(
                        rgb,
                        "red",
                        index,
                    ),
                    _rgb_component(
                        rgb,
                        "green",
                        index,
                    ),
                    _rgb_component(
                        rgb,
                        "blue",
                        index,
                    ),
                ),
            )
        )

    return tuple(colors)


def _rgb_component(
    color: dict[str, Any],
    component: str,
    index: int,
) -> int:
    """
    Return one validated persistent Artifact RGB component.
    """

    value = color.get(
        component,
    )

    if (
        isinstance(
            value,
            bool,
        )
        or not isinstance(
            value,
            int,
        )
        or value < 0
        or value > 255
    ):
        raise ValueError(
            f"Registered Artwork Artifact color {index!r} has invalid {component} component."
        )

    return value


# =========================================================
# Registered Artwork analysis
# =========================================================


def analyze_registered_artwork_colors(
    *,
    manifest: Path,
    resolver: ColorAnalysisResolver,
) -> ArtworkColorAnalysis:
    """
    Analyze registered Artwork against three color-availability scopes.

    Persistent Artifact colors are the measured colors for every scope.

    Printer candidates are selected by resolved printer configuration.

    Library candidates are selected by resolved filament-library
    configuration.

    Catalog candidates include all physical catalog entries. Synthetic
    test entries remain available when explicitly selected by printer or
    library configuration but are excluded from catalog-wide analysis.

    Each scope is assigned independently using the generic globally
    optimal one-to-one color-assignment operation.
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
        if _is_physical_catalog_color(
            entry,
        )
    )

    printer_assignments = assign_colors(
        artwork_colors,
        printer_colors,
    )

    library_assignments = assign_colors(
        artwork_colors,
        library_colors,
    )

    catalog_assignments = assign_colors(
        artwork_colors,
        catalog_colors,
    )

    return ArtworkColorAnalysis(
        printer_assignments=printer_assignments,
        library_assignments=library_assignments,
        catalog_assignments=catalog_assignments,
    )


def _resolve_catalog_colors(
    resolver: ColorAnalysisResolver,
    parameter: str,
) -> tuple[PaletteColor, ...]:
    """
    Resolve catalog colors selected by an availability parameter.
    """

    names = resolver(
        parameter,
    )

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

    rgb = entry.get(
        "rgb",
    )

    if (
        not isinstance(
            rgb,
            list | tuple,
        )
        or len(rgb) != 3
    ):
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

    if (
        isinstance(
            value,
            bool,
        )
        or not isinstance(
            value,
            int,
        )
        or value < 0
        or value > 255
    ):
        raise ValueError(f"Color catalog entry {name!r} has invalid RGB.")

    return value


def _is_physical_catalog_color(
    entry: object,
) -> bool:
    """
    Return whether a catalog entry represents physical filament.
    """

    return (
        isinstance(
            entry,
            Mapping,
        )
        and entry.get("manufacturer") != "test"
    )


__all__ = [
    "ArtworkColorAnalysis",
    "ColorAnalysisResolver",
    "analyze_registered_artwork_colors",
    "load_registered_artwork_colors",
]
