"""
Tests for Shape registered structural geometry.
"""
# File: tests/model/shape/test_structure.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from lowkey_artifact_builder.model.models.shape.stages import structure

# =========================================================
# Circle registered geometry
# =========================================================


def test_circle_geometry_uses_canonical_registered_extent() -> None:
    """
    Circle structural geometry uses the canonical Shape registered extent.

    Registered Shape geometry is nonphysical. The complete circle has
    diameter 1.0 regardless of the Shape's later physical size.
    """

    geometry = structure.create_circle_geometry()

    assert geometry.diameter == 1.0
    assert geometry.width == 1.0
    assert geometry.height == 1.0


def test_circle_geometry_is_centered_about_registered_origin() -> None:
    """
    Registered circle geometry is centered about the Shape origin.

    The canonical Shape envelope spans -0.5 through +0.5 on both axes.
    """

    geometry = structure.create_circle_geometry()

    assert geometry.min_x == -0.5
    assert geometry.max_x == 0.5
    assert geometry.min_y == -0.5
    assert geometry.max_y == 0.5


def test_circle_geometry_requires_no_physical_size() -> None:
    """
    Registered structural construction is independent of physical Shape size.

    Physical X/Y dimensionalization belongs to the downstream Shape
    dimensionalization boundary.
    """

    first = structure.create_circle_geometry()
    second = structure.create_circle_geometry()

    assert first == second
    assert first.diameter == 1.0


# =========================================================
# Circle registered production geometry
# =========================================================


def test_circle_geometry_produces_canonical_registered_circle() -> None:
    """
    Circle geometry can be expressed as registered two-dimensional geometry.

    Rendering preserves the canonical unit-diameter circle rather than
    introducing a physical Shape dimension.
    """

    geometry = structure.create_circle_geometry()

    source = structure.render_circle_2d_source(
        geometry,
        openscad_fn=360,
    )

    assert "circle(d=1.0" in source


def test_circle_registered_geometry_uses_configured_curve_resolution() -> None:
    """
    Rendering resolution does not alter registered geometry semantics.
    """

    geometry = structure.create_circle_geometry()

    source = structure.render_circle_2d_source(
        geometry,
        openscad_fn=180,
    )

    assert "$fn=180" in source
    assert "circle(d=1.0" in source
