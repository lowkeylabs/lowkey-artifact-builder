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
        (0, (50.0, 82.0)),
        (90, (82.0, 50.0)),
        (180, (50.0, 18.0)),
        (-90, (18.0, 50.0)),
    ],
)
def test_loop_is_centered_on_selected_cardinal_axis(
    position: int,
    expected_center: tuple[float, float],
) -> None:
    """
    Loop center follows Artwork's cardinal-coordinate convention.

    Position 0 is top (+Y), 90 is right (+X), 180 is bottom (-Y),
    and -90 is left (-X).

    For a 4 mm inner diameter, the Loop center lies one 2 mm inner
    radius outward from the selected envelope boundary.
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
        (0, (50.0, 80.0)),
        (90, (80.0, 50.0)),
        (180, (50.0, 20.0)),
        (-90, (20.0, 50.0)),
    ],
)
def test_loop_inner_circle_is_tangent_to_artwork_envelope(
    position: int,
    attachment_point: tuple[float, float],
) -> None:
    """
    The Loop's inner opening is externally tangent to the Artwork envelope.

    The complete inner opening therefore remains outside the rectangular
    Artwork envelope while touching it at the selected cardinal boundary.
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
# Registration
# =========================================================


def test_loop_geometry_remains_in_artwork_coordinate_system() -> None:
    """
    Loop geometry is expressed in the dimensionalized Artwork coordinate system.

    Placement uses the supplied Artwork envelope rather than assuming an
    origin-centered or fixed-size Artwork.
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

    assert geometry.center_x == pytest.approx(140.0)
    assert geometry.center_y == pytest.approx(36.0)
    assert geometry.inner_attachment_point == pytest.approx((137.0, 36.0))


# =========================================================
# Physical extent
# =========================================================


@pytest.mark.parametrize(
    ("position", "expected_bounds"),
    [
        (0, (0.0, 0.0, 100.0, 108.0)),
        (90, (0.0, 0.0, 108.0, 100.0)),
        (180, (0.0, -8.0, 100.0, 100.0)),
        (-90, (-8.0, 0.0, 100.0, 100.0)),
    ],
)
def test_loop_extends_beyond_artwork_envelope(
    position: int,
    expected_bounds: tuple[float, float, float, float],
) -> None:
    """
    Loop increases manufactured-object extent outside the Artwork envelope.

    With a 6 mm inner diameter and 2 mm radial width, the inner radius
    is 3 mm and the outer radius is 5 mm. Because the inner opening is
    tangent to the Artwork envelope, the Loop extends 8 mm beyond the
    selected envelope boundary.

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
    assert geometry.envelope_bounds.max_x - geometry.envelope_bounds.min_x == pytest.approx(100.0)
    assert geometry.envelope_bounds.max_y - geometry.envelope_bounds.min_y == pytest.approx(100.0)


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
    assert manufactured_height == pytest.approx(108.0)
