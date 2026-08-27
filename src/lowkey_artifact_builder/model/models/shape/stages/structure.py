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


@dataclass(
    frozen=True,
    slots=True,
)
class StructuralBase:
    """
    Physical structural base of a Shape.

    geometry defines the base's X/Y extent.

    thickness defines its physical Z extent. Structural bases begin
    at Z=0 and extend upward through their configured thickness.
    """

    geometry: CircleGeometry
    thickness: float

    @property
    def min_z(self) -> float:
        """Return the minimum Z coordinate."""

        return 0.0

    @property
    def max_z(self) -> float:
        """Return the maximum Z coordinate."""

        return self.thickness


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


def create_structural_base(
    geometry: CircleGeometry,
    *,
    shape_base_raise: float,
) -> StructuralBase:
    """
    Construct the physical structural base for Shape geometry.

    shape_base_raise defines the base's physical thickness.

    The base begins at Z=0 and extends upward through
    shape_base_raise.
    """

    return StructuralBase(
        geometry=geometry,
        thickness=shape_base_raise,
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


def render_structural_base_source(
    base: StructuralBase,
    *,
    openscad_fn: int,
) -> str:
    """
    Render a structural Shape base as OpenSCAD source.

    The base's two-dimensional geometry determines its physical X/Y
    extent. Its thickness determines the extrusion height from Z=0.

    OpenSCAD curve resolution controls rendering quality without
    changing the physical geometry semantics.
    """

    geometry_source = render_circle_2d_source(
        base.geometry,
        openscad_fn=openscad_fn,
    )

    return f"linear_extrude(height={base.thickness}) {{\n{geometry_source}}}\n"
