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

    The source-raster crop origin is removed when the prepared envelope is
    registered.
    """

    prepared_envelope = tmp_path / "prepare" / "envelope.svg"

    _write_prepared_envelope(
        prepared_envelope,
    )

    registered_envelope = tmp_path / "vector" / "envelope.svg"

    crop = vector.RasterCrop(
        x=2,
        y=3,
        size=14,
    )

    vector._register_envelope(
        prepared_envelope,
        registered_envelope,
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
    Registering the Artwork envelope translates its source-image geometry
    into the canonical Registered Artwork coordinate system.

    A source crop beginning at (2, 3) becomes a registered coordinate
    system beginning at (0, 0). The envelope and traced vector layers can
    therefore share one reusable coordinate system independent of the
    source-raster crop origin.
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

    crop = vector.RasterCrop(
        x=2,
        y=3,
        size=14,
    )

    vector._register_envelope(
        prepared_envelope,
        registered_envelope,
        crop=crop,
    )

    root = ET.parse(
        registered_envelope,
    ).getroot()

    assert root.get("viewBox") == "0 0 14 14"

    group = next(element for element in root if element.tag == f"{{{vector.SVG_NS}}}g")

    rectangle = next(element for element in group if element.tag == f"{{{vector.SVG_NS}}}rect")

    assert group.get("transform") == "translate(-2 -3)"

    assert float(rectangle.get("x", "nan")) == pytest.approx(4.0)
    assert float(rectangle.get("y", "nan")) == pytest.approx(6.0)
    assert float(rectangle.get("width", "nan")) == pytest.approx(8.0)
    assert float(rectangle.get("height", "nan")) == pytest.approx(6.0)


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
