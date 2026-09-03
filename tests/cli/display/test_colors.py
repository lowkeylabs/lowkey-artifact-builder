"""
Tests for Artwork color analysis presentation.
"""
# File: tests/cli/display/test_colors.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from lowkey_artifact_builder.cli.display import (
    display_color_analysis,
)
from lowkey_artifact_builder.colors import (
    ColorAssignment,
    ColorAssignmentResult,
    MeasuredColor,
    PaletteColor,
)
from lowkey_artifact_builder.model.models.artwork.color_analysis import (
    ArtworkColorAnalysis,
)

# =========================================================
# Test support
# =========================================================


def _assignment_result(
    *,
    names: tuple[str, ...],
    distances: tuple[float, ...],
) -> ColorAssignmentResult:
    """
    Return assignments for three persistent Artifact colors.
    """

    measured = (
        MeasuredColor(
            index=1,
            rgb=(250, 10, 10),
        ),
        MeasuredColor(
            index=2,
            rgb=(10, 250, 10),
        ),
        MeasuredColor(
            index=3,
            rgb=(10, 10, 250),
        ),
    )

    assignments = tuple(
        ColorAssignment(
            measured=color,
            color=PaletteColor(
                name=name,
                rgb=color.rgb,
            ),
            distance=distance,
        )
        for color, name, distance in zip(
            measured,
            names,
            distances,
            strict=True,
        )
    )

    return ColorAssignmentResult(
        assignments=assignments,
        distance=sum(distances),
    )


def _analysis() -> ArtworkColorAnalysis:
    """
    Return representative three-scope Artwork analysis.
    """

    return ArtworkColorAnalysis(
        printer=_assignment_result(
            names=(
                "printer-red",
                "printer-green",
                "printer-blue",
            ),
            distances=(
                1.0,
                2.0,
                3.0,
            ),
        ),
        library=_assignment_result(
            names=(
                "library-red",
                "library-green",
                "library-blue",
            ),
            distances=(
                4.0,
                5.0,
                6.0,
            ),
        ),
        catalog=_assignment_result(
            names=(
                "catalog-red",
                "catalog-green",
                "catalog-blue",
            ),
            distances=(
                7.0,
                8.0,
                9.0,
            ),
        ),
    )


# =========================================================
# Assignment scopes
# =========================================================


def test_color_report_displays_three_assignment_scopes(
    capsys,
) -> None:
    """
    The color report distinguishes printer, library, and catalog assignments.
    """

    display_color_analysis(
        _analysis(),
    )

    output = capsys.readouterr().out

    assert "Artifact" in output
    assert "Printer" in output
    assert "Library" in output
    assert "Catalog" in output


def test_color_report_displays_every_selected_physical_color(
    capsys,
) -> None:
    """
    The color report presents every selected physical color in every scope.
    """

    display_color_analysis(
        _analysis(),
    )

    output = capsys.readouterr().out

    for name in (
        "printer-red",
        "printer-green",
        "printer-blue",
        "library-red",
        "library-green",
        "library-blue",
        "catalog-red",
        "catalog-green",
        "catalog-blue",
    ):
        assert name in output


def test_three_color_report_displays_three_assignments_per_scope(
    capsys,
) -> None:
    """
    Three Artifact colors produce three displayed assignments per scope.
    """

    display_color_analysis(
        _analysis(),
    )

    output = capsys.readouterr().out

    assert output.count("printer-") == 3
    assert output.count("library-") == 3
    assert output.count("catalog-") == 3


# =========================================================
# Artifact colors
# =========================================================


def test_color_report_displays_every_artifact_color(
    capsys,
) -> None:
    """
    The color report includes every persistent Artifact color.
    """

    display_color_analysis(
        _analysis(),
    )

    output = capsys.readouterr().out

    assert "(250, 10, 10)" in output
    assert "(10, 250, 10)" in output
    assert "(10, 10, 250)" in output


def test_color_report_displays_source_derived_artifact_rgb(
    capsys,
) -> None:
    """
    Artifact RGB presentation comes from measured Artifact color information.

    Physical candidate RGB values do not replace the persistent Artifact RGB
    values presented by the report.
    """

    measured = MeasuredColor(
        index=1,
        rgb=(201, 17, 33),
    )

    analysis = ArtworkColorAnalysis(
        printer=ColorAssignmentResult(
            assignments=(
                ColorAssignment(
                    measured=measured,
                    color=PaletteColor(
                        name="printer-red",
                        rgb=(255, 0, 0),
                    ),
                    distance=1.0,
                ),
            ),
            distance=1.0,
        ),
        library=ColorAssignmentResult(
            assignments=(
                ColorAssignment(
                    measured=measured,
                    color=PaletteColor(
                        name="library-red",
                        rgb=(220, 20, 20),
                    ),
                    distance=2.0,
                ),
            ),
            distance=2.0,
        ),
        catalog=ColorAssignmentResult(
            assignments=(
                ColorAssignment(
                    measured=measured,
                    color=PaletteColor(
                        name="catalog-red",
                        rgb=(190, 10, 10),
                    ),
                    distance=3.0,
                ),
            ),
            distance=3.0,
        ),
    )

    display_color_analysis(
        analysis,
    )

    output = capsys.readouterr().out

    assert "(201, 17, 33)" in output
    assert "(255, 0, 0)" not in output
    assert "(220, 20, 20)" not in output
    assert "(190, 10, 10)" not in output


# =========================================================
# Distances
# =========================================================


def test_color_report_displays_individual_assignment_distances(
    capsys,
) -> None:
    """
    The color report exposes individual perceptual assignment distances.
    """

    display_color_analysis(
        _analysis(),
    )

    output = capsys.readouterr().out

    for distance in (
        "1.00",
        "2.00",
        "3.00",
        "4.00",
        "5.00",
        "6.00",
        "7.00",
        "8.00",
        "9.00",
    ):
        assert distance in output


def test_color_report_displays_aggregate_assignment_distances(
    capsys,
) -> None:
    """
    The color report exposes aggregate distance for every assignment scope.
    """

    display_color_analysis(
        _analysis(),
    )

    output = capsys.readouterr().out

    assert "Aggregate Distance" in output

    assert "6.00" in output
    assert "15.00" in output
    assert "24.00" in output


# =========================================================
# Ordering
# =========================================================


def test_color_report_preserves_structured_analysis_order(
    capsys,
) -> None:
    """
    Color report ordering follows the structured analysis assignment order.
    """

    display_color_analysis(
        _analysis(),
    )

    output = capsys.readouterr().out

    red = output.index("(250, 10, 10)")
    green = output.index("(10, 250, 10)")
    blue = output.index("(10, 10, 250)")

    assert red < green < blue

    assert output.index("printer-red") < output.index("printer-green")
    assert output.index("printer-green") < output.index("printer-blue")
