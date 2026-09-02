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
    *,
    registration: dict[str, Any] | None = None,
) -> None:
    """
    Write a raster manifest for vector-stage tests.

    Legacy test shorthand using name/color describes an Artifact color
    whose current printer assignment has the same RGB value.
    """

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    normalized_products: list[dict[str, Any]] = []

    for product in products:
        if "artifact_color" in product:
            normalized_products.append(
                product,
            )
            continue

        index = product["index"]
        name = product["name"]
        color = product["color"]

        normalized_products.append(
            {
                "index": index,
                "path": product["path"],
                "artifact_color": {
                    "index": index,
                    "rgb": color,
                },
                "printer_color": {
                    "name": name,
                    "rgb": color,
                },
                "distance": 0.0,
            }
        )

    data = {
        "registration": (
            registration
            if registration is not None
            else {
                "x": 0.0,
                "y": 0.0,
                "size": 20.0,
                "pixels": 20,
            }
        ),
        "products": normalized_products,
    }

    path.write_text(
        json.dumps(
            data,
            indent=2,
        )
        + "\n",
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
                "artifact_color": {
                    "index": 1,
                    "rgb": {
                        "red": 255,
                        "green": 215,
                        "blue": 0,
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
                "distance": 0.0,
            }
        ],
    }


def test_vector_preserves_artifact_color_identity_and_rgb(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Registered Artwork preserves Artifact color identity and RGB.

    Vectorization changes geometry representation without replacing or
    reinterpreting the Artifact colors discovered by multicolor tracing.
    """

    raster_directory = tmp_path / "raster"

    raster = raster_directory / "color-1.png"

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
                "artifact_color": {
                    "index": 7,
                    "rgb": _color(
                        17,
                        43,
                        91,
                    ),
                },
                "printer_color": {
                    "name": "physical-blue",
                    "rgb": _color(
                        20,
                        40,
                        90,
                    ),
                },
                "distance": 1.25,
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


def test_registered_artwork_manifest_is_sufficient_to_recover_artifact_colors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Persistent Registered Artwork is sufficient to recover Artifact colors.

    Consumers do not require the source image, prepared trace, or raster
    manifest to recover stable Artifact color identities and RGB values.
    """

    raster_directory = tmp_path / "raster"

    first_raster = raster_directory / "color-1.png"
    second_raster = raster_directory / "color-2.png"

    _write_raster(
        first_raster,
        box=(2, 4, 8, 12),
    )

    _write_raster(
        second_raster,
        box=(10, 6, 18, 16),
    )

    raster_manifest = raster_directory / "products.json"

    _write_raster_manifest(
        raster_manifest,
        [
            {
                "index": 1,
                "path": first_raster.name,
                "artifact_color": {
                    "index": 3,
                    "rgb": _color(
                        17,
                        43,
                        91,
                    ),
                },
                "printer_color": {
                    "name": "physical-blue",
                    "rgb": _color(
                        20,
                        40,
                        90,
                    ),
                },
                "distance": 1.25,
            },
            {
                "index": 2,
                "path": second_raster.name,
                "artifact_color": {
                    "index": 8,
                    "rgb": _color(
                        211,
                        173,
                        61,
                    ),
                },
                "printer_color": {
                    "name": "physical-gold",
                    "rgb": _color(
                        210,
                        170,
                        60,
                    ),
                },
                "distance": 2.5,
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

    #
    # Registered Artwork is now the only product information consulted.
    #
    # Removing the producer manifest demonstrates that Artifact color
    # semantics have crossed the persistent-product boundary.
    #
    raster_manifest.unlink()

    data = json.loads(
        vector_manifest.read_text(
            encoding="utf-8",
        )
    )

    assert [product["artifact_color"] for product in data["products"]] == [
        {
            "index": 3,
            "rgb": {
                "red": 17,
                "green": 43,
                "blue": 91,
            },
        },
        {
            "index": 8,
            "rgb": {
                "red": 211,
                "green": 173,
                "blue": 61,
            },
        },
    ]


def test_vector_binary_trace_does_not_rediscover_color(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Vector tracing derives geometry only from the registered raster mask.

    Artifact and printer color semantics come from the raster manifest rather
    than being rediscovered or reinterpreted during binary mask tracing.
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
                "artifact_color": {
                    "index": 7,
                    "rgb": _color(
                        17,
                        43,
                        91,
                    ),
                },
                "printer_color": {
                    "name": "physical-blue",
                    "rgb": _color(
                        20,
                        40,
                        90,
                    ),
                },
                "distance": 1.25,
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

    traced: list[tuple[Path, vector.RasterCrop]] = []

    def fake_trace_mask(
        source: Path,
        output: Path,
        *,
        crop: vector.RasterCrop,
    ) -> None:
        traced.append(
            (
                source,
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

    assert traced == [
        (
            raster,
            vector.RasterCrop(
                x=5,
                y=5,
                size=10,
            ),
        ),
    ]

    data = json.loads(
        vector_manifest.read_text(
            encoding="utf-8",
        )
    )

    assert data["products"] == [
        {
            "index": 1,
            "path": "color-1.svg",
            "artifact_color": {
                "index": 7,
                "rgb": _color(
                    17,
                    43,
                    91,
                ),
            },
            "printer_color": {
                "name": "physical-blue",
                "rgb": _color(
                    20,
                    40,
                    90,
                ),
            },
            "distance": 1.25,
        },
    ]
