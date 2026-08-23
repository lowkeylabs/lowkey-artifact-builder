"""
Tests for the artwork prepare stage.

These tests characterize the storage boundary between the build engine
and the prepare-stage implementation.

The prepare stage must consume only the paths supplied through
StageContext. Its persistent products must be written exactly to the
declared trace and envelope output paths.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

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

        self._colors = {
            "white": {
                "rgb": [
                    255,
                    255,
                    255,
                ],
            },
            "black": {
                "rgb": [
                    0,
                    0,
                    0,
                ],
            },
        }

    def __call__(
        self,
        name: str,
    ) -> Any:
        return self._values[name]

    def color(
        self,
        name: str,
    ) -> Any:
        return self._colors[name]


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


def _resolver() -> StubResolver:
    """
    Return standard prepare-stage configuration.
    """

    return StubResolver(
        {
            "artwork_colors": [
                "white",
                "black",
            ],
        }
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
