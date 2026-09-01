"""
Tests for Shape Artwork-fill registered geometry.
"""
# File: tests/model/shape/test_artwork_fill.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from lowkey_artifact_builder.model.models.shape.stages import compose

# =========================================================
# Helpers
# =========================================================


def _write_rectangular_artwork_envelope(
    path: Path,
    *,
    x: float = 2.0,
    y: float = 3.0,
    width: float = 12.0,
    height: float = 10.0,
) -> None:
    """
    Write a representative authoritative registered Artwork envelope.
    """

    path.write_text(
        (
            '<svg xmlns="http://www.w3.org/2000/svg" '
            'viewBox="0 0 16 16">'
            f'<rect x="{x}" y="{y}" '
            f'width="{width}" height="{height}"/>'
            "</svg>"
        ),
        encoding="utf-8",
    )


def _registered_artwork(
    envelope: Path,
) -> compose.RegisteredArtwork:
    """
    Create representative registered Artwork with an authoritative envelope.

    Component geometry is intentionally absent. Artwork-fill geometry depends
    on the producer-published envelope rather than individual color components.
    """

    return compose.RegisteredArtwork(
        registered_extent=compose.RegisteredExtent(
            width=16.0,
            height=16.0,
        ),
        envelope=envelope,
        components=(),
    )


def _circle_interior(
    *,
    radius: float = 0.5,
) -> ET.Element:
    """
    Create a circular interior in canonical registered Shape coordinates.
    """

    return ET.Element(
        compose.SVG_CIRCLE,
        {
            "cx": "0.0",
            "cy": "0.0",
            "r": str(radius),
        },
    )


# =========================================================
# Registered Artwork fill geometry
# =========================================================


def test_artwork_fill_region_is_shape_interior_minus_transformed_artwork_envelope(
    tmp_path: Path,
) -> None:
    """
    Artwork fill occupies Shape interior not occupied by registered Artwork.

    The authoritative Artwork envelope is transformed into registered Shape
    coordinates using the same placement transform as the incorporated
    Artwork. That transformed envelope becomes the inner boundary of the fill
    while the Shape interior remains its outer boundary.
    """

    envelope = tmp_path / "envelope.svg"

    _write_rectangular_artwork_envelope(
        envelope,
    )

    artwork = _registered_artwork(
        envelope,
    )

    interior = _circle_interior()

    transform = compose.RegisteredArtworkTransform(
        scale=0.05,
        width=0.6,
        height=0.5,
        translate_x=-0.4,
        translate_y=-0.4,
    )

    fill = compose.registered_artwork_fill_region(
        interior,
        artwork,
        transform=transform,
    )

    assert fill.outer_boundary.tag == compose.SVG_CIRCLE
    assert float(fill.outer_boundary.get("cx", "nan")) == pytest.approx(
        0.0,
    )
    assert float(fill.outer_boundary.get("cy", "nan")) == pytest.approx(
        0.0,
    )
    assert float(fill.outer_boundary.get("r", "nan")) == pytest.approx(
        0.5,
    )

    assert fill.inner_boundary.tag == compose.SVG_RECT

    #
    # Authoritative Artwork envelope:
    #
    #     x = 2..14
    #     y = 3..13
    #
    # Transform:
    #
    #     x' = x * 0.05 - 0.4
    #     y' = y * 0.05 - 0.4
    #
    # Therefore the transformed occupied region is:
    #
    #     x = -0.30 .. 0.30
    #     y = -0.25 .. 0.25
    #
    assert float(fill.inner_boundary.get("x", "nan")) == pytest.approx(
        -0.30,
    )
    assert float(fill.inner_boundary.get("y", "nan")) == pytest.approx(
        -0.25,
    )
    assert float(fill.inner_boundary.get("width", "nan")) == pytest.approx(
        0.60,
    )
    assert float(fill.inner_boundary.get("height", "nan")) == pytest.approx(
        0.50,
    )


def test_artwork_fill_region_uses_authoritative_artwork_envelope(
    tmp_path: Path,
) -> None:
    """
    Artwork fill subtraction is defined by the authoritative Artwork envelope.

    Shape must not infer the fill boundary from individual Artwork component
    bounds. Components remain registered payloads whose separate geometry does
    not redefine the producer-published occupied envelope.
    """

    envelope = tmp_path / "envelope.svg"
    left_component = tmp_path / "left.svg"
    right_component = tmp_path / "right.svg"

    _write_rectangular_artwork_envelope(
        envelope,
    )

    #
    # Deliberately make the component occupancies substantially smaller than
    # the authoritative envelope. If Shape were to infer occupancy from these
    # components, the resulting fill hole would differ from the envelope.
    #
    left_component.write_text(
        (
            '<svg xmlns="http://www.w3.org/2000/svg" '
            'viewBox="0 0 16 16">'
            '<rect x="4" y="6" width="2" height="2"/>'
            "</svg>"
        ),
        encoding="utf-8",
    )

    right_component.write_text(
        (
            '<svg xmlns="http://www.w3.org/2000/svg" '
            'viewBox="0 0 16 16">'
            '<rect x="10" y="8" width="2" height="2"/>'
            "</svg>"
        ),
        encoding="utf-8",
    )

    artwork = compose.RegisteredArtwork(
        registered_extent=compose.RegisteredExtent(
            width=16.0,
            height=16.0,
        ),
        envelope=envelope,
        components=(
            compose.RegisteredArtworkComponent(
                index=1,
                path=left_component,
                name="left",
                color={
                    "red": 255,
                    "green": 255,
                    "blue": 255,
                },
            ),
            compose.RegisteredArtworkComponent(
                index=2,
                path=right_component,
                name="right",
                color={
                    "red": 0,
                    "green": 0,
                    "blue": 0,
                },
            ),
        ),
    )

    transform = compose.RegisteredArtworkTransform(
        scale=0.05,
        width=0.6,
        height=0.5,
        translate_x=-0.4,
        translate_y=-0.4,
    )

    fill = compose.registered_artwork_fill_region(
        _circle_interior(),
        artwork,
        transform=transform,
    )

    #
    # These dimensions come from envelope.svg:
    #
    #     12 x 10 registered Artwork units
    #
    # rather than either component's 2 x 2 occupied region.
    #
    assert fill.inner_boundary.tag == compose.SVG_RECT

    assert float(fill.inner_boundary.get("x", "nan")) == pytest.approx(
        -0.30,
    )
    assert float(fill.inner_boundary.get("y", "nan")) == pytest.approx(
        -0.25,
    )
    assert float(fill.inner_boundary.get("width", "nan")) == pytest.approx(
        0.60,
    )
    assert float(fill.inner_boundary.get("height", "nan")) == pytest.approx(
        0.50,
    )


def test_artwork_fill_region_remains_in_registered_shape_space(
    tmp_path: Path,
) -> None:
    """
    Artwork fill remains registered geometry until physical dimensionalization.

    Composition establishes the spatial relationship between Shape interior
    and incorporated Artwork without applying shape_size or any physical Z
    dimensions. The fill therefore remains in canonical registered Shape
    coordinates.
    """

    envelope = tmp_path / "envelope.svg"

    _write_rectangular_artwork_envelope(
        envelope,
    )

    artwork = _registered_artwork(
        envelope,
    )

    interior = _circle_interior(
        radius=0.45,
    )

    transform = compose.RegisteredArtworkTransform(
        scale=0.04,
        width=0.48,
        height=0.40,
        translate_x=-0.32,
        translate_y=-0.32,
    )

    fill = compose.registered_artwork_fill_region(
        interior,
        artwork,
        transform=transform,
    )

    #
    # The outer boundary remains the registered Shape interior. It has not
    # become a physical radius such as 45 mm.
    #
    assert fill.outer_boundary.tag == compose.SVG_CIRCLE
    assert float(fill.outer_boundary.get("r", "nan")) == pytest.approx(
        0.45,
    )

    #
    # The Artwork hole is likewise expressed in registered Shape coordinates.
    #
    # Envelope x = 2..14, y = 3..13 under:
    #
    #     scale = 0.04
    #     translation = (-0.32, -0.32)
    #
    # becomes:
    #
    #     x = -0.24 .. 0.24
    #     y = -0.20 .. 0.20
    #
    assert fill.inner_boundary.tag == compose.SVG_RECT

    assert float(fill.inner_boundary.get("x", "nan")) == pytest.approx(
        -0.24,
    )
    assert float(fill.inner_boundary.get("y", "nan")) == pytest.approx(
        -0.20,
    )
    assert float(fill.inner_boundary.get("width", "nan")) == pytest.approx(
        0.48,
    )
    assert float(fill.inner_boundary.get("height", "nan")) == pytest.approx(
        0.40,
    )
