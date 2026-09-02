"""
Focused tests for Artwork prepare-stage multicolor tracing.

These tests establish that substantial semantic color regions surviving
raster preparation are also represented by geometry after Inkscape
multicolor tracing.
"""
# File: tests/model/artwork/test_prepare_trace.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from lowkey_artifact_builder.model.models.artwork.stages import prepare

# =========================================================
# Test support
# =========================================================


ASSETS = Path(__file__).parents[2] / "assets"

PALETTE = (
    (
        "red",
        (
            221,
            55,
            52,
        ),
    ),
    (
        "green",
        (
            87,
            121,
            79,
        ),
    ),
    (
        "gold",
        (
            214,
            164,
            76,
        ),
    ),
    (
        "white",
        (
            255,
            255,
            255,
        ),
    ),
)


def _load_fixture(
    name: str,
) -> Image.Image:
    """
    Load one representative Artwork fixture as RGBA.
    """

    source = ASSETS / name

    assert source.is_file()

    with Image.open(source) as image:
        return image.convert(
            "RGBA",
        )


def _prepare_raster(
    image: Image.Image,
) -> tuple[Image.Image, np.ndarray]:
    """
    Prepare one source image through the complete raster pipeline used
    immediately before multicolor tracing.
    """

    envelope = prepare._derive_envelope(
        image,
        mode="shrink-wrap",
    )

    normalized = prepare._normalize_image(
        image,
        envelope,
        fill_color=(
            255,
            255,
            255,
        ),
    )

    quantized = prepare._quantize_image(
        normalized,
        envelope,
        palette=PALETTE,
    )

    quantized = prepare._cleanup_quantized_image(
        quantized,
        envelope,
        palette=PALETTE,
        radius=1,
        minimum_support=3,
    )

    prepared = prepare._cleanup_thin_features(
        quantized,
        envelope,
        palette=PALETTE,
        maximum_radius=prepare.DEFAULT_THIN_FEATURE_PIXELS,
        replacement_radius=2,
    )

    return (
        prepared,
        envelope,
    )


def _svg_fill_colors(
    source: Path,
) -> set[str]:
    """
    Return explicit hexadecimal fill colors represented in an SVG.

    Fill colors may be expressed either directly on an element or
    through an element's style attribute.
    """

    tree = ET.parse(
        source,
    )

    colors: set[str] = set()

    for element in tree.iter():
        fill = element.get(
            "fill",
        )

        if fill is not None and fill.startswith("#"):
            colors.add(
                fill.lower(),
            )

        style = element.get(
            "style",
        )

        if style is None:
            continue

        for declaration in style.split(";"):
            name, separator, value = declaration.partition(":")

            if separator and name.strip() == "fill" and value.strip().startswith("#"):
                colors.add(
                    value.strip().lower(),
                )

    return colors


# =========================================================
# Multicolor tracing
# =========================================================


@pytest.mark.slow
def test_multicolor_trace_preserves_prepared_house_palette(
    tmp_path: Path,
) -> None:
    """
    Inkscape multicolor tracing preserves the semantic color layers
    represented by prepared clean-background house Artwork.

    Inkscape may choose representative SVG fill values that differ from
    the exact raster palette RGB values. The required invariant at this
    boundary is that every substantial prepared palette layer survives
    as a distinct vector color layer.
    """

    image = _load_fixture(
        "clean_bg_house.png",
    )

    prepared: Image.Image | None = None

    try:
        prepared, _envelope = _prepare_raster(
            image,
        )

        raster = tmp_path / "prepared.png"

        trace = tmp_path / "trace.svg"

        prepared.save(
            raster,
            format="PNG",
        )

        #
        # Establish the precondition independently of Inkscape: every
        # configured palette color is substantially represented in the
        # raster supplied to the tracer.
        #
        rgba = np.asarray(
            prepared,
            dtype=np.uint8,
        )

        for color_name, rgb in PALETTE:
            matches = np.all(
                rgba[:, :, :3]
                == np.asarray(
                    rgb,
                    dtype=np.uint8,
                ),
                axis=2,
            ) & (rgba[:, :, 3] == 255)

            count = int(
                np.count_nonzero(
                    matches,
                )
            )

            assert count > 100, (
                f"Expected substantial {color_name} Artwork before tracing, found {count} pixels."
            )

        #
        # Exercise the real prepare-stage Inkscape operation.
        #
        prepare._trace_multicolor(
            raster,
            trace,
            colors=len(PALETTE),
        )

        assert trace.is_file()

        fills = _svg_fill_colors(
            trace,
        )

        #
        # Inkscape's multicolor tracer may choose representative SVG
        # fill values that differ slightly from the exact raster palette.
        #
        # At this boundary the required invariant is that every
        # substantial prepared palette layer survives as a distinct
        # vector color layer.
        #
        assert len(
            fills,
        ) == len(
            PALETTE,
        ), (
            "Expected one traced vector color layer for every "
            f"prepared palette color; found {sorted(fills)}."
        )

    finally:
        if prepared is not None:
            prepared.close()

        image.close()


@pytest.mark.slow
def test_envelope_clipping_preserves_traced_house_palette_layers(
    tmp_path: Path,
) -> None:
    """
    Clipping traced house Artwork to its physical envelope preserves
    every vector color layer produced by multicolor tracing.

    The Artwork envelope constrains vector geometry spatially. It must
    not eliminate a semantic color layer that survived preparation and
    tracing.
    """

    image = _load_fixture(
        "clean_bg_house.png",
    )

    prepared: Image.Image | None = None

    try:
        prepared, envelope = _prepare_raster(
            image,
        )

        raster = tmp_path / "prepared.png"
        trace = tmp_path / "trace.svg"

        prepared.save(
            raster,
            format="PNG",
        )

        #
        # Produce the real multicolor trace.
        #
        prepare._trace_multicolor(
            raster,
            trace,
            colors=len(PALETTE),
        )

        assert trace.is_file()

        fills_before = _svg_fill_colors(
            trace,
        )

        #
        # Establish the tracing precondition. The preceding test covers
        # this behavior independently; repeating it here makes any
        # clipping failure unambiguous.
        #
        assert len(
            fills_before,
        ) == len(
            PALETTE,
        ), (
            "Expected one traced vector color layer for every "
            f"prepared palette color; found {sorted(fills_before)}."
        )

        #
        # Apply the real prepare-stage envelope clipping operation.
        #
        prepare._clip_trace_to_envelope(
            trace,
            envelope,
        )

        fills_after = _svg_fill_colors(
            trace,
        )

        #
        # Clipping changes spatial visibility, not semantic color
        # identity. Every traced color layer must remain represented.
        #
        assert fills_after == fills_before, (
            "Envelope clipping changed the traced palette layers; "
            f"before={sorted(fills_before)}, "
            f"after={sorted(fills_after)}."
        )

    finally:
        if prepared is not None:
            prepared.close()

        image.close()
