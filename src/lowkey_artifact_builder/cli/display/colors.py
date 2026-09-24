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
from lowkey_artifact_builder.model.models.shape.color_analysis import (
    ShapeColorAnalysis,
    ShapeColorCandidate,
)

from .common import (
    console,
    create_table,
)

# =========================================================
# Color analysis
# =========================================================


def _format_shape_candidate(
    candidate: ShapeColorCandidate,
) -> str:
    """
    Format one advisory Shape color comparison.
    """

    return f"{candidate.name}\n{candidate.distance:.2f}"


def display_color_analysis(
    analysis: ArtworkColorAnalysis | ShapeColorAnalysis,
) -> None:
    """
    Display physical color analysis.
    """

    if isinstance(
        analysis,
        ArtworkColorAnalysis,
    ):
        _display_artwork_color_analysis(
            analysis,
        )
        return

    if isinstance(
        analysis,
        ShapeColorAnalysis,
    ):
        _display_shape_color_analysis(
            analysis,
        )
        return

    raise TypeError(f"Unsupported color-analysis type: {type(analysis).__name__}.")


def _display_shape_color_analysis(
    analysis: ShapeColorAnalysis,
) -> None:
    """
    Display Shape Realization color analysis.

    Shape-owned structural colors retain semantic-color comparison semantics.
    Participating Artwork colors retain Artwork physical-color assignment
    semantics. Both are presented in one realization-level table with
    component usage.
    """

    table = create_table(expand=False)

    table.add_column("Layer", no_wrap=True)
    table.add_column("System", no_wrap=True)
    table.add_column("Printer", no_wrap=True)
    table.add_column("Library", no_wrap=True)
    table.add_column("Catalog", no_wrap=True)
    table.add_column("Used By", no_wrap=True)

    for color in analysis.colors:
        table.add_row(
            color.color,
            _format_shape_candidate(
                color.system_candidate,
            ),
            _format_shape_candidate(
                color.printer_candidate,
            ),
            _format_shape_candidate(
                color.library_candidate,
            ),
            _format_shape_candidate(
                color.catalog_candidate,
            ),
            ", ".join(
                color.used_by,
            ),
        )

    if analysis.artwork is not None:
        system = _assignments_by_index(
            analysis.artwork.system_assignments,
        )
        printer = _assignments_by_index(
            analysis.artwork.printer_assignments,
        )
        library = _assignments_by_index(
            analysis.artwork.library_assignments,
        )
        catalog = _assignments_by_index(
            analysis.artwork.catalog_assignments,
        )

        for assignment in analysis.artwork.printer_assignments.assignments:
            index = assignment.measured.index

            table.add_row(
                _format_artifact_color(
                    index,
                    assignment.measured.rgb,
                ),
                _format_assignment(
                    system[index],
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
                ", ".join(
                    (analysis.artwork_used_by or {}).get(
                        index,
                        (),
                    ),
                ),
            )

    console.print(table)


def _display_artwork_color_analysis(
    analysis: ArtworkColorAnalysis,
) -> None:
    """
    Display Artwork physical color-assignment analysis.
    """

    table = create_table()

    table.add_column("Layer", no_wrap=True)
    table.add_column("System")
    table.add_column("Printer")
    table.add_column("Library")
    table.add_column("Catalog")

    system = _assignments_by_index(
        analysis.system_assignments,
    )
    printer = _assignments_by_index(
        analysis.printer_assignments,
    )
    library = _assignments_by_index(
        analysis.library_assignments,
    )
    catalog = _assignments_by_index(
        analysis.catalog_assignments,
    )

    for assignment in analysis.printer_assignments.assignments:
        index = assignment.measured.index

        table.add_row(
            _format_artifact_color(
                assignment.measured.index,
                assignment.measured.rgb,
            ),
            _format_assignment(
                system[index],
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
        (
            "System",
            analysis.system_assignments,
        ),
        (
            "Printer",
            analysis.printer_assignments,
        ),
        (
            "Library",
            analysis.library_assignments,
        ),
        (
            "Catalog",
            analysis.catalog_assignments,
        ),
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
