"""
Focused tests for Artwork palette preparation.

These tests exercise normalization, palette quantization, and cleanup
performed before the prepared raster is traced into vector Artwork.
"""
# File: tests/model/artwork/test_prepare_palette.py
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


ASSETS = Path(__file__).parents[2] / "assets"


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


# =========================================================
# Representative Artwork
# =========================================================


def test_prepare_palette_preserves_red_artwork_in_real_house() -> None:
    """
    Palette preparation preserves substantial red Artwork in the
    representative clean-background house fixture.

    The test exercises the complete raster preparation sequence used
    immediately before multicolor tracing.
    """

    image = _load_fixture(
        "clean_bg_house.png",
    )

    try:
        envelope = prepare._derive_envelope(
            image,
            mode="shrink-wrap",
        )

        #
        # Use representative semantic colors from the house rather
        # than testing arbitrary quantization colors.
        #
        palette = (
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
            palette=palette,
        )

        quantized = prepare._cleanup_quantized_image(
            quantized,
            envelope,
            palette=palette,
            radius=1,
            minimum_support=3,
        )

        quantized = prepare._cleanup_thin_features(
            quantized,
            envelope,
            palette=palette,
            maximum_radius=prepare.DEFAULT_THIN_FEATURE_PIXELS,
            replacement_radius=2,
        )

        rgba = np.asarray(
            quantized,
            dtype=np.uint8,
        )

        red = np.all(
            rgba[
                :,
                :,
                :3,
            ]
            == np.asarray(
                (
                    221,
                    55,
                    52,
                ),
                dtype=np.uint8,
            ),
            axis=2,
        ) & (
            rgba[
                :,
                :,
                3,
            ]
            == 255
        )

        #
        # Red is a substantial semantic component of this Artwork.
        # Raster preparation must not eliminate it before tracing.
        #
        assert np.any(
            red,
        )

        assert (
            np.count_nonzero(
                red,
            )
            > 100
        )

    finally:
        image.close()


@pytest.mark.parametrize(
    (
        "color_name",
        "rgb",
    ),
    [
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
    ],
)
def test_prepare_palette_preserves_substantial_real_house_artwork(
    color_name: str,
    rgb: tuple[int, int, int],
) -> None:
    """
    Palette preparation preserves substantial semantic color regions
    in representative clean-background house Artwork.
    """

    image = _load_fixture(
        "clean_bg_house.png",
    )

    try:
        envelope = prepare._derive_envelope(
            image,
            mode="shrink-wrap",
        )

        palette = (
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
            palette=palette,
        )

        quantized = prepare._cleanup_quantized_image(
            quantized,
            envelope,
            palette=palette,
            radius=1,
            minimum_support=3,
        )

        quantized = prepare._cleanup_thin_features(
            quantized,
            envelope,
            palette=palette,
            maximum_radius=prepare.DEFAULT_THIN_FEATURE_PIXELS,
            replacement_radius=2,
        )

        rgba = np.asarray(
            quantized,
            dtype=np.uint8,
        )

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
            f"Expected substantial {color_name} Artwork "
            f"after palette preparation, found {count} pixels."
        )

    finally:
        image.close()
