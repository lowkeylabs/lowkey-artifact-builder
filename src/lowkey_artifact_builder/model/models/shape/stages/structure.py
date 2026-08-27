"""
Structural geometry for the Shape model.

This module defines the geometry semantics used by Shape structural
production.

Physical extrusion and persistent product generation are introduced by
later implementation slices.
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
    Physical two-dimensional geometry of a circular Shape.

    diameter is the complete physical X/Y extent of the circle.

    The circle is centered about the model origin so its bounds extend
    equally in each direction from zero.
    """

    diameter: float

    @property
    def width(self) -> float:
        """Return the physical X extent."""

        return self.diameter

    @property
    def height(self) -> float:
        """Return the physical Y extent."""

        return self.diameter

    @property
    def min_x(self) -> float:
        """Return the minimum X coordinate."""

        return -(self.diameter / 2.0)

    @property
    def max_x(self) -> float:
        """Return the maximum X coordinate."""

        return self.diameter / 2.0

    @property
    def min_y(self) -> float:
        """Return the minimum Y coordinate."""

        return -(self.diameter / 2.0)

    @property
    def max_y(self) -> float:
        """Return the maximum Y coordinate."""

        return self.diameter / 2.0


# =========================================================
# Geometry construction
# =========================================================


def create_circle_geometry(
    *,
    shape_size: float,
) -> CircleGeometry:
    """
    Construct circular Shape geometry.

    shape_size is the physical diameter of the circle and therefore
    defines both its X and Y extent.
    """

    return CircleGeometry(
        diameter=shape_size,
    )


# =========================================================
# Geometry rendering
# =========================================================


def render_circle_2d_source(
    geometry: CircleGeometry,
    *,
    openscad_fn: int,
) -> str:
    """
    Render circular Shape geometry as OpenSCAD 2D source.

    The circle remains centered about the model origin. OpenSCAD curve
    resolution controls rendering quality without changing the physical
    geometry semantics.
    """

    return f"$fn={openscad_fn};\n\ncircle(d={geometry.diameter});\n"
