"""
Tests for Artwork Hole planar geometry.

Hole geometry is Artwork-owned physical geometry derived from the
dimensionalized Artwork envelope and resolved Hole parameters.

The Hole is subtractive geometry placed inward from one of the cardinal
boundaries of the applicable size-controlled Artwork extent.
"""
# File: tests/model/artwork/test_hole_geometry.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import pytest

from lowkey_artifact_builder.model.models.artwork.hole import (
    Bounds,
    create_hole_geometry,
)

# =========================================================
# Hole dimensions
# =========================================================


def test_hole_radius_is_half_configured_diameter() -> None:
    """
    Hole diameter directly determines the radius of the circular opening.
    """

    geometry = create_hole_geometry(
        envelope_bounds=Bounds(
            min_x=-20.0,
            min_y=-15.0,
            max_x=20.0,
            max_y=15.0,
        ),
        diameter=6.0,
        edge_distance=1.0,
        position=0,
    )

    assert geometry.radius == pytest.approx(3.0)


# =========================================================
# Cardinal placement
# =========================================================


@pytest.mark.parametrize(
    (
        "position",
        "expected_x",
        "expected_y",
    ),
    (
        (0, 0.0, 11.0),
        (90, 16.0, 0.0),
        (180, 0.0, -11.0),
        (-90, -16.0, 0.0),
    ),
)
def test_hole_center_is_placed_inward_from_cardinal_boundary(
    position: int,
    expected_x: float,
    expected_y: float,
) -> None:
    """
    Hole center lies on the selected cardinal axis through the Artwork
    center.

    The center is inset from the selected boundary by the Hole radius plus
    the configured edge distance.
    """

    geometry = create_hole_geometry(
        envelope_bounds=Bounds(
            min_x=-20.0,
            min_y=-15.0,
            max_x=20.0,
            max_y=15.0,
        ),
        diameter=6.0,
        edge_distance=1.0,
        position=position,
    )

    assert geometry.center_x == pytest.approx(expected_x)
    assert geometry.center_y == pytest.approx(expected_y)


@pytest.mark.parametrize(
    (
        "position",
        "expected_x",
        "expected_y",
    ),
    (
        (0, 0.0, 14.0),
        (90, 19.0, 0.0),
        (180, 0.0, -14.0),
        (-90, -19.0, 0.0),
    ),
)
def test_hole_nearest_edge_is_configured_distance_from_boundary(
    position: int,
    expected_x: float,
    expected_y: float,
) -> None:
    """
    The nearest Hole edge is exactly edge_distance inward from the selected
    outer boundary.

    For a 6 mm Hole with a 1 mm edge distance, the center is therefore
    4 mm inward and the nearest circular edge is 1 mm inward.
    """

    geometry = create_hole_geometry(
        envelope_bounds=Bounds(
            min_x=-20.0,
            min_y=-15.0,
            max_x=20.0,
            max_y=15.0,
        ),
        diameter=6.0,
        edge_distance=1.0,
        position=position,
    )

    assert geometry.nearest_edge_x == pytest.approx(expected_x)
    assert geometry.nearest_edge_y == pytest.approx(expected_y)


# =========================================================
# Non-square Artwork
# =========================================================


def test_hole_top_placement_uses_actual_vertical_boundary() -> None:
    """
    Top Hole placement uses the actual Y boundary of a non-square Artwork
    rather than assuming artwork_size in both dimensions.
    """

    geometry = create_hole_geometry(
        envelope_bounds=Bounds(
            min_x=-20.0,
            min_y=-10.0,
            max_x=20.0,
            max_y=10.0,
        ),
        diameter=4.0,
        edge_distance=1.0,
        position=0,
    )

    assert geometry.center_x == pytest.approx(0.0)
    assert geometry.center_y == pytest.approx(7.0)

    assert geometry.nearest_edge_x == pytest.approx(0.0)
    assert geometry.nearest_edge_y == pytest.approx(9.0)


def test_hole_right_placement_uses_actual_horizontal_boundary() -> None:
    """
    Right Hole placement uses the actual X boundary of a non-square Artwork
    rather than assuming artwork_size in both dimensions.
    """

    geometry = create_hole_geometry(
        envelope_bounds=Bounds(
            min_x=-20.0,
            min_y=-10.0,
            max_x=20.0,
            max_y=10.0,
        ),
        diameter=4.0,
        edge_distance=1.0,
        position=90,
    )

    assert geometry.center_x == pytest.approx(17.0)
    assert geometry.center_y == pytest.approx(0.0)

    assert geometry.nearest_edge_x == pytest.approx(19.0)
    assert geometry.nearest_edge_y == pytest.approx(0.0)


# =========================================================
# Coordinate registration
# =========================================================


@pytest.mark.parametrize(
    (
        "position",
        "expected_x",
        "expected_y",
    ),
    (
        (0, 40.0, 36.0),
        (90, 56.0, 25.0),
        (180, 40.0, 14.0),
        (-90, 24.0, 25.0),
    ),
)
def test_hole_placement_uses_actual_envelope_center(
    position: int,
    expected_x: float,
    expected_y: float,
) -> None:
    """
    Hole cardinal placement is relative to the actual envelope center rather
    than coordinate-system origin.

    The envelope from (20, 10) through (60, 40) has center (40, 25).
    """

    geometry = create_hole_geometry(
        envelope_bounds=Bounds(
            min_x=20.0,
            min_y=10.0,
            max_x=60.0,
            max_y=40.0,
        ),
        diameter=6.0,
        edge_distance=1.0,
        position=position,
    )

    assert geometry.center_x == pytest.approx(expected_x)
    assert geometry.center_y == pytest.approx(expected_y)


@pytest.mark.parametrize(
    (
        "position",
        "expected_x",
        "expected_y",
    ),
    (
        (0, 40.0, 39.0),
        (90, 59.0, 25.0),
        (180, 40.0, 11.0),
        (-90, 21.0, 25.0),
    ),
)
def test_hole_nearest_edge_uses_actual_non_origin_boundary(
    position: int,
    expected_x: float,
    expected_y: float,
) -> None:
    """
    Hole edge distance is measured from the actual selected envelope
    boundary even when the envelope is not centered on coordinate origin.
    """

    geometry = create_hole_geometry(
        envelope_bounds=Bounds(
            min_x=20.0,
            min_y=10.0,
            max_x=60.0,
            max_y=40.0,
        ),
        diameter=6.0,
        edge_distance=1.0,
        position=position,
    )

    assert geometry.nearest_edge_x == pytest.approx(expected_x)
    assert geometry.nearest_edge_y == pytest.approx(expected_y)


# =========================================================
# Size-controlled extent
# =========================================================


def test_hole_geometry_preserves_applicable_outer_bounds() -> None:
    """
    Hole is subtractive geometry and does not increase or redefine the
    applicable size-controlled Artwork outer extent.
    """

    bounds = Bounds(
        min_x=-20.0,
        min_y=-15.0,
        max_x=20.0,
        max_y=15.0,
    )

    geometry = create_hole_geometry(
        envelope_bounds=bounds,
        diameter=6.0,
        edge_distance=1.0,
        position=0,
    )

    assert geometry.envelope_bounds == bounds


def test_hole_geometry_does_not_expand_outer_extent() -> None:
    """
    Every point of the Hole lies inward from the selected size-controlled
    boundary.

    Hole geometry therefore cannot become an additional manufactured outer
    extent.
    """

    bounds = Bounds(
        min_x=-20.0,
        min_y=-15.0,
        max_x=20.0,
        max_y=15.0,
    )

    geometry = create_hole_geometry(
        envelope_bounds=bounds,
        diameter=6.0,
        edge_distance=1.0,
        position=0,
    )

    assert geometry.center_x - geometry.radius >= bounds.min_x
    assert geometry.center_x + geometry.radius <= bounds.max_x
    assert geometry.center_y - geometry.radius >= bounds.min_y
    assert geometry.center_y + geometry.radius <= bounds.max_y
