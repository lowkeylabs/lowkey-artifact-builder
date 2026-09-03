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


def test_color_report_displays_three_assignment_scopes(
    capsys,
) -> None:
    """
    The color report presents printer, library, and catalog assignments.
    """

    display_color_analysis(
        _analysis(),
    )

    output = capsys.readouterr().out

    assert "Artifact" in output
    assert "Printer" in output
    assert "Library" in output
    assert "Catalog" in output

    assert "printer-red" in output
    assert "library-red" in output
    assert "catalog-red" in output


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

    assert "1.00" in output
    assert "5.00" in output
    assert "9.00" in output


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
