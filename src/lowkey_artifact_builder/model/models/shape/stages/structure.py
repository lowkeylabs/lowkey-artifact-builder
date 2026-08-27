"""
Registered structural geometry for the Shape model.

This module defines the registered, nonphysical geometry produced by Shape
structural production and the physical base geometry derived from it.

Physical persistence and extrusion belong to downstream Shape stages.
"""
# File: src/lowkey_artifact_builder/model/models/shape/stages/structure.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import math
import xml.etree.ElementTree as ET
from dataclasses import dataclass

from lowkey_artifact_builder.engine import StageContext
from lowkey_artifact_builder.formats import svg
from lowkey_artifact_builder.formats.svg import SVG_NS

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


@dataclass(
    frozen=True,
    slots=True,
)
class SquareGeometry:
    """
    Registered two-dimensional geometry of a square Shape.

    The square fills the canonical unit envelope centered about the origin.
    """

    side: float = 1.0

    @property
    def width(self) -> float:
        """Return the registered X extent."""

        return self.side

    @property
    def height(self) -> float:
        """Return the registered Y extent."""

        return self.side

    @property
    def min_x(self) -> float:
        """Return the minimum registered X coordinate."""

        return -(self.side / 2.0)

    @property
    def max_x(self) -> float:
        """Return the maximum registered X coordinate."""

        return self.side / 2.0

    @property
    def min_y(self) -> float:
        """Return the minimum registered Y coordinate."""

        return -(self.side / 2.0)

    @property
    def max_y(self) -> float:
        """Return the maximum registered Y coordinate."""

        return self.side / 2.0


@dataclass(
    frozen=True,
    slots=True,
)
class OctagonGeometry:
    """
    Registered two-dimensional geometry of a regular octagonal Shape.

    The octagon is centered about the origin and fits within the canonical
    unit bounding envelope.
    """

    extent: float = 1.0

    @property
    def width(self) -> float:
        """Return the registered X extent."""

        return self.extent

    @property
    def height(self) -> float:
        """Return the registered Y extent."""

        return self.extent

    @property
    def min_x(self) -> float:
        """Return the minimum registered X coordinate."""

        return -(self.extent / 2.0)

    @property
    def max_x(self) -> float:
        """Return the maximum registered X coordinate."""

        return self.extent / 2.0

    @property
    def min_y(self) -> float:
        """Return the minimum registered Y coordinate."""

        return -(self.extent / 2.0)

    @property
    def max_y(self) -> float:
        """Return the maximum registered Y coordinate."""

        return self.extent / 2.0

    @property
    def vertices(self) -> tuple[tuple[float, float], ...]:
        """
        Return the vertices of the centered regular octagon.

        Opposing horizontal and vertical vertices establish the complete
        canonical registered bounding envelope.
        """

        radius = self.extent / 2.0

        return tuple(
            (
                radius * math.cos(math.radians(angle)),
                radius * math.sin(math.radians(angle)),
            )
            for angle in range(
                0,
                360,
                45,
            )
        )


type RegisteredGeometry = CircleGeometry | SquareGeometry | OctagonGeometry


@dataclass(
    frozen=True,
    slots=True,
)
class StructuralBase:
    """
    Physical structural base derived from registered Shape geometry.

    registered_geometry identifies the reusable nonphysical Shape geometry.

    shape_size defines the complete physical X/Y envelope in millimeters.

    thickness defines the physical Z extent. The structural base begins at
    Z=0 and extends upward through its configured thickness.
    """

    registered_geometry: RegisteredGeometry
    geometry_name: str
    shape_size: float
    thickness: float

    @property
    def width(self) -> float:
        """Return the physical X extent in millimeters."""

        return self.shape_size

    @property
    def height(self) -> float:
        """Return the physical Y extent in millimeters."""

        return self.shape_size

    @property
    def min_z(self) -> float:
        """Return the minimum physical Z coordinate."""

        return 0.0

    @property
    def max_z(self) -> float:
        """Return the maximum physical Z coordinate."""

        return self.thickness


# =========================================================
# Public interface
# =========================================================


def execute(
    context: StageContext,
) -> None:
    """
    Execute registered Shape structural production.

    Structural production resolves the selected Shape geometry and
    materializes the declared registered SVG product through StageContext.

    Physical dimensionalization and extrusion belong to downstream
    Shape stages.
    """

    shape_geometry = context.resolver(
        "shape_geometry",
    )

    if shape_geometry == "circle":
        document = create_circle_svg(
            create_circle_geometry(),
        )

    elif shape_geometry == "square":
        document = create_square_svg(
            create_square_geometry(),
        )

    elif shape_geometry == "octagon":
        document = create_octagon_svg(
            create_octagon_geometry(),
        )

    else:
        raise ValueError(f"Unsupported Shape geometry: {shape_geometry!r}.")

    output = context.output(
        "structure",
    )

    svg.save(
        document,
        output,
    )


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


def create_square_geometry() -> SquareGeometry:
    """
    Construct canonical registered square Shape geometry.

    The square fills the canonical unit envelope centered about the origin
    without introducing physical dimensions.
    """

    return SquareGeometry()


def create_octagon_geometry() -> OctagonGeometry:
    """
    Construct canonical registered regular octagonal Shape geometry.

    The octagon is centered about the origin and fits within the canonical
    unit bounding envelope without introducing physical dimensions.
    """

    return OctagonGeometry()


def create_structural_base(
    registered_geometry: RegisteredGeometry,
    *,
    shape_size: float,
    shape_base_raise: float,
) -> StructuralBase:
    """
    Dimensionalize registered Shape geometry as a physical structural base.

    shape_size establishes the complete physical X/Y envelope in millimeters.
    shape_base_raise establishes the physical base thickness.

    The registered source geometry remains unchanged.
    """

    if isinstance(
        registered_geometry,
        CircleGeometry,
    ):
        geometry_name = "circle"

    elif isinstance(
        registered_geometry,
        SquareGeometry,
    ):
        geometry_name = "square"

    elif isinstance(
        registered_geometry,
        OctagonGeometry,
    ):
        geometry_name = "octagon"

    else:
        raise TypeError(
            f"Unsupported registered Shape geometry: {type(registered_geometry).__name__}."
        )

    return StructuralBase(
        registered_geometry=registered_geometry,
        geometry_name=geometry_name,
        shape_size=shape_size,
        thickness=shape_base_raise,
    )


# =========================================================
# SVG construction
# =========================================================


def create_circle_svg(
    geometry: CircleGeometry,
) -> ET.ElementTree[ET.Element[str]]:
    """
    Construct an SVG document containing registered circular Shape geometry.

    The document uses the geometry's registered bounds as its viewBox and does
    not assign physical width or height attributes.
    """

    root = _create_svg_root(
        min_x=geometry.min_x,
        min_y=geometry.min_y,
        width=geometry.width,
        height=geometry.height,
    )

    ET.SubElement(
        root,
        f"{{{SVG_NS}}}circle",
        {
            "cx": "0.0",
            "cy": "0.0",
            "r": str(geometry.diameter / 2.0),
        },
    )

    return ET.ElementTree(
        root,
    )


def create_square_svg(
    geometry: SquareGeometry,
) -> ET.ElementTree[ET.Element[str]]:
    """
    Construct an SVG document containing registered square Shape geometry.

    The square fills the canonical registered envelope and does not introduce
    physical dimensions.
    """

    root = _create_svg_root(
        min_x=geometry.min_x,
        min_y=geometry.min_y,
        width=geometry.width,
        height=geometry.height,
    )

    ET.SubElement(
        root,
        f"{{{SVG_NS}}}rect",
        {
            "x": str(geometry.min_x),
            "y": str(geometry.min_y),
            "width": str(geometry.width),
            "height": str(geometry.height),
        },
    )

    return ET.ElementTree(
        root,
    )


def create_octagon_svg(
    geometry: OctagonGeometry,
) -> ET.ElementTree[ET.Element[str]]:
    """
    Construct an SVG document containing registered octagonal Shape geometry.

    The regular octagon is centered within the canonical registered envelope
    and does not introduce physical dimensions.
    """

    root = _create_svg_root(
        min_x=geometry.min_x,
        min_y=geometry.min_y,
        width=geometry.width,
        height=geometry.height,
    )

    points = " ".join(f"{x},{y}" for x, y in geometry.vertices)

    ET.SubElement(
        root,
        f"{{{SVG_NS}}}polygon",
        {
            "points": points,
        },
    )

    return ET.ElementTree(
        root,
    )


# =========================================================
# SVG helpers
# =========================================================


def _create_svg_root(
    *,
    min_x: float,
    min_y: float,
    width: float,
    height: float,
) -> ET.Element[str]:
    """
    Construct the root for a registered Shape SVG document.

    Registered SVG documents describe geometry only and therefore omit
    physical width and height attributes.
    """

    return ET.Element(
        f"{{{SVG_NS}}}svg",
        {
            "viewBox": (f"{min_x} {min_y} {width} {height}"),
        },
    )
