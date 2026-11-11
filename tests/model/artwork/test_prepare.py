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
        resolver=_resolver(
            envelope_mode="alpha",
        ),
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
        resolver=_resolver(
            envelope_mode="alpha",
        ),
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


def test_prepare_defaults_to_shrink_wrap_envelope_mode(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    When no envelope mode is explicitly resolved, Prepare uses
    the Model-defined shrink-wrap default.

    This fallback must agree with the permanent Artwork
    specification and Model parameter defaults.
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

    real_derive_envelope = prepare._derive_envelope

    def observed_derive_envelope(
        image: Image.Image,
        *,
        mode: str,
    ) -> np.ndarray:
        observed_modes.append(
            mode,
        )

        return real_derive_envelope(
            image,
            mode=mode,
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

    assert observed_modes == ["shrink-wrap"]

    assert context.output("trace").is_file()
    assert context.output("envelope").is_file()


def test_prepare_explicit_alpha_envelope_mode_remains_supported(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Explicit alpha mode remains selectable independently of
    the Model's shrink-wrap default.
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
        resolver=_resolver(
            envelope_mode="alpha",
        ),
    )

    observed_modes: list[str] = []

    real_derive_envelope = prepare._derive_envelope

    def observed_derive_envelope(
        image: Image.Image,
        *,
        mode: str,
    ) -> np.ndarray:
        observed_modes.append(
            mode,
        )

        return real_derive_envelope(
            image,
            mode=mode,
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

    assert observed_modes == ["alpha"]

    assert context.output("trace").is_file()
    assert context.output("envelope").is_file()


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
            artifact_color_count=1,
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


@pytest.mark.slow
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


@pytest.mark.slow
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


@pytest.mark.parametrize(
    ("color_count", "expected_mode"),
    [
        (1, "single"),
        (2, "multicolor"),
        (3, "multicolor"),
    ],
)
def test_prepare_selects_tracing_mode_from_color_count(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    color_count: int,
    expected_mode: str,
) -> None:
    """
    Prepare selects single-scan tracing for one Artifact color
    and multicolor tracing for two or more Artifact colors.

    Both operations produce the same declared trace Product.
    """
    source = tmp_path / "source.png"

    rgba = np.zeros((40, 40, 4), dtype=np.uint8)

    colors = [
        (255, 0, 0, 255),
        (0, 255, 0, 255),
        (0, 0, 255, 255),
    ]

    for index in range(color_count):
        x0 = 4 + index * 12
        rgba[8:32, x0 : x0 + 10] = colors[index]

    Image.fromarray(rgba, mode="RGBA").save(source)

    trace = tmp_path / "trace.svg"
    envelope = tmp_path / "envelope.svg"

    context = StubContext(
        inputs={"source": source},
        outputs={
            "trace": trace,
            "envelope": envelope,
        },
        resolver=_resolver(
            artifact_color_count=color_count,
            envelope_mode="shrink-wrap",
        ),
    )

    observed: list[tuple[str, int | None]] = []

    def write_trace(
        output: Path,
    ) -> None:
        output.write_text(
            (
                '<svg xmlns="http://www.w3.org/2000/svg" '
                'viewBox="0 0 40 40">'
                '<rect x="8" y="8" width="24" height="24" '
                'fill="#000000"/>'
                "</svg>"
            ),
            encoding="utf-8",
        )

    def fake_single(
        source: Path,
        output: Path,
    ) -> None:
        assert source.is_file()
        observed.append(("single", None))
        write_trace(output)

    def fake_multicolor(
        source: Path,
        output: Path,
        *,
        colors: int,
    ) -> None:
        assert source.is_file()
        observed.append(("multicolor", colors))
        write_trace(output)

    monkeypatch.setattr(
        prepare,
        "_trace_single_color",
        fake_single,
        raising=False,
    )

    monkeypatch.setattr(
        prepare,
        "_trace_multicolor",
        fake_multicolor,
    )

    monkeypatch.setattr(
        prepare,
        "_clip_trace_to_envelope",
        lambda trace_path, artwork_envelope: None,
    )

    prepare.execute(context)  # type: ignore[arg-type]

    assert observed == [
        (
            expected_mode,
            None if color_count == 1 else color_count,
        ),
    ]

    assert trace.is_file()
    assert envelope.is_file()


def test_trace_single_color_produces_declared_svg(
    tmp_path: Path,
) -> None:
    """
    Single-color tracing produces one compound SVG foreground path.

    Preserve disconnected regions, interior holes, exact pixel-edge
    geometry, and source registration, including boundary contact.
    """
    import xml.etree.ElementTree as ET

    source = tmp_path / "source.png"
    output = tmp_path / "trace.svg"

    # Transparent 40x40 raster with:
    # - one 20x20 foreground square,
    # - one 8x8 transparent interior hole,
    # - one disconnected 5x5 foreground square,
    # - one region touching the left raster boundary.
    image = np.zeros(
        (40, 40, 4),
        dtype=np.uint8,
    )

    image[8:28, 8:28] = (0, 0, 0, 255)
    image[14:22, 14:22] = (0, 0, 0, 0)
    image[32:37, 32:37] = (0, 0, 0, 255)
    image[18:23, 0:4] = (0, 0, 0, 255)

    Image.fromarray(
        image,
        mode="RGBA",
    ).save(source)

    prepare._trace_single_color(
        source,
        output,
    )

    assert output.is_file()

    tree = ET.parse(output)
    root = tree.getroot()

    assert root.tag == "{http://www.w3.org/2000/svg}svg"
    assert root.get("width") == "40"
    assert root.get("height") == "40"
    assert root.get("viewBox") == "0 0 40 40"

    paths = root.findall("{http://www.w3.org/2000/svg}path")

    assert len(paths) == 1

    path = paths[0]

    assert path.get("fill") == "#000000"
    assert path.get("fill-rule") == "nonzero"

    path_data = path.get("d")

    assert path_data is not None

    # Three foreground components and one enclosed hole
    # must produce four closed boundary loops.
    assert path_data.count("M ") == 4
    assert path_data.count("Z") == 4

    # Exact pixel boundaries, rather than OpenCV pixel-center
    # contours, must remain represented in the SVG.
    assert "8 8" in path_data
    assert "28 28" in path_data
    assert "14 14" in path_data
    assert "22 22" in path_data
    assert "32 32" in path_data
    assert "37 37" in path_data

    # Foreground touching the left boundary must not be inset.
    assert "0 18" in path_data or "0 23" in path_data


@pytest.mark.parametrize(
    ("foreground_rgb", "expected_fill"),
    [
        ((255, 0, 0), "#ff0000"),
        ((0, 0, 255), "#0000ff"),
        ((35, 140, 85), "#238c55"),
        ((0, 0, 0), "#000000"),
    ],
)
def test_trace_single_color_preserves_source_rgb(
    tmp_path: Path,
    foreground_rgb: tuple[int, int, int],
    expected_fill: str,
) -> None:
    """
    Single-color tracing preserves the authored foreground RGB.

    Transparent pixels do not contribute colors. Foreground
    color is independent of physical printer-color assignment.
    """
    import xml.etree.ElementTree as ET

    source = tmp_path / "source.png"
    output = tmp_path / "trace.svg"

    image = np.zeros(
        (40, 40, 4),
        dtype=np.uint8,
    )

    image[8:32, 8:32] = (
        *foreground_rgb,
        255,
    )

    # Transparent pixels may contain arbitrary RGB values.
    # They must not affect foreground color discovery.
    image[0:4, 0:4, :3] = (255, 255, 0)

    Image.fromarray(
        image,
        mode="RGBA",
    ).save(source)

    prepare._trace_single_color(
        source,
        output,
    )

    root = ET.parse(output).getroot()

    paths = root.findall("{http://www.w3.org/2000/svg}path")

    assert len(paths) == 1

    assert paths[0].get("fill") == expected_fill
    assert paths[0].get("fill-rule") == "nonzero"

    assert root.get("viewBox") == "0 0 40 40"


def test_prepare_single_color_preserves_source_rgb_through_clipping(
    tmp_path: Path,
) -> None:
    """
    Prepare preserves single-color source RGB through the
    complete PNG preparation and clipping pipeline.

    No Inkscape tracing or physical printer-color assignment
    is required for this operation.
    """
    import xml.etree.ElementTree as ET

    source = tmp_path / "source.png"
    trace = tmp_path / "trace.svg"
    envelope = tmp_path / "envelope.svg"

    image = np.zeros(
        (64, 64, 4),
        dtype=np.uint8,
    )

    # A green foreground region with an enclosed transparent hole.
    image[8:56, 8:56] = (35, 140, 85, 255)
    image[24:40, 24:40] = (0, 0, 0, 0)

    Image.fromarray(
        image,
        mode="RGBA",
    ).save(source)

    context = StubContext(
        inputs={
            "source": source,
        },
        outputs={
            "trace": trace,
            "envelope": envelope,
        },
        resolver=_resolver(
            artifact_color_count=1,
            envelope_mode="alpha",
        ),
    )

    prepare.execute(context)  # type: ignore[arg-type]

    assert trace.is_file()
    assert envelope.is_file()

    root = ET.parse(trace).getroot()

    namespace = "{http://www.w3.org/2000/svg}"

    artwork = root.find(f"{namespace}g[@id='artwork']")

    assert artwork is not None
    assert artwork.get("clip-path") == "url(#artwork-envelope)"

    paths = artwork.findall(f"{namespace}path")

    assert len(paths) == 1

    path = paths[0]

    assert path.get("fill") == "#238c55"
    assert path.get("fill-rule") == "nonzero"

    path_data = path.get("d")

    assert path_data is not None

    # Outer foreground boundary and interior hole.
    assert path_data.count("M ") == 2
    assert path_data.count("Z") == 2

    # The SVG retains the source coordinate system.
    assert root.get("viewBox") == "0 0 64 64"


def test_trace_single_color_ignores_antialiased_edge_rgb(
    tmp_path: Path,
) -> None:
    """
    Single-color tracing tolerates incidental RGB variation
    at partially transparent foreground boundaries.

    The authored opaque interior determines the Artifact RGB.
    Edge variation does not introduce additional Artifact colors
    or change the registered source coordinate system.
    """
    import xml.etree.ElementTree as ET

    source = tmp_path / "source.png"
    output = tmp_path / "trace.svg"

    image = np.zeros(
        (40, 40, 4),
        dtype=np.uint8,
    )

    # Slightly varied red along the partially transparent edge.
    # Alpha remains above the meaningful foreground threshold.
    image[7:33, 7:33] = (248, 8, 5, 160)

    # The solid interior contains the authored foreground color.
    image[8:32, 8:32] = (255, 0, 0, 255)

    # Transparent pixels may contain arbitrary RGB.
    image[0:4, 0:4, :3] = (0, 255, 0)

    Image.fromarray(
        image,
        mode="RGBA",
    ).save(source)

    prepare._trace_single_color(
        source,
        output,
    )

    root = ET.parse(output).getroot()

    paths = root.findall("{http://www.w3.org/2000/svg}path")

    assert len(paths) == 1

    path = paths[0]

    assert path.get("fill") == "#ff0000"
    assert path.get("fill-rule") == "nonzero"

    assert root.get("viewBox") == "0 0 40 40"

    path_data = path.get("d")

    assert path_data is not None

    # The partially transparent boundary remains meaningful
    # foreground geometry rather than being discarded.
    assert "7 7" in path_data
    assert "33 33" in path_data


def test_trace_single_color_rejects_distinct_opaque_colors(
    tmp_path: Path,
) -> None:
    """
    Single-color tracing must not silently merge two distinct
    authored opaque foreground colors into one Artifact color.

    Such artwork requires multicolor interpretation or an
    explicit future color-reduction policy.
    """
    source = tmp_path / "source.png"
    output = tmp_path / "trace.svg"

    image = np.zeros(
        (40, 40, 4),
        dtype=np.uint8,
    )

    # Two substantial, fully opaque foreground regions.
    image[8:20, 8:32] = (255, 0, 0, 255)
    image[20:32, 8:32] = (0, 0, 255, 255)

    Image.fromarray(
        image,
        mode="RGBA",
    ).save(source)

    with pytest.raises(
        prepare.PrepareError,
        match="Single-color tracing requires exactly one foreground",
    ):
        prepare._trace_single_color(
            source,
            output,
        )

    assert not output.exists()


def test_trace_single_color_rejects_distinct_partially_transparent_color(
    tmp_path: Path,
) -> None:
    """
    Single-color tracing must reject substantially different RGB
    colors in meaningful partially transparent foreground pixels.

    Partial transparency permits incidental antialiasing variation,
    but must not permit distinct authored foreground colors to
    be silently merged.

    Fully transparent background pixels do not contribute colors.
    """
    source = tmp_path / "source.png"
    output = tmp_path / "trace.svg"

    image = np.zeros(
        (40, 40, 4),
        dtype=np.uint8,
    )

    # Fully opaque red establishes the representative foreground RGB.
    image[8:32, 8:32] = (255, 0, 0, 255)

    # A substantial partially transparent blue region is a
    # different authored foreground color, not incidental
    # antialiasing of the red foreground.
    image[12:20, 12:20] = (0, 0, 255, 160)

    # Arbitrary RGB in fully transparent pixels must be ignored.
    image[0:4, 0:4, :3] = (0, 255, 0)

    Image.fromarray(
        image,
        mode="RGBA",
    ).save(source)

    with pytest.raises(
        prepare.PrepareError,
        match=("Single-color tracing requires exactly one foreground RGB color"),
    ):
        prepare._trace_single_color(
            source,
            output,
        )

    # Rejected artwork must not produce a misleading trace.
    assert not output.exists()


@pytest.mark.parametrize(
    ("foreground_rgb", "alpha", "expected_fill"),
    [
        ((255, 0, 0), 160, "#ff0000"),
        ((35, 140, 85), 200, "#238c55"),
        ((0, 0, 255), 128, "#0000ff"),
    ],
)
def test_trace_single_color_accepts_uniform_translucent_foreground(
    tmp_path: Path,
    foreground_rgb: tuple[int, int, int],
    alpha: int,
    expected_fill: str,
) -> None:
    """
    A uniformly translucent foreground remains one Artifact color.

    Fully opaque pixels are not required to establish the source RGB.
    The SVG preserves source registration and occupied geometry.
    """
    import xml.etree.ElementTree as ET

    source = tmp_path / "source.png"
    output = tmp_path / "trace.svg"

    image = np.zeros((40, 40, 4), dtype=np.uint8)
    image[8:32, 8:32] = (*foreground_rgb, alpha)

    Image.fromarray(image, mode="RGBA").save(source)

    prepare._trace_single_color(source, output)

    root = ET.parse(output).getroot()
    paths = root.findall("{http://www.w3.org/2000/svg}path")

    assert len(paths) == 1
    assert paths[0].get("fill") == expected_fill
    assert paths[0].get("fill-rule") == "nonzero"
    assert root.get("viewBox") == "0 0 40 40"

    path_data = paths[0].get("d")
    assert path_data is not None
    assert "8 8" in path_data
    assert "32 32" in path_data


def test_trace_single_color_accepts_translucent_antialiased_edges(
    tmp_path: Path,
) -> None:
    """
    When no pixel is fully opaque, the most opaque foreground
    establishes the RGB representation.

    Slightly different, less opaque edge colors are incidental
    and do not change the occupied geometry.
    """
    import xml.etree.ElementTree as ET

    source = tmp_path / "source.png"
    output = tmp_path / "trace.svg"

    image = np.zeros((40, 40, 4), dtype=np.uint8)

    image[7:33, 7:33] = (248, 8, 5, 160)
    image[8:32, 8:32] = (255, 0, 0, 200)

    Image.fromarray(image, mode="RGBA").save(source)

    prepare._trace_single_color(source, output)

    root = ET.parse(output).getroot()
    paths = root.findall("{http://www.w3.org/2000/svg}path")

    assert len(paths) == 1
    assert paths[0].get("fill") == "#ff0000"

    path_data = paths[0].get("d")
    assert path_data is not None
    assert "7 7" in path_data
    assert "33 33" in path_data

    assert root.get("viewBox") == "0 0 40 40"


def test_trace_single_color_rejects_distinct_maximum_opacity_colors(
    tmp_path: Path,
) -> None:
    """
    Distinct foreground colors at the same maximum opacity
    cannot be interpreted as one authored Artifact color.

    This remains true even when neither color is fully opaque.
    """
    source = tmp_path / "source.png"
    output = tmp_path / "trace.svg"

    image = np.zeros((40, 40, 4), dtype=np.uint8)

    image[8:20, 8:32] = (255, 0, 0, 200)
    image[20:32, 8:32] = (0, 0, 255, 200)

    Image.fromarray(image, mode="RGBA").save(source)

    with pytest.raises(
        prepare.PrepareError,
        match="Single-color tracing requires exactly one foreground",
    ):
        prepare._trace_single_color(source, output)

    assert not output.exists()


def test_prepare_single_color_excludes_opaque_exterior_background(
    tmp_path: Path,
) -> None:
    """
    Shrink-wrap preparation excludes an opaque white exterior
    background before single-color PNG tracing.

    The prepared trace contains only the authored foreground RGB,
    preserves its original pixel coordinates, and introduces
    neither white background geometry nor a second Artifact color.
    """
    import xml.etree.ElementTree as ET

    source = tmp_path / "source.png"
    trace = tmp_path / "trace.svg"
    envelope = tmp_path / "envelope.svg"

    image = np.full(
        (64, 64, 4),
        (255, 255, 255, 255),
        dtype=np.uint8,
    )

    # One solid green foreground on opaque white background.
    image[16:48, 16:48] = (35, 140, 85, 255)

    Image.fromarray(
        image,
        mode="RGBA",
    ).save(source)

    context = StubContext(
        inputs={"source": source},
        outputs={
            "trace": trace,
            "envelope": envelope,
        },
        resolver=_resolver(
            artifact_color_count=1,
            envelope_mode="shrink-wrap",
        ),
    )

    prepare.execute(context)  # type: ignore[arg-type]

    assert trace.is_file()
    assert envelope.is_file()

    namespace = "{http://www.w3.org/2000/svg}"

    root = ET.parse(trace).getroot()

    assert root.get("viewBox") == "0 0 64 64"

    artwork = root.find(f"{namespace}g[@id='artwork']")

    assert artwork is not None

    paths = artwork.findall(f"{namespace}path")

    assert len(paths) == 1

    path = paths[0]

    assert path.get("fill") == "#238c55"
    assert path.get("fill-rule") == "nonzero"

    path_data = path.get("d")

    assert path_data is not None

    # The original foreground has one closed boundary.
    assert path_data.count("M ") == 1
    assert path_data.count("Z") == 1

    # Original source coordinates remain registered.
    assert "16 16" in path_data
    assert "48 48" in path_data

    # Exterior white must not become foreground geometry.
    assert "0 0" not in path_data
    assert "64 64" not in path_data


def test_prepare_single_color_alpha_mode_does_not_infer_white_background(
    tmp_path: Path,
) -> None:
    """
    Alpha envelope mode uses source alpha as authoritative.

    An opaque white background is meaningful under alpha mode;
    it must not be silently removed through shrink-wrap inference.

    Because the source contains two distinct fully opaque RGB
    colors, single-color tracing must reject it.
    """
    source = tmp_path / "source.png"
    trace = tmp_path / "trace.svg"
    envelope = tmp_path / "envelope.svg"

    image = np.full(
        (64, 64, 4),
        (255, 255, 255, 255),
        dtype=np.uint8,
    )

    image[16:48, 16:48] = (35, 140, 85, 255)

    Image.fromarray(
        image,
        mode="RGBA",
    ).save(source)

    context = StubContext(
        inputs={"source": source},
        outputs={
            "trace": trace,
            "envelope": envelope,
        },
        resolver=_resolver(
            artifact_color_count=1,
            envelope_mode="alpha",
        ),
    )

    with pytest.raises(
        prepare.PrepareError,
        match=r"Reducing multicolor artwork to one color is not supported",
    ):
        prepare.execute(context)  # type: ignore[arg-type]

    assert not trace.exists()


# =========================================================
# Automatic Artifact color-count resolution
# =========================================================


@pytest.mark.parametrize(
    ("foreground_colors", "expected_count"),
    [
        ([(255, 0, 0)], 1),
        ([(255, 0, 0), (0, 0, 255)], 2),
    ],
)
def test_prepare_automatically_discovers_png_color_count(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    foreground_colors: list[tuple[int, int, int]],
    expected_count: int,
) -> None:
    """
    PNG preparation discovers meaningful foreground colors
    within the configured maximum artifact color count.

    One color selects single-color tracing; multiple colors
    select multicolor tracing. The automatic decision is logged
    at INFO level.
    """
    import logging

    source = tmp_path / "source.png"
    trace = tmp_path / "trace.svg"
    envelope = tmp_path / "envelope.svg"

    image = np.zeros((64, 64, 4), dtype=np.uint8)

    image[8:56, 8:56] = (*foreground_colors[0], 255)

    if len(foreground_colors) > 1:
        image[32:56, 8:56] = (*foreground_colors[1], 255)

    Image.fromarray(image, mode="RGBA").save(source)

    context = StubContext(
        inputs={"source": source},
        outputs={"trace": trace, "envelope": envelope},
        resolver=StubResolver(
            {
                "artwork_envelope_mode": "alpha",
                "artifact_color_count": 2,
            }
        ),
    )

    selected_counts: list[int] = []

    def trace_single(
        source_path: Path,
        output_path: Path,
    ) -> None:
        assert source_path.is_file()
        selected_counts.append(1)
        output_path.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg"/>',
            encoding="utf-8",
        )

    def trace_multi(
        source_path: Path,
        output_path: Path,
        *,
        colors: int,
    ) -> None:
        assert source_path.is_file()
        selected_counts.append(colors)
        output_path.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg"/>',
            encoding="utf-8",
        )

    monkeypatch.setattr(
        prepare,
        "_trace_single_color",
        trace_single,
    )
    monkeypatch.setattr(
        prepare,
        "_trace_multicolor",
        trace_multi,
    )
    monkeypatch.setattr(
        prepare,
        "_clip_trace_to_envelope",
        lambda trace_path, artwork_envelope: None,
    )

    with caplog.at_level(logging.INFO):
        prepare.execute(context)  # type: ignore[arg-type]

    assert selected_counts == [expected_count]
    assert trace.is_file()
    assert envelope.is_file()

    messages = [
        record.getMessage().lower() for record in caplog.records if record.levelno == logging.INFO
    ]

    assert any(
        str(expected_count) in message and ("discover" in message or "automatic" in message)
        for message in messages
    )


@pytest.mark.parametrize(
    ("maximum_count", "should_succeed"),
    [
        (1, False),
        (2, True),
        (3, True),
    ],
)
def test_prepare_maximum_png_color_count_preserves_authored_colors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    maximum_count: int,
    should_succeed: bool,
) -> None:
    """
    The configured count is a maximum, not an exact tracing count.

    Two authored colors require at least two available colors.
    A larger maximum must not invent additional colors.
    """
    import logging

    source = tmp_path / "source.png"
    trace = tmp_path / "trace.svg"
    envelope = tmp_path / "envelope.svg"

    rgba = np.zeros((64, 64, 4), dtype=np.uint8)

    rgba[8:32, 8:56] = (255, 0, 0, 255)
    rgba[32:56, 8:56] = (0, 0, 255, 255)

    Image.fromarray(rgba, mode="RGBA").save(source)

    context = StubContext(
        inputs={"source": source},
        outputs={"trace": trace, "envelope": envelope},
        resolver=StubResolver(
            {
                "artwork_envelope_mode": "alpha",
                "artifact_color_count": maximum_count,
            }
        ),
    )

    traced_counts: list[int] = []

    def trace_multi(
        source_path: Path,
        output_path: Path,
        *,
        colors: int,
    ) -> None:
        traced_counts.append(colors)

        output_path.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg"/>',
            encoding="utf-8",
        )

    monkeypatch.setattr(
        prepare,
        "_trace_multicolor",
        trace_multi,
    )

    monkeypatch.setattr(
        prepare,
        "_clip_trace_to_envelope",
        lambda trace_path, artwork_envelope: None,
    )

    with caplog.at_level(logging.INFO):
        if should_succeed:
            prepare.execute(context)  # type: ignore[arg-type]
        else:
            with pytest.raises(
                prepare.PrepareError,
                match=r"Reducing multicolor artwork to one color is not supported",
            ):
                prepare.execute(context)  # type: ignore[arg-type]

    if should_succeed:
        assert traced_counts == [2]
        assert trace.is_file()
        assert envelope.is_file()

        assert any(
            record.levelno == logging.INFO
            and "Discovered 2 foreground colors" in record.getMessage()
            and f"maximum={maximum_count}" in record.getMessage()
            and "effective tracing count=2" in record.getMessage()
            for record in caplog.records
        )
    else:
        assert traced_counts == []
        assert not trace.exists()


def test_prepare_matching_single_color_override_succeeds(
    tmp_path: Path,
) -> None:
    """
    Explicit artifact_color_count=1 is valid when exactly
    one meaningful foreground color is discovered.
    """
    import xml.etree.ElementTree as ET

    source = tmp_path / "source.png"
    trace = tmp_path / "trace.svg"
    envelope = tmp_path / "envelope.svg"

    rgba = np.zeros((48, 48, 4), dtype=np.uint8)

    rgba[0:32, 0:32] = (30, 120, 210, 255)

    # Incidental antialiasing must not create another color.
    rgba[31, 0:32] = (33, 118, 207, 180)

    Image.fromarray(rgba, mode="RGBA").save(source)

    context = StubContext(
        inputs={"source": source},
        outputs={"trace": trace, "envelope": envelope},
        resolver=StubResolver(
            {
                "artwork_envelope_mode": "alpha",
                "artifact_color_count": 1,
            }
        ),
    )

    prepare.execute(context)  # type: ignore[arg-type]

    assert trace.is_file()
    assert envelope.is_file()

    namespace = "{http://www.w3.org/2000/svg}"

    root = ET.parse(trace).getroot()

    artwork = root.find(f"{namespace}g[@id='artwork']")

    assert artwork is not None

    paths = artwork.findall(f"{namespace}path")

    assert len(paths) == 1
    assert paths[0].get("fill") == "#1e78d2"

    assert root.get("viewBox") == "0 0 48 48"


def test_prepare_explicit_color_count_cannot_quantize_gradient(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    An explicit tracing count does not authorize implicit
    quantization of continuously varying source colors.
    """
    source = tmp_path / "gradient.png"
    trace = tmp_path / "trace.svg"
    envelope = tmp_path / "envelope.svg"

    rgba = np.zeros((64, 64, 4), dtype=np.uint8)

    for x in range(8, 56):
        fraction = (x - 8) / 47

        red = round(255 * (1 - fraction))
        blue = round(255 * fraction)

        rgba[8:56, x] = (red, 0, blue, 255)

    Image.fromarray(rgba, mode="RGBA").save(source)

    context = StubContext(
        inputs={"source": source},
        outputs={"trace": trace, "envelope": envelope},
        resolver=StubResolver(
            {
                "artwork_envelope_mode": "alpha",
                "artifact_color_count": 3,
            }
        ),
    )

    traced_counts: list[int] = []

    def trace_multi(
        source_path: Path,
        output_path: Path,
        *,
        colors: int,
    ) -> None:
        traced_counts.append(colors)

        output_path.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg"/>',
            encoding="utf-8",
        )

    monkeypatch.setattr(
        prepare,
        "_trace_multicolor",
        trace_multi,
    )

    with pytest.raises(
        prepare.PrepareError,
        match=r"(?i)(ambiguous|gradient|color variation)",
    ):
        prepare.execute(context)  # type: ignore[arg-type]

    assert traced_counts == []
    assert not trace.exists()


@pytest.mark.parametrize(
    ("include_second_color", "expected_count"),
    [
        (False, 1),
        (True, 2),
    ],
)
def test_discover_png_color_count_ignores_opaque_rgb_noise(
    include_second_color: bool,
    expected_count: int,
) -> None:
    """
    Minor RGB differences within an authored foreground region
    must not introduce additional Artifact colors, including
    when every pixel is fully opaque.

    A substantial, distinctly colored authored region must
    remain a separate Artifact color.
    """
    rgba = np.zeros((64, 64, 4), dtype=np.uint8)

    rgba[8:56, 8:56] = (255, 0, 0, 255)

    # Small variations of the same authored red.
    rgba[12:16, 12:16] = (252, 3, 2, 255)
    rgba[20:24, 20:24] = (249, 5, 4, 255)
    rgba[40:44, 40:44] = (253, 2, 1, 255)

    if include_second_color:
        rgba[32:56, 8:56] = (0, 0, 255, 255)

    image = Image.fromarray(rgba, mode="RGBA")

    assert prepare._discover_png_color_count(image) == expected_count


@pytest.mark.parametrize(
    ("interior_alpha", "include_second_color", "expected_count"),
    [
        (255, False, 1),
        (200, False, 1),
        (200, True, 2),
    ],
)
def test_discover_png_color_count_handles_translucent_edges(
    interior_alpha: int,
    include_second_color: bool,
    expected_count: int,
) -> None:
    """
    Antialiased edges belong to their authored foreground
    color even when no fully opaque pixels exist.

    A substantially different meaningful translucent region
    must be discovered independently.
    """
    rgba = np.zeros((64, 64, 4), dtype=np.uint8)

    # Edge pixels have slightly different RGB and lower alpha.
    rgba[7:57, 7:57] = (248, 8, 5, 160)

    # Main authored foreground.
    rgba[8:56, 8:56] = (255, 0, 0, interior_alpha)

    if include_second_color:
        rgba[24:40, 24:40] = (0, 0, 255, 160)

    # Arbitrary RGB in fully transparent pixels is irrelevant.
    rgba[0:4, 0:4, :3] = (0, 255, 0)

    image = Image.fromarray(rgba, mode="RGBA")

    assert prepare._discover_png_color_count(image) == expected_count


def test_prepare_auto_single_color_accepts_minor_opaque_rgb_variation(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """
    Automatic color discovery and single-color tracing must agree.

    Minor fully opaque RGB variations belong to one authored
    foreground color. They must not cause tracing to fail or
    create additional SVG paths.
    """
    import logging
    import xml.etree.ElementTree as ET

    source = tmp_path / "source.png"
    trace = tmp_path / "trace.svg"
    envelope = tmp_path / "envelope.svg"

    rgba = np.zeros((64, 64, 4), dtype=np.uint8)

    rgba[8:56, 8:56] = (255, 0, 0, 255)

    # Minor opaque variations within the same red region.
    rgba[12:16, 12:16] = (252, 3, 2, 255)
    rgba[20:24, 20:24] = (249, 5, 4, 255)
    rgba[40:44, 40:44] = (253, 2, 1, 255)

    Image.fromarray(rgba, mode="RGBA").save(source)

    context = StubContext(
        inputs={"source": source},
        outputs={"trace": trace, "envelope": envelope},
        resolver=_resolver(artifact_color_count=2, envelope_mode="alpha"),
    )

    with caplog.at_level(logging.INFO):
        prepare.execute(context)  # type: ignore[arg-type]

    assert trace.is_file()
    assert envelope.is_file()

    root = ET.parse(trace).getroot()
    namespace = "{http://www.w3.org/2000/svg}"

    assert root.get("viewBox") == "0 0 64 64"

    artwork = root.find(f"{namespace}g[@id='artwork']")
    assert artwork is not None

    paths = artwork.findall(f"{namespace}path")
    assert len(paths) == 1

    path = paths[0]
    assert path.get("fill") == "#ff0000"
    assert path.get("fill-rule") == "nonzero"

    path_data = path.get("d")
    assert path_data is not None
    assert "8 8" in path_data
    assert "56 56" in path_data

    assert any(
        record.levelno == logging.INFO
        and "Discovered 1 foreground colors" in record.getMessage()
        and "effective tracing count=1" in record.getMessage()
        for record in caplog.records
    )


def test_prepare_explicit_single_color_rejects_distinct_opaque_colors(
    tmp_path: Path,
) -> None:
    """
    An explicit count of one cannot authorize merging two
    substantially different authored foreground colors.

    The preparation stage must reject the source rather than
    producing misleading single-color geometry.
    """
    source = tmp_path / "source.png"
    trace = tmp_path / "trace.svg"
    envelope = tmp_path / "envelope.svg"

    rgba = np.zeros((64, 64, 4), dtype=np.uint8)

    rgba[8:32, 8:56] = (255, 0, 0, 255)
    rgba[32:56, 8:56] = (0, 0, 255, 255)

    Image.fromarray(rgba, mode="RGBA").save(source)

    context = StubContext(
        inputs={"source": source},
        outputs={"trace": trace, "envelope": envelope},
        resolver=StubResolver(
            {
                "artwork_envelope_mode": "alpha",
                "artifact_color_count": 1,
            }
        ),
    )

    with pytest.raises(
        prepare.PrepareError,
        match=r"Reducing multicolor artwork to one color is not supported",
    ):
        prepare.execute(context)  # type: ignore[arg-type]

    assert not trace.exists()


def test_prepare_auto_color_discovery_rejects_continuous_gradient(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """
    Continuous color variation is not an unambiguous set
    of discrete authored Artifact colors.

    Automatic discovery must fail with an actionable warning
    instead of selecting an arbitrary multicolor tracing count.
    """
    import logging

    source = tmp_path / "source.png"
    trace = tmp_path / "trace.svg"
    envelope = tmp_path / "envelope.svg"

    rgba = np.zeros((64, 64, 4), dtype=np.uint8)

    # A fully opaque, continuous red-to-blue gradient.
    # Transparent margins establish the exterior background.
    for x in range(8, 56):
        fraction = (x - 8) / 47
        red = round(255 * (1 - fraction))
        blue = round(255 * fraction)

        rgba[8:56, x] = (red, 0, blue, 255)

    Image.fromarray(rgba, mode="RGBA").save(source)

    context = StubContext(
        inputs={"source": source},
        outputs={"trace": trace, "envelope": envelope},
        resolver=_resolver(artifact_color_count=20, envelope_mode="alpha"),
    )

    with caplog.at_level(logging.WARNING):
        with pytest.raises(
            prepare.PrepareError,
            match=r"(?i)(ambiguous|gradient|color variation)",
        ):
            prepare.execute(context)  # type: ignore[arg-type]

    assert not trace.exists()

    warnings = [
        record.getMessage().lower()
        for record in caplog.records
        if record.levelno == logging.WARNING
    ]

    assert any(
        ("color" in message) and ("ambiguous" in message or "gradient" in message)
        for message in warnings
    )

    assert any("artifact_color_count" in message for message in warnings)


def test_discover_png_color_count_preserves_three_distinct_regions() -> None:
    """
    Automatic discovery must not reject ordinary discrete
    multicolor artwork merely because it contains more
    than two authored foreground colors.
    """
    rgba = np.zeros((64, 64, 4), dtype=np.uint8)

    rgba[8:24, 8:56] = (255, 0, 0, 255)
    rgba[24:40, 8:56] = (0, 255, 0, 255)
    rgba[40:56, 8:56] = (0, 0, 255, 255)

    image = Image.fromarray(rgba, mode="RGBA")

    assert prepare._discover_png_color_count(image) == 3


def test_discover_png_color_count_accepts_twenty_discrete_colors() -> None:
    """
    Twenty distinctly authored color regions are valid artwork.

    Automatic discovery must not impose an arbitrary maximum
    color count or classify sharp boundaries as gradients.

    Each authored RGB color is separated from every other
    by more than the incidental-variation tolerance.
    """
    rgba = np.zeros((64, 128, 4), dtype=np.uint8)

    levels = (0, 127, 255)

    colors = [(red, green, blue) for red in levels for green in levels for blue in levels][:20]

    assert len(colors) == 20
    assert len(set(colors)) == 20

    for index, color in enumerate(colors):
        x0 = 4 + index * 6

        rgba[8:56, x0 : x0 + 6] = (
            *color,
            255,
        )

    image = Image.fromarray(
        rgba,
        mode="RGBA",
    )

    assert prepare._discover_png_color_count(image) == 20


def test_discover_png_color_count_accepts_antialiased_color_boundary() -> None:
    """
    A narrow antialiased transition between two solid authored
    colors must not be interpreted as a continuous gradient.
    """
    rgba = np.zeros((64, 64, 4), dtype=np.uint8)

    rgba[8:56, 8:32] = (255, 0, 0, 255)
    rgba[8:56, 32:56] = (0, 0, 255, 255)

    # Slight RGB variations near the boundary.
    rgba[8:56, 30] = (250, 3, 5, 255)
    rgba[8:56, 31] = (245, 5, 10, 255)
    rgba[8:56, 32] = (10, 5, 245, 255)
    rgba[8:56, 33] = (5, 3, 250, 255)

    image = Image.fromarray(rgba, mode="RGBA")

    assert prepare._discover_png_color_count(image) == 2


def test_discover_png_color_count_accepts_scattered_rgb_noise() -> None:
    """
    Small isolated RGB variations are incidental source noise,
    not a continuous gradient or additional authored colors.
    """
    rgba = np.zeros((64, 64, 4), dtype=np.uint8)

    rgba[8:56, 8:56] = (200, 50, 30, 255)

    for y in range(12, 52, 8):
        for x in range(12, 52, 8):
            rgba[y, x] = (196, 53, 33, 255)

    image = Image.fromarray(rgba, mode="RGBA")

    assert prepare._discover_png_color_count(image) == 1


@pytest.mark.parametrize(
    ("edge", "bounds"),
    [
        ("top", (8, 0, 24, 20)),
        ("bottom", (8, 12, 24, 32)),
        ("left", (0, 8, 20, 24)),
        ("right", (12, 8, 32, 24)),
    ],
)
def test_prepare_single_color_preserves_boundary_touching_artwork(
    tmp_path: Path,
    edge: str,
    bounds: tuple[int, int, int, int],
) -> None:
    """
    Foreground touching any image boundary is valid artwork.

    Preparation preserves original coordinates, source dimensions,
    source RGB, and a closed physical envelope.
    """
    import xml.etree.ElementTree as ET

    source = tmp_path / f"{edge}.png"
    trace = tmp_path / "trace.svg"
    envelope = tmp_path / "envelope.svg"

    rgba = np.zeros((32, 32, 4), dtype=np.uint8)

    x0, y0, x1, y1 = bounds

    rgba[y0:y1, x0:x1] = (0, 0, 0, 255)

    Image.fromarray(rgba, mode="RGBA").save(source)

    context = StubContext(
        inputs={"source": source},
        outputs={"trace": trace, "envelope": envelope},
        resolver=_resolver(artifact_color_count=1, envelope_mode="alpha"),
    )

    prepare.execute(context)  # type: ignore[arg-type]

    namespace = "{http://www.w3.org/2000/svg}"

    trace_root = ET.parse(trace).getroot()
    envelope_root = ET.parse(envelope).getroot()

    assert trace_root.get("viewBox") == "0 0 32 32"
    assert envelope_root.get("viewBox") == "0 0 32 32"

    artwork = trace_root.find(f"{namespace}g[@id='artwork']")
    assert artwork is not None

    paths = artwork.findall(f"{namespace}path")
    assert len(paths) == 1
    assert paths[0].get("fill") == "#000000"

    path_data = paths[0].get("d")
    assert path_data is not None

    # The traced geometry must retain the original rectangle.
    for x, y in (
        (x0, y0),
        (x1, y0),
        (x1, y1),
        (x0, y1),
    ):
        assert f"{x} {y}" in path_data

    envelope_paths = envelope_root.findall(f"{namespace}path")
    assert len(envelope_paths) == 1

    envelope_data = envelope_paths[0].get("d")
    assert envelope_data is not None
    assert envelope_data.strip().endswith("Z")


def test_prepare_single_color_preserves_corner_touching_artwork(
    tmp_path: Path,
) -> None:
    """
    Foreground occupying an image corner must remain intact
    without artificial transparent padding.
    """
    import xml.etree.ElementTree as ET

    source = tmp_path / "corner.png"
    trace = tmp_path / "trace.svg"
    envelope = tmp_path / "envelope.svg"

    rgba = np.zeros((32, 32, 4), dtype=np.uint8)

    rgba[0:20, 0:20] = (35, 140, 85, 255)

    Image.fromarray(rgba, mode="RGBA").save(source)

    context = StubContext(
        inputs={"source": source},
        outputs={"trace": trace, "envelope": envelope},
        resolver=_resolver(artifact_color_count=1, envelope_mode="alpha"),
    )

    prepare.execute(context)  # type: ignore[arg-type]

    namespace = "{http://www.w3.org/2000/svg}"

    root = ET.parse(trace).getroot()
    artwork = root.find(f"{namespace}g[@id='artwork']")

    assert artwork is not None

    paths = artwork.findall(f"{namespace}path")
    assert len(paths) == 1

    assert paths[0].get("fill") == "#238c55"

    path_data = paths[0].get("d")
    assert path_data is not None

    for coordinate in (
        "0 0",
        "20 0",
        "20 20",
        "0 20",
    ):
        assert coordinate in path_data

    envelope_root = ET.parse(envelope).getroot()
    assert envelope_root.get("viewBox") == "0 0 32 32"


def test_prepare_single_color_accepts_fully_occupied_image(
    tmp_path: Path,
) -> None:
    """
    A fully occupied single-color PNG has a valid closed
    envelope and does not require exterior transparency.
    """
    import xml.etree.ElementTree as ET

    source = tmp_path / "full.png"
    trace = tmp_path / "trace.svg"
    envelope = tmp_path / "envelope.svg"

    rgba = np.zeros((32, 32, 4), dtype=np.uint8)
    rgba[:, :] = (0, 0, 0, 255)

    Image.fromarray(rgba, mode="RGBA").save(source)

    context = StubContext(
        inputs={"source": source},
        outputs={"trace": trace, "envelope": envelope},
        resolver=_resolver(artifact_color_count=1, envelope_mode="alpha"),
    )

    prepare.execute(context)  # type: ignore[arg-type]

    namespace = "{http://www.w3.org/2000/svg}"

    trace_root = ET.parse(trace).getroot()
    envelope_root = ET.parse(envelope).getroot()

    assert trace_root.get("viewBox") == "0 0 32 32"
    assert envelope_root.get("viewBox") == "0 0 32 32"

    artwork = trace_root.find(f"{namespace}g[@id='artwork']")
    assert artwork is not None

    paths = artwork.findall(f"{namespace}path")
    assert len(paths) == 1

    path_data = paths[0].get("d")
    assert path_data is not None

    for coordinate in (
        "0 0",
        "32 0",
        "32 32",
        "0 32",
    ):
        assert coordinate in path_data

    envelope_paths = envelope_root.findall(f"{namespace}path")
    assert len(envelope_paths) == 1
    assert envelope_paths[0].get("d", "").strip().endswith("Z")


def test_prepare_bug06_preserves_boundary_touching_artwork(
    tmp_path: Path,
) -> None:
    """
    BUG-006 regression: real boundary-touching PNG artwork.

    The original source must prepare successfully without
    transparent padding or changes to its dimensions.

    Preparation must produce a valid, closed Artwork envelope
    and registered SVG geometry in source coordinates.
    """
    import xml.etree.ElementTree as ET

    source = Path(__file__).resolve().parents[2] / "assets" / "bug06.png"

    assert source.is_file(), f"Missing BUG-006 reproduction fixture: {source}"

    with Image.open(source) as image:
        assert image.format == "PNG"

        width, height = image.size

        rgba = np.asarray(
            image.convert("RGBA"),
            dtype=np.uint8,
        )

    assert width > 0
    assert height > 0

    alpha = rgba[:, :, 3]

    # Confirm that the fixture exercises boundary-touching
    # foreground rather than merely containing an arbitrary PNG.
    threshold = prepare.DEFAULT_ALPHA_THRESHOLD

    foreground = alpha >= threshold

    assert np.any(foreground)

    assert (
        np.any(foreground[0, :])
        or np.any(foreground[-1, :])
        or np.any(foreground[:, 0])
        or np.any(foreground[:, -1])
    ), "BUG-006 fixture must contain boundary-touching foreground."

    trace = tmp_path / "trace.svg"
    envelope = tmp_path / "envelope.svg"

    context = StubContext(
        inputs={
            "source": source,
        },
        outputs={
            "trace": trace,
            "envelope": envelope,
        },
        resolver=StubResolver(
            {
                "artwork_envelope_mode": "alpha",
                "artifact_color_count": 20,
            }
        ),
    )

    # Execute the actual preparation implementation.
    # Do not mock tracing, envelope construction, or clipping.
    prepare.execute(context)  # type: ignore[arg-type]

    assert trace.is_file()
    assert envelope.is_file()

    namespace = "{http://www.w3.org/2000/svg}"

    trace_root = ET.parse(trace).getroot()
    envelope_root = ET.parse(envelope).getroot()

    expected_viewbox = f"0 0 {width} {height}"

    assert trace_root.get("viewBox") == expected_viewbox
    assert envelope_root.get("viewBox") == expected_viewbox

    # Registered artwork must exist and contain real geometry.
    artwork = trace_root.find(f"{namespace}g[@id='artwork']")

    assert artwork is not None

    artwork_paths = artwork.findall(f"{namespace}path")

    assert artwork_paths

    assert all(path.get("d") for path in artwork_paths)

    # The envelope must contain a closed contour.
    envelope_paths = envelope_root.findall(f"{namespace}path")

    assert envelope_paths

    envelope_data = " ".join(path.get("d", "") for path in envelope_paths)

    assert envelope_data.strip()
    assert "Z" in envelope_data.upper()

    # The source fixture must not be modified by preparation.
    with Image.open(source) as image:
        assert image.size == (width, height)
        assert image.format == "PNG"


def test_bug06_shrink_wrap_produces_valid_envelope() -> None:
    """
    BUG-006: the original PNG must produce a valid
    shrink-wrap envelope in its source coordinate system.

    Foreground touching the raster boundary must not
    be lost during morphological closing.
    """
    source = Path(__file__).resolve().parents[2] / "assets" / "bug06.png"

    assert source.is_file()

    with Image.open(source) as image:
        rgba_image = image.convert("RGBA")
        width, height = rgba_image.size

        envelope = prepare._derive_envelope(
            rgba_image,
            mode="shrink-wrap",
        )

    assert envelope.shape == (height, width)
    assert envelope.dtype == np.bool_
    assert np.any(envelope)

    # At least one occupied boundary pixel must survive
    # shrink-wrap construction when the source foreground
    # reaches that boundary.
    source_alpha = np.asarray(rgba_image)[:, :, 3]

    source_boundary = np.concatenate(
        (
            source_alpha[0, :],
            source_alpha[-1, :],
            source_alpha[:, 0],
            source_alpha[:, -1],
        )
    )

    envelope_boundary = np.concatenate(
        (
            envelope[0, :],
            envelope[-1, :],
            envelope[:, 0],
            envelope[:, -1],
        )
    )

    if np.any(source_boundary >= prepare.DEFAULT_ALPHA_THRESHOLD):
        assert np.any(envelope_boundary)

    # Verify that the resulting mask can be converted
    # into a closed physical SVG contour.
    path_data = prepare._envelope_path_data(envelope)

    assert path_data
    assert path_data.strip().endswith("Z")


def test_prepare_bug06_shrink_wrap_produces_registered_svg(
    tmp_path: Path,
) -> None:
    """
    BUG-006: the real PNG must prepare successfully
    using shrink-wrap envelope construction.

    The output SVGs must retain source dimensions,
    contain registered artwork, and provide a closed
    physical envelope.
    """
    import xml.etree.ElementTree as ET

    source = Path(__file__).resolve().parents[2] / "assets" / "bug06.png"

    assert source.is_file()

    with Image.open(source) as image:
        assert image.format == "PNG"
        width, height = image.size

    trace = tmp_path / "trace.svg"
    envelope = tmp_path / "envelope.svg"

    context = StubContext(
        inputs={"source": source},
        outputs={
            "trace": trace,
            "envelope": envelope,
        },
        resolver=StubResolver(
            {
                "artwork_envelope_mode": "shrink-wrap",
                "artifact_color_count": 20,
            }
        ),
    )

    prepare.execute(context)  # type: ignore[arg-type]

    assert trace.is_file()
    assert envelope.is_file()

    namespace = "{http://www.w3.org/2000/svg}"
    expected_viewbox = f"0 0 {width} {height}"

    trace_root = ET.parse(trace).getroot()
    envelope_root = ET.parse(envelope).getroot()

    assert trace_root.get("viewBox") == expected_viewbox
    assert envelope_root.get("viewBox") == expected_viewbox

    artwork = trace_root.find(f"{namespace}g[@id='artwork']")

    assert artwork is not None

    artwork_paths = artwork.findall(f"{namespace}path")

    assert artwork_paths
    assert all(path.get("d") for path in artwork_paths)

    envelope_paths = envelope_root.findall(f"{namespace}path")

    assert len(envelope_paths) == 1

    envelope_data = envelope_paths[0].get("d")

    assert envelope_data is not None
    assert envelope_data.strip().endswith("Z")

    # Preparation must not rewrite the source.
    with Image.open(source) as image:
        assert image.format == "PNG"
        assert image.size == (width, height)


def test_discover_png_color_count_preserves_nydeli_authored_colors() -> None:
    """
    The New York Deli acceptance artwork contains three meaningful
    foreground colors: black, white, and red.

    Black is authored foreground geometry, not an exterior background.

    Transparent exterior pixels do not contribute an Artifact color.
    Antialiasing and incidental RGB variations around authored color
    boundaries must not create additional Artifact colors.

    This regression protects source-driven color discovery without
    introducing physical printer-color selection or quantization.
    """
    repository_root = Path(__file__).resolve().parents[3]
    source = repository_root / "tests" / "assets" / "nydeli-clean.png"

    assert source.is_file(), f"Missing acceptance artwork fixture: {source}"

    with Image.open(source) as image:
        rgba = image.convert("RGBA")

        try:
            pixels = np.asarray(rgba)

            assert pixels.ndim == 3
            assert pixels.shape[2] == 4

            alpha = pixels[:, :, 3]

            # The exterior is transparent rather than an opaque
            # black background.
            assert np.any(alpha == 0)

            # The image also contains visible authored artwork.
            assert np.any(alpha == 255)

            # Fully opaque black must remain meaningful foreground.
            opaque_black = (alpha == 255) & np.all(pixels[:, :, :3] == (0, 0, 0), axis=2)
            assert np.any(opaque_black)

            # Verify the other two principal authored colors exist
            # independently of the black foreground.
            opaque = alpha == 255
            rgb = pixels[:, :, :3]

            white = opaque & np.all(rgb >= (240, 240, 240), axis=2)
            assert np.any(white)

            red = opaque & (rgb[:, :, 0] >= 150) & (rgb[:, :, 1] <= 100) & (rgb[:, :, 2] <= 100)
            assert np.any(red)

            discovered = prepare._discover_png_color_count(rgba)

            assert discovered == 3, (
                "New York Deli artwork must resolve to three "
                "meaningful foreground colors (black, white, red), "
                f"not {discovered}. Incidental antialiasing must "
                "not introduce additional Artifact colors."
            )

        finally:
            rgba.close()


def test_discover_png_color_count_ignores_multicolor_antialiasing() -> None:
    """
    Discover three authored foreground colors despite RGB variations
    introduced by antialiasing at boundaries between color regions.

    Black, white, and red are all authored foreground colors.

    The source contains substantial opaque regions of each color.
    Boundary pixels contain intermediate RGB values, including
    transitions between black and white and between red and white.

    Those intermediate colors are not independently authored colors
    and must not increase the discovered Artifact color count.

    Transparent exterior pixels must not contribute a color.

    This test protects source-color discovery without requiring
    tracing, physical printer-color selection, or quantization.
    """
    image = Image.new(
        "RGBA",
        (128, 96),
        (0, 0, 0, 0),
    )

    try:
        pixels = image.load()

        assert pixels is not None

        # -------------------------------------------------
        # Three substantial authored foreground regions
        # -------------------------------------------------

        for y in range(16, 80):
            for x in range(12, 116):
                if x < 46:
                    pixels[x, y] = (0, 0, 0, 255)
                elif x < 82:
                    pixels[x, y] = (255, 255, 255, 255)
                else:
                    pixels[x, y] = (220, 0, 0, 255)

        # -------------------------------------------------
        # Black-to-white antialiased transition
        # -------------------------------------------------
        #
        # Replace a narrow interior boundary with
        # intermediate grayscale values. These pixels
        # are fully opaque because they represent color
        # blending between adjacent foreground regions.
        #
        # Their RGB distances from black and white are
        # intentionally larger than the existing discovery
        # tolerance of 24.
        #
        for y in range(16, 80):
            pixels[42, y] = (32, 32, 32, 255)
            pixels[43, y] = (64, 64, 64, 255)
            pixels[44, y] = (96, 96, 96, 255)
            pixels[45, y] = (128, 128, 128, 255)
            pixels[46, y] = (160, 160, 160, 255)
            pixels[47, y] = (192, 192, 192, 255)
            pixels[48, y] = (224, 224, 224, 255)

        # -------------------------------------------------
        # White-to-red antialiased transition
        # -------------------------------------------------
        #
        # These values interpolate between authored
        # white and red. They are transitional pixels,
        # not additional authored colors.
        #
        for y in range(16, 80):
            for offset, fraction in enumerate(
                (
                    0.125,
                    0.250,
                    0.375,
                    0.500,
                    0.625,
                    0.750,
                    0.875,
                )
            ):
                x = 78 + offset

                red = round(255 * (1.0 - fraction) + 220 * fraction)
                green = round(255 * (1.0 - fraction))
                blue = round(255 * (1.0 - fraction))

                pixels[x, y] = (
                    red,
                    green,
                    blue,
                    255,
                )

        # -------------------------------------------------
        # Verify test fixture assumptions
        # -------------------------------------------------

        rgba = np.asarray(
            image,
            dtype=np.uint8,
        )

        alpha = rgba[:, :, 3]
        rgb = rgba[:, :, :3]

        assert np.any(alpha == 0)
        assert np.any(alpha == 255)

        opaque = alpha == 255

        for authored_color in (
            (0, 0, 0),
            (255, 255, 255),
            (220, 0, 0),
        ):
            matching = opaque & np.all(
                rgb == authored_color,
                axis=2,
            )

            assert np.count_nonzero(matching) > 100

        # Confirm the image contains more than three
        # literal RGB values. Discovery must distinguish
        # authored colors from incidental transitions.
        unique_colors = np.unique(
            rgb[opaque],
            axis=0,
        )

        assert len(unique_colors) > 3

        # -------------------------------------------------
        # Source-color discovery contract
        # -------------------------------------------------

        discovered = prepare._discover_png_color_count(
            image,
        )

        assert discovered == 3, (
            "Antialiased boundaries between black, white, "
            "and red must not create additional Artifact "
            f"colors; discovered {discovered} instead of 3."
        )

    finally:
        image.close()


def test_prepare_warns_when_vector_tracing_reduces_source_colors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """
    Reducing discovered Artifact colors to a configured vector
    tracing maximum is a potentially lossy operation.

    Prepare must warn about the reduction while preserving the
    supported multicolor tracing workflow.
    """
    import logging

    source = tmp_path / "source.png"
    trace = tmp_path / "trace.svg"
    envelope = tmp_path / "envelope.svg"

    rgba = np.zeros((64, 64, 4), dtype=np.uint8)

    # Three substantial, distinctly colored authored regions.
    rgba[8:24, 8:56] = (255, 0, 0, 255)
    rgba[24:40, 8:56] = (0, 255, 0, 255)
    rgba[40:56, 8:56] = (0, 0, 255, 255)

    Image.fromarray(
        rgba,
        mode="RGBA",
    ).save(source)

    context = StubContext(
        inputs={
            "source": source,
        },
        outputs={
            "trace": trace,
            "envelope": envelope,
        },
        resolver=StubResolver(
            {
                "artwork_envelope_mode": "alpha",
                "artifact_color_count": 2,
            }
        ),
    )

    traced_counts: list[int] = []

    def trace_multicolor(
        source_path: Path,
        output_path: Path,
        *,
        colors: int,
    ) -> None:
        assert source_path.is_file()

        traced_counts.append(colors)

        output_path.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg"/>',
            encoding="utf-8",
        )

    monkeypatch.setattr(
        prepare,
        "_trace_multicolor",
        trace_multicolor,
    )

    monkeypatch.setattr(
        prepare,
        "_clip_trace_to_envelope",
        lambda trace_path, artwork_envelope: None,
    )

    with caplog.at_level(logging.INFO):
        prepare.execute(context)  # type: ignore[arg-type]

    # The existing supported reduction must still succeed.
    assert traced_counts == [2]
    assert trace.is_file()
    assert envelope.is_file()

    # A potentially lossy reduction must be visible as a warning.
    warnings = [
        record.getMessage().lower()
        for record in caplog.records
        if record.levelno == logging.WARNING
    ]

    assert any("reduc" in message and "3" in message and "2" in message for message in warnings)
