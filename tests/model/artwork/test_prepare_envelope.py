"""
Focused tests for Artwork envelope derivation.

These tests exercise representative source artwork and envelope semantics
without involving downstream raster, vector, extrusion, or packaging
stages.
"""
# File: tests/model/artwork/test_prepare_envelope.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from lowkey_artifact_builder.model.models.artwork.stages import prepare


# =========================================================
# Test support
# =========================================================


FIXTURES = Path(__file__).parent / "fixtures"


def _load_fixture(
    name: str,
) -> Image.Image:
    """
    Load one representative Artwork fixture as RGBA.
    """

    source = FIXTURES / name

    assert source.is_file()

    with Image.open(source) as image:
        return image.convert(
            "RGBA",
        )


# =========================================================
# Shrink-wrap semantics
# =========================================================


def test_shrink_wrap_excludes_transparent_exterior_background() -> None:
    """
    Transparent source background connected to the exterior lies outside
    the Artwork envelope.
    """

    image = Image.new(
        "RGBA",
        (80, 80),
        (255, 255, 255, 0),
    )

    try:
        pixels = image.load()

        assert pixels is not None

        for y in range(20, 60):
            for x in range(20, 60):
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
        assert not envelope[0, 79]
        assert not envelope[79, 0]
        assert not envelope[79, 79]

        assert envelope[40, 40]

    finally:
        image.close()


def test_shrink_wrap_excludes_translucent_exterior_background() -> None:
    """
    Translucent source background connected to the exterior lies outside
    the Artwork envelope.
    """

    image = Image.new(
        "RGBA",
        (80, 80),
        (255, 255, 255, 96),
    )

    try:
        pixels = image.load()

        assert pixels is not None

        for y in range(20, 60):
            for x in range(20, 60):
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
        assert not envelope[0, 79]
        assert not envelope[79, 0]
        assert not envelope[79, 79]

        assert envelope[40, 40]

    finally:
        image.close()


def test_shrink_wrap_preserves_enclosed_transparent_region() -> None:
    """
    Transparency alone does not make a source region exterior.

    A transparent region enclosed by Artwork remains inside the Artwork
    envelope.
    """

    image = Image.new(
        "RGBA",
        (80, 80),
        (255, 255, 255, 0),
    )

    try:
        pixels = image.load()

        assert pixels is not None

        for y in range(15, 65):
            for x in range(15, 65):
                pixels[x, y] = (
                    0,
                    0,
                    0,
                    255,
                )

        for y in range(30, 50):
            for x in range(30, 50):
                pixels[x, y] = (
                    255,
                    255,
                    255,
                    0,
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


# =========================================================
# Representative Artwork
# =========================================================


@pytest.mark.slow
@pytest.mark.parametrize(
    "fixture_name",
    [
        "busy_bg_person.png",
        "clean_bg_cat.png",
        "clean_bg_dog.png",
        "clean_bg_house.png",
        "clean_bg_person.png",
    ],
)
def test_shrink_wrap_real_artwork_does_not_use_source_rectangle(
    fixture_name: str,
) -> None:
    """
    Shrink-wrap derives a bounded envelope for representative real
    Artwork rather than treating the complete source raster as Artwork.

    This is a processability test rather than a claim that shrink-wrap
    performs arbitrary photographic subject extraction.
    """

    image = _load_fixture(
        fixture_name,
    )

    try:
        envelope = prepare._derive_envelope(
            image,
            mode="shrink-wrap",
        )

        assert np.any(
            envelope,
        )

        height, width = envelope.shape

        assert not np.all(
            envelope,
        )

        assert not np.any(
            envelope[0, :],
        )

        assert not np.any(
            envelope[height - 1, :],
        )

        assert not np.any(
            envelope[:, 0],
        )

        assert not np.any(
            envelope[:, width - 1],
        )

        occupied_y, occupied_x = np.nonzero(
            envelope,
        )

        assert occupied_x.min() > 0
        assert occupied_y.min() > 0
        assert occupied_x.max() < width - 1
        assert occupied_y.max() < height - 1

    finally:
        image.close()
    