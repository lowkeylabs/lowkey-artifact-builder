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
class PolygonGeometry:
    """
    Registered two-dimensional geometry of a regular polygon Shape.

    vertices contain the normalized registered polygon coordinates.

    The polygon is uniformly normalized after rotation so that its greatest
    X/Y extent is 1.0. Its registered bounding envelope is centered about
    the Shape origin.

    number_of_sides and rotation retain the structural policy from which the
    registered vertices were constructed.
    """

    number_of_sides: int
    rotation: float
    vertices: tuple[tuple[float, float], ...]

    @property
    def width(self) -> float:
        """Return the registered X extent."""

        return self.max_x - self.min_x

    @property
    def height(self) -> float:
        """Return the registered Y extent."""

        return self.max_y - self.min_y

    @property
    def min_x(self) -> float:
        """Return the minimum registered X coordinate."""

        return min(x for x, _ in self.vertices)

    @property
    def max_x(self) -> float:
        """Return the maximum registered X coordinate."""

        return max(x for x, _ in self.vertices)

    @property
    def min_y(self) -> float:
        """Return the minimum registered Y coordinate."""

        return min(y for _, y in self.vertices)

    @property
    def max_y(self) -> float:
        """Return the maximum registered Y coordinate."""

        return max(y for _, y in self.vertices)


type RegisteredGeometry = CircleGeometry | SquareGeometry | PolygonGeometry


@dataclass(
    frozen=True,
    slots=True,
)
class StructuralBase:
    """
    Physical structural base derived from registered Shape geometry.

    registered_geometry identifies the reusable nonphysical Shape geometry.

    shape_size defines the maximum physical X/Y envelope in millimeters.

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

        return self.registered_geometry.width * self.shape_size

    @property
    def height(self) -> float:
        """Return the physical Y extent in millimeters."""

        return self.registered_geometry.height * self.shape_size

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

    Polygon side count and rotation are resolved only when polygon geometry
    is selected.

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

    elif shape_geometry == "polygon":
        number_of_sides = context.resolver(
            "shape_sides",
        )
        rotation = context.resolver(
            "shape_rotation",
        )

        document = create_polygon_svg(
            create_polygon_geometry(
                number_of_sides=number_of_sides,
                rotation=rotation,
            ),
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


def create_polygon_geometry(
    *,
    number_of_sides: int,
    rotation: float,
) -> PolygonGeometry:
    """
    Construct canonical registered regular polygon Shape geometry.

    The unrotated polygon begins with one vertex on the positive Y axis.
    Positive rotation is counterclockwise when viewed from above.

    After rotation, the polygon is uniformly normalized and centered so that
    its greatest X/Y extent is 1.0. Uniform normalization preserves the
    regular polygon's proportions.
    """

    if number_of_sides < 3:
        raise ValueError("Regular polygon geometry requires at least 3 sides.")

    vertices = _create_regular_polygon_vertices(
        number_of_sides=number_of_sides,
        rotation=rotation,
    )

    normalized_vertices = _normalize_polygon_vertices(
        vertices,
    )

    return PolygonGeometry(
        number_of_sides=number_of_sides,
        rotation=rotation,
        vertices=normalized_vertices,
    )


def create_structural_base(
    registered_geometry: RegisteredGeometry,
    *,
    shape_size: float,
    shape_base_raise: float,
) -> StructuralBase:
    """
    Dimensionalize registered Shape geometry as a physical structural base.

    shape_size establishes the maximum physical X/Y envelope in millimeters.
    shape_base_raise establishes the physical base thickness.

    Registered geometry is normalized so that its greatest X/Y extent is 1.0.
    Physical dimensionalization therefore scales both axes uniformly by
    shape_size. Circle and square occupy shape_size on both axes, while a
    polygon may occupy less than shape_size on one axis depending on its side
    count and rotation.

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
        PolygonGeometry,
    ):
        geometry_name = "polygon"

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
# Polygon helpers
# =========================================================


def _create_regular_polygon_vertices(
    *,
    number_of_sides: int,
    rotation: float,
) -> tuple[tuple[float, float], ...]:
    """
    Construct rotated vertices for a regular polygon.

    Vertex zero begins on the positive Y axis before rotation. Positive
    rotation proceeds counterclockwise, so positive rotation moves that
    vertex toward the negative X axis.

    The returned vertices have not yet been normalized into the canonical
    registered Shape envelope.
    """

    angular_step = 360.0 / number_of_sides

    return tuple(
        _vertex_from_top_angle(
            rotation + index * angular_step,
        )
        for index in range(
            number_of_sides,
        )
    )


def _vertex_from_top_angle(
    angle: float,
) -> tuple[float, float]:
    """
    Return a unit-radius vertex using an angle measured from positive Y.

    Positive angles rotate counterclockwise from the positive Y axis.
    """

    radians = math.radians(
        angle,
    )

    return (
        -math.sin(radians),
        math.cos(radians),
    )


def _normalize_polygon_vertices(
    vertices: tuple[tuple[float, float], ...],
) -> tuple[tuple[float, float], ...]:
    """
    Uniformly normalize polygon vertices into registered Shape space.

    The polygon's rotated bounding envelope is first centered about the
    registered origin. All coordinates are then scaled by the same factor so
    that the greatest X/Y extent becomes 1.0.

    Uniform scaling preserves polygon proportions.
    """

    xs = [x for x, _ in vertices]
    ys = [y for _, y in vertices]

    min_x = min(xs)
    max_x = max(xs)
    min_y = min(ys)
    max_y = max(ys)

    width = max_x - min_x
    height = max_y - min_y

    maximum_extent = max(
        width,
        height,
    )

    center_x = (min_x + max_x) / 2.0
    center_y = (min_y + max_y) / 2.0

    scale = 1.0 / maximum_extent

    return tuple(
        (
            (x - center_x) * scale,
            (y - center_y) * scale,
        )
        for x, y in vertices
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


def create_polygon_svg(
    geometry: PolygonGeometry,
) -> ET.ElementTree[ET.Element[str]]:
    """
    Construct an SVG document containing registered regular polygon geometry.

    The polygon is persisted using its normalized registered vertices without
    introducing physical dimensions.
    """

    root = _create_svg_root(
        min_x=-0.5,
        min_y=-0.5,
        width=1.0,
        height=1.0,
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
