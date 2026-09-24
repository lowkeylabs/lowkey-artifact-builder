"""
Tests for Shape color analysis.
"""
# File: tests/model/shape/test_color_analysis.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from lowkey_artifact_builder.colors import (
    ColorAssignment,
    ColorAssignmentResult,
    MeasuredColor,
    PaletteColor,
)
from lowkey_artifact_builder.model.models.artwork.color_analysis import (
    ArtworkColorAnalysis,
)
from lowkey_artifact_builder.model.models.shape.color_analysis import (
    ShapeColorAnalysis,
    analyze_shape_colors,
)


class StubResolver:
    """
    Minimal resolved Shape configuration for color analysis.
    """

    def __init__(
        self,
        values: dict[str, object],
        *,
        system_values: dict[str, object] | None = None,
        colors: dict[str, object] | None = None,
    ) -> None:
        self._values = {
            "printer_colors": [
                "black",
                "white",
            ],
            "library_colors": [
                "black",
                "white",
            ],
            **values,
        }
        self._system_values = {
            "printer_colors": [
                "black",
                "white",
            ],
            **(system_values or {}),
        }
        self._colors = colors or {
            "black": {
                "rgb": [0, 0, 0],
                "manufacturer": "test-default",
            },
            "white": {
                "rgb": [255, 255, 255],
                "manufacturer": "test-default",
            },
        }

    def __call__(
        self,
        name: str,
    ) -> object:
        return self._values[name]

    def system_value(
        self,
        name: str,
    ) -> object:
        return self._system_values[name]

    @property
    def colors(
        self,
    ) -> dict[str, object]:
        return self._colors


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


def test_shape_color_analysis_compares_semantic_color_to_printer_palette() -> None:
    """
    A structural semantic color retains its identity while independently
    reporting the nearest color available in the effective Printer palette.
    """

    resolver = StubResolver(
        {
            "shape_base_color": "orange",
            "shape_outer_ridge_width": 0.0,
            "shape_artwork_fill_color": "none",
            "printer_colors": [
                "red",
                "blue",
            ],
        },
        colors={
            "orange": {
                "rgb": [255, 128, 0],
            },
            "red": {
                "rgb": [255, 0, 0],
            },
            "blue": {
                "rgb": [0, 0, 255],
            },
        },
    )

    analysis = analyze_shape_colors(
        resolver=resolver,
    )

    assert len(analysis.colors) == 1

    color = analysis.colors[0]

    assert color.color == "orange"
    assert color.used_by == ("base",)

    assert color.printer_candidate.name == "red"
    assert color.printer_candidate.distance > 0.0


def test_shape_color_analysis_compares_system_and_printer_independently() -> None:
    """
    System and Printer advisory comparisons use their distinct palettes.

    System uses unresolved system-default printer_colors while Printer uses
    the effective resolved printer_colors. Neither comparison replaces the
    structural semantic color identity.
    """

    resolver = StubResolver(
        {
            "shape_base_color": "purple",
            "shape_outer_ridge_width": 0.0,
            "shape_artwork_fill_color": "none",
            "printer_colors": [
                "red",
            ],
        },
        system_values={
            "printer_colors": [
                "blue",
            ],
        },
        colors={
            "purple": {
                "rgb": [128, 0, 128],
            },
            "red": {
                "rgb": [255, 0, 0],
            },
            "blue": {
                "rgb": [0, 0, 255],
            },
        },
    )

    analysis = analyze_shape_colors(
        resolver=resolver,
    )

    assert len(analysis.colors) == 1

    color = analysis.colors[0]

    assert color.color == "purple"
    assert color.used_by == ("base",)

    assert color.system_candidate.name == "blue"
    assert color.system_candidate.distance > 0.0

    assert color.printer_candidate.name == "red"
    assert color.printer_candidate.distance > 0.0


def test_shape_color_analysis_compares_library_independently() -> None:
    """
    Library advisory comparison uses the resolved Library palette
    independently of System and Printer.

    The comparison does not replace the structural semantic color identity.
    """

    resolver = StubResolver(
        {
            "shape_base_color": "orange",
            "shape_outer_ridge_width": 0.0,
            "shape_artwork_fill_color": "none",
            "printer_colors": [
                "red",
            ],
            "library_colors": [
                "yellow",
            ],
        },
        system_values={
            "printer_colors": [
                "blue",
            ],
        },
        colors={
            "orange": {
                "rgb": [255, 128, 0],
            },
            "red": {
                "rgb": [255, 0, 0],
            },
            "blue": {
                "rgb": [0, 0, 255],
            },
            "yellow": {
                "rgb": [255, 255, 0],
            },
        },
    )

    analysis = analyze_shape_colors(
        resolver=resolver,
    )

    assert len(analysis.colors) == 1

    color = analysis.colors[0]

    assert color.color == "orange"
    assert color.used_by == ("base",)

    assert color.system_candidate.name == "blue"
    assert color.system_candidate.distance > 0.0

    assert color.printer_candidate.name == "red"
    assert color.printer_candidate.distance > 0.0

    assert color.library_candidate.name == "yellow"
    assert color.library_candidate.distance > 0.0


def test_shape_color_analysis_compares_physical_catalog_independently() -> None:
    """
    Catalog advisory comparison uses all physical catalog colors independently
    of System, Printer, and Library.

    Nonphysical test colors are excluded from catalog-wide comparison, and the
    comparison does not replace the structural semantic color identity.
    """

    resolver = StubResolver(
        {
            "shape_base_color": "orange",
            "shape_outer_ridge_width": 0.0,
            "shape_artwork_fill_color": "none",
            "printer_colors": [
                "red",
            ],
            "library_colors": [
                "yellow",
            ],
        },
        system_values={
            "printer_colors": [
                "blue",
            ],
        },
        colors={
            "orange": {
                "rgb": [255, 128, 0],
                "manufacturer": "test",
            },
            "red": {
                "rgb": [255, 0, 0],
                "manufacturer": "test",
            },
            "blue": {
                "rgb": [0, 0, 255],
                "manufacturer": "test",
            },
            "yellow": {
                "rgb": [255, 255, 0],
                "manufacturer": "test",
            },
            "physical-green": {
                "rgb": [0, 255, 0],
                "manufacturer": "Example",
            },
        },
    )

    analysis = analyze_shape_colors(
        resolver=resolver,
    )

    assert len(analysis.colors) == 1

    color = analysis.colors[0]

    assert color.color == "orange"
    assert color.used_by == ("base",)

    assert color.system_candidate.name == "blue"
    assert color.printer_candidate.name == "red"
    assert color.library_candidate.name == "yellow"

    assert color.catalog_candidate.name == "physical-green"
    assert color.catalog_candidate.distance > 0.0


def test_shape_color_analysis_preserves_artwork_assignment_analysis() -> None:
    """
    Artwork-derived colors participating in a Shape Realization retain their
    Artwork assignment semantics rather than becoming structural semantic-color
    comparisons.
    """

    measured = MeasuredColor(
        index=1,
        rgb=(240, 80, 40),
    )

    def assignment_result(
        name: str,
        distance: float,
    ) -> ColorAssignmentResult:
        return ColorAssignmentResult(
            assignments=(
                ColorAssignment(
                    measured=measured,
                    color=PaletteColor(
                        name=name,
                        rgb=measured.rgb,
                    ),
                    distance=distance,
                ),
            ),
            distance=distance,
        )

    artwork = ArtworkColorAnalysis(
        system_assignments=assignment_result(
            "system-red",
            1.0,
        ),
        printer_assignments=assignment_result(
            "printer-red",
            2.0,
        ),
        library_assignments=assignment_result(
            "library-red",
            3.0,
        ),
        catalog_assignments=assignment_result(
            "catalog-red",
            4.0,
        ),
    )

    analysis = ShapeColorAnalysis(
        colors=(),
        artwork=artwork,
    )

    assert analysis.artwork is artwork


def test_shape_color_analysis_preserves_supplied_artwork_analysis() -> None:
    """
    Shape color analysis preserves participating Artwork analysis separately
    from Shape-owned structural semantic-color comparisons.
    """

    resolver = StubResolver(
        {
            "shape_base_color": "white",
            "shape_outer_ridge_width": 0.0,
            "shape_artwork_fill_color": "none",
        }
    )

    measured = MeasuredColor(
        index=1,
        rgb=(240, 80, 40),
    )

    def assignment_result(
        name: str,
    ) -> ColorAssignmentResult:
        return ColorAssignmentResult(
            assignments=(
                ColorAssignment(
                    measured=measured,
                    color=PaletteColor(
                        name=name,
                        rgb=measured.rgb,
                    ),
                    distance=0.0,
                ),
            ),
            distance=0.0,
        )

    artwork = ArtworkColorAnalysis(
        system_assignments=assignment_result("system-red"),
        printer_assignments=assignment_result("printer-red"),
        library_assignments=assignment_result("library-red"),
        catalog_assignments=assignment_result("catalog-red"),
    )

    analysis = analyze_shape_colors(
        resolver=resolver,
        artwork=artwork,
    )

    assert analysis.artwork is artwork
