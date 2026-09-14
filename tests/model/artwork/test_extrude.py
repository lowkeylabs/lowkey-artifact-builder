"""
Tests for the artwork extrusion stage.

These tests characterize the storage boundary between the build engine
and the extrusion-stage implementation.

The extrusion stage must consume only the paths supplied through
StageContext. Dynamic STL products are stage-local products whose
locations are determined by the declared extrusion manifest.
"""
# File: tests/model/artwork/test_extrude.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from lowkey_artifact_builder.config import Resolver, get_resolver
from lowkey_artifact_builder.model.models.artwork.base_color import (
    BaseColor,
)
from lowkey_artifact_builder.model.models.artwork.loop_color import (
    LoopColor,
)
from lowkey_artifact_builder.model.models.artwork.stages import extrude

# =========================================================
# Test support
# =========================================================


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


def _product(
    *,
    index: int,
    path: str,
    artifact_color_index: int,
    artifact_rgb: tuple[int, int, int],
    printer_color_name: str,
    printer_rgb: tuple[int, int, int],
    distance: float,
) -> dict[str, Any]:
    """
    Return one registered vector product.
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
        "printer_color": {
            "name": printer_color_name,
            "rgb": _color(
                *printer_rgb,
            ),
        },
        "distance": distance,
    }


def _write_vector_manifest(
    path: Path,
    products: list[dict[str, Any]],
    *,
    registered_extent: int = 20,
) -> None:
    """
    Write a minimal registered vector manifest.

    The registered envelope occupies the complete registered extent unless
    a test constructs a more specific manifest explicitly.
    """

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    envelope = path.parent / "envelope.svg"

    envelope.write_text(
        f"""
        <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 {registered_extent} {registered_extent}"
        >
            <rect
                x="0"
                y="0"
                width="{registered_extent}"
                height="{registered_extent}"
            />
        </svg>
        """,
        encoding="utf-8",
    )

    path.write_text(
        json.dumps(
            {
                "registered_extent": registered_extent,
                "envelope": envelope.name,
                "products": products,
            }
        ),
        encoding="utf-8",
    )


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


def _fake_render_stl_source(
    source: str,
    output: Path,
) -> None:
    """
    Materialize a fake STL product.
    """

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output.write_text(
        "stl",
        encoding="utf-8",
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


# =========================================================
# Storage-boundary tests
# =========================================================


@pytest.mark.slow
def test_extrude_uses_declared_vector_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    The extrusion stage consumes the vector manifest supplied by
    StageContext without reconstructing its filesystem location.
    """

    vector_directory = tmp_path / "deliberately" / "unrelated" / "vector-input"

    svg = vector_directory / "layer.svg"

    vector_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    svg.write_text(
        "<svg/>",
        encoding="utf-8",
    )

    vector_manifest = vector_directory / "anything.json"

    _write_vector_manifest(
        vector_manifest,
        [
            _product(
                index=1,
                path=svg.name,
                artifact_color_index=1,
                artifact_rgb=(
                    250,
                    250,
                    250,
                ),
                printer_color_name="white",
                printer_rgb=(
                    255,
                    255,
                    255,
                ),
                distance=1.25,
            )
        ],
    )

    extrude_manifest = tmp_path / "completely-different" / "output" / "manifest.json"

    context = StubContext(
        inputs={
            "vector.manifest": vector_manifest,
        },
        outputs={
            "manifest": extrude_manifest,
        },
        resolver=_resolver(
            tmp_path,
        ),
    )

    rendered_sources: list[str] = []

    def fake_render_stl_source(
        source: str,
        output: Path,
    ) -> None:
        rendered_sources.append(source)

        _fake_render_stl_source(
            source,
            output,
        )

    monkeypatch.setattr(
        extrude,
        "render_stl_source",
        fake_render_stl_source,
    )

    extrude.execute(context)  # type: ignore[arg-type]

    assert len(rendered_sources) == 1

    assert str(svg.resolve()) in rendered_sources[0]

    assert extrude_manifest.is_file()


@pytest.mark.slow
def test_extrude_places_dynamic_stls_beside_declared_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Dynamic STL products are placed beside the extrusion manifest
    supplied by StageContext.
    """

    vector_directory = tmp_path / "vector"

    first_svg = vector_directory / "first.svg"
    second_svg = vector_directory / "second.svg"

    vector_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    first_svg.write_text(
        "<svg/>",
        encoding="utf-8",
    )

    second_svg.write_text(
        "<svg/>",
        encoding="utf-8",
    )

    vector_manifest = vector_directory / "products.json"

    _write_vector_manifest(
        vector_manifest,
        [
            _product(
                index=2,
                path=second_svg.name,
                artifact_color_index=2,
                artifact_rgb=(
                    5,
                    5,
                    5,
                ),
                printer_color_name="black",
                printer_rgb=(
                    0,
                    0,
                    0,
                ),
                distance=1.5,
            ),
            _product(
                index=1,
                path=first_svg.name,
                artifact_color_index=1,
                artifact_rgb=(
                    250,
                    250,
                    250,
                ),
                printer_color_name="white",
                printer_rgb=(
                    255,
                    255,
                    255,
                ),
                distance=1.25,
            ),
        ],
    )

    output_directory = tmp_path / "arbitrary" / "extrusion-products"

    extrude_manifest = output_directory / "custom-name.json"

    context = StubContext(
        inputs={
            "vector.manifest": vector_manifest,
        },
        outputs={
            "manifest": extrude_manifest,
        },
        resolver=_resolver(tmp_path),
    )

    rendered_outputs: list[Path] = []

    def fake_render_stl_source(
        source: str,
        output: Path,
    ) -> None:
        rendered_outputs.append(output)

        _fake_render_stl_source(
            source,
            output,
        )

    monkeypatch.setattr(
        extrude,
        "render_stl_source",
        fake_render_stl_source,
    )

    extrude.execute(context)  # type: ignore[arg-type]

    assert rendered_outputs == [
        output_directory / "color-1.stl",
        output_directory / "color-2.stl",
    ]

    assert all(path.is_file() for path in rendered_outputs)


@pytest.mark.slow
def test_extrude_manifest_describes_stage_local_products(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    The extrusion manifest records dynamic STL products using filenames
    relative to the manifest rather than canonical artifact paths.
    """

    vector_directory = tmp_path / "input"

    svg = vector_directory / "layer.svg"

    vector_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    svg.write_text(
        "<svg/>",
        encoding="utf-8",
    )

    vector_manifest = vector_directory / "manifest.json"

    _write_vector_manifest(
        vector_manifest,
        [
            _product(
                index=1,
                path=svg.name,
                artifact_color_index=1,
                artifact_rgb=(
                    250,
                    205,
                    10,
                ),
                printer_color_name="gold",
                printer_rgb=(
                    255,
                    215,
                    0,
                ),
                distance=3.5,
            )
        ],
    )

    extrude_manifest = tmp_path / "wherever" / "extruded" / "products.json"

    context = StubContext(
        inputs={
            "vector.manifest": vector_manifest,
        },
        outputs={
            "manifest": extrude_manifest,
        },
        resolver=_resolver(tmp_path),
    )

    monkeypatch.setattr(
        extrude,
        "render_stl_source",
        _fake_render_stl_source,
    )

    extrude.execute(context)  # type: ignore[arg-type]

    data = json.loads(
        extrude_manifest.read_text(
            encoding="utf-8",
        )
    )

    assert data == {
        "artwork_raise": 1.0,
        "products": [
            {
                "index": 1,
                "path": "color-1.stl",
                "artifact_color": {
                    "index": 1,
                    "rgb": {
                        "red": 250,
                        "green": 205,
                        "blue": 10,
                    },
                },
                "printer_color": {
                    "name": "gold",
                    "rgb": {
                        "red": 255,
                        "green": 215,
                        "blue": 0,
                    },
                },
                "distance": 3.5,
            }
        ],
    }


@pytest.mark.slow
def test_participating_loop_produces_stage_local_stl_component(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    A participating Loop becomes an independently printable stage-local
    extrusion product.
    """

    vector_directory = tmp_path / "vector"

    svg = vector_directory / "layer.svg"

    vector_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    svg.write_text(
        "<svg/>",
        encoding="utf-8",
    )

    vector_manifest = vector_directory / "products.json"

    _write_vector_manifest(
        vector_manifest,
        [
            _product(
                index=1,
                path=svg.name,
                artifact_color_index=1,
                artifact_rgb=(
                    250,
                    250,
                    250,
                ),
                printer_color_name="white",
                printer_rgb=(
                    255,
                    255,
                    255,
                ),
                distance=0.0,
            )
        ],
    )

    extrude_manifest = tmp_path / "extrude" / "products.json"

    context = StubContext(
        inputs={
            "vector.manifest": vector_manifest,
        },
        outputs={
            "manifest": extrude_manifest,
        },
        resolver=_resolver(
            tmp_path,
            artwork_size=100.0,
            artwork_raise=1.0,
            loop_inner_diameter=6.0,
            loop_width=2.0,
            loop_position=0,
            loop_raise=1.5,
            loop_color="black",
        ),
    )

    rendered_outputs: list[Path] = []

    def fake_render_stl_source(
        source: str,
        output: Path,
    ) -> None:
        rendered_outputs.append(
            output,
        )

        _fake_render_stl_source(
            source,
            output,
        )

    monkeypatch.setattr(
        extrude,
        "render_stl_source",
        fake_render_stl_source,
    )

    extrude.execute(context)  # type: ignore[arg-type]

    assert extrude_manifest.parent / "loop.stl" in rendered_outputs
    assert (extrude_manifest.parent / "loop.stl").is_file()


# =========================================================
# Color-semantic tests
# =========================================================


@pytest.mark.slow
def test_extrude_preserves_artifact_and_printer_color_semantics(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Extrusion preserves Artifact color identity and RGB separately from
    the physical printer assignment.

    Physical dimensionalization does not reinterpret either color.
    """

    vector_directory = tmp_path / "vector"

    svg = vector_directory / "color.svg"

    vector_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    svg.write_text(
        "<svg/>",
        encoding="utf-8",
    )

    vector_manifest = vector_directory / "manifest.json"

    _write_vector_manifest(
        vector_manifest,
        [
            _product(
                index=1,
                path=svg.name,
                artifact_color_index=7,
                artifact_rgb=(
                    17,
                    43,
                    91,
                ),
                printer_color_name="physical-blue",
                printer_rgb=(
                    20,
                    40,
                    90,
                ),
                distance=1.25,
            )
        ],
    )

    extrude_manifest = tmp_path / "extrude" / "manifest.json"

    context = StubContext(
        inputs={
            "vector.manifest": vector_manifest,
        },
        outputs={
            "manifest": extrude_manifest,
        },
        resolver=_resolver(tmp_path),
    )

    monkeypatch.setattr(
        extrude,
        "render_stl_source",
        _fake_render_stl_source,
    )

    extrude.execute(context)  # type: ignore[arg-type]

    data = json.loads(
        extrude_manifest.read_text(
            encoding="utf-8",
        )
    )

    product = data["products"][0]

    assert product["artifact_color"] == {
        "index": 7,
        "rgb": {
            "red": 17,
            "green": 43,
            "blue": 91,
        },
    }

    assert product["printer_color"] == {
        "name": "physical-blue",
        "rgb": {
            "red": 20,
            "green": 40,
            "blue": 90,
        },
    }

    assert product["distance"] == 1.25


# =========================================================
# Dimensionalization tests
# =========================================================


@pytest.mark.slow
def test_extrude_sizes_and_centers_occupied_envelope_in_physical_space(
    tmp_path: Path,
) -> None:
    """
    Standalone Artwork extrusion dimensionalizes the occupied envelope.

    The registered Artwork may occupy a non-square, offset region of its
    common coordinate system. Extrusion must uniformly scale that occupied
    region so its maximum X/Y extent equals artwork_size, center it at the
    physical origin, and preserve registration between color layers.

    This test intentionally renders real STL products through OpenSCAD.
    Inspecting generated SCAD alone is insufficient because SVG import unit
    interpretation is part of the physical dimensionalization boundary.
    """

    vector_directory = tmp_path / "vector"

    vector_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    envelope = vector_directory / "envelope.svg"

    envelope.write_text(
        """
        <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 100 100"
        >
            <rect
                x="20"
                y="30"
                width="40"
                height="20"
            />
        </svg>
        """,
        encoding="utf-8",
    )

    first_svg = vector_directory / "color-1.svg"
    second_svg = vector_directory / "color-2.svg"

    first_svg.write_text(
        """
        <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 100 100"
        >
            <rect
                x="20"
                y="30"
                width="20"
                height="20"
            />
        </svg>
        """,
        encoding="utf-8",
    )

    second_svg.write_text(
        """
        <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 100 100"
        >
            <rect
                x="40"
                y="30"
                width="20"
                height="20"
            />
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
                        artifact_rgb=(
                            255,
                            0,
                            0,
                        ),
                        printer_color_name="red",
                        printer_rgb=(
                            255,
                            0,
                            0,
                        ),
                        distance=0.0,
                    ),
                    _product(
                        index=2,
                        path=second_svg.name,
                        artifact_color_index=2,
                        artifact_rgb=(
                            0,
                            0,
                            255,
                        ),
                        printer_color_name="blue",
                        printer_rgb=(
                            0,
                            0,
                            255,
                        ),
                        distance=0.0,
                    ),
                ],
            }
        ),
        encoding="utf-8",
    )

    extrude_manifest = tmp_path / "extrude" / "products.json"

    context = StubContext(
        inputs={
            "vector.manifest": vector_manifest,
        },
        outputs={
            "manifest": extrude_manifest,
        },
        resolver=_resolver(
            tmp_path,
            artwork_size=120.0,
            artwork_raise=1.0,
            loop_inner_diameter=0.0,
        ),
    )

    extrude.execute(context)  # type: ignore[arg-type]

    first_stl = extrude_manifest.parent / "color-1.stl"
    second_stl = extrude_manifest.parent / "color-2.stl"

    first_bounds = _stl_bounds(first_stl)
    second_bounds = _stl_bounds(second_stl)

    first_min_x, first_max_x, first_min_y, first_max_y, first_min_z, first_max_z = first_bounds
    (
        second_min_x,
        second_max_x,
        second_min_y,
        second_max_y,
        second_min_z,
        second_max_z,
    ) = second_bounds

    min_x = min(
        first_min_x,
        second_min_x,
    )
    max_x = max(
        first_max_x,
        second_max_x,
    )
    min_y = min(
        first_min_y,
        second_min_y,
    )
    max_y = max(
        first_max_y,
        second_max_y,
    )

    assert max_x - min_x == pytest.approx(
        120.0,
        abs=0.01,
    )

    assert max_y - min_y == pytest.approx(
        60.0,
        abs=0.01,
    )

    assert (min_x + max_x) / 2.0 == pytest.approx(
        0.0,
        abs=0.01,
    )

    assert (min_y + max_y) / 2.0 == pytest.approx(
        0.0,
        abs=0.01,
    )

    assert first_max_x == pytest.approx(
        second_min_x,
        abs=0.01,
    )

    assert first_min_z == pytest.approx(
        0.0,
        abs=0.01,
    )
    assert second_min_z == pytest.approx(
        0.0,
        abs=0.01,
    )
    assert first_max_z == pytest.approx(
        1.0,
        abs=0.01,
    )
    assert second_max_z == pytest.approx(
        1.0,
        abs=0.01,
    )


def test_build_scad_introduces_physical_z_from_artwork_raise(
    tmp_path: Path,
) -> None:
    """
    Extrusion introduces physical Z through artwork_raise.

    Registered vector geometry has no physical thickness. The extrusion
    consumer introduces that dimension from resolved Artwork configuration.
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
        artwork_raise=1.25,
    )

    assert "artwork_raise = 1.25;" in source
    assert "linear_extrude(" in source
    assert "height = artwork_raise" in source


@pytest.mark.slow
def test_participating_loop_is_declared_as_semantic_color_product(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    A participating Loop is declared as an independently printable extrusion
    product with its resolved semantic physical color identity.
    """

    vector_directory = tmp_path / "vector"

    svg = vector_directory / "layer-white.svg"

    vector_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    svg.write_text(
        "<svg/>",
        encoding="utf-8",
    )

    vector_manifest = vector_directory / "products.json"

    _write_vector_manifest(
        vector_manifest,
        [
            _product(
                index=1,
                path=svg.name,
                artifact_color_index=1,
                artifact_rgb=(
                    255,
                    255,
                    255,
                ),
                printer_color_name="white",
                printer_rgb=(
                    255,
                    255,
                    255,
                ),
                distance=0.0,
            )
        ],
    )

    extrude_manifest = tmp_path / "extrude" / "products.json"

    context = StubContext(
        inputs={
            "vector.manifest": vector_manifest,
        },
        outputs={
            "manifest": extrude_manifest,
        },
        resolver=_resolver(
            tmp_path,
            artwork_size=100.0,
            artwork_raise=1.0,
            loop_inner_diameter=6.0,
            loop_width=2.0,
            loop_position=0,
            loop_raise=1.5,
            loop_color="black",
        ),
    )

    monkeypatch.setattr(
        extrude,
        "render_stl_source",
        _fake_render_stl_source,
    )

    extrude.execute(context)  # type: ignore[arg-type]

    data = json.loads(
        extrude_manifest.read_text(
            encoding="utf-8",
        )
    )

    loop_product = next(product for product in data["products"] if product["path"] == "loop.stl")

    assert loop_product["printer_color"]["name"] == "black"


@pytest.mark.slow
def test_participating_loop_manifest_uses_attachment_derived_color(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Without an explicit loop_color, a participating Loop preserves the
    semantic physical color selected from Registered Artwork at its
    attachment position.
    """

    vector_directory = tmp_path / "vector"

    svg = vector_directory / "layer-red.svg"

    vector_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

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

    vector_manifest = vector_directory / "products.json"

    _write_vector_manifest(
        vector_manifest,
        [
            _product(
                index=1,
                path=svg.name,
                artifact_color_index=1,
                artifact_rgb=(
                    250,
                    0,
                    0,
                ),
                printer_color_name="red",
                printer_rgb=(
                    255,
                    0,
                    0,
                ),
                distance=0.0,
            )
        ],
    )

    extrude_manifest = tmp_path / "extrude" / "products.json"

    context = StubContext(
        inputs={
            "vector.manifest": vector_manifest,
        },
        outputs={
            "manifest": extrude_manifest,
        },
        resolver=_resolver(
            tmp_path,
            artwork_size=100.0,
            artwork_raise=1.0,
            loop_inner_diameter=6.0,
            loop_width=2.0,
            loop_position=0,
            loop_raise=1.5,
        ),
    )

    monkeypatch.setattr(
        extrude,
        "render_stl_source",
        _fake_render_stl_source,
    )

    extrude.execute(context)  # type: ignore[arg-type]

    data = json.loads(
        extrude_manifest.read_text(
            encoding="utf-8",
        )
    )

    loop_product = next(product for product in data["products"] if product["path"] == "loop.stl")

    assert loop_product["printer_color"]["name"] == "red"


@pytest.mark.slow
def test_participating_loop_manifest_preserves_attachment_printer_rgb(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    A participating Loop whose color is derived from its Artwork attachment
    preserves the complete physical printer color assignment through
    extrusion.
    """

    vector_directory = tmp_path / "vector"

    svg = vector_directory / "layer-red.svg"

    vector_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

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

    vector_manifest = vector_directory / "products.json"

    _write_vector_manifest(
        vector_manifest,
        [
            _product(
                index=1,
                path=svg.name,
                artifact_color_index=1,
                artifact_rgb=(
                    250,
                    0,
                    0,
                ),
                printer_color_name="red",
                printer_rgb=(
                    255,
                    0,
                    0,
                ),
                distance=0.0,
            )
        ],
    )

    extrude_manifest = tmp_path / "extrude" / "products.json"

    context = StubContext(
        inputs={
            "vector.manifest": vector_manifest,
        },
        outputs={
            "manifest": extrude_manifest,
        },
        resolver=_resolver(
            tmp_path,
            artwork_size=100.0,
            artwork_raise=1.0,
            loop_inner_diameter=6.0,
            loop_width=2.0,
            loop_position=0,
            loop_raise=1.5,
        ),
    )

    monkeypatch.setattr(
        extrude,
        "render_stl_source",
        _fake_render_stl_source,
    )

    extrude.execute(context)  # type: ignore[arg-type]

    data = json.loads(
        extrude_manifest.read_text(
            encoding="utf-8",
        )
    )

    loop_product = next(product for product in data["products"] if product["path"] == "loop.stl")

    assert loop_product["printer_color"] == {
        "name": "red",
        "rgb": {
            "red": 255,
            "green": 0,
            "blue": 0,
        },
    }


# =========================================================
# Base product-boundary tests
# =========================================================


def test_disabled_base_does_not_produce_stage_local_stl_component(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    artwork_base_raise == 0 disables Base participation.

    A disabled Base produces no stage-local STL product and does not alter
    ordinary Artwork extrusion.
    """

    vector_directory = tmp_path / "vector"

    svg = vector_directory / "layer.svg"

    vector_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    svg.write_text(
        "<svg/>",
        encoding="utf-8",
    )

    vector_manifest = vector_directory / "products.json"

    _write_vector_manifest(
        vector_manifest,
        [
            _product(
                index=1,
                path=svg.name,
                artifact_color_index=1,
                artifact_rgb=(
                    255,
                    255,
                    255,
                ),
                printer_color_name="white",
                printer_rgb=(
                    255,
                    255,
                    255,
                ),
                distance=0.0,
            )
        ],
    )

    extrude_manifest = tmp_path / "extrude" / "products.json"

    context = StubContext(
        inputs={
            "vector.manifest": vector_manifest,
        },
        outputs={
            "manifest": extrude_manifest,
        },
        resolver=_resolver(tmp_path),
    )

    rendered_outputs: list[Path] = []

    def fake_render_stl_source(
        source: str,
        output: Path,
    ) -> None:
        rendered_outputs.append(
            output,
        )

        _fake_render_stl_source(
            source,
            output,
        )

    monkeypatch.setattr(
        extrude,
        "render_stl_source",
        fake_render_stl_source,
    )

    extrude.execute(context)  # type: ignore[arg-type]

    assert extrude_manifest.parent / "base.stl" not in rendered_outputs
    assert not (extrude_manifest.parent / "base.stl").exists()

    data = json.loads(
        extrude_manifest.read_text(
            encoding="utf-8",
        )
    )

    assert all(product["path"] != "base.stl" for product in data["products"])


def test_participating_base_produces_stage_local_stl_component(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    A positive artwork_base_raise makes Base an independently printable
    stage-local extrusion product.
    """

    vector_directory = tmp_path / "vector"

    svg = vector_directory / "layer.svg"

    vector_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    svg.write_text(
        "<svg/>",
        encoding="utf-8",
    )

    vector_manifest = vector_directory / "products.json"

    _write_vector_manifest(
        vector_manifest,
        [
            _product(
                index=1,
                path=svg.name,
                artifact_color_index=1,
                artifact_rgb=(
                    255,
                    255,
                    255,
                ),
                printer_color_name="white",
                printer_rgb=(
                    255,
                    255,
                    255,
                ),
                distance=0.0,
            )
        ],
    )

    extrude_manifest = tmp_path / "extrude" / "products.json"

    context = StubContext(
        inputs={
            "vector.manifest": vector_manifest,
        },
        outputs={
            "manifest": extrude_manifest,
        },
        resolver=_resolver(
            tmp_path,
            artwork_size=100.0,
            artwork_raise=1.0,
            loop_inner_diameter=0.0,
            artwork_base_raise=1.5,
        ),
    )

    rendered_outputs: list[Path] = []

    def fake_render_stl_source(
        source: str,
        output: Path,
    ) -> None:
        rendered_outputs.append(
            output,
        )

        _fake_render_stl_source(
            source,
            output,
        )

    monkeypatch.setattr(
        extrude,
        "render_stl_source",
        fake_render_stl_source,
    )

    monkeypatch.setattr(
        extrude,
        "resolve_base_color_identity",
        lambda artwork, *, resolver: BaseColor(
            name="white",
            rgb=(
                255,
                255,
                255,
            ),
        ),
    )

    extrude.execute(context)  # type: ignore[arg-type]

    base = extrude_manifest.parent / "base.stl"

    assert base in rendered_outputs
    assert base.is_file()


def test_participating_base_is_built_from_registered_envelope(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    The standalone Base is rendered from the registered Artwork envelope,
    not from any individual Artwork color layer.
    """

    vector_directory = tmp_path / "vector"

    svg = vector_directory / "layer.svg"

    vector_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    svg.write_text(
        "<svg/>",
        encoding="utf-8",
    )

    vector_manifest = vector_directory / "products.json"

    _write_vector_manifest(
        vector_manifest,
        [
            _product(
                index=1,
                path=svg.name,
                artifact_color_index=1,
                artifact_rgb=(
                    255,
                    255,
                    255,
                ),
                printer_color_name="white",
                printer_rgb=(
                    255,
                    255,
                    255,
                ),
                distance=0.0,
            )
        ],
    )

    extrude_manifest = tmp_path / "extrude" / "products.json"

    context = StubContext(
        inputs={
            "vector.manifest": vector_manifest,
        },
        outputs={
            "manifest": extrude_manifest,
        },
        resolver=_resolver(
            tmp_path,
            artwork_size=100.0,
            artwork_raise=1.0,
            loop_inner_diameter=0.0,
            artwork_base_raise=1.5,
        ),
    )

    rendered_sources: dict[Path, str] = {}

    def fake_render_stl_source(
        source: str,
        output: Path,
    ) -> None:
        rendered_sources[output] = source

        _fake_render_stl_source(
            source,
            output,
        )

    monkeypatch.setattr(
        extrude,
        "render_stl_source",
        fake_render_stl_source,
    )

    monkeypatch.setattr(
        extrude,
        "resolve_base_color_identity",
        lambda artwork, *, resolver: BaseColor(
            name="white",
            rgb=(
                255,
                255,
                255,
            ),
        ),
    )

    extrude.execute(context)  # type: ignore[arg-type]

    base = extrude_manifest.parent / "base.stl"

    assert base in rendered_sources

    base_source = rendered_sources[base]

    envelope = vector_manifest.parent / "envelope.svg"

    assert str(envelope.resolve()) in base_source
    assert str(svg.resolve()) not in base_source


def test_participating_base_translates_all_artwork_layers_upward(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Base participation translates every Artwork color component upward by the
    same artwork_base_raise.

    Relative Z registration between Artwork color components is preserved.
    """

    vector_directory = tmp_path / "vector"

    first_svg = vector_directory / "first.svg"
    second_svg = vector_directory / "second.svg"

    vector_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    first_svg.write_text(
        "<svg/>",
        encoding="utf-8",
    )

    second_svg.write_text(
        "<svg/>",
        encoding="utf-8",
    )

    vector_manifest = vector_directory / "products.json"

    _write_vector_manifest(
        vector_manifest,
        [
            _product(
                index=1,
                path=first_svg.name,
                artifact_color_index=1,
                artifact_rgb=(
                    255,
                    0,
                    0,
                ),
                printer_color_name="red",
                printer_rgb=(
                    255,
                    0,
                    0,
                ),
                distance=0.0,
            ),
            _product(
                index=2,
                path=second_svg.name,
                artifact_color_index=2,
                artifact_rgb=(
                    0,
                    0,
                    255,
                ),
                printer_color_name="blue",
                printer_rgb=(
                    0,
                    0,
                    255,
                ),
                distance=0.0,
            ),
        ],
    )

    extrude_manifest = tmp_path / "extrude" / "products.json"

    context = StubContext(
        inputs={
            "vector.manifest": vector_manifest,
        },
        outputs={
            "manifest": extrude_manifest,
        },
        resolver=_resolver(
            tmp_path,
            artwork_size=100.0,
            artwork_raise=1.0,
            loop_inner_diameter=0.0,
            artwork_base_raise=1.5,
        ),
    )

    rendered_sources: dict[Path, str] = {}

    def fake_render_stl_source(
        source: str,
        output: Path,
    ) -> None:
        rendered_sources[output] = source

        _fake_render_stl_source(
            source,
            output,
        )

    monkeypatch.setattr(
        extrude,
        "render_stl_source",
        fake_render_stl_source,
    )

    monkeypatch.setattr(
        extrude,
        "resolve_base_color_identity",
        lambda artwork, *, resolver: BaseColor(
            name="red",
            rgb=(
                255,
                0,
                0,
            ),
        ),
    )

    extrude.execute(context)  # type: ignore[arg-type]

    first_source = rendered_sources[extrude_manifest.parent / "color-1.stl"]

    second_source = rendered_sources[extrude_manifest.parent / "color-2.stl"]

    assert "artwork_z = 1.5;" in first_source
    assert "artwork_z = 1.5;" in second_source


def test_participating_base_is_declared_as_semantic_color_product(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    A participating Base is declared as an independently printable extrusion
    product with its complete resolved semantic physical color identity.
    """

    vector_directory = tmp_path / "vector"

    svg = vector_directory / "layer.svg"

    vector_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    svg.write_text(
        "<svg/>",
        encoding="utf-8",
    )

    vector_manifest = vector_directory / "products.json"

    _write_vector_manifest(
        vector_manifest,
        [
            _product(
                index=1,
                path=svg.name,
                artifact_color_index=1,
                artifact_rgb=(
                    255,
                    0,
                    0,
                ),
                printer_color_name="red",
                printer_rgb=(
                    255,
                    0,
                    0,
                ),
                distance=0.0,
            )
        ],
    )

    extrude_manifest = tmp_path / "extrude" / "products.json"

    context = StubContext(
        inputs={
            "vector.manifest": vector_manifest,
        },
        outputs={
            "manifest": extrude_manifest,
        },
        resolver=_resolver(
            tmp_path,
            artwork_size=100.0,
            artwork_raise=1.0,
            loop_inner_diameter=0.0,
            artwork_base_raise=1.5,
            artwork_base_color="test-yellow",
        ),
    )

    monkeypatch.setattr(
        extrude,
        "render_stl_source",
        _fake_render_stl_source,
    )

    extrude.execute(context)  # type: ignore[arg-type]

    manifest = json.loads(
        extrude_manifest.read_text(
            encoding="utf-8",
        )
    )

    base = next(product for product in manifest["products"] if product["path"] == "base.stl")

    assert base == {
        "path": "base.stl",
        "printer_color": {
            "name": "test-yellow",
            "rgb": {
                "red": 255,
                "green": 255,
                "blue": 0,
            },
        },
    }


def test_explicit_base_color_uses_its_own_physical_rgb(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    An explicitly configured Base color is authoritative.

    The Base resolves the physical RGB belonging to its explicitly selected
    semantic color rather than inheriting an unrelated registered Artwork RGB.
    """

    vector_directory = tmp_path / "vector"
    svg = vector_directory / "layer.svg"

    vector_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    svg.write_text(
        "<svg/>",
        encoding="utf-8",
    )

    vector_manifest = vector_directory / "products.json"

    _write_vector_manifest(
        vector_manifest,
        [
            _product(
                index=1,
                path=svg.name,
                artifact_color_index=1,
                artifact_rgb=(
                    255,
                    0,
                    0,
                ),
                printer_color_name="red",
                printer_rgb=(
                    255,
                    0,
                    0,
                ),
                distance=0.0,
            )
        ],
    )

    extrude_manifest = tmp_path / "extrude" / "products.json"

    context = StubContext(
        inputs={
            "vector.manifest": vector_manifest,
        },
        outputs={
            "manifest": extrude_manifest,
        },
        resolver=_resolver(
            tmp_path,
            artwork_size=100.0,
            artwork_raise=1.0,
            loop_inner_diameter=0.0,
            artwork_base_raise=1.5,
            artwork_base_color="test-yellow",
        ),
    )

    monkeypatch.setattr(
        extrude,
        "render_stl_source",
        _fake_render_stl_source,
    )

    extrude.execute(context)  # type: ignore[arg-type]

    manifest = json.loads(
        extrude_manifest.read_text(
            encoding="utf-8",
        )
    )

    base = next(product for product in manifest["products"] if product["path"] == "base.stl")

    assert base["printer_color"] == {
        "name": "test-yellow",
        "rgb": {
            "red": 255,
            "green": 255,
            "blue": 0,
        },
    }

    assert base["printer_color"]["rgb"] != {
        "red": 255,
        "green": 0,
        "blue": 0,
    }


def test_derived_base_color_with_loop_preserves_attachment_printer_rgb(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    A participating Base preserves the complete physical color identity
    resolved by the model-owned Base color operation when Loop participates.
    """

    vector_directory = tmp_path / "vector"
    svg = vector_directory / "layer.svg"

    vector_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    svg.write_text(
        "<svg/>",
        encoding="utf-8",
    )

    vector_manifest = vector_directory / "products.json"

    _write_vector_manifest(
        vector_manifest,
        [
            _product(
                index=1,
                path=svg.name,
                artifact_color_index=1,
                artifact_rgb=(
                    17,
                    34,
                    51,
                ),
                printer_color_name="attachment-blue",
                printer_rgb=(
                    20,
                    40,
                    200,
                ),
                distance=0.0,
            )
        ],
    )

    extrude_manifest = tmp_path / "extrude" / "products.json"

    context = StubContext(
        inputs={
            "vector.manifest": vector_manifest,
        },
        outputs={
            "manifest": extrude_manifest,
        },
        resolver=_resolver(
            tmp_path,
            artwork_size=100.0,
            artwork_raise=1.0,
            artwork_base_raise=1.5,
            loop_inner_diameter=5.0,
            loop_width=2.0,
            loop_position=0,
            loop_raise=1.0,
        ),
    )

    monkeypatch.setattr(
        extrude,
        "render_stl_source",
        _fake_render_stl_source,
    )

    monkeypatch.setattr(
        extrude,
        "resolve_base_color_identity",
        lambda artwork, *, resolver: BaseColor(
            name="attachment-blue",
            rgb=(
                20,
                40,
                200,
            ),
        ),
    )

    monkeypatch.setattr(
        extrude,
        "resolve_loop_color_identity",
        lambda artwork, *, resolver: LoopColor(
            name="attachment-blue",
            rgb=(
                20,
                40,
                200,
            ),
        ),
    )

    extrude.execute(context)  # type: ignore[arg-type]

    data = json.loads(
        extrude_manifest.read_text(
            encoding="utf-8",
        )
    )

    base_product = next(product for product in data["products"] if product["path"] == "base.stl")

    loop_product = next(product for product in data["products"] if product["path"] == "loop.stl")

    assert base_product["printer_color"] == {
        "name": "attachment-blue",
        "rgb": {
            "red": 20,
            "green": 40,
            "blue": 200,
        },
    }

    assert base_product["printer_color"] == loop_product["printer_color"]


def test_derived_base_color_without_loop_preserves_position_zero_printer_rgb(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    A participating Base preserves the complete physical color identity
    resolved by the model-owned Base color operation without Loop.
    """

    vector_directory = tmp_path / "vector"
    svg = vector_directory / "layer.svg"

    vector_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    svg.write_text(
        "<svg/>",
        encoding="utf-8",
    )

    vector_manifest = vector_directory / "products.json"

    _write_vector_manifest(
        vector_manifest,
        [
            _product(
                index=1,
                path=svg.name,
                artifact_color_index=1,
                artifact_rgb=(
                    170,
                    85,
                    0,
                ),
                printer_color_name="attachment-orange",
                printer_rgb=(
                    230,
                    110,
                    20,
                ),
                distance=0.0,
            )
        ],
    )

    extrude_manifest = tmp_path / "extrude" / "products.json"

    context = StubContext(
        inputs={
            "vector.manifest": vector_manifest,
        },
        outputs={
            "manifest": extrude_manifest,
        },
        resolver=_resolver(
            tmp_path,
            artwork_size=100.0,
            artwork_raise=1.0,
            artwork_base_raise=1.5,
            loop_inner_diameter=0.0,
        ),
    )

    monkeypatch.setattr(
        extrude,
        "render_stl_source",
        _fake_render_stl_source,
    )

    monkeypatch.setattr(
        extrude,
        "resolve_base_color_identity",
        lambda artwork, *, resolver: BaseColor(
            name="attachment-orange",
            rgb=(
                230,
                110,
                20,
            ),
        ),
    )

    extrude.execute(context)  # type: ignore[arg-type]

    data = json.loads(
        extrude_manifest.read_text(
            encoding="utf-8",
        )
    )

    base_product = next(product for product in data["products"] if product["path"] == "base.stl")

    assert base_product["printer_color"] == {
        "name": "attachment-orange",
        "rgb": {
            "red": 230,
            "green": 110,
            "blue": 20,
        },
    }


@pytest.mark.slow
def test_base_and_loop_share_artwork_supporting_plane(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    When Base and Loop both participate, Artwork proper and Loop begin at
    the top of Base while Base itself begins at Z=0.
    """

    vector_manifest = tmp_path / "vector" / "products.json"

    layer = vector_manifest.parent / "color-1.svg"

    layer.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    layer.write_text(
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

    _write_vector_manifest(
        vector_manifest,
        [
            _product(
                index=1,
                path="color-1.svg",
                artifact_color_index=1,
                artifact_rgb=(255, 0, 0),
                printer_color_name="test-red",
                printer_rgb=(255, 0, 0),
                distance=0.0,
            ),
        ],
    )

    extrude_manifest = tmp_path / "extrude" / "products.json"

    context = StubContext(
        inputs={
            "vector.manifest": vector_manifest,
        },
        outputs={
            "manifest": extrude_manifest,
        },
        resolver=_resolver(
            tmp_path,
            artwork_size=20.0,
            artwork_raise=3.0,
            artwork_base_raise=2.0,
            artwork_base_color="test-red",
            loop_inner_diameter=4.0,
            loop_width=2.0,
            loop_position=0,
            loop_raise=3.0,
        ),
    )

    monkeypatch.setattr(
        extrude,
        "query_all",
        lambda _path, *, millimeters=False: {
            "svg1": {
                "x": 0.0,
                "y": 0.0,
                "width": 20.0,
                "height": 20.0,
            },
        },
    )

    extrude.execute(context)  # type: ignore[arg-type]

    base_bounds = _stl_bounds(
        extrude_manifest.parent / "base.stl",
    )

    artwork_bounds = _stl_bounds(
        extrude_manifest.parent / "color-1.stl",
    )

    loop_bounds = _stl_bounds(
        extrude_manifest.parent / "loop.stl",
    )

    assert base_bounds[4:6] == pytest.approx(
        (
            0.0,
            2.0,
        )
    )

    assert artwork_bounds[4:6] == pytest.approx(
        (
            2.0,
            5.0,
        )
    )

    assert loop_bounds[4:6] == pytest.approx(
        (
            2.0,
            5.0,
        )
    )


@pytest.mark.slow
def test_base_and_loop_preserve_independent_raises_above_common_support(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Loop and Artwork may have different physical heights while sharing the
    same Base-supported starting Z plane.
    """

    vector_manifest = tmp_path / "vector" / "products.json"

    layer = vector_manifest.parent / "color-1.svg"

    layer.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    layer.write_text(
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

    _write_vector_manifest(
        vector_manifest,
        [
            _product(
                index=1,
                path="color-1.svg",
                artifact_color_index=1,
                artifact_rgb=(255, 0, 0),
                printer_color_name="test-red",
                printer_rgb=(255, 0, 0),
                distance=0.0,
            ),
        ],
    )

    extrude_manifest = tmp_path / "extrude" / "products.json"

    context = StubContext(
        inputs={
            "vector.manifest": vector_manifest,
        },
        outputs={
            "manifest": extrude_manifest,
        },
        resolver=_resolver(
            tmp_path,
            artwork_size=20.0,
            artwork_raise=3.0,
            artwork_base_raise=2.0,
            artwork_base_color="test-red",
            loop_inner_diameter=4.0,
            loop_width=2.0,
            loop_position=0,
            loop_raise=5.0,
        ),
    )

    monkeypatch.setattr(
        extrude,
        "query_all",
        lambda _path, *, millimeters=False: {
            "svg1": {
                "x": 0.0,
                "y": 0.0,
                "width": 20.0,
                "height": 20.0,
            },
        },
    )

    extrude.execute(context)  # type: ignore[arg-type]

    artwork_bounds = _stl_bounds(
        extrude_manifest.parent / "color-1.stl",
    )

    loop_bounds = _stl_bounds(
        extrude_manifest.parent / "loop.stl",
    )

    assert artwork_bounds[4:6] == pytest.approx(
        (
            2.0,
            5.0,
        )
    )

    assert loop_bounds[4:6] == pytest.approx(
        (
            2.0,
            7.0,
        )
    )


def test_explicit_base_and_loop_colors_preserve_independent_physical_identities(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Explicit Base and Loop colors remain independent when both Features
    participate.

    Each independently printable component preserves the complete physical
    printer color identity belonging to its explicitly selected semantic
    color.
    """

    vector_directory = tmp_path / "vector"
    svg = vector_directory / "layer.svg"

    vector_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    svg.write_text(
        "<svg/>",
        encoding="utf-8",
    )

    vector_manifest = vector_directory / "products.json"

    _write_vector_manifest(
        vector_manifest,
        [
            _product(
                index=1,
                path=svg.name,
                artifact_color_index=1,
                artifact_rgb=(
                    255,
                    0,
                    0,
                ),
                printer_color_name="red",
                printer_rgb=(
                    255,
                    0,
                    0,
                ),
                distance=0.0,
            )
        ],
    )

    extrude_manifest = tmp_path / "extrude" / "products.json"

    context = StubContext(
        inputs={
            "vector.manifest": vector_manifest,
        },
        outputs={
            "manifest": extrude_manifest,
        },
        resolver=_resolver(
            tmp_path,
            artwork_size=100.0,
            artwork_raise=1.0,
            artwork_base_raise=1.5,
            artwork_base_color="test-yellow",
            loop_inner_diameter=5.0,
            loop_width=2.0,
            loop_position=0,
            loop_raise=1.0,
            loop_color="test-black",
        ),
    )

    monkeypatch.setattr(
        extrude,
        "render_stl_source",
        _fake_render_stl_source,
    )

    extrude.execute(context)  # type: ignore[arg-type]

    manifest = json.loads(
        extrude_manifest.read_text(
            encoding="utf-8",
        )
    )

    base = next(product for product in manifest["products"] if product["path"] == "base.stl")

    loop = next(product for product in manifest["products"] if product["path"] == "loop.stl")

    assert base["printer_color"] == {
        "name": "test-yellow",
        "rgb": {
            "red": 255,
            "green": 255,
            "blue": 0,
        },
    }

    assert loop["printer_color"] == {
        "name": "test-black",
        "rgb": {
            "red": 0,
            "green": 0,
            "blue": 0,
        },
    }
