"""
Artwork color-analysis presentation.
"""
# File: src/lowkey_artifact_builder/cli/display/colors.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from lowkey_artifact_builder.colors import (
    ColorAssignment,
    ColorAssignmentResult,
)
from lowkey_artifact_builder.model.models.artwork.color_analysis import (
    ArtworkColorAnalysis,
)

from .common import (
    console,
    create_table,
)

# =========================================================
# Color analysis
# =========================================================


def display_color_analysis(
    analysis: ArtworkColorAnalysis,
) -> None:
    """
    Display Artwork physical color-assignment analysis.
    """

    table = create_table()

    table.add_column("Artifact")
    table.add_column("Printer")
    table.add_column("Library")
    table.add_column("Catalog")

    printer = _assignments_by_index(
        analysis.printer,
    )
    library = _assignments_by_index(
        analysis.library,
    )
    catalog = _assignments_by_index(
        analysis.catalog,
    )

    for assignment in analysis.printer.assignments:
        index = assignment.measured.index

        table.add_row(
            _format_artifact_color(
                assignment.measured.index,
                assignment.measured.rgb,
            ),
            _format_assignment(
                printer[index],
            ),
            _format_assignment(
                library[index],
            ),
            _format_assignment(
                catalog[index],
            ),
        )

    console.print(table)

    totals = create_table()

    totals.add_column("Scope")
    totals.add_column("Aggregate Distance")

    for scope, result in (
        ("Printer", analysis.printer),
        ("Library", analysis.library),
        ("Catalog", analysis.catalog),
    ):
        totals.add_row(
            scope,
            f"{result.distance:.2f}",
        )

    console.print(totals)


def _assignments_by_index(
    result: ColorAssignmentResult,
) -> dict[int, ColorAssignment]:
    """
    Index color assignments by persistent Artifact color identity.
    """

    return {assignment.measured.index: assignment for assignment in result.assignments}


def _format_artifact_color(
    index: int,
    rgb: tuple[int, int, int],
) -> str:
    """
    Format one persistent Artifact color.
    """

    return f"{index} ({rgb[0]}, {rgb[1]}, {rgb[2]})"


def _format_assignment(
    assignment: ColorAssignment,
) -> str:
    """
    Format one physical color assignment.
    """

    return f"{assignment.color.name} {assignment.distance:.2f}"


__all__ = [
    "display_color_analysis",
]
