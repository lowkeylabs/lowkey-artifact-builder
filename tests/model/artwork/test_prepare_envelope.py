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

import logging
from pathlib import Path

import numpy as np
import pytest
from PIL import Image
from scipy import ndimage

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


def test_shrink_wrap_preserves_enclosed_color_matching_transparent_exterior() -> None:
    """
    An enclosed Artwork region is not excluded solely because its RGB
    matches the transparent exterior background.

    Shrink-wrap classifies exterior background by region membership,
    rather than treating every occurrence of the exterior RGB as
    background.
    """

    image = Image.new(
        "RGBA",
        (100, 100),
        (255, 255, 255, 0),
    )

    try:
        pixels = image.load()

        assert pixels is not None

        #
        # Create one solid Artwork domain.
        #
        for y in range(20, 80):
            for x in range(20, 80):
                pixels[x, y] = (
                    0,
                    0,
                    0,
                    255,
                )

        #
        # Put a legitimate opaque white region inside the Artwork.
        #
        # Its RGB is identical to the transparent exterior background,
        # but it belongs to the enclosed Artwork domain.
        #
        for y in range(40, 60):
            for x in range(40, 60):
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
        # Exterior background remains outside the Artwork.
        #
        assert not envelope[
            0,
            0,
        ]

        #
        # Ordinary Artwork remains inside.
        #
        assert envelope[
            30,
            30,
        ]

        #
        # Most importantly, the enclosed white region remains inside
        # even though its RGB matches the exterior background.
        #
        assert envelope[
            50,
            50,
        ]

    finally:
        image.close()


def test_shrink_wrap_preserves_known_artwork_region_in_real_house() -> None:
    """
    Shrink-wrap preserves a known Artwork region in representative
    clean-background house Artwork.

    The sampled point lies within the green house facade. Green is
    semantic Artwork in this fixture and therefore belongs inside the
    Artwork envelope.
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
        # This point lies well inside the green house facade rather
        # than on an antialiased edge or exterior background.
        #
        assert envelope[
            255,
            448,
        ]

    finally:
        image.close()


def test_shrink_wrap_preserves_non_white_artwork_at_exterior_boundary() -> None:
    """
    Shrink-wrap includes non-white Artwork up to its exterior boundary.

    White exterior background is excluded, while non-white pixels
    adjacent to that background remain part of the Artwork envelope.
    """

    image = Image.new(
        "RGBA",
        (100, 100),
        (255, 255, 255, 255),
    )

    try:
        pixels = image.load()

        assert pixels is not None

        #
        # Create a red Artwork region surrounded directly by the
        # white exterior background.
        #
        for y in range(30, 70):
            for x in range(30, 70):
                pixels[x, y] = (
                    220,
                    40,
                    40,
                    255,
                )

        envelope = prepare._derive_envelope(
            image,
            mode="shrink-wrap",
        )

        #
        # Exterior white background is not Artwork.
        #
        assert not envelope[
            50,
            29,
        ]

        #
        # The immediately adjacent red pixel is Artwork.
        #
        assert envelope[
            50,
            30,
        ]

    finally:
        image.close()


def test_shrink_wrap_follows_red_artwork_boundary_in_real_house() -> None:
    """
    Shrink-wrap includes red Artwork at the exterior boundary of
    representative clean-background house Artwork.

    The white or near-white region immediately outside that Artwork is
    excluded from the envelope.
    """

    image = _load_fixture(
        "clean_bg_house.png",
    )

    try:
        envelope = prepare._derive_envelope(
            image,
            mode="shrink-wrap",
        )

        rgba = np.asarray(
            image,
            dtype=np.uint8,
        )

        #
        # Find red Artwork pixels in the lower portion of the image,
        # where the flower bed and brickwork reach the exterior edge
        # of the composition.
        #
        red = (
            (rgba[:, :, 0] >= 160)
            & (rgba[:, :, 1] <= 100)
            & (rgba[:, :, 2] <= 100)
            & (rgba[:, :, 3] >= prepare.DEFAULT_ALPHA_THRESHOLD)
        )

        height = red.shape[0]

        red[
            : height // 2,
            :,
        ] = False

        #
        # Every meaningful red source pixel is Artwork and therefore
        # must lie inside the shrink-wrapped envelope.
        #
        assert np.any(
            red,
        )

        assert np.all(
            envelope[red],
        )

    finally:
        image.close()


def test_shrink_wrap_excludes_substantial_exterior_white_background_in_real_house() -> None:
    """
    Shrink-wrap excludes substantial exterior white background surrounding
    the representative clean-background house Artwork.

    The source is circularly cropped. Transparent pixels outside the crop
    connect to white/near-white background inside the crop. Most of that
    connected white background must remain outside the Artwork envelope.

    Shrink-wrap may incorporate limited exterior-connected white regions
    when doing so repairs a narrow, disproportionately deep concavity.
    """

    image = _load_fixture(
        "clean_bg_house.png",
    )

    try:
        envelope = prepare._derive_envelope(
            image,
            mode="shrink-wrap",
        )

        rgba = np.asarray(
            image,
            dtype=np.uint8,
        )

        transparent = rgba[:, :, 3] < prepare.DEFAULT_ALPHA_THRESHOLD

        white = (
            (rgba[:, :, 0] >= prepare.DEFAULT_SHRINK_WRAP_WHITE_MINIMUM)
            & (rgba[:, :, 1] >= prepare.DEFAULT_SHRINK_WRAP_WHITE_MINIMUM)
            & (rgba[:, :, 2] >= prepare.DEFAULT_SHRINK_WRAP_WHITE_MINIMUM)
            & (rgba[:, :, 3] >= prepare.DEFAULT_ALPHA_THRESHOLD)
        )

        background_candidate = transparent | white

        assert np.any(
            transparent,
        )

        assert np.any(
            white,
        )

        boundary_seed = np.zeros_like(
            background_candidate,
            dtype=bool,
        )

        boundary_seed[0, :] = background_candidate[0, :]
        boundary_seed[-1, :] = background_candidate[-1, :]
        boundary_seed[:, 0] = background_candidate[:, 0]
        boundary_seed[:, -1] = background_candidate[:, -1]

        exterior_background = np.asarray(
            ndimage.binary_propagation(
                boundary_seed,
                mask=background_candidate,
            ),
            dtype=bool,
        )

        exterior_white = exterior_background & white

        assert np.any(
            exterior_white,
        ), (
            "Expected exterior background connectivity to reach "
            "white background inside the circular crop."
        )

        excluded_exterior_white = exterior_white & ~envelope

        assert np.any(
            excluded_exterior_white,
        ), (
            "Shrink-wrap failed to exclude exterior-connected white "
            "background surrounding the Artwork."
        )

        excluded_fraction = np.count_nonzero(
            excluded_exterior_white,
        ) / np.count_nonzero(
            exterior_white,
        )

        assert excluded_fraction >= 0.90, (
            "Shrink-wrap incorporated too much exterior-connected white "
            "background into the Artwork envelope: "
            f"{excluded_fraction:.1%} remained excluded."
        )

    finally:
        image.close()


def test_shrink_wrap_crosses_transparent_crop_into_white_exterior_background() -> None:
    """
    Shrink-wrap treats transparent exterior and connected white background
    as one exterior background domain.

    A transparent crop boundary must not prevent connected white background
    inside the crop from being excluded from the Artwork envelope.
    """

    image = Image.new(
        "RGBA",
        (100, 100),
        (255, 255, 255, 0),
    )

    try:
        pixels = image.load()

        assert pixels is not None

        #
        # Simulate an opaque white crop surrounded by transparency.
        #
        for y in range(10, 90):
            for x in range(10, 90):
                pixels[x, y] = (
                    255,
                    255,
                    255,
                    255,
                )

        #
        # Place non-white Artwork inside the white crop.
        #
        for y in range(30, 70):
            for x in range(30, 70):
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

        #
        # Transparent rectangular exterior remains outside.
        #
        assert not envelope[
            0,
            0,
        ]

        #
        # White background inside the transparent crop boundary is still
        # exterior background.
        #
        assert not envelope[
            20,
            20,
        ]

        #
        # Non-white Artwork remains inside the envelope.
        #
        assert envelope[
            50,
            50,
        ]

    finally:
        image.close()


def test_real_house_shrink_wrap_preserves_exterior_classification_during_envelope_build() -> None:
    """
    Envelope construction does not reintroduce exterior background
    identified by shrink-wrap classification.

    Shrink-wrap distinguishes foreground from known exterior background.
    Subsequent envelope morphology may fill ordinary enclosed holes, but
    must preserve the exclusion of known exterior background.
    """

    image = _load_fixture(
        "clean_bg_house.png",
    )

    try:
        foreground, exterior = prepare._shrink_wrap_foreground_mask(
            image,
        )

        assert np.any(
            foreground,
        )

        assert np.any(
            exterior,
        )

        #
        # Classification establishes disjoint foreground and exterior
        # domains.
        #
        assert not np.any(foreground & exterior)

        envelope = prepare._build_envelope(
            foreground,
            excluded=exterior,
        )

        #
        # Envelope morphology must not reintroduce anything already
        # classified as exterior background.
        #
        assert not np.any(envelope & exterior)

    finally:
        image.close()


def test_envelope_build_fills_enclosed_foreground_hole() -> None:
    """
    Envelope construction fills a region completely enclosed by foreground.

    The envelope describes the outer occupied Artwork region rather than
    preserving internal holes in the foreground mask.
    """

    foreground = np.zeros(
        (
            100,
            100,
        ),
        dtype=bool,
    )

    foreground[
        20:80,
        20:80,
    ] = True

    foreground[
        40:60,
        40:60,
    ] = False

    envelope = prepare._build_envelope(
        foreground,
    )

    assert envelope[
        30,
        30,
    ]

    assert envelope[
        50,
        50,
    ]

    assert not envelope[
        10,
        10,
    ]


def test_shrink_wrap_bridges_narrow_deep_exterior_concavity() -> None:
    """
    Shrink-wrap rejects a narrow exterior intrusion that would create
    a disproportionately deep concavity in the Artwork envelope.

    A small opening in an otherwise substantial Artwork boundary must
    not allow exterior background to penetrate deeply into the physical
    envelope.
    """

    image = Image.new(
        "RGBA",
        (200, 200),
        (255, 255, 255, 255),
    )

    try:
        pixels = image.load()

        assert pixels is not None

        #
        # Create one large solid Artwork region surrounded by white
        # exterior background.
        #
        for y in range(30, 170):
            for x in range(30, 170):
                pixels[x, y] = (
                    0,
                    0,
                    0,
                    255,
                )

        #
        # Cut a narrow exterior-connected channel deeply into the
        # Artwork from the right.
        #
        # The opening is only four pixels high but penetrates 100 pixels
        # into an otherwise substantial Artwork domain.
        #
        for y in range(98, 102):
            for x in range(70, 170):
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
        # Ordinary exterior background remains outside.
        #
        assert not envelope[
            100,
            180,
        ]

        #
        # Artwork on both sides of the narrow intrusion remains inside.
        #
        assert envelope[
            90,
            120,
        ]

        assert envelope[
            110,
            120,
        ]

        #
        # The narrow entrance must not create a deep concavity in the
        # physical envelope.
        #
        assert envelope[
            100,
            80,
        ]

    finally:
        image.close()


def test_shrink_wrap_preserves_broad_shallow_exterior_concavity() -> None:
    """
    Shrink-wrap preserves a broad, shallow concavity in the Artwork
    boundary.

    Exterior-connected background is legitimate envelope geometry when
    its opening is broad relative to its penetration depth.
    """

    image = Image.new(
        "RGBA",
        (200, 200),
        (255, 255, 255, 255),
    )

    try:
        pixels = image.load()

        assert pixels is not None

        #
        # Create one large solid Artwork region surrounded by white
        # exterior background.
        #
        for y in range(30, 170):
            for x in range(30, 170):
                pixels[x, y] = (
                    0,
                    0,
                    0,
                    255,
                )

        #
        # Cut a broad but shallow concavity into the right side.
        #
        # The opening is 60 pixels high while penetrating only
        # 20 pixels into the Artwork.
        #
        for y in range(70, 130):
            for x in range(150, 170):
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
        # Ordinary exterior remains outside.
        #
        assert not envelope[
            100,
            180,
        ]

        #
        # Artwork surrounding the concavity remains inside.
        #
        assert envelope[
            60,
            155,
        ]

        assert envelope[
            140,
            155,
        ]

        #
        # The broad, shallow concavity is legitimate exterior geometry
        # and must remain outside the envelope.
        #
        assert not envelope[
            100,
            155,
        ]

        #
        # Artwork immediately beyond the depth of the concavity remains
        # inside.
        #
        assert envelope[
            100,
            145,
        ]

    finally:
        image.close()


def test_shrink_wrap_preserves_narrow_shallow_exterior_concavity() -> None:
    """
    Shrink-wrap preserves a narrow, shallow exterior concavity.

    A narrow opening alone is not sufficient reason to bridge exterior
    background. Narrow concavities remain legitimate when they penetrate
    only a short distance into the Artwork envelope.
    """

    image = Image.new(
        "RGBA",
        (200, 200),
        (255, 255, 255, 255),
    )

    try:
        pixels = image.load()

        assert pixels is not None

        #
        # Large solid Artwork region surrounded by white exterior.
        #
        for y in range(30, 170):
            for x in range(30, 170):
                pixels[x, y] = (
                    0,
                    0,
                    0,
                    255,
                )

        #
        # Narrow but shallow exterior-connected crevice.
        #
        # Its width matches the narrow/deep regression, but it penetrates
        # only a short distance into the Artwork.
        #
        for y in range(98, 102):
            for x in range(155, 170):
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
        # Ordinary exterior remains outside.
        #
        assert not envelope[
            100,
            180,
        ]

        #
        # Artwork surrounding the crevice remains inside.
        #
        assert envelope[
            90,
            160,
        ]

        assert envelope[
            110,
            160,
        ]

        #
        # The narrow opening is legitimate because its penetration is
        # shallow. Shrink-wrap must therefore preserve the crevice.
        #
        assert not envelope[
            100,
            160,
        ]

        #
        # Artwork immediately beyond the end of the crevice remains inside.
        #
        assert envelope[
            100,
            150,
        ]

    finally:
        image.close()


def test_shrink_wrap_warns_for_complex_opaque_exterior(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """
    Shrink-wrap warns when an opaque exterior is too complex for reliable
    background inference.
    """

    image = Image.new(
        "RGBA",
        (120, 120),
        (255, 255, 255, 255),
    )

    try:
        pixels = image.load()

        assert pixels is not None

        checker_size = 10

        for y in range(120):
            for x in range(120):
                if ((x // checker_size) + (y // checker_size)) % 2 == 0:
                    pixels[x, y] = (
                        255,
                        255,
                        255,
                        255,
                    )
                else:
                    pixels[x, y] = (
                        225,
                        225,
                        225,
                        255,
                    )

        for y in range(30, 90):
            for x in range(30, 90):
                pixels[x, y] = (
                    0,
                    0,
                    0,
                    255,
                )

        with caplog.at_level(
            logging.WARNING,
            logger=prepare.__name__,
        ):
            prepare._derive_envelope(
                image,
                mode="shrink-wrap",
            )

        assert (
            "Artwork has a complex exterior background. "
            "Shrink-wrap may produce an inaccurate envelope. "
            "Consider removing the background or replacing it with "
            "transparency or a uniform color." in caplog.messages
        )

    finally:
        image.close()


def test_shrink_wrap_does_not_warn_for_uniform_opaque_exterior(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """
    Shrink-wrap does not warn for a simple uniform opaque exterior.
    """

    image = Image.new(
        "RGBA",
        (120, 120),
        (255, 255, 255, 255),
    )

    try:
        pixels = image.load()

        assert pixels is not None

        for y in range(30, 90):
            for x in range(30, 90):
                pixels[x, y] = (
                    0,
                    0,
                    0,
                    255,
                )

        with caplog.at_level(
            logging.WARNING,
            logger=prepare.__name__,
        ):
            prepare._derive_envelope(
                image,
                mode="shrink-wrap",
            )

        assert not caplog.records

    finally:
        image.close()


def test_shrink_wrap_does_not_warn_for_transparent_exterior(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """
    Shrink-wrap does not warn when transparency identifies the exterior.
    """

    image = Image.new(
        "RGBA",
        (120, 120),
        (0, 0, 0, 0),
    )

    try:
        pixels = image.load()

        assert pixels is not None

        for y in range(30, 90):
            for x in range(30, 90):
                pixels[x, y] = (
                    0,
                    0,
                    0,
                    255,
                )

        with caplog.at_level(
            logging.WARNING,
            logger=prepare.__name__,
        ):
            prepare._derive_envelope(
                image,
                mode="shrink-wrap",
            )

        assert not caplog.records

    finally:
        image.close()
