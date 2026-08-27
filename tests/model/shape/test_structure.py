"""
Tests for Shape structural geometry.
"""
# File: tests/model/shape/test_structure.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from lowkey_artifact_builder.model.models.shape.stages import structure

# =========================================================
# Circle geometry
# =========================================================


def test_circle_geometry_uses_shape_size_as_diameter() -> None:
    """
    Circle shape_size defines the complete physical X/Y envelope.

    A circle with shape_size 100 therefore has a 100 mm diameter and
    occupies a 100 mm by 100 mm bounding envelope.
    """

    geometry = structure.create_circle_geometry(
        shape_size=100.0,
    )

    assert geometry.diameter == 100.0
    assert geometry.width == 100.0
    assert geometry.height == 100.0


def test_circle_geometry_is_centered_about_origin() -> None:
    """
    Structural circle geometry is centered about the model origin.

    Centering establishes a stable coordinate system for later extrusion,
    ridge construction, and registered Artwork placement.
    """

    geometry = structure.create_circle_geometry(
        shape_size=100.0,
    )

    assert geometry.min_x == -50.0
    assert geometry.max_x == 50.0
    assert geometry.min_y == -50.0
    assert geometry.max_y == 50.0


def test_circle_geometry_scales_directly_with_shape_size() -> None:
    """
    Changing shape_size changes the circle's physical envelope directly.

    shape_size is physical Shape policy rather than an arbitrary source-space
    dimension requiring a later independent scaling decision.
    """

    geometry = structure.create_circle_geometry(
        shape_size=72.0,
    )

    assert geometry.diameter == 72.0
    assert geometry.width == 72.0
    assert geometry.height == 72.0

    assert geometry.min_x == -36.0
    assert geometry.max_x == 36.0
    assert geometry.min_y == -36.0
    assert geometry.max_y == 36.0
