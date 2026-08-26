"""
Tests for the artwork vector stage.

These tests characterize the storage boundary between the build engine
and the vector-stage implementation.

The vector stage must consume only the paths supplied through
StageContext. Dynamic SVG products are stage-local products whose
locations are determined by the declared vector manifest.
"""
# File: tests/model/test_vector.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from PIL import Image

from lowkey_artifact_builder.model.models.artwork.stages import vector

# =========================================================
# Test support
# =========================================================


class StubResolver:
    """
    Minimal Resolver-compatible object for vector-stage tests.
    """

    def __init__(
        self,
        values: dict[str, Any],
    ) -> None:
        self._values = values

    def __call__(
        self,
        name: str,
    ) -> Any:
        return self._values[name]


class StubContext:
    """
    Minimal StageContext-compatible object for vector-stage tests.
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


def _color(
    red: int,
    green: int,
    blue: int,
) -> dict[str, int]:
    """
    Return a raster-manifest RGB color.
    """

    return {
        "red": red,
        "green": green,
        "blue": blue,
    }


def _write_raster(
    path: Path,
    *,
    box: tuple[int, int, int, int],
) -> None:
    """
    Write a simple transparent raster containing opaque geometry.
    """

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    image = Image.new(
        "RGBA",
        (20, 20),
        (0, 0, 0, 0),
    )

    try:
        pixels = image.load()

        assert pixels is not None

        left, top, right, bottom = box

        for y in range(top, bottom):
            for x in range(left, right):
                pixels[x, y] = (255, 255, 255, 255)

        image.save(
            path,
            format="PNG",
        )

    finally:
        image.close()


def _write_raster_manifest(
    path: Path,
    products: list[dict[str, Any]],
) -> None:
    """
    Write a minimal raster manifest.
    """

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        json.dumps(
            {
                "products": products,
            }
        ),
        encoding="utf-8",
    )


def _resolver() -> StubResolver:
    """
    Return standard vector-stage configuration.
    """

    return StubResolver({})


# =========================================================
# Storage-boundary tests
# =========================================================


def test_vector_uses_declared_raster_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    The vector stage consumes the raster manifest supplied by
    StageContext without reconstructing its filesystem location.
    """

    raster_directory = tmp_path / "deliberately" / "unrelated" / "raster-input"

    raster = raster_directory / "layer.png"

    _write_raster(
        raster,
        box=(4, 5, 14, 15),
    )

    raster_manifest = raster_directory / "anything.json"

    _write_raster_manifest(
        raster_manifest,
        [
            {
                "index": 1,
                "path": raster.name,
                "name": "white",
                "color": _color(
                    255,
                    255,
                    255,
                ),
            }
        ],
    )

    vector_manifest = tmp_path / "completely-different" / "vector-output" / "manifest.json"

    context = StubContext(
        inputs={
            "raster.manifest": raster_manifest,
        },
        outputs={
            "manifest": vector_manifest,
        },
        resolver=_resolver(),
    )

    traced_sources: list[Path] = []

    def fake_trace_mask(
        source: Path,
        output: Path,
        *,
        crop: vector.RasterCrop,
    ) -> None:
        traced_sources.append(source)

        output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        output.write_text(
            "<svg/>",
            encoding="utf-8",
        )

    monkeypatch.setattr(
        vector,
        "_trace_mask",
        fake_trace_mask,
    )

    vector.execute(context)  # type: ignore[arg-type]

    assert traced_sources == [
        raster,
    ]

    assert vector_manifest.is_file()


def test_vector_places_dynamic_svgs_beside_declared_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Dynamic SVG products are placed beside the vector manifest supplied
    by StageContext.
    """

    raster_directory = tmp_path / "raster"

    first_raster = raster_directory / "first.png"
    second_raster = raster_directory / "second.png"

    _write_raster(
        first_raster,
        box=(3, 3, 12, 12),
    )

    _write_raster(
        second_raster,
        box=(8, 8, 17, 17),
    )

    raster_manifest = raster_directory / "products.json"

    _write_raster_manifest(
        raster_manifest,
        [
            {
                "index": 2,
                "path": second_raster.name,
                "name": "black",
                "color": _color(
                    0,
                    0,
                    0,
                ),
            },
            {
                "index": 1,
                "path": first_raster.name,
                "name": "white",
                "color": _color(
                    255,
                    255,
                    255,
                ),
            },
        ],
    )

    output_directory = tmp_path / "arbitrary" / "vector-products"

    vector_manifest = output_directory / "custom-name.json"

    context = StubContext(
        inputs={
            "raster.manifest": raster_manifest,
        },
        outputs={
            "manifest": vector_manifest,
        },
        resolver=_resolver(),
    )

    traced_outputs: list[Path] = []

    def fake_trace_mask(
        source: Path,
        output: Path,
        *,
        crop: vector.RasterCrop,
    ) -> None:
        traced_outputs.append(output)

        output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        output.write_text(
            "<svg/>",
            encoding="utf-8",
        )

    monkeypatch.setattr(
        vector,
        "_trace_mask",
        fake_trace_mask,
    )

    vector.execute(context)  # type: ignore[arg-type]

    assert traced_outputs == [
        output_directory / "color-1.svg",
        output_directory / "color-2.svg",
    ]

    assert all(path.is_file() for path in traced_outputs)


def test_vector_manifest_describes_stage_local_products(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    The vector manifest records dynamic SVG products using filenames
    relative to the manifest rather than canonical artifact paths.
    """

    raster_directory = tmp_path / "input"

    raster = raster_directory / "layer.png"

    _write_raster(
        raster,
        box=(5, 5, 15, 15),
    )

    raster_manifest = raster_directory / "manifest.json"

    _write_raster_manifest(
        raster_manifest,
        [
            {
                "index": 1,
                "path": raster.name,
                "name": "gold",
                "color": _color(
                    255,
                    215,
                    0,
                ),
            }
        ],
    )

    vector_manifest = tmp_path / "wherever" / "vectors" / "products.json"

    context = StubContext(
        inputs={
            "raster.manifest": raster_manifest,
        },
        outputs={
            "manifest": vector_manifest,
        },
        resolver=_resolver(),
    )

    def fake_trace_mask(
        source: Path,
        output: Path,
        *,
        crop: vector.RasterCrop,
    ) -> None:
        output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        output.write_text(
            "<svg/>",
            encoding="utf-8",
        )

    monkeypatch.setattr(
        vector,
        "_trace_mask",
        fake_trace_mask,
    )

    vector.execute(context)  # type: ignore[arg-type]

    data = json.loads(
        vector_manifest.read_text(
            encoding="utf-8",
        )
    )

    assert data == {
        "products": [
            {
                "index": 1,
                "path": "color-1.svg",
                "name": "gold",
                "color": {
                    "red": 255,
                    "green": 215,
                    "blue": 0,
                },
            }
        ],
    }


# =========================================================
# Registered-geometry tests
# =========================================================


def test_vector_generation_is_independent_of_physical_size(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Vector generation operates entirely in registered geometry.

    Physical artwork size is not required to trace raster layers into
    registered vector products.
    """

    raster_directory = tmp_path / "raster"

    raster = raster_directory / "layer.png"

    _write_raster(
        raster,
        box=(5, 5, 15, 15),
    )

    raster_manifest = raster_directory / "products.json"

    _write_raster_manifest(
        raster_manifest,
        [
            {
                "index": 1,
                "path": raster.name,
                "name": "white",
                "color": _color(
                    255,
                    255,
                    255,
                ),
            }
        ],
    )

    vector_manifest = tmp_path / "vector" / "products.json"

    context = StubContext(
        inputs={
            "raster.manifest": raster_manifest,
        },
        outputs={
            "manifest": vector_manifest,
        },
        resolver=StubResolver({}),
    )

    observed_crop: vector.RasterCrop | None = None

    def fake_trace_mask(
        source: Path,
        output: Path,
        *,
        crop: vector.RasterCrop,
    ) -> None:
        nonlocal observed_crop

        observed_crop = crop

        output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        output.write_text(
            "<svg/>",
            encoding="utf-8",
        )

    monkeypatch.setattr(
        vector,
        "_trace_mask",
        fake_trace_mask,
    )

    vector.execute(context)  # type: ignore[arg-type]

    assert observed_crop == vector.RasterCrop(
        x=5,
        y=5,
        size=10,
    )

    assert vector_manifest.is_file()
