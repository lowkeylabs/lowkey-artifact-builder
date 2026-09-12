"""
Tests for Artwork Loop geometry.

Loop geometry is Artwork-owned physical geometry derived from the
dimensionalized Artwork envelope and resolved Loop parameters.
"""
# File: tests/model/artwork/test_loop_geometry.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import pytest

from lowkey_artifact_builder.model.models.artwork import loop

# =========================================================
# Annular geometry
# =========================================================


@pytest.mark.parametrize(
    ("inner_diameter", "width", "outer_diameter"),
    [
        (0.5, 1.0, 2.5),
        (4.0, 1.0, 6.0),
        (6.0, 2.0, 10.0),
    ],
)
def test_loop_has_defined_annular_dimensions(
    inner_diameter: float,
    width: float,
    outer_diameter: float,
) -> None:
    """
    Loop outer diameter is derived from inner diameter and radial width.
    """

    geometry = loop.create_loop_geometry(
        envelope_bounds=loop.Bounds(
            min_x=20.0,
            min_y=20.0,
            max_x=80.0,
            max_y=80.0,
        ),
        inner_diameter=inner_diameter,
        width=width,
        position=0,
    )

    assert geometry.inner_radius == pytest.approx(inner_diameter / 2.0)
    assert geometry.outer_radius == pytest.approx(inner_diameter / 2.0 + width)
    assert geometry.outer_diameter == pytest.approx(outer_diameter)


# =========================================================
# Cardinal placement
# =========================================================


@pytest.mark.parametrize(
    ("position", "expected_center"),
    [
        (0, (50.0, 22.0)),
        (90, (78.0, 50.0)),
        (180, (50.0, 78.0)),
        (-90, (22.0, 50.0)),
    ],
)
def test_loop_is_centered_on_selected_cardinal_axis(
    position: int,
    expected_center: tuple[float, float],
) -> None:
    """
    Loop center is positioned from the selected envelope attachment boundary.

    For a 4 mm inner diameter and 1 mm width, the inner radius is 2 mm.
    The inward-facing point of the inner circle lies on the envelope boundary.
    """

    geometry = loop.create_loop_geometry(
        envelope_bounds=loop.Bounds(
            min_x=20.0,
            min_y=20.0,
            max_x=80.0,
            max_y=80.0,
        ),
        inner_diameter=4.0,
        width=1.0,
        position=position,
    )

    assert geometry.center_x == pytest.approx(expected_center[0])
    assert geometry.center_y == pytest.approx(expected_center[1])


# =========================================================
# Envelope attachment
# =========================================================


@pytest.mark.parametrize(
    ("position", "attachment_point"),
    [
        (0, (50.0, 20.0)),
        (90, (80.0, 50.0)),
        (180, (50.0, 80.0)),
        (-90, (20.0, 50.0)),
    ],
)
def test_loop_inner_circle_touches_artwork_envelope(
    position: int,
    attachment_point: tuple[float, float],
) -> None:
    """
    The inward-facing point of the inner circle lies on the envelope boundary.
    """

    geometry = loop.create_loop_geometry(
        envelope_bounds=loop.Bounds(
            min_x=20.0,
            min_y=20.0,
            max_x=80.0,
            max_y=80.0,
        ),
        inner_diameter=4.0,
        width=1.0,
        position=position,
    )

    assert geometry.inner_attachment_point == pytest.approx(attachment_point)


# =========================================================
# Artwork overlap
# =========================================================


@pytest.mark.parametrize(
    "position",
    [
        0,
        90,
        180,
        -90,
    ],
)
def test_loop_overlaps_artwork_by_exactly_loop_width(
    position: int,
) -> None:
    """
    The Loop extends inward from the Artwork boundary by exactly its width.
    """

    geometry = loop.create_loop_geometry(
        envelope_bounds=loop.Bounds(
            min_x=20.0,
            min_y=20.0,
            max_x=80.0,
            max_y=80.0,
        ),
        inner_diameter=4.0,
        width=1.5,
        position=position,
    )

    assert geometry.inward_overlap == pytest.approx(1.5)


# =========================================================
# Registration
# =========================================================


def test_loop_geometry_remains_in_artwork_coordinate_system() -> None:
    """
    Loop geometry is expressed in the dimensionalized Artwork coordinate system.

    Placement must use the actual dimensionalized envelope rather than assuming
    an origin-centered or fixed-size Artwork.
    """

    geometry = loop.create_loop_geometry(
        envelope_bounds=loop.Bounds(
            min_x=37.0,
            min_y=11.0,
            max_x=137.0,
            max_y=61.0,
        ),
        inner_diameter=6.0,
        width=2.0,
        position=90,
    )

    assert geometry.center_x == pytest.approx(134.0)
    assert geometry.center_y == pytest.approx(36.0)
    assert geometry.inner_attachment_point == pytest.approx((137.0, 36.0))


# =========================================================
# Physical extent
# =========================================================


@pytest.mark.parametrize(
    ("position", "expected_bounds"),
    [
        (0, (0.0, -2.0, 100.0, 100.0)),
        (90, (0.0, 0.0, 102.0, 100.0)),
        (180, (0.0, 0.0, 100.0, 102.0)),
        (-90, (-2.0, 0.0, 100.0, 100.0)),
    ],
)
def test_loop_extends_beyond_artwork_envelope(
    position: int,
    expected_bounds: tuple[float, float, float, float],
) -> None:
    """
    Loop increases manufactured-object extent outside the Artwork envelope.

    artwork_size controls the Artwork envelope itself, not the combined
    Artwork-plus-Loop object.
    """

    envelope = loop.Bounds(
        min_x=0.0,
        min_y=0.0,
        max_x=100.0,
        max_y=100.0,
    )

    geometry = loop.create_loop_geometry(
        envelope_bounds=envelope,
        inner_diameter=6.0,
        width=2.0,
        position=position,
    )

    assert geometry.manufactured_bounds == loop.Bounds(
        min_x=expected_bounds[0],
        min_y=expected_bounds[1],
        max_x=expected_bounds[2],
        max_y=expected_bounds[3],
    )


def test_loop_does_not_change_artwork_envelope_extent() -> None:
    """
    Enabling Loop does not shrink the Artwork proper to preserve total extent.
    """

    envelope = loop.Bounds(
        min_x=0.0,
        min_y=0.0,
        max_x=100.0,
        max_y=100.0,
    )

    geometry = loop.create_loop_geometry(
        envelope_bounds=envelope,
        inner_diameter=6.0,
        width=2.0,
        position=0,
    )

    assert geometry.envelope_bounds == envelope
    assert geometry.envelope_bounds.max_x - geometry.envelope_bounds.min_x == (pytest.approx(100.0))
    assert geometry.envelope_bounds.max_y - geometry.envelope_bounds.min_y == (pytest.approx(100.0))


def test_total_manufactured_extent_increases_when_loop_participates() -> None:
    """
    Total standalone manufactured extent includes Loop outside Artwork.
    """

    envelope = loop.Bounds(
        min_x=0.0,
        min_y=0.0,
        max_x=100.0,
        max_y=100.0,
    )

    geometry = loop.create_loop_geometry(
        envelope_bounds=envelope,
        inner_diameter=6.0,
        width=2.0,
        position=0,
    )

    artwork_width = envelope.max_x - envelope.min_x
    artwork_height = envelope.max_y - envelope.min_y

    manufactured_width = geometry.manufactured_bounds.max_x - geometry.manufactured_bounds.min_x
    manufactured_height = geometry.manufactured_bounds.max_y - geometry.manufactured_bounds.min_y

    assert manufactured_width == pytest.approx(artwork_width)
    assert manufactured_height > artwork_height
    assert manufactured_height == pytest.approx(102.0)
