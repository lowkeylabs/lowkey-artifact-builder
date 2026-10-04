"""
Tests for Shape Loop planar geometry.

Shape Loop geometry is Shape-owned physical geometry positioned relative
to the complete dimensionalized Shape envelope.
"""
# File: tests/model/shape/test_loop_geometry.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import pytest

from lowkey_artifact_builder.model.geometry import Bounds
from lowkey_artifact_builder.model.models.shape import loop


@pytest.mark.parametrize(
    ("position", "expected_center", "attachment_point"),
    [
        (0, (0.0, 52.0), (0.0, 50.0)),
        (90, (52.0, 0.0), (50.0, 0.0)),
        (180, (0.0, -52.0), (0.0, -50.0)),
        (-90, (-52.0, 0.0), (-50.0, 0.0)),
    ],
)
def test_shape_loop_preserves_annular_dimensions_and_tangent_placement(
    position: int,
    expected_center: tuple[float, float],
    attachment_point: tuple[float, float],
) -> None:
    """
    Shape Loop uses the configured annular dimensions and attaches its
    inner opening tangentially to the complete physical Shape envelope.

    A 4 mm inner diameter gives a 2 mm inner radius. With 1 mm radial
    width, the outer radius is 3 mm. The Loop center therefore lies
    2 mm beyond the selected boundary of a centered 100 mm Shape.
    """

    envelope = Bounds(
        min_x=-50.0,
        min_y=-50.0,
        max_x=50.0,
        max_y=50.0,
    )

    geometry = loop.create_loop_geometry(
        envelope_bounds=envelope,
        inner_diameter=4.0,
        width=1.0,
        position=position,
    )

    assert geometry.envelope_bounds == envelope
    assert geometry.inner_radius == pytest.approx(2.0)
    assert geometry.outer_radius == pytest.approx(3.0)
    assert geometry.center_x == pytest.approx(expected_center[0])
    assert geometry.center_y == pytest.approx(expected_center[1])
    assert geometry.inner_attachment_point == pytest.approx(
        attachment_point,
    )
