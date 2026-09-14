"""
Tests for Artwork Outer Ridge geometry.

Outer Ridge geometry is Artwork-owned physical geometry derived from the
dimensionalized Artwork envelope and resolved Outer Ridge width.

The Outer Ridge preserves artwork_size as the full size-controlled extent.
Artwork proper is uniformly scaled inward, preserving aspect ratio and
registration.
"""
# File: tests/model/artwork/test_outer_ridge_geometry.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import pytest

from lowkey_artifact_builder.model.models.artwork.outer_ridge import (
    artwork_scale_for_outer_ridge,
    create_outer_ridge_geometry,
)

# =========================================================
# Artwork scaling
# =========================================================


def test_outer_ridge_uniformly_scales_artwork_inside_reserved_perimeter() -> None:
    """
    Outer Ridge width reserves physical space around the size-controlling
    Artwork extent.

    The remaining Artwork is uniformly scaled in X and Y rather than
    independently subtracting ridge width from each occupied dimension.
    """

    scale = artwork_scale_for_outer_ridge(
        artwork_size=40.0,
        outer_ridge_width=2.0,
    )

    assert scale == pytest.approx(0.9)


def test_outer_ridge_uniform_scaling_preserves_artwork_aspect_ratio() -> None:
    """
    Outer Ridge scaling preserves the aspect ratio of a non-square Artwork
    envelope.

    A 40 x 30 mm envelope with a 2 mm Outer Ridge becomes 36 x 27 mm,
    rather than 36 x 26 mm.
    """

    scale = artwork_scale_for_outer_ridge(
        artwork_size=40.0,
        outer_ridge_width=2.0,
    )

    width = 40.0 * scale
    height = 30.0 * scale

    assert width == pytest.approx(36.0)
    assert height == pytest.approx(27.0)
    assert width / height == pytest.approx(40.0 / 30.0)


def test_disabled_outer_ridge_does_not_scale_artwork() -> None:
    """
    Disabled Outer Ridge leaves standalone Artwork at its ordinary size.
    """

    scale = artwork_scale_for_outer_ridge(
        artwork_size=40.0,
        outer_ridge_width=0.0,
    )

    assert scale == pytest.approx(1.0)


# =========================================================
# Envelope geometry
# =========================================================


def test_outer_ridge_preserves_full_size_outer_envelope() -> None:
    """
    Outer Ridge outer geometry retains the full dimensionalized Artwork
    envelope.

    artwork_size continues to control the maximum Artwork extent.
    """

    geometry = create_outer_ridge_geometry(
        envelope_width=40.0,
        envelope_height=30.0,
        artwork_size=40.0,
        outer_ridge_width=2.0,
    )

    assert geometry.outer_width == pytest.approx(40.0)
    assert geometry.outer_height == pytest.approx(30.0)


def test_outer_ridge_inner_envelope_is_uniformly_scaled() -> None:
    """
    The inner Outer Ridge boundary is the uniformly scaled Artwork envelope.

    A 40 x 30 mm envelope with a 2 mm ridge therefore has a 36 x 27 mm
    inner envelope.
    """

    geometry = create_outer_ridge_geometry(
        envelope_width=40.0,
        envelope_height=30.0,
        artwork_size=40.0,
        outer_ridge_width=2.0,
    )

    assert geometry.inner_width == pytest.approx(36.0)
    assert geometry.inner_height == pytest.approx(27.0)


def test_outer_ridge_inner_and_outer_envelopes_share_center() -> None:
    """
    Uniformly scaling Artwork inward preserves the envelope center.

    The reserved Outer Ridge therefore surrounds the Artwork rather than
    shifting it toward one side of the full-size envelope.
    """

    geometry = create_outer_ridge_geometry(
        envelope_width=40.0,
        envelope_height=30.0,
        artwork_size=40.0,
        outer_ridge_width=2.0,
    )

    assert geometry.inner_offset_x == pytest.approx(2.0)
    assert geometry.inner_offset_y == pytest.approx(1.5)


# =========================================================
# Registered-envelope transform
# =========================================================


def test_outer_ridge_inner_transform_scales_about_envelope_center() -> None:
    """
    The inner envelope is produced by uniformly scaling the registered
    envelope about its own center.

    Scaling must not move the envelope toward the registered origin.
    """

    geometry = create_outer_ridge_geometry(
        envelope_width=40.0,
        envelope_height=30.0,
        artwork_size=40.0,
        outer_ridge_width=2.0,
    )

    transform = geometry.inner_transform

    assert transform.scale_x == pytest.approx(0.9)
    assert transform.scale_y == pytest.approx(0.9)

    assert transform.translate_x == pytest.approx(2.0)
    assert transform.translate_y == pytest.approx(1.5)


def test_outer_ridge_inner_transform_preserves_non_origin_envelope_center() -> None:
    """
    Inner-envelope scaling is centered on the actual registered envelope,
    not on coordinate-system origin.

    This preserves registration for envelopes whose bounds do not begin
    at zero.
    """

    geometry = create_outer_ridge_geometry(
        envelope_width=40.0,
        envelope_height=30.0,
        artwork_size=40.0,
        outer_ridge_width=2.0,
        envelope_min_x=20.0,
        envelope_min_y=10.0,
    )

    transform = geometry.inner_transform

    assert transform.scale_x == pytest.approx(0.9)
    assert transform.scale_y == pytest.approx(0.9)

    # Original center = (40, 25).
    # Scaling about that center maps:
    #
    # x' = 40 + 0.9 * (x - 40)
    # y' = 25 + 0.9 * (y - 25)
    #
    # or equivalently:
    #
    # x' = 0.9*x + 4.0
    # y' = 0.9*y + 2.5

    assert transform.translate_x == pytest.approx(4.0)
    assert transform.translate_y == pytest.approx(2.5)


def test_outer_ridge_inner_transform_maps_outer_bounds_to_inner_bounds() -> None:
    """
    Applying the inner transform to the outer envelope bounds produces
    the centered uniformly scaled inner bounds.
    """

    geometry = create_outer_ridge_geometry(
        envelope_width=40.0,
        envelope_height=30.0,
        artwork_size=40.0,
        outer_ridge_width=2.0,
        envelope_min_x=20.0,
        envelope_min_y=10.0,
    )

    transform = geometry.inner_transform

    min_x = transform.scale_x * 20.0 + transform.translate_x
    max_x = transform.scale_x * 60.0 + transform.translate_x
    min_y = transform.scale_y * 10.0 + transform.translate_y
    max_y = transform.scale_y * 40.0 + transform.translate_y

    assert min_x == pytest.approx(22.0)
    assert max_x == pytest.approx(58.0)
    assert min_y == pytest.approx(11.5)
    assert max_y == pytest.approx(38.5)
