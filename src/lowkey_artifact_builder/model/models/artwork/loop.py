"""
Artwork Loop geometry.

This module owns the Artwork-specific geometric policy for constructing and
placing the optional Loop Feature relative to dimensionalized Artwork.

Loop geometry is expressed in the same physical coordinate system as the
dimensionalized Artwork envelope.

This module defines geometry only. It does not own Loop participation,
configuration resolution, color selection, Z placement, extrusion, or
packaging.
"""
# File: src/lowkey_artifact_builder/model/models/artwork/loop.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from dataclasses import dataclass

# =========================================================
# Errors
# =========================================================


class LoopGeometryError(ValueError):
    """
    Raised when Loop geometry cannot be constructed.
    """


# =========================================================
# Geometry
# =========================================================


@dataclass(
    frozen=True,
    slots=True,
)
class Bounds:
    """
    Axis-aligned dimensionalized Artwork envelope bounds.
    """

    min_x: float
    min_y: float
    max_x: float
    max_y: float

    @property
    def center_x(
        self,
    ) -> float:
        """
        Return the horizontal center of the envelope.
        """

        return (self.min_x + self.max_x) / 2.0

    @property
    def center_y(
        self,
    ) -> float:
        """
        Return the vertical center of the envelope.
        """

        return (self.min_y + self.max_y) / 2.0


@dataclass(
    frozen=True,
    slots=True,
)
class LoopGeometry:
    """
    Resolved planar geometry for one participating Artwork Loop.

    The Loop is an annulus centered at ``center_x``, ``center_y``.

    ``inner_attachment_point`` is the inward-facing point of the inner circle.
    By definition that point lies on the selected cardinal boundary of the
    dimensionalized Artwork envelope.

    ``envelope_bounds`` preserves the physical extent of the Artwork proper.
    ``manufactured_bounds`` includes both the Artwork envelope and Loop.
    """

    envelope_bounds: Bounds
    center_x: float
    center_y: float
    inner_radius: float
    outer_radius: float
    position: int
    inner_attachment_point: tuple[float, float]

    @property
    def inner_diameter(
        self,
    ) -> float:
        """
        Return the Loop inner diameter.
        """

        return self.inner_radius * 2.0

    @property
    def width(
        self,
    ) -> float:
        """
        Return the radial width of the annulus.
        """

        return self.outer_radius - self.inner_radius

    @property
    def outer_diameter(
        self,
    ) -> float:
        """
        Return the derived Loop outer diameter.
        """

        return self.outer_radius * 2.0

    @property
    def inward_overlap(
        self,
    ) -> float:
        """
        Return the Loop's inward overlap with the Artwork envelope.

        The inner circle touches the Artwork boundary. The annulus extends
        outward from that inner circle by its radial width, so the annulus
        overlaps the Artwork envelope inward by exactly that width.
        """

        return self.width

    @property
    def manufactured_bounds(
        self,
    ) -> Bounds:
        """
        Return the combined planar extent of Artwork and Loop.

        The Artwork envelope retains its original physical extent. The
        manufactured bounds expand only where Loop geometry extends beyond
        that envelope.
        """

        loop_min_x = self.center_x - self.outer_radius
        loop_min_y = self.center_y - self.outer_radius
        loop_max_x = self.center_x + self.outer_radius
        loop_max_y = self.center_y + self.outer_radius

        return Bounds(
            min_x=min(
                self.envelope_bounds.min_x,
                loop_min_x,
            ),
            min_y=min(
                self.envelope_bounds.min_y,
                loop_min_y,
            ),
            max_x=max(
                self.envelope_bounds.max_x,
                loop_max_x,
            ),
            max_y=max(
                self.envelope_bounds.max_y,
                loop_max_y,
            ),
        )


# =========================================================
# Public interface
# =========================================================


def create_loop_geometry(
    *,
    envelope_bounds: Bounds,
    inner_diameter: float,
    width: float,
    position: int,
) -> LoopGeometry:
    """
    Construct planar geometry for a participating Artwork Loop.

    The Loop is centered on the cardinal axis selected by ``position``.

    Supported positions are:

        0       top
        90      right
        180     bottom
        -90     left

    The inward-facing point of the Loop's inner circle lies exactly on the
    selected boundary of the dimensionalized Artwork envelope.

    Consequently the annulus overlaps the Artwork envelope inward by exactly
    ``width``.
    """

    if inner_diameter <= 0.0:
        raise LoopGeometryError("Participating Loop inner diameter must be positive.")

    if width <= 0.0:
        raise LoopGeometryError("Participating Loop width must be positive.")

    if position not in {
        0,
        90,
        180,
        -90,
    }:
        raise LoopGeometryError(f"Unsupported Artwork Loop position: {position}")

    inner_radius = inner_diameter / 2.0
    outer_radius = inner_radius + width

    center_x: float
    center_y: float
    attachment_x: float
    attachment_y: float

    if position == 0:
        center_x = envelope_bounds.center_x
        center_y = envelope_bounds.min_y + inner_radius

        attachment_x = envelope_bounds.center_x
        attachment_y = envelope_bounds.min_y

    elif position == 90:
        center_x = envelope_bounds.max_x - inner_radius
        center_y = envelope_bounds.center_y

        attachment_x = envelope_bounds.max_x
        attachment_y = envelope_bounds.center_y

    elif position == 180:
        center_x = envelope_bounds.center_x
        center_y = envelope_bounds.max_y - inner_radius

        attachment_x = envelope_bounds.center_x
        attachment_y = envelope_bounds.max_y

    else:
        center_x = envelope_bounds.min_x + inner_radius
        center_y = envelope_bounds.center_y

        attachment_x = envelope_bounds.min_x
        attachment_y = envelope_bounds.center_y

    return LoopGeometry(
        envelope_bounds=envelope_bounds,
        center_x=center_x,
        center_y=center_y,
        inner_radius=inner_radius,
        outer_radius=outer_radius,
        position=position,
        inner_attachment_point=(
            attachment_x,
            attachment_y,
        ),
    )
