"""
Shape Hole planar geometry.

This module owns Shape-specific planar geometry for the optional
Hole Feature.

Hole geometry is derived from the complete dimensionalized Shape
outer boundary. The Hole is circular and is positioned inward from one
of the cardinal boundaries by its radius plus the configured edge
distance.

This module defines geometry only. It does not own Hole participation,
configuration resolution, subtraction, extrusion, or packaging.
"""
# File: src/lowkey_artifact_builder/model/models/shape/hole.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from dataclasses import dataclass

from lowkey_artifact_builder.model.geometry import Bounds


@dataclass(
    frozen=True,
    slots=True,
)
class HoleGeometry:
    """
    Resolved planar geometry for one participating Shape Hole.
    """

    envelope_bounds: Bounds
    center_x: float
    center_y: float
    radius: float
    nearest_edge_x: float
    nearest_edge_y: float


def create_hole_geometry(
    *,
    envelope_bounds: Bounds,
    diameter: float,
    edge_distance: float,
    position: int,
) -> HoleGeometry:
    """
    Create planar geometry for a participating Shape Hole.

    The Hole center lies on the selected cardinal axis through the
    complete dimensionalized Shape boundary center. Its nearest circular
    edge is ``edge_distance`` inward from the selected boundary.

    Cardinal positions are:

        0       top (+Y)
        90      right (+X)
        180     bottom (-Y)
        -90     left (-X)

    Configuration validation owns validity of diameter, edge distance,
    and position. This function resolves already-valid configuration
    into physical planar geometry.

    The supplied bounds describe the complete Shape envelope established
    by ``shape_size``. Optional features that extend beyond that envelope
    do not redefine the Hole positioning boundary.
    """

    radius = diameter / 2.0
    inset = radius + edge_distance

    center_x = envelope_bounds.center_x
    center_y = envelope_bounds.center_y

    nearest_edge_x = center_x
    nearest_edge_y = center_y

    if position == 0:
        center_y = envelope_bounds.max_y - inset
        nearest_edge_y = envelope_bounds.max_y - edge_distance

    elif position == 90:
        center_x = envelope_bounds.max_x - inset
        nearest_edge_x = envelope_bounds.max_x - edge_distance

    elif position == 180:
        center_y = envelope_bounds.min_y + inset
        nearest_edge_y = envelope_bounds.min_y + edge_distance

    elif position == -90:
        center_x = envelope_bounds.min_x + inset
        nearest_edge_x = envelope_bounds.min_x + edge_distance

    return HoleGeometry(
        envelope_bounds=envelope_bounds,
        center_x=center_x,
        center_y=center_y,
        radius=radius,
        nearest_edge_x=nearest_edge_x,
        nearest_edge_y=nearest_edge_y,
    )


__all__ = [
    "HoleGeometry",
    "create_hole_geometry",
]
