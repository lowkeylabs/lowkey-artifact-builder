"""
Artwork color-analysis presentation.
"""
# File: src/lowkey_artifact_builder/cli/display/colors.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from collections.abc import Sequence

from lowkey_artifact_builder.colors import ColorMatch
from lowkey_artifact_builder.model.models.artwork.color_analysis import (
    ArtworkColorMatch,
)

from .common import (
    console,
    create_table,
)

# =========================================================
# Color analysis
# =========================================================


def display_color_matches(
    matches: Sequence[ArtworkColorMatch],
) -> None:
    """
    Display structured Artwork color-match analysis.
    """

    table = create_table()

    table.add_column("Artwork")
    table.add_column("Printer")
    table.add_column("Library")
    table.add_column("Catalog")

    for match in matches:
        table.add_row(
            match.artwork.name,
            _format_match(match.printer),
            _format_match(match.library),
            _format_match(match.catalog),
        )

    console.print(table)


def _format_match(
    match: ColorMatch,
) -> str:
    """
    Format one color match for presentation.
    """

    return f"{match.color.name} {match.distance:.2f}"


__all__ = [
    "display_color_matches",
]
