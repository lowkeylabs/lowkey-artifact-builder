"""
Tests for the artwork vector stage.

These tests characterize the storage boundary between the build engine
and the vector-stage implementation.

The vector stage must consume only the paths supplied through
StageContext. Dynamic registered Artwork products are stage-local
products whose locations are determined by the declared vector manifest.
"""
# File: tests/model/artwork/test_vector.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import pytest
from PIL import Image

from lowkey_artifact_builder.model.models.artwork.stages import vector
from lowkey_artifact_builder.model.models.shape.stages import compose

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
    Write a minimal raster manifest with identity source registration.
    """

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        json.dumps(
            {
                "registration": {
                    "x": 0.0,
                    "y": 0.0,
                    "size": 20.0,
                    "pixels": 20,
                },
                "products": products,
            }
        ),
        encoding="utf-8",
    )


def _write_prepared_envelope(
    path: Path,
) -> None:
    """
    Write a minimal prepared Artwork envelope.
    """

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        (
            '<svg xmlns="http://www.w3.org/2000/svg" '
            'width="20" '
            'height="20" '
            'viewBox="0 0 20 20">'
            '<rect x="5" y="5" width="10" height="10"/>'
            "</svg>"
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
    The vector stage consumes declared inputs supplied by StageContext
    without reconstructing their filesystem locations.
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

    prepared_envelope = tmp_path / "another" / "unrelated" / "prepared-envelope.svg"

    _write_prepared_envelope(
        prepared_envelope,
    )

    vector_manifest = tmp_path / "completely-different" / "vector-output" / "manifest.json"

    context = StubContext(
        inputs={
            "raster.manifest": raster_manifest,
            "prepare.envelope": prepared_envelope,
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
        traced_sources.append(
            source,
        )

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

    vector.execute(
        context,  # type: ignore[arg-type]
    )

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

    prepared_envelope = tmp_path / "prepare" / "envelope.svg"

    _write_prepared_envelope(
        prepared_envelope,
    )

    output_directory = tmp_path / "arbitrary" / "vector-products"

    vector_manifest = output_directory / "custom-name.json"

    context = StubContext(
        inputs={
            "raster.manifest": raster_manifest,
            "prepare.envelope": prepared_envelope,
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
        traced_outputs.append(
            output,
        )

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

    vector.execute(
        context,  # type: ignore[arg-type]
    )

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
    The vector manifest records registered Artwork products using filenames
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

    prepared_envelope = tmp_path / "prepare" / "envelope.svg"

    _write_prepared_envelope(
        prepared_envelope,
    )

    vector_manifest = tmp_path / "wherever" / "vectors" / "products.json"

    context = StubContext(
        inputs={
            "raster.manifest": raster_manifest,
            "prepare.envelope": prepared_envelope,
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

    vector.execute(
        context,  # type: ignore[arg-type]
    )

    data = json.loads(
        vector_manifest.read_text(
            encoding="utf-8",
        )
    )

    assert data == {
        "registered_extent": 10,
        "envelope": "envelope.svg",
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


def test_registered_envelope_preserves_occupied_bounds_relative_to_common_crop(
    tmp_path: Path,
) -> None:
    """
    Vector registration preserves the Artwork envelope's occupied position.

    When source coordinates map one-to-one into raster coordinates,
    registering into the common vector crop translates the occupied envelope
    by the crop origin and materializes that translation into its geometry.
    """

    source = tmp_path / "prepared-envelope.svg"
    output = tmp_path / "registered-envelope.svg"

    source.write_text(
        (
            '<svg xmlns="http://www.w3.org/2000/svg" '
            'width="100" '
            'height="100" '
            'viewBox="0 0 100 100">'
            '<rect x="30" y="20" width="40" height="60"/>'
            "</svg>"
        ),
        encoding="utf-8",
    )

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
        source,
        output,
        registration=registration,
        crop=crop,
    )

    root = ET.parse(
        output,
    ).getroot()

    assert root.get("viewBox") == "0 0 80 80"
    assert root.get("width") == "80"
    assert root.get("height") == "80"

    rectangle = next(element for element in root if element.tag == f"{{{vector.SVG_NS}}}rect")

    assert float(
        rectangle.get(
            "x",
            "nan",
        )
    ) == pytest.approx(10.0)

    assert float(
        rectangle.get(
            "y",
            "nan",
        )
    ) == pytest.approx(10.0)

    assert float(
        rectangle.get(
            "width",
            "nan",
        )
    ) == pytest.approx(40.0)

    assert float(
        rectangle.get(
            "height",
            "nan",
        )
    ) == pytest.approx(60.0)

    assert rectangle.get("transform") is None


def test_registered_envelope_remains_registered_with_common_layer_crop(
    tmp_path: Path,
) -> None:
    """
    The Artwork envelope remains registered with differently sized color layers.

    When source and raster coordinates are identical, the common layer crop
    maps directly into source coordinates and is materialized into the
    registered envelope geometry.
    """

    first_raster = tmp_path / "first.png"
    second_raster = tmp_path / "second.png"

    _write_raster(
        first_raster,
        box=(2, 4, 8, 12),
    )

    _write_raster(
        second_raster,
        box=(10, 6, 18, 16),
    )

    layers = [
        vector.RasterLayer(
            index=1,
            path=first_raster,
            name="white",
            color=(
                255,
                255,
                255,
            ),
        ),
        vector.RasterLayer(
            index=2,
            path=second_raster,
            name="black",
            color=(
                0,
                0,
                0,
            ),
        ),
    ]

    crop = vector._common_crop(
        layers,
    )

    assert crop == vector.RasterCrop(
        x=2,
        y=2,
        size=16,
    )

    source = tmp_path / "prepared-envelope.svg"
    output = tmp_path / "registered-envelope.svg"

    source.write_text(
        (
            '<svg xmlns="http://www.w3.org/2000/svg" '
            'width="20" '
            'height="20" '
            'viewBox="0 0 20 20">'
            '<rect x="2" y="4" width="16" height="12"/>'
            "</svg>"
        ),
        encoding="utf-8",
    )

    registration = vector.RasterRegistration(
        x=0.0,
        y=0.0,
        size=20.0,
        pixels=20,
    )

    vector._register_envelope(
        source,
        output,
        registration=registration,
        crop=crop,
    )

    root = ET.parse(
        output,
    ).getroot()

    assert root.get("viewBox") == "0 0 16 16"

    rectangle = next(element for element in root if element.tag == f"{{{vector.SVG_NS}}}rect")

    assert float(
        rectangle.get(
            "x",
            "nan",
        )
    ) == pytest.approx(0.0)

    assert float(
        rectangle.get(
            "y",
            "nan",
        )
    ) == pytest.approx(2.0)

    assert float(
        rectangle.get(
            "width",
            "nan",
        )
    ) == pytest.approx(16.0)

    assert float(
        rectangle.get(
            "height",
            "nan",
        )
    ) == pytest.approx(12.0)

    assert rectangle.get("transform") is None


def test_vector_layer_records_common_registered_coordinate_system(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Every vector layer uses the canonical Registered Artwork coordinate system.

    The source-raster crop establishes the registered extent, but its source
    X/Y origin is not part of the reusable Registered Artwork coordinate
    system.
    """

    source = tmp_path / "source.png"
    output = tmp_path / "color-1.svg"

    _write_raster(
        source,
        box=(4, 6, 12, 14),
    )

    crop = vector.RasterCrop(
        x=2,
        y=3,
        size=14,
    )

    def fake_run(
        source: Path,
        *,
        actions: tuple[str, ...],
    ) -> None:
        export_action = next(action for action in actions if action.startswith("export-filename:"))

        export_path = Path(
            export_action.removeprefix("export-filename:"),
        )

        export_path.write_text(
            (
                '<svg xmlns="http://www.w3.org/2000/svg" '
                'width="14" '
                'height="14" '
                'viewBox="0 0 14 14">'
                '<rect x="2" y="3" width="4" height="5"/>'
                "</svg>"
            ),
            encoding="utf-8",
        )

    monkeypatch.setattr(
        vector,
        "run",
        fake_run,
    )

    vector._trace_mask(
        source,
        output,
        crop=crop,
    )

    root = ET.parse(
        output,
    ).getroot()

    assert root.get("viewBox") == "0 0 14 14"
    assert root.get("width") == "14"
    assert root.get("height") == "14"


def test_vector_layer_geometry_remains_in_canonical_registered_coordinates(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Traced vector geometry remains in crop-local coordinates that are the
    canonical reusable Registered Artwork coordinates.

    Source-raster crop position does not alter the registered position of
    traced geometry.
    """

    source = tmp_path / "source.png"
    output = tmp_path / "color-1.svg"

    _write_raster(
        source,
        box=(4, 6, 12, 14),
    )

    crop = vector.RasterCrop(
        x=2,
        y=3,
        size=14,
    )

    def fake_run(
        source: Path,
        *,
        actions: tuple[str, ...],
    ) -> None:
        export_action = next(action for action in actions if action.startswith("export-filename:"))

        export_path = Path(
            export_action.removeprefix("export-filename:"),
        )

        export_path.write_text(
            (
                '<svg xmlns="http://www.w3.org/2000/svg" '
                'width="14" '
                'height="14" '
                'viewBox="0 0 14 14">'
                "<g>"
                '<rect x="2" y="3" width="4" height="5"/>'
                "</g>"
                "</svg>"
            ),
            encoding="utf-8",
        )

    monkeypatch.setattr(
        vector,
        "run",
        fake_run,
    )

    vector._trace_mask(
        source,
        output,
        crop=crop,
    )

    root = ET.parse(
        output,
    ).getroot()

    group = next(
        iter(root),
    )

    rectangle = next(
        iter(group),
    )

    assert float(rectangle.get("x", "nan")) == pytest.approx(2.0)
    assert float(rectangle.get("y", "nan")) == pytest.approx(3.0)
    assert float(rectangle.get("width", "nan")) == pytest.approx(4.0)
    assert float(rectangle.get("height", "nan")) == pytest.approx(5.0)

    assert group.get("transform") is None


def test_registered_envelope_uses_same_crop_as_vector_layers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    The Artwork envelope and every vector layer use one common registration.
    """

    raster_directory = tmp_path / "raster"

    first_raster = raster_directory / "first.png"
    second_raster = raster_directory / "second.png"

    _write_raster(
        first_raster,
        box=(2, 4, 8, 10),
    )

    _write_raster(
        second_raster,
        box=(12, 10, 18, 16),
    )

    raster_manifest = raster_directory / "products.json"

    _write_raster_manifest(
        raster_manifest,
        [
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
        ],
    )

    prepared_envelope = tmp_path / "prepare" / "envelope.svg"

    _write_prepared_envelope(
        prepared_envelope,
    )

    vector_manifest = tmp_path / "vector" / "products.json"

    context = StubContext(
        inputs={
            "raster.manifest": raster_manifest,
            "prepare.envelope": prepared_envelope,
        },
        outputs={
            "manifest": vector_manifest,
        },
        resolver=_resolver(),
    )

    envelope_crops: list[vector.RasterCrop] = []
    layer_crops: list[vector.RasterCrop] = []

    def fake_register_envelope(
        source: Path,
        output: Path,
        *,
        registration: vector.RasterRegistration,
        crop: vector.RasterCrop,
    ) -> None:
        envelope_crops.append(
            crop,
        )

        output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        output.write_text(
            "<svg/>",
            encoding="utf-8",
        )

    def fake_trace_mask(
        source: Path,
        output: Path,
        *,
        crop: vector.RasterCrop,
    ) -> None:
        layer_crops.append(
            crop,
        )

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
        "_register_envelope",
        fake_register_envelope,
    )

    monkeypatch.setattr(
        vector,
        "_trace_mask",
        fake_trace_mask,
    )

    vector.execute(
        context,  # type: ignore[arg-type]
    )

    expected = vector.RasterCrop(
        x=2,
        y=2,
        size=16,
    )

    assert envelope_crops == [
        expected,
    ]

    assert layer_crops == [
        expected,
        expected,
    ]


def test_registered_envelope_records_common_coordinate_system(
    tmp_path: Path,
) -> None:
    """
    The persistent Artwork envelope uses the canonical Registered Artwork
    coordinate system defined by registered_extent.
    """

    prepared_envelope = tmp_path / "prepare" / "envelope.svg"

    _write_prepared_envelope(
        prepared_envelope,
    )

    registered_envelope = tmp_path / "vector" / "envelope.svg"

    registration = vector.RasterRegistration(
        x=0.0,
        y=0.0,
        size=20.0,
        pixels=20,
    )

    crop = vector.RasterCrop(
        x=2,
        y=3,
        size=14,
    )

    vector._register_envelope(
        prepared_envelope,
        registered_envelope,
        registration=registration,
        crop=crop,
    )

    root = ET.parse(
        registered_envelope,
    ).getroot()

    assert root.get("viewBox") == "0 0 14 14"
    assert root.get("width") == "14"
    assert root.get("height") == "14"


def test_registered_envelope_geometry_is_translated_to_canonical_coordinates(
    tmp_path: Path,
) -> None:
    """
    Identity raster registration materializes the common vector-crop
    translation into canonical Registered Artwork geometry.
    """

    prepared_envelope = tmp_path / "prepare" / "envelope.svg"

    prepared_envelope.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    prepared_envelope.write_text(
        (
            '<svg xmlns="http://www.w3.org/2000/svg" '
            'width="20" '
            'height="20" '
            'viewBox="0 0 20 20">'
            '<rect x="4" y="6" width="8" height="6"/>'
            "</svg>"
        ),
        encoding="utf-8",
    )

    registered_envelope = tmp_path / "vector" / "envelope.svg"

    registration = vector.RasterRegistration(
        x=0.0,
        y=0.0,
        size=20.0,
        pixels=20,
    )

    crop = vector.RasterCrop(
        x=2,
        y=3,
        size=14,
    )

    vector._register_envelope(
        prepared_envelope,
        registered_envelope,
        registration=registration,
        crop=crop,
    )

    root = ET.parse(
        registered_envelope,
    ).getroot()

    assert root.get("viewBox") == "0 0 14 14"

    rectangle = next(element for element in root if element.tag == f"{{{vector.SVG_NS}}}rect")

    assert float(
        rectangle.get(
            "x",
            "nan",
        )
    ) == pytest.approx(2.0)

    assert float(
        rectangle.get(
            "y",
            "nan",
        )
    ) == pytest.approx(3.0)

    assert float(
        rectangle.get(
            "width",
            "nan",
        )
    ) == pytest.approx(8.0)

    assert float(
        rectangle.get(
            "height",
            "nan",
        )
    ) == pytest.approx(6.0)

    assert rectangle.get("transform") is None


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

    prepared_envelope = tmp_path / "prepare" / "envelope.svg"

    _write_prepared_envelope(
        prepared_envelope,
    )

    vector_manifest = tmp_path / "vector" / "products.json"

    context = StubContext(
        inputs={
            "raster.manifest": raster_manifest,
            "prepare.envelope": prepared_envelope,
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

    vector.execute(
        context,  # type: ignore[arg-type]
    )

    assert observed_crop == vector.RasterCrop(
        x=5,
        y=5,
        size=10,
    )

    assert vector_manifest.is_file()


def test_vector_manifest_records_registered_extent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    The vector manifest records the common registered coordinate extent.

    Downstream consumers use this extent to dimensionalize registered
    vector geometry without inspecting individual SVG documents.
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

    prepared_envelope = tmp_path / "prepare" / "envelope.svg"

    _write_prepared_envelope(
        prepared_envelope,
    )

    vector_manifest = tmp_path / "vector" / "products.json"

    context = StubContext(
        inputs={
            "raster.manifest": raster_manifest,
            "prepare.envelope": prepared_envelope,
        },
        outputs={
            "manifest": vector_manifest,
        },
        resolver=StubResolver({}),
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

    vector.execute(
        context,  # type: ignore[arg-type]
    )

    data = json.loads(
        vector_manifest.read_text(
            encoding="utf-8",
        )
    )

    assert data["registered_extent"] == 10


def test_vector_layers_share_one_registered_coordinate_system(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Every vector layer is traced in one common registered coordinate system.

    Individual raster layers may occupy different regions of the source
    raster. Vectorization must nevertheless apply the same union crop to
    every layer so downstream consumers can combine the resulting geometry
    without independently aligning the SVG products.
    """

    raster_directory = tmp_path / "raster"

    first_raster = raster_directory / "first.png"
    second_raster = raster_directory / "second.png"

    _write_raster(
        first_raster,
        box=(2, 4, 8, 10),
    )

    _write_raster(
        second_raster,
        box=(12, 10, 18, 16),
    )

    raster_manifest = raster_directory / "products.json"

    _write_raster_manifest(
        raster_manifest,
        [
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
        ],
    )

    prepared_envelope = tmp_path / "prepare" / "envelope.svg"

    _write_prepared_envelope(
        prepared_envelope,
    )

    vector_manifest = tmp_path / "vector" / "products.json"

    context = StubContext(
        inputs={
            "raster.manifest": raster_manifest,
            "prepare.envelope": prepared_envelope,
        },
        outputs={
            "manifest": vector_manifest,
        },
        resolver=StubResolver({}),
    )

    observed: list[
        tuple[
            Path,
            Path,
            vector.RasterCrop,
        ]
    ] = []

    def fake_trace_mask(
        source: Path,
        output: Path,
        *,
        crop: vector.RasterCrop,
    ) -> None:
        observed.append(
            (
                source,
                output,
                crop,
            )
        )

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

    vector.execute(
        context,  # type: ignore[arg-type]
    )

    assert len(observed) == 2

    first_crop = observed[0][2]
    second_crop = observed[1][2]

    assert first_crop == second_crop

    assert first_crop == vector.RasterCrop(
        x=2,
        y=2,
        size=16,
    )

    data = json.loads(
        vector_manifest.read_text(
            encoding="utf-8",
        )
    )

    assert data["registered_extent"] == first_crop.size

    assert [product["name"] for product in data["products"]] == [
        "white",
        "black",
    ]

    assert [product["index"] for product in data["products"]] == [
        1,
        2,
    ]


def test_vector_registration_is_based_on_union_of_all_layers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Registered vector extent is determined from the union of all layers.

    No individual color layer may establish its own coordinate extent,
    because doing so would destroy registration between independently
    consumable vector products.
    """

    raster_directory = tmp_path / "raster"

    left_raster = raster_directory / "left.png"
    right_raster = raster_directory / "right.png"

    _write_raster(
        left_raster,
        box=(1, 8, 5, 12),
    )

    _write_raster(
        right_raster,
        box=(15, 8, 19, 12),
    )

    raster_manifest = raster_directory / "products.json"

    _write_raster_manifest(
        raster_manifest,
        [
            {
                "index": 1,
                "path": left_raster.name,
                "name": "white",
                "color": _color(
                    255,
                    255,
                    255,
                ),
            },
            {
                "index": 2,
                "path": right_raster.name,
                "name": "black",
                "color": _color(
                    0,
                    0,
                    0,
                ),
            },
        ],
    )

    prepared_envelope = tmp_path / "prepare" / "envelope.svg"

    _write_prepared_envelope(
        prepared_envelope,
    )

    vector_manifest = tmp_path / "vector" / "products.json"

    context = StubContext(
        inputs={
            "raster.manifest": raster_manifest,
            "prepare.envelope": prepared_envelope,
        },
        outputs={
            "manifest": vector_manifest,
        },
        resolver=StubResolver({}),
    )

    crops: list[vector.RasterCrop] = []

    def fake_trace_mask(
        source: Path,
        output: Path,
        *,
        crop: vector.RasterCrop,
    ) -> None:
        crops.append(
            crop,
        )

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

    vector.execute(
        context,  # type: ignore[arg-type]
    )

    assert crops == [
        vector.RasterCrop(
            x=1,
            y=1,
            size=18,
        ),
        vector.RasterCrop(
            x=1,
            y=1,
            size=18,
        ),
    ]

    data = json.loads(
        vector_manifest.read_text(
            encoding="utf-8",
        )
    )

    assert data["registered_extent"] == 18


def test_vector_manifest_contains_no_physical_manufacturing_dimensions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Reusable registered Artwork contains no physical manufacturing dimensions.

    Physical X/Y size and Z extrusion semantics belong to the downstream
    consumer rather than the registered vector product.
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
            },
        ],
    )

    prepared_envelope = tmp_path / "prepare" / "envelope.svg"

    _write_prepared_envelope(
        prepared_envelope,
    )

    vector_manifest = tmp_path / "vector" / "products.json"

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

    context = StubContext(
        inputs={
            "raster.manifest": raster_manifest,
            "prepare.envelope": prepared_envelope,
        },
        outputs={
            "manifest": vector_manifest,
        },
        resolver=_resolver(),
    )

    vector.execute(
        context,  # type: ignore[arg-type]
    )

    data = json.loads(
        vector_manifest.read_text(
            encoding="utf-8",
        )
    )

    assert set(data) == {
        "registered_extent",
        "envelope",
        "products",
    }

    for product in data["products"]:
        assert set(product) == {
            "index",
            "path",
            "name",
            "color",
        }


def test_registered_vector_artwork_exposes_envelope(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Registered vector Artwork exposes its registered envelope.
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
            },
        ],
    )

    prepared_envelope = tmp_path / "prepare" / "envelope.svg"

    _write_prepared_envelope(
        prepared_envelope,
    )

    vector_manifest = tmp_path / "vector" / "products.json"

    context = StubContext(
        inputs={
            "raster.manifest": raster_manifest,
            "prepare.envelope": prepared_envelope,
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

    vector.execute(
        context,  # type: ignore[arg-type]
    )

    data = json.loads(
        vector_manifest.read_text(
            encoding="utf-8",
        )
    )

    assert "envelope" in data

    envelope = vector_manifest.parent / data["envelope"]

    assert envelope.is_file()


def test_registered_vector_artwork_envelope_is_stage_local(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Registered Artwork locates its envelope relative to the vector manifest.
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
            },
        ],
    )

    prepared_envelope = tmp_path / "somewhere" / "prepare" / "envelope.svg"

    _write_prepared_envelope(
        prepared_envelope,
    )

    vector_manifest = tmp_path / "somewhere-else" / "registered-artwork" / "products.json"

    context = StubContext(
        inputs={
            "raster.manifest": raster_manifest,
            "prepare.envelope": prepared_envelope,
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

    vector.execute(
        context,  # type: ignore[arg-type]
    )

    data = json.loads(
        vector_manifest.read_text(
            encoding="utf-8",
        )
    )

    envelope = Path(
        data["envelope"],
    )

    assert not envelope.is_absolute()

    assert (vector_manifest.parent / envelope) == (vector_manifest.parent / "envelope.svg")

    assert (vector_manifest.parent / envelope).is_file()


def test_vector_path_geometry_remains_in_canonical_registered_coordinates(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Traced path geometry remains in canonical Registered Artwork coordinates
    rather than being translated back into source-raster coordinates.
    """

    source = tmp_path / "source.png"
    output = tmp_path / "color-1.svg"

    _write_raster(
        source,
        box=(4, 6, 12, 14),
    )

    crop = vector.RasterCrop(
        x=2,
        y=3,
        size=14,
    )

    def fake_run(
        source: Path,
        *,
        actions: tuple[str, ...],
    ) -> None:
        export_action = next(action for action in actions if action.startswith("export-filename:"))

        export_path = Path(
            export_action.removeprefix("export-filename:"),
        )

        export_path.write_text(
            (
                '<svg xmlns="http://www.w3.org/2000/svg" '
                'width="14" '
                'height="14" '
                'viewBox="0 0 14 14">'
                "<g>"
                '<path d="M 2,3 H 6 V 8 H 2 Z"/>'
                "</g>"
                "</svg>"
            ),
            encoding="utf-8",
        )

    monkeypatch.setattr(
        vector,
        "run",
        fake_run,
    )

    vector._trace_mask(
        source,
        output,
        crop=crop,
    )

    root = ET.parse(
        output,
    ).getroot()

    group = next(
        iter(root),
    )

    path = next(
        iter(group),
    )

    assert path.get("d") == "M 2,3 H 6 V 8 H 2 Z"
    assert group.get("transform") is None


def test_vector_path_registration_preserves_existing_transform(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Registering traced geometry preserves transforms already present on the
    Inkscape geometry group without adding a source-crop translation.
    """

    source = tmp_path / "source.png"
    output = tmp_path / "color-1.svg"

    _write_raster(
        source,
        box=(4, 6, 12, 14),
    )

    crop = vector.RasterCrop(
        x=2,
        y=3,
        size=14,
    )

    def fake_run(
        source: Path,
        *,
        actions: tuple[str, ...],
    ) -> None:
        export_action = next(action for action in actions if action.startswith("export-filename:"))

        export_path = Path(
            export_action.removeprefix("export-filename:"),
        )

        export_path.write_text(
            (
                '<svg xmlns="http://www.w3.org/2000/svg" '
                'width="14" '
                'height="14" '
                'viewBox="0 0 14 14">'
                '<g transform="scale(0.5)">'
                '<path d="M 2,3 H 6 V 8 H 2 Z"/>'
                "</g>"
                "</svg>"
            ),
            encoding="utf-8",
        )

    monkeypatch.setattr(
        vector,
        "run",
        fake_run,
    )

    vector._trace_mask(
        source,
        output,
        crop=crop,
    )

    root = ET.parse(
        output,
    ).getroot()

    group = next(
        iter(root),
    )

    path = next(
        iter(group),
    )

    assert path.get("d") == "M 2,3 H 6 V 8 H 2 Z"
    assert group.get("transform") == "scale(0.5)"


@pytest.mark.slow
def test_vector_trace_preserves_asymmetric_registered_geometry(
    tmp_path: Path,
) -> None:
    """
    Real vector tracing preserves asymmetric geometry in the canonical
    Registered Artwork coordinate system.
    """

    source = tmp_path / "source.png"
    output = tmp_path / "color-1.svg"

    _write_raster(
        source,
        box=(4, 6, 8, 12),
    )

    crop = vector.RasterCrop(
        x=2,
        y=3,
        size=14,
    )

    vector._trace_mask(
        source,
        output,
        crop=crop,
    )

    root = ET.parse(
        output,
    ).getroot()

    assert root.get("viewBox") == "0 0 14 14"
    assert root.get("width") == "14"
    assert root.get("height") == "14"

    geometry = [element for element in root.iter() if element.tag == f"{{{vector.SVG_NS}}}path"]

    assert geometry

    geometry_parent = next(element for element in root if element.tag == f"{{{vector.SVG_NS}}}g")

    assert geometry_parent.get("transform") is None


@pytest.mark.slow
def test_vector_trace_distinguishes_registered_top_and_bottom(
    tmp_path: Path,
) -> None:
    """
    Real tracing preserves vertical orientation in registered Artwork.
    """

    top_source = tmp_path / "top.png"
    bottom_source = tmp_path / "bottom.png"

    top_output = tmp_path / "top.svg"
    bottom_output = tmp_path / "bottom.svg"

    _write_raster(
        top_source,
        box=(4, 2, 8, 6),
    )

    _write_raster(
        bottom_source,
        box=(4, 10, 8, 14),
    )

    crop = vector.RasterCrop(
        x=2,
        y=0,
        size=16,
    )

    vector._trace_mask(
        top_source,
        top_output,
        crop=crop,
    )

    vector._trace_mask(
        bottom_source,
        bottom_output,
        crop=crop,
    )

    top_root = ET.parse(
        top_output,
    ).getroot()

    bottom_root = ET.parse(
        bottom_output,
    ).getroot()

    top_paths = [
        element for element in top_root.iter() if element.tag == f"{{{vector.SVG_NS}}}path"
    ]

    bottom_paths = [
        element for element in bottom_root.iter() if element.tag == f"{{{vector.SVG_NS}}}path"
    ]

    assert top_paths
    assert bottom_paths

    assert [element.get("d") for element in top_paths] != [
        element.get("d") for element in bottom_paths
    ]


@pytest.mark.slow
def test_vector_registration_does_not_transform_document_metadata(
    tmp_path: Path,
) -> None:
    """
    Registered Artwork transforms rendered geometry without modifying
    non-rendered Inkscape document metadata.
    """

    source = tmp_path / "source.png"
    output = tmp_path / "color-1.svg"

    _write_raster(
        source,
        box=(4, 6, 8, 12),
    )

    crop = vector.RasterCrop(
        x=2,
        y=3,
        size=14,
    )

    vector._trace_mask(
        source,
        output,
        crop=crop,
    )

    root = ET.parse(
        output,
    ).getroot()

    defs = next(element for element in root if element.tag == f"{{{vector.SVG_NS}}}defs")

    assert defs.get("transform") is None

    non_svg_children = [
        element for element in root if not element.tag.startswith(f"{{{vector.SVG_NS}}}")
    ]

    assert non_svg_children

    assert all(element.get("transform") is None for element in non_svg_children)


@pytest.mark.slow
def test_vector_registration_preserves_common_coordinates_between_envelope_and_layers(
    tmp_path: Path,
) -> None:
    """
    Vector Artwork products share one registered coordinate system.

    The common raster crop establishes one registered coordinate system for
    every vector layer and envelope.svg. The envelope remains authoritative
    for Artwork occupancy within that coordinate system.
    """

    first_raster = tmp_path / "first.png"
    second_raster = tmp_path / "second.png"

    _write_raster(
        first_raster,
        box=(2, 4, 8, 12),
    )

    _write_raster(
        second_raster,
        box=(10, 6, 18, 16),
    )

    layers = [
        vector.RasterLayer(
            index=1,
            path=first_raster,
            name="white",
            color=(
                255,
                255,
                255,
            ),
        ),
        vector.RasterLayer(
            index=2,
            path=second_raster,
            name="black",
            color=(
                0,
                0,
                0,
            ),
        ),
    ]

    crop = vector._common_crop(
        layers,
    )

    assert crop == vector.RasterCrop(
        x=2,
        y=2,
        size=16,
    )

    prepared_envelope = tmp_path / "prepared-envelope.svg"
    registered_envelope = tmp_path / "registered-envelope.svg"

    prepared_envelope.write_text(
        (
            '<svg xmlns="http://www.w3.org/2000/svg" '
            'width="20" '
            'height="20" '
            'viewBox="0 0 20 20">'
            '<rect x="3" y="4" width="14" height="12"/>'
            "</svg>"
        ),
        encoding="utf-8",
    )

    registration = vector.RasterRegistration(
        x=0.0,
        y=0.0,
        size=20.0,
        pixels=20,
    )

    vector._register_envelope(
        prepared_envelope,
        registered_envelope,
        registration=registration,
        crop=crop,
    )

    envelope_root = ET.parse(
        registered_envelope,
    ).getroot()

    assert envelope_root.get("viewBox") == "0 0 16 16"
    assert envelope_root.get("width") == "16"
    assert envelope_root.get("height") == "16"

    envelope_rectangle = next(
        element for element in envelope_root if element.tag == f"{{{vector.SVG_NS}}}rect"
    )

    assert envelope_rectangle.get("transform") is None

    registered_layers: list[Path] = []

    for layer in layers:
        output = tmp_path / f"registered-{layer.index}.svg"

        vector._trace_mask(
            layer.path,
            output,
            crop=crop,
        )

        registered_layers.append(
            output,
        )

    for registered_layer in registered_layers:
        root = ET.parse(
            registered_layer,
        ).getroot()

        assert root.get("viewBox") == "0 0 16 16"
        assert root.get("width") == "16"
        assert root.get("height") == "16"

    assert float(
        envelope_rectangle.get(
            "x",
            "nan",
        )
    ) == pytest.approx(1.0)

    assert float(
        envelope_rectangle.get(
            "y",
            "nan",
        )
    ) == pytest.approx(2.0)

    assert float(
        envelope_rectangle.get(
            "width",
            "nan",
        )
    ) == pytest.approx(14.0)

    assert float(
        envelope_rectangle.get(
            "height",
            "nan",
        )
    ) == pytest.approx(12.0)


def test_shape_reads_vector_registered_envelope_in_common_coordinates(
    tmp_path: Path,
) -> None:
    """
    Shape interprets Artwork's registered envelope in producer coordinates.

    With identity raster registration, the common vector crop translates the
    prepared envelope into canonical Registered Artwork coordinates.
    """

    prepared_envelope = tmp_path / "prepared-envelope.svg"
    registered_envelope = tmp_path / "envelope.svg"

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

    assert bounds.x == pytest.approx(10.0)
    assert bounds.y == pytest.approx(10.0)

    assert bounds.width == pytest.approx(40.0)
    assert bounds.height == pytest.approx(60.0)

    envelope_center_x = (bounds.x + bounds.x + bounds.width) / 2.0

    envelope_center_y = (bounds.y + bounds.y + bounds.height) / 2.0

    assert envelope_center_x == pytest.approx(30.0)
    assert envelope_center_y == pytest.approx(40.0)

    registered_center_x = artwork.registered_extent.width / 2.0

    assert registered_center_x == pytest.approx(40.0)

    assert envelope_center_x != pytest.approx(
        registered_center_x,
    )


def test_registered_envelope_materializes_source_to_raster_scale_in_path_geometry(
    tmp_path: Path,
) -> None:
    """
    Registered Artwork materializes source-to-raster scaling into envelope paths.

    The persistent envelope must expose geometry directly in Registered Artwork
    coordinates rather than requiring downstream consumers to interpret an SVG
    scale transform.
    """

    source = tmp_path / "prepared-envelope.svg"
    output = tmp_path / "registered-envelope.svg"

    source.write_text(
        """
<svg
    xmlns="http://www.w3.org/2000/svg"
    width="200"
    height="180"
    viewBox="0 0 200 180"
>
    <path
        d="M 36 42 L 164 42 L 164 138 L 36 138 Z"
    />
</svg>
""".strip(),
        encoding="utf-8",
    )

    registration = vector.RasterRegistration(
        x=20.0,
        y=10.0,
        size=160.0,
        pixels=100,
    )

    crop = vector.RasterCrop(
        x=10,
        y=10,
        size=80,
    )

    vector._register_envelope(
        source,
        output,
        registration=registration,
        crop=crop,
    )

    root = ET.parse(
        output,
    ).getroot()

    assert root.get("viewBox") == "0 0 80 80"
    assert root.get("width") == "80"
    assert root.get("height") == "80"

    artwork = compose.RegisteredArtwork(
        registered_extent=compose.RegisteredExtent(
            width=80.0,
            height=80.0,
        ),
        envelope=output,
        components=(),
    )

    bounds = compose.registered_artwork_envelope_bounds(
        artwork,
    )

    assert bounds.x == pytest.approx(0.0)
    assert bounds.y == pytest.approx(10.0)
    assert bounds.width == pytest.approx(80.0)
    assert bounds.height == pytest.approx(60.0)

    assert all("scale(" not in (element.get("transform") or "") for element in root.iter())


def test_vector_stage_registers_envelope_through_raster_registration(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Vector registration maps the prepared envelope through raster registration.

    The raster manifest defines how source coordinates were mapped into raster
    pixels. Vector registration must use that mapping before applying its common
    raster crop so the envelope and vector layers share one registered
    coordinate system.
    """

    raster_dir = tmp_path / "raster"
    prepare_dir = tmp_path / "prepare"
    vector_dir = tmp_path / "vector"

    raster_dir.mkdir()
    prepare_dir.mkdir()
    vector_dir.mkdir()

    #
    # The raster stage exported this source-coordinate square:
    #
    #     X = 20..180
    #     Y = 10..170
    #
    # into:
    #
    #     100 x 100 pixels
    #
    # Therefore:
    #
    #     source X 20..180 -> raster X 0..100
    #     source Y 10..170 -> raster Y 0..100
    #

    raster_layer = raster_dir / "color-1.png"

    image = Image.new(
        "RGBA",
        (100, 100),
        (0, 0, 0, 0),
    )

    try:
        #
        # Actual visible geometry occupies:
        #
        #     raster X = 10..90
        #     raster Y = 20..80
        #
        # The vector common crop therefore becomes:
        #
        #     X = 10..90
        #     Y = 10..90
        #
        # because the 80-pixel width determines the square crop.
        #
        for y in range(20, 80):
            for x in range(10, 90):
                image.putpixel(
                    (x, y),
                    (255, 0, 0, 255),
                )

        image.save(
            raster_layer,
            format="PNG",
        )

    finally:
        image.close()

    raster_manifest = raster_dir / "products.json"

    raster_manifest.write_text(
        json.dumps(
            {
                "registration": {
                    "x": 20.0,
                    "y": 10.0,
                    "size": 160.0,
                    "pixels": 100,
                },
                "products": [
                    {
                        "index": 1,
                        "path": "color-1.png",
                        "name": "red",
                        "color": {
                            "red": 255,
                            "green": 0,
                            "blue": 0,
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    #
    # This envelope occupies exactly the same source-space region as the
    # visible raster geometry:
    #
    # raster X 10..90 corresponds to source X 36..164
    # raster Y 20..80 corresponds to source Y 42..138
    #
    # After the vector crop:
    #
    #     envelope X = 0..80
    #     envelope Y = 10..70
    #
    # inside the common 80 x 80 registered extent.
    #

    prepared_envelope = prepare_dir / "envelope.svg"

    prepared_envelope.write_text(
        """
<svg
    xmlns="http://www.w3.org/2000/svg"
    width="200"
    height="180"
    viewBox="0 0 200 180"
>
    <rect
        x="36"
        y="42"
        width="128"
        height="96"
    />
</svg>
""".strip(),
        encoding="utf-8",
    )

    vector_manifest = vector_dir / "products.json"

    class Context:
        def input(
            self,
            name: str,
        ) -> Path:
            return {
                "raster.manifest": raster_manifest,
                "prepare.envelope": prepared_envelope,
            }[name]

        def output(
            self,
            name: str,
        ) -> Path:
            assert name == "manifest"
            return vector_manifest

    def fake_trace_mask(
        source: Path,
        output: Path,
        *,
        crop: vector.RasterCrop,
    ) -> None:
        assert source == raster_layer

        output.write_text(
            f"""
<svg
    xmlns="http://www.w3.org/2000/svg"
    width="{crop.size}"
    height="{crop.size}"
    viewBox="0 0 {crop.size} {crop.size}"
>
    <rect
        x="0"
        y="10"
        width="{crop.size}"
        height="60"
    />
</svg>
""".strip(),
            encoding="utf-8",
        )

    monkeypatch.setattr(
        vector,
        "_trace_mask",
        fake_trace_mask,
    )

    vector.execute(
        Context(),  # type: ignore[arg-type]
    )

    registered_envelope = vector_dir / "envelope.svg"

    assert registered_envelope.is_file()

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

    assert bounds.x == pytest.approx(0.0)
    assert bounds.y == pytest.approx(10.0)
    assert bounds.width == pytest.approx(80.0)
    assert bounds.height == pytest.approx(60.0)
