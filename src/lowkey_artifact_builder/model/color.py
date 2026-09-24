"""
Model-specific color interpretation.

This module translates resolved Model color semantics into independently
printable packaged component color identities.

Generic palette resolution, perceptual comparison, and color assignment
belong to lowkey_artifact_builder.colors. File-format mutation belongs to
the formats layer.
"""
# File: src/lowkey_artifact_builder/model/color.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from lowkey_artifact_builder.colors import (
    PaletteColor,
)
from lowkey_artifact_builder.model.models.artwork.color_analysis import (
    ArtworkColorAnalysis,
)


def artwork_component_colors(
    analysis: ArtworkColorAnalysis,
) -> dict[str, PaletteColor]:
    """
    Return packaged Artwork component colors from effective Printer
    assignments.

    Persistent Artwork measured-color indexes identify the corresponding
    independently printable packaged Artwork components.
    """

    return {
        f"artwork-{assignment.measured.index}": assignment.color
        for assignment in analysis.printer_assignments.assignments
    }


__all__ = [
    "artwork_component_colors",
]
