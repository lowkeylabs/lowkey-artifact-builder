"""
Tests for Artwork color-assignment analysis.
"""
# File: tests/model/artwork/test_color_analysis.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

import pytest

from lowkey_artifact_builder.colors import (
    ColorError,
    MeasuredColor,
)
from lowkey_artifact_builder.model.models.artwork.color_analysis import (
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
        values: Mapping[str, object],
        colors: Mapping[str, object],
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
    ) -> Mapping[str, object]:
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


def _registered_artwork_product(
    *,
    index: int,
    artifact_rgb: tuple[int, int, int],
    printer_name: str,
    printer_rgb: tuple[int, int, int],
    distance: float,
) -> dict[str, object]:
    """
    Return one registered Artwork product using the persistent color schema.
    """

    return {
        "index": index,
        "path": f"color-{index}.svg",
        "artifact_color": {
            "index": index,
            "rgb": {
                "red": artifact_rgb[0],
                "green": artifact_rgb[1],
                "blue": artifact_rgb[2],
            },
        },
        "printer_color": {
            "name": printer_name,
            "rgb": {
                "red": printer_rgb[0],
                "green": printer_rgb[1],
                "blue": printer_rgb[2],
            },
        },
        "distance": distance,
    }


def _write_registered_artwork_manifest(
    path: Path,
    *,
    products: list[dict[str, object]],
) -> None:
    """
    Write a registered Artwork vector manifest.
    """

    path.write_text(
        json.dumps(
            {
                "registered_extent": 100,
                "products": products,
            }
        ),
        encoding="utf-8",
    )


# =========================================================
# Persistent Artifact colors
# =========================================================


def test_registered_artwork_colors_are_loaded_from_artifact_color_metadata(
    tmp_path: Path,
) -> None:
    """
    Color analysis loads persistent Artifact identities and RGB values.

    Printer assignments describe physical realization and do not redefine
    the Artifact colors measured from the Artwork.
    """

    manifest = tmp_path / "products.json"

    _write_registered_artwork_manifest(
        manifest,
        products=[
            _registered_artwork_product(
                index=1,
                artifact_rgb=(241, 17, 23),
                printer_name="physical-red",
                printer_rgb=(220, 0, 0),
                distance=2.5,
            ),
            _registered_artwork_product(
                index=2,
                artifact_rgb=(19, 31, 227),
                printer_name="physical-blue",
                printer_rgb=(0, 0, 200),
                distance=3.5,
            ),
        ],
    )

    colors = load_registered_artwork_colors(
        manifest,
    )

    assert colors == (
        MeasuredColor(
            index=1,
            rgb=(241, 17, 23),
        ),
        MeasuredColor(
            index=2,
            rgb=(19, 31, 227),
        ),
    )


def test_registered_artwork_colors_preserve_manifest_order(
    tmp_path: Path,
) -> None:
    """
    Persistent Artifact-color order follows registered Artwork product order.
    """

    manifest = tmp_path / "products.json"

    _write_registered_artwork_manifest(
        manifest,
        products=[
            _registered_artwork_product(
                index=2,
                artifact_rgb=(20, 30, 40),
                printer_name="printer-second",
                printer_rgb=(21, 31, 41),
                distance=1.0,
            ),
            _registered_artwork_product(
                index=1,
                artifact_rgb=(50, 60, 70),
                printer_name="printer-first",
                printer_rgb=(51, 61, 71),
                distance=1.0,
            ),
        ],
    )

    colors = load_registered_artwork_colors(
        manifest,
    )

    assert colors == (
        MeasuredColor(
            index=2,
            rgb=(20, 30, 40),
        ),
        MeasuredColor(
            index=1,
            rgb=(50, 60, 70),
        ),
    )


def test_registered_artwork_analysis_uses_artifact_rgb_not_printer_rgb(
    tmp_path: Path,
) -> None:
    """
    Alternative physical assignments are measured from Artifact RGB.

    Persisted printer RGB describes the current manufacturing realization
    and must not replace Artifact RGB as the measured analysis color.
    """

    manifest = tmp_path / "products.json"

    _write_registered_artwork_manifest(
        manifest,
        products=[
            _registered_artwork_product(
                index=1,
                artifact_rgb=(250, 0, 0),
                printer_name="current-black",
                printer_rgb=(0, 0, 0),
                distance=50.0,
            ),
        ],
    )

    resolver = StubColorResolver(
        values={
            "printer_colors": ["candidate-red"],
            "library_colors": ["candidate-red"],
        },
        colors={
            "candidate-red": _catalog_color(
                manufacturer="eSUN",
                rgb=(250, 0, 0),
            ),
            "candidate-black": _catalog_color(
                manufacturer="eSUN",
                rgb=(0, 0, 0),
            ),
        },
    )

    analysis = analyze_registered_artwork_colors(
        manifest=manifest,
        resolver=resolver,
    )

    assert analysis.printer.assignments[0].measured == MeasuredColor(
        index=1,
        rgb=(250, 0, 0),
    )
    assert analysis.printer.assignments[0].color.name == "candidate-red"
    assert analysis.printer.assignments[0].distance == pytest.approx(
        0.0,
    )

    assert analysis.library.assignments[0].measured == MeasuredColor(
        index=1,
        rgb=(250, 0, 0),
    )
    assert analysis.library.assignments[0].color.name == "candidate-red"
    assert analysis.library.assignments[0].distance == pytest.approx(
        0.0,
    )

    assert analysis.catalog.assignments[0].measured == MeasuredColor(
        index=1,
        rgb=(250, 0, 0),
    )
    assert analysis.catalog.assignments[0].color.name == "candidate-red"
    assert analysis.catalog.assignments[0].distance == pytest.approx(
        0.0,
    )


# =========================================================
# Three-scope assignment
# =========================================================


def test_registered_artwork_analysis_produces_three_independent_assignment_scopes(
    tmp_path: Path,
) -> None:
    """
    Printer, library, and catalog assignments use independent candidate sets.
    """

    manifest = tmp_path / "products.json"

    _write_registered_artwork_manifest(
        manifest,
        products=[
            _registered_artwork_product(
                index=1,
                artifact_rgb=(250, 10, 10),
                printer_name="old-printer-red",
                printer_rgb=(180, 0, 0),
                distance=10.0,
            ),
            _registered_artwork_product(
                index=2,
                artifact_rgb=(10, 10, 250),
                printer_name="old-printer-blue",
                printer_rgb=(0, 0, 180),
                distance=10.0,
            ),
        ],
    )

    resolver = StubColorResolver(
        values={
            "printer_colors": [
                "printer-red",
                "printer-blue",
            ],
            "library_colors": [
                "library-red",
                "library-blue",
            ],
        },
        colors={
            "printer-red": _catalog_color(
                manufacturer="eSUN",
                rgb=(200, 0, 0),
            ),
            "printer-blue": _catalog_color(
                manufacturer="eSUN",
                rgb=(0, 0, 200),
            ),
            "library-red": _catalog_color(
                manufacturer="eSUN",
                rgb=(230, 5, 5),
            ),
            "library-blue": _catalog_color(
                manufacturer="eSUN",
                rgb=(5, 5, 230),
            ),
            "catalog-red": _catalog_color(
                manufacturer="eSUN",
                rgb=(250, 10, 10),
            ),
            "catalog-blue": _catalog_color(
                manufacturer="eSUN",
                rgb=(10, 10, 250),
            ),
        },
    )

    analysis = analyze_registered_artwork_colors(
        manifest=manifest,
        resolver=resolver,
    )

    assert tuple(assignment.color.name for assignment in analysis.printer.assignments) == (
        "printer-red",
        "printer-blue",
    )

    assert tuple(assignment.color.name for assignment in analysis.library.assignments) == (
        "library-red",
        "library-blue",
    )

    assert tuple(assignment.color.name for assignment in analysis.catalog.assignments) == (
        "catalog-red",
        "catalog-blue",
    )


def test_registered_artwork_analysis_uses_global_one_to_one_assignment(
    tmp_path: Path,
) -> None:
    """
    Every scope assigns distinct physical colors jointly.

    Independent nearest-neighbor matching would assign both Artifact colors
    to the same closest candidate in this fixture. The complete assignment
    must instead select a globally optimal one-to-one mapping.
    """

    manifest = tmp_path / "products.json"

    _write_registered_artwork_manifest(
        manifest,
        products=[
            _registered_artwork_product(
                index=1,
                artifact_rgb=(100, 100, 100),
                printer_name="old-a",
                printer_rgb=(0, 0, 0),
                distance=10.0,
            ),
            _registered_artwork_product(
                index=2,
                artifact_rgb=(110, 110, 110),
                printer_name="old-b",
                printer_rgb=(255, 255, 255),
                distance=10.0,
            ),
        ],
    )

    resolver = StubColorResolver(
        values={
            "printer_colors": [
                "candidate-near",
                "candidate-other",
            ],
            "library_colors": [
                "candidate-near",
                "candidate-other",
            ],
        },
        colors={
            "candidate-near": _catalog_color(
                manufacturer="eSUN",
                rgb=(105, 105, 105),
            ),
            "candidate-other": _catalog_color(
                manufacturer="eSUN",
                rgb=(80, 80, 80),
            ),
        },
    )

    analysis = analyze_registered_artwork_colors(
        manifest=manifest,
        resolver=resolver,
    )

    for scope in (
        analysis.printer,
        analysis.library,
        analysis.catalog,
    ):
        selected = tuple(assignment.color.name for assignment in scope.assignments)

        assert len(selected) == 2
        assert len(set(selected)) == 2
        assert set(selected) == {
            "candidate-near",
            "candidate-other",
        }


def test_three_color_artwork_selects_three_colors_from_five_candidates(
    tmp_path: Path,
) -> None:
    """
    Assignment cardinality follows Artifact colors, not printer capacity.
    """

    manifest = tmp_path / "products.json"

    _write_registered_artwork_manifest(
        manifest,
        products=[
            _registered_artwork_product(
                index=1,
                artifact_rgb=(250, 0, 0),
                printer_name="old-red",
                printer_rgb=(200, 0, 0),
                distance=5.0,
            ),
            _registered_artwork_product(
                index=2,
                artifact_rgb=(0, 250, 0),
                printer_name="old-green",
                printer_rgb=(0, 200, 0),
                distance=5.0,
            ),
            _registered_artwork_product(
                index=3,
                artifact_rgb=(0, 0, 250),
                printer_name="old-blue",
                printer_rgb=(0, 0, 200),
                distance=5.0,
            ),
        ],
    )

    colors = {
        "red": _catalog_color(
            manufacturer="eSUN",
            rgb=(250, 0, 0),
        ),
        "green": _catalog_color(
            manufacturer="eSUN",
            rgb=(0, 250, 0),
        ),
        "blue": _catalog_color(
            manufacturer="eSUN",
            rgb=(0, 0, 250),
        ),
        "white": _catalog_color(
            manufacturer="eSUN",
            rgb=(255, 255, 255),
        ),
        "black": _catalog_color(
            manufacturer="eSUN",
            rgb=(0, 0, 0),
        ),
    }

    resolver = StubColorResolver(
        values={
            "printer_colors": [
                "white",
                "red",
                "green",
                "blue",
                "black",
            ],
            "library_colors": [
                "white",
                "red",
                "green",
                "blue",
                "black",
            ],
        },
        colors=colors,
    )

    analysis = analyze_registered_artwork_colors(
        manifest=manifest,
        resolver=resolver,
    )

    assert len(analysis.printer.assignments) == 3
    assert len(analysis.library.assignments) == 3
    assert len(analysis.catalog.assignments) == 3

    assert {assignment.color.name for assignment in analysis.printer.assignments} == {
        "red",
        "green",
        "blue",
    }

    assert {assignment.color.name for assignment in analysis.library.assignments} == {
        "red",
        "green",
        "blue",
    }

    assert {assignment.color.name for assignment in analysis.catalog.assignments} == {
        "red",
        "green",
        "blue",
    }


# =========================================================
# Assignment distances
# =========================================================


def test_registered_artwork_analysis_exposes_individual_and_aggregate_distances(
    tmp_path: Path,
) -> None:
    """
    Each scope exposes individual distances and their aggregate distance.
    """

    manifest = tmp_path / "products.json"

    _write_registered_artwork_manifest(
        manifest,
        products=[
            _registered_artwork_product(
                index=1,
                artifact_rgb=(240, 20, 20),
                printer_name="old-red",
                printer_rgb=(200, 0, 0),
                distance=5.0,
            ),
            _registered_artwork_product(
                index=2,
                artifact_rgb=(20, 20, 240),
                printer_name="old-blue",
                printer_rgb=(0, 0, 200),
                distance=5.0,
            ),
        ],
    )

    resolver = StubColorResolver(
        values={
            "printer_colors": [
                "printer-red",
                "printer-blue",
            ],
            "library_colors": [
                "library-red",
                "library-blue",
            ],
        },
        colors={
            "printer-red": _catalog_color(
                manufacturer="eSUN",
                rgb=(220, 0, 0),
            ),
            "printer-blue": _catalog_color(
                manufacturer="eSUN",
                rgb=(0, 0, 220),
            ),
            "library-red": _catalog_color(
                manufacturer="eSUN",
                rgb=(230, 10, 10),
            ),
            "library-blue": _catalog_color(
                manufacturer="eSUN",
                rgb=(10, 10, 230),
            ),
            "catalog-red": _catalog_color(
                manufacturer="eSUN",
                rgb=(239, 19, 19),
            ),
            "catalog-blue": _catalog_color(
                manufacturer="eSUN",
                rgb=(19, 19, 239),
            ),
        },
    )

    analysis = analyze_registered_artwork_colors(
        manifest=manifest,
        resolver=resolver,
    )

    for scope in (
        analysis.printer,
        analysis.library,
        analysis.catalog,
    ):
        assert all(assignment.distance >= 0.0 for assignment in scope.assignments)

        assert scope.distance == pytest.approx(
            sum(assignment.distance for assignment in scope.assignments)
        )


# =========================================================
# Catalog scope
# =========================================================


def test_catalog_assignment_excludes_synthetic_test_colors(
    tmp_path: Path,
) -> None:
    """
    Catalog-wide assignment excludes synthetic test catalog entries.

    Synthetic entries remain valid when explicitly selected by printer or
    library configuration.
    """

    manifest = tmp_path / "products.json"

    _write_registered_artwork_manifest(
        manifest,
        products=[
            _registered_artwork_product(
                index=1,
                artifact_rgb=(255, 0, 0),
                printer_name="old-red",
                printer_rgb=(200, 0, 0),
                distance=5.0,
            ),
        ],
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

    assert analysis.printer.assignments[0].color.name == "test-red"
    assert analysis.library.assignments[0].color.name == "test-red"
    assert analysis.catalog.assignments[0].color.name == "physical-red"


# =========================================================
# Availability requirements
# =========================================================


@pytest.mark.parametrize(
    (
        "parameter",
        "values",
    ),
    [
        (
            "printer_colors",
            ["red", "green"],
        ),
        (
            "library_colors",
            ["red", "green"],
        ),
    ],
)
def test_registered_artwork_analysis_rejects_insufficient_configured_candidates(
    tmp_path: Path,
    parameter: str,
    values: list[str],
) -> None:
    """
    Every analyzed availability scope requires enough distinct candidates.
    """

    manifest = tmp_path / "products.json"

    _write_registered_artwork_manifest(
        manifest,
        products=[
            _registered_artwork_product(
                index=1,
                artifact_rgb=(255, 0, 0),
                printer_name="old-red",
                printer_rgb=(200, 0, 0),
                distance=5.0,
            ),
            _registered_artwork_product(
                index=2,
                artifact_rgb=(0, 255, 0),
                printer_name="old-green",
                printer_rgb=(0, 200, 0),
                distance=5.0,
            ),
            _registered_artwork_product(
                index=3,
                artifact_rgb=(0, 0, 255),
                printer_name="old-blue",
                printer_rgb=(0, 0, 200),
                distance=5.0,
            ),
        ],
    )

    resolved = {
        "printer_colors": [
            "red",
            "green",
            "blue",
        ],
        "library_colors": [
            "red",
            "green",
            "blue",
        ],
    }

    resolved[parameter] = values

    resolver = StubColorResolver(
        values=resolved,
        colors={
            "red": _catalog_color(
                manufacturer="eSUN",
                rgb=(255, 0, 0),
            ),
            "green": _catalog_color(
                manufacturer="eSUN",
                rgb=(0, 255, 0),
            ),
            "blue": _catalog_color(
                manufacturer="eSUN",
                rgb=(0, 0, 255),
            ),
        },
    )

    with pytest.raises(
        ColorError,
        match="Palette color count cannot be smaller",
    ):
        analyze_registered_artwork_colors(
            manifest=manifest,
            resolver=resolver,
        )


def test_registered_artwork_analysis_rejects_insufficient_catalog_candidates(
    tmp_path: Path,
) -> None:
    """
    Catalog analysis requires enough physical catalog candidates.
    """

    manifest = tmp_path / "products.json"

    _write_registered_artwork_manifest(
        manifest,
        products=[
            _registered_artwork_product(
                index=1,
                artifact_rgb=(255, 0, 0),
                printer_name="old-red",
                printer_rgb=(200, 0, 0),
                distance=5.0,
            ),
            _registered_artwork_product(
                index=2,
                artifact_rgb=(0, 255, 0),
                printer_name="old-green",
                printer_rgb=(0, 200, 0),
                distance=5.0,
            ),
        ],
    )

    resolver = StubColorResolver(
        values={
            "printer_colors": [
                "test-red",
                "test-green",
            ],
            "library_colors": [
                "test-red",
                "test-green",
            ],
        },
        colors={
            "test-red": _catalog_color(
                manufacturer="test",
                rgb=(255, 0, 0),
            ),
            "test-green": _catalog_color(
                manufacturer="test",
                rgb=(0, 255, 0),
            ),
            "physical-red": _catalog_color(
                manufacturer="eSUN",
                rgb=(240, 0, 0),
            ),
        },
    )

    with pytest.raises(
        ColorError,
        match="Palette color count cannot be smaller",
    ):
        analyze_registered_artwork_colors(
            manifest=manifest,
            resolver=resolver,
        )


# =========================================================
# Analysis purity
# =========================================================


def test_registered_artwork_analysis_does_not_mutate_inputs(
    tmp_path: Path,
) -> None:
    """
    Artwork analysis does not modify persistent products or color availability.
    """

    manifest = tmp_path / "products.json"

    _write_registered_artwork_manifest(
        manifest,
        products=[
            _registered_artwork_product(
                index=1,
                artifact_rgb=(250, 10, 10),
                printer_name="current-red",
                printer_rgb=(220, 0, 0),
                distance=3.0,
            ),
        ],
    )

    printer_colors = ["printer-red"]
    library_colors = ["library-red"]

    colors: dict[str, object] = {
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
    }

    resolver = StubColorResolver(
        values={
            "printer_colors": printer_colors,
            "library_colors": library_colors,
        },
        colors=colors,
    )

    manifest_before = manifest.read_bytes()
    printer_before = list(printer_colors)
    library_before = list(library_colors)
    catalog_before = json.loads(json.dumps(colors))

    analyze_registered_artwork_colors(
        manifest=manifest,
        resolver=resolver,
    )

    assert manifest.read_bytes() == manifest_before
    assert printer_colors == printer_before
    assert library_colors == library_before
    assert colors == catalog_before
