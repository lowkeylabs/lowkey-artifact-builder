"""
Model-level color interpretation tests.

These tests protect the translation between Model-owned color semantics
and independently printable packaged component identities.

Generic palette resolution, perceptual comparison, and color assignment
belong to lowkey_artifact_builder.colors. File-format mutation belongs to
the formats layer. This module tests only Model-specific interpretation
of resolved color results.
"""
# File: tests/model/test_color.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from lowkey_artifact_builder.colors import (
    ColorAssignment,
    ColorAssignmentResult,
    MeasuredColor,
    PaletteColor,
)
from lowkey_artifact_builder.model.color import (
    artwork_component_colors,
)
from lowkey_artifact_builder.model.models.artwork.color_analysis import (
    ArtworkColorAnalysis,
)


def test_artwork_component_colors_maps_persistent_colors_to_components() -> None:
    """
    Artwork Printer assignments map persistent Artifact color identities to
    the corresponding independently printable packaged Artwork components.
    """

    printer_assignments = ColorAssignmentResult(
        assignments=(
            ColorAssignment(
                measured=MeasuredColor(
                    index=1,
                    rgb=(200, 0, 0),
                ),
                color=PaletteColor(
                    name="fire-engine-red",
                    rgb=(220, 38, 38),
                ),
                distance=1.0,
            ),
            ColorAssignment(
                measured=MeasuredColor(
                    index=2,
                    rgb=(250, 250, 250),
                ),
                color=PaletteColor(
                    name="cold-white",
                    rgb=(245, 245, 240),
                ),
                distance=2.0,
            ),
        ),
        distance=3.0,
    )

    analysis = ArtworkColorAnalysis(
        system_assignments=printer_assignments,
        printer_assignments=printer_assignments,
        library_assignments=printer_assignments,
        catalog_assignments=printer_assignments,
    )

    assert artwork_component_colors(
        analysis,
    ) == {
        "artwork-1": PaletteColor(
            name="fire-engine-red",
            rgb=(220, 38, 38),
        ),
        "artwork-2": PaletteColor(
            name="cold-white",
            rgb=(245, 245, 240),
        ),
    }
