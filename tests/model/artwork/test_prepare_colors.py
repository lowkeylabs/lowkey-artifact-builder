"""
Focused tests for Artwork prepare-stage color semantics.

Prepare derives registered Artwork from the source image while preserving
source color information for multicolor tracing.

Physical printer-color selection and assignment are not Prepare
responsibilities.
"""
# File: tests/model/artwork/test_prepare_colors.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, cast

import pytest
from PIL import Image

from lowkey_artifact_builder.config import write_artifact_config
from lowkey_artifact_builder.engine import StageContext
from lowkey_artifact_builder.engine.dependency_build import execute_dependency_build
from lowkey_artifact_builder.engine.plan import create_build_plans
from lowkey_artifact_builder.model.models.artwork.stages import prepare, vector
from lowkey_artifact_builder.model.specs import ProductRef

# =========================================================
# Test support
# =========================================================


class StubResolver:
    """
    Minimal Resolver-compatible object recording values requested by
    Prepare.
    """

    def __init__(
        self,
        values: dict[str, Any],
    ) -> None:
        self._values = values
        self.requested: list[str] = []

    def __call__(
        self,
        name: str,
    ) -> Any:
        self.requested.append(
            name,
        )

        if name in {
            "printer_colors",
            "artwork_colors",
            "artwork_fill_color",
        }:
            raise AssertionError(
                f"Prepare must not resolve {name!r}.",
            )

        return self._values[name]


class StubContext:
    """
    Minimal StageContext-compatible object for Prepare color tests.
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


def _write_fake_trace(
    destination: Path,
) -> None:
    """
    Write minimal drawable SVG geometry representing a successful trace.
    """

    destination.write_text(
        ('<svg xmlns="http://www.w3.org/2000/svg"><path d="M 6 6 L 26 6 L 26 26 L 6 26 Z"/></svg>'),
        encoding="utf-8",
    )


def _source_image(
    path: Path,
) -> None:
    """
    Write source Artwork containing several distinct visible colors.

    The Artwork is intentionally large enough for normal envelope
    morphology so these tests exercise Prepare color semantics rather
    than envelope-size edge cases.
    """

    image = Image.new(
        "RGBA",
        (
            32,
            32,
        ),
        (
            0,
            0,
            0,
            0,
        ),
    )

    try:
        pixels = image.load()

        assert pixels is not None

        for y in range(6, 26):
            for x in range(6, 11):
                pixels[x, y] = (
                    220,
                    40,
                    40,
                    255,
                )

            for x in range(11, 16):
                pixels[x, y] = (
                    40,
                    180,
                    70,
                    255,
                )

            for x in range(16, 21):
                pixels[x, y] = (
                    40,
                    80,
                    220,
                    255,
                )

            for x in range(21, 26):
                pixels[x, y] = (
                    230,
                    190,
                    40,
                    255,
                )

        image.save(
            path,
            format="PNG",
        )

    finally:
        image.close()


def _context(
    tmp_path: Path,
    resolver: StubResolver,
) -> StubContext:
    """
    Construct a minimal Prepare stage context.
    """

    source = tmp_path / "source.png"
    trace = tmp_path / "trace.svg"
    envelope = tmp_path / "envelope.svg"

    _source_image(
        source,
    )

    return StubContext(
        inputs={
            "source": source,
        },
        outputs={
            "trace": trace,
            "envelope": envelope,
        },
        resolver=resolver,
    )


# =========================================================
# Prepare color configuration
# =========================================================


def test_prepare_uses_artifact_color_count_for_multicolor_trace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Prepare uses artifact_color_count as the requested multicolor trace
    count.

    The number of Artifact colors is independent of any physical printer
    palette.
    """

    resolver = StubResolver(
        {
            "artifact_color_count": 4,
            "artwork_envelope_mode": "alpha",
        }
    )

    context = _context(
        tmp_path,
        resolver,
    )

    traced_counts: list[int] = []

    def fake_trace_multicolor(
        source: Path,
        destination: Path,
        *,
        colors: int,
    ) -> None:
        traced_counts.append(
            colors,
        )

        _write_fake_trace(
            destination,
        )

    monkeypatch.setattr(
        prepare,
        "_trace_multicolor",
        fake_trace_multicolor,
    )

    prepare.execute(
        cast(
            StageContext,
            context,
        ),
    )
    assert traced_counts == [
        4,
    ]


def test_prepare_does_not_resolve_physical_printer_colors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Prepare does not resolve printer_colors.

    Physical printer-color assignment belongs to Raster rather than
    Prepare.
    """

    resolver = StubResolver(
        {
            "artifact_color_count": 2,
            "artwork_envelope_mode": "alpha",
        }
    )

    context = _context(
        tmp_path,
        resolver,
    )

    def fake_trace_multicolor(
        source: Path,
        destination: Path,
        *,
        colors: int,
    ) -> None:
        _write_fake_trace(
            destination,
        )

    monkeypatch.setattr(
        prepare,
        "_trace_multicolor",
        fake_trace_multicolor,
    )

    prepare.execute(
        cast(
            StageContext,
            context,
        ),
    )

    assert "printer_colors" not in resolver.requested


def test_prepare_does_not_resolve_obsolete_artwork_palette_configuration(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Prepare does not resolve the removed artwork_colors or
    artwork_fill_color configuration values.

    Artifact colors are derived product information rather than a
    configured physical palette.
    """

    resolver = StubResolver(
        {
            "artifact_color_count": 2,
            "artwork_envelope_mode": "alpha",
        }
    )

    context = _context(
        tmp_path,
        resolver,
    )

    def fake_trace_multicolor(
        source: Path,
        destination: Path,
        *,
        colors: int,
    ) -> None:
        _write_fake_trace(
            destination,
        )

    monkeypatch.setattr(
        prepare,
        "_trace_multicolor",
        fake_trace_multicolor,
    )

    prepare.execute(
        cast(
            StageContext,
            context,
        ),
    )
    assert "artwork_colors" not in resolver.requested
    assert "artwork_fill_color" not in resolver.requested


def test_prepare_vector_auto_accepts_jpeg_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Vector preparation accepts JPEG input and normalizes it for
    the established PNG tracing workflow.

    JPEG decoding must not introduce a separate vector-processing
    algorithm or change the registered SVG Product contract.
    """

    source = tmp_path / "source.jpg"
    trace = tmp_path / "trace.svg"
    envelope = tmp_path / "envelope.svg"

    with Image.new("RGB", (64, 64), "white") as image:
        for y in range(12, 52):
            for x in range(12, 52):
                image.putpixel((x, y), (0, 0, 0))
        image.save(source, format="JPEG", quality=100)

    resolver = StubResolver(
        {
            "artifact_color_count": 1,
            "artwork_envelope_mode": "shrink-wrap",
        }
    )

    context = StubContext(
        inputs={"source": source},
        outputs={
            "trace": trace,
            "envelope": envelope,
        },
        resolver=resolver,
    )

    traced_sources: list[Path] = []

    def fake_trace_single_color(
        input_path: Path,
        output_path: Path,
    ) -> None:
        with Image.open(input_path) as image:
            assert image.format == "PNG"
            assert image.size == (64, 64)

        traced_sources.append(input_path)
        _write_fake_trace(output_path)

    monkeypatch.setattr(
        prepare,
        "_trace_single_color",
        fake_trace_single_color,
    )

    prepare.execute(
        cast(StageContext, context),
    )

    assert len(traced_sources) == 1
    assert trace.is_file()
    assert envelope.is_file()


def test_vector_auto_builds_registered_vector_from_jpeg(
    tmp_path: Path,
) -> None:
    """
    A JPEG-backed vector + auto Realization builds its registered
    vector Product through the public dependency planner.

    The source is decoded for tracing without requiring the
    independent raster-preserving Stage.
    """
    source = tmp_path / "customer.jpg"

    with Image.new("RGB", (96, 96), "white") as image:
        for y in range(24, 72):
            for x in range(24, 72):
                image.putpixel((x, y), (0, 0, 0))

        image.save(source, format="JPEG", quality=100)

    artifact_id = "jpeg-vector"
    realization = "traced"

    write_artifact_config(
        artifact_id,
        {
            "source": str(source),
            "realizations": {
                realization: {
                    "model": "artwork",
                    "parameters": {
                        "artwork_representation": "vector",
                        "artwork_processing": "auto",
                        "artifact_color_count": 1,
                    },
                },
            },
        },
        project_root=tmp_path,
    )

    target = ProductRef(
        artifact=artifact_id,
        model="artwork",
        realization=realization,
        stage="vector",
        product="manifest",
    )

    plans = create_build_plans(
        artifact_id,
        realization=realization,
        targets=(target,),
        project_root=tmp_path,
    )

    assert len(plans) == 1

    plan = plans[0]
    stage_names = [stage.name for stage in plan.stages]

    assert "prepare" in stage_names
    assert "vector" in stage_names
    assert "raster_source" not in stage_names
    assert "extrude" not in stage_names
    assert "package" not in stage_names

    execute_dependency_build(plan)

    vector_stage = next(stage for stage in plan.stages if stage.name == "vector")

    vector_product = next(
        product.path for product in vector_stage.products if product.spec.name == "manifest"
    )

    assert vector_product.is_file()
    assert vector_product.stat().st_size > 0


def test_vector_auto_preserves_native_svg_without_bitmap_tracing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    A native SVG source builds registered vector color layers through
    the public planner without bitmap tracing.

    Authored path geometry and colors remain represented in the
    registered Products.
    """
    source = tmp_path / "customer.svg"

    authored_paths = {
        "red-region": ("M 10 10 H 40 V 40 H 10 Z", "#cc2233"),
        "blue-region": ("M 50 50 H 80 V 80 H 50 Z", "#2255cc"),
    }

    source.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" '
        'viewBox="0 0 100 100" width="100" height="100">'
        '<path id="red-region" fill="#cc2233" '
        'd="M 10 10 H 40 V 40 H 10 Z"/>'
        '<path id="blue-region" fill="#2255cc" '
        'd="M 50 50 H 80 V 80 H 50 Z"/>'
        "</svg>",
        encoding="utf-8",
    )

    original_bytes = source.read_bytes()

    def forbidden_bitmap_trace(*args: object, **kwargs: object) -> None:
        pytest.fail("Native SVG artwork must not be bitmap-traced.")

    monkeypatch.setattr(
        prepare,
        "_trace_single_color",
        forbidden_bitmap_trace,
    )
    monkeypatch.setattr(
        prepare,
        "_trace_multicolor",
        forbidden_bitmap_trace,
    )
    monkeypatch.setattr(
        vector,
        "_trace_mask",
        forbidden_bitmap_trace,
    )

    artifact_id = "native-svg-vector"
    realization = "authored"

    write_artifact_config(
        artifact_id,
        {
            "source": str(source),
            "realizations": {
                realization: {
                    "model": "artwork",
                    "parameters": {
                        "artwork_representation": "vector",
                        "artwork_processing": "auto",
                        "artifact_color_count": 2,
                    },
                },
            },
        },
        project_root=tmp_path,
    )

    target = ProductRef(
        artifact=artifact_id,
        model="artwork",
        realization=realization,
        stage="vector",
        product="manifest",
    )

    plans = create_build_plans(
        artifact_id,
        realization=realization,
        targets=(target,),
        project_root=tmp_path,
    )

    assert len(plans) == 1

    plan = plans[0]
    stage_names = {stage.name for stage in plan.stages}

    assert {"prepare", "raster", "vector"} <= stage_names
    assert "raster_source" not in stage_names
    assert "extrude" not in stage_names
    assert "package" not in stage_names

    execute_dependency_build(plan)

    vector_stage = next(stage for stage in plan.stages if stage.name == "vector")

    manifest_path = next(
        product.path for product in vector_stage.products if product.spec.name == "manifest"
    )

    assert manifest_path.is_file()

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert isinstance(manifest["products"], list)
    assert len(manifest["products"]) == 2

    registered_paths: dict[str, str] = {}

    for layer_file in manifest_path.parent.glob("color-*.svg"):
        root = ET.parse(layer_file).getroot()

        for path in root.iter("{http://www.w3.org/2000/svg}path"):
            path_id = path.get("id")

            if path_id in authored_paths:
                assert path_id not in registered_paths
                registered_paths[path_id] = path.get("d", "")

    assert registered_paths == {
        path_id: geometry for path_id, (geometry, _) in authored_paths.items()
    }

    assert source.read_bytes() == original_bytes


def test_prepare_preserves_foreground_touching_source_boundary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Transparent PNG foreground touching the top and left source
    boundaries must survive envelope derivation and tracing.

    Boundary-touching opaque pixels are authored artwork, not
    exterior background.
    """
    source = tmp_path / "boundary.png"
    trace = tmp_path / "trace.svg"
    envelope = tmp_path / "envelope.svg"

    with Image.new(
        "RGBA",
        (64, 64),
        (0, 0, 0, 0),
    ) as image:
        for y in range(0, 32):
            for x in range(0, 32):
                image.putpixel(
                    (x, y),
                    (0, 0, 0, 255),
                )

        image.save(
            source,
            format="PNG",
        )

    resolver = StubResolver(
        {
            "artifact_color_count": 1,
            "artwork_envelope_mode": "alpha",
        }
    )

    context = StubContext(
        inputs={
            "source": source,
        },
        outputs={
            "trace": trace,
            "envelope": envelope,
        },
        resolver=resolver,
    )

    traced_pixels: list[tuple[int, int, int, int]] = []

    def fake_trace_single_color(
        input_path: Path,
        output_path: Path,
    ) -> None:
        with Image.open(input_path) as prepared:
            rgba = prepared.convert("RGBA")

            try:
                sample_points = [
                    (0, 0),
                    (31, 0),
                    (0, 31),
                    (31, 31),
                    (32, 32),
                ]

                for point in sample_points:
                    pixel = rgba.getpixel(point)

                    assert isinstance(pixel, tuple)
                    assert len(pixel) == 4
                    assert all(isinstance(channel, int) for channel in pixel)

                    r, g, b, a = pixel
                    traced_pixels.append((r, g, b, a))
            finally:
                rgba.close()

        _write_fake_trace(output_path)

    monkeypatch.setattr(
        prepare,
        "_trace_single_color",
        fake_trace_single_color,
    )

    prepare.execute(
        cast(StageContext, context),
    )

    assert traced_pixels == [
        (0, 0, 0, 255),
        (0, 0, 0, 255),
        (0, 0, 0, 255),
        (0, 0, 0, 255),
        (0, 0, 0, 0),
    ]

    assert trace.is_file()
    assert envelope.is_file()

    # The derived envelope must include the authored boundary.
    envelope_root = ET.parse(envelope).getroot()

    envelope_paths = list(envelope_root.iter("{http://www.w3.org/2000/svg}path"))

    assert envelope_paths, "Expected a drawable artwork envelope."


def test_prepare_reduces_four_authored_colors_to_explicit_two(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """
    An explicit artifact_color_count of two limits tracing of
    four discovered authored colors to two.

    Reduction must be reported, not performed silently, and
    physical printer colors must remain outside Prepare.
    """
    resolver = StubResolver(
        {
            "artifact_color_count": 2,
            "artwork_envelope_mode": "alpha",
        }
    )

    context = _context(
        tmp_path,
        resolver,
    )

    traced_counts: list[int] = []

    def fake_trace_multicolor(
        source: Path,
        destination: Path,
        *,
        colors: int,
    ) -> None:
        with Image.open(source) as image:
            assert image.format == "PNG"
            assert image.size == (32, 32)

        traced_counts.append(colors)
        _write_fake_trace(destination)

    monkeypatch.setattr(
        prepare,
        "_trace_multicolor",
        fake_trace_multicolor,
    )

    with caplog.at_level("WARNING"):
        prepare.execute(
            cast(StageContext, context),
        )

    assert traced_counts == [2]

    assert "Reducing source artwork from 4 to" in caplog.text
    assert "at most 2 colors" in caplog.text

    assert "artifact_color_count" in resolver.requested
    assert "printer_colors" not in resolver.requested

    assert context.output("trace").is_file()
    assert context.output("envelope").is_file()


def test_prepare_explicit_one_color_rejects_multicolor_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    An explicit one-color maximum cannot silently discard
    multiple authored foreground colors.
    """
    resolver = StubResolver(
        {
            "artifact_color_count": 1,
            "artwork_envelope_mode": "alpha",
        }
    )
    context = _context(tmp_path, resolver)

    def forbidden_trace(*args: object, **kwargs: object) -> None:
        pytest.fail("Invalid color reduction must fail before tracing.")

    monkeypatch.setattr(prepare, "_trace_single_color", forbidden_trace)
    monkeypatch.setattr(prepare, "_trace_multicolor", forbidden_trace)

    with pytest.raises(
        prepare.PrepareError,
        match="Reducing multicolor artwork to one color",
    ):
        prepare.execute(cast(StageContext, context))


def test_prepare_does_not_increase_discovered_color_count(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    A maximum above the number of discovered authored colors
    must not manufacture additional Artifact colors.
    """
    resolver = StubResolver(
        {
            "artifact_color_count": 8,
            "artwork_envelope_mode": "alpha",
        }
    )
    context = _context(tmp_path, resolver)

    traced_counts: list[int] = []

    def fake_trace_multicolor(
        source: Path,
        destination: Path,
        *,
        colors: int,
    ) -> None:
        traced_counts.append(colors)
        _write_fake_trace(destination)

    monkeypatch.setattr(prepare, "_trace_multicolor", fake_trace_multicolor)

    prepare.execute(cast(StageContext, context))

    assert traced_counts == [4]
    assert "printer_colors" not in resolver.requested


def test_prepare_rejects_zero_artifact_color_count(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Zero is not a valid maximum number of Artifact colors.
    """
    resolver = StubResolver(
        {
            "artifact_color_count": 0,
            "artwork_envelope_mode": "alpha",
        }
    )
    context = _context(tmp_path, resolver)

    def forbidden_trace(*args: object, **kwargs: object) -> None:
        pytest.fail("Invalid color count must fail before tracing.")

    monkeypatch.setattr(prepare, "_trace_single_color", forbidden_trace)
    monkeypatch.setattr(prepare, "_trace_multicolor", forbidden_trace)

    with pytest.raises(
        prepare.PrepareError,
        match="artifact_color_count must be a positive integer",
    ):
        prepare.execute(cast(StageContext, context))


def test_prepare_rejects_boolean_artifact_color_count(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Boolean values must not be accepted as integer color counts.
    """
    resolver = StubResolver(
        {
            "artifact_color_count": True,
            "artwork_envelope_mode": "alpha",
        }
    )
    context = _context(tmp_path, resolver)

    def forbidden_trace(*args: object, **kwargs: object) -> None:
        pytest.fail("Boolean color count must fail before tracing.")

    monkeypatch.setattr(prepare, "_trace_single_color", forbidden_trace)
    monkeypatch.setattr(prepare, "_trace_multicolor", forbidden_trace)

    with pytest.raises(
        prepare.PrepareError,
        match="artifact_color_count must be a positive integer",
    ):
        prepare.execute(cast(StageContext, context))


def test_prepare_selects_single_color_tracer_for_one_authored_color(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    One discovered foreground color uses the single-color tracer,
    even when the configured maximum permits more colors.
    """
    source = tmp_path / "single-color.png"
    trace = tmp_path / "trace.svg"
    envelope = tmp_path / "envelope.svg"

    with Image.new("RGBA", (64, 64), (0, 0, 0, 0)) as image:
        for y in range(12, 52):
            for x in range(12, 52):
                image.putpixel((x, y), (30, 60, 180, 255))
        image.save(source, format="PNG")

    resolver = StubResolver(
        {
            "artifact_color_count": 4,
            "artwork_envelope_mode": "alpha",
        }
    )
    context = StubContext(
        inputs={"source": source},
        outputs={"trace": trace, "envelope": envelope},
        resolver=resolver,
    )

    traced_sources: list[Path] = []

    def fake_trace_single_color(
        input_path: Path,
        output_path: Path,
    ) -> None:
        traced_sources.append(input_path)
        _write_fake_trace(output_path)

    def forbidden_multicolor_trace(
        *args: object,
        **kwargs: object,
    ) -> None:
        pytest.fail("One authored color must not use multicolor tracing.")

    monkeypatch.setattr(prepare, "_trace_single_color", fake_trace_single_color)
    monkeypatch.setattr(prepare, "_trace_multicolor", forbidden_multicolor_trace)

    prepare.execute(cast(StageContext, context))

    assert len(traced_sources) == 1
    assert trace.is_file()
    assert envelope.is_file()
