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

from pathlib import Path
from typing import Any, cast

import pytest
from PIL import Image

from lowkey_artifact_builder.engine import StageContext
from lowkey_artifact_builder.model.models.artwork.stages import prepare

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
            "artifact_color_count": 3,
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
        3,
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
