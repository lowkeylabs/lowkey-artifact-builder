"""
Focused tests for Artwork prepare-stage multicolor tracing.

These tests establish that source color information preserved during
Artwork preparation is represented by geometry after Inkscape
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

ARTIFACT_COLOR_COUNT = 4


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
    Prepare one source image through the raster processing used
    immediately before multicolor tracing.

    Preparation derives the physical Artwork envelope and preserves
    source RGBA information inside that envelope. Physical printer-color
    selection and assignment are not Prepare responsibilities.
    """

    envelope = prepare._derive_envelope(
        image,
        mode="shrink-wrap",
    )

    prepared = prepare._prepare_source_image(
        image,
        envelope,
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
def test_multicolor_trace_produces_requested_house_color_layers(
    tmp_path: Path,
) -> None:
    """
    Inkscape multicolor tracing produces the requested number of color
    layers from prepared clean-background house Artwork.

    Prepare preserves source color information rather than first
    quantizing the source to a configured physical printer palette.
    Inkscape therefore determines representative Artifact colors from
    the prepared source raster.
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
        # Exercise the real prepare-stage Inkscape operation. The
        # requested count describes Artifact colors, not a physical
        # printer palette.
        #
        prepare._trace_multicolor(
            raster,
            trace,
            colors=ARTIFACT_COLOR_COUNT,
        )

        assert trace.is_file()

        fills = _svg_fill_colors(
            trace,
        )

        #
        # Inkscape chooses the representative RGB value for each traced
        # Artifact color layer. At this boundary the required invariant
        # is that the requested number of distinct color layers survives
        # into vector geometry.
        #
        assert (
            len(
                fills,
            )
            == ARTIFACT_COLOR_COUNT
        ), f"Expected the requested number of traced Artifact color layers; found {sorted(fills)}."

    finally:
        if prepared is not None:
            prepared.close()

        image.close()


@pytest.mark.slow
def test_envelope_clipping_preserves_traced_house_color_layers(
    tmp_path: Path,
) -> None:
    """
    Clipping traced house Artwork to its physical envelope preserves
    every vector color layer produced by multicolor tracing.

    The Artwork envelope constrains vector geometry spatially. It must
    not eliminate an Artifact color layer that survived source
    preparation and tracing.
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
        # Produce the real multicolor trace from preserved source color
        # information.
        #
        prepare._trace_multicolor(
            raster,
            trace,
            colors=ARTIFACT_COLOR_COUNT,
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
        assert (
            len(
                fills_before,
            )
            == ARTIFACT_COLOR_COUNT
        ), (
            "Expected the requested number of traced Artifact color "
            f"layers; found {sorted(fills_before)}."
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
        # Clipping changes spatial visibility, not Artifact color
        # identity. Every traced color layer must remain represented.
        #
        assert fills_after == fills_before, (
            "Envelope clipping changed the traced Artifact color layers; "
            f"before={sorted(fills_before)}, "
            f"after={sorted(fills_after)}."
        )

    finally:
        if prepared is not None:
            prepared.close()

        image.close()
