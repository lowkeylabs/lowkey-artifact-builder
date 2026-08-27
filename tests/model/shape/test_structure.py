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


# =========================================================
# Circle 2D production geometry
# =========================================================


def test_circle_geometry_produces_centered_openscad_circle() -> None:
    """
    Circle geometry can be expressed as executable 2D production geometry.

    The generated circle uses shape_size as its physical diameter and remains
    centered about the model origin.
    """

    geometry = structure.create_circle_geometry(
        shape_size=100.0,
    )

    source = structure.render_circle_2d_source(
        geometry,
        openscad_fn=360,
    )

    assert "circle(d=100.0" in source


def test_circle_2d_geometry_uses_configured_curve_resolution() -> None:
    """
    Circle production geometry uses the supplied OpenSCAD curve resolution.

    Rendering resolution does not alter the semantic physical size of the
    Shape.
    """

    geometry = structure.create_circle_geometry(
        shape_size=100.0,
    )

    source = structure.render_circle_2d_source(
        geometry,
        openscad_fn=180,
    )

    assert "$fn=180" in source


# =========================================================
# Structural base
# =========================================================


def test_circle_base_uses_shape_base_raise_as_thickness() -> None:
    """
    Circle base thickness is determined by shape_base_raise.

    The structural base begins at Z=0 and extends through the configured
    physical base raise.
    """

    geometry = structure.create_circle_geometry(
        shape_size=100.0,
    )

    base = structure.create_structural_base(
        geometry,
        shape_base_raise=2.0,
    )

    assert base.geometry is geometry
    assert base.thickness == 2.0
    assert base.min_z == 0.0
    assert base.max_z == 2.0


def test_circle_base_thickness_changes_with_shape_base_raise() -> None:
    """
    Changing shape_base_raise changes only the physical Z extent of the base.

    Base thickness is independent of the circle's X/Y size semantics.
    """

    geometry = structure.create_circle_geometry(
        shape_size=72.0,
    )

    base = structure.create_structural_base(
        geometry,
        shape_base_raise=3.5,
    )

    assert base.geometry.width == 72.0
    assert base.geometry.height == 72.0

    assert base.thickness == 3.5
    assert base.min_z == 0.0
    assert base.max_z == 3.5


# =========================================================
# Structural base production geometry
# =========================================================


def test_circle_base_extrudes_circle_to_configured_thickness() -> None:
    """
    Circle structural geometry is extruded through shape_base_raise.

    The resulting production geometry combines the circle's physical X/Y
    extent with the structural base's physical Z extent.
    """

    geometry = structure.create_circle_geometry(
        shape_size=100.0,
    )

    base = structure.create_structural_base(
        geometry,
        shape_base_raise=2.0,
    )

    source = structure.render_structural_base_source(
        base,
        openscad_fn=360,
    )

    assert "linear_extrude(height=2.0" in source
    assert "circle(d=100.0" in source


def test_circle_base_extrusion_uses_independent_xy_and_z_dimensions() -> None:
    """
    Structural base X/Y size and Z thickness remain independent policies.

    shape_size controls the circle diameter while shape_base_raise controls
    only its extrusion height.
    """

    geometry = structure.create_circle_geometry(
        shape_size=72.0,
    )

    base = structure.create_structural_base(
        geometry,
        shape_base_raise=3.5,
    )

    source = structure.render_structural_base_source(
        base,
        openscad_fn=180,
    )

    assert "$fn=180" in source
    assert "linear_extrude(height=3.5" in source
    assert "circle(d=72.0" in source
