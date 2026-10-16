"""
Tests for the Artwork prepare stage.

These tests characterize the storage boundary between the build engine
and the prepare-stage implementation and the derivation of the physical
Artwork envelope.

The prepare stage must consume only the paths supplied through
StageContext. Its persistent products must be written exactly to the
declared trace and envelope output paths.

Prepare preserves source color information for multicolor tracing.
Physical printer-color selection and assignment are not Prepare
responsibilities.
"""
# File: tests/model/artwork/test_prepare.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pytest
from PIL import Image

from lowkey_artifact_builder.model.models.artwork.stages import prepare

# =========================================================
# Test support
# =========================================================


class StubResolver:
    """
    Minimal Resolver-compatible object for prepare-stage tests.
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
    Minimal StageContext-compatible object for prepare-stage tests.
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


def _resolver(
    *,
    artifact_color_count: int = 2,
    envelope_mode: str | None = None,
) -> StubResolver:
    """
    Return standard prepare-stage configuration.
    """

    values: dict[str, Any] = {
        "artifact_color_count": artifact_color_count,
    }

    if envelope_mode is not None:
        values["artwork_envelope_mode"] = envelope_mode

    return StubResolver(
        values,
    )


def _write_source(
    path: Path,
) -> None:
    """
    Write simple source artwork with a meaningful opaque envelope.
    """

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    image = Image.new(
        "RGBA",
        (40, 40),
        (0, 0, 0, 0),
    )

    try:
        pixels = image.load()

        assert pixels is not None

        for y in range(8, 32):
            for x in range(8, 32):
                pixels[x, y] = (
                    255,
                    255,
                    255,
                    255,
                )

        for y in range(14, 26):
            for x in range(14, 26):
                pixels[x, y] = (
                    0,
                    0,
                    0,
                    255,
                )

        image.save(
            path,
            format="PNG",
        )

    finally:
        image.close()


def _fake_trace_multicolor(
    source: Path,
    output: Path,
    *,
    colors: int,
) -> None:
    """
    Stand in for Inkscape while preserving prepare-stage filesystem use.
    """

    assert source.is_file()
    assert colors == 2

    output.write_text(
        (
            '<svg xmlns="http://www.w3.org/2000/svg" '
            'width="40" height="40" viewBox="0 0 40 40">'
            '<rect x="0" y="0" width="40" height="40" fill="#ffffff"/>'
            "</svg>"
        ),
        encoding="utf-8",
    )


def _capture_traced_image(
    captured: list[Image.Image],
):
    """
    Return a trace stub that captures the prepared raster supplied for
    color tracing.
    """

    def capture(
        source: Path,
        output: Path,
        *,
        colors: int,
    ) -> None:
        with Image.open(source) as image:
            captured.append(
                image.convert(
                    "RGBA",
                )
            )

        _fake_trace_multicolor(
            source,
            output,
            colors=colors,
        )

    return capture


# =========================================================
# Storage-boundary tests
# =========================================================


def test_prepare_uses_declared_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    The prepare stage consumes the source path supplied by StageContext
    without reconstructing its filesystem location.
    """

    source = tmp_path / "deliberately" / "unrelated" / "source-input" / "anything.png"

    _write_source(source)

    trace = tmp_path / "somewhere-else" / "trace-output" / "anything.svg"

    envelope = tmp_path / "yet-another-place" / "envelope-output" / "boundary.svg"

    context = StubContext(
        inputs={
            "source": source,
        },
        outputs={
            "trace": trace,
            "envelope": envelope,
        },
        resolver=_resolver(),
    )

    loaded_sources: list[Path] = []

    real_load_source_image = prepare._load_source_image

    def observed_load_source_image(
        path: Path,
    ) -> Image.Image:
        loaded_sources.append(path)

        return real_load_source_image(path)

    monkeypatch.setattr(
        prepare,
        "_load_source_image",
        observed_load_source_image,
    )

    monkeypatch.setattr(
        prepare,
        "_trace_multicolor",
        _fake_trace_multicolor,
    )

    monkeypatch.setattr(
        prepare,
        "_clip_trace_to_envelope",
        lambda trace_path, artwork_envelope: None,
    )

    prepare.execute(context)  # type: ignore[arg-type]

    assert loaded_sources == [
        source,
    ]

    assert trace.is_file()
    assert envelope.is_file()


def test_prepare_uses_declared_output_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Trace and envelope products are written exactly to their declared
    StageContext output paths.

    The two products deliberately use unrelated parent directories.
    """

    source = tmp_path / "input" / "source.png"

    _write_source(source)

    trace = tmp_path / "arbitrary" / "trace-products" / "custom-trace.svg"

    envelope = tmp_path / "completely" / "different" / "envelope-products" / "custom-envelope.svg"

    context = StubContext(
        inputs={
            "source": source,
        },
        outputs={
            "trace": trace,
            "envelope": envelope,
        },
        resolver=_resolver(),
    )

    observed_trace: Path | None = None
    observed_envelope: Path | None = None

    real_write_envelope_svg = prepare._write_envelope_svg

    def observed_write_envelope_svg(
        artwork_envelope,
        output: Path,
    ) -> None:
        nonlocal observed_envelope

        observed_envelope = output

        real_write_envelope_svg(
            artwork_envelope,
            output,
        )

    def observed_trace_multicolor(
        temporary_source: Path,
        output: Path,
        *,
        colors: int,
    ) -> None:
        nonlocal observed_trace

        observed_trace = output

        _fake_trace_multicolor(
            temporary_source,
            output,
            colors=colors,
        )

    monkeypatch.setattr(
        prepare,
        "_write_envelope_svg",
        observed_write_envelope_svg,
    )

    monkeypatch.setattr(
        prepare,
        "_trace_multicolor",
        observed_trace_multicolor,
    )

    monkeypatch.setattr(
        prepare,
        "_clip_trace_to_envelope",
        lambda trace_path, artwork_envelope: None,
    )

    prepare.execute(context)  # type: ignore[arg-type]

    assert observed_trace == trace
    assert observed_envelope == envelope

    assert trace.is_file()
    assert envelope.is_file()


def test_prepare_temporary_raster_is_stage_local_and_removed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    The prepare stage places its temporary normalized raster beside the
    declared trace output and removes it after tracing.
    """

    source = tmp_path / "input" / "source.png"

    _write_source(source)

    trace_directory = tmp_path / "arbitrary" / "trace-products"

    trace = trace_directory / "trace.svg"

    envelope = tmp_path / "different" / "envelope-products" / "envelope.svg"

    context = StubContext(
        inputs={
            "source": source,
        },
        outputs={
            "trace": trace,
            "envelope": envelope,
        },
        resolver=_resolver(),
    )

    temporary_source: Path | None = None

    def observed_trace_multicolor(
        source_path: Path,
        output: Path,
        *,
        colors: int,
    ) -> None:
        nonlocal temporary_source

        temporary_source = source_path

        _fake_trace_multicolor(
            source_path,
            output,
            colors=colors,
        )

    monkeypatch.setattr(
        prepare,
        "_trace_multicolor",
        observed_trace_multicolor,
    )

    monkeypatch.setattr(
        prepare,
        "_clip_trace_to_envelope",
        lambda trace_path, artwork_envelope: None,
    )

    prepare.execute(context)  # type: ignore[arg-type]

    assert temporary_source is not None
    assert temporary_source.parent == trace_directory
    assert not temporary_source.exists()

    assert trace.is_file()
    assert envelope.is_file()


# =========================================================
# Artwork envelope semantics
# =========================================================


def test_prepare_defaults_to_alpha_envelope_mode(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Artwork preparation defaults to alpha envelope derivation when no
    envelope mode is explicitly configured.
    """

    source = tmp_path / "source.png"

    _write_source(
        source,
    )

    context = StubContext(
        inputs={
            "source": source,
        },
        outputs={
            "trace": tmp_path / "trace.svg",
            "envelope": tmp_path / "envelope.svg",
        },
        resolver=_resolver(),
    )

    observed_modes: list[str] = []

    def observed_derive_envelope(
        image: Image.Image,
        *,
        mode: str,
    ) -> np.ndarray:
        observed_modes.append(
            mode,
        )

        return prepare._build_envelope(
            prepare._foreground_mask(
                image,
            )
        )

    monkeypatch.setattr(
        prepare,
        "_derive_envelope",
        observed_derive_envelope,
    )

    monkeypatch.setattr(
        prepare,
        "_trace_multicolor",
        _fake_trace_multicolor,
    )

    monkeypatch.setattr(
        prepare,
        "_clip_trace_to_envelope",
        lambda trace_path, artwork_envelope: None,
    )

    prepare.execute(context)  # type: ignore[arg-type]

    assert observed_modes == [
        "alpha",
    ]


def test_alpha_envelope_mode_preserves_existing_alpha_behavior() -> None:
    """
    Alpha envelope mode preserves the existing alpha-derived envelope
    behavior.
    """

    image = Image.new(
        "RGBA",
        (
            40,
            40,
        ),
        (
            255,
            255,
            255,
            255,
        ),
    )

    try:
        expected = prepare._build_envelope(
            prepare._foreground_mask(
                image,
            )
        )

        envelope = prepare._derive_envelope(
            image,
            mode="alpha",
        )

        assert np.array_equal(
            envelope,
            expected,
        )

    finally:
        image.close()


def test_shrink_wrap_envelope_mode_excludes_opaque_exterior_background() -> None:
    """
    Shrink-wrap excludes opaque exterior background that alpha envelope
    derivation would otherwise treat as Artwork.
    """

    image = Image.new(
        "RGBA",
        (
            60,
            60,
        ),
        (
            255,
            255,
            255,
            255,
        ),
    )

    try:
        pixels = image.load()

        assert pixels is not None

        for y in range(
            15,
            45,
        ):
            for x in range(
                15,
                45,
            ):
                pixels[x, y] = (
                    0,
                    0,
                    0,
                    255,
                )

        envelope = prepare._derive_envelope(
            image,
            mode="shrink-wrap",
        )

        assert not envelope[0, 0]
        assert not envelope[0, 59]
        assert not envelope[59, 0]
        assert not envelope[59, 59]

        assert envelope[30, 30]

    finally:
        image.close()


def test_shrink_wrap_preserves_enclosed_region_matching_exterior_background() -> None:
    """
    Shrink-wrap does not exclude an enclosed Artwork region solely because
    its color matches the exterior background.
    """

    image = Image.new(
        "RGBA",
        (
            80,
            80,
        ),
        (
            255,
            255,
            255,
            255,
        ),
    )

    try:
        pixels = image.load()

        assert pixels is not None

        #
        # A solid black Artwork body separates its interior from the
        # white exterior background.
        #
        for y in range(
            15,
            65,
        ):
            for x in range(
                15,
                65,
            ):
                pixels[x, y] = (
                    0,
                    0,
                    0,
                    255,
                )

        #
        # This white region has exactly the same RGB value as the
        # exterior background, but it is enclosed by Artwork.
        #
        for y in range(
            30,
            50,
        ):
            for x in range(
                30,
                50,
            ):
                pixels[x, y] = (
                    255,
                    255,
                    255,
                    255,
                )

        envelope = prepare._derive_envelope(
            image,
            mode="shrink-wrap",
        )

        assert not envelope[0, 0]

        assert envelope[20, 20]
        assert envelope[40, 40]

    finally:
        image.close()


def test_shrink_wrap_bridges_exterior_connected_concavity() -> None:
    """
    Shrink-wrap produces a conservative outer envelope rather than
    following a deep exterior-connected concavity into the Artwork.
    """

    image = Image.new(
        "RGBA",
        (
            80,
            80,
        ),
        (
            255,
            255,
            255,
            255,
        ),
    )

    try:
        pixels = image.load()

        assert pixels is not None

        #
        # Begin with a large solid Artwork body.
        #
        for y in range(
            15,
            65,
        ):
            for x in range(
                15,
                65,
            ):
                pixels[x, y] = (
                    0,
                    0,
                    0,
                    255,
                )

        #
        # Cut a deep background-colored channel from the exterior into
        # the top of the Artwork. The channel remains connected to the
        # exterior background.
        #
        for y in range(
            0,
            45,
        ):
            for x in range(
                37,
                43,
            ):
                pixels[x, y] = (
                    255,
                    255,
                    255,
                    255,
                )

        envelope = prepare._derive_envelope(
            image,
            mode="shrink-wrap",
        )

        #
        # True exterior remains excluded.
        #
        assert not envelope[0, 0]

        #
        # Ordinary Artwork remains enclosed.
        #
        assert envelope[40, 25]
        assert envelope[40, 55]

        #
        # The deep exterior-connected concavity is bridged by the
        # conservative outer envelope.
        #
        assert envelope[30, 40]

    finally:
        image.close()


def test_unsupported_artwork_envelope_mode_is_rejected() -> None:
    """
    Artwork preparation rejects envelope modes not defined by the model.
    """

    image = Image.new(
        "RGBA",
        (
            40,
            40,
        ),
        (
            255,
            255,
            255,
            255,
        ),
    )

    try:
        with pytest.raises(
            prepare.PrepareError,
            match="Unsupported artwork envelope mode",
        ):
            prepare._derive_envelope(
                image,
                mode="aggressive",
            )

    finally:
        image.close()


# =========================================================
# Persistent envelope configuration
# =========================================================


def test_prepare_configured_shrink_wrap_changes_persistent_envelope(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Configured shrink-wrap mode affects the persistent envelope.svg
    produced by Artwork preparation.
    """

    source = tmp_path / "source.png"

    image = Image.new(
        "RGBA",
        (
            60,
            60,
        ),
        (
            255,
            255,
            255,
            255,
        ),
    )

    try:
        pixels = image.load()

        assert pixels is not None

        for y in range(
            15,
            45,
        ):
            for x in range(
                15,
                45,
            ):
                pixels[x, y] = (
                    0,
                    0,
                    0,
                    255,
                )

        image.save(
            source,
        )

    finally:
        image.close()

    monkeypatch.setattr(
        prepare,
        "_trace_multicolor",
        _fake_trace_multicolor,
    )

    monkeypatch.setattr(
        prepare,
        "_clip_trace_to_envelope",
        lambda trace_path, artwork_envelope: None,
    )

    alpha_envelope = tmp_path / "alpha-envelope.svg"

    alpha_context = StubContext(
        inputs={
            "source": source,
        },
        outputs={
            "trace": tmp_path / "alpha-trace.svg",
            "envelope": alpha_envelope,
        },
        resolver=_resolver(
            envelope_mode="alpha",
        ),
    )

    prepare.execute(
        alpha_context,  # type: ignore[arg-type]
    )

    shrink_wrap_envelope = tmp_path / "shrink-wrap-envelope.svg"

    shrink_wrap_context = StubContext(
        inputs={
            "source": source,
        },
        outputs={
            "trace": tmp_path / "shrink-wrap-trace.svg",
            "envelope": shrink_wrap_envelope,
        },
        resolver=_resolver(
            envelope_mode="shrink-wrap",
        ),
    )

    prepare.execute(
        shrink_wrap_context,  # type: ignore[arg-type]
    )

    assert alpha_envelope.is_file()
    assert shrink_wrap_envelope.is_file()

    assert alpha_envelope.read_text(
        encoding="utf-8",
    ) != shrink_wrap_envelope.read_text(
        encoding="utf-8",
    )


def test_prepare_svg_preserves_native_geometry_without_raster_tracing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    SVG preparation preserves authored vector geometry and colors
    without converting the source to PNG for multicolor tracing.
    """

    import xml.etree.ElementTree as ET

    source = tmp_path / "input" / "artwork.svg"
    source.parent.mkdir(parents=True)

    source.write_text(
        (
            '<svg xmlns="http://www.w3.org/2000/svg" '
            'width="100" height="100" viewBox="0 0 100 100">'
            '<path d="M 10 10 H 90 V 90 H 10 Z" '
            'fill="#ff0000"/>'
            "</svg>"
        ),
        encoding="utf-8",
    )

    trace = tmp_path / "products" / "trace.svg"
    envelope = tmp_path / "products" / "envelope.svg"

    context = StubContext(
        inputs={"source": source},
        outputs={
            "trace": trace,
            "envelope": envelope,
        },
        resolver=_resolver(artifact_color_count=5),
    )

    def unexpected_trace(*args: Any, **kwargs: Any) -> None:
        pytest.fail("SVG source must not use PNG multicolor tracing.")

    monkeypatch.setattr(
        prepare,
        "_trace_multicolor",
        unexpected_trace,
    )

    prepare.execute(context)  # type: ignore[arg-type]

    assert trace.is_file()
    assert envelope.is_file()

    tree = ET.parse(trace)

    paths = [element for element in tree.getroot().iter() if element.tag.endswith("}path")]

    assert any(element.get("d") == "M 10 10 H 90 V 90 H 10 Z" for element in paths)


def test_prepare_svg_preserves_colors_transforms_and_holes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Native SVG preparation preserves authored color regions and
    geometry, including transforms and holes, independently of the
    configured PNG tracing color count.
    """

    import xml.etree.ElementTree as ET

    source = tmp_path / "input" / "artwork.svg"
    source.parent.mkdir(parents=True)

    source.write_text(
        (
            '<svg xmlns="http://www.w3.org/2000/svg" '
            'width="100" height="100" viewBox="0 0 100 100">'
            '<g transform="translate(10, 5)">'
            '<path d="M 0 0 H 60 V 60 H 0 Z '
            'M 20 20 H 40 V 40 H 20 Z" '
            'fill="#ff0000" fill-rule="evenodd"/>'
            "</g>"
            '<path d="M 70 70 H 90 V 90 H 70 Z" '
            'fill="#0000ff"/>'
            "</svg>"
        ),
        encoding="utf-8",
    )

    trace = tmp_path / "products" / "trace.svg"
    envelope = tmp_path / "products" / "envelope.svg"

    context = StubContext(
        inputs={"source": source},
        outputs={
            "trace": trace,
            "envelope": envelope,
        },
        resolver=_resolver(artifact_color_count=1),
    )

    def unexpected_trace(*args: Any, **kwargs: Any) -> None:
        pytest.fail("SVG source must not use PNG multicolor tracing.")

    monkeypatch.setattr(
        prepare,
        "_trace_multicolor",
        unexpected_trace,
    )

    prepare.execute(context)  # type: ignore[arg-type]

    assert trace.is_file()
    assert envelope.is_file()

    root = ET.parse(trace).getroot()

    serialized = ET.tostring(
        root,
        encoding="unicode",
    ).lower()

    assert "#ff0000" in serialized
    assert "#0000ff" in serialized

    # The prepared trace must retain native vector geometry.
    paths = [element for element in root.iter() if element.tag.rsplit("}", 1)[-1] == "path"]

    assert paths

    # The transformed geometry must remain represented as SVG vectors.
    assert not any(element.tag.rsplit("}", 1)[-1] == "image" for element in root.iter())


def test_prepare_svg_rejects_embedded_raster_content(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Unsupported raster content embedded in an SVG must produce an
    actionable preparation error without invoking PNG tracing.
    """

    source = tmp_path / "input" / "artwork.svg"
    source.parent.mkdir(parents=True)

    source.write_text(
        (
            '<svg xmlns="http://www.w3.org/2000/svg" '
            'width="100" height="100" viewBox="0 0 100 100">'
            '<image x="10" y="10" width="80" height="80" '
            'href="data:image/png;base64,'
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJ"
            "AAAADUlEQVQIHWP4z8DwHwAFgAI/ScL/nwAAAABJRU5ErkJggg=="
            '"/>'
            "</svg>"
        ),
        encoding="utf-8",
    )

    trace = tmp_path / "products" / "trace.svg"
    envelope = tmp_path / "products" / "envelope.svg"

    context = StubContext(
        inputs={"source": source},
        outputs={
            "trace": trace,
            "envelope": envelope,
        },
        resolver=_resolver(),
    )

    def unexpected_trace(*args: Any, **kwargs: Any) -> None:
        pytest.fail("Unsupported SVG must not fall back to PNG tracing.")

    monkeypatch.setattr(
        prepare,
        "_trace_multicolor",
        unexpected_trace,
    )

    with pytest.raises(
        prepare.PrepareError,
        match=r"(?i)(unsupported|embedded|raster|image)",
    ):
        prepare.execute(context)  # type: ignore[arg-type]
