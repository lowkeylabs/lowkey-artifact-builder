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
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Any

import pytest

from lowkey_artifact_builder.config import Resolver, get_resolver
from lowkey_artifact_builder.formats.threemf import CORE_NS, component_name
from lowkey_artifact_builder.model.models.artwork.stages import extrude, package

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


class _SVGPackageResolver:
    """Minimal packaging resolver with an explicit physical palette."""

    def __init__(
        self,
        printer_colors: list[str],
        colors: dict[str, dict[str, list[int]]],
    ) -> None:
        self._values: dict[str, Any] = {
            "printer_colors": printer_colors,
        }
        self.colors = colors

    def __call__(self, name: str) -> Any:
        return self._values[name]

    def has(self, name: str) -> bool:
        return name in self._values


class _SVGPackageContext:
    """StageContext-compatible packaging context."""

    def __init__(
        self,
        *,
        manifest: Path,
        artifact: Path,
        resolver: _SVGPackageResolver,
    ) -> None:
        self.artifact_id = "native-svg"
        self.resolver = resolver
        self._manifest = manifest
        self._artifact = artifact

    def input(self, name: str) -> Path:
        assert name == "extrude.manifest"
        return self._manifest

    def output(self, name: str) -> Path:
        assert name == "artifact"
        return self._artifact


def _native_svg_two_color_context(
    tmp_path: Path,
    **overrides: Any,
) -> tuple[StubContext, Path]:
    """
    Create two adjacent registered SVG color layers.

    Registered envelope: X=30..110, Y=40..80.
    Physical envelope: 100 x 50.

    Layer 1 occupies the left half; Layer 2 the right half.
    """
    context, manifest = _manufacturing_svg_context(
        tmp_path,
        **overrides,
    )

    vector_manifest = context.input("artwork.vector.manifest")
    vector_directory = vector_manifest.parent

    first = vector_directory / "color-1.svg"
    second = vector_directory / "color-2.svg"

    first.write_text(
        """
        <svg xmlns="http://www.w3.org/2000/svg"
             viewBox="0 0 200 200">
            <g transform="translate(30,40)">
                <path d="M 0 0 H 40 V 40 H 0 Z"/>
            </g>
        </svg>
        """,
        encoding="utf-8",
    )

    second.write_text(
        """
        <svg xmlns="http://www.w3.org/2000/svg"
             viewBox="0 0 200 200">
            <g transform="translate(30,40)">
                <path d="M 40 0 H 80 V 40 H 40 Z"/>
            </g>
        </svg>
        """,
        encoding="utf-8",
    )

    vector_manifest.write_text(
        json.dumps(
            {
                "registered_extent": 200,
                "envelope": "envelope.svg",
                "products": [
                    _product(
                        index=1,
                        path=first.name,
                        artifact_color_index=1,
                        artifact_rgb=(255, 0, 0),
                    ),
                    _product(
                        index=2,
                        path=second.name,
                        artifact_color_index=2,
                        artifact_rgb=(0, 0, 255),
                    ),
                ],
            }
        ),
        encoding="utf-8",
    )

    return context, manifest


def _package_native_svg(
    manifest: Path,
    artifact: Path,
    *,
    printer_colors: list[str],
    colors: dict[str, dict[str, list[int]]],
) -> None:
    """Package actual OpenSCAD STL products into a real 3MF."""
    context = _SVGPackageContext(
        manifest=manifest,
        artifact=artifact,
        resolver=_SVGPackageResolver(
            printer_colors,
            colors,
        ),
    )

    package.execute(context)  # type: ignore[arg-type]

    assert artifact.is_file()
    assert zipfile.is_zipfile(artifact)


def _native_svg_3mf_objects(
    artifact: Path,
) -> dict[str, tuple[str, tuple[float, ...]]]:
    """
    Inspect real 3MF component names, physical colors, and mesh vertices.

    Return each component's physical color and flattened XYZ coordinates.
    """
    with zipfile.ZipFile(artifact) as archive:
        root = ET.fromstring(archive.read("3D/3dmodel.model"))

    ns = f"{{{CORE_NS}}}"

    materials = {element.get("id"): element for element in root.findall(f".//{ns}basematerials")}

    result: dict[str, tuple[str, tuple[float, ...]]] = {}

    for obj in root.findall(f".//{ns}object"):
        name = obj.get("name")
        material_id = obj.get("pid")

        assert name is not None
        assert material_id is not None
        assert name not in result

        material = materials[material_id].find(f"{ns}base")
        assert material is not None

        color = material.get("displaycolor")
        assert color is not None

        coordinates: list[float] = []

        for vertex in obj.findall(f"./{ns}mesh/{ns}vertices/{ns}vertex"):
            coordinates.extend(float(vertex.get(axis, "nan")) for axis in ("x", "y", "z"))

        assert coordinates

        result[name] = (
            color,
            tuple(coordinates),
        )

    build_items = root.findall(f"./{ns}build/{ns}item")
    assert len(build_items) == len(result)

    return result


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


# ----------------------------------------------------------------
# Batch 2 — Native SVG manufacturing integration
# ----------------------------------------------------------------


def _manufacturing_svg_context(
    tmp_path: Path,
    **overrides: Any,
) -> tuple[StubContext, Path]:
    """
    Construct a transformed, non-square registered SVG for real extrusion.

    Authored envelope: X=0..80, Y=0..40.
    Registered envelope: X=30..110, Y=40..80.
    Physical envelope at artwork_size=100: 100 x 50, centered.
    """
    vector_directory = tmp_path / "vector"
    vector_directory.mkdir(parents=True, exist_ok=True)

    svg = """
        <svg xmlns="http://www.w3.org/2000/svg"
             viewBox="0 0 200 200">
            <g transform="translate(30,40)">
                <path d="M 0 0 H 80 V 40 H 0 Z"/>
            </g>
        </svg>
    """

    envelope = vector_directory / "envelope.svg"
    layer = vector_directory / "color-1.svg"

    envelope.write_text(svg, encoding="utf-8")
    layer.write_text(svg, encoding="utf-8")

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

    parameters: dict[str, Any] = {
        "artwork_size": 100.0,
        "artwork_raise": 1.5,
        "artwork_base_raise": 0.0,
        "artwork_outer_ridge_width": 0.0,
        "loop_inner_diameter": 0.0,
        "artwork_hole_diameter": 0.0,
    }
    parameters.update(overrides)

    context = StubContext(
        inputs={"artwork.vector.manifest": vector_manifest},
        outputs={"manifest": extrude_manifest},
        resolver=_resolver(tmp_path, **parameters),
    )

    return context, extrude_manifest


def _stl_top_surface_contains(
    path: Path,
    *,
    x: float,
    y: float,
    z: float,
) -> bool:
    """
    Determine whether an interior point belongs to an STL top surface.

    This checks actual rendered triangles, not just the STL bounding box.
    Test points should be strictly inside or outside expected regions,
    rather than exactly on their boundaries.
    """
    vertices: list[tuple[float, float, float]] = []

    for line in path.read_text(encoding="utf-8").splitlines():
        fields = line.strip().split()

        if fields[:1] != ["vertex"]:
            continue

        vertex = tuple(float(value) for value in fields[1:])
        assert len(vertex) == 3
        vertices.append(vertex)

    assert vertices
    assert len(vertices) % 3 == 0

    for index in range(0, len(vertices), 3):
        a, b, c = vertices[index : index + 3]

        if not all(abs(vertex[2] - z) < 0.01 for vertex in (a, b, c)):
            continue

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


@pytest.mark.slow
def test_native_svg_base_preserves_transformed_envelope_and_z_registration(
    tmp_path: Path,
) -> None:
    """
    Base uses the transformed native SVG envelope.

    The Base occupies Z=0..2, and Artwork occupies Z=2..3.5.
    Both retain the same physical XY registration.
    """
    context, manifest = _manufacturing_svg_context(
        tmp_path,
        artwork_base_raise=2.0,
    )

    extrude.execute(context)  # type: ignore[arg-type]

    base = manifest.parent / "base.stl"
    artwork = manifest.parent / "color-1.stl"

    assert base.is_file()
    assert artwork.is_file()

    assert _stl_bounds(base) == pytest.approx(
        (-50.0, 50.0, -25.0, 25.0, 0.0, 2.0),
        abs=0.01,
    )

    assert _stl_bounds(artwork) == pytest.approx(
        (-50.0, 50.0, -25.0, 25.0, 2.0, 3.5),
        abs=0.01,
    )


@pytest.mark.slow
def test_native_svg_loop_attaches_to_transformed_envelope(
    tmp_path: Path,
) -> None:
    """
    Loop attaches to the physical top edge of the registered SVG.

    The envelope's physical top is Y=25, not the viewBox top.
    The Loop inner radius is 3 and outer radius is 5, placing
    its center at Y=28 and its outer extent at Y=23..33.
    """
    context, manifest = _manufacturing_svg_context(
        tmp_path,
        artwork_base_raise=2.0,
        loop_inner_diameter=6.0,
        loop_width=2.0,
        loop_position=0,
        loop_raise=1.5,
    )

    extrude.execute(context)  # type: ignore[arg-type]

    loop = manifest.parent / "loop.stl"
    artwork = manifest.parent / "color-1.stl"

    assert loop.is_file()
    assert artwork.is_file()

    assert _stl_bounds(artwork) == pytest.approx(
        (-50.0, 50.0, -25.0, 25.0, 2.0, 3.5),
        abs=0.01,
    )

    assert _stl_bounds(loop) == pytest.approx(
        (-5.0, 5.0, 23.0, 33.0, 2.0, 3.5),
        abs=0.01,
    )

    # The annulus contains material outside its inner opening.
    assert _stl_top_surface_contains(loop, x=0.0, y=32.0, z=3.5)

    # The central opening remains empty.
    assert not _stl_top_surface_contains(loop, x=0.0, y=28.0, z=3.5)


@pytest.mark.slow
def test_native_svg_outer_ridge_preserves_registered_perimeter(
    tmp_path: Path,
) -> None:
    """
    Outer Ridge surrounds the transformed SVG envelope.

    The overall manufactured envelope remains 100 x 50.
    A ridge width of 4 reserves a uniform scale of 0.92
    for the Artwork proper, producing 92 x 46 geometry.
    """
    context, manifest = _manufacturing_svg_context(
        tmp_path,
        artwork_outer_ridge_width=4.0,
        artwork_outer_ridge_raise=2.0,
    )

    extrude.execute(context)  # type: ignore[arg-type]

    ridge = manifest.parent / "outer-ridge.stl"
    artwork = manifest.parent / "color-1.stl"

    assert ridge.is_file()
    assert artwork.is_file()

    assert _stl_bounds(ridge) == pytest.approx(
        (-50.0, 50.0, -25.0, 25.0, 0.0, 2.0),
        abs=0.01,
    )

    assert _stl_bounds(artwork) == pytest.approx(
        (-46.0, 46.0, -23.0, 23.0, 0.0, 1.5),
        abs=0.01,
    )

    # The ridge contains perimeter material.
    assert _stl_top_surface_contains(ridge, x=49.0, y=0.0, z=2.0)

    # The ridge interior is empty.
    assert not _stl_top_surface_contains(ridge, x=0.0, y=0.0, z=2.0)

    # The reduced Artwork occupies the ridge opening.
    assert _stl_top_surface_contains(artwork, x=0.0, y=0.0, z=1.5)


@pytest.mark.slow
def test_native_svg_configured_hole_subtracts_base_and_artwork(
    tmp_path: Path,
) -> None:
    """
    A configured Hole subtracts material from native SVG Artwork and Base.

    The physical envelope is 100 x 50, centered at the origin.
    With a 10 mm hole and 5 mm edge distance at the top,
    the hole center is (0, 15), radius 5.

    The Hole is independent of SVG-authored even-odd holes.
    """
    context, manifest = _manufacturing_svg_context(
        tmp_path,
        artwork_base_raise=2.0,
        artwork_hole_diameter=10.0,
        artwork_hole_edge_distance=5.0,
        artwork_hole_position=0,
    )

    extrude.execute(context)  # type: ignore[arg-type]

    base = manifest.parent / "base.stl"
    artwork = manifest.parent / "color-1.stl"

    assert base.is_file()
    assert artwork.is_file()

    assert _stl_bounds(base) == pytest.approx(
        (-50.0, 50.0, -25.0, 25.0, 0.0, 2.0),
        abs=0.01,
    )

    assert _stl_bounds(artwork) == pytest.approx(
        (-50.0, 50.0, -25.0, 25.0, 2.0, 3.5),
        abs=0.01,
    )

    # Material exists away from the configured Hole.
    assert _stl_top_surface_contains(base, x=20.0, y=0.0, z=2.0)
    assert _stl_top_surface_contains(artwork, x=20.0, y=0.0, z=3.5)

    # The configured Hole passes through both components.
    assert not _stl_top_surface_contains(base, x=0.0, y=15.0, z=2.0)
    assert not _stl_top_surface_contains(artwork, x=0.0, y=15.0, z=3.5)


def test_native_svg_multicolor_package_preserves_component_registration(
    tmp_path: Path,
) -> None:
    """
    Native SVG color layers retain physical registration in a real 3MF.

    Package must preserve the two independently extruded regions,
    canonical artwork-N identities, and assigned physical colors.
    """
    context, manifest = _native_svg_two_color_context(tmp_path)

    extrude.execute(context)  # type: ignore[arg-type]

    first_stl = manifest.parent / "color-1.stl"
    second_stl = manifest.parent / "color-2.stl"

    assert _stl_bounds(first_stl) == pytest.approx(
        (-50.0, 0.0, -25.0, 25.0, 0.0, 1.5),
        abs=0.01,
    )
    assert _stl_bounds(second_stl) == pytest.approx(
        (0.0, 50.0, -25.0, 25.0, 0.0, 1.5),
        abs=0.01,
    )

    artifact = tmp_path / "native-svg.3mf"

    _package_native_svg(
        manifest,
        artifact,
        printer_colors=["red", "blue"],
        colors={
            "red": {"rgb": [255, 0, 0]},
            "blue": {"rgb": [0, 0, 255]},
        },
    )

    objects = _native_svg_3mf_objects(artifact)

    first_name = component_name("native-svg", "artwork-1", "red")
    second_name = component_name("native-svg", "artwork-2", "blue")

    assert set(objects) == {first_name, second_name}
    assert objects[first_name][0] == "#FF0000"
    assert objects[second_name][0] == "#0000FF"

    def bounds(name: str) -> tuple[float, ...]:
        values = objects[name][1]
        xs = values[0::3]
        ys = values[1::3]
        zs = values[2::3]
        return (
            min(xs),
            max(xs),
            min(ys),
            max(ys),
            min(zs),
            max(zs),
        )

    assert bounds(first_name) == pytest.approx(
        (-50.0, 0.0, -25.0, 25.0, 0.0, 1.5),
        abs=0.01,
    )
    assert bounds(second_name) == pytest.approx(
        (0.0, 50.0, -25.0, 25.0, 0.0, 1.5),
        abs=0.01,
    )


@pytest.mark.slow
def test_native_svg_package_features_inherit_attached_artifact_colors(
    tmp_path: Path,
) -> None:
    """
    Base, Loop, and Outer Ridge inherit their attached Artwork colors.

    Logical attachment is established during extrusion; physical color
    assignment is performed only during packaging.
    """
    context, manifest = _native_svg_two_color_context(
        tmp_path,
        artwork_base_raise=2.0,
        artwork_outer_ridge_width=4.0,
        artwork_outer_ridge_raise=1.5,
        loop_inner_diameter=6.0,
        loop_width=2.0,
        loop_position=0,
        loop_raise=1.5,
    )

    extrude.execute(context)  # type: ignore[arg-type]

    data = json.loads(manifest.read_text(encoding="utf-8"))
    products = data["products"]

    layers = {
        product["artifact_color"]["index"]: product for product in products if "index" in product
    }

    assert set(layers) == {1, 2}

    features = {product["path"]: product for product in products if "index" not in product}

    assert set(features) == {
        "base.stl",
        "loop.stl",
        "outer-ridge.stl",
    }

    for product in features.values():
        assert product["artifact_color_index"] in layers

    artifact = tmp_path / "features.3mf"

    _package_native_svg(
        manifest,
        artifact,
        printer_colors=["red", "blue"],
        colors={
            "red": {"rgb": [255, 0, 0]},
            "blue": {"rgb": [0, 0, 255]},
        },
    )

    objects = _native_svg_3mf_objects(artifact)

    assignments = {
        1: ("red", "#FF0000"),
        2: ("blue", "#0000FF"),
    }

    expected_names = {
        component_name("native-svg", "artwork-1", "red"),
        component_name("native-svg", "artwork-2", "blue"),
    }

    for filename, product in features.items():
        index = product["artifact_color_index"]
        color_name, color_rgb = assignments[index]

        semantic_name = Path(filename).stem
        name = component_name("native-svg", semantic_name, color_name)

        expected_names.add(name)
        assert objects[name][0] == color_rgb

    assert set(objects) == expected_names

    # Every packaged component has actual mesh geometry.
    assert all(len(coordinates) >= 9 for _, coordinates in objects.values())


def test_native_svg_printer_reassignment_preserves_extrusion_geometry(
    tmp_path: Path,
) -> None:
    """
    Printer-color changes affect packaging, not native SVG extrusion.

    Two packages built from the same extrusion manifest must contain
    identical mesh geometry but different physical color assignments.
    """
    context, manifest = _native_svg_two_color_context(tmp_path)

    extrude.execute(context)  # type: ignore[arg-type]

    original_manifest = manifest.read_bytes()
    original_stls = {path.name: path.read_bytes() for path in manifest.parent.glob("*.stl")}

    first_artifact = tmp_path / "original.3mf"
    second_artifact = tmp_path / "reassigned.3mf"

    _package_native_svg(
        manifest,
        first_artifact,
        printer_colors=["red", "blue"],
        colors={
            "red": {"rgb": [255, 0, 0]},
            "blue": {"rgb": [0, 0, 255]},
        },
    )

    _package_native_svg(
        manifest,
        second_artifact,
        printer_colors=["warm-red", "deep-blue"],
        colors={
            "warm-red": {"rgb": [240, 0, 0]},
            "deep-blue": {"rgb": [0, 0, 240]},
        },
    )

    first = _native_svg_3mf_objects(first_artifact)
    second = _native_svg_3mf_objects(second_artifact)

    expected_first = {
        component_name("native-svg", "artwork-1", "red"): "#FF0000",
        component_name("native-svg", "artwork-2", "blue"): "#0000FF",
    }

    expected_second = {
        component_name("native-svg", "artwork-1", "warm-red"): "#F00000",
        component_name("native-svg", "artwork-2", "deep-blue"): "#0000F0",
    }

    assert {name: color for name, (color, _) in first.items()} == expected_first

    assert {name: color for name, (color, _) in second.items()} == expected_second

    # Compare physical meshes by stable semantic component identity.
    first_geometry = {
        name.split(" - ", 1)[0]: coordinates for name, (_, coordinates) in first.items()
    }

    second_geometry = {
        name.split(" - ", 1)[0]: coordinates for name, (_, coordinates) in second.items()
    }

    assert first_geometry == second_geometry

    # Packaging must not mutate upstream manufacturing products.
    assert manifest.read_bytes() == original_manifest

    assert {path.name: path.read_bytes() for path in manifest.parent.glob("*.stl")} == original_stls


# ----------------------------------------------------------------
# Batch 4 — Native SVG Prepare -> Raster -> Vector integration
# ----------------------------------------------------------------


def _native_svg_pipeline(
    tmp_path: Path,
    *,
    source_text: str,
    **parameters: Any,
) -> tuple[Path, Path, Path, Path]:
    """
    Execute the real native SVG registration pipeline.

    Prepare may render a temporary PNG to derive the envelope.
    Raster and Vector must preserve authored color geometry without
    bitmap tracing.

    Return source, prepared trace, raster manifest, vector manifest.
    """
    from lowkey_artifact_builder.model.models.artwork.stages import (
        prepare,
        raster,
        vector,
    )

    source = tmp_path / "source.svg"
    source.write_text(source_text, encoding="utf-8")

    prepared = tmp_path / "prepare"
    raster_dir = tmp_path / "raster"
    vector_dir = tmp_path / "vector"

    trace = prepared / "trace.svg"
    envelope = prepared / "envelope.svg"
    raster_manifest = raster_dir / "products.json"
    vector_manifest = vector_dir / "products.json"

    resolver = _resolver(
        tmp_path,
        artwork_envelope_mode="alpha",
        **parameters,
    )

    prepare.execute(
        StubContext(
            inputs={"source": source},
            outputs={
                "trace": trace,
                "envelope": envelope,
            },
            resolver=resolver,
        )  # type: ignore[arg-type]
    )

    raster.execute(
        StubContext(
            inputs={"prepare.trace": trace},
            outputs={"manifest": raster_manifest},
            resolver=resolver,
        )  # type: ignore[arg-type]
    )

    vector.execute(
        StubContext(
            inputs={
                "raster.manifest": raster_manifest,
                "prepare.envelope": envelope,
            },
            outputs={"manifest": vector_manifest},
            resolver=resolver,
        )  # type: ignore[arg-type]
    )

    return source, trace, raster_manifest, vector_manifest


def _native_svg_pipeline_source() -> str:
    """
    Three authored objects in two colors.

    The red objects are disconnected but share one Artifact color.
    Blue occupies the adjacent right-hand region.
    """
    return """
        <svg xmlns="http://www.w3.org/2000/svg"
             viewBox="0 0 200 200">
            <g transform="translate(30,40)">
                <g transform="scale(2)">
                    <path id="red-left"
                          d="M 0 0 H 10 V 20 H 0 Z"
                          fill="#ff0000"/>
                    <path id="red-middle"
                          d="M 10 0 H 20 V 20 H 10 Z"
                          style="fill:#ff0000"/>
                    <path id="blue-right"
                          d="M 20 0 H 40 V 20 H 20 Z"
                          fill="#0000ff"/>
                </g>
            </g>
        </svg>
    """


def _native_svg_layer_paths(
    manifest: Path,
) -> dict[int, Path]:
    """Resolve registered Vector products using their manifest paths."""
    data = json.loads(manifest.read_text(encoding="utf-8"))

    result: dict[int, Path] = {}

    for product in data["products"]:
        index = product["artifact_color"]["index"]
        result[index] = manifest.parent / product["path"]

    return result


def _native_svg_path_ids(path: Path) -> set[str]:
    """Read authored path identities from a registered SVG layer."""
    root = ET.parse(path).getroot()
    namespace = "{http://www.w3.org/2000/svg}"

    return {element.attrib["id"] for element in root.iter(f"{namespace}path")}


@pytest.mark.slow
def test_native_svg_pipeline_preserves_authored_geometry_and_colors(
    tmp_path: Path,
) -> None:
    """
    Prepare, Raster, and Vector preserve authored SVG color geometry.

    Two red objects share one Artifact-color identity. The blue
    object receives another. All authored paths survive unchanged.
    """
    source_text = _native_svg_pipeline_source()

    source, trace, raster_manifest, vector_manifest = _native_svg_pipeline(
        tmp_path,
        source_text=source_text,
    )

    # Prepare preserves the original SVG source verbatim.
    assert ET.canonicalize(
        trace.read_text(encoding="utf-8"),
        strip_text=True,
    ) == ET.canonicalize(
        source.read_text(encoding="utf-8"),
        strip_text=True,
    )

    raster_data = json.loads(raster_manifest.read_text(encoding="utf-8"))

    assert raster_data["representation"] == "native-svg"

    products = raster_data["products"]

    assert [product["object_id"] for product in products] == [
        "red-left",
        "red-middle",
        "blue-right",
    ]

    assert [product["artifact_color"]["index"] for product in products] == [1, 1, 2]

    assert products[0]["artifact_color"]["rgb"] == _color(255, 0, 0)
    assert products[1]["artifact_color"]["rgb"] == _color(255, 0, 0)
    assert products[2]["artifact_color"]["rgb"] == _color(0, 0, 255)

    vector_data = json.loads(vector_manifest.read_text(encoding="utf-8"))

    assert vector_data["registered_extent"] == 200
    assert len(vector_data["products"]) == 2

    layers = _native_svg_layer_paths(vector_manifest)
    assert set(layers) == {1, 2}

    assert _native_svg_path_ids(layers[1]) == {
        "red-left",
        "red-middle",
    }
    assert _native_svg_path_ids(layers[2]) == {
        "blue-right",
    }

    source_root = ET.parse(source).getroot()
    source_paths = {
        element.get("id"): element.get("d")
        for element in source_root.iter("{http://www.w3.org/2000/svg}path")
    }

    for layer in layers.values():
        root = ET.parse(layer).getroot()

        for element in root.iter("{http://www.w3.org/2000/svg}path"):
            object_id = element.get("id")
            assert object_id in source_paths
            assert element.get("d") == source_paths[object_id]

        # Authored nested transforms survive registration.
        transforms = [
            element.get("transform") for element in root.iter("{http://www.w3.org/2000/svg}g")
        ]

        assert "translate(30,40)" in transforms
        assert "scale(2)" in transforms


@pytest.mark.slow
def test_native_svg_pipeline_does_not_retrace_color_geometry(
    tmp_path: Path,
) -> None:
    """
    Native SVG Raster and Vector produce SVG-only registered products.

    Prepare may use temporary rasterization for envelope analysis,
    but authored color geometry must never become bitmap products.
    """
    source, trace, raster_manifest, vector_manifest = _native_svg_pipeline(
        tmp_path,
        source_text=_native_svg_pipeline_source(),
    )

    assert source.is_file()
    assert ET.canonicalize(
        trace.read_text(encoding="utf-8"),
        strip_text=True,
    ) == ET.canonicalize(
        source.read_text(encoding="utf-8"),
        strip_text=True,
    )

    raster_data = json.loads(raster_manifest.read_text(encoding="utf-8"))

    assert raster_data["representation"] == "native-svg"

    # Raster publishes object/color identity, not bitmap layers.
    assert all("object_id" in product for product in raster_data["products"])

    assert not list(raster_manifest.parent.glob("*.png"))

    # Vector publishes registered SVG layers, not traced PNGs.
    layers = _native_svg_layer_paths(vector_manifest)

    assert len(layers) == 2
    assert all(path.suffix == ".svg" for path in layers.values())
    assert all(path.is_file() for path in layers.values())
    assert not list(vector_manifest.parent.glob("*.png"))

    # Every output still contains authored path commands.
    assert _native_svg_path_ids(layers[1]) == {
        "red-left",
        "red-middle",
    }
    assert _native_svg_path_ids(layers[2]) == {
        "blue-right",
    }


@pytest.mark.slow
def test_native_svg_pipeline_excludes_unpainted_geometry(
    tmp_path: Path,
) -> None:
    """
    fill='none' objects do not create registered color layers.

    Painted geometry remains intact and the unpainted path
    is absent from the resulting registered Artwork products.
    """
    source_text = """
        <svg xmlns="http://www.w3.org/2000/svg"
             viewBox="0 0 100 100">
            <g transform="translate(10,10)">
                <path id="painted"
                      d="M 0 0 H 60 V 60 H 0 Z"
                      fill="#ff0000"/>
                <path id="unpainted"
                      d="M 20 20 H 40 V 40 H 20 Z"
                      fill="none"/>
            </g>
        </svg>
    """

    _, _, raster_manifest, vector_manifest = _native_svg_pipeline(
        tmp_path,
        source_text=source_text,
    )

    raster_data = json.loads(raster_manifest.read_text(encoding="utf-8"))

    assert [product["object_id"] for product in raster_data["products"]] == ["painted"]

    layers = _native_svg_layer_paths(vector_manifest)

    assert set(layers) == {1}
    assert _native_svg_path_ids(layers[1]) == {"painted"}

    root = ET.parse(layers[1]).getroot()

    assert not any(element.get("id") == "unpainted" for element in root.iter())


@pytest.mark.slow
def test_native_svg_pipeline_is_independent_of_printer_palette(
    tmp_path: Path,
) -> None:
    """
    Printer colors and PNG tracing settings do not change
    registered native SVG geometry or Artifact-color identities.
    """
    source_text = _native_svg_pipeline_source()

    first_root = tmp_path / "first"
    second_root = tmp_path / "second"

    first_root.mkdir()
    second_root.mkdir()

    _, first_trace, first_raster, first_vector = _native_svg_pipeline(
        first_root,
        source_text=source_text,
        printer_colors=["red", "blue"],
        artifact_color_count=2,
        artwork_pixels=512,
    )

    _, second_trace, second_raster, second_vector = _native_svg_pipeline(
        second_root,
        source_text=source_text,
        printer_colors=["green", "yellow", "black"],
        artifact_color_count=5,
        artwork_pixels=1024,
    )

    assert first_trace.read_bytes() == second_trace.read_bytes()

    first_raster_data = json.loads(first_raster.read_text(encoding="utf-8"))
    second_raster_data = json.loads(second_raster.read_text(encoding="utf-8"))

    assert first_raster_data["products"] == (second_raster_data["products"])

    first_vector_data = json.loads(first_vector.read_text(encoding="utf-8"))
    second_vector_data = json.loads(second_vector.read_text(encoding="utf-8"))

    assert first_vector_data["registered_extent"] == (second_vector_data["registered_extent"])

    assert first_vector_data["products"] == (second_vector_data["products"])

    first_layers = _native_svg_layer_paths(first_vector)
    second_layers = _native_svg_layer_paths(second_vector)

    assert set(first_layers) == set(second_layers)

    for index in first_layers:
        assert first_layers[index].read_bytes() == second_layers[index].read_bytes()


def test_native_svg_extrude_preserves_large_registered_coordinates(
    tmp_path: Path,
) -> None:
    """
    A large native SVG must retain its intended physical dimensions.

    Regression for fan-shell-style registration:
    - Registered canvas: 1120 x 1120
    - Authored geometry: 1120 x 680
    - Registration translation: Y +220
    - Requested physical artwork width: 100 mm

    The rendered STL must be 100 x (100 * 680 / 1120) mm,
    centered at the origin.
    """
    vector_directory = tmp_path / "vector"
    vector_directory.mkdir(parents=True, exist_ok=True)

    svg = """
        <svg xmlns="http://www.w3.org/2000/svg"
             width="1120"
             height="1120"
             viewBox="0 0 1120 1120">
            <g transform="translate(0,220)">
                <path d="M 0 0 H 1120 V 680 H 0 Z"
                      fill="#303030"/>
            </g>
        </svg>
    """

    envelope = vector_directory / "envelope.svg"
    layer = vector_directory / "color-1.svg"

    envelope.write_text(svg, encoding="utf-8")
    layer.write_text(svg, encoding="utf-8")

    vector_manifest = vector_directory / "products.json"
    vector_manifest.write_text(
        json.dumps(
            {
                "registered_extent": 1120,
                "envelope": envelope.name,
                "products": [
                    _product(
                        index=1,
                        path=layer.name,
                        artifact_color_index=1,
                        artifact_rgb=(48, 48, 48),
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

    # Exercise the real OpenSCAD SVG importer.
    extrude.execute(context)  # type: ignore[arg-type]

    bounds = _stl_bounds(extrude_manifest.parent / "color-1.stl")

    half_height = 50.0 * 680.0 / 1120.0

    assert bounds == pytest.approx(
        (
            -50.0,
            50.0,
            -half_height,
            half_height,
            0.0,
            1.5,
        ),
        abs=0.01,
    )


@pytest.mark.slow
def test_native_svg_fan_shell_extrusion_matches_envelope(
    tmp_path: Path,
) -> None:
    """
    The actual fan-shell SVG must extrude to a centered 100 mm artwork.

    Run the real Prepare -> Raster -> Vector -> Extrude pipeline
    to reproduce any registration or dimensionalization defect.
    """
    source = Path("tests/assets/fan-shell.svg")
    assert source.is_file()

    source_text = source.read_text(encoding="utf-8")

    _, _, _, vector_manifest = _native_svg_pipeline(
        tmp_path,
        source_text=source_text,
    )

    prepare_envelope = tmp_path / "prepare" / "envelope.svg"

    print(
        "PREPARE envelope:",
        extrude._envelope_bounds(prepare_envelope),
    )

    print(
        "VECTOR envelope:",
        extrude._envelope_bounds(vector_manifest.parent / "envelope.svg"),
    )

    vector_data = json.loads(vector_manifest.read_text(encoding="utf-8"))

    envelope = vector_manifest.parent / vector_data["envelope"]
    xmin, ymin, xmax, ymax = extrude._envelope_bounds(envelope)

    envelope_width = xmax - xmin
    envelope_height = ymax - ymin

    assert envelope_width > 0
    assert envelope_height > 0

    scale = 100.0 / max(envelope_width, envelope_height)
    expected_width = envelope_width * scale
    expected_height = envelope_height * scale

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
            artwork_size=100.0,
            artwork_raise=1.0,
            artwork_base_raise=0.0,
            artwork_outer_ridge_width=0.0,
            loop_inner_diameter=0.0,
        ),
    )

    print(
        "Registered envelope:",
        extrude._envelope_bounds(envelope),
    )

    for index, layer in _native_svg_layer_paths(vector_manifest).items():
        print(
            f"Layer {index} SVG:",
            layer,
        )

    # Real OpenSCAD extrusion.
    extrude.execute(context)  # type: ignore[arg-type]

    data = json.loads(extrude_manifest.read_text(encoding="utf-8"))

    assert len(data["products"]) == 1

    stl = extrude_manifest.parent / data["products"][0]["path"]
    bounds = _stl_bounds(stl)

    print(f"\nEnvelope SVG bounds: {(xmin, ymin, xmax, ymax)}")
    print(f"Envelope physical size: {(expected_width, expected_height)}")
    print(f"Artwork STL bounds: {bounds}")
    print(
        "Artwork physical size:",
        (bounds[1] - bounds[0], bounds[3] - bounds[2]),
    )

    assert bounds == pytest.approx(
        (
            -expected_width / 2.0,
            expected_width / 2.0,
            -expected_height / 2.0,
            expected_height / 2.0,
            0.0,
            1.0,
        ),
        abs=0.05,
    )

    assert max(
        bounds[1] - bounds[0],
        bounds[3] - bounds[2],
    ) == pytest.approx(100.0, abs=0.05)


def test_native_svg_envelope_retains_disconnected_regions() -> None:
    """
    Native SVG envelopes must preserve all disconnected regions
    without applying PNG-oriented component filtering.
    """
    import numpy as np

    from lowkey_artifact_builder.model.models.artwork.stages import prepare

    foreground = np.zeros((100, 200), dtype=bool)

    # Two substantial, separated artwork regions.
    foreground[20:80, 10:70] = True
    foreground[20:80, 130:190] = True

    path_data = prepare._envelope_path_data(
        foreground,
        preserve_all=True,
    )

    # Both disconnected regions must be represented as closed subpaths.
    assert path_data.count("M ") == 2
    assert path_data.count("Z") == 2

    # Neither region should be omitted.
    assert "10 " in path_data
    assert "190 " in path_data
