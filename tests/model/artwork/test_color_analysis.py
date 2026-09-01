"""
Tests for Artwork color-match analysis.
"""
# File: tests/model/artwork/test_color_analysis.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
from pathlib import Path

from lowkey_artifact_builder.colors import (
    PaletteColor,
)
from lowkey_artifact_builder.model.models.artwork.color_analysis import (
    analyze_color_matches,
    analyze_registered_artwork_colors,
    load_registered_artwork_colors,
)

# =========================================================
# Test support
# =========================================================


class StubColorResolver:
    """
    Resolver-compatible configuration and color-catalog source.
    """

    def __init__(
        self,
        *,
        values: dict[str, object],
        colors: dict[str, object],
    ) -> None:
        self._values = values
        self._colors = colors

    def __call__(
        self,
        name: str,
    ) -> object:
        return self._values[name]

    @property
    def colors(
        self,
    ) -> dict[str, object]:
        return self._colors


def _catalog_color(
    *,
    manufacturer: str,
    rgb: tuple[int, int, int],
) -> dict[str, object]:
    """
    Return one color-catalog entry.
    """

    return {
        "manufacturer": manufacturer,
        "filament": "Test Filament",
        "rgb": list(rgb),
    }


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


def test_artwork_color_analysis_matches_supplied_catalog_candidates_without_policy() -> None:
    """
    Direct color matching applies no physical-catalog selection policy.
    """

    artwork = PaletteColor(
        name="artwork-red",
        rgb=(255, 0, 0),
    )

    synthetic = PaletteColor(
        name="test-red",
        rgb=(255, 0, 0),
    )

    physical = PaletteColor(
        name="physical-red",
        rgb=(240, 0, 0),
    )

    result = analyze_color_matches(
        artwork_colors=(artwork,),
        printer_colors=(physical,),
        library_colors=(physical,),
        catalog_colors=(
            synthetic,
            physical,
        ),
    )[0]

    assert result.catalog.color is synthetic
    assert result.catalog.distance == 0.0


# =========================================================
# Registered Artwork colors
# =========================================================


def test_registered_artwork_colors_are_loaded_from_vector_manifest(
    tmp_path: Path,
) -> None:
    """
    Prepared Artwork semantic colors come from registered Artwork.
    """

    manifest = tmp_path / "products.json"

    manifest.write_text(
        json.dumps(
            {
                "registered_extent": 100,
                "products": [
                    {
                        "index": 1,
                        "path": "color-1.svg",
                        "name": "prepared-red",
                        "color": {
                            "red": 241,
                            "green": 17,
                            "blue": 23,
                        },
                    },
                    {
                        "index": 2,
                        "path": "color-2.svg",
                        "name": "prepared-blue",
                        "color": {
                            "red": 19,
                            "green": 31,
                            "blue": 227,
                        },
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    colors = load_registered_artwork_colors(
        manifest,
    )

    assert colors == (
        PaletteColor(
            name="prepared-red",
            rgb=(241, 17, 23),
        ),
        PaletteColor(
            name="prepared-blue",
            rgb=(19, 31, 227),
        ),
    )


def test_registered_artwork_colors_preserve_manifest_order(
    tmp_path: Path,
) -> None:
    """
    Registered Artwork color order follows the persistent manifest.
    """

    manifest = tmp_path / "products.json"

    manifest.write_text(
        json.dumps(
            {
                "registered_extent": 100,
                "products": [
                    {
                        "index": 2,
                        "path": "second.svg",
                        "name": "second",
                        "color": {
                            "red": 20,
                            "green": 30,
                            "blue": 40,
                        },
                    },
                    {
                        "index": 1,
                        "path": "first.svg",
                        "name": "first",
                        "color": {
                            "red": 50,
                            "green": 60,
                            "blue": 70,
                        },
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    colors = load_registered_artwork_colors(
        manifest,
    )

    assert tuple(color.name for color in colors) == (
        "second",
        "first",
    )


def test_registered_artwork_colors_drive_color_analysis(
    tmp_path: Path,
) -> None:
    """
    Color analysis can consume semantic colors persisted by registered Artwork.
    """

    manifest = tmp_path / "products.json"

    manifest.write_text(
        json.dumps(
            {
                "registered_extent": 100,
                "products": [
                    {
                        "index": 1,
                        "path": "color-1.svg",
                        "name": "prepared-red",
                        "color": {
                            "red": 250,
                            "green": 10,
                            "blue": 10,
                        },
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    artwork_colors = load_registered_artwork_colors(
        manifest,
    )

    analysis = analyze_color_matches(
        artwork_colors=artwork_colors,
        printer_colors=(
            PaletteColor(
                name="printer-red",
                rgb=(240, 0, 0),
            ),
        ),
        library_colors=(
            PaletteColor(
                name="library-red",
                rgb=(245, 5, 5),
            ),
        ),
        catalog_colors=(
            PaletteColor(
                name="catalog-red",
                rgb=(249, 9, 9),
            ),
        ),
    )

    assert analysis[0].artwork == PaletteColor(
        name="prepared-red",
        rgb=(250, 10, 10),
    )


def test_registered_artwork_analysis_uses_resolved_availability(
    tmp_path: Path,
) -> None:
    """
    Registered Artwork analysis uses resolved printer and library colors.
    """

    manifest = tmp_path / "products.json"

    manifest.write_text(
        json.dumps(
            {
                "registered_extent": 100,
                "products": [
                    {
                        "index": 1,
                        "path": "color-1.svg",
                        "name": "artwork-red",
                        "color": {
                            "red": 250,
                            "green": 10,
                            "blue": 10,
                        },
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    resolver = StubColorResolver(
        values={
            "printer_colors": ["printer-red"],
            "library_colors": ["library-red"],
        },
        colors={
            "printer-red": _catalog_color(
                manufacturer="eSUN",
                rgb=(220, 0, 0),
            ),
            "library-red": _catalog_color(
                manufacturer="eSUN",
                rgb=(240, 5, 5),
            ),
            "catalog-red": _catalog_color(
                manufacturer="eSUN",
                rgb=(249, 9, 9),
            ),
        },
    )

    analysis = analyze_registered_artwork_colors(
        manifest=manifest,
        resolver=resolver,
    )

    assert analysis[0].artwork.name == "artwork-red"
    assert analysis[0].printer.color.name == "printer-red"
    assert analysis[0].library.color.name == "library-red"
    assert analysis[0].catalog.color.name == "catalog-red"


def test_registered_artwork_analysis_excludes_synthetic_catalog_entries(
    tmp_path: Path,
) -> None:
    """
    Catalog matching derives physical candidates from catalog metadata.
    """

    manifest = tmp_path / "products.json"

    manifest.write_text(
        json.dumps(
            {
                "registered_extent": 100,
                "products": [
                    {
                        "index": 1,
                        "path": "color-1.svg",
                        "name": "artwork-red",
                        "color": {
                            "red": 255,
                            "green": 0,
                            "blue": 0,
                        },
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    resolver = StubColorResolver(
        values={
            "printer_colors": ["test-red"],
            "library_colors": ["test-red"],
        },
        colors={
            "test-red": _catalog_color(
                manufacturer="test",
                rgb=(255, 0, 0),
            ),
            "physical-red": _catalog_color(
                manufacturer="eSUN",
                rgb=(240, 0, 0),
            ),
        },
    )

    analysis = analyze_registered_artwork_colors(
        manifest=manifest,
        resolver=resolver,
    )

    assert analysis[0].printer.color.name == "test-red"
    assert analysis[0].library.color.name == "test-red"
    assert analysis[0].catalog.color.name == "physical-red"


def test_registered_artwork_analysis_does_not_mutate_configuration(
    tmp_path: Path,
) -> None:
    """
    Artwork color analysis does not mutate resolved color configuration.
    """

    manifest = tmp_path / "products.json"

    manifest.write_text(
        json.dumps(
            {
                "registered_extent": 100,
                "products": [
                    {
                        "index": 1,
                        "path": "color-1.svg",
                        "name": "artwork-red",
                        "color": {
                            "red": 250,
                            "green": 10,
                            "blue": 10,
                        },
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    printer_colors = ["printer-red"]
    library_colors = ["library-red"]

    resolver = StubColorResolver(
        values={
            "printer_colors": printer_colors,
            "library_colors": library_colors,
        },
        colors={
            "printer-red": _catalog_color(
                manufacturer="eSUN",
                rgb=(220, 0, 0),
            ),
            "library-red": _catalog_color(
                manufacturer="eSUN",
                rgb=(240, 5, 5),
            ),
            "catalog-red": _catalog_color(
                manufacturer="eSUN",
                rgb=(249, 9, 9),
            ),
        },
    )

    analyze_registered_artwork_colors(
        manifest=manifest,
        resolver=resolver,
    )

    assert printer_colors == ["printer-red"]
    assert library_colors == ["library-red"]
