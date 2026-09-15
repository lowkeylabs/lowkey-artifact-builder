"""
Artwork Hole planar geometry.

This module owns Artwork-specific planar geometry for the optional
standalone Hole Feature.

Hole geometry is derived from the applicable dimensionalized Artwork
outer boundary. The Hole is circular and is positioned inward from one
of the cardinal boundaries by its radius plus the configured edge
distance.
"""
# File: src/lowkey_artifact_builder/model/models/artwork/hole.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from dataclasses import dataclass

from lowkey_artifact_builder.model.models.artwork.loop import Bounds


@dataclass(
    frozen=True,
    slots=True,
)
class HoleGeometry:
    """
    Resolved planar geometry for one participating Artwork Hole.
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
    Create planar geometry for a participating Artwork Hole.

    The Hole center lies on the selected cardinal axis through the
    applicable outer-boundary center. Its nearest circular edge is
    ``edge_distance`` inward from the selected boundary.

    Cardinal positions are:

        0       top
        90      right
        180     bottom
        -90     left

    Configuration validation owns validity of diameter, edge distance,
    and position. This function resolves already-valid configuration
    into physical planar geometry.
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
    "Bounds",
    "HoleGeometry",
    "create_hole_geometry",
]
