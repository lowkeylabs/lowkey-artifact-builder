"""
Tests for Shape inlaid physical extrusion.
"""
# File: tests/model/shape/test_inlaid_extrude.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from lowkey_artifact_builder.engine import StageContext
from lowkey_artifact_builder.model.models.shape.stages import extrude

# =========================================================
# Test support
# =========================================================


def _write_square_ridge_composition(
    path: Path,
) -> None:
    """
    Write registered square geometry containing an outer-ridge partition.

    The complete Shape is 1.0 x 1.0 registered units. The inner boundary is
    inset by 0.05 on every side, producing a 5 mm separate Outer Ridge on a
    100 mm Shape.
    """

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        """
<svg
    xmlns="http://www.w3.org/2000/svg"
    viewBox="-0.5 -0.5 1.0 1.0"
>
    <rect
        id="shape-boundary"
        x="-0.5"
        y="-0.5"
        width="1.0"
        height="1.0"
    />
    <rect
        id="ridge-inner-boundary"
        x="-0.45"
        y="-0.45"
        width="0.9"
        height="0.9"
    />
</svg>
""".strip(),
        encoding="utf-8",
    )


def _write_polygon_ridge_composition(
    path: Path,
) -> None:
    """
    Write registered polygon geometry containing an outer-ridge partition.

    The representative Shape uses concentric square polygons so the test
    exercises registered polygon extrusion without introducing unrelated
    polygon-area complexity.
    """

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        """
<svg
    xmlns="http://www.w3.org/2000/svg"
    viewBox="-0.5 -0.5 1.0 1.0"
>
    <polygon
        id="shape-boundary"
        points="-0.5,-0.5 0.5,-0.5 0.5,0.5 -0.5,0.5"
    />
    <polygon
        id="ridge-inner-boundary"
        points="-0.45,-0.45 0.45,-0.45 0.45,0.45 -0.45,0.45"
    />
</svg>
""".strip(),
        encoding="utf-8",
    )


def _write_artwork_fill_composition(
    path: Path,
) -> None:
    """
    Write representative registered Shape geometry for Artwork Fill extrusion.
    """

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        (
            '<svg xmlns="http://www.w3.org/2000/svg" '
            'viewBox="-0.5 -0.5 1 1">'
            '<circle id="shape-boundary" cx="0" cy="0" r="0.5"/>'
            "</svg>"
        ),
        encoding="utf-8",
    )


def _write_artwork_fill_manifest(
    path: Path,
) -> None:
    """
    Write representative persisted registered Artwork Fill geometry.
    """

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        json.dumps(
            {
                "composition": "composition.svg",
                "artwork": None,
                "artwork_fill": {
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
                },
            }
        ),
        encoding="utf-8",
    )


def _write_border_label_component(
    path: Path,
    *,
    element_id: str,
    d: str,
) -> None:
    """
    Write one persistent registered Border Label component.
    """

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        f"""
<svg
    xmlns="http://www.w3.org/2000/svg"
    viewBox="-0.5 -0.5 1.0 1.0"
>
    <path
        id="{element_id}"
        d="{d}"
    />
</svg>
""".strip(),
        encoding="utf-8",
    )


def _write_inner_ridge_composition(
    path: Path,
) -> None:
    """
    Write registered circle composition containing an Inner Ridge partition.

    The complete Shape boundary has radius 0.5. The representative Inner Ridge
    occupies the annulus between registered radii 0.35 and 0.40.
    """

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        """
<svg
    xmlns="http://www.w3.org/2000/svg"
    viewBox="-0.5 -0.5 1.0 1.0"
>
    <circle
        id="shape-boundary"
        cx="0.0"
        cy="0.0"
        r="0.5"
    />
    <circle
        id="inner-ridge-outer-boundary"
        cx="0.0"
        cy="0.0"
        r="0.40"
    />
    <circle
        id="inner-ridge-inner-boundary"
        cx="0.0"
        cy="0.0"
        r="0.35"
    />
</svg>
""".strip(),
        encoding="utf-8",
    )


def _write_artwork_composition(
    path: Path,
) -> None:
    """
    Write a registered circle composition for incorporated Artwork.

    No Shape-native surface partition is present. The incorporated Artwork
    supplied by the composition manifest provides the representative inlaid
    surface component.
    """

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        """
<svg
    xmlns="http://www.w3.org/2000/svg"
    viewBox="-0.5 -0.5 1.0 1.0"
>
    <circle
        id="shape-boundary"
        cx="0.0"
        cy="0.0"
        r="0.5"
    />
</svg>
""".strip(),
        encoding="utf-8",
    )


def _stl_face_triangles_at_z(
    path: Path,
    *,
    z: float,
) -> list[
    tuple[
        tuple[float, float],
        tuple[float, float],
        tuple[float, float],
    ]
]:
    """
    Return STL triangles lying completely in the requested Z plane.

    This exposes a physical component's triangulated top or bottom face
    without introducing a separate mesh or constructive-geometry dependency.
    """

    vertices: list[
        tuple[
            float,
            float,
            float,
        ]
    ] = []

    triangles: list[
        tuple[
            tuple[float, float],
            tuple[float, float],
            tuple[float, float],
        ]
    ] = []

    for line in path.read_text(
        encoding="utf-8",
    ).splitlines():
        fields = line.strip().split()

        if len(fields) != 4 or fields[0] != "vertex":
            continue

        vertices.append(
            (
                float(fields[1]),
                float(fields[2]),
                float(fields[3]),
            )
        )

        if len(vertices) != 3:
            continue

        if all(vertex[2] == pytest.approx(z) for vertex in vertices):
            triangles.append(
                (
                    (vertices[0][0], vertices[0][1]),
                    (vertices[1][0], vertices[1][1]),
                    (vertices[2][0], vertices[2][1]),
                )
            )

        vertices = []

    return triangles


def _triangle_area(
    triangle: tuple[
        tuple[float, float],
        tuple[float, float],
        tuple[float, float],
    ],
) -> float:
    """
    Return the absolute XY area of one triangle.
    """

    (x1, y1), (x2, y2), (x3, y3) = triangle

    return abs((x1 * (y2 - y3) + x2 * (y3 - y1) + x3 * (y1 - y2)) / 2.0)


def _stl_face_area(
    path: Path,
    *,
    z: float,
) -> float:
    """
    Return the triangulated STL face area at one Z plane.
    """

    return sum(
        _triangle_area(
            triangle,
        )
        for triangle in _stl_face_triangles_at_z(
            path,
            z=z,
        )
    )


def _write_artwork_composition_manifest(
    path: Path,
) -> None:
    """
    Write a composition manifest containing one incorporated Artwork component.

    The registered Artwork component occupies a 20 x 40 region inside a
    100 x 100 registered extent. The persisted transform places that region
    at the Shape origin while preserving its registered X/Y geometry.
    """

    component = path.parent / "color-1.svg"

    component.write_text(
        """
<svg
    xmlns="http://www.w3.org/2000/svg"
    width="100"
    height="100"
    viewBox="0 0 100 100"
>
    <rect
        x="10"
        y="20"
        width="20"
        height="40"
    />
</svg>
""".strip(),
        encoding="utf-8",
    )

    path.write_text(
        json.dumps(
            {
                "composition": "composition.svg",
                "artwork": {
                    "registered_extent": {
                        "width": 100.0,
                        "height": 100.0,
                    },
                    "transform": {
                        "scale": 0.01,
                        "translate_x": -0.20,
                        "translate_y": -0.40,
                    },
                    "components": [
                        {
                            "index": 1,
                            "path": "color-1.svg",
                            "artifact_color": {
                                "index": 1,
                                "rgb": {
                                    "red": 224,
                                    "green": 32,
                                    "blue": 32,
                                },
                            },
                        },
                    ],
                },
            }
        ),
        encoding="utf-8",
    )


def _write_ridge_composition(
    path: Path,
) -> None:
    """
    Write registered circle composition containing an outer-ridge partition.

    The complete Shape boundary has radius 0.5. A 5 mm ridge on a
    100 mm Shape has a registered inset of 0.05, giving the ridge an
    inner radius of 0.45.
    """

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        """
<svg
    xmlns="http://www.w3.org/2000/svg"
    viewBox="-0.5 -0.5 1.0 1.0"
>
    <circle
        id="shape-boundary"
        cx="0.0"
        cy="0.0"
        r="0.5"
    />
    <circle
        id="ridge-inner-boundary"
        cx="0.0"
        cy="0.0"
        r="0.45"
    />
</svg>
""".strip(),
        encoding="utf-8",
    )


def _write_composition_manifest(
    path: Path,
) -> None:
    """
    Write the registered-composition manifest consumed by Shape extrusion.
    """

    path.write_text(
        json.dumps(
            {
                "composition": "composition.svg",
                "artwork": None,
            }
        ),
        encoding="utf-8",
    )


def _configure_extrude_context_inputs(
    context: Mock,
    *,
    composition: Path,
    composition_manifest: Path,
) -> None:
    """
    Configure the declared Compose-stage inputs consumed by Shape Extrude.
    """

    context.input.side_effect = {
        "compose.composition": composition,
        "compose.manifest": composition_manifest,
    }.__getitem__


def _make_inlaid_extrude_resolver() -> Mock:
    """
    Create the minimal resolver for the representative inlaid Extrude seam.

    The positive outer-ridge raise is intentional. In raised construction it
    would produce a 3 mm ridge on a 2 mm base. Inlaid construction must retain
    that resolved value while dimensionalizing the ridge only through the
    complete 2 mm Shape thickness.
    """

    return Mock(
        side_effect={
            "shape_size": 100.0,
            "shape_base_raise": 2.0,
            "shape_raise_style": "inlaid",
            "shape_outer_ridge_raise": 1.0,
            "shape_outer_ridge_style": "separate",
            "shape_artwork_raise": 1.0,
            "shape_hole_diameter": 0.0,
            "shape_hole_position": 0,
            "shape_hole_edge_distance": 0.4,
            "shape_loop_inner_diameter": 0.0,
        }.__getitem__,
    )


def _read_manifest(
    path: Path,
) -> dict:
    """
    Read a Shape physical-component manifest.
    """

    return json.loads(
        path.read_text(
            encoding="utf-8",
        )
    )


def _stl_bounds(
    path: Path,
) -> tuple[
    float,
    float,
    float,
    float,
    float,
    float,
]:
    """
    Return X/Y/Z bounds from an ASCII STL produced by OpenSCAD.

    The tuple contains:

        min_x, max_x, min_y, max_y, min_z, max_z
    """

    vertices: list[
        tuple[
            float,
            float,
            float,
        ]
    ] = []

    for line in path.read_text(
        encoding="utf-8",
    ).splitlines():
        fields = line.strip().split()

        if len(fields) != 4 or fields[0] != "vertex":
            continue

        vertices.append(
            (
                float(fields[1]),
                float(fields[2]),
                float(fields[3]),
            )
        )

    if not vertices:
        raise AssertionError(
            f"STL contains no readable vertices: {path}",
        )

    xs = tuple(vertex[0] for vertex in vertices)
    ys = tuple(vertex[1] for vertex in vertices)
    zs = tuple(vertex[2] for vertex in vertices)

    return (
        min(xs),
        max(xs),
        min(ys),
        max(ys),
        min(zs),
        max(zs),
    )


# =========================================================
# Inlaid physical partition
# =========================================================


@pytest.mark.slow
def test_inlaid_outer_ridge_partitions_complete_shape_thickness(
    tmp_path: Path,
) -> None:
    """
    Inlaid dimensionalization partitions the complete Shape thickness.

    A representative 100 mm circle has:

        base thickness       = 2 mm
        outer-ridge raise    = +1 mm
        outer-ridge style    = separate
        Shape raise style    = inlaid

    The resolved +1 mm ridge raise retains its raised-style meaning but does
    not determine the inlaid ridge height.

    Instead, the registered outer-ridge partition is dimensionalized through
    the complete Shape thickness:

        base  -> 90 mm interior from Z=0 through Z=2
        ridge -> 100/90 mm perimeter from Z=0 through Z=2

    Base and ridge therefore remain adjacent, nonoverlapping physical
    components with their existing semantic identities, while the assembled
    Shape is flat at both Z=0 and Z=2.
    """

    composition = tmp_path / "composition.svg"
    composition_manifest = tmp_path / "composition-products.json"
    manifest = tmp_path / "products.json"

    _write_ridge_composition(
        composition,
    )
    _write_composition_manifest(
        composition_manifest,
    )

    context = Mock(
        spec=StageContext,
    )
    context.resolver = _make_inlaid_extrude_resolver()

    _configure_extrude_context_inputs(
        context,
        composition=composition,
        composition_manifest=composition_manifest,
    )

    context.output.return_value = manifest

    extrude.execute(
        context,
    )

    data = _read_manifest(
        manifest,
    )

    assert data["components"] == [
        {
            "name": "base",
            "path": "base.stl",
        },
        {
            "name": "ridge",
            "path": "ridge.stl",
        },
    ]

    base = manifest.parent / "base.stl"
    ridge = manifest.parent / "ridge.stl"

    assert base.is_file()
    assert ridge.is_file()

    base_bounds = _stl_bounds(
        base,
    )
    ridge_bounds = _stl_bounds(
        ridge,
    )

    assert base_bounds == pytest.approx(
        (
            -45.0,
            45.0,
            -45.0,
            45.0,
            0.0,
            2.0,
        )
    )

    assert ridge_bounds == pytest.approx(
        (
            -50.0,
            50.0,
            -50.0,
            50.0,
            0.0,
            2.0,
        )
    )


@pytest.mark.slow
def test_inlaid_outer_ridge_partitions_complete_shape_area(
    tmp_path: Path,
) -> None:
    """
    Inlaid Base and Ridge partition the complete Shape face.

    The representative registered circle has:

        complete radius = 50 mm
        base radius     = 45 mm
        ridge           = 45..50 mm annulus

    Both components span the complete 2 mm Shape thickness. Their planar
    partitions therefore reconstruct the complete 100 mm circle without
    duplicating its area.

    The same partition must be exposed at both Z=0 and Z=2.
    """

    composition = tmp_path / "composition.svg"
    composition_manifest = tmp_path / "composition-products.json"
    manifest = tmp_path / "products.json"

    _write_ridge_composition(
        composition,
    )
    _write_composition_manifest(
        composition_manifest,
    )

    context = Mock(
        spec=StageContext,
    )
    context.resolver = _make_inlaid_extrude_resolver()

    _configure_extrude_context_inputs(
        context,
        composition=composition,
        composition_manifest=composition_manifest,
    )

    context.output.return_value = manifest

    extrude.execute(
        context,
    )

    base = manifest.parent / "base.stl"
    ridge = manifest.parent / "ridge.stl"

    base_bottom_area = _stl_face_area(
        base,
        z=0.0,
    )
    base_top_area = _stl_face_area(
        base,
        z=2.0,
    )

    ridge_bottom_area = _stl_face_area(
        ridge,
        z=0.0,
    )
    ridge_top_area = _stl_face_area(
        ridge,
        z=2.0,
    )

    expected_base_area = pytest.approx(
        3.141592653589793 * 45.0**2,
        rel=0.001,
    )
    expected_complete_area = pytest.approx(
        3.141592653589793 * 50.0**2,
        rel=0.001,
    )

    assert base_bottom_area == expected_base_area
    assert base_top_area == expected_base_area

    assert base_bottom_area + ridge_bottom_area == expected_complete_area
    assert base_top_area + ridge_top_area == expected_complete_area

    assert base_bottom_area == pytest.approx(
        base_top_area,
    )
    assert ridge_bottom_area == pytest.approx(
        ridge_top_area,
    )


@pytest.mark.slow
def test_inlaid_incorporated_artwork_spans_complete_shape_thickness(
    tmp_path: Path,
) -> None:
    """
    Incorporated Artwork obeys Shape inlaid dimensionalization.

    A representative Shape has:

        base thickness       = 2 mm
        Artwork raise        = +1 mm
        Shape raise style    = inlaid

    Under raised construction, the Artwork raise would place the component
    above the Base from Z=2 through Z=3.

    Under inlaid construction, the resolved Artwork raise retains that
    raised-style meaning but does not determine physical Z placement.
    Incorporated Artwork instead spans the complete Shape thickness from
    Z=0 through Z=2.

    The Artwork retains its registered X/Y geometry and canonical semantic
    component identity.
    """

    composition = tmp_path / "composition.svg"
    composition_manifest = tmp_path / "composition-products.json"
    manifest = tmp_path / "products.json"

    _write_artwork_composition(
        composition,
    )
    _write_artwork_composition_manifest(
        composition_manifest,
    )

    context = Mock(
        spec=StageContext,
    )
    context.resolver = _make_inlaid_extrude_resolver()

    _configure_extrude_context_inputs(
        context,
        composition=composition,
        composition_manifest=composition_manifest,
    )

    context.output.return_value = manifest

    extrude.execute(
        context,
    )

    data = _read_manifest(
        manifest,
    )

    artwork_component = next(
        component for component in data["components"] if component["name"] == "artwork-1"
    )

    artwork = manifest.parent / artwork_component["path"]

    assert artwork.is_file()

    bounds = _stl_bounds(
        artwork,
    )

    assert bounds == pytest.approx(
        (
            -10.0,
            10.0,
            -20.0,
            20.0,
            0.0,
            2.0,
        ),
        abs=0.002,
    )


@pytest.mark.slow
def test_inlaid_incorporated_artwork_is_removed_from_base(
    tmp_path: Path,
) -> None:
    """
    Inlaid incorporated Artwork partitions the Base through full thickness.

    The representative registered Artwork occupies a 20 x 40 mm rectangle,
    centered within a circular Shape.

    Under inlaid dimensionalization, that Artwork region is removed from Base
    through the complete Shape thickness. Base and Artwork therefore form
    complementary physical regions whose union reconstructs the same complete
    Shape face as an otherwise identical Shape without incorporated Artwork.

    The same partition is exposed at both Z=0 and Z=2.
    """

    partitioned_directory = tmp_path / "partitioned"
    reference_directory = tmp_path / "reference"

    partitioned_composition = partitioned_directory / "composition.svg"
    partitioned_composition_manifest = partitioned_directory / "composition-products.json"
    partitioned_manifest = partitioned_directory / "products.json"

    _write_artwork_composition(
        partitioned_composition,
    )
    _write_artwork_composition_manifest(
        partitioned_composition_manifest,
    )

    partitioned_context = Mock(
        spec=StageContext,
    )
    partitioned_context.resolver = _make_inlaid_extrude_resolver()

    _configure_extrude_context_inputs(
        partitioned_context,
        composition=partitioned_composition,
        composition_manifest=partitioned_composition_manifest,
    )

    partitioned_context.output.return_value = partitioned_manifest

    extrude.execute(
        partitioned_context,
    )

    data = _read_manifest(
        partitioned_manifest,
    )

    artwork_component = next(
        component for component in data["components"] if component["name"] == "artwork-1"
    )

    base = partitioned_manifest.parent / "base.stl"
    artwork = partitioned_manifest.parent / artwork_component["path"]

    base_bottom_area = _stl_face_area(
        base,
        z=0.0,
    )
    base_top_area = _stl_face_area(
        base,
        z=2.0,
    )

    artwork_bottom_area = _stl_face_area(
        artwork,
        z=0.0,
    )
    artwork_top_area = _stl_face_area(
        artwork,
        z=2.0,
    )

    reference_composition = reference_directory / "composition.svg"
    reference_composition_manifest = reference_directory / "composition-products.json"
    reference_manifest = reference_directory / "products.json"

    _write_artwork_composition(
        reference_composition,
    )
    _write_composition_manifest(
        reference_composition_manifest,
    )

    reference_context = Mock(
        spec=StageContext,
    )
    reference_context.resolver = _make_inlaid_extrude_resolver()

    _configure_extrude_context_inputs(
        reference_context,
        composition=reference_composition,
        composition_manifest=reference_composition_manifest,
    )

    reference_context.output.return_value = reference_manifest

    extrude.execute(
        reference_context,
    )

    reference_base = reference_manifest.parent / "base.stl"

    reference_bottom_area = _stl_face_area(
        reference_base,
        z=0.0,
    )
    reference_top_area = _stl_face_area(
        reference_base,
        z=2.0,
    )

    expected_artwork_area = pytest.approx(
        20.0 * 40.0,
        rel=0.001,
    )

    assert artwork_bottom_area == expected_artwork_area
    assert artwork_top_area == expected_artwork_area

    assert base_bottom_area == pytest.approx(
        base_top_area,
        rel=0.001,
    )
    assert artwork_bottom_area == pytest.approx(
        artwork_top_area,
        rel=0.001,
    )

    assert base_bottom_area + artwork_bottom_area == pytest.approx(
        reference_bottom_area,
        rel=0.001,
    )
    assert base_top_area + artwork_top_area == pytest.approx(
        reference_top_area,
        rel=0.001,
    )


@pytest.mark.slow
def test_inlaid_inner_ridge_partitions_complete_shape_thickness(
    tmp_path: Path,
) -> None:
    """
    Inlaid Inner Ridge partitions the complete Shape thickness.

    The registered Inner Ridge retains its semantic X/Y annulus while inlaid
    dimensionalization makes it span the complete Shape thickness. Its occupied
    region is removed from Base so Base and Inner Ridge reconstruct the same
    physical Shape as an otherwise identical Shape without the Inner Ridge.
    """

    partitioned_directory = tmp_path / "partitioned"
    reference_directory = tmp_path / "reference"

    partitioned_composition = partitioned_directory / "composition.svg"
    partitioned_composition_manifest = partitioned_directory / "composition-products.json"
    partitioned_manifest = partitioned_directory / "products.json"

    _write_inner_ridge_composition(
        partitioned_composition,
    )
    _write_composition_manifest(
        partitioned_composition_manifest,
    )

    partitioned_context = Mock(
        spec=StageContext,
    )

    partitioned_context.resolver = Mock(
        side_effect={
            "shape_size": 100.0,
            "shape_base_raise": 2.0,
            "shape_raise_style": "inlaid",
            "shape_outer_ridge_raise": 1.0,
            "shape_outer_ridge_style": "separate",
            "shape_inner_ridge_raise": 1.0,
            "shape_hole_diameter": 0.0,
            "shape_hole_position": 0,
            "shape_hole_edge_distance": 0.4,
            "shape_loop_inner_diameter": 0.0,
        }.__getitem__,
    )

    _configure_extrude_context_inputs(
        partitioned_context,
        composition=partitioned_composition,
        composition_manifest=partitioned_composition_manifest,
    )

    partitioned_context.output.return_value = partitioned_manifest

    extrude.execute(
        partitioned_context,
    )

    data = _read_manifest(
        partitioned_manifest,
    )

    inner_ridge_component = next(
        component for component in data["components"] if component["name"] == "inner-ridge"
    )

    base = partitioned_manifest.parent / "base.stl"
    inner_ridge = partitioned_manifest.parent / inner_ridge_component["path"]

    assert _stl_bounds(
        inner_ridge,
    ) == pytest.approx(
        (
            -40.0,
            40.0,
            -40.0,
            40.0,
            0.0,
            2.0,
        ),
        abs=0.002,
    )

    reference_composition = reference_directory / "composition.svg"
    reference_composition_manifest = reference_directory / "composition-products.json"
    reference_manifest = reference_directory / "products.json"

    _write_artwork_composition(
        reference_composition,
    )
    _write_composition_manifest(
        reference_composition_manifest,
    )

    reference_context = Mock(
        spec=StageContext,
    )
    reference_context.resolver = _make_inlaid_extrude_resolver()

    _configure_extrude_context_inputs(
        reference_context,
        composition=reference_composition,
        composition_manifest=reference_composition_manifest,
    )

    reference_context.output.return_value = reference_manifest

    extrude.execute(
        reference_context,
    )

    reference_base = reference_manifest.parent / "base.stl"

    base_bottom_area = _stl_face_area(
        base,
        z=0.0,
    )
    base_top_area = _stl_face_area(
        base,
        z=2.0,
    )

    inner_ridge_bottom_area = _stl_face_area(
        inner_ridge,
        z=0.0,
    )
    inner_ridge_top_area = _stl_face_area(
        inner_ridge,
        z=2.0,
    )

    reference_bottom_area = _stl_face_area(
        reference_base,
        z=0.0,
    )
    reference_top_area = _stl_face_area(
        reference_base,
        z=2.0,
    )

    assert inner_ridge_bottom_area > 0.0
    assert inner_ridge_bottom_area == pytest.approx(
        inner_ridge_top_area,
        rel=0.001,
    )

    assert base_bottom_area + inner_ridge_bottom_area == pytest.approx(
        reference_bottom_area,
        rel=0.001,
    )
    assert base_top_area + inner_ridge_top_area == pytest.approx(
        reference_top_area,
        rel=0.001,
    )


@pytest.mark.slow
def test_inlaid_artwork_fill_spans_complete_shape_thickness(
    tmp_path: Path,
) -> None:
    """
    Inlaid Artwork Fill retains its registered X/Y partition while spanning
    the complete Shape thickness.

    The positive shape_artwork_fill_raise remains resolved configuration with
    its raised-style meaning, but does not determine the inlaid Z interval.
    """

    composition = tmp_path / "composition.svg"
    composition_manifest = tmp_path / "composition-products.json"
    manifest = tmp_path / "products.json"

    _write_artwork_fill_composition(
        composition,
    )
    _write_artwork_fill_manifest(
        composition_manifest,
    )

    context = Mock(
        spec=StageContext,
    )

    context.resolver = Mock(
        side_effect={
            "shape_size": 100.0,
            "shape_base_raise": 2.0,
            "shape_raise_style": "inlaid",
            "shape_outer_ridge_raise": 0.0,
            "shape_outer_ridge_style": "integrated",
            "shape_artwork_fill_raise": 0.6,
            "shape_hole_diameter": 0.0,
            "shape_loop_inner_diameter": 0.0,
        }.__getitem__,
    )

    _configure_extrude_context_inputs(
        context,
        composition=composition,
        composition_manifest=composition_manifest,
    )

    context.output.return_value = manifest

    extrude.execute(
        context,
    )

    data = _read_manifest(
        manifest,
    )

    artwork_fill_component = next(
        component for component in data["components"] if component["name"] == "artwork-fill"
    )

    artwork_fill = manifest.parent / artwork_fill_component["path"]

    assert artwork_fill.is_file()

    bounds = _stl_bounds(
        artwork_fill,
    )

    #
    # The registered fill occupies the 45 mm-radius Shape interior outside
    # the centered 60 x 50 mm Artwork envelope. Therefore its overall X/Y
    # bounds remain the 90 mm outer circle.
    #
    # Raised construction would occupy Z=2.0..2.6. Inlaid construction must
    # instead span the complete 2 mm Shape thickness.
    #

    assert bounds == pytest.approx(
        (
            -45.0,
            45.0,
            -45.0,
            45.0,
            0.0,
            2.0,
        ),
        abs=0.002,
    )


@pytest.mark.slow
def test_inlaid_border_label_spans_complete_shape_thickness(
    tmp_path: Path,
) -> None:
    """
    Inlaid Border Label preserves its registered physical X/Y geometry while
    spanning the complete Shape thickness.

    Raised and inlaid dimensionalization consume the same registered Border
    Label. Raise style may therefore change only its physical Z interval:

        raised -> Z=2..3
        inlaid -> Z=0..2

    The positive label raise remains resolved configuration with its
    raised-style meaning but does not determine the inlaid Z interval.
    """

    composition = tmp_path / "composition.svg"
    composition_manifest = tmp_path / "composition-products.json"

    _write_artwork_composition(
        composition,
    )

    top_border_label = tmp_path / "top-border-label.svg"

    _write_border_label_component(
        top_border_label,
        element_id="top-border-label",
        d=("M 0.10,-0.40 L 0.20,-0.40 L 0.20,-0.30 L 0.10,-0.30 Z"),
    )

    composition_manifest.write_text(
        json.dumps(
            {
                "composition": "composition.svg",
                "border_labels": {
                    "top": {
                        "path": top_border_label.name,
                    },
                    "bottom": None,
                },
                "artwork": None,
                "artwork_fill": None,
            }
        ),
        encoding="utf-8",
    )

    def render(
        *,
        shape_raise_style: str,
        output_directory: Path,
    ) -> tuple[
        float,
        float,
        float,
        float,
        float,
        float,
    ]:
        manifest = output_directory / "products.json"

        context = Mock(
            spec=StageContext,
        )

        context.resolver = Mock(
            side_effect={
                "shape_size": 100.0,
                "shape_base_raise": 2.0,
                "shape_raise_style": shape_raise_style,
                "shape_outer_ridge_raise": 0.0,
                "shape_outer_ridge_style": "integrated",
                "shape_top_border_label_raise": 1.0,
                "shape_hole_diameter": 0.0,
                "shape_loop_inner_diameter": 0.0,
            }.__getitem__,
        )

        _configure_extrude_context_inputs(
            context,
            composition=composition,
            composition_manifest=composition_manifest,
        )

        context.output.return_value = manifest

        extrude.execute(
            context,
        )

        data = _read_manifest(
            manifest,
        )

        component = next(
            component for component in data["components"] if component["name"] == "top-border-label"
        )

        stl = manifest.parent / component["path"]

        assert stl.is_file()

        return _stl_bounds(
            stl,
        )

    raised_bounds = render(
        shape_raise_style="raised",
        output_directory=tmp_path / "raised",
    )

    inlaid_bounds = render(
        shape_raise_style="inlaid",
        output_directory=tmp_path / "inlaid",
    )

    #
    # Raise style must not alter registered Border Label X/Y placement.
    #

    assert inlaid_bounds[:4] == pytest.approx(
        raised_bounds[:4],
        abs=0.01,
    )

    #
    # Existing raised dimensionalization places the 1 mm label above the
    # 2 mm structural base.
    #

    assert raised_bounds[4:] == pytest.approx(
        (
            2.0,
            3.0,
        ),
        abs=0.01,
    )

    #
    # Inlaid dimensionalization instead spans the complete Shape thickness.
    #

    assert inlaid_bounds[4:] == pytest.approx(
        (
            0.0,
            2.0,
        ),
        abs=0.01,
    )


@pytest.mark.slow
def test_inlaid_artwork_fill_is_removed_from_base(
    tmp_path: Path,
) -> None:
    """
    Inlaid Artwork Fill partitions the Base through the complete Shape
    thickness.

    Base and Artwork Fill are complementary physical regions whose union
    reconstructs the same complete Shape as an otherwise identical Shape
    without Artwork Fill.

    The same partition is exposed at both physical faces.
    """

    partitioned_directory = tmp_path / "partitioned"
    reference_directory = tmp_path / "reference"

    partitioned_composition = partitioned_directory / "composition.svg"
    partitioned_composition_manifest = partitioned_directory / "composition-products.json"
    partitioned_manifest = partitioned_directory / "products.json"

    _write_artwork_fill_composition(
        partitioned_composition,
    )
    _write_artwork_fill_manifest(
        partitioned_composition_manifest,
    )

    partitioned_context = Mock(
        spec=StageContext,
    )

    partitioned_context.resolver = Mock(
        side_effect={
            "shape_size": 100.0,
            "shape_base_raise": 2.0,
            "shape_raise_style": "inlaid",
            "shape_outer_ridge_raise": 0.0,
            "shape_outer_ridge_style": "integrated",
            "shape_artwork_fill_raise": 0.6,
            "shape_hole_diameter": 0.0,
            "shape_loop_inner_diameter": 0.0,
        }.__getitem__,
    )

    _configure_extrude_context_inputs(
        partitioned_context,
        composition=partitioned_composition,
        composition_manifest=partitioned_composition_manifest,
    )

    partitioned_context.output.return_value = partitioned_manifest

    extrude.execute(
        partitioned_context,
    )

    data = _read_manifest(
        partitioned_manifest,
    )

    artwork_fill_component = next(
        component for component in data["components"] if component["name"] == "artwork-fill"
    )

    base = partitioned_manifest.parent / "base.stl"
    artwork_fill = partitioned_manifest.parent / artwork_fill_component["path"]

    reference_composition = reference_directory / "composition.svg"
    reference_composition_manifest = reference_directory / "composition-products.json"
    reference_manifest = reference_directory / "products.json"

    _write_artwork_fill_composition(
        reference_composition,
    )
    _write_composition_manifest(
        reference_composition_manifest,
    )

    reference_context = Mock(
        spec=StageContext,
    )

    reference_context.resolver = Mock(
        side_effect={
            "shape_size": 100.0,
            "shape_base_raise": 2.0,
            "shape_raise_style": "inlaid",
            "shape_outer_ridge_raise": 0.0,
            "shape_outer_ridge_style": "integrated",
            "shape_hole_diameter": 0.0,
            "shape_loop_inner_diameter": 0.0,
        }.__getitem__,
    )

    _configure_extrude_context_inputs(
        reference_context,
        composition=reference_composition,
        composition_manifest=reference_composition_manifest,
    )

    reference_context.output.return_value = reference_manifest

    extrude.execute(
        reference_context,
    )

    reference_base = reference_manifest.parent / "base.stl"

    for z in (
        0.0,
        2.0,
    ):
        base_area = _stl_face_area(
            base,
            z=z,
        )
        artwork_fill_area = _stl_face_area(
            artwork_fill,
            z=z,
        )
        reference_area = _stl_face_area(
            reference_base,
            z=z,
        )

        assert artwork_fill_area > 0.0

        assert base_area + artwork_fill_area == pytest.approx(
            reference_area,
            rel=0.001,
        )


@pytest.mark.slow
def test_inlaid_border_label_is_removed_from_base(
    tmp_path: Path,
) -> None:
    """
    An inlaid Border Label partitions the Base through the complete Shape
    thickness.

    Base and Border Label are complementary physical regions whose union
    reconstructs the same complete Shape as an otherwise identical Shape
    without the label.

    The same partition is exposed at both physical faces.
    """

    partitioned_directory = tmp_path / "partitioned"
    reference_directory = tmp_path / "reference"

    partitioned_composition = partitioned_directory / "composition.svg"
    partitioned_composition_manifest = partitioned_directory / "composition-products.json"
    partitioned_manifest = partitioned_directory / "products.json"

    _write_artwork_composition(
        partitioned_composition,
    )

    top_border_label = partitioned_directory / "top-border-label.svg"

    _write_border_label_component(
        top_border_label,
        element_id="top-border-label",
        d=("M 0.10,-0.40 L 0.20,-0.40 L 0.20,-0.30 L 0.10,-0.30 Z"),
    )

    partitioned_composition_manifest.write_text(
        json.dumps(
            {
                "composition": "composition.svg",
                "border_labels": {
                    "top": {
                        "path": top_border_label.name,
                    },
                    "bottom": None,
                },
                "artwork": None,
                "artwork_fill": None,
            }
        ),
        encoding="utf-8",
    )

    partitioned_context = Mock(
        spec=StageContext,
    )

    partitioned_context.resolver = Mock(
        side_effect={
            "shape_size": 100.0,
            "shape_base_raise": 2.0,
            "shape_raise_style": "inlaid",
            "shape_outer_ridge_raise": 0.0,
            "shape_outer_ridge_style": "integrated",
            "shape_top_border_label_raise": 1.0,
            "shape_hole_diameter": 0.0,
            "shape_loop_inner_diameter": 0.0,
        }.__getitem__,
    )

    _configure_extrude_context_inputs(
        partitioned_context,
        composition=partitioned_composition,
        composition_manifest=partitioned_composition_manifest,
    )

    partitioned_context.output.return_value = partitioned_manifest

    extrude.execute(
        partitioned_context,
    )

    data = _read_manifest(
        partitioned_manifest,
    )

    border_label_component = next(
        component for component in data["components"] if component["name"] == "top-border-label"
    )

    base = partitioned_manifest.parent / "base.stl"
    border_label = partitioned_manifest.parent / border_label_component["path"]

    reference_composition = reference_directory / "composition.svg"
    reference_composition_manifest = reference_directory / "composition-products.json"
    reference_manifest = reference_directory / "products.json"

    _write_artwork_composition(
        reference_composition,
    )
    _write_composition_manifest(
        reference_composition_manifest,
    )

    reference_context = Mock(
        spec=StageContext,
    )

    reference_context.resolver = Mock(
        side_effect={
            "shape_size": 100.0,
            "shape_base_raise": 2.0,
            "shape_raise_style": "inlaid",
            "shape_outer_ridge_raise": 0.0,
            "shape_outer_ridge_style": "integrated",
            "shape_hole_diameter": 0.0,
            "shape_loop_inner_diameter": 0.0,
        }.__getitem__,
    )

    _configure_extrude_context_inputs(
        reference_context,
        composition=reference_composition,
        composition_manifest=reference_composition_manifest,
    )

    reference_context.output.return_value = reference_manifest

    extrude.execute(
        reference_context,
    )

    reference_base = reference_manifest.parent / "base.stl"

    for z in (
        0.0,
        2.0,
    ):
        base_area = _stl_face_area(
            base,
            z=z,
        )
        border_label_area = _stl_face_area(
            border_label,
            z=z,
        )
        reference_area = _stl_face_area(
            reference_base,
            z=z,
        )

        assert border_label_area > 0.0

        assert base_area + border_label_area == pytest.approx(
            reference_area,
            rel=0.001,
        )


@pytest.mark.slow
def test_inlaid_outer_ridge_and_artwork_form_one_complete_partition(
    tmp_path: Path,
) -> None:
    """
    Outer Ridge and incorporated Artwork compose into one inlaid partition.

    A representative circular Shape contains both:

        separate Outer Ridge -> 45..50 mm annulus
        incorporated Artwork -> 20 x 40 mm interior rectangle

    Under inlaid dimensionalization, Base, Ridge, and Artwork all span the
    complete Shape thickness and occupy complementary physical regions.

    Their union must reconstruct exactly one complete 100 mm circular Shape
    at both physical faces. In particular, the Artwork region must be removed
    from the Base even when Base construction is owned by the Outer Ridge path.
    """

    composition = tmp_path / "composition.svg"
    composition_manifest = tmp_path / "composition-products.json"
    manifest = tmp_path / "products.json"

    #
    # Reuse the registered Outer Ridge geometry and incorporated Artwork
    # manifest already exercised independently by this test module.
    #

    _write_ridge_composition(
        composition,
    )

    _write_artwork_composition_manifest(
        composition_manifest,
    )

    context = Mock(
        spec=StageContext,
    )
    context.resolver = _make_inlaid_extrude_resolver()

    _configure_extrude_context_inputs(
        context,
        composition=composition,
        composition_manifest=composition_manifest,
    )

    context.output.return_value = manifest

    extrude.execute(
        context,
    )

    data = _read_manifest(
        manifest,
    )

    components = {component["name"]: component for component in data["components"]}

    assert set(components) == {
        "base",
        "ridge",
        "artwork-1",
    }

    base = manifest.parent / components["base"]["path"]
    ridge = manifest.parent / components["ridge"]["path"]
    artwork = manifest.parent / components["artwork-1"]["path"]

    #
    # Every member of the inlaid partition spans the same complete physical
    # thickness.
    #

    for component in (
        base,
        ridge,
        artwork,
    ):
        bounds = _stl_bounds(
            component,
        )

        assert bounds[4:] == pytest.approx(
            (
                0.0,
                2.0,
            ),
            abs=0.002,
        )

    #
    # The three semantic components must form one nonoverlapping partition of
    # the complete circular Shape at both physical faces.
    #
    # This is deliberately an assembled-area assertion rather than separate
    # component-area expectations. Outer Ridge and Artwork already have
    # independent geometry tests above; this test owns their composition.
    #

    expected_complete_area = pytest.approx(
        3.141592653589793 * 50.0**2,
        rel=0.001,
    )

    for z in (
        0.0,
        2.0,
    ):
        base_area = _stl_face_area(
            base,
            z=z,
        )
        ridge_area = _stl_face_area(
            ridge,
            z=z,
        )
        artwork_area = _stl_face_area(
            artwork,
            z=z,
        )

        assert artwork_area > 0.0

        assert (base_area + ridge_area + artwork_area) == expected_complete_area


@pytest.mark.slow
@pytest.mark.parametrize(
    (
        "write_composition",
        "expected_base_bounds",
        "expected_ridge_bounds",
        "expected_complete_area",
    ),
    [
        (
            _write_square_ridge_composition,
            (
                -45.0,
                45.0,
                -45.0,
                45.0,
                0.0,
                2.0,
            ),
            (
                -50.0,
                50.0,
                -50.0,
                50.0,
                0.0,
                2.0,
            ),
            100.0 * 100.0,
        ),
        (
            _write_polygon_ridge_composition,
            (
                -45.0,
                45.0,
                -45.0,
                45.0,
                0.0,
                2.0,
            ),
            (
                -50.0,
                50.0,
                -50.0,
                50.0,
                0.0,
                2.0,
            ),
            100.0 * 100.0,
        ),
    ],
    ids=(
        "square",
        "polygon",
    ),
)
def test_inlaid_separate_ridge_geometry_partitions_complete_shape(
    tmp_path: Path,
    write_composition,
    expected_base_bounds: tuple[
        float,
        float,
        float,
        float,
        float,
        float,
    ],
    expected_ridge_bounds: tuple[
        float,
        float,
        float,
        float,
        float,
        float,
    ],
    expected_complete_area: float,
) -> None:
    """
    Alternate registered geometries obey the complete inlaid ridge contract.

    Square and polygon Shape paths each pass through their own registered Base
    builder. This acceptance seam verifies that both geometry-specific paths
    preserve the same inlaid physical contract already established for circle:

        Base and Ridge span the complete Shape thickness;
        Base and Ridge retain their registered X/Y partition;
        their union reconstructs exactly one complete Shape face;
        the same partition is exposed at Z=0 and Z=shape_base_raise.
    """

    composition = tmp_path / "composition.svg"
    composition_manifest = tmp_path / "composition-products.json"
    manifest = tmp_path / "products.json"

    write_composition(
        composition,
    )
    _write_composition_manifest(
        composition_manifest,
    )

    context = Mock(
        spec=StageContext,
    )
    context.resolver = _make_inlaid_extrude_resolver()

    _configure_extrude_context_inputs(
        context,
        composition=composition,
        composition_manifest=composition_manifest,
    )

    context.output.return_value = manifest

    extrude.execute(
        context,
    )

    data = _read_manifest(
        manifest,
    )

    assert data["components"] == [
        {
            "name": "base",
            "path": "base.stl",
        },
        {
            "name": "ridge",
            "path": "ridge.stl",
        },
    ]

    base = manifest.parent / "base.stl"
    ridge = manifest.parent / "ridge.stl"

    assert base.is_file()
    assert ridge.is_file()

    assert _stl_bounds(
        base,
    ) == pytest.approx(
        expected_base_bounds,
        abs=0.002,
    )

    assert _stl_bounds(
        ridge,
    ) == pytest.approx(
        expected_ridge_bounds,
        abs=0.002,
    )

    for z in (
        0.0,
        2.0,
    ):
        base_area = _stl_face_area(
            base,
            z=z,
        )
        ridge_area = _stl_face_area(
            ridge,
            z=z,
        )

        assert base_area > 0.0
        assert ridge_area > 0.0

        assert base_area + ridge_area == pytest.approx(
            expected_complete_area,
            rel=0.001,
        )
