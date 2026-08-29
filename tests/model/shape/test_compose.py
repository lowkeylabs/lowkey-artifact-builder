"""
Tests for Shape registered-Artwork composition.
"""
# File: tests/model/shape/test_compose.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
import math
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import Mock, call

import pytest

from lowkey_artifact_builder.engine import StageContext
from lowkey_artifact_builder.engine.bootstrap import build_stage_registry
from lowkey_artifact_builder.model.models.shape import stages
from lowkey_artifact_builder.model.models.shape.stages import compose

# =========================================================
# Helpers
# =========================================================


def _configure_compose_inputs(
    context: Mock,
    *,
    structure: Path,
    artwork_manifest: Path | None = None,
) -> None:
    """
    Configure declared Shape compose-stage inputs.

    Registered Artwork participates only when its external product dependency
    is bound into the stage context.
    """

    inputs = {
        "structure.structure": structure,
    }

    if artwork_manifest is not None:
        inputs["artwork.vector.manifest"] = artwork_manifest

    context.input.side_effect = inputs.__getitem__


def _configure_compose_outputs(
    context: Mock,
    *,
    composition: Path,
) -> Path:
    """
    Configure canonical Shape compose-stage outputs.

    Return the persistent composition manifest path for tests that need to
    inspect it.
    """

    manifest = composition.parent / f"{composition.stem}-products.json"

    outputs = {
        "composition": composition,
        "manifest": manifest,
    }

    context.output.side_effect = outputs.__getitem__

    return manifest


def _write_vector_manifest(
    path: Path,
) -> None:
    """
    Write a representative registered Artwork vector manifest.
    """

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    envelope = path.parent / "envelope.svg"

    envelope.write_text(
        (
            '<svg xmlns="http://www.w3.org/2000/svg" '
            'viewBox="0 0 16 12">'
            '<rect x="2" y="1" width="12" height="10"/>'
            "</svg>"
        ),
        encoding="utf-8",
    )

    path.write_text(
        json.dumps(
            {
                "registered_extent": {
                    "width": 16.0,
                    "height": 12.0,
                },
                "envelope": "envelope.svg",
                "products": [
                    {
                        "index": 1,
                        "path": "white.svg",
                        "name": "white",
                        "color": {
                            "r": 255,
                            "g": 255,
                            "b": 255,
                            "a": 255,
                        },
                    },
                    {
                        "index": 2,
                        "path": "black.svg",
                        "name": "black",
                        "color": {
                            "r": 0,
                            "g": 0,
                            "b": 0,
                            "a": 255,
                        },
                    },
                ],
            }
        ),
        encoding="utf-8",
    )


def _write_registered_structure(
    path: Path,
) -> None:
    """
    Write representative registered Shape structure.
    """

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        (
            '<svg xmlns="http://www.w3.org/2000/svg" '
            'viewBox="-0.5 -0.5 1.0 1.0">'
            '<circle cx="0.0" cy="0.0" r="0.5" />'
            "</svg>"
        ),
        encoding="utf-8",
    )


def _write_registered_square_structure(
    path: Path,
) -> None:
    """
    Write representative registered square Shape structure.
    """

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        (
            '<svg xmlns="http://www.w3.org/2000/svg" '
            'viewBox="-0.5 -0.5 1.0 1.0">'
            '<rect x="-0.5" y="-0.5" width="1.0" height="1.0" />'
            "</svg>"
        ),
        encoding="utf-8",
    )


def _write_registered_polygon_structure(
    path: Path,
    *,
    number_of_sides: int = 8,
    rotation: float = 22.5,
) -> None:
    """
    Write representative registered regular-polygon Shape structure.
    """

    from lowkey_artifact_builder.model.models.shape.stages import structure

    geometry = structure.create_polygon_geometry(
        number_of_sides=number_of_sides,
        rotation=rotation,
    )

    document = structure.create_polygon_svg(
        geometry,
    )

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    document.write(
        path,
        encoding="unicode",
    )


def _polygon_points(
    element: ET.Element,
) -> tuple[tuple[float, float], ...]:
    """
    Read registered polygon vertices from an SVG polygon element.
    """

    points = element.get(
        "points",
    )

    assert points is not None

    vertices: list[tuple[float, float]] = []

    for point in points.split():
        x_text, y_text = point.split(
            ",",
        )

        vertices.append(
            (
                float(x_text),
                float(y_text),
            )
        )

    return tuple(
        vertices,
    )


def _configure_shape_resolver(
    context: Mock,
    *,
    shape_size: float = 100.0,
    ridge_width: float = 0.0,
    ridge_style: str = "integrated",
) -> Mock:
    """
    Configure representative Shape composition parameters.
    """

    resolver = Mock()

    values = {
        "shape_size": shape_size,
        "shape_outer_ridge_width": ridge_width,
        "shape_outer_ridge_style": ridge_style,
    }

    resolver.side_effect = values.__getitem__
    context.resolver = resolver

    return resolver


# =========================================================
# Registered Artwork manifest
# =========================================================


def test_load_registered_artwork_uses_declared_manifest_membership(
    tmp_path: Path,
) -> None:
    """
    Registered Artwork membership comes from the manifest.

    Files that happen to exist beside the manifest are not implicitly
    incorporated into the registered component set.
    """

    manifest = tmp_path / "vector" / "products.json"

    _write_vector_manifest(
        manifest,
    )

    unexpected = manifest.parent / "unexpected.svg"

    unexpected.write_text(
        "<svg/>",
        encoding="utf-8",
    )

    artwork = compose.load_registered_artwork(
        manifest,
    )

    assert tuple(component.path.name for component in artwork.components) == (
        "white.svg",
        "black.svg",
    )


def test_load_registered_artwork_resolves_components_beside_manifest(
    tmp_path: Path,
) -> None:
    """
    Manifest component paths are resolved relative to the manifest itself.

    Shape consumes the manifest contract rather than constructing Artwork
    stage-directory paths.
    """

    manifest = tmp_path / "arbitrary-location" / "products.json"

    _write_vector_manifest(
        manifest,
    )

    artwork = compose.load_registered_artwork(
        manifest,
    )

    assert tuple(component.path for component in artwork.components) == (
        manifest.parent / "white.svg",
        manifest.parent / "black.svg",
    )


def test_load_registered_artwork_preserves_component_metadata(
    tmp_path: Path,
) -> None:
    """
    Shape retains semantic component identity supplied by Artwork.

    The registered component payload remains opaque; Shape needs membership
    and semantic metadata without independently interpreting SVG geometry.
    """

    manifest = tmp_path / "vector" / "products.json"

    _write_vector_manifest(
        manifest,
    )

    artwork = compose.load_registered_artwork(
        manifest,
    )

    first = artwork.components[0]
    second = artwork.components[1]

    assert first.index == 1
    assert first.name == "white"
    assert first.color == {
        "r": 255,
        "g": 255,
        "b": 255,
        "a": 255,
    }

    assert second.index == 2
    assert second.name == "black"
    assert second.color == {
        "r": 0,
        "g": 0,
        "b": 0,
        "a": 255,
    }


def test_load_registered_artwork_reads_common_registered_extent(
    tmp_path: Path,
) -> None:
    """
    Shape obtains one common registered extent from the Artwork manifest.

    The consumer does not calculate independent bounds for individual
    registered components.
    """

    manifest = tmp_path / "vector" / "products.json"

    _write_vector_manifest(
        manifest,
    )

    artwork = compose.load_registered_artwork(
        manifest,
    )

    assert artwork.registered_extent.width == 16.0
    assert artwork.registered_extent.height == 12.0


def test_load_registered_artwork_resolves_envelope_beside_manifest(
    tmp_path: Path,
) -> None:
    """
    Registered Artwork exposes its envelope through the manifest contract.

    Shape resolves the envelope relative to the supplied vector manifest
    rather than reconstructing an Artwork stage path.
    """

    manifest = tmp_path / "arbitrary-location" / "products.json"

    _write_vector_manifest(
        manifest,
    )

    artwork = compose.load_registered_artwork(
        manifest,
    )

    assert artwork.envelope == manifest.parent / "envelope.svg"


def test_load_registered_artwork_requires_declared_envelope(
    tmp_path: Path,
) -> None:
    """
    Registered Artwork requires the envelope published by its manifest.

    Shape does not infer Artwork occupancy from individual component bounds.
    """

    manifest = tmp_path / "vector" / "products.json"

    _write_vector_manifest(
        manifest,
    )

    data = json.loads(
        manifest.read_text(
            encoding="utf-8",
        )
    )

    del data["envelope"]

    manifest.write_text(
        json.dumps(
            data,
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="envelope",
    ):
        compose.load_registered_artwork(
            manifest,
        )


# =========================================================
# Registered Shape interior region
# =========================================================


def test_square_interior_with_ridge_uses_inner_boundary(
    tmp_path: Path,
) -> None:
    """
    A square ridge's inner boundary defines the registered interior region.
    """

    structure = tmp_path / "structure.svg"
    composition = tmp_path / "composition.svg"

    _write_registered_square_structure(
        structure,
    )

    compose._compose_ridge(
        structure,
        composition,
        shape_size=100.0,
        ridge_width=5.0,
    )

    interior = compose.registered_interior_region(
        composition,
    )

    assert interior.get("id") == "ridge-inner-boundary"
    assert interior.tag == "{http://www.w3.org/2000/svg}rect"
    assert float(interior.get("x", "nan")) == pytest.approx(-0.45)
    assert float(interior.get("y", "nan")) == pytest.approx(-0.45)
    assert float(interior.get("width", "nan")) == pytest.approx(0.9)
    assert float(interior.get("height", "nan")) == pytest.approx(0.9)


def test_polygon_interior_with_ridge_uses_inner_boundary(
    tmp_path: Path,
) -> None:
    """
    A polygon ridge's inner boundary defines the registered interior region.
    """

    structure = tmp_path / "structure.svg"
    composition = tmp_path / "composition.svg"

    _write_registered_polygon_structure(
        structure,
    )

    compose._compose_ridge(
        structure,
        composition,
        shape_size=100.0,
        ridge_width=5.0,
    )

    interior = compose.registered_interior_region(
        composition,
    )

    assert interior.get("id") == "ridge-inner-boundary"
    assert interior.tag == "{http://www.w3.org/2000/svg}polygon"

    inner_points = _polygon_points(
        interior,
    )

    assert len(inner_points) == 8


def test_shape_interior_without_ridge_is_shape_boundary(
    tmp_path: Path,
) -> None:
    """
    Without a ridge, the registered Shape boundary defines the interior region.
    """

    structure = tmp_path / "structure.svg"

    _write_registered_structure(
        structure,
    )

    interior = compose.registered_interior_region(
        structure,
    )

    assert interior.tag == "{http://www.w3.org/2000/svg}circle"
    assert float(interior.get("cx", "nan")) == 0.0
    assert float(interior.get("cy", "nan")) == 0.0
    assert float(interior.get("r", "nan")) == 0.5


def test_shape_interior_with_ridge_is_innermost_ridge_boundary(
    tmp_path: Path,
) -> None:
    """
    The innermost existing ridge boundary defines the registered interior region.
    """

    structure = tmp_path / "structure.svg"
    composition = tmp_path / "composition.svg"

    _write_registered_structure(
        structure,
    )

    compose._compose_ridge(
        structure,
        composition,
        shape_size=100.0,
        ridge_width=5.0,
    )

    interior = compose.registered_interior_region(
        composition,
    )

    assert interior.get("id") == "ridge-inner-boundary"
    assert interior.tag == "{http://www.w3.org/2000/svg}circle"
    assert float(interior.get("cx", "nan")) == 0.0
    assert float(interior.get("cy", "nan")) == 0.0
    assert float(interior.get("r", "nan")) == pytest.approx(0.45)


# =========================================================
# Registered Artwork placement
# =========================================================


def test_registered_artwork_fits_into_rectangular_shape_interior(
    tmp_path: Path,
) -> None:
    """
    Registered Artwork fits within the actual rectangular Shape interior.

    Shape placement derives the available region from registered structural
    geometry rather than requiring callers to independently supply dimensions.
    """

    structure = tmp_path / "structure.svg"
    composition = tmp_path / "composition.svg"
    envelope = tmp_path / "envelope.svg"

    _write_registered_square_structure(
        structure,
    )

    compose._compose_ridge(
        structure,
        composition,
        shape_size=100.0,
        ridge_width=5.0,
    )

    envelope.write_text(
        (
            '<svg xmlns="http://www.w3.org/2000/svg" '
            'viewBox="0 0 16 12">'
            '<rect x="2" y="1" width="12" height="10"/>'
            "</svg>"
        ),
        encoding="utf-8",
    )

    artwork = compose.RegisteredArtwork(
        registered_extent=compose.RegisteredExtent(
            width=16.0,
            height=12.0,
        ),
        envelope=envelope,
        components=(),
    )

    placement = compose.fit_registered_artwork_to_shape(
        artwork,
        composition=composition,
    )

    assert placement.scale == pytest.approx(0.075)
    assert placement.width == pytest.approx(0.9)
    assert placement.height == pytest.approx(0.75)


def test_registered_artwork_centers_within_rectangular_shape_interior(
    tmp_path: Path,
) -> None:
    """
    Registered Artwork is centered in the registered Shape interior.

    Placement accounts for both the Shape interior origin and the Artwork
    envelope's position in its own registered coordinate system.
    """

    structure = tmp_path / "structure.svg"
    composition = tmp_path / "composition.svg"
    envelope = tmp_path / "envelope.svg"

    _write_registered_square_structure(
        structure,
    )

    compose._compose_ridge(
        structure,
        composition,
        shape_size=100.0,
        ridge_width=5.0,
    )

    envelope.write_text(
        (
            '<svg xmlns="http://www.w3.org/2000/svg" '
            'viewBox="0 0 16 12">'
            '<rect x="2" y="1" width="12" height="10"/>'
            "</svg>"
        ),
        encoding="utf-8",
    )

    artwork = compose.RegisteredArtwork(
        registered_extent=compose.RegisteredExtent(
            width=16.0,
            height=12.0,
        ),
        envelope=envelope,
        components=(),
    )

    transform = compose.fit_registered_artwork_to_shape(
        artwork,
        composition=composition,
    )

    assert transform.translate_x == pytest.approx(-0.6)
    assert transform.translate_y == pytest.approx(-0.45)


def test_registered_artwork_fits_inside_circular_shape_interior(
    tmp_path: Path,
) -> None:
    """
    Registered Artwork is contained by the actual circular Shape interior.

    Fitting uses circular containment rather than the circle's rectangular
    bounding box, so no occupied Artwork corner extends outside the Shape.
    """

    structure = tmp_path / "structure.svg"
    composition = tmp_path / "composition.svg"
    envelope = tmp_path / "envelope.svg"

    _write_registered_structure(
        structure,
    )

    compose._compose_ridge(
        structure,
        composition,
        shape_size=100.0,
        ridge_width=5.0,
    )

    envelope.write_text(
        (
            '<svg xmlns="http://www.w3.org/2000/svg" '
            'viewBox="0 0 16 12">'
            '<rect x="2" y="1" width="12" height="10"/>'
            "</svg>"
        ),
        encoding="utf-8",
    )

    artwork = compose.RegisteredArtwork(
        registered_extent=compose.RegisteredExtent(
            width=16.0,
            height=12.0,
        ),
        envelope=envelope,
        components=(),
    )

    transform = compose.fit_registered_artwork_to_shape(
        artwork,
        composition=composition,
    )

    expected_scale = 0.45 / math.hypot(
        6.0,
        5.0,
    )

    assert transform.scale == pytest.approx(expected_scale)
    assert transform.width == pytest.approx(
        12.0 * expected_scale,
    )
    assert transform.height == pytest.approx(
        10.0 * expected_scale,
    )


def test_registered_artwork_centers_within_circular_shape_interior(
    tmp_path: Path,
) -> None:
    """
    Registered Artwork occupancy is centered on the circular Shape interior.

    The common transform accounts for the Artwork envelope's registered
    offset while preserving registration of the complete Artwork collection.
    """

    structure = tmp_path / "structure.svg"
    composition = tmp_path / "composition.svg"
    envelope = tmp_path / "envelope.svg"

    _write_registered_structure(
        structure,
    )

    compose._compose_ridge(
        structure,
        composition,
        shape_size=100.0,
        ridge_width=5.0,
    )

    envelope.write_text(
        (
            '<svg xmlns="http://www.w3.org/2000/svg" '
            'viewBox="0 0 16 12">'
            '<rect x="2" y="1" width="12" height="10"/>'
            "</svg>"
        ),
        encoding="utf-8",
    )

    artwork = compose.RegisteredArtwork(
        registered_extent=compose.RegisteredExtent(
            width=16.0,
            height=12.0,
        ),
        envelope=envelope,
        components=(),
    )

    transform = compose.fit_registered_artwork_to_shape(
        artwork,
        composition=composition,
    )

    expected_scale = 0.45 / math.hypot(
        6.0,
        5.0,
    )

    assert transform.translate_x == pytest.approx(
        -(8.0 * expected_scale),
    )
    assert transform.translate_y == pytest.approx(
        -(6.0 * expected_scale),
    )


def test_registered_artwork_fits_inside_polygon_shape_interior(
    tmp_path: Path,
) -> None:
    """
    Registered Artwork is contained by the actual polygon Shape interior.

    Fitting respects polygon edges rather than merely fitting within the
    polygon's rectangular bounding box.
    """

    structure = tmp_path / "structure.svg"
    composition = tmp_path / "composition.svg"
    envelope = tmp_path / "envelope.svg"

    _write_registered_polygon_structure(
        structure,
    )

    compose._compose_ridge(
        structure,
        composition,
        shape_size=100.0,
        ridge_width=5.0,
    )

    envelope.write_text(
        (
            '<svg xmlns="http://www.w3.org/2000/svg" '
            'viewBox="-1 -1 2 2">'
            '<rect x="-1" y="-1" width="2" height="2"/>'
            "</svg>"
        ),
        encoding="utf-8",
    )

    artwork = compose.RegisteredArtwork(
        registered_extent=compose.RegisteredExtent(
            width=2.0,
            height=2.0,
        ),
        envelope=envelope,
        components=(),
    )

    transform = compose.fit_registered_artwork_to_shape(
        artwork,
        composition=composition,
    )

    interior = compose.registered_interior_region(
        composition,
    )
    polygon = compose._read_polygon_points(
        interior,
    )

    transformed_corners = (
        (-transform.scale, -transform.scale),
        (transform.scale, -transform.scale),
        (transform.scale, transform.scale),
        (-transform.scale, transform.scale),
    )

    for corner in transformed_corners:
        assert _point_is_inside_convex_polygon(
            corner,
            polygon,
        )


def _point_is_inside_convex_polygon(
    point: tuple[float, float],
    polygon: tuple[tuple[float, float], ...],
) -> bool:
    """
    Return whether a point lies inside or on a convex polygon.
    """

    signs: list[float] = []

    for index, start in enumerate(polygon):
        end = polygon[(index + 1) % len(polygon)]

        edge_x = end[0] - start[0]
        edge_y = end[1] - start[1]

        point_x = point[0] - start[0]
        point_y = point[1] - start[1]

        cross = edge_x * point_y - edge_y * point_x

        if not math.isclose(
            cross,
            0.0,
            abs_tol=1.0e-12,
        ):
            signs.append(cross)

    return all(sign >= 0.0 for sign in signs) or all(sign <= 0.0 for sign in signs)


def test_registered_artwork_centers_within_polygon_shape_interior(
    tmp_path: Path,
) -> None:
    """
    Registered Artwork occupancy is centered within the polygon Shape interior.

    Polygon containment preserves one common registered transformation rather
    than independently positioning Artwork geometry.
    """

    structure = tmp_path / "structure.svg"
    composition = tmp_path / "composition.svg"
    envelope = tmp_path / "envelope.svg"

    _write_registered_polygon_structure(
        structure,
    )

    compose._compose_ridge(
        structure,
        composition,
        shape_size=100.0,
        ridge_width=5.0,
    )

    envelope.write_text(
        (
            '<svg xmlns="http://www.w3.org/2000/svg" '
            'viewBox="-1 -1 2 2">'
            '<rect x="-1" y="-1" width="2" height="2"/>'
            "</svg>"
        ),
        encoding="utf-8",
    )

    artwork = compose.RegisteredArtwork(
        registered_extent=compose.RegisteredExtent(
            width=2.0,
            height=2.0,
        ),
        envelope=envelope,
        components=(),
    )

    transform = compose.fit_registered_artwork_to_shape(
        artwork,
        composition=composition,
    )

    assert transform.translate_x == pytest.approx(0.0)
    assert transform.translate_y == pytest.approx(0.0)


def test_registered_artwork_fit_uses_envelope_occupancy(
    tmp_path: Path,
) -> None:
    """
    Artwork fitting uses its occupied envelope rather than registered_extent.

    registered_extent defines the common coordinate system; the envelope
    defines the region that must fit within the Shape interior.
    """

    envelope = tmp_path / "envelope.svg"

    envelope.write_text(
        (
            '<svg xmlns="http://www.w3.org/2000/svg" '
            'viewBox="0 0 16 12">'
            '<rect x="4" y="3" width="8" height="6"/>'
            "</svg>"
        ),
        encoding="utf-8",
    )

    artwork = compose.RegisteredArtwork(
        registered_extent=compose.RegisteredExtent(
            width=16.0,
            height=12.0,
        ),
        envelope=envelope,
        components=(),
    )

    transform = compose.fit_registered_artwork(
        artwork,
        available_width=80.0,
        available_height=80.0,
    )

    assert transform.scale == 10.0
    assert transform.width == 80.0
    assert transform.height == 60.0


def test_registered_artwork_fit_centers_envelope_occupancy(
    tmp_path: Path,
) -> None:
    """
    Artwork fitting centers the occupied envelope within the available region.

    Envelope position within registered_extent participates in the common
    transform so the occupied Artwork, rather than the coordinate extent,
    is centered.
    """

    envelope = tmp_path / "envelope.svg"

    envelope.write_text(
        (
            '<svg xmlns="http://www.w3.org/2000/svg" '
            'viewBox="0 0 16 12">'
            '<rect x="2" y="3" width="8" height="6"/>'
            "</svg>"
        ),
        encoding="utf-8",
    )

    artwork = compose.RegisteredArtwork(
        registered_extent=compose.RegisteredExtent(
            width=16.0,
            height=12.0,
        ),
        envelope=envelope,
        components=(),
    )

    transform = compose.fit_registered_artwork(
        artwork,
        available_width=80.0,
        available_height=80.0,
    )

    assert transform.scale == 10.0
    assert transform.width == 80.0
    assert transform.height == 60.0
    assert transform.translate_x == -20.0
    assert transform.translate_y == -20.0


def test_registered_artwork_fit_preserves_aspect_ratio(
    tmp_path: Path,
) -> None:
    """
    Registered Artwork uses uniform contain-style scaling.

    The limiting interior dimension determines one X/Y scale from the occupied
    envelope so Artwork is completely contained without stretching.
    """

    envelope = tmp_path / "envelope.svg"

    envelope.write_text(
        (
            '<svg xmlns="http://www.w3.org/2000/svg" '
            'viewBox="0 0 16 12">'
            '<rect x="4" y="3" width="8" height="6"/>'
            "</svg>"
        ),
        encoding="utf-8",
    )

    artwork = compose.RegisteredArtwork(
        registered_extent=compose.RegisteredExtent(
            width=16.0,
            height=12.0,
        ),
        envelope=envelope,
        components=(),
    )

    transform = compose.fit_registered_artwork(
        artwork,
        available_width=64.0,
        available_height=36.0,
    )

    assert transform.scale == 6.0
    assert transform.width == 48.0
    assert transform.height == 36.0


def test_registered_artwork_components_share_one_transform(
    tmp_path: Path,
) -> None:
    """
    Every registered component receives the same Artwork transformation.

    Shape does not independently fit component payloads because doing so could
    destroy registration between the component layers.
    """

    envelope = tmp_path / "envelope.svg"

    envelope.write_text(
        (
            '<svg xmlns="http://www.w3.org/2000/svg" '
            'viewBox="0 0 16 12">'
            '<rect x="2" y="1" width="12" height="10"/>'
            "</svg>"
        ),
        encoding="utf-8",
    )

    artwork = compose.RegisteredArtwork(
        registered_extent=compose.RegisteredExtent(
            width=16.0,
            height=12.0,
        ),
        envelope=envelope,
        components=(
            compose.RegisteredArtworkComponent(
                index=1,
                path=tmp_path / "white.svg",
                name="white",
                color={
                    "r": 255,
                    "g": 255,
                    "b": 255,
                    "a": 255,
                },
            ),
            compose.RegisteredArtworkComponent(
                index=2,
                path=tmp_path / "black.svg",
                name="black",
                color={
                    "r": 0,
                    "g": 0,
                    "b": 0,
                    "a": 255,
                },
            ),
        ),
    )

    placement = compose.place_registered_artwork(
        artwork,
        available_width=80.0,
        available_height=80.0,
    )

    assert tuple(component.transform for component in placement.components) == (
        placement.transform,
        placement.transform,
    )

    assert tuple(component.component for component in placement.components) == artwork.components


# =========================================================
# Compose stage execution
# =========================================================


def test_compose_stage_materializes_registered_composition_manifest(
    tmp_path: Path,
) -> None:
    """
    Shape composition materializes its declared persistent manifest.

    The manifest provides the stable downstream contract for discovering
    registered composition products without scanning the stage directory.
    """

    structure_input = tmp_path / "structure.svg"
    composition_output = tmp_path / "composition.svg"
    manifest_output = tmp_path / "products.json"

    _write_registered_structure(
        structure_input,
    )

    context = Mock(
        spec=StageContext,
    )
    _configure_compose_inputs(
        context,
        structure=structure_input,
    )

    outputs = {
        "composition": composition_output,
        "manifest": manifest_output,
    }
    context.output.side_effect = outputs.__getitem__

    _configure_shape_resolver(
        context,
    )

    compose.execute(
        context,
    )

    assert composition_output.is_file()
    assert manifest_output.is_file()

    assert context.output.call_args_list == [
        call("composition"),
        call("manifest"),
    ]


def test_compose_stage_manifest_declares_structural_composition(
    tmp_path: Path,
) -> None:
    """
    Shape-only composition records its structural registered geometry.

    Downstream stages locate the persistent composition through the manifest
    rather than reconstructing its filename or scanning stage outputs.
    """

    structure_input = tmp_path / "structure.svg"
    composition_output = tmp_path / "composition.svg"
    manifest_output = tmp_path / "products.json"

    _write_registered_structure(
        structure_input,
    )

    context = Mock(
        spec=StageContext,
    )
    _configure_compose_inputs(
        context,
        structure=structure_input,
    )

    outputs = {
        "composition": composition_output,
        "manifest": manifest_output,
    }
    context.output.side_effect = outputs.__getitem__

    _configure_shape_resolver(
        context,
    )

    compose.execute(
        context,
    )

    manifest = json.loads(
        manifest_output.read_text(
            encoding="utf-8",
        )
    )

    assert manifest == {
        "composition": "composition.svg",
        "artwork": None,
    }


def test_compose_stage_materializes_registered_composition(
    tmp_path: Path,
) -> None:
    """
    Shape composition materializes its declared registered product.

    The stage obtains registered Shape structure and its output location
    through StageContext rather than constructing artifact filesystem paths.
    """

    structure_input = tmp_path / "structure.svg"
    output = tmp_path / "composition.svg"

    _write_registered_structure(
        structure_input,
    )

    context = Mock(
        spec=StageContext,
    )
    _configure_compose_inputs(
        context,
        structure=structure_input,
    )
    _configure_compose_outputs(
        context,
        composition=output,
    )

    _configure_shape_resolver(
        context,
    )

    compose.execute(
        context,
    )

    assert context.input.call_args_list == [
        call("structure.structure"),
        call("artwork.vector.manifest"),
    ]

    assert context.output.call_args_list == [
        call("composition"),
        call("manifest"),
    ]

    assert output.is_file()


def test_compose_stage_preserves_registered_shape_geometry(
    tmp_path: Path,
) -> None:
    """
    Shape composition preserves structural geometry in registered Shape space.

    Composition does not introduce physical X/Y dimensions before the
    downstream dimensionalization boundary.
    """

    structure_input = tmp_path / "structure.svg"
    output = tmp_path / "composition.svg"

    _write_registered_structure(
        structure_input,
    )

    context = Mock(
        spec=StageContext,
    )
    _configure_compose_inputs(
        context,
        structure=structure_input,
    )

    _configure_compose_outputs(
        context,
        composition=output,
    )

    _configure_shape_resolver(
        context,
    )

    compose.execute(
        context,
    )

    root = ET.parse(
        output,
    ).getroot()

    assert root.get("viewBox") == "-0.5 -0.5 1.0 1.0"
    assert root.get("width") is None
    assert root.get("height") is None

    circle = root.find(
        "{http://www.w3.org/2000/svg}circle",
    )

    assert circle is not None
    assert circle.get("cx") == "0.0"
    assert circle.get("cy") == "0.0"
    assert circle.get("r") == "0.5"


def test_compose_stage_resolves_only_registered_partition_parameters(
    tmp_path: Path,
) -> None:
    """
    Registered composition resolves only parameters needed for partitioning.

    Shape size and ridge width establish the ridge inset in registered space.
    Ridge style establishes structural partition policy. Physical Z dimensions
    remain downstream.
    """

    structure_input = tmp_path / "structure.svg"
    output = tmp_path / "composition.svg"

    _write_registered_structure(
        structure_input,
    )

    context = Mock(
        spec=StageContext,
    )
    _configure_compose_inputs(
        context,
        structure=structure_input,
    )
    _configure_compose_outputs(
        context,
        composition=output,
    )

    resolver = _configure_shape_resolver(
        context,
    )

    compose.execute(
        context,
    )

    assert resolver.call_args_list == [
        call("shape_size"),
        call("shape_outer_ridge_width"),
        call("shape_outer_ridge_style"),
    ]


# =========================================================
# Registered outer-ridge composition
# =========================================================


def test_compose_circle_integrated_ridge_preserves_outer_boundary(
    tmp_path: Path,
) -> None:
    """
    An integrated ridge does not change the registered outer Shape boundary.

    Ridge width is measured inward from the complete Shape boundary, while
    the base retains the complete registered circle envelope. Registered
    boundaries retain semantic identity for downstream dimensionalization.
    """

    structure_input = tmp_path / "structure.svg"
    output = tmp_path / "composition.svg"

    _write_registered_structure(
        structure_input,
    )

    context = Mock(
        spec=StageContext,
    )
    _configure_compose_inputs(
        context,
        structure=structure_input,
    )
    _configure_compose_outputs(
        context,
        composition=output,
    )

    _configure_shape_resolver(
        context,
        shape_size=100.0,
        ridge_width=5.0,
        ridge_style="integrated",
    )

    compose.execute(
        context,
    )

    root = ET.parse(
        output,
    ).getroot()

    outer_boundary = root.find(
        '{http://www.w3.org/2000/svg}circle[@id="shape-boundary"]',
    )
    ridge_inner_boundary = root.find(
        '{http://www.w3.org/2000/svg}circle[@id="ridge-inner-boundary"]',
    )

    assert outer_boundary is not None
    assert ridge_inner_boundary is not None

    assert outer_boundary.get("cx") == "0.0"
    assert outer_boundary.get("cy") == "0.0"
    assert float(outer_boundary.get("r", "0.0")) == 0.5

    assert ridge_inner_boundary.get("cx") == "0.0"
    assert ridge_inner_boundary.get("cy") == "0.0"
    assert float(ridge_inner_boundary.get("r", "0.0")) == 0.45


def test_compose_circle_ridge_width_is_relative_to_shape_size(
    tmp_path: Path,
) -> None:
    """
    Physical ridge width is converted into a registered-space inset.

    Proportionally equal physical ridge widths produce the same registered
    ridge geometry regardless of the later physical Shape size.
    """

    radii_by_dimensions: list[list[float]] = []

    for index, (shape_size, ridge_width) in enumerate(
        (
            (100.0, 5.0),
            (200.0, 10.0),
        )
    ):
        structure_input = tmp_path / f"structure-{index}.svg"
        output = tmp_path / f"composition-{index}.svg"

        _write_registered_structure(
            structure_input,
        )

        context = Mock(
            spec=StageContext,
        )
        _configure_compose_inputs(
            context,
            structure=structure_input,
        )
        _configure_compose_outputs(
            context,
            composition=output,
        )

        _configure_shape_resolver(
            context,
            shape_size=shape_size,
            ridge_width=ridge_width,
            ridge_style="integrated",
        )

        compose.execute(
            context,
        )

        root = ET.parse(
            output,
        ).getroot()

        circles = root.findall(
            "{http://www.w3.org/2000/svg}circle",
        )

        radii_by_dimensions.append(sorted(float(circle.get("r", "0.0")) for circle in circles))

    assert radii_by_dimensions == [
        [0.45, 0.5],
        [0.45, 0.5],
    ]


def test_compose_circle_zero_width_produces_no_ridge_partition(
    tmp_path: Path,
) -> None:
    """
    Zero ridge width disables the outer ridge.

    Ridge style does not create registered ridge geometry when the configured
    ridge width is zero.
    """

    structure_input = tmp_path / "structure.svg"
    output = tmp_path / "composition.svg"

    _write_registered_structure(
        structure_input,
    )

    context = Mock(
        spec=StageContext,
    )
    _configure_compose_inputs(
        context,
        structure=structure_input,
    )
    _configure_compose_outputs(
        context,
        composition=output,
    )

    _configure_shape_resolver(
        context,
        shape_size=100.0,
        ridge_width=0.0,
        ridge_style="integrated",
    )

    compose.execute(
        context,
    )

    root = ET.parse(
        output,
    ).getroot()

    circles = root.findall(
        "{http://www.w3.org/2000/svg}circle",
    )

    assert len(circles) == 1
    assert circles[0].get("r") == "0.5"


def test_compose_square_ridge_preserves_outer_boundary(
    tmp_path: Path,
) -> None:
    """
    A square ridge preserves the complete registered Shape boundary.

    Ridge width is measured inward from the complete square envelope.
    A 5 mm ridge on a 100 mm square therefore leaves the outer registered
    envelope unchanged at 1x1 while producing a 0.9x0.9 inner boundary.
    """

    structure_input = tmp_path / "structure.svg"
    output = tmp_path / "composition.svg"

    _write_registered_square_structure(
        structure_input,
    )

    context = Mock(
        spec=StageContext,
    )
    _configure_compose_inputs(
        context,
        structure=structure_input,
    )
    _configure_compose_outputs(
        context,
        composition=output,
    )

    _configure_shape_resolver(
        context,
        shape_size=100.0,
        ridge_width=5.0,
        ridge_style="integrated",
    )

    compose.execute(
        context,
    )

    root = ET.parse(
        output,
    ).getroot()

    outer_boundary = root.find(
        '{http://www.w3.org/2000/svg}rect[@id="shape-boundary"]',
    )
    ridge_inner_boundary = root.find(
        '{http://www.w3.org/2000/svg}rect[@id="ridge-inner-boundary"]',
    )

    assert outer_boundary is not None
    assert ridge_inner_boundary is not None

    assert float(outer_boundary.get("x", "0.0")) == -0.5
    assert float(outer_boundary.get("y", "0.0")) == -0.5
    assert float(outer_boundary.get("width", "0.0")) == 1.0
    assert float(outer_boundary.get("height", "0.0")) == 1.0

    assert float(ridge_inner_boundary.get("x", "0.0")) == -0.45
    assert float(ridge_inner_boundary.get("y", "0.0")) == -0.45
    assert float(ridge_inner_boundary.get("width", "0.0")) == 0.9
    assert float(ridge_inner_boundary.get("height", "0.0")) == 0.9


def test_compose_square_ridge_style_preserves_registered_boundaries(
    tmp_path: Path,
) -> None:
    """
    Square ridge style does not change registered ridge geometry.

    Integrated and separate construction use identical outer and inner
    registered boundaries. Style affects later physical component
    partitioning rather than registered Shape geometry.
    """

    boundaries_by_style: dict[
        str,
        tuple[
            tuple[float, float, float, float],
            tuple[float, float, float, float],
        ],
    ] = {}

    for ridge_style in (
        "integrated",
        "separate",
    ):
        structure_input = tmp_path / f"structure-{ridge_style}.svg"
        output = tmp_path / f"composition-{ridge_style}.svg"

        _write_registered_square_structure(
            structure_input,
        )

        context = Mock(
            spec=StageContext,
        )
        _configure_compose_inputs(
            context,
            structure=structure_input,
        )
        _configure_compose_outputs(
            context,
            composition=output,
        )

        _configure_shape_resolver(
            context,
            shape_size=100.0,
            ridge_width=5.0,
            ridge_style=ridge_style,
        )

        compose.execute(
            context,
        )

        root = ET.parse(
            output,
        ).getroot()

        outer = root.find(
            '{http://www.w3.org/2000/svg}rect[@id="shape-boundary"]',
        )
        inner = root.find(
            '{http://www.w3.org/2000/svg}rect[@id="ridge-inner-boundary"]',
        )

        assert outer is not None
        assert inner is not None

        boundaries_by_style[ridge_style] = (
            (
                float(outer.get("x", "0.0")),
                float(outer.get("y", "0.0")),
                float(outer.get("width", "0.0")),
                float(outer.get("height", "0.0")),
            ),
            (
                float(inner.get("x", "0.0")),
                float(inner.get("y", "0.0")),
                float(inner.get("width", "0.0")),
                float(inner.get("height", "0.0")),
            ),
        )

    assert boundaries_by_style["integrated"] == boundaries_by_style["separate"]


def test_compose_polygon_ridge_preserves_outer_boundary(
    tmp_path: Path,
) -> None:
    """
    A polygon ridge preserves the complete registered Shape boundary.

    Ridge composition adds an inner polygon boundary without changing the
    normalized and rotated outer polygon produced by structural geometry.
    """

    structure_input = tmp_path / "structure.svg"
    output = tmp_path / "composition.svg"

    _write_registered_polygon_structure(
        structure_input,
        number_of_sides=8,
        rotation=22.5,
    )

    original_root = ET.parse(
        structure_input,
    ).getroot()

    original_polygon = original_root.find(
        "{http://www.w3.org/2000/svg}polygon",
    )

    assert original_polygon is not None

    original_points = _polygon_points(
        original_polygon,
    )

    context = Mock(
        spec=StageContext,
    )
    _configure_compose_inputs(
        context,
        structure=structure_input,
    )
    _configure_compose_outputs(
        context,
        composition=output,
    )

    _configure_shape_resolver(
        context,
        shape_size=100.0,
        ridge_width=5.0,
        ridge_style="integrated",
    )

    compose.execute(
        context,
    )

    root = ET.parse(
        output,
    ).getroot()

    outer_boundary = root.find(
        '{http://www.w3.org/2000/svg}polygon[@id="shape-boundary"]',
    )
    ridge_inner_boundary = root.find(
        '{http://www.w3.org/2000/svg}polygon[@id="ridge-inner-boundary"]',
    )

    assert outer_boundary is not None
    assert ridge_inner_boundary is not None

    outer_points = _polygon_points(
        outer_boundary,
    )

    assert len(outer_points) == len(original_points)

    for actual, expected in zip(
        outer_points,
        original_points,
        strict=True,
    ):
        assert actual == pytest.approx(
            expected,
        )


def test_compose_polygon_ridge_offsets_edges_perpendicularly(
    tmp_path: Path,
) -> None:
    """
    Polygon ridge width is a perpendicular inward edge offset.

    Every inner ridge edge remains parallel to its corresponding outer edge
    and is separated from that edge by ridge_width / shape_size registered
    units.
    """

    structure_input = tmp_path / "structure.svg"
    output = tmp_path / "composition.svg"

    _write_registered_polygon_structure(
        structure_input,
        number_of_sides=8,
        rotation=17.0,
    )

    context = Mock(
        spec=StageContext,
    )
    _configure_compose_inputs(
        context,
        structure=structure_input,
    )
    _configure_compose_outputs(
        context,
        composition=output,
    )

    _configure_shape_resolver(
        context,
        shape_size=100.0,
        ridge_width=5.0,
        ridge_style="integrated",
    )

    compose.execute(
        context,
    )

    root = ET.parse(
        output,
    ).getroot()

    outer = root.find(
        '{http://www.w3.org/2000/svg}polygon[@id="shape-boundary"]',
    )
    inner = root.find(
        '{http://www.w3.org/2000/svg}polygon[@id="ridge-inner-boundary"]',
    )

    assert outer is not None
    assert inner is not None

    outer_points = _polygon_points(
        outer,
    )
    inner_points = _polygon_points(
        inner,
    )

    assert len(inner_points) == len(outer_points)

    registered_inset = 0.05

    for index in range(len(outer_points)):
        outer_start = outer_points[index]
        outer_end = outer_points[(index + 1) % len(outer_points)]

        inner_start = inner_points[index]
        inner_end = inner_points[(index + 1) % len(inner_points)]

        outer_dx = outer_end[0] - outer_start[0]
        outer_dy = outer_end[1] - outer_start[1]

        inner_dx = inner_end[0] - inner_start[0]
        inner_dy = inner_end[1] - inner_start[1]

        cross_product = outer_dx * inner_dy - outer_dy * inner_dx

        assert cross_product == pytest.approx(
            0.0,
            abs=1.0e-9,
        )

        outer_length = math.hypot(
            outer_dx,
            outer_dy,
        )

        distance = (
            abs(
                outer_dx * (inner_start[1] - outer_start[1])
                - outer_dy * (inner_start[0] - outer_start[0])
            )
            / outer_length
        )

        assert distance == pytest.approx(
            registered_inset,
        )


def test_compose_polygon_ridge_style_preserves_registered_boundaries(
    tmp_path: Path,
) -> None:
    """
    Polygon ridge style does not change registered ridge geometry.

    Integrated and separate construction use identical outer and inner
    registered boundaries. Style affects later physical component
    partitioning rather than registered Shape geometry.
    """

    boundaries_by_style: dict[
        str,
        tuple[
            tuple[tuple[float, float], ...],
            tuple[tuple[float, float], ...],
        ],
    ] = {}

    for ridge_style in (
        "integrated",
        "separate",
    ):
        structure_input = tmp_path / f"structure-{ridge_style}.svg"
        output = tmp_path / f"composition-{ridge_style}.svg"

        _write_registered_polygon_structure(
            structure_input,
            number_of_sides=6,
            rotation=30.0,
        )

        context = Mock(
            spec=StageContext,
        )
        _configure_compose_inputs(
            context,
            structure=structure_input,
        )
        _configure_compose_outputs(
            context,
            composition=output,
        )

        _configure_shape_resolver(
            context,
            shape_size=100.0,
            ridge_width=5.0,
            ridge_style=ridge_style,
        )

        compose.execute(
            context,
        )

        root = ET.parse(
            output,
        ).getroot()

        outer = root.find(
            '{http://www.w3.org/2000/svg}polygon[@id="shape-boundary"]',
        )
        inner = root.find(
            '{http://www.w3.org/2000/svg}polygon[@id="ridge-inner-boundary"]',
        )

        assert outer is not None
        assert inner is not None

        boundaries_by_style[ridge_style] = (
            _polygon_points(
                outer,
            ),
            _polygon_points(
                inner,
            ),
        )

    integrated = boundaries_by_style["integrated"]
    separate = boundaries_by_style["separate"]

    for integrated_boundary, separate_boundary in zip(
        integrated,
        separate,
        strict=True,
    ):
        for integrated_point, separate_point in zip(
            integrated_boundary,
            separate_boundary,
            strict=True,
        ):
            assert integrated_point == pytest.approx(
                separate_point,
            )


# =========================================================
# Compose stage registration
# =========================================================


def test_shape_registers_compose_stage_implementation() -> None:
    """
    Shape contributes its compose implementation through its stage package.

    Registration uses logical model and stage identities rather than numeric
    stage IDs or engine-specific orchestration.
    """

    registry = Mock()

    stages.register_stage_implementations(
        registry,
    )

    assert (
        call(
            "shape",
            "compose",
            compose.execute,
        )
        in registry.register.call_args_list
    )


def test_engine_bootstrap_discovers_shape_compose_implementation() -> None:
    """
    Normal engine bootstrap discovers the executable Shape compose stage.

    Shape participates in generic model stage discovery without requiring the
    engine to know about the Shape model explicitly.
    """

    registry = build_stage_registry()

    implementation = registry.get(
        "shape",
        "compose",
    )

    assert implementation is compose.execute


def test_zero_outer_ridge_width_preserves_structure_without_ridge(
    tmp_path: Path,
) -> None:
    """
    Zero outer-ridge width produces no registered ridge partition.

    Ridge existence is determined solely by shape_outer_ridge_width.
    Composition therefore preserves the structural Shape boundary without
    introducing a ridge inner boundary when the configured width is zero.
    """

    structure_path = tmp_path / "structure.svg"
    composition_path = tmp_path / "composition.svg"

    _write_registered_polygon_structure(
        structure_path,
        number_of_sides=8,
        rotation=22.5,
    )

    compose._compose_ridge(
        structure_path,
        composition_path,
        shape_size=100.0,
        ridge_width=0.0,
    )

    root = ET.parse(
        composition_path,
    ).getroot()

    shape_boundary = root.find(
        ".//*[@id='shape-boundary']",
    )
    ridge_inner_boundary = root.find(
        ".//*[@id='ridge-inner-boundary']",
    )

    assert shape_boundary is not None
    assert ridge_inner_boundary is None


def test_negative_outer_ridge_width_is_rejected(
    tmp_path: Path,
) -> None:
    """
    Negative outer-ridge width is invalid Shape geometry.

    Ridge width is a nonnegative physical dimension and must be rejected
    before registered ridge geometry is produced.
    """

    structure_path = tmp_path / "structure.svg"
    composition_path = tmp_path / "composition.svg"

    _write_registered_polygon_structure(
        structure_path,
        number_of_sides=8,
        rotation=22.5,
    )

    with pytest.raises(
        ValueError,
        match="ridge",
    ):
        compose._compose_ridge(
            structure_path,
            composition_path,
            shape_size=100.0,
            ridge_width=-1.0,
        )

    assert not composition_path.exists()


def test_compose_manifest_preserves_registered_artwork_membership(
    tmp_path: Path,
) -> None:
    """
    Shape composition persists incorporated Artwork component membership.

    Dynamic Artwork membership comes from the producer manifest and is
    retained explicitly so downstream stages never discover components by
    scanning directories.
    """

    artwork_dir = tmp_path / "artwork"
    artwork_dir.mkdir()

    artwork_manifest = artwork_dir / "products.json"
    _write_vector_manifest(
        artwork_manifest,
    )

    structure_input = tmp_path / "structure.svg"
    composition_output = tmp_path / "composition.svg"
    manifest_output = tmp_path / "shape-products.json"

    _write_registered_structure(
        structure_input,
    )

    context = Mock(
        spec=StageContext,
    )

    inputs = {
        "structure.structure": structure_input,
        "artwork.vector.manifest": artwork_manifest,
    }
    context.input.side_effect = inputs.__getitem__

    outputs = {
        "composition": composition_output,
        "manifest": manifest_output,
    }
    context.output.side_effect = outputs.__getitem__

    _configure_shape_resolver(
        context,
    )

    compose.execute(
        context,
    )

    manifest = json.loads(
        manifest_output.read_text(
            encoding="utf-8",
        )
    )

    assert manifest["artwork"]["components"] == [
        {
            "index": 1,
            "path": "white.svg",
            "name": "white",
            "color": {
                "r": 255,
                "g": 255,
                "b": 255,
                "a": 255,
            },
        },
        {
            "index": 2,
            "path": "black.svg",
            "name": "black",
            "color": {
                "r": 0,
                "g": 0,
                "b": 0,
                "a": 255,
            },
        },
    ]


def test_compose_manifest_records_one_common_artwork_transform(
    tmp_path: Path,
) -> None:
    """
    Shape composition persists one common transformation for Artwork.

    The transformation belongs to the registered Artwork collection rather
    than to individual components so their producer-established registration
    cannot diverge downstream.
    """

    artwork_dir = tmp_path / "artwork"
    artwork_dir.mkdir()

    artwork_manifest = artwork_dir / "products.json"
    _write_vector_manifest(
        artwork_manifest,
    )

    structure_input = tmp_path / "structure.svg"
    composition_output = tmp_path / "composition.svg"
    manifest_output = tmp_path / "shape-products.json"

    _write_registered_structure(
        structure_input,
    )

    context = Mock(
        spec=StageContext,
    )

    inputs = {
        "structure.structure": structure_input,
        "artwork.vector.manifest": artwork_manifest,
    }
    context.input.side_effect = inputs.__getitem__

    outputs = {
        "composition": composition_output,
        "manifest": manifest_output,
    }
    context.output.side_effect = outputs.__getitem__

    _configure_shape_resolver(
        context,
    )

    compose.execute(
        context,
    )

    manifest = json.loads(
        manifest_output.read_text(
            encoding="utf-8",
        )
    )

    artwork = compose.load_registered_artwork(
        artwork_manifest,
    )
    expected = compose.fit_registered_artwork_to_shape(
        artwork,
        composition=composition_output,
    )

    assert manifest["artwork"]["transform"] == {
        "scale": expected.scale,
        "translate_x": expected.translate_x,
        "translate_y": expected.translate_y,
    }

    assert all("transform" not in component for component in manifest["artwork"]["components"])
