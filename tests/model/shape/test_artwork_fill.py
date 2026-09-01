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


# =========================================================
# Registered Artwork envelope forms
# =========================================================


def test_artwork_fill_region_transforms_circular_artwork_envelope(
    tmp_path: Path,
) -> None:
    """
    A circular authoritative Artwork envelope remains circular after placement.

    Artwork-fill subtraction applies the same common registered Artwork
    transform used for incorporated Artwork rather than replacing the
    producer-published envelope with rectangular bounds.
    """

    envelope = tmp_path / "envelope.svg"

    envelope.write_text(
        (
            '<svg xmlns="http://www.w3.org/2000/svg" '
            'viewBox="0 0 100 100">'
            '<circle cx="40" cy="50" r="20"/>'
            "</svg>"
        ),
        encoding="utf-8",
    )

    artwork = compose.RegisteredArtwork(
        registered_extent=compose.RegisteredExtent(
            width=100.0,
            height=100.0,
        ),
        envelope=envelope,
        components=(),
    )

    transform = compose.RegisteredArtworkTransform(
        scale=0.01,
        width=0.4,
        height=0.4,
        translate_x=-0.4,
        translate_y=-0.5,
    )

    fill = compose.registered_artwork_fill_region(
        _circle_interior(),
        artwork,
        transform=transform,
    )

    assert fill.inner_boundary.tag == compose.SVG_CIRCLE

    assert float(
        fill.inner_boundary.get(
            "cx",
            "nan",
        )
    ) == pytest.approx(
        0.0,
    )

    assert float(
        fill.inner_boundary.get(
            "cy",
            "nan",
        )
    ) == pytest.approx(
        0.0,
    )

    assert float(
        fill.inner_boundary.get(
            "r",
            "nan",
        )
    ) == pytest.approx(
        0.2,
    )


def test_artwork_fill_region_transforms_polygon_artwork_envelope(
    tmp_path: Path,
) -> None:
    """
    A polygon authoritative Artwork envelope retains its registered geometry.

    Every polygon vertex receives the common registered Artwork transform.
    Shape does not replace the envelope with its rectangular occupied bounds.
    """

    envelope = tmp_path / "envelope.svg"

    envelope.write_text(
        (
            '<svg xmlns="http://www.w3.org/2000/svg" '
            'viewBox="0 0 100 100">'
            '<polygon points="20,30 60,30 70,50 60,70 20,70 10,50"/>'
            "</svg>"
        ),
        encoding="utf-8",
    )

    artwork = compose.RegisteredArtwork(
        registered_extent=compose.RegisteredExtent(
            width=100.0,
            height=100.0,
        ),
        envelope=envelope,
        components=(),
    )

    transform = compose.RegisteredArtworkTransform(
        scale=0.01,
        width=0.6,
        height=0.4,
        translate_x=-0.4,
        translate_y=-0.5,
    )

    fill = compose.registered_artwork_fill_region(
        _circle_interior(),
        artwork,
        transform=transform,
    )

    assert fill.inner_boundary.tag == compose.SVG_POLYGON

    points = tuple(
        tuple(
            float(coordinate)
            for coordinate in point.split(
                ",",
            )
        )
        for point in fill.inner_boundary.get(
            "points",
            "",
        ).split()
    )

    expected_points = (
        (-0.2, -0.2),
        (0.2, -0.2),
        (0.3, 0.0),
        (0.2, 0.2),
        (-0.2, 0.2),
        (-0.3, 0.0),
    )

    assert len(points) == len(expected_points)

    for point, expected_point in zip(
        points,
        expected_points,
        strict=True,
    ):
        assert point == pytest.approx(
            expected_point,
        )


def test_artwork_fill_region_transforms_linear_path_artwork_envelope(
    tmp_path: Path,
) -> None:
    """
    A linear-path Artwork envelope is transformed as authoritative geometry.

    Registered Artwork envelopes produced as absolute move/line paths retain
    their path representation and receive the same common transform as the
    incorporated Artwork.
    """

    envelope = tmp_path / "envelope.svg"

    envelope.write_text(
        (
            '<svg xmlns="http://www.w3.org/2000/svg" '
            'viewBox="0 0 100 100">'
            '<path d="M 20 30 L 60 30 L 60 70 L 20 70 Z"/>'
            "</svg>"
        ),
        encoding="utf-8",
    )

    artwork = compose.RegisteredArtwork(
        registered_extent=compose.RegisteredExtent(
            width=100.0,
            height=100.0,
        ),
        envelope=envelope,
        components=(),
    )

    transform = compose.RegisteredArtworkTransform(
        scale=0.01,
        width=0.4,
        height=0.4,
        translate_x=-0.4,
        translate_y=-0.5,
    )

    fill = compose.registered_artwork_fill_region(
        _circle_interior(),
        artwork,
        transform=transform,
    )

    assert fill.inner_boundary.tag == compose.SVG_PATH

    assert fill.inner_boundary.get(
        "d",
    ) == (
        "M -0.2 -0.2 "
        "L 0.19999999999999996 -0.2 "
        "L 0.19999999999999996 0.20000000000000007 "
        "L -0.2 0.20000000000000007 Z"
    )


def test_artwork_fill_region_applies_registered_group_translation_before_artwork_transform(
    tmp_path: Path,
) -> None:
    """
    Registered envelope transforms are preserved before Artwork placement.

    A producer-published group translation participates in the authoritative
    envelope geometry before Shape applies the common registered Artwork
    placement transform.
    """

    envelope = tmp_path / "envelope.svg"

    envelope.write_text(
        (
            '<svg xmlns="http://www.w3.org/2000/svg" '
            'viewBox="0 0 100 100">'
            '<g transform="translate(20 30)">'
            '<rect x="5" y="10" width="40" height="20"/>'
            "</g>"
            "</svg>"
        ),
        encoding="utf-8",
    )

    artwork = compose.RegisteredArtwork(
        registered_extent=compose.RegisteredExtent(
            width=100.0,
            height=100.0,
        ),
        envelope=envelope,
        components=(),
    )

    transform = compose.RegisteredArtworkTransform(
        scale=0.01,
        width=0.4,
        height=0.2,
        translate_x=-0.45,
        translate_y=-0.5,
    )

    fill = compose.registered_artwork_fill_region(
        _circle_interior(),
        artwork,
        transform=transform,
    )

    assert fill.inner_boundary.tag == compose.SVG_GROUP

    assert (
        fill.inner_boundary.get(
            "transform",
        )
        is None
    )

    children = tuple(
        fill.inner_boundary,
    )

    assert len(children) == 1

    transformed_rect = children[0]

    assert transformed_rect.tag == compose.SVG_RECT

    #
    # Producer geometry:
    #
    #     rect x = 5, y = 10, width = 40, height = 20
    #
    # Producer group translation:
    #
    #     translate(20, 30)
    #
    # Effective source geometry:
    #
    #     x = 25, y = 40, width = 40, height = 20
    #
    # Shape Artwork transform:
    #
    #     scale = 0.01
    #     translate = (-0.45, -0.5)
    #
    # Result:
    #
    #     x = -0.20
    #     y = -0.10
    #     width = 0.40
    #     height = 0.20
    #
    assert float(
        transformed_rect.get(
            "x",
            "nan",
        )
    ) == pytest.approx(
        -0.20,
    )

    assert float(
        transformed_rect.get(
            "y",
            "nan",
        )
    ) == pytest.approx(
        -0.10,
    )

    assert float(
        transformed_rect.get(
            "width",
            "nan",
        )
    ) == pytest.approx(
        0.40,
    )

    assert float(
        transformed_rect.get(
            "height",
            "nan",
        )
    ) == pytest.approx(
        0.20,
    )


# =========================================================
# Artwork-fill composition policy
# =========================================================


def test_artwork_fill_is_absent_when_fill_color_is_none(
    tmp_path: Path,
) -> None:
    """
    The default none fill policy produces no registered Artwork-fill geometry.

    Fill existence is controlled by Shape's fill policy rather than by the
    mere presence of incorporated Artwork.
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
        width=0.60,
        height=0.50,
        translate_x=-0.40,
        translate_y=-0.40,
    )

    fill = compose.registered_artwork_fill(
        interior,
        artwork,
        transform=transform,
        fill_color="none",
    )

    assert fill is None


def test_artwork_fill_is_present_when_fill_color_is_configured(
    tmp_path: Path,
) -> None:
    """
    A configured fill color enables registered Artwork-fill geometry.

    The resulting region is the registered Shape interior minus the
    transformed authoritative Artwork envelope.
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
        width=0.60,
        height=0.50,
        translate_x=-0.40,
        translate_y=-0.40,
    )

    fill = compose.registered_artwork_fill(
        interior,
        artwork,
        transform=transform,
        fill_color="white",
    )

    assert fill is not None

    assert fill.outer_boundary.tag == compose.SVG_CIRCLE

    assert float(
        fill.outer_boundary.get(
            "r",
            "nan",
        )
    ) == pytest.approx(
        0.5,
    )

    assert fill.inner_boundary.tag == compose.SVG_RECT

    assert float(
        fill.inner_boundary.get(
            "x",
            "nan",
        )
    ) == pytest.approx(
        -0.30,
    )

    assert float(
        fill.inner_boundary.get(
            "y",
            "nan",
        )
    ) == pytest.approx(
        -0.25,
    )

    assert float(
        fill.inner_boundary.get(
            "width",
            "nan",
        )
    ) == pytest.approx(
        0.60,
    )

    assert float(
        fill.inner_boundary.get(
            "height",
            "nan",
        )
    ) == pytest.approx(
        0.50,
    )


def test_artwork_fill_color_does_not_change_registered_fill_geometry(
    tmp_path: Path,
) -> None:
    """
    Semantic fill color does not participate in registered fill geometry.

    Different enabled colors produce the same registered Shape region for the
    same Shape interior, Artwork envelope, and common Artwork transform.
    """

    envelope = tmp_path / "envelope.svg"

    _write_rectangular_artwork_envelope(
        envelope,
    )

    artwork = _registered_artwork(
        envelope,
    )

    transform = compose.RegisteredArtworkTransform(
        scale=0.05,
        width=0.60,
        height=0.50,
        translate_x=-0.40,
        translate_y=-0.40,
    )

    white_fill = compose.registered_artwork_fill(
        _circle_interior(),
        artwork,
        transform=transform,
        fill_color="white",
    )

    black_fill = compose.registered_artwork_fill(
        _circle_interior(),
        artwork,
        transform=transform,
        fill_color="black",
    )

    assert white_fill is not None
    assert black_fill is not None

    assert ET.tostring(
        white_fill.outer_boundary,
    ) == ET.tostring(
        black_fill.outer_boundary,
    )

    assert ET.tostring(
        white_fill.inner_boundary,
    ) == ET.tostring(
        black_fill.inner_boundary,
    )


def test_artwork_fill_region_is_independent_of_ridge_style(
    tmp_path: Path,
) -> None:
    """
    Ridge partitioning style does not alter registered Artwork-fill geometry.

    Integrated and separate ridges having the same registered inner boundary
    provide the same Shape interior for Artwork fill.
    """

    envelope = tmp_path / "envelope.svg"

    _write_rectangular_artwork_envelope(
        envelope,
    )

    artwork = _registered_artwork(
        envelope,
    )

    transform = compose.RegisteredArtworkTransform(
        scale=0.04,
        width=0.48,
        height=0.40,
        translate_x=-0.32,
        translate_y=-0.32,
    )

    #
    # Ridge style determines physical component partitioning, not the
    # registered interior boundary. With the same ridge width, integrated and
    # separate styles therefore provide the same registered interior.
    #
    integrated_interior = ET.Element(
        compose.SVG_CIRCLE,
        {
            "id": "ridge-inner-boundary",
            "cx": "0.0",
            "cy": "0.0",
            "r": "0.45",
        },
    )

    separate_interior = ET.Element(
        compose.SVG_CIRCLE,
        {
            "id": "ridge-inner-boundary",
            "cx": "0.0",
            "cy": "0.0",
            "r": "0.45",
        },
    )

    integrated_fill = compose.registered_artwork_fill(
        integrated_interior,
        artwork,
        transform=transform,
        fill_color="white",
    )

    separate_fill = compose.registered_artwork_fill(
        separate_interior,
        artwork,
        transform=transform,
        fill_color="white",
    )

    assert integrated_fill is not None
    assert separate_fill is not None

    assert ET.tostring(
        integrated_fill.outer_boundary,
    ) == ET.tostring(
        separate_fill.outer_boundary,
    )

    assert ET.tostring(
        integrated_fill.inner_boundary,
    ) == ET.tostring(
        separate_fill.inner_boundary,
    )
