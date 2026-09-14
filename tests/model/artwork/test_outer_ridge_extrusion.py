"""
Tests for Artwork Outer Ridge extrusion integration.

Outer Ridge reserves physical space inside artwork_size by uniformly
scaling Artwork proper while preserving its existing center and
registration.
"""
# File: tests/model/artwork/test_outer_ridge_extrusion.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path

from lowkey_artifact_builder.model.models.artwork.stages import extrude


def _write_svg(
    path: Path,
) -> None:
    path.write_text(
        """
<svg xmlns="http://www.w3.org/2000/svg"
     width="100"
     height="100"
     viewBox="0 0 100 100">
  <rect x="20" y="10" width="40" height="30"/>
</svg>
""".strip(),
        encoding="utf-8",
    )


def test_outer_ridge_scales_artwork_proper_inside_full_artwork_size(
    tmp_path: Path,
) -> None:
    """
    Participating Outer Ridge uniformly scales Artwork proper inside the
    ordinary standalone artwork_size.

    A 2 mm ridge on 40 mm Artwork leaves a 36 mm size-controlled Artwork
    extent, giving a uniform scale factor of 0.9.
    """

    svg = tmp_path / "layer.svg"
    _write_svg(svg)

    source = extrude._build_scad(
        svg,
        registered_extent=100,
        envelope_bounds=(
            20.0,
            10.0,
            60.0,
            40.0,
        ),
        artwork_size=40.0,
        artwork_raise=1.0,
        artwork_scale=0.9,
    )

    assert "artwork_scale = 0.9;" in source
    assert "artwork_size * artwork_scale / envelope_extent" in source


def test_disabled_outer_ridge_preserves_ordinary_artwork_dimensionalization(
    tmp_path: Path,
) -> None:
    """
    A scale of one preserves the existing standalone Artwork
    dimensionalization exactly.
    """

    svg = tmp_path / "layer.svg"
    _write_svg(svg)

    source = extrude._build_scad(
        svg,
        registered_extent=100,
        envelope_bounds=(
            20.0,
            10.0,
            60.0,
            40.0,
        ),
        artwork_size=40.0,
        artwork_raise=1.0,
        artwork_scale=1.0,
    )

    assert "artwork_scale = 1;" in source
    assert "artwork_size * artwork_scale / envelope_extent" in source


def test_outer_ridge_artwork_scaling_preserves_existing_centering(
    tmp_path: Path,
) -> None:
    """
    Outer Ridge scaling changes only the common physical scale.

    Registered Artwork continues to be centered from the occupied envelope,
    so every color layer retains the same center and registration.
    """

    svg = tmp_path / "layer.svg"
    _write_svg(svg)

    source = extrude._build_scad(
        svg,
        registered_extent=100,
        envelope_bounds=(
            20.0,
            10.0,
            60.0,
            40.0,
        ),
        artwork_size=40.0,
        artwork_raise=1.0,
        artwork_scale=0.9,
    )

    assert "envelope_center_x = 40;" in source

    # SVG center Y is 25. OpenSCAD reverses the registered Y axis:
    # 100 - 25 = 75.
    assert "envelope_openscad_center_y = 75;" in source

    assert "-envelope_center_x" in source
    assert "-envelope_openscad_center_y" in source


def test_build_scad_uses_neutral_artwork_scale_without_outer_ridge(
    tmp_path: Path,
) -> None:
    """
    Ordinary Artwork dimensionalization uses a neutral Artwork scale.

    The occupied envelope continues to be fitted to artwork_size when no
    Outer Ridge space has been reserved.
    """

    svg = tmp_path / "layer.svg"

    svg.write_text(
        """
        <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 20 20"
        >
            <rect
                x="0"
                y="0"
                width="20"
                height="20"
            />
        </svg>
        """,
        encoding="utf-8",
    )

    source = extrude._build_scad(
        svg,
        registered_extent=20,
        envelope_bounds=(
            0.0,
            0.0,
            20.0,
            20.0,
        ),
        artwork_size=150.0,
        artwork_raise=1.0,
    )

    assert "registered_extent = 20;" in source
    assert "envelope_width = 20;" in source
    assert "envelope_height = 20;" in source
    assert "envelope_extent = 20;" in source
    assert "envelope_center_x = 10;" in source
    assert "envelope_openscad_center_y = 10;" in source

    assert "artwork_size = 150;" in source
    assert "artwork_scale = 1;" in source

    assert "artwork_size * artwork_scale / envelope_extent" in source

    assert "dpi = 25.4" in source


def test_build_scad_artwork_scale_is_independent_of_z_raise(
    tmp_path: Path,
) -> None:
    """
    Outer-Ridge-aware X/Y scaling remains independent of Artwork Z height.

    artwork_size and artwork_scale dimensionalize the registered coordinate
    system in X/Y while artwork_raise independently supplies extrusion height.
    """

    svg = tmp_path / "layer.svg"

    svg.write_text(
        "<svg/>",
        encoding="utf-8",
    )

    low = extrude._build_scad(
        svg,
        registered_extent=25,
        envelope_bounds=(
            0.0,
            0.0,
            25.0,
            25.0,
        ),
        artwork_size=100.0,
        artwork_raise=0.5,
        artwork_scale=0.9,
    )

    high = extrude._build_scad(
        svg,
        registered_extent=25,
        envelope_bounds=(
            0.0,
            0.0,
            25.0,
            25.0,
        ),
        artwork_size=100.0,
        artwork_raise=2.0,
        artwork_scale=0.9,
    )

    assert "artwork_scale = 0.9;" in low
    assert "artwork_scale = 0.9;" in high

    assert "artwork_size * artwork_scale / envelope_extent" in low
    assert "artwork_size * artwork_scale / envelope_extent" in high

    assert "artwork_raise = 0.5;" in low
    assert "artwork_raise = 2;" in high

    assert "height = artwork_raise" in low
    assert "height = artwork_raise" in high
