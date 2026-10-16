"""
Tests for the artwork extrusion stage.

These tests characterize the storage boundary between the build engine
and the extrusion-stage implementation.

The extrusion stage must consume only the paths supplied through
StageContext. Dynamic STL products are stage-local products whose
locations are determined by the declared extrusion manifest.

"""
# File: tests/model/artwork/test_svg_processing.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from lowkey_artifact_builder.config import Resolver, get_resolver
from lowkey_artifact_builder.model.models.artwork.stages import extrude

pytestmark = pytest.mark.slow

# ----------------------------------------------------------------
# helpers
# ----------------------------------------------------------------


class StubResolver:
    """

    Minimal Resolver-compatible object for extrusion-stage tests.

    """

    def __init__(
        self,
        values: dict[str, Any],
        *,
        colors: dict[str, Any] | None = None,
    ) -> None:
        self._values = values

        self.colors = colors or {}

    def __call__(
        self,
        name: str,
    ) -> Any:
        return self._values[name]

    def configured_names(
        self,
    ) -> frozenset[str]:
        """

        Return configuration names explicitly supplied to this resolver.

        """

        return frozenset(
            self._values,
        )


class StubContext:
    """

    Minimal StageContext-compatible object for extrusion-stage tests.

    """

    def __init__(
        self,
        *,
        inputs: dict[str, Path],
        outputs: dict[str, Path],
        resolver: Resolver | StubResolver,
    ) -> None:
        self._inputs = inputs

        self._outputs = outputs

        self.resolver = resolver

    def input(
        self,
        name: str,
    ) -> Path:
        return self._inputs[name]

    def output(
        self,
        name: str,
    ) -> Path:
        return self._outputs[name]


def _resolver(
    tmp_path: Path,
    **overrides: Any,
) -> Resolver:
    resolver = get_resolver(
        "test-artifact",
        model="artwork",
        project_root=tmp_path,
    )

    return resolver.with_values(
        overrides,
        provenance="test",
    )


def _product(
    *,
    index: int,
    path: str,
    artifact_color_index: int,
    artifact_rgb: tuple[int, int, int],
) -> dict[str, Any]:
    """
    Return one registered vector product.

    Registered vector products preserve Artifact-color identity and geometry.
    Physical printer-color assignment belongs to downstream packaging.
    """

    return {
        "index": index,
        "path": path,
        "artifact_color": {
            "index": artifact_color_index,
            "rgb": _color(
                *artifact_rgb,
            ),
        },
    }


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

    Return physical X/Y/Z bounds from an ASCII STL product.

    """

    coordinates: list[
        tuple[
            float,
            float,
            float,
        ]
    ] = []

    for line in path.read_text(
        encoding="utf-8",
    ).splitlines():
        stripped = line.strip()

        if not stripped.startswith(
            "vertex ",
        ):
            continue

        _, x, y, z = stripped.split()

        coordinates.append(
            (
                float(x),
                float(y),
                float(z),
            )
        )

    assert coordinates

    xs = [point[0] for point in coordinates]

    ys = [point[1] for point in coordinates]

    zs = [point[2] for point in coordinates]

    return (
        min(xs),
        max(xs),
        min(ys),
        max(ys),
        min(zs),
        max(zs),
    )


def _color(
    red: int,
    green: int,
    blue: int,
) -> dict[str, int]:
    """

    Return a manifest RGB color.

    """

    return {
        "red": red,
        "green": green,
        "blue": blue,
    }


# ----------------------------------------------------------------
# Tests
# ----------------------------------------------------------------


def test_native_svg_envelope_bounds_include_registration_transform(
    tmp_path: Path,
) -> None:
    """
    Native Vector may register authored SVG geometry through an
    outer group transform.

    Extrude must measure the registered envelope, not the original
    untransformed path coordinates.
    """

    envelope = tmp_path / "envelope.svg"

    envelope.write_text(
        """
        <svg xmlns="http://www.w3.org/2000/svg"
             viewBox="0 0 100 100">
            <g transform="translate(-20,-10)">
                <path d="M 30 20 H 70 V 60 H 30 Z"/>
            </g>
        </svg>
        """,
        encoding="utf-8",
    )

    assert extrude._envelope_bounds(envelope) == pytest.approx((10.0, 10.0, 50.0, 50.0))


def test_native_svg_envelope_points_include_nested_transforms(
    tmp_path: Path,
) -> None:
    """
    Nested SVG transforms must be composed in document order.

    Registration must preserve the actual polygon vertices used for
    physical sizing and Loop attachment.
    """

    envelope = tmp_path / "envelope.svg"

    envelope.write_text(
        """
        <svg xmlns="http://www.w3.org/2000/svg"
             viewBox="0 0 100 100">
            <g transform="translate(10,5)">
                <g transform="scale(2)">
                    <path d="M 0 0 H 20 V 10 H 0 Z"/>
                </g>
            </g>
        </svg>
        """,
        encoding="utf-8",
    )

    points = extrude._envelope_path_points(envelope)

    assert len(points) == 4

    expected = (
        (10.0, 5.0),
        (50.0, 5.0),
        (50.0, 25.0),
        (10.0, 25.0),
    )

    for actual, expected_point in zip(points, expected, strict=True):
        assert actual == pytest.approx(expected_point)

    assert extrude._envelope_bounds(envelope) == pytest.approx((10.0, 5.0, 50.0, 25.0))


def test_native_svg_envelope_without_transform_preserves_bounds(
    tmp_path: Path,
) -> None:
    """
    Adding native transform support must not change ordinary
    registered envelopes produced by the existing PNG workflow.
    """

    envelope = tmp_path / "envelope.svg"

    envelope.write_text(
        """
        <svg xmlns="http://www.w3.org/2000/svg"
             viewBox="0 0 100 100">
            <path d="M 10 15 H 70 V 55 H 10 Z"/>
        </svg>
        """,
        encoding="utf-8",
    )

    assert extrude._envelope_bounds(envelope) == pytest.approx((10.0, 15.0, 70.0, 55.0))


def test_native_svg_extrude_preserves_transformed_layer_registration(
    tmp_path: Path,
) -> None:
    """
    Native SVG group transforms survive physical extrusion.

    Two registered color layers must occupy adjacent physical regions
    after OpenSCAD imports their transformed SVG geometry.
    """

    vector_directory = tmp_path / "vector"
    vector_directory.mkdir(parents=True, exist_ok=True)

    envelope = vector_directory / "envelope.svg"
    envelope.write_text(
        """
        <svg xmlns="http://www.w3.org/2000/svg"
             viewBox="0 0 100 100">
            <g transform="translate(-10,-5)">
                <path d="M 20 15 H 80 V 45 H 20 Z"/>
            </g>
        </svg>
        """,
        encoding="utf-8",
    )

    first_svg = vector_directory / "color-1.svg"
    first_svg.write_text(
        """
        <svg xmlns="http://www.w3.org/2000/svg"
             viewBox="0 0 100 100">
            <g transform="translate(-10,-10)">
                <g transform="scale(2)">
                    <path d="M 10 10 H 25 V 25 H 10 Z"/>
                </g>
            </g>
        </svg>
        """,
        encoding="utf-8",
    )

    second_svg = vector_directory / "color-2.svg"
    second_svg.write_text(
        """
        <svg xmlns="http://www.w3.org/2000/svg"
             viewBox="0 0 100 100">
            <g transform="translate(-10,-5)">
                <path d="M 50 15 H 80 V 45 H 50 Z"/>
            </g>
        </svg>
        """,
        encoding="utf-8",
    )

    vector_manifest = vector_directory / "products.json"
    vector_manifest.write_text(
        json.dumps(
            {
                "registered_extent": 100,
                "envelope": envelope.name,
                "products": [
                    _product(
                        index=1,
                        path=first_svg.name,
                        artifact_color_index=1,
                        artifact_rgb=(255, 0, 0),
                    ),
                    _product(
                        index=2,
                        path=second_svg.name,
                        artifact_color_index=2,
                        artifact_rgb=(0, 0, 255),
                    ),
                ],
            }
        ),
        encoding="utf-8",
    )

    extrude_manifest = tmp_path / "extrude" / "products.json"

    context = StubContext(
        inputs={
            "artwork.vector.manifest": vector_manifest,
        },
        outputs={
            "manifest": extrude_manifest,
        },
        resolver=_resolver(
            tmp_path,
            artwork_size=120.0,
            artwork_raise=1.5,
            artwork_base_raise=0.0,
            artwork_outer_ridge_width=0.0,
            loop_inner_diameter=0.0,
        ),
    )

    # Deliberately use real OpenSCAD rendering.
    extrude.execute(context)  # type: ignore[arg-type]

    first_bounds = _stl_bounds(extrude_manifest.parent / "color-1.stl")
    second_bounds = _stl_bounds(extrude_manifest.parent / "color-2.stl")

    # Registered envelope:
    # X = 10..70, Y = 10..40.
    # Physical size 120 gives scale 2.
    #
    # Layer 1: X = -60..0, Y = -30..30.
    # Layer 2: X = 0..60, Y = -30..30.

    assert first_bounds == pytest.approx(
        (-60.0, 0.0, -30.0, 30.0, 0.0, 1.5),
        abs=0.01,
    )

    assert second_bounds == pytest.approx(
        (0.0, 60.0, -30.0, 30.0, 0.0, 1.5),
        abs=0.01,
    )

    assert first_bounds[1] == pytest.approx(
        second_bounds[0],
        abs=0.01,
    )


def test_native_svg_extrude_preserves_evenodd_hole(
    tmp_path: Path,
) -> None:
    """
    Native SVG even-odd fill produces a physical through-hole.

    Inspect the actual OpenSCAD STL top surface rather than SVG
    markup or STL bounds alone.
    """

    vector_directory = tmp_path / "vector"
    vector_directory.mkdir(parents=True, exist_ok=True)

    envelope = vector_directory / "envelope.svg"
    envelope.write_text(
        """
        <svg xmlns="http://www.w3.org/2000/svg"
             viewBox="0 0 100 100">
            <path d="M 0 0 H 100 V 100 H 0 Z"/>
        </svg>
        """,
        encoding="utf-8",
    )

    layer = vector_directory / "color-1.svg"
    layer.write_text(
        """
        <svg xmlns="http://www.w3.org/2000/svg"
             viewBox="0 0 100 100">
            <g transform="translate(10,10)">
                <path
                    d="M 0 0 H 80 V 80 H 0 Z
                       M 30 30 H 50 V 50 H 30 Z"
                    fill="#ff0000"
                    fill-rule="evenodd"
                />
            </g>
        </svg>
        """,
        encoding="utf-8",
    )

    vector_manifest = vector_directory / "products.json"
    vector_manifest.write_text(
        json.dumps(
            {
                "registered_extent": 100,
                "envelope": envelope.name,
                "products": [
                    _product(
                        index=1,
                        path=layer.name,
                        artifact_color_index=1,
                        artifact_rgb=(255, 0, 0),
                    ),
                ],
            }
        ),
        encoding="utf-8",
    )

    extrude_manifest = tmp_path / "extrude" / "products.json"

    context = StubContext(
        inputs={"artwork.vector.manifest": vector_manifest},
        outputs={"manifest": extrude_manifest},
        resolver=_resolver(
            tmp_path,
            artwork_size=100.0,
            artwork_raise=1.5,
            artwork_base_raise=0.0,
            artwork_outer_ridge_width=0.0,
            loop_inner_diameter=0.0,
        ),
    )

    # Real OpenSCAD extrusion; no renderer mocking.
    extrude.execute(context)  # type: ignore[arg-type]

    stl = extrude_manifest.parent / "color-1.stl"

    assert stl.is_file()

    assert _stl_bounds(stl) == pytest.approx(
        (-40.0, 40.0, -40.0, 40.0, 0.0, 1.5),
        abs=0.01,
    )

    vertices = []
    triangles = []

    for line in stl.read_text(encoding="utf-8").splitlines():
        fields = line.strip().split()

        if fields[:1] != ["vertex"]:
            continue

        vertices.append(tuple(float(value) for value in fields[1:]))

        if len(vertices) == 3:
            triangles.append(tuple(vertices))
            vertices = []

    assert triangles

    def top_surface_contains(x: float, y: float) -> bool:
        """
        Check whether a point lies on any top-surface triangle.
        """

        for triangle in triangles:
            if not all(abs(vertex[2] - 1.5) < 0.01 for vertex in triangle):
                continue

            a, b, c = triangle

            def cross(
                p: tuple[float, float, float],
                q: tuple[float, float, float],
            ) -> float:
                return (q[0] - p[0]) * (y - p[1]) - (q[1] - p[1]) * (x - p[0])

            values = (
                cross(a, b),
                cross(b, c),
                cross(c, a),
            )

            if min(values) >= -1e-6 or max(values) <= 1e-6:
                return True

        return False

    # Solid material remains outside the interior cutout.
    assert top_surface_contains(30.0, 0.0)

    # The central square is empty through the extrusion.
    assert not top_surface_contains(0.0, 0.0)


def test_native_svg_extrude_preserves_asymmetric_y_orientation(
    tmp_path: Path,
) -> None:
    """
    Native SVG geometry preserves its vertical orientation in physical space.

    SVG Y increases downward, while OpenSCAD Y increases upward.
    An asymmetric upper-left feature must therefore occupy positive
    physical Y, not appear mirrored below the origin.
    """

    vector_directory = tmp_path / "vector"
    vector_directory.mkdir(parents=True, exist_ok=True)

    envelope = vector_directory / "envelope.svg"
    envelope.write_text(
        """
        <svg xmlns="http://www.w3.org/2000/svg"
             viewBox="0 0 100 100">
            <path d="M 0 0 H 100 V 100 H 0 Z"/>
        </svg>
        """,
        encoding="utf-8",
    )

    layer = vector_directory / "color-1.svg"
    layer.write_text(
        """
        <svg xmlns="http://www.w3.org/2000/svg"
             viewBox="0 0 100 100">
            <g transform="translate(10,10)">
                <path d="M 0 0 H 30 V 20 H 0 Z"/>
            </g>
        </svg>
        """,
        encoding="utf-8",
    )

    vector_manifest = vector_directory / "products.json"
    vector_manifest.write_text(
        json.dumps(
            {
                "registered_extent": 100,
                "envelope": envelope.name,
                "products": [
                    _product(
                        index=1,
                        path=layer.name,
                        artifact_color_index=1,
                        artifact_rgb=(255, 0, 0),
                    ),
                ],
            }
        ),
        encoding="utf-8",
    )

    extrude_manifest = tmp_path / "extrude" / "products.json"

    context = StubContext(
        inputs={"artwork.vector.manifest": vector_manifest},
        outputs={"manifest": extrude_manifest},
        resolver=_resolver(
            tmp_path,
            artwork_size=100.0,
            artwork_raise=1.5,
            artwork_base_raise=0.0,
            artwork_outer_ridge_width=0.0,
            loop_inner_diameter=0.0,
        ),
    )

    # Real OpenSCAD extrusion; no renderer mocking.
    extrude.execute(context)  # type: ignore[arg-type]

    bounds = _stl_bounds(extrude_manifest.parent / "color-1.stl")

    # Registered feature:
    # SVG X = 10..40, Y = 10..30.
    #
    # Physical coordinates:
    # X = -40..-10, Y = 20..40.
    # Z = 0..1.5.

    assert bounds == pytest.approx(
        (-40.0, -10.0, 20.0, 40.0, 0.0, 1.5),
        abs=0.01,
    )


def test_native_svg_extrude_preserves_nested_rotation_and_scale(
    tmp_path: Path,
) -> None:
    """
    Nested rotation, scaling, and translation preserve physical registration.

    The SVG geometry is asymmetric so incorrect transform composition
    cannot produce the same physical bounds.
    """

    vector_directory = tmp_path / "vector"
    vector_directory.mkdir(parents=True, exist_ok=True)

    envelope = vector_directory / "envelope.svg"
    envelope.write_text(
        """
        <svg xmlns="http://www.w3.org/2000/svg"
             viewBox="0 0 100 100">
            <path d="M 0 0 H 100 V 100 H 0 Z"/>
        </svg>
        """,
        encoding="utf-8",
    )

    layer = vector_directory / "color-1.svg"
    layer.write_text(
        """
        <svg xmlns="http://www.w3.org/2000/svg"
             viewBox="0 0 100 100">
            <g transform="translate(60,20)">
                <g transform="rotate(90)">
                    <g transform="scale(2,1)">
                        <path d="M 0 0 H 10 V 30 H 0 Z"/>
                    </g>
                </g>
            </g>
        </svg>
        """,
        encoding="utf-8",
    )

    vector_manifest = vector_directory / "products.json"
    vector_manifest.write_text(
        json.dumps(
            {
                "registered_extent": 100,
                "envelope": envelope.name,
                "products": [
                    _product(
                        index=1,
                        path=layer.name,
                        artifact_color_index=1,
                        artifact_rgb=(255, 0, 0),
                    ),
                ],
            }
        ),
        encoding="utf-8",
    )

    extrude_manifest = tmp_path / "extrude" / "products.json"

    context = StubContext(
        inputs={"artwork.vector.manifest": vector_manifest},
        outputs={"manifest": extrude_manifest},
        resolver=_resolver(
            tmp_path,
            artwork_size=100.0,
            artwork_raise=1.5,
            artwork_base_raise=0.0,
            artwork_outer_ridge_width=0.0,
            loop_inner_diameter=0.0,
        ),
    )

    extrude.execute(context)  # type: ignore[arg-type]

    bounds = _stl_bounds(extrude_manifest.parent / "color-1.stl")

    # Transform composition:
    # Scale:     X = 0..20, Y = 0..30
    # Rotate 90: X = -30..0, Y = 0..20
    # Translate: X = 30..60, Y = 20..40
    #
    # Physical coordinates after centering and Y inversion:
    # X = -20..10, Y = 10..30.

    assert bounds == pytest.approx(
        (-20.0, 10.0, 10.0, 30.0, 0.0, 1.5),
        abs=0.01,
    )


def test_native_svg_extrude_preserves_non_square_transformed_envelope(
    tmp_path: Path,
) -> None:
    """
    Native SVG dimensionalization uses the transformed occupied envelope.

    The maximum envelope dimension determines artwork_size, while the
    shorter dimension retains its proportional physical extent.
    """

    vector_directory = tmp_path / "vector"
    vector_directory.mkdir(parents=True, exist_ok=True)

    envelope = vector_directory / "envelope.svg"
    envelope.write_text(
        """
        <svg xmlns="http://www.w3.org/2000/svg"
             viewBox="0 0 200 200">
            <g transform="translate(20,30)">
                <path d="M 0 0 H 80 V 40 H 0 Z"/>
            </g>
        </svg>
        """,
        encoding="utf-8",
    )

    layer = vector_directory / "color-1.svg"
    layer.write_text(
        """
        <svg xmlns="http://www.w3.org/2000/svg"
             viewBox="0 0 200 200">
            <g transform="translate(20,30)">
                <path d="M 0 0 H 80 V 40 H 0 Z"/>
            </g>
        </svg>
        """,
        encoding="utf-8",
    )

    vector_manifest = vector_directory / "products.json"
    vector_manifest.write_text(
        json.dumps(
            {
                "registered_extent": 200,
                "envelope": envelope.name,
                "products": [
                    _product(
                        index=1,
                        path=layer.name,
                        artifact_color_index=1,
                        artifact_rgb=(255, 0, 0),
                    ),
                ],
            }
        ),
        encoding="utf-8",
    )

    extrude_manifest = tmp_path / "extrude" / "products.json"

    context = StubContext(
        inputs={"artwork.vector.manifest": vector_manifest},
        outputs={"manifest": extrude_manifest},
        resolver=_resolver(
            tmp_path,
            artwork_size=120.0,
            artwork_raise=2.0,
            artwork_base_raise=0.0,
            artwork_outer_ridge_width=0.0,
            loop_inner_diameter=0.0,
        ),
    )

    extrude.execute(context)  # type: ignore[arg-type]

    bounds = _stl_bounds(extrude_manifest.parent / "color-1.stl")

    # Registered envelope: X = 20..100, Y = 30..70.
    # Envelope dimensions: 80 x 40.
    # artwork_size = 120 -> scale = 1.5.
    # Physical dimensions: 120 x 60, centered at origin.

    assert bounds == pytest.approx(
        (-60.0, 60.0, -30.0, 30.0, 0.0, 2.0),
        abs=0.01,
    )


def test_native_svg_extrude_preserves_disconnected_regions(
    tmp_path: Path,
) -> None:
    """
    Disconnected native SVG regions remain disconnected after extrusion.

    Both filled regions must survive, and no material may bridge the gap.
    """

    vector_directory = tmp_path / "vector"
    vector_directory.mkdir(parents=True, exist_ok=True)

    envelope = vector_directory / "envelope.svg"
    envelope.write_text(
        """
        <svg xmlns="http://www.w3.org/2000/svg"
             viewBox="0 0 100 100">
            <path d="M 0 0 H 100 V 100 H 0 Z"/>
        </svg>
        """,
        encoding="utf-8",
    )

    layer = vector_directory / "color-1.svg"
    layer.write_text(
        """
        <svg xmlns="http://www.w3.org/2000/svg"
             viewBox="0 0 100 100">
            <g transform="translate(10,20)">
                <path d="M 0 0 H 20 V 40 H 0 Z"/>
                <path d="M 60 0 H 80 V 40 H 60 Z"/>
            </g>
        </svg>
        """,
        encoding="utf-8",
    )

    vector_manifest = vector_directory / "products.json"
    vector_manifest.write_text(
        json.dumps(
            {
                "registered_extent": 100,
                "envelope": envelope.name,
                "products": [
                    _product(
                        index=1,
                        path=layer.name,
                        artifact_color_index=1,
                        artifact_rgb=(255, 0, 0),
                    ),
                ],
            }
        ),
        encoding="utf-8",
    )

    extrude_manifest = tmp_path / "extrude" / "products.json"

    context = StubContext(
        inputs={"artwork.vector.manifest": vector_manifest},
        outputs={"manifest": extrude_manifest},
        resolver=_resolver(
            tmp_path,
            artwork_size=100.0,
            artwork_raise=1.5,
            artwork_base_raise=0.0,
            artwork_outer_ridge_width=0.0,
            loop_inner_diameter=0.0,
        ),
    )

    extrude.execute(context)  # type: ignore[arg-type]

    stl = extrude_manifest.parent / "color-1.stl"

    assert stl.is_file()

    assert _stl_bounds(stl) == pytest.approx(
        (-40.0, 40.0, -10.0, 30.0, 0.0, 1.5),
        abs=0.01,
    )

    triangles = []
    vertices = []

    for line in stl.read_text(encoding="utf-8").splitlines():
        fields = line.strip().split()

        if fields[:1] != ["vertex"]:
            continue

        vertices.append(tuple(float(value) for value in fields[1:]))

        if len(vertices) == 3:
            triangles.append(tuple(vertices))
            vertices = []

    assert triangles

    def top_surface_contains(x: float, y: float) -> bool:
        for triangle in triangles:
            if not all(abs(vertex[2] - 1.5) < 0.01 for vertex in triangle):
                continue

            a, b, c = triangle

            def cross(
                p: tuple[float, float, float],
                q: tuple[float, float, float],
            ) -> float:
                return (q[0] - p[0]) * (y - p[1]) - (q[1] - p[1]) * (x - p[0])

            values = (
                cross(a, b),
                cross(b, c),
                cross(c, a),
            )

            if min(values) >= -1e-6 or max(values) <= 1e-6:
                return True

        return False

    # Left and right regions contain material.
    assert top_surface_contains(-30.0, 0.0)
    assert top_surface_contains(30.0, 0.0)

    # The space between the regions remains empty.
    assert not top_surface_contains(0.0, 0.0)
