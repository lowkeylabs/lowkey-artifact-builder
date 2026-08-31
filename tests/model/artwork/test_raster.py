"""
Tests for the artwork raster stage.

These tests characterize the storage boundary between the build engine
and the raster-stage implementation.

The raster stage must consume only the paths supplied through
StageContext. Dynamic PNG products are stage-local products whose
locations are determined by the declared raster manifest.
"""
# File: tests/model/test_raster.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from PIL import Image

from lowkey_artifact_builder.colors import PaletteColor
from lowkey_artifact_builder.model.models.artwork.stages import raster

# =========================================================
# Test support
# =========================================================


class StubResolver:
    """
    Minimal Resolver-compatible object for raster-stage tests.
    """

    def __init__(
        self,
        values: dict[str, Any],
    ) -> None:
        self._values = values

        self.colors = {
            "white": {
                "red": 255,
                "green": 255,
                "blue": 255,
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
            "artwork_colors": [
                "white",
            ],
            "artwork_pixels": 20,
            "artwork_min_island_area": 4,
            "artwork_island_connectivity": 8,
        }
    )


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


def _assignment(
    *,
    measured: tuple[int, int, int] = (
        255,
        255,
        255,
    ),
    distance: float = 0.0,
) -> raster.ColorAssignment:
    """
    Return a real color assignment for raster-stage tests.
    """

    return raster.ColorAssignment(
        measured=raster.MeasuredColor(
            index=1,
            rgb=measured,
        ),
        color=PaletteColor(
            name="white",
            rgb=(
                255,
                255,
                255,
            ),
        ),
        distance=distance,
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

    monkeypatch.setattr(
        raster,
        "resolve_palette",
        lambda names, colors: ("palette",),
    )

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
        "get_trace_objects",
        lambda tree: ["object-1"],
    )

    monkeypatch.setattr(
        raster,
        "get_fill_rgb",
        lambda tree, object_id: (255, 255, 255),
    )

    assignment = _assignment()

    monkeypatch.setattr(
        raster,
        "assign_colors",
        lambda measured, palette: (assignment,),
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
        lambda path, layers, assignments, *, pixels, bounds: path.write_text(
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
        "resolve_palette",
        lambda names, colors: ("palette",),
    )

    monkeypatch.setattr(
        raster,
        "load",
        lambda source: object(),
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

    assignment = _assignment()

    monkeypatch.setattr(
        raster,
        "assign_colors",
        lambda measured, palette: (assignment,),
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
        lambda path, layers, assignments, *, pixels, bounds: path.write_text(
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
    The raster manifest records dynamic PNG products using filenames
    relative to the manifest rather than canonical artifact paths.
    """

    output_directory = tmp_path / "wherever" / "rasters"

    layer = output_directory / "color-1.png"

    _write_layer(layer)

    manifest = output_directory / "products.json"

    assignment = _assignment(
        measured=(
            250,
            250,
            250,
        ),
        distance=1.25,
    )

    bounds = raster.RasterBounds(
        x=2.5,
        y=3.5,
        size=20.0,
    )

    raster._write_manifest(
        manifest,
        [layer],
        (assignment,),
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
                "name": "white",
                "color": {
                    "red": 255,
                    "green": 255,
                    "blue": 255,
                },
                "trace_color": {
                    "red": 250,
                    "green": 250,
                    "blue": 250,
                },
                "distance": 1.25,
            }
        ],
    }


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

    assignment = _assignment()

    bounds = raster.RasterBounds(
        x=12.5,
        y=7.5,
        size=80.0,
    )

    raster._write_manifest(
        manifest,
        [layer],
        (assignment,),
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
