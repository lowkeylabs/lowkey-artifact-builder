"""
Tests for Shape Artwork-fill registered geometry.
"""
# File: tests/model/shape/test_artwork_fill.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import Mock

import pytest

from lowkey_artifact_builder.engine import StageContext
from lowkey_artifact_builder.model.models.shape.stages import compose, extrude

# =========================================================
# Helpers
# =========================================================


def _write_registered_structure(
    path: Path,
) -> None:
    """
    Write representative registered circular Shape structure.
    """

    path.write_text(
        (
            '<svg xmlns="http://www.w3.org/2000/svg" '
            'viewBox="-0.5 -0.5 1.0 1.0">'
            '<circle cx="0.0" cy="0.0" r="0.5"/>'
            "</svg>"
        ),
        encoding="utf-8",
    )


def _write_registered_artwork_manifest(
    path: Path,
) -> None:
    """
    Write representative registered Artwork consumed by Shape composition.
    """

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    envelope = path.parent / "envelope.svg"

    _write_rectangular_artwork_envelope(
        envelope,
    )

    component = path.parent / "white.svg"

    component.write_text(
        (
            '<svg xmlns="http://www.w3.org/2000/svg" '
            'viewBox="0 0 16 16">'
            '<rect x="2" y="3" width="12" height="10"/>'
            "</svg>"
        ),
        encoding="utf-8",
    )

    path.write_text(
        json.dumps(
            {
                "registered_extent": 16,
                "envelope": "envelope.svg",
                "products": [
                    {
                        "index": 1,
                        "path": "white.svg",
                        "artifact_color": {
                            "index": 1,
                            "rgb": {
                                "red": 250,
                                "green": 250,
                                "blue": 250,
                            },
                        },
                        "printer_color": {
                            "name": "white",
                            "rgb": {
                                "red": 255,
                                "green": 255,
                                "blue": 255,
                            },
                        },
                        "distance": 1.25,
                    },
                ],
            }
        ),
        encoding="utf-8",
    )


def _compose_context(
    *,
    structure_path: Path,
    registered_artwork_manifest: Path,
    composition_path: Path,
    manifest_path: Path,
) -> Mock:
    """
    Build a Shape Compose context containing representative Compose defaults.

    Registered Artwork-fill geometry is a composition concern independent of
    physical printer-color policy. Physical fill participation is decided by
    Extrude through shape_artwork_fill_raise, and physical fill color is
    resolved by Package.
    """

    context = Mock(spec=StageContext)

    inputs = {
        "structure.structure": structure_path,
        "artwork.vector.manifest": registered_artwork_manifest,
    }

    outputs = {
        "composition": composition_path,
        "manifest": manifest_path,
    }

    values = {
        "shape_size": 100.0,
        "shape_outer_ridge_width": 0.0,
        "shape_outer_ridge_style": "integrated",
        "shape_inner_ridge_width": 0.0,
        "shape_inner_to_outer_ridge_dist": 10.0,
        "shape_border_label_width": 1.0,
        "shape_border_label_max_glyph_height": 5.0,
        "shape_border_label_arc_degrees": 140.0,
        "shape_border_label_end_margin": 1.0,
        "shape_border_label_font_family": "DejaVu Sans",
        "shape_top_border_label_text": "",
        "shape_bottom_border_label_text": "",
        "shape_qr_payload": "",
    }

    context.input.side_effect = inputs.__getitem__
    context.output.side_effect = outputs.__getitem__
    context.resolver.side_effect = values.__getitem__

    return context


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

    Registered Artwork components preserve Artifact-color identity only.
    Physical printer-color assignment is a downstream packaging concern and
    does not participate in registered fill geometry.
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
                artifact_color_index=1,
                artifact_color={
                    "red": 250,
                    "green": 250,
                    "blue": 250,
                },
            ),
            compose.RegisteredArtworkComponent(
                index=2,
                path=right_component,
                artifact_color_index=2,
                artifact_color={
                    "red": 5,
                    "green": 5,
                    "blue": 5,
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


def test_registered_artwork_fill_exists_independent_of_physical_color(
    tmp_path: Path,
) -> None:
    """
    Registered Artwork-fill geometry is independent of physical color policy.

    Compose determines the potential registered fill region from Shape and
    registered Artwork geometry. It does not use shape_artwork_fill_color to
    decide whether that geometry exists.
    """
    structure = tmp_path / "structure.svg"
    artwork_manifest = tmp_path / "artwork" / "products.json"
    composition = tmp_path / "composition.svg"
    manifest = tmp_path / "products.json"

    _write_registered_structure(
        structure,
    )
    _write_registered_artwork_manifest(
        artwork_manifest,
    )

    context = _compose_context(
        structure_path=structure,
        registered_artwork_manifest=artwork_manifest,
        composition_path=composition,
        manifest_path=manifest,
    )

    compose.execute(
        context,
    )

    products = json.loads(
        manifest.read_text(
            encoding="utf-8",
        )
    )

    assert products["artwork_fill"] is not None

    assert all(
        call.args != ("shape_artwork_fill_color",) for call in context.resolver.call_args_list
    )


def test_registered_artwork_fill_exists_independent_of_physical_fill_raise(
    tmp_path: Path,
) -> None:
    """
    Registered Artwork-fill geometry is independent of physical fill height.

    Compose persists the potential registered fill region. Extrude later uses
    shape_artwork_fill_raise to decide whether that region participates in the
    physical Product and how high it is.
    """
    structure = tmp_path / "structure.svg"
    artwork_manifest = tmp_path / "artwork" / "products.json"
    composition = tmp_path / "composition.svg"
    manifest = tmp_path / "products.json"

    _write_registered_structure(
        structure,
    )
    _write_registered_artwork_manifest(
        artwork_manifest,
    )

    context = _compose_context(
        structure_path=structure,
        registered_artwork_manifest=artwork_manifest,
        composition_path=composition,
        manifest_path=manifest,
    )

    compose.execute(
        context,
    )

    products = json.loads(
        manifest.read_text(
            encoding="utf-8",
        )
    )

    assert products["artwork_fill"] is not None

    assert all(
        call.args != ("shape_artwork_fill_raise",) for call in context.resolver.call_args_list
    )


def test_compose_does_not_resolve_artwork_fill_physical_color(
    tmp_path: Path,
) -> None:
    """
    Compose does not resolve Artwork-fill physical color.

    shape_artwork_fill_color belongs exclusively to Package and therefore
    cannot influence registered fill geometry.
    """
    structure = tmp_path / "structure.svg"
    artwork_manifest = tmp_path / "artwork" / "products.json"
    composition = tmp_path / "composition.svg"
    manifest = tmp_path / "products.json"

    _write_registered_structure(
        structure,
    )
    _write_registered_artwork_manifest(
        artwork_manifest,
    )

    context = _compose_context(
        structure_path=structure,
        registered_artwork_manifest=artwork_manifest,
        composition_path=composition,
        manifest_path=manifest,
    )

    compose.execute(
        context,
    )

    assert all(
        call.args != ("shape_artwork_fill_color",) for call in context.resolver.call_args_list
    )

    assert composition.exists()
    assert manifest.exists()


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


# =========================================================
# Persistent Artwork-fill composition
# =========================================================


def test_compose_stage_persists_registered_artwork_fill_geometry(
    tmp_path: Path,
) -> None:
    """
    Compose persists potential registered Artwork-fill geometry.

    Physical participation is deliberately unresolved at this stage. Extrude
    decides later whether the registered fill participates using
    shape_artwork_fill_raise.
    """
    structure = tmp_path / "structure.svg"
    artwork_manifest = tmp_path / "artwork" / "products.json"
    composition = tmp_path / "composition.svg"
    manifest = tmp_path / "products.json"

    _write_registered_structure(
        structure,
    )
    _write_registered_artwork_manifest(
        artwork_manifest,
    )

    context = _compose_context(
        structure_path=structure,
        registered_artwork_manifest=artwork_manifest,
        composition_path=composition,
        manifest_path=manifest,
    )

    compose.execute(
        context,
    )

    products = json.loads(
        manifest.read_text(
            encoding="utf-8",
        )
    )

    fill = products["artwork_fill"]

    assert fill is not None

    assert set(fill) == {
        "outer_boundary",
        "inner_boundary",
    }

    assert fill["outer_boundary"]["type"] == "circle"
    assert fill["inner_boundary"]["type"] == "rect"


def test_compose_stage_persists_artwork_fill_without_physical_policy(
    tmp_path: Path,
) -> None:
    """
    Persistent registered Artwork-fill state contains geometry rather than
    physical participation or printer-color policy.
    """
    structure = tmp_path / "structure.svg"
    artwork_manifest = tmp_path / "artwork" / "products.json"
    composition = tmp_path / "composition.svg"
    manifest = tmp_path / "products.json"

    _write_registered_structure(
        structure,
    )
    _write_registered_artwork_manifest(
        artwork_manifest,
    )

    context = _compose_context(
        structure_path=structure,
        registered_artwork_manifest=artwork_manifest,
        composition_path=composition,
        manifest_path=manifest,
    )

    compose.execute(
        context,
    )

    products = json.loads(
        manifest.read_text(
            encoding="utf-8",
        )
    )

    fill = products["artwork_fill"]

    assert fill is not None

    serialized = json.dumps(
        fill,
    )

    assert "shape_artwork_fill_color" not in serialized
    assert "shape_artwork_fill_raise" not in serialized
    assert "printer_color" not in serialized
    assert "printer_head" not in serialized


def test_persistent_artwork_fill_remains_registered_and_self_contained(
    tmp_path: Path,
) -> None:
    """
    Persistent Artwork fill contains the registered geometry extrusion needs.

    Downstream dimensionalization must not need the producer's Artwork envelope
    to reconstruct the fill region. No physical X/Y or Z dimensions are
    introduced by composition.
    """
    structure = tmp_path / "structure.svg"
    artwork_manifest = tmp_path / "artwork" / "products.json"
    composition = tmp_path / "composition.svg"
    manifest = tmp_path / "products.json"

    _write_registered_structure(
        structure,
    )
    _write_registered_artwork_manifest(
        artwork_manifest,
    )

    context = _compose_context(
        structure_path=structure,
        registered_artwork_manifest=artwork_manifest,
        composition_path=composition,
        manifest_path=manifest,
    )

    compose.execute(
        context,
    )

    products = json.loads(
        manifest.read_text(
            encoding="utf-8",
        )
    )

    fill = products["artwork_fill"]

    assert fill is not None

    assert set(fill) == {
        "outer_boundary",
        "inner_boundary",
    }

    serialized = json.dumps(
        fill,
    )

    assert "shape_size" not in serialized
    assert "shape_base_raise" not in serialized
    assert "shape_artwork_raise" not in serialized
    assert "shape_artwork_fill_raise" not in serialized
    assert '"z"' not in serialized.lower()


# =========================================================
# Physical Artwork-fill dimensionalization
# =========================================================


def _write_physical_fill_composition(
    composition: Path,
) -> None:
    """
    Write representative registered Shape geometry for fill extrusion.
    """

    composition.write_text(
        (
            '<svg xmlns="http://www.w3.org/2000/svg" '
            'viewBox="-0.5 -0.5 1 1">'
            '<circle id="shape-boundary" cx="0" cy="0" r="0.5"/>'
            '<circle id="ridge-inner-boundary" cx="0" cy="0" r="0.45"/>'
            "</svg>"
        ),
        encoding="utf-8",
    )


def _write_physical_fill_artwork_component(
    path: Path,
) -> None:
    """
    Write one representative registered Artwork component.
    """

    path.write_text(
        (
            '<svg xmlns="http://www.w3.org/2000/svg" '
            'viewBox="0 0 16 16">'
            '<rect x="2" y="3" width="12" height="10"/>'
            "</svg>"
        ),
        encoding="utf-8",
    )


def _write_physical_fill_manifest(
    path: Path,
    *,
    artwork_fill: dict[str, object] | None,
) -> None:
    """
    Write a persistent Shape composition manifest for physical fill tests.

    Incorporated Artwork is retained so the tests exercise the actual
    Artwork-fill case rather than a fill detached from Artwork.
    """

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    artwork_component = path.parent / "white.svg"

    _write_physical_fill_artwork_component(
        artwork_component,
    )

    path.write_text(
        json.dumps(
            {
                "composition": "composition.svg",
                "artwork": {
                    "registered_extent": {
                        "width": 16.0,
                        "height": 16.0,
                    },
                    "transform": {
                        "scale": 0.05,
                        "translate_x": -0.4,
                        "translate_y": -0.4,
                    },
                    "components": [
                        {
                            "index": 1,
                            "path": artwork_component.name,
                            "artifact_color": {
                                "index": 1,
                                "rgb": {
                                    "red": 250,
                                    "green": 250,
                                    "blue": 250,
                                },
                            },
                            "printer_color": {
                                "name": "white",
                                "rgb": {
                                    "red": 255,
                                    "green": 255,
                                    "blue": 255,
                                },
                            },
                            "distance": 1.25,
                        },
                    ],
                },
                "artwork_fill": artwork_fill,
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def _physical_fill_region() -> dict[str, object]:
    """
    Return representative persisted registered Artwork-fill geometry.
    """

    return {
        "outer_boundary": {
            "type": "circle",
            "cx": 0.0,
            "cy": 0.0,
            "r": 0.45,
        },
        "inner_boundary": {
            "type": "rect",
            "x": -0.30,
            "y": -0.25,
            "width": 0.60,
            "height": 0.50,
        },
    }


def _physical_fill_extrude_context(
    *,
    composition: Path,
    composition_manifest: Path,
    output_manifest: Path,
    artwork_fill_raise: float = 0.6,
) -> Mock:
    """
    Configure Shape extrusion for Artwork-fill dimensionalization tests.

    Parameters material to Artwork-fill behavior are explicit.

    Unrelated optional Shape Extrude features resolve to their ordinary
    nonparticipating defaults so adding another optional Feature does not
    require Artwork-fill tests to enumerate that Feature's parameter contract.
    """

    context = Mock(
        spec=StageContext,
    )

    inputs = {
        "compose.composition": composition,
        "compose.manifest": composition_manifest,
    }

    outputs = {
        "manifest": output_manifest,
    }

    values = {
        "shape_size": 100.0,
        "shape_base_raise": 2.0,
        "shape_raise_style": "raised",
        "shape_outer_ridge_raise": 1.0,
        "shape_outer_ridge_style": "integrated",
        "shape_artwork_raise": 0.6,
        "shape_artwork_fill_raise": artwork_fill_raise,
    }

    nonparticipating_defaults = {
        "shape_hole_diameter": 0.0,
        "shape_loop_inner_diameter": 0.0,
    }

    def resolver(
        name: str,
    ) -> object:
        if name in values:
            return values[name]

        if name in nonparticipating_defaults:
            return nonparticipating_defaults[name]

        raise KeyError(
            name,
        )

    context.input.side_effect = inputs.__getitem__
    context.output.side_effect = outputs.__getitem__
    context.resolver.side_effect = resolver

    return context


def test_extrude_produces_no_artwork_fill_component_when_fill_raise_is_zero(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Zero Artwork-fill raise disables the physical fill component.

    Registered fill geometry may exist in the persistent composition, but
    physical participation belongs to extrusion and is controlled by
    shape_artwork_fill_raise rather than by physical color policy.
    """

    composition = tmp_path / "composition.svg"
    composition_manifest = tmp_path / "composition-products.json"
    output_manifest = tmp_path / "extrude" / "products.json"

    _write_physical_fill_composition(
        composition,
    )
    _write_physical_fill_manifest(
        composition_manifest,
        artwork_fill=_physical_fill_region(),
    )

    rendered_paths: list[Path] = []

    def fake_render_stl_source(
        source: str,
        output: Path,
    ) -> None:
        del source

        output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        output.write_text(
            "solid test\nendsolid test\n",
            encoding="utf-8",
        )

        rendered_paths.append(
            output,
        )

    monkeypatch.setattr(
        extrude,
        "render_stl_source",
        fake_render_stl_source,
    )

    context = _physical_fill_extrude_context(
        composition=composition,
        composition_manifest=composition_manifest,
        output_manifest=output_manifest,
        artwork_fill_raise=0.0,
    )

    extrude.execute(
        context,
    )

    products = json.loads(
        output_manifest.read_text(
            encoding="utf-8",
        )
    )

    component_names = {component["name"] for component in products["components"]}

    assert "base" in component_names
    assert "artwork-1" in component_names
    assert "artwork-fill" not in component_names

    assert all(path.name != "artwork-fill.stl" for path in rendered_paths)


def test_extrude_produces_artwork_fill_component_when_fill_raise_is_positive(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Positive Artwork-fill raise enables the physical fill component.

    Physical participation is independent of physical color selection.
    """

    composition = tmp_path / "composition.svg"
    composition_manifest = tmp_path / "composition-products.json"
    output_manifest = tmp_path / "extrude" / "products.json"

    _write_physical_fill_composition(
        composition,
    )
    _write_physical_fill_manifest(
        composition_manifest,
        artwork_fill=_physical_fill_region(),
    )

    rendered_paths: list[Path] = []

    def fake_render_stl_source(
        source: str,
        output: Path,
    ) -> None:
        del source

        output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        output.write_text(
            "solid test\nendsolid test\n",
            encoding="utf-8",
        )

        rendered_paths.append(
            output,
        )

    monkeypatch.setattr(
        extrude,
        "render_stl_source",
        fake_render_stl_source,
    )

    context = _physical_fill_extrude_context(
        composition=composition,
        composition_manifest=composition_manifest,
        output_manifest=output_manifest,
        artwork_fill_raise=0.4,
    )

    extrude.execute(
        context,
    )

    products = json.loads(
        output_manifest.read_text(
            encoding="utf-8",
        )
    )

    component_names = {component["name"] for component in products["components"]}

    assert "base" in component_names
    assert "artwork-fill" in component_names
    assert "artwork-1" in component_names

    assert tmp_path / "extrude" / "artwork-fill.stl" in rendered_paths


def test_artwork_fill_uses_independent_fill_physical_interval(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Artwork fill has its own Shape-owned physical Z dimension.

    Fill begins at the top of the structural base and its height is controlled
    by shape_artwork_fill_raise independently of shape_artwork_raise.
    """

    composition = tmp_path / "composition.svg"
    composition_manifest = tmp_path / "composition-products.json"
    output_manifest = tmp_path / "extrude" / "products.json"

    _write_physical_fill_composition(
        composition,
    )
    _write_physical_fill_manifest(
        composition_manifest,
        artwork_fill=_physical_fill_region(),
    )

    rendered_sources: dict[str, str] = {}

    def fake_render_stl_source(
        source: str,
        output: Path,
    ) -> None:
        output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        output.write_text(
            "solid test\nendsolid test\n",
            encoding="utf-8",
        )

        rendered_sources[output.name] = source

    monkeypatch.setattr(
        extrude,
        "render_stl_source",
        fake_render_stl_source,
    )

    context = _physical_fill_extrude_context(
        composition=composition,
        composition_manifest=composition_manifest,
        output_manifest=output_manifest,
        artwork_fill_raise=0.4,
    )

    extrude.execute(
        context,
    )

    fill_source = rendered_sources["artwork-fill.stl"]

    assert "shape_size = 100;" in fill_source
    assert "shape_base_raise = 2;" in fill_source
    assert "shape_artwork_fill_raise = 0.4;" in fill_source

    assert "translate([0, 0, 2])" in fill_source
    assert "height = 0.4" in fill_source

    assert "circle(r = 45, $fn = 256);" in fill_source
    assert "square([60, 50], center = false);" in fill_source


def test_artwork_fill_physical_geometry_is_independent_of_ridge_style(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Integrated and separate ridge partitioning do not alter Artwork-fill
    physical geometry.

    Fill geometry has already been established during registered composition.
    Extrusion dimensionalizes that persistent geometry without reconstructing
    it from physical ridge policy.
    """

    rendered_fill_sources: dict[str, str] = {}

    def fake_render_stl_source(
        source: str,
        output: Path,
    ) -> None:
        output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        output.write_text(
            "solid test\nendsolid test\n",
            encoding="utf-8",
        )

        if output.name == "artwork-fill.stl":
            rendered_fill_sources[current_style[0]] = source

    monkeypatch.setattr(
        extrude,
        "render_stl_source",
        fake_render_stl_source,
    )

    current_style = ["integrated"]

    for style in (
        "integrated",
        "separate",
    ):
        current_style[0] = style

        directory = tmp_path / style
        composition = directory / "composition.svg"
        composition_manifest = directory / "composition-products.json"
        output_manifest = directory / "extrude" / "products.json"

        directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        _write_physical_fill_composition(
            composition,
        )
        _write_physical_fill_manifest(
            composition_manifest,
            artwork_fill=_physical_fill_region(),
        )

        context = _physical_fill_extrude_context(
            composition=composition,
            composition_manifest=composition_manifest,
            output_manifest=output_manifest,
            artwork_fill_raise=0.6,
        )

        original_resolver = context.resolver.side_effect

        def resolver(
            name: str,
            *,
            ridge_style: str = style,
            fallback_resolver=original_resolver,
        ) -> object:
            if name == "shape_outer_ridge_style":
                return ridge_style

            assert fallback_resolver is not None
            return fallback_resolver(
                name,
            )

        extrude.execute(
            context,
        )

    assert rendered_fill_sources["integrated"] == rendered_fill_sources["separate"]


def test_artwork_fill_physical_geometry_does_not_manufacture_ridge_geometry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Physical Artwork fill is produced solely from its persistent registered
    region and does not reconstruct or manufacture structural ridge geometry.
    """

    composition = tmp_path / "composition.svg"
    composition_manifest = tmp_path / "composition-products.json"
    output_manifest = tmp_path / "extrude" / "products.json"

    _write_physical_fill_composition(
        composition,
    )
    _write_physical_fill_manifest(
        composition_manifest,
        artwork_fill=_physical_fill_region(),
    )

    rendered_sources: dict[str, str] = {}

    def fake_render_stl_source(
        source: str,
        output: Path,
    ) -> None:
        output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        output.write_text(
            "solid test\nendsolid test\n",
            encoding="utf-8",
        )

        rendered_sources[output.name] = source

    monkeypatch.setattr(
        extrude,
        "render_stl_source",
        fake_render_stl_source,
    )

    context = _physical_fill_extrude_context(
        composition=composition,
        composition_manifest=composition_manifest,
        output_manifest=output_manifest,
    )

    extrude.execute(
        context,
    )

    fill_source = rendered_sources["artwork-fill.stl"]

    assert "difference()" in fill_source

    # Persisted Artwork-fill geometry is dimensionalized directly.
    assert "circle(r = 45, $fn = 256);" in fill_source
    assert "translate([-30, -25, 0])" in fill_source
    assert "square([60, 50], center = false);" in fill_source

    # Extrude does not reconstruct fill from structural ridge geometry.
    assert "registered_shape_boundary" not in fill_source
    assert "registered_ridge_inner_boundary" not in fill_source
    assert "shape_outer_ridge_raise" not in fill_source


def test_artwork_fill_physically_excludes_incorporated_artwork_envelope(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Physical Artwork fill excludes the incorporated Artwork envelope in X/Y.

    The fill dimensionalizes the persistent registered region as the Shape
    interior minus the same transformed authoritative Artwork envelope used
    to place incorporated Artwork. Extrusion must preserve that subtraction
    rather than covering the Artwork footprint.
    """

    composition = tmp_path / "composition.svg"
    composition_manifest = tmp_path / "composition-products.json"
    output_manifest = tmp_path / "extrude" / "products.json"

    _write_physical_fill_composition(
        composition,
    )
    _write_physical_fill_manifest(
        composition_manifest,
        artwork_fill=_physical_fill_region(),
    )

    rendered_sources: dict[str, str] = {}

    def fake_render_stl_source(
        source: str,
        output: Path,
    ) -> None:
        output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        output.write_text(
            "solid test\nendsolid test\n",
            encoding="utf-8",
        )

        rendered_sources[output.name] = source

    monkeypatch.setattr(
        extrude,
        "render_stl_source",
        fake_render_stl_source,
    )

    context = _physical_fill_extrude_context(
        composition=composition,
        composition_manifest=composition_manifest,
        output_manifest=output_manifest,
    )

    extrude.execute(
        context,
    )

    fill_source = rendered_sources["artwork-fill.stl"]

    assert "difference()" in fill_source

    # The registered Shape interior is the outer fill boundary.
    assert "circle(r = 45, $fn = 256);" in fill_source

    # The transformed authoritative Artwork envelope remains the
    # subtracted inner boundary.
    assert "translate([-30, -25, 0])" in fill_source
    assert "square([60, 50], center = false);" in fill_source


def test_artwork_fill_manifest_preserves_shape_component_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Physical Artwork fill preserves its Shape-owned component identity.

    Extrusion produces physical geometry but does not resolve or persist
    physical printer-color assignment. Shape-owned physical color is resolved
    downstream during packaging.
    """

    composition = tmp_path / "composition.svg"
    composition_manifest = tmp_path / "composition-products.json"
    output_manifest = tmp_path / "extrude" / "products.json"

    _write_physical_fill_composition(
        composition,
    )
    _write_physical_fill_manifest(
        composition_manifest,
        artwork_fill=_physical_fill_region(),
    )

    def fake_render_stl_source(
        source: str,
        output: Path,
    ) -> None:
        del source

        output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        output.write_text(
            "solid test\nendsolid test\n",
            encoding="utf-8",
        )

    monkeypatch.setattr(
        extrude,
        "render_stl_source",
        fake_render_stl_source,
    )

    context = _physical_fill_extrude_context(
        composition=composition,
        composition_manifest=composition_manifest,
        output_manifest=output_manifest,
        artwork_fill_raise=0.6,
    )

    extrude.execute(
        context,
    )

    products = json.loads(
        output_manifest.read_text(
            encoding="utf-8",
        )
    )

    fill = next(
        component for component in products["components"] if component["name"] == "artwork-fill"
    )

    assert fill == {
        "name": "artwork-fill",
        "path": "artwork-fill.stl",
    }


def test_artwork_fill_extrusion_does_not_resolve_physical_color(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Artwork-fill extrusion does not resolve physical printer color.

    Physical color policy belongs exclusively to Shape Package. Extrusion
    may resolve whatever dimensional parameters its participating Features
    require, but it must not resolve shape_artwork_fill_color.
    """

    composition = tmp_path / "composition.svg"
    composition_manifest = tmp_path / "composition-products.json"
    output_manifest = tmp_path / "extrude" / "products.json"

    _write_physical_fill_composition(
        composition,
    )
    _write_physical_fill_manifest(
        composition_manifest,
        artwork_fill=_physical_fill_region(),
    )

    def fake_render_stl_source(
        source: str,
        output: Path,
    ) -> None:
        del source

        output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        output.write_text(
            "solid test\nendsolid test\n",
            encoding="utf-8",
        )

    monkeypatch.setattr(
        extrude,
        "render_stl_source",
        fake_render_stl_source,
    )

    context = _physical_fill_extrude_context(
        composition=composition,
        composition_manifest=composition_manifest,
        output_manifest=output_manifest,
        artwork_fill_raise=0.6,
    )

    original_resolver = context.resolver.side_effect

    def resolver(
        name: str,
    ) -> object:
        if name == "shape_artwork_fill_color":
            raise AssertionError("Extrude must not resolve shape_artwork_fill_color.")

        assert original_resolver is not None
        return original_resolver(
            name,
        )

    context.resolver.side_effect = resolver

    extrude.execute(
        context,
    )

    assert all(
        call.args != ("shape_artwork_fill_color",) for call in context.resolver.call_args_list
    )


def test_artwork_fill_remains_distinct_from_incorporated_artwork(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Shape-owned Artwork fill remains distinct from incorporated Artwork.

    Incorporated Artwork preserves logical Artifact-color identity through
    extrusion. Shape-owned Artwork fill preserves only its component identity.
    Physical printer-color assignment for both remains a Package concern.
    """

    composition = tmp_path / "composition.svg"
    composition_manifest = tmp_path / "composition-products.json"
    output_manifest = tmp_path / "extrude" / "products.json"

    _write_physical_fill_composition(
        composition,
    )
    _write_physical_fill_manifest(
        composition_manifest,
        artwork_fill=_physical_fill_region(),
    )

    def fake_render_stl_source(
        source: str,
        output: Path,
    ) -> None:
        del source

        output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        output.write_text(
            "solid test\nendsolid test\n",
            encoding="utf-8",
        )

    monkeypatch.setattr(
        extrude,
        "render_stl_source",
        fake_render_stl_source,
    )

    context = _physical_fill_extrude_context(
        composition=composition,
        composition_manifest=composition_manifest,
        output_manifest=output_manifest,
        artwork_fill_raise=0.6,
    )

    extrude.execute(
        context,
    )

    products = json.loads(
        output_manifest.read_text(
            encoding="utf-8",
        )
    )

    artwork = next(
        component for component in products["components"] if component["name"] == "artwork-1"
    )

    fill = next(
        component for component in products["components"] if component["name"] == "artwork-fill"
    )

    assert artwork["color"] == {
        "index": 1,
        "rgb": {
            "red": 250,
            "green": 250,
            "blue": 250,
        },
    }

    assert fill == {
        "name": "artwork-fill",
        "path": "artwork-fill.stl",
    }

    assert artwork["name"] == "artwork-1"
    assert fill["name"] == "artwork-fill"

    assert artwork["path"] != fill["path"]


def test_artwork_fill_extrusion_is_independent_of_invalid_physical_color(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Artwork-fill extrusion is independent of physical color validity.

    shape_artwork_fill_color is Package-owned policy. Extrusion therefore
    succeeds without resolving or validating that parameter.
    """

    composition = tmp_path / "composition.svg"
    composition_manifest = tmp_path / "composition-products.json"
    output_manifest = tmp_path / "extrude" / "products.json"

    _write_physical_fill_composition(
        composition,
    )
    _write_physical_fill_manifest(
        composition_manifest,
        artwork_fill=_physical_fill_region(),
    )

    def fake_render_stl_source(
        source: str,
        output: Path,
    ) -> None:
        del source

        output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        output.write_text(
            "solid test\nendsolid test\n",
            encoding="utf-8",
        )

    monkeypatch.setattr(
        extrude,
        "render_stl_source",
        fake_render_stl_source,
    )

    context = _physical_fill_extrude_context(
        composition=composition,
        composition_manifest=composition_manifest,
        output_manifest=output_manifest,
        artwork_fill_raise=0.6,
    )

    original_resolver = context.resolver.side_effect

    def resolver(name: str) -> object:
        if name == "shape_artwork_fill_color":
            raise AssertionError("Extrude must not resolve shape_artwork_fill_color.")

        assert original_resolver is not None
        return original_resolver(name)

    context.resolver.side_effect = resolver

    extrude.execute(
        context,
    )

    products = json.loads(
        output_manifest.read_text(
            encoding="utf-8",
        )
    )

    assert any(component["name"] == "artwork-fill" for component in products["components"])

    assert all(
        call.args != ("shape_artwork_fill_color",) for call in context.resolver.call_args_list
    )


def test_artwork_fill_manifest_contains_no_physical_color_assignment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Artwork-fill extrusion contains no physical color assignment.

    Shape Extrude owns physical geometry and component participation.
    Shape Package owns physical printer-color assignment.
    """

    composition = tmp_path / "composition.svg"
    composition_manifest = tmp_path / "composition-products.json"
    output_manifest = tmp_path / "extrude" / "products.json"

    _write_physical_fill_composition(
        composition,
    )
    _write_physical_fill_manifest(
        composition_manifest,
        artwork_fill=_physical_fill_region(),
    )

    def fake_render_stl_source(
        source: str,
        output: Path,
    ) -> None:
        del source

        output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        output.write_text(
            "solid test\nendsolid test\n",
            encoding="utf-8",
        )

    monkeypatch.setattr(
        extrude,
        "render_stl_source",
        fake_render_stl_source,
    )

    context = _physical_fill_extrude_context(
        composition=composition,
        composition_manifest=composition_manifest,
        output_manifest=output_manifest,
        artwork_fill_raise=0.6,
    )

    extrude.execute(
        context,
    )

    products = json.loads(
        output_manifest.read_text(
            encoding="utf-8",
        )
    )

    fill = next(
        component for component in products["components"] if component["name"] == "artwork-fill"
    )

    assert fill == {
        "name": "artwork-fill",
        "path": "artwork-fill.stl",
    }

    assert "color" not in fill
    assert "printer_color" not in fill
    assert "printer_head" not in fill
