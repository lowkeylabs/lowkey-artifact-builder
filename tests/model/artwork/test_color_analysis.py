"""
Tests for Artwork color-match analysis.
"""
# File: tests/model/artwork/test_color_analysis.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from lowkey_artifact_builder.colors import PaletteColor
from lowkey_artifact_builder.model.models.artwork.color_analysis import (
    analyze_color_matches,
)


def test_artwork_color_analysis_matches_each_prepared_color_independently() -> None:
    """
    Every prepared Artwork semantic color receives its own color matches.
    """

    artwork_colors = (
        PaletteColor(
            name="artwork-red",
            rgb=(240, 20, 20),
        ),
        PaletteColor(
            name="artwork-green",
            rgb=(20, 180, 40),
        ),
    )

    printer_colors = (
        PaletteColor(
            name="printer-red",
            rgb=(255, 0, 0),
        ),
        PaletteColor(
            name="printer-green",
            rgb=(0, 150, 0),
        ),
    )

    library_colors = (
        PaletteColor(
            name="library-red",
            rgb=(245, 10, 10),
        ),
        PaletteColor(
            name="library-green",
            rgb=(10, 190, 30),
        ),
    )

    catalog_colors = (
        PaletteColor(
            name="catalog-red",
            rgb=(241, 19, 19),
        ),
        PaletteColor(
            name="catalog-green",
            rgb=(19, 181, 39),
        ),
    )

    analysis = analyze_color_matches(
        artwork_colors=artwork_colors,
        printer_colors=printer_colors,
        library_colors=library_colors,
        catalog_colors=catalog_colors,
    )

    assert tuple(result.artwork for result in analysis) == artwork_colors

    assert tuple(result.printer.color.name for result in analysis) == (
        "printer-red",
        "printer-green",
    )

    assert tuple(result.library.color.name for result in analysis) == (
        "library-red",
        "library-green",
    )

    assert tuple(result.catalog.color.name for result in analysis) == (
        "catalog-red",
        "catalog-green",
    )


def test_artwork_color_analysis_preserves_semantic_color_information() -> None:
    """
    Analysis preserves Artwork and matched filament identities and RGB values.
    """

    artwork = PaletteColor(
        name="artwork-red",
        rgb=(240, 20, 20),
    )

    printer = PaletteColor(
        name="fire-engine-red",
        rgb=(255, 0, 0),
    )

    result = analyze_color_matches(
        artwork_colors=(artwork,),
        printer_colors=(printer,),
        library_colors=(printer,),
        catalog_colors=(printer,),
    )[0]

    assert result.artwork is artwork

    assert result.artwork.name == "artwork-red"
    assert result.artwork.rgb == (240, 20, 20)

    assert result.printer.color is printer
    assert result.printer.color.name == "fire-engine-red"
    assert result.printer.color.rgb == (255, 0, 0)

    assert result.printer.distance > 0.0


def test_artwork_color_analysis_keeps_availability_scopes_independent() -> None:
    """
    Printer, library, and catalog matching use their own candidate sets.
    """

    artwork = PaletteColor(
        name="artwork",
        rgb=(250, 10, 10),
    )

    printer = PaletteColor(
        name="printer-only",
        rgb=(0, 0, 0),
    )

    library = PaletteColor(
        name="library-only",
        rgb=(200, 0, 0),
    )

    catalog = PaletteColor(
        name="catalog-only",
        rgb=(250, 0, 0),
    )

    result = analyze_color_matches(
        artwork_colors=(artwork,),
        printer_colors=(printer,),
        library_colors=(library,),
        catalog_colors=(catalog,),
    )[0]

    assert result.printer.color is printer
    assert result.library.color is library
    assert result.catalog.color is catalog

    assert result.catalog.distance < result.library.distance
    assert result.library.distance < result.printer.distance
