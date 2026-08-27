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

import xml.etree.ElementTree as ET
from dataclasses import dataclass

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

    root = ET.Element(
        f"{{{SVG_NS}}}svg",
        {
            "viewBox": (f"{geometry.min_x} {geometry.min_y} {geometry.width} {geometry.height}"),
        },
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
