"""
Tests for the artwork prepare stage.

These tests characterize the storage boundary between the build engine
and the prepare-stage implementation and the application of configured
Artwork fill semantics.

The prepare stage must consume only the paths supplied through
StageContext. Its persistent products must be written exactly to the
declared trace and envelope output paths.

Otherwise-unassigned pixels inside the Artwork envelope use the
configured artwork_fill_color before color separation.
"""
# File: tests/model/test_prepare.py
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
            "red": {
                "rgb": [
                    255,
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


def _resolver(
    *,
    colors: list[str] | None = None,
    fill_color: str = "white",
    envelope_mode: str | None = None,
) -> StubResolver:
    """
    Return standard prepare-stage configuration.
    """

    values: dict[str, Any] = {
        "artwork_colors": (
            colors
            if colors is not None
            else [
                "white",
                "black",
            ]
        ),
        "artwork_fill_color": fill_color,
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


def _write_source_with_unassigned_interior(
    path: Path,
) -> None:
    """
    Write source artwork containing transparent pixels inside its envelope.
    """

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    image = Image.new(
        "RGBA",
        (40, 40),
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

        for y in range(8, 32):
            for x in range(8, 32):
                pixels[x, y] = (
                    0,
                    0,
                    0,
                    255,
                )

        for y in range(16, 24):
            for x in range(16, 24):
                pixels[x, y] = (
                    0,
                    0,
                    0,
                    0,
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
# Artwork fill semantics
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


def test_prepare_normalization_supports_non_white_fill_color() -> None:
    """
    Image normalization can assign a non-white fill color to
    transparent pixels inside the Artwork envelope.
    """

    image = Image.new(
        "RGBA",
        (
            3,
            3,
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

        pixels[1, 1] = (
            0,
            0,
            0,
            255,
        )

        envelope = np.ones(
            (
                3,
                3,
            ),
            dtype=bool,
        )

        normalized = prepare._normalize_image(
            image,
            envelope,
            fill_color=(
                255,
                0,
                0,
            ),
        )

        try:
            normalized_pixels = normalized.load()

            assert normalized_pixels is not None

            assert normalized_pixels[0, 0] == (
                255,
                0,
                0,
                255,
            )

            assert normalized_pixels[1, 1] == (
                0,
                0,
                0,
                255,
            )

        finally:
            normalized.close()

    finally:
        image.close()


def test_prepare_applies_configured_non_white_fill_color(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Prepare assigns otherwise-unassigned envelope pixels the configured
    non-white Artwork fill color.
    """

    source = tmp_path / "source.png"

    _write_source_with_unassigned_interior(
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
            colors=[
                "red",
                "black",
            ],
            fill_color="red",
        ),
    )

    captured: list[Image.Image] = []

    monkeypatch.setattr(
        prepare,
        "_trace_multicolor",
        _capture_traced_image(
            captured,
        ),
    )

    monkeypatch.setattr(
        prepare,
        "_clip_trace_to_envelope",
        lambda trace_path, artwork_envelope: None,
    )

    prepare.execute(context)  # type: ignore[arg-type]

    assert len(captured) == 1

    try:
        pixels = captured[0].load()

        assert pixels is not None

        assert pixels[20, 20] == (
            255,
            0,
            0,
            255,
        )

    finally:
        captured[0].close()


def test_prepare_does_not_require_white_when_fill_color_is_configured(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Prepare succeeds with a palette containing no white when the
    configured fill color belongs to that palette.
    """

    source = tmp_path / "source.png"

    _write_source_with_unassigned_interior(
        source,
    )

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
        resolver=_resolver(
            colors=[
                "red",
                "black",
            ],
            fill_color="red",
        ),
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

    assert trace.is_file()
    assert envelope.is_file()


@pytest.mark.slow
def test_shrink_wrap_real_opaque_artwork_does_not_use_source_rectangle() -> None:
    """
    Shrink-wrap derives a meaningful envelope for representative opaque
    artwork instead of treating the complete source rectangle as Artwork.
    """

    source = Path(__file__).parent / "fixtures" / "clean_bg_cat.png"

    assert source.is_file()

    with Image.open(source) as image:
        rgba = image.convert(
            "RGBA",
        )

    envelope = prepare._derive_envelope(
        rgba,
        mode="shrink-wrap",
    )

    assert np.any(envelope)

    height, width = envelope.shape

    # Representative opaque-background artwork must not collapse to the
    # historical alpha-mode failure of treating the complete raster as
    # Artwork.
    assert not np.all(envelope)

    # The shrink-wrapped subject should have exterior background on every
    # side rather than coinciding with the source-image rectangle.
    assert not np.any(envelope[0, :])
    assert not np.any(envelope[height - 1, :])
    assert not np.any(envelope[:, 0])
    assert not np.any(envelope[:, width - 1])

    occupied_y, occupied_x = np.nonzero(
        envelope,
    )

    assert occupied_x.min() > 0
    assert occupied_y.min() > 0
    assert occupied_x.max() < width - 1
    assert occupied_y.max() < height - 1


def test_shrink_wrap_treats_near_background_colors_as_exterior() -> None:
    """
    Shrink-wrap recognizes a visually uniform exterior background even
    when its raster pixels contain small RGB variations.
    """

    image = Image.new(
        "RGBA",
        (60, 60),
        (250, 250, 250, 255),
    )

    pixels = image.load()
    assert pixels is not None

    # Introduce small deterministic variation throughout the exterior
    # background, as occurs in real raster artwork.
    for y in range(60):
        for x in range(60):
            variation = (x + y) % 6

            value = 250 + variation

            pixels[x, y] = (
                value,
                value,
                value,
                255,
            )

    # A clearly distinct subject occupies the center.
    for y in range(18, 42):
        for x in range(18, 42):
            pixels[x, y] = (
                30,
                30,
                30,
                255,
            )

    envelope = prepare._derive_envelope(
        image,
        mode="shrink-wrap",
    )

    # Exterior background must be excluded.
    assert not envelope[10, 10]
    assert not envelope[10, 30]
    assert not envelope[30, 10]
    assert not envelope[50, 50]

    # The subject must remain Artwork.
    assert envelope[30, 30]
