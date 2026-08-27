"""
Registered structural geometry for the Shape model.

This module defines the registered, nonphysical geometry produced by Shape
structural production.

Physical dimensionalization and extrusion belong to downstream Shape stages.
"""
# File: src/lowkey_artifact_builder/model/models/shape/stages/structure.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from dataclasses import dataclass

# =========================================================
# Geometry specifications
# =========================================================


@dataclass(
    frozen=True,
    slots=True,
)
class CircleGeometry:
    """
    Registered two-dimensional geometry of a circular Shape.

    Shape registered geometry uses a canonical unit envelope centered about
    the origin. A circle therefore has diameter 1.0 and extends from -0.5
    through +0.5 on both axes.
    """

    diameter: float = 1.0

    @property
    def width(self) -> float:
        """Return the registered X extent."""

        return self.diameter

    @property
    def height(self) -> float:
        """Return the registered Y extent."""

        return self.diameter

    @property
    def min_x(self) -> float:
        """Return the minimum registered X coordinate."""

        return -(self.diameter / 2.0)

    @property
    def max_x(self) -> float:
        """Return the maximum registered X coordinate."""

        return self.diameter / 2.0

    @property
    def min_y(self) -> float:
        """Return the minimum registered Y coordinate."""

        return -(self.diameter / 2.0)

    @property
    def max_y(self) -> float:
        """Return the maximum registered Y coordinate."""

        return self.diameter / 2.0


# =========================================================
# Geometry construction
# =========================================================


def create_circle_geometry() -> CircleGeometry:
    """
    Construct canonical registered circular Shape geometry.

    Registered Shape geometry is independent of the Shape's eventual physical
    size. Physical X/Y dimensionalization is introduced downstream.
    """

    return CircleGeometry()


# =========================================================
# Geometry rendering
# =========================================================


def render_circle_2d_source(
    geometry: CircleGeometry,
    *,
    openscad_fn: int,
) -> str:
    """
    Render registered circular Shape geometry as OpenSCAD 2D source.

    The circle remains centered about the Shape origin with its canonical
    registered diameter. Rendering resolution does not alter the registered
    geometry semantics.
    """

    return f"$fn={openscad_fn};\n\ncircle(d={geometry.diameter});\n"
