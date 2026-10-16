"""
Tests for the artwork raster stage.

These tests characterize the storage boundary between the build engine
and the raster-stage implementation.

The raster stage must consume only the paths supplied through
StageContext. Dynamic PNG products are stage-local products whose
locations are determined by the declared raster manifest.
"""
# File: tests/model/artwork/test_raster.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from PIL import Image

from lowkey_artifact_builder.model.models.artwork.stages import raster

# =========================================================
# Test support
# =========================================================


class StubResolver:
    """
    Minimal configuration resolver for raster-stage tests.
    """

    def __init__(
        self,
        values: dict[str, Any],
        *,
        colors: dict[str, dict[str, Any]] | None = None,
    ) -> None:
        self._values = values

        self.colors = colors or {
            "white": {
                "rgb": [
                    255,
                    255,
                    255,
                ],
            },
        }

    def __call__(
        self,
        name: str,
    ) -> Any:
        return self._values[name]


class StubContext:
    """
    Minimal StageContext-compatible object for raster-stage tests.
    """

    def __init__(
        self,
        *,
        inputs: dict[str, Path],
        outputs: dict[str, Path],
        resolver: StubResolver,
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


def _resolver() -> StubResolver:
    """
    Return standard raster-stage configuration.
    """

    return StubResolver(
        {
            "artwork_pixels": 20,
            "artwork_min_island_area": 4,
            "artwork_island_connectivity": 8,
        }
    )


def _execute_native_svg(
    tmp_path: Path,
    paths: str,
) -> Path:
    """
    Execute Raster against authored native SVG paths.

    Return the declared Raster manifest path.
    """

    trace = tmp_path / "prepare" / "trace.svg"
    trace.parent.mkdir(parents=True, exist_ok=True)

    trace.write_text(
        (
            '<svg xmlns="http://www.w3.org/2000/svg" '
            'width="100" height="100" '
            'viewBox="0 0 100 100">'
            f"{paths}"
            "</svg>"
        ),
        encoding="utf-8",
    )

    manifest = tmp_path / "raster" / "products.json"

    context = StubContext(
        inputs={"prepare.trace": trace},
        outputs={"manifest": manifest},
        resolver=_resolver(),
    )

    raster.execute(context)  # type: ignore[arg-type]

    return manifest


def _write_layer(
    path: Path,
) -> None:
    """
    Write a simple opaque raster layer.
    """

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    image = Image.new(
        "RGBA",
        (20, 20),
        (255, 255, 255, 255),
    )

    try:
        image.save(
            path,
            format="PNG",
        )

    finally:
        image.close()


def _execute_stubbed_raster(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    resolver: StubResolver,
    trace_colors: tuple[
        tuple[int, int, int],
        ...,
    ],
) -> dict[str, Any]:
    """
    Execute Raster with geometry operations stubbed.

    Real color assignment and manifest production remain active.
    """

    trace = tmp_path / "prepare" / "trace.svg"

    trace.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    trace.write_text(
        "<svg/>",
        encoding="utf-8",
    )

    manifest = tmp_path / "raster" / "products.json"

    context = StubContext(
        inputs={
            "prepare.trace": trace,
        },
        outputs={
            "manifest": manifest,
        },
        resolver=resolver,
    )

    objects = [
        f"object-{index}"
        for index in range(
            1,
            len(trace_colors) + 1,
        )
    ]

    color_by_object = dict(
        zip(
            objects,
            trace_colors,
            strict=True,
        )
    )

    monkeypatch.setattr(
        raster,
        "load",
        lambda source: object(),
    )

    monkeypatch.setattr(
        raster,
        "_is_native_svg",
        lambda tree: False,
    )

    monkeypatch.setattr(
        raster,
        "get_trace_objects",
        lambda tree: objects,
    )

    monkeypatch.setattr(
        raster,
        "get_fill_rgb",
        lambda tree, object_id: color_by_object[object_id],
    )

    monkeypatch.setattr(
        raster,
        "_square_bounds",
        lambda source, selected_objects: raster.RasterBounds(
            x=0.0,
            y=0.0,
            size=20.0,
        ),
    )

    def fake_render_layers(
        source: Path,
        selected_objects: list[str],
        colors: tuple[tuple[int, int, int], ...],
        *,
        directory: Path,
        bounds: raster.RasterBounds,
        pixels: int,
    ) -> list[Path]:
        outputs: list[Path] = []

        for index, color in enumerate(
            colors,
            start=1,
        ):
            output = directory / f"color-{index}.png"

            output.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            image = Image.new(
                "RGBA",
                (
                    pixels,
                    pixels,
                ),
                (
                    color[0],
                    color[1],
                    color[2],
                    255,
                ),
            )

            try:
                image.save(
                    output,
                    format="PNG",
                )

            finally:
                image.close()

            outputs.append(output)

        return outputs

    monkeypatch.setattr(
        raster,
        "_render_layers",
        fake_render_layers,
    )

    monkeypatch.setattr(
        raster,
        "_cleanup_layers",
        lambda layers, **kwargs: None,
    )

    raster.execute(context)  # type: ignore[arg-type]

    return json.loads(
        manifest.read_text(
            encoding="utf-8",
        )
    )


# =========================================================
# Storage-boundary tests
# =========================================================


def test_raster_uses_declared_prepare_trace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    The raster stage consumes the prepared trace supplied by
    StageContext without reconstructing its filesystem location.
    """

    trace = tmp_path / "deliberately" / "unrelated" / "prepare-output" / "anything.svg"

    trace.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    trace.write_text(
        "<svg/>",
        encoding="utf-8",
    )

    manifest = tmp_path / "completely-different" / "raster-output" / "manifest.json"

    context = StubContext(
        inputs={
            "prepare.trace": trace,
        },
        outputs={
            "manifest": manifest,
        },
        resolver=_resolver(),
    )

    loaded_sources: list[Path] = []

    def fake_load(
        source: Path,
    ) -> object:
        loaded_sources.append(source)

        return object()

    monkeypatch.setattr(
        raster,
        "load",
        fake_load,
    )

    monkeypatch.setattr(
        raster,
        "_is_native_svg",
        lambda tree: False,
    )

    monkeypatch.setattr(
        raster,
        "get_trace_objects",
        lambda tree: ["object-1"],
    )

    monkeypatch.setattr(
        raster,
        "get_fill_rgb",
        lambda tree, object_id: (255, 255, 255),
    )

    monkeypatch.setattr(
        raster,
        "_square_bounds",
        lambda source, objects: raster.RasterBounds(
            x=0.0,
            y=0.0,
            size=20.0,
        ),
    )

    def fake_render_layers(
        source: Path,
        objects: list[str],
        colors: tuple[tuple[int, int, int], ...],
        *,
        directory: Path,
        bounds: raster.RasterBounds,
        pixels: int,
    ) -> list[Path]:
        output = directory / "color-1.png"

        _write_layer(output)

        return [output]

    monkeypatch.setattr(
        raster,
        "_render_layers",
        fake_render_layers,
    )

    monkeypatch.setattr(
        raster,
        "_cleanup_layers",
        lambda layers, **kwargs: None,
    )

    monkeypatch.setattr(
        raster,
        "_write_manifest",
        lambda path, layers, artifact_colors, **kwargs: path.write_text(
            "{}",
            encoding="utf-8",
        ),
    )

    raster.execute(context)  # type: ignore[arg-type]

    assert loaded_sources == [
        trace,
    ]

    assert manifest.is_file()


def test_raster_places_dynamic_pngs_beside_declared_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Dynamic PNG products are placed beside the raster manifest supplied
    by StageContext.
    """

    trace = tmp_path / "input" / "trace.svg"

    trace.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    trace.write_text(
        "<svg/>",
        encoding="utf-8",
    )

    output_directory = tmp_path / "arbitrary" / "raster-products"

    manifest = output_directory / "custom-name.json"

    context = StubContext(
        inputs={
            "prepare.trace": trace,
        },
        outputs={
            "manifest": manifest,
        },
        resolver=_resolver(),
    )

    monkeypatch.setattr(
        raster,
        "load",
        lambda source: object(),
    )

    monkeypatch.setattr(
        raster,
        "_is_native_svg",
        lambda tree: False,
    )

    monkeypatch.setattr(
        raster,
        "get_trace_objects",
        lambda tree: ["object-1"],
    )

    monkeypatch.setattr(
        raster,
        "get_fill_rgb",
        lambda tree, object_id: (255, 255, 255),
    )

    monkeypatch.setattr(
        raster,
        "_square_bounds",
        lambda source, objects: raster.RasterBounds(
            x=0.0,
            y=0.0,
            size=20.0,
        ),
    )

    observed_directory: Path | None = None

    def fake_render_layers(
        source: Path,
        objects: list[str],
        colors: tuple[tuple[int, int, int], ...],
        *,
        directory: Path,
        bounds: raster.RasterBounds,
        pixels: int,
    ) -> list[Path]:
        nonlocal observed_directory

        observed_directory = directory

        output = directory / "color-1.png"

        _write_layer(output)

        return [output]

    monkeypatch.setattr(
        raster,
        "_render_layers",
        fake_render_layers,
    )

    monkeypatch.setattr(
        raster,
        "_cleanup_layers",
        lambda layers, **kwargs: None,
    )

    monkeypatch.setattr(
        raster,
        "_write_manifest",
        lambda path, layers, artifact_colors, **kwargs: path.write_text(
            "{}",
            encoding="utf-8",
        ),
    )

    raster.execute(context)  # type: ignore[arg-type]

    assert observed_directory == output_directory

    assert (output_directory / "color-1.png").is_file()


def test_raster_manifest_describes_stage_local_products(
    tmp_path: Path,
) -> None:
    """
    The raster manifest records registered Artifact-color products.

    Raster products use paths relative to the manifest and preserve Artifact
    color identity without physical printer-color assignment.
    """

    output_directory = tmp_path / "wherever" / "rasters"

    layer = output_directory / "color-1.png"

    _write_layer(layer)

    manifest = output_directory / "products.json"

    artifact_colors = (
        raster.MeasuredColor(
            index=1,
            rgb=(250, 250, 250),
        ),
    )

    bounds = raster.RasterBounds(
        x=2.5,
        y=3.5,
        size=20.0,
    )

    raster._write_manifest(
        manifest,
        [layer],
        artifact_colors,
        pixels=20,
        bounds=bounds,
    )

    data = json.loads(
        manifest.read_text(
            encoding="utf-8",
        )
    )

    assert data == {
        "pixels": 20,
        "registration": {
            "x": 2.5,
            "y": 3.5,
            "size": 20.0,
            "pixels": 20,
        },
        "products": [
            {
                "index": 1,
                "path": "color-1.png",
                "artifact_color": {
                    "index": 1,
                    "rgb": {
                        "red": 250,
                        "green": 250,
                        "blue": 250,
                    },
                },
            }
        ],
    }


def test_raster_manifest_excludes_physical_printer_assignment(
    tmp_path: Path,
) -> None:
    """
    Raster products do not contain physical printer-color assignment.

    Physical printer colors do not affect raster geometry and belong to
    downstream packaging.
    """

    output_directory = tmp_path / "rasters"

    layer = output_directory / "color-1.png"

    _write_layer(layer)

    manifest = output_directory / "products.json"

    artifact_color = raster.MeasuredColor(
        index=1,
        rgb=(
            17,
            43,
            91,
        ),
    )

    raster._write_manifest(
        manifest,
        [layer],
        (artifact_color,),
        pixels=20,
        bounds=raster.RasterBounds(
            x=0.0,
            y=0.0,
            size=20.0,
        ),
    )

    data = json.loads(
        manifest.read_text(
            encoding="utf-8",
        )
    )

    product = data["products"][0]

    assert "printer_assignment" not in data
    assert "printer_color" not in product
    assert "distance" not in product


# =========================================================
# Island-cleanup tests
# =========================================================


def test_cleanup_layers_uses_raster_pixel_area(
    tmp_path: Path,
) -> None:
    """
    Island cleanup uses raster pixel area rather than physical size.

    An island smaller than the configured pixel-area threshold is
    removed, while an island meeting the threshold is preserved.
    """

    path = tmp_path / "layer.png"

    image = Image.new(
        "RGBA",
        (10, 10),
        (255, 255, 255, 0),
    )

    try:
        pixels = image.load()

        assert pixels is not None

        # Three-pixel island.
        pixels[1, 1] = (255, 255, 255, 255)
        pixels[1, 2] = (255, 255, 255, 255)
        pixels[2, 1] = (255, 255, 255, 255)

        # Four-pixel island.
        pixels[6, 6] = (255, 255, 255, 255)
        pixels[6, 7] = (255, 255, 255, 255)
        pixels[7, 6] = (255, 255, 255, 255)
        pixels[7, 7] = (255, 255, 255, 255)

        image.save(
            path,
            format="PNG",
        )

    finally:
        image.close()

    raster._cleanup_layers(
        [path],
        minimum_area=4,
        connectivity=4,
    )

    with Image.open(path) as result:
        alpha = result.getchannel("A")

        try:
            assert alpha.getpixel((1, 1)) == 0
            assert alpha.getpixel((6, 6)) == 255

        finally:
            alpha.close()


def test_raster_manifest_records_source_registration_bounds(
    tmp_path: Path,
) -> None:
    """
    Raster products record the source bounds used to register their pixels.

    Downstream consumers must be able to map source-coordinate geometry into
    the raster coordinate system without reconstructing raster-stage policy.
    """

    output_directory = tmp_path / "rasters"

    layer = output_directory / "color-1.png"

    _write_layer(
        layer,
    )

    manifest = output_directory / "products.json"

    artifact_color = raster.MeasuredColor(
        index=1,
        rgb=(255, 255, 255),
    )

    bounds = raster.RasterBounds(
        x=12.5,
        y=7.5,
        size=80.0,
    )

    raster._write_manifest(
        manifest,
        [layer],
        (artifact_color,),
        pixels=100,
        bounds=bounds,
    )

    data = json.loads(
        manifest.read_text(
            encoding="utf-8",
        )
    )

    assert data["registration"] == {
        "x": 12.5,
        "y": 7.5,
        "size": 80.0,
        "pixels": 100,
    }


# =========================================================
# Artifact-color persistence tests
# =========================================================


def test_raster_manifest_records_one_artifact_color_per_traced_region(
    tmp_path: Path,
) -> None:
    """
    Each traced color region has one stable Artifact color identity.

    Artifact color identity is derived from traced-region identity rather
    than from a configured physical filament color.
    """

    output_directory = tmp_path / "rasters"

    layers = [
        output_directory / "color-1.png",
        output_directory / "color-2.png",
        output_directory / "color-3.png",
    ]

    for layer in layers:
        _write_layer(layer)

    manifest = output_directory / "products.json"

    artifact_colors = (
        raster.MeasuredColor(
            index=1,
            rgb=(17, 43, 91),
        ),
        raster.MeasuredColor(
            index=2,
            rgb=(103, 47, 29),
        ),
        raster.MeasuredColor(
            index=3,
            rgb=(211, 173, 61),
        ),
    )

    raster._write_manifest(
        manifest,
        layers,
        artifact_colors,
        pixels=20,
        bounds=raster.RasterBounds(
            x=0.0,
            y=0.0,
            size=20.0,
        ),
    )

    data = json.loads(
        manifest.read_text(
            encoding="utf-8",
        )
    )

    assert [product["artifact_color"]["index"] for product in data["products"]] == [
        1,
        2,
        3,
    ]


def test_raster_manifest_preserves_traced_rgb_as_artifact_rgb(
    tmp_path: Path,
) -> None:
    """
    Artifact RGB is the RGB discovered by multicolor tracing.

    Physical printer-color assignment is not part of the raster product.
    """

    output_directory = tmp_path / "rasters"

    layer = output_directory / "color-1.png"

    _write_layer(layer)

    manifest = output_directory / "products.json"

    artifact_color = raster.MeasuredColor(
        index=1,
        rgb=(
            17,
            43,
            91,
        ),
    )

    raster._write_manifest(
        manifest,
        [layer],
        (artifact_color,),
        pixels=20,
        bounds=raster.RasterBounds(
            x=0.0,
            y=0.0,
            size=20.0,
        ),
    )

    data = json.loads(
        manifest.read_text(
            encoding="utf-8",
        )
    )

    product = data["products"][0]

    assert product["artifact_color"] == {
        "index": 1,
        "rgb": {
            "red": 17,
            "green": 43,
            "blue": 91,
        },
    }


def test_raster_executes_without_printer_colors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Rasterization does not require physical printer-color configuration.

    Raster owns registered Artifact-color geometry. Physical printer-color
    assignment is downstream packaging configuration.
    """

    resolver = StubResolver(
        {
            "artwork_pixels": 20,
            "artwork_min_island_area": 4,
            "artwork_island_connectivity": 8,
        }
    )

    data = _execute_stubbed_raster(
        tmp_path,
        monkeypatch,
        resolver=resolver,
        trace_colors=(
            (17, 43, 91),
            (103, 47, 29),
            (211, 173, 61),
        ),
    )

    assert [product["artifact_color"]["rgb"] for product in data["products"]] == [
        {
            "red": 17,
            "green": 43,
            "blue": 91,
        },
        {
            "red": 103,
            "green": 47,
            "blue": 29,
        },
        {
            "red": 211,
            "green": 173,
            "blue": 61,
        },
    ]


def test_raster_native_svg_preserves_authored_colors_without_rasterization(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Native SVG passes through Raster without PNG rendering or tracing.

    The manifest identifies the native source and its authored color
    regions for subsequent registered-vector processing.
    """

    trace = tmp_path / "prepare" / "trace.svg"
    trace.parent.mkdir(parents=True)

    trace.write_text(
        """
        <svg xmlns="http://www.w3.org/2000/svg"
             width="100" height="100"
             viewBox="0 0 100 100">
          <g transform="translate(10, 5)">
            <path id="red-region"
                  d="M 0 0 H 60 V 60 H 0 Z
                     M 20 20 H 40 V 40 H 20 Z"
                  fill="#ff0000"
                  fill-rule="evenodd"/>
          </g>
          <path id="blue-region"
                d="M 70 70 H 90 V 90 H 70 Z"
                fill="#0000ff"/>
        </svg>
        """,
        encoding="utf-8",
    )

    manifest = tmp_path / "raster" / "products.json"

    context = StubContext(
        inputs={"prepare.trace": trace},
        outputs={"manifest": manifest},
        resolver=_resolver(),
    )

    def unexpected_rasterization(
        *args: Any,
        **kwargs: Any,
    ) -> None:
        pytest.fail("Native SVG must not generate raster layers.")

    monkeypatch.setattr(
        raster,
        "_render_layers",
        unexpected_rasterization,
    )

    monkeypatch.setattr(
        raster,
        "_cleanup_layers",
        unexpected_rasterization,
    )

    raster.execute(context)  # type: ignore[arg-type]

    assert manifest.is_file()

    data = json.loads(manifest.read_text(encoding="utf-8"))

    assert data["representation"] == "native-svg"

    source = data["source"]

    assert isinstance(source, str)
    assert (manifest.parent / source).resolve() == trace.resolve()

    products = data["products"]

    assert len(products) == 2

    assert [product["artifact_color"] for product in products] == [
        {
            "index": 1,
            "rgb": {"red": 255, "green": 0, "blue": 0},
        },
        {
            "index": 2,
            "rgb": {"red": 0, "green": 0, "blue": 255},
        },
    ]

    assert {product["object_id"] for product in products} == {"red-region", "blue-region"}

    assert not list(manifest.parent.glob("color-*.png"))


def test_raster_native_svg_groups_objects_by_authored_color(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Separate SVG objects with the same authored RGB share one
    Artifact-color identity without losing their object identities.
    """

    trace = tmp_path / "prepare" / "trace.svg"
    trace.parent.mkdir(parents=True)

    trace.write_text(
        """
        <svg xmlns="http://www.w3.org/2000/svg"
             width="100" height="100"
             viewBox="0 0 100 100">
          <path id="red-left"
                d="M 0 0 H 20 V 20 H 0 Z"
                fill="#ff0000"/>
          <path id="blue-middle"
                d="M 30 0 H 50 V 20 H 30 Z"
                fill="#0000ff"/>
          <path id="red-right"
                d="M 60 0 H 80 V 20 H 60 Z"
                fill="#ff0000"/>
        </svg>
        """,
        encoding="utf-8",
    )

    manifest = tmp_path / "raster" / "products.json"

    context = StubContext(
        inputs={"prepare.trace": trace},
        outputs={"manifest": manifest},
        resolver=_resolver(),
    )

    def unexpected_rasterization(
        *args: Any,
        **kwargs: Any,
    ) -> None:
        pytest.fail("Native SVG must not generate raster layers.")

    monkeypatch.setattr(
        raster,
        "_render_layers",
        unexpected_rasterization,
    )

    monkeypatch.setattr(
        raster,
        "_cleanup_layers",
        unexpected_rasterization,
    )

    raster.execute(context)  # type: ignore[arg-type]

    data = json.loads(manifest.read_text(encoding="utf-8"))

    products = data["products"]

    assert len(products) == 3

    by_object = {product["object_id"]: product["artifact_color"] for product in products}

    assert by_object["red-left"] == by_object["red-right"]

    assert by_object["red-left"] != by_object["blue-middle"]

    assert {color["index"] for color in by_object.values()} == {1, 2}

    assert not list(manifest.parent.glob("color-*.png"))


def test_raster_native_svg_rejects_overlapping_color_regions(
    tmp_path: Path,
) -> None:
    """
    Filled regions of different Artifact colors must not overlap.

    Raster must reject the source without publishing a manifest.
    """

    paths = (
        '<path id="red" '
        'd="M 0 0 H 80 V 80 H 0 Z" '
        'fill="#ff0000"/>'
        '<path id="blue" '
        'd="M 40 40 H 100 V 100 H 40 Z" '
        'fill="#0000ff"/>'
    )

    with pytest.raises(
        raster.RasterError,
        match=r"(?i)overlap",
    ):
        _execute_native_svg(tmp_path, paths)

    assert not (tmp_path / "raster" / "products.json").exists()


def test_raster_native_svg_accepts_shared_color_boundaries(
    tmp_path: Path,
) -> None:
    """
    Different Artifact colors may share boundaries without
    overlapping filled interiors.
    """

    paths = (
        '<path id="red" '
        'd="M 0 0 H 50 V 100 H 0 Z" '
        'fill="#ff0000"/>'
        '<path id="blue" '
        'd="M 50 0 H 100 V 100 H 50 Z" '
        'fill="#0000ff"/>'
    )

    manifest = _execute_native_svg(tmp_path, paths)

    data = json.loads(manifest.read_text(encoding="utf-8"))

    assert data["representation"] == "native-svg"
    assert len(data["products"]) == 2

    assert {product["object_id"] for product in data["products"]} == {"red", "blue"}


def test_raster_native_svg_excludes_holes_from_overlap(
    tmp_path: Path,
) -> None:
    """
    A different-color region entirely inside an evenodd hole
    does not overlap the surrounding filled region.
    """

    paths = (
        '<path id="red-ring" '
        'd="M 0 0 H 100 V 100 H 0 Z '
        'M 30 30 H 70 V 70 H 30 Z" '
        'fill="#ff0000" '
        'fill-rule="evenodd"/>'
        '<path id="blue-center" '
        'd="M 40 40 H 60 V 60 H 40 Z" '
        'fill="#0000ff"/>'
    )

    manifest = _execute_native_svg(tmp_path, paths)

    data = json.loads(manifest.read_text(encoding="utf-8"))

    assert len(data["products"]) == 2

    assert {product["object_id"] for product in data["products"]} == {"red-ring", "blue-center"}


def test_raster_native_svg_rejects_overlap_after_transform(
    tmp_path: Path,
) -> None:
    """
    Overlap validation must evaluate transformed geometry
    in common document coordinates.
    """

    paths = (
        '<path id="red" '
        'd="M 0 0 H 40 V 40 H 0 Z" '
        'fill="#ff0000"/>'
        '<g transform="translate(20, 20)">'
        '<path id="blue" '
        'd="M 0 0 H 40 V 40 H 0 Z" '
        'fill="#0000ff"/>'
        "</g>"
    )

    with pytest.raises(
        raster.RasterError,
        match=r"(?i)overlap",
    ):
        _execute_native_svg(tmp_path, paths)

    assert not (tmp_path / "raster" / "products.json").exists()


def test_raster_native_svg_accepts_same_color_overlap(
    tmp_path: Path,
) -> None:
    """
    Overlapping SVG objects with the same authored RGB
    share one Artifact-color identity and are permitted.
    """

    paths = (
        '<path id="red-left" '
        'd="M 0 0 H 60 V 60 H 0 Z" '
        'fill="#ff0000"/>'
        '<path id="red-right" '
        'd="M 40 40 H 100 V 100 H 40 Z" '
        'fill="#ff0000"/>'
    )

    manifest = _execute_native_svg(tmp_path, paths)

    data = json.loads(manifest.read_text(encoding="utf-8"))

    products = data["products"]

    assert len(products) == 2

    assert {product["object_id"] for product in products} == {"red-left", "red-right"}

    assert products[0]["artifact_color"] == products[1]["artifact_color"]
