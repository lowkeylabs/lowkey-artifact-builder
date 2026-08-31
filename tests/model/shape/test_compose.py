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
    context.has_input.side_effect = inputs.__contains__


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
    Write a representative registered Artwork vector product set.
    """

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    envelope = path.parent / "envelope.svg"

    envelope.write_text(
        (
            '<svg xmlns="http://www.w3.org/2000/svg" '
            'viewBox="0 0 16 16">'
            '<rect x="2" y="3" width="12" height="10"/>'
            "</svg>"
        ),
        encoding="utf-8",
    )

    white = path.parent / "white.svg"

    white.write_text(
        (
            '<svg xmlns="http://www.w3.org/2000/svg" '
            'viewBox="0 0 16 16">'
            '<rect x="2" y="3" width="6" height="10"/>'
            "</svg>"
        ),
        encoding="utf-8",
    )

    black = path.parent / "black.svg"

    black.write_text(
        (
            '<svg xmlns="http://www.w3.org/2000/svg" '
            'viewBox="0 0 16 16">'
            '<rect x="8" y="3" width="6" height="10"/>'
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
                        "name": "white",
                        "color": {
                            "red": 255,
                            "green": 255,
                            "blue": 255,
                        },
                    },
                    {
                        "index": 2,
                        "path": "black.svg",
                        "name": "black",
                        "color": {
                            "red": 0,
                            "green": 0,
                            "blue": 0,
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
        "red": 255,
        "green": 255,
        "blue": 255,
    }

    assert second.index == 2
    assert second.name == "black"
    assert second.color == {
        "red": 0,
        "green": 0,
        "blue": 0,
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
    assert artwork.registered_extent.height == 16.0


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


@pytest.mark.parametrize(
    (
        "interior",
        "expected_radius",
    ),
    [
        (
            ET.Element(
                "{http://www.w3.org/2000/svg}circle",
                {
                    "cx": "0.0",
                    "cy": "0.0",
                    "r": "0.42",
                },
            ),
            0.42,
        ),
        (
            ET.Element(
                "{http://www.w3.org/2000/svg}rect",
                {
                    "x": "-0.45",
                    "y": "-0.45",
                    "width": "0.9",
                    "height": "0.9",
                },
            ),
            0.45,
        ),
        (
            ET.Element(
                "{http://www.w3.org/2000/svg}polygon",
                {
                    "points": (
                        "0.0,-0.45 "
                        "0.389711,-0.225 "
                        "0.389711,0.225 "
                        "0.0,0.45 "
                        "-0.389711,0.225 "
                        "-0.389711,-0.225"
                    ),
                },
            ),
            pytest.approx(
                0.389711,
                abs=1.0e-6,
            ),
        ),
    ],
    ids=[
        "circle",
        "square",
        "polygon",
    ],
)
def test_artwork_placement_circle_uses_common_interior_boundary_computation(
    interior: ET.Element,
    expected_radius: float,
) -> None:
    """
    Every supported Shape interior uses one Artwork placement-circle contract.

    The placement region is the largest circle centered at the registered
    Shape origin that is wholly contained within the supplied interior
    boundary.
    """

    placement = compose.artwork_placement_circle(
        interior,
    )

    assert placement.center_x == pytest.approx(
        0.0,
        abs=1.0e-12,
    )
    assert placement.center_y == pytest.approx(
        0.0,
        abs=1.0e-12,
    )
    assert placement.radius == expected_radius


def test_artwork_placement_circle_uses_heptagon_ridge_inner_boundary(
    tmp_path: Path,
) -> None:
    """
    Polygon Artwork placement is derived from the actual ridge interior.

    A seven-sided Shape uses the same origin-centered placement-circle
    computation as every other supported Shape geometry.
    """

    structure = tmp_path / "structure.svg"
    composition = tmp_path / "composition.svg"

    _write_registered_polygon_structure(
        structure,
        number_of_sides=7,
        rotation=0.0,
    )

    compose._compose_ridge(
        structure,
        composition,
        shape_size=120.0,
        ridge_width=2.0,
    )

    interior = compose.registered_interior_region(
        composition,
    )

    placement = compose.artwork_placement_circle(
        interior,
    )

    polygon = compose._read_polygon_points(
        interior,
    )

    expected_radius = min(
        abs(start[0] * end[1] - start[1] * end[0])
        / math.hypot(
            end[0] - start[0],
            end[1] - start[1],
        )
        for start, end in zip(
            polygon,
            polygon[1:] + polygon[:1],
            strict=True,
        )
    )

    assert placement.center_x == pytest.approx(
        0.0,
        abs=1.0e-12,
    )
    assert placement.center_y == pytest.approx(
        0.0,
        abs=1.0e-12,
    )
    assert placement.radius == pytest.approx(
        expected_radius,
        abs=1.0e-12,
    )


def test_registered_artwork_fits_into_square_placement_circle(
    tmp_path: Path,
) -> None:
    """
    Registered Artwork fits within the square Shape's placement circle.

    The square interior determines the largest origin-centered placement
    circle, and the authoritative Artwork envelope is uniformly scaled to
    remain within that circle.
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

    expected_radius = 0.45
    envelope_radius = math.hypot(
        12.0 / 2.0,
        10.0 / 2.0,
    )
    expected_scale = expected_radius / envelope_radius

    assert placement.scale == pytest.approx(
        expected_scale,
    )
    assert placement.width == pytest.approx(
        12.0 * expected_scale,
    )
    assert placement.height == pytest.approx(
        10.0 * expected_scale,
    )


def test_square_shape_fit_maps_envelope_into_placement_circle(
    tmp_path: Path,
) -> None:
    """
    Square Shape fitting maps Artwork occupancy into its placement circle.

    Artwork coordinates remain independent of Shape coordinates, while the
    authoritative envelope is centered and uniformly fitted within the
    origin-centered placement region.
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
        ridge_width=13.0,
    )

    envelope.write_text(
        """
<svg
    xmlns="http://www.w3.org/2000/svg"
    width="137"
    height="137"
    viewBox="0 0 137 137"
>
    <rect
        x="11"
        y="20"
        width="72"
        height="40"
    />
</svg>
""".strip(),
        encoding="utf-8",
    )

    artwork = compose.RegisteredArtwork(
        registered_extent=compose.RegisteredExtent(
            width=137.0,
            height=137.0,
        ),
        envelope=envelope,
        components=(),
    )

    interior = compose.registered_interior_region(
        composition,
    )

    placement_circle = compose.artwork_placement_circle(
        interior,
    )

    bounds = compose.registered_artwork_envelope_bounds(
        artwork,
    )

    transform = compose.fit_registered_artwork_to_shape(
        artwork,
        composition=composition,
    )

    envelope_radius = math.hypot(
        bounds.width / 2.0,
        bounds.height / 2.0,
    )

    expected_scale = placement_circle.radius / envelope_radius

    assert placement_circle.radius == pytest.approx(
        0.37,
    )

    assert transform.scale == pytest.approx(
        expected_scale,
    )

    transformed_center_x = (bounds.x + bounds.width / 2.0) * transform.scale + transform.translate_x

    transformed_center_y = (
        bounds.y + bounds.height / 2.0
    ) * transform.scale + transform.translate_y

    assert transformed_center_x == pytest.approx(
        0.0,
    )
    assert transformed_center_y == pytest.approx(
        0.0,
    )


def test_registered_artwork_centers_within_square_placement_circle(
    tmp_path: Path,
) -> None:
    """
    Registered Artwork is centered on the Shape origin after fitting.

    Placement accounts for the Artwork envelope's position in its own
    registered coordinate system while centering the occupied envelope within
    the Shape's origin-centered placement circle.
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

    bounds = compose.registered_artwork_envelope_bounds(
        artwork,
    )

    transform = compose.fit_registered_artwork_to_shape(
        artwork,
        composition=composition,
    )

    transformed_center_x = (bounds.x + bounds.width / 2.0) * transform.scale + transform.translate_x

    transformed_center_y = (
        bounds.y + bounds.height / 2.0
    ) * transform.scale + transform.translate_y

    assert transformed_center_x == pytest.approx(
        0.0,
    )
    assert transformed_center_y == pytest.approx(
        0.0,
    )


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


def test_registered_artwork_centers_on_shape_origin_in_seven_sided_polygon(
    tmp_path: Path,
) -> None:
    """
    Artwork in a regular polygon is centered on the registered Shape origin.

    Odd-sided polygon geometry has an asymmetric axis-aligned envelope.
    That asymmetry must not shift incorporated Artwork away from the Shape
    origin.
    """

    structure = tmp_path / "structure.svg"
    composition = tmp_path / "composition.svg"
    envelope = tmp_path / "envelope.svg"

    _write_registered_polygon_structure(
        structure,
        number_of_sides=7,
        rotation=0.0,
    )

    compose._compose_ridge(
        structure,
        composition,
        shape_size=120.0,
        ridge_width=5.0,
    )

    envelope.write_text(
        (
            '<svg xmlns="http://www.w3.org/2000/svg" '
            'viewBox="0 0 100 100">'
            '<rect x="10" y="20" width="60" height="50"/>'
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

    bounds = compose.registered_artwork_envelope_bounds(
        artwork,
    )

    transform = compose.fit_registered_artwork_to_shape(
        artwork,
        composition=composition,
    )

    transformed_center_x = (bounds.x + bounds.width / 2.0) * transform.scale + transform.translate_x

    transformed_center_y = (
        bounds.y + bounds.height / 2.0
    ) * transform.scale + transform.translate_y

    assert transformed_center_x == pytest.approx(
        0.0,
        abs=1.0e-12,
    )

    assert transformed_center_y == pytest.approx(
        0.0,
        abs=1.0e-12,
    )


def test_registered_artwork_centered_in_seven_sided_polygon_remains_contained(
    tmp_path: Path,
) -> None:
    """
    Centered Artwork remains contained by a seven-sided polygon interior.

    Polygon fitting centers Artwork on the Shape origin and chooses a uniform
    scale that keeps every occupied envelope corner within the actual ridge
    inner boundary.
    """

    structure = tmp_path / "structure.svg"
    composition = tmp_path / "composition.svg"
    envelope = tmp_path / "envelope.svg"

    _write_registered_polygon_structure(
        structure,
        number_of_sides=7,
        rotation=0.0,
    )

    compose._compose_ridge(
        structure,
        composition,
        shape_size=120.0,
        ridge_width=5.0,
    )

    envelope.write_text(
        (
            '<svg xmlns="http://www.w3.org/2000/svg" '
            'viewBox="0 0 100 100">'
            '<rect x="10" y="20" width="60" height="50"/>'
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

    bounds = compose.registered_artwork_envelope_bounds(
        artwork,
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

    source_corners = (
        (
            bounds.x,
            bounds.y,
        ),
        (
            bounds.x + bounds.width,
            bounds.y,
        ),
        (
            bounds.x + bounds.width,
            bounds.y + bounds.height,
        ),
        (
            bounds.x,
            bounds.y + bounds.height,
        ),
    )

    transformed_corners = tuple(
        (
            x * transform.scale + transform.translate_x,
            y * transform.scale + transform.translate_y,
        )
        for x, y in source_corners
    )

    for corner in transformed_corners:
        assert _point_is_inside_convex_polygon(
            corner,
            polygon,
        )


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


def test_compose_stage_can_rewrite_existing_composition_after_size_change(
    tmp_path: Path,
) -> None:
    """
    Shape composition can rebuild into its existing persistent output.

    Changing shape_size may invalidate registered composition because physical
    ridge width is represented relative to Shape size. Re-executing the stage
    must replace its previous composition with valid registered Shape geometry.
    """

    structure_input = tmp_path / "structure.svg"
    composition_output = tmp_path / "composition.svg"

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
        composition=composition_output,
    )

    _configure_shape_resolver(
        context,
        shape_size=100.0,
        ridge_width=0.0,
    )

    compose.execute(
        context,
    )

    initial_root = ET.parse(
        composition_output,
    ).getroot()

    initial_boundary = initial_root.find(
        './/*[@id="shape-boundary"]',
    )

    assert initial_boundary is not None

    _configure_shape_resolver(
        context,
        shape_size=90.0,
        ridge_width=0.0,
    )

    compose.execute(
        context,
    )

    rebuilt_root = ET.parse(
        composition_output,
    ).getroot()

    rebuilt_boundary = rebuilt_root.find(
        './/*[@id="shape-boundary"]',
    )

    assert rebuilt_boundary is not None
    assert rebuilt_boundary.tag == "{http://www.w3.org/2000/svg}circle"
    assert float(rebuilt_boundary.get("r", "nan")) == pytest.approx(
        0.5,
    )


def test_compose_serialization_restores_svg_default_namespace(
    tmp_path: Path,
) -> None:
    """
    Shape composition owns the serialization of its persistent SVG product.

    ElementTree namespace registration is process-global. Composition must
    therefore establish the SVG default namespace when it serializes rather
    than relying on namespace state established when its module was imported.
    """

    structure_input = tmp_path / "structure.svg"
    composition_output = tmp_path / "composition.svg"

    _write_registered_structure(
        structure_input,
    )

    #
    # Simulate another XML subsystem changing ElementTree's
    # process-global namespace registration after compose was
    # imported.
    #

    ET.register_namespace(
        "",
        "urn:lowkey:test",
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
        composition=composition_output,
    )

    _configure_shape_resolver(
        context,
        shape_size=90.0,
        ridge_width=0.0,
    )

    compose.execute(
        context,
    )

    serialized = composition_output.read_text(
        encoding="utf-8",
    )

    assert '<svg xmlns="http://www.w3.org/2000/svg"' in serialized


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
    ]

    context.has_input.assert_called_once_with(
        "artwork.vector.manifest",
    )

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


def test_composition_manifest_preserves_artwork_registered_extent(
    tmp_path: Path,
) -> None:
    """
    Persistent Shape composition retains the registered coordinate extent
    needed to dimensionalize incorporated Artwork downstream.
    """

    component = tmp_path / "color-1.svg"
    envelope = tmp_path / "envelope.svg"
    manifest = tmp_path / "composition.json"

    component.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg"/>',
        encoding="utf-8",
    )
    envelope.write_text(
        (
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<rect x="10" y="20" width="20" height="40"/>'
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
        components=(
            compose.RegisteredArtworkComponent(
                index=1,
                path=component,
                name="color-1",
                color={
                    "hex": "#ff0000",
                },
            ),
        ),
    )

    transform = compose.RegisteredArtworkTransform(
        scale=0.01,
        width=0.2,
        height=0.4,
        translate_x=-0.5,
        translate_y=-0.5,
    )

    compose._write_composition_manifest(
        manifest,
        composition=tmp_path / "composition.svg",
        artwork=artwork,
        artwork_transform=transform,
    )

    document = json.loads(
        manifest.read_text(
            encoding="utf-8",
        )
    )

    assert document["artwork"]["registered_extent"] == {
        "width": 100.0,
        "height": 100.0,
    }


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
                "red": 255,
                "green": 255,
                "blue": 255,
            },
        },
        {
            "index": 2,
            "path": "black.svg",
            "name": "black",
            "color": {
                "red": 0,
                "green": 0,
                "blue": 0,
            },
        },
    ]

    for component in manifest["artwork"]["components"]:
        component_path = manifest_output.parent / component["path"]

        assert component_path.is_file()

    for component in manifest["artwork"]["components"]:
        relative_path = component["path"]

        assert (manifest_output.parent / relative_path).read_bytes() == (
            artwork_manifest.parent / relative_path
        ).read_bytes()


def test_compose_stage_places_artwork_from_manifest_envelope_occupancy(
    tmp_path: Path,
) -> None:
    """
    Shape composition places registered Artwork from its declared envelope.

    Individual Artwork components may have different occupied extents.
    The vector manifest's envelope is the authoritative occupied region for
    fitting the complete registered Artwork collection into the Shape.

    Composition must therefore center the envelope occupancy rather than the
    registered extent or any individual component.
    """

    artwork_dir = tmp_path / "artwork"
    artwork_dir.mkdir()

    artwork_manifest = artwork_dir / "products.json"
    envelope = artwork_dir / "envelope.svg"
    left_component = artwork_dir / "left.svg"
    right_component = artwork_dir / "right.svg"

    envelope.write_text(
        (
            '<svg xmlns="http://www.w3.org/2000/svg" '
            'viewBox="0 0 20 20">'
            '<rect x="3" y="2" width="12" height="16"/>'
            "</svg>"
        ),
        encoding="utf-8",
    )

    left_component.write_text(
        (
            '<svg xmlns="http://www.w3.org/2000/svg" '
            'viewBox="0 0 20 20">'
            '<rect x="4" y="5" width="3" height="8"/>'
            "</svg>"
        ),
        encoding="utf-8",
    )

    right_component.write_text(
        (
            '<svg xmlns="http://www.w3.org/2000/svg" '
            'viewBox="0 0 20 20">'
            '<rect x="10" y="7" width="4" height="6"/>'
            "</svg>"
        ),
        encoding="utf-8",
    )

    artwork_manifest.write_text(
        json.dumps(
            {
                "registered_extent": 20,
                "envelope": "envelope.svg",
                "products": [
                    {
                        "index": 1,
                        "path": "left.svg",
                        "name": "white",
                        "color": {
                            "red": 255,
                            "green": 255,
                            "blue": 255,
                        },
                    },
                    {
                        "index": 2,
                        "path": "right.svg",
                        "name": "black",
                        "color": {
                            "red": 0,
                            "green": 0,
                            "blue": 0,
                        },
                    },
                ],
            }
        ),
        encoding="utf-8",
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

    _configure_compose_inputs(
        context,
        structure=structure_input,
        artwork_manifest=artwork_manifest,
    )

    outputs = {
        "composition": composition_output,
        "manifest": manifest_output,
    }
    context.output.side_effect = outputs.__getitem__

    _configure_shape_resolver(
        context,
        shape_size=100.0,
        ridge_width=0.0,
    )

    compose.execute(
        context,
    )

    manifest = json.loads(
        manifest_output.read_text(
            encoding="utf-8",
        )
    )

    transform = manifest["artwork"]["transform"]

    #
    # Circular containment is limited by the envelope corner radius.
    #
    # Envelope:
    #
    #     x = 3..15     center x = 9
    #     y = 2..18     center y = 10
    #
    # Its half extents are 6 x 8. The envelope corner radius is therefore
    # 10, so fitting it inside the radius-0.5 Shape uses scale 0.05.
    #
    expected_scale = 0.5 / math.hypot(
        6.0,
        8.0,
    )

    assert transform["scale"] == pytest.approx(
        expected_scale,
    )

    #
    # The envelope center, not registered_extent center (10, 10), is mapped
    # onto the Shape origin.
    #
    # This distinction is deliberate: using registered_extent would produce
    # translate_x = -0.5 rather than the required -0.45.
    #
    assert transform["translate_x"] == pytest.approx(
        -(9.0 * expected_scale),
    )

    assert transform["translate_y"] == pytest.approx(
        -(10.0 * expected_scale),
    )

    #
    # Individual component extents do not participate in placement.
    #
    assert transform["translate_x"] != pytest.approx(
        -(5.5 * expected_scale),
    )

    assert transform["translate_x"] != pytest.approx(
        -(12.0 * expected_scale),
    )


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


def test_load_registered_artwork_accepts_artwork_vector_extent(
    tmp_path: Path,
) -> None:
    """
    Shape consumes the registered extent published by Artwork vectorization.

    Artwork publishes one scalar extent for its square common registered
    coordinate system. Shape must consume that producer contract directly
    rather than requiring a Shape-specific manifest representation.
    """

    manifest = tmp_path / "products.json"
    envelope = tmp_path / "envelope.svg"
    component = tmp_path / "color-0.svg"

    envelope.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg"><rect x="2" y="3" width="10" height="8"/></svg>',
        encoding="utf-8",
    )
    component.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg"/>',
        encoding="utf-8",
    )

    manifest.write_text(
        json.dumps(
            {
                "registered_extent": 16,
                "envelope": "envelope.svg",
                "products": [
                    {
                        "index": 0,
                        "path": "color-0.svg",
                        "name": "white",
                        "color": {
                            "red": 255,
                            "green": 255,
                            "blue": 255,
                        },
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    artwork = compose.load_registered_artwork(
        manifest,
    )

    assert artwork.registered_extent == compose.RegisteredExtent(
        width=16.0,
        height=16.0,
    )


def test_load_registered_artwork_preserves_artwork_vector_color_metadata(
    tmp_path: Path,
) -> None:
    """
    Shape preserves semantic color metadata published by Artwork vectorization.

    The consumer accepts Artwork's shared RGB representation without
    translating it into a Shape-specific color schema.
    """

    manifest = tmp_path / "products.json"
    envelope = tmp_path / "envelope.svg"
    component = tmp_path / "color-0.svg"

    envelope.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg"><rect x="0" y="0" width="16" height="16"/></svg>',
        encoding="utf-8",
    )
    component.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg"/>',
        encoding="utf-8",
    )

    manifest.write_text(
        json.dumps(
            {
                "registered_extent": 16,
                "envelope": "envelope.svg",
                "products": [
                    {
                        "index": 0,
                        "path": "color-0.svg",
                        "name": "gold",
                        "color": {
                            "red": 212,
                            "green": 175,
                            "blue": 55,
                        },
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    artwork = compose.load_registered_artwork(
        manifest,
    )

    assert artwork.components[0].name == "gold"
    assert artwork.components[0].color == {
        "red": 212,
        "green": 175,
        "blue": 55,
    }


def test_compose_stage_succeeds_without_registered_artwork(
    tmp_path: Path,
) -> None:
    """
    Registered Artwork is optional for Shape composition.

    Without a bound Artwork product dependency, Shape produces a valid
    registered composition whose manifest declares no incorporated Artwork.
    """

    structure = tmp_path / "structure.svg"
    composition = tmp_path / "composition.svg"

    _write_registered_structure(
        structure,
    )

    context = Mock(
        spec=StageContext,
    )

    _configure_compose_inputs(
        context,
        structure=structure,
    )

    manifest = _configure_compose_outputs(
        context,
        composition=composition,
    )

    _configure_shape_resolver(
        context,
    )

    compose.execute(
        context,
    )

    assert composition.exists()
    assert manifest.exists()

    data = json.loads(
        manifest.read_text(
            encoding="utf-8",
        )
    )

    assert data["composition"] == composition.name
    assert data["artwork"] is None

    context.has_input.assert_called_once_with(
        "artwork.vector.manifest",
    )


def test_registered_artwork_envelope_bounds_applies_group_translation(
    tmp_path: Path,
) -> None:
    """
    Registered Artwork envelope bounds include registration transforms.

    Artwork may publish occupied envelope geometry beneath a translated SVG
    group while retaining the common registered coordinate system. Shape
    interprets the resulting occupied bounds in that registered coordinate
    system.
    """

    envelope = tmp_path / "envelope.svg"

    envelope.write_text(
        """
        <svg xmlns="http://www.w3.org/2000/svg"
             viewBox="0 0 100 100">
          <g transform="translate(20 30)">
            <rect
                x="5"
                y="10"
                width="40"
                height="20"
            />
          </g>
        </svg>
        """,
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

    bounds = compose.registered_artwork_envelope_bounds(
        artwork,
    )

    assert bounds == compose.RegisteredBounds(
        x=25.0,
        y=40.0,
        width=40.0,
        height=20.0,
    )


def test_registered_artwork_envelope_bounds_supports_linear_path(
    tmp_path: Path,
) -> None:
    """
    Registered Artwork envelope bounds support producer linear path geometry.

    Artwork may publish occupied envelope geometry as an SVG path composed of
    absolute move and line commands. Shape interprets the path occupancy before
    applying its registration-group transform.
    """

    envelope = tmp_path / "envelope.svg"

    envelope.write_text(
        """
        <svg xmlns="http://www.w3.org/2000/svg"
             viewBox="0 0 100 100">
          <g transform="translate(-10 -20)">
            <path
                d="M 20 30 L 60 30 L 60 70 L 20 70 Z"
                fill="none"
                stroke="#000000"
            />
          </g>
        </svg>
        """,
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

    bounds = compose.registered_artwork_envelope_bounds(
        artwork,
    )

    assert bounds == compose.RegisteredBounds(
        x=10.0,
        y=10.0,
        width=40.0,
        height=40.0,
    )


@pytest.mark.slow
def test_compose_output_is_consumable_by_openscad(
    tmp_path: Path,
) -> None:
    """
    Persistent Shape composition is consumable by physical extrusion.

    Compose owns the persistent registered Shape representation. Its SVG
    serialization must therefore remain a valid manufacturing input for the
    downstream extrusion operation, not merely valid XML.
    """

    from lowkey_artifact_builder.model.models.shape.stages import (
        extrude,
        structure,
    )

    structure_path = tmp_path / "10-structure" / "structure.svg"

    composition_path = tmp_path / "20-compose" / "composition.svg"

    output_path = tmp_path / "30-extrude" / "base.stl"

    structure_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    composition_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    geometry = structure.create_circle_geometry()

    document = structure.create_circle_svg(
        geometry,
    )

    document.write(
        structure_path,
        encoding="unicode",
    )

    compose._compose_ridge(
        structure_path,
        composition_path,
        shape_size=90.0,
        ridge_width=0.0,
    )

    source = extrude._build_scad(
        composition_path,
        shape_size=90.0,
        shape_base_raise=2.0,
        shape_outer_ridge_raise=1.0,
        shape_outer_ridge_style="integrated",
    )

    extrude.render_stl_source(
        source,
        output_path,
    )

    assert output_path.is_file()


def test_shape_reads_vector_registered_envelope_in_common_coordinates(
    tmp_path: Path,
) -> None:
    """
    Shape interprets Artwork's registered envelope in producer coordinates.

    With identity raster registration, the common vector crop translates the
    prepared envelope into canonical Registered Artwork coordinates.

    The envelope, not individual Artwork layers or registered_extent, defines
    the occupied Artwork region used for placement.
    """

    from lowkey_artifact_builder.model.models.artwork.stages import vector

    prepared_envelope = tmp_path / "prepared-envelope.svg"
    registered_envelope = tmp_path / "envelope.svg"

    #
    # The prepared Artwork envelope occupies:
    #
    #     X = 30..70
    #     Y = 20..80
    #
    # in the original source coordinate system.
    #

    prepared_envelope.write_text(
        """
<svg
    xmlns="http://www.w3.org/2000/svg"
    width="100"
    height="100"
    viewBox="0 0 100 100"
>
    <rect
        x="30"
        y="20"
        width="40"
        height="60"
    />
</svg>
""".strip(),
        encoding="utf-8",
    )

    #
    # This fixture uses identity source-to-raster registration:
    #
    #     source X/Y == raster X/Y
    #
    # Artwork's common vector crop then begins at raster coordinate
    # (20, 10), establishing:
    #
    #     registered X = source X - 20
    #     registered Y = source Y - 10
    #
    # The registered envelope occupancy must consequently be:
    #
    #     X = 10..50
    #     Y = 10..70
    #

    registration = vector.RasterRegistration(
        x=0.0,
        y=0.0,
        size=100.0,
        pixels=100,
    )

    crop = vector.RasterCrop(
        x=20,
        y=10,
        size=80,
    )

    vector._register_envelope(
        prepared_envelope,
        registered_envelope,
        registration=registration,
        crop=crop,
    )

    assert registered_envelope.is_file()

    #
    # Consume the exact representation written by Artwork vectorization.
    #
    # Shape receives only the registered extent and envelope product. It
    # should not need to know how Artwork performed source-to-registered
    # coordinate conversion internally.
    #

    artwork = compose.RegisteredArtwork(
        registered_extent=compose.RegisteredExtent(
            width=80.0,
            height=80.0,
        ),
        envelope=registered_envelope,
        components=(),
    )

    bounds = compose.registered_artwork_envelope_bounds(
        artwork,
    )

    #
    # Shape observes the effective Registered Artwork coordinates rather
    # than the original source coordinates.
    #

    assert bounds.x == pytest.approx(10.0)
    assert bounds.y == pytest.approx(10.0)

    assert bounds.width == pytest.approx(40.0)
    assert bounds.height == pytest.approx(60.0)

    envelope_min_x = bounds.x
    envelope_max_x = bounds.x + bounds.width
    envelope_center_x = (envelope_min_x + envelope_max_x) / 2.0

    assert envelope_min_x == pytest.approx(10.0)
    assert envelope_max_x == pytest.approx(50.0)
    assert envelope_center_x == pytest.approx(30.0)

    envelope_min_y = bounds.y
    envelope_max_y = bounds.y + bounds.height
    envelope_center_y = (envelope_min_y + envelope_max_y) / 2.0

    assert envelope_min_y == pytest.approx(10.0)
    assert envelope_max_y == pytest.approx(70.0)
    assert envelope_center_y == pytest.approx(40.0)

    #
    # registered_extent defines the common coordinate system but does not
    # redefine Artwork occupancy. In particular, its center differs from
    # the occupied envelope center along X.
    #

    registered_center_x = artwork.registered_extent.width / 2.0

    assert registered_center_x == pytest.approx(40.0)

    assert envelope_center_x != pytest.approx(
        registered_center_x,
    )


@pytest.mark.parametrize(
    "interior",
    [
        ET.Element(
            "{http://www.w3.org/2000/svg}circle",
            {
                "cx": "0.0",
                "cy": "0.0",
                "r": "0.4",
            },
        ),
        ET.Element(
            "{http://www.w3.org/2000/svg}rect",
            {
                "x": "-0.4",
                "y": "-0.4",
                "width": "0.8",
                "height": "0.8",
            },
        ),
        ET.Element(
            "{http://www.w3.org/2000/svg}polygon",
            {
                "points": (
                    "0.0,-0.4618802153517006 "
                    "0.4,-0.2309401076758503 "
                    "0.4,0.2309401076758503 "
                    "0.0,0.4618802153517006 "
                    "-0.4,0.2309401076758503 "
                    "-0.4,-0.2309401076758503"
                ),
            },
        ),
    ],
    ids=[
        "circle",
        "square",
        "polygon",
    ],
)
def test_registered_artwork_fit_uses_common_placement_circle(
    tmp_path: Path,
    interior: ET.Element,
) -> None:
    """
    Artwork fitting depends on the common placement circle, not Shape geometry.

    Each supplied Shape interior has the same largest origin-centered placement
    circle with radius 0.4. The same authoritative Artwork envelope must
    therefore receive the same maximal uniform transform for every geometry.
    """

    composition = tmp_path / "composition.svg"
    envelope = tmp_path / "envelope.svg"

    root = ET.Element(
        "{http://www.w3.org/2000/svg}svg",
        {
            "viewBox": "-0.5 -0.5 1 1",
        },
    )

    interior.set(
        "id",
        "ridge-inner-boundary",
    )

    root.append(
        interior,
    )

    ET.ElementTree(
        root,
    ).write(
        composition,
        encoding="unicode",
    )

    envelope.write_text(
        (
            '<svg xmlns="http://www.w3.org/2000/svg" '
            'viewBox="0 0 100 100">'
            '<rect x="10" y="10" width="60" height="80"/>'
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

    transform = compose.fit_registered_artwork_to_shape(
        artwork,
        composition=composition,
    )

    #
    # The occupied Artwork envelope is 60 x 80. Relative to its center,
    # its corners are (+/-30, +/-40), giving a corner radius of 50.
    #
    # The common placement-circle radius is 0.4, so the largest uniform
    # scale that contains the authoritative envelope is:
    #
    #     0.4 / 50 = 0.008
    #
    expected_scale = 0.008

    assert transform.scale == pytest.approx(
        expected_scale,
        abs=1.0e-12,
    )

    assert transform.width == pytest.approx(
        60.0 * expected_scale,
        abs=1.0e-12,
    )

    assert transform.height == pytest.approx(
        80.0 * expected_scale,
        abs=1.0e-12,
    )

    bounds = compose.registered_artwork_envelope_bounds(
        artwork,
    )

    transformed_center_x = (bounds.x + bounds.width / 2.0) * transform.scale + transform.translate_x

    transformed_center_y = (
        bounds.y + bounds.height / 2.0
    ) * transform.scale + transform.translate_y

    assert transformed_center_x == pytest.approx(
        0.0,
        abs=1.0e-12,
    )

    assert transformed_center_y == pytest.approx(
        0.0,
        abs=1.0e-12,
    )
