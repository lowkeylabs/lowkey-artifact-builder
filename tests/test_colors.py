"""
Tests for general color resolution and matching utilities.
"""
# File: tests/test_colors.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import pytest

from lowkey_artifact_builder.colors import (
    ColorError,
    MeasuredColor,
    PaletteColor,
    assign_colors,
    color_distance,
    css_rgb,
    match_color,
    resolve_palette,
    resolve_palette_color,
    rgb_to_lab,
)

# =========================================================
# CSS color resolution
# =========================================================


def test_css_rgb_resolves_named_color() -> None:
    """
    Standard CSS color names resolve to RGB values.
    """

    assert css_rgb("red") == (
        255,
        0,
        0,
    )


def test_css_rgb_is_case_insensitive() -> None:
    """
    CSS color resolution accepts normal CSS name casing.
    """

    assert css_rgb("White") == (
        255,
        255,
        255,
    )


def test_css_rgb_rejects_unknown_color() -> None:
    """
    Unknown CSS color names are rejected.
    """

    with pytest.raises(
        ColorError,
        match="recognized CSS color",
    ):
        css_rgb("definitely-not-a-color")


def test_css_rgb_rejects_empty_name() -> None:
    """
    Empty color names are rejected.
    """

    with pytest.raises(
        ColorError,
        match="non-empty string",
    ):
        css_rgb("")


# =========================================================
# Palette color resolution
# =========================================================


def test_resolve_palette_color_uses_css_color() -> None:
    """
    Unconfigured standard color names resolve through CSS.
    """

    color = resolve_palette_color(
        "black",
        {},
    )

    assert color == PaletteColor(
        name="black",
        rgb=(
            0,
            0,
            0,
        ),
    )


def test_resolve_palette_color_uses_configured_rgb() -> None:
    """
    Explicit palette RGB values override CSS color values.
    """

    color = resolve_palette_color(
        "red",
        {
            "red": {
                "rgb": [
                    200,
                    20,
                    30,
                ],
            },
        },
    )

    assert color == PaletteColor(
        name="red",
        rgb=(
            200,
            20,
            30,
        ),
    )


def test_resolve_palette_color_uses_css_for_configured_color_without_rgb() -> None:
    """
    Configured CSS colors may omit an explicit RGB value.
    """

    color = resolve_palette_color(
        "white",
        {
            "white": {},
        },
    )

    assert color == PaletteColor(
        name="white",
        rgb=(
            255,
            255,
            255,
        ),
    )


def test_resolve_palette_color_rejects_invalid_palette() -> None:
    """
    Palette configuration must be a mapping.
    """

    with pytest.raises(
        ColorError,
        match="palette must be a mapping",
    ):
        resolve_palette_color(
            "red",
            [],  # type: ignore[arg-type]
        )


def test_resolve_palette_color_rejects_non_table_entry() -> None:
    """
    Configured palette entries must be mappings.
    """

    with pytest.raises(
        ColorError,
        match=r"palette\.red must be a table",
    ):
        resolve_palette_color(
            "red",
            {
                "red": "255,0,0",
            },
        )


@pytest.mark.parametrize(
    "rgb",
    [
        [255, 0],
        [255, 0, 0, 0],
        [-1, 0, 0],
        [256, 0, 0],
        [255.0, 0, 0],
        [True, 0, 0],
    ],
)
def test_resolve_palette_color_rejects_invalid_rgb(
    rgb: object,
) -> None:
    """
    Explicit RGB values must contain three byte-sized integers.
    """

    with pytest.raises(
        ColorError,
    ):
        resolve_palette_color(
            "custom",
            {
                "custom": {
                    "rgb": rgb,
                },
            },
        )


# =========================================================
# Palette resolution
# =========================================================


def test_resolve_palette_preserves_order() -> None:
    """
    Palette resolution preserves configured color order.
    """

    palette = resolve_palette(
        (
            "red",
            "black",
            "white",
        ),
        {},
    )

    assert tuple(color.name for color in palette) == (
        "red",
        "black",
        "white",
    )

    assert tuple(color.rgb for color in palette) == (
        (
            255,
            0,
            0,
        ),
        (
            0,
            0,
            0,
        ),
        (
            255,
            255,
            255,
        ),
    )


def test_resolve_palette_uses_configured_overrides() -> None:
    """
    Palette resolution applies configured RGB overrides.
    """

    palette = resolve_palette(
        (
            "red",
            "white",
        ),
        {
            "red": {
                "rgb": [
                    190,
                    30,
                    40,
                ],
            },
        },
    )

    assert palette == (
        PaletteColor(
            name="red",
            rgb=(
                190,
                30,
                40,
            ),
        ),
        PaletteColor(
            name="white",
            rgb=(
                255,
                255,
                255,
            ),
        ),
    )


def test_resolve_palette_rejects_empty_sequence() -> None:
    """
    An empty palette is invalid.
    """

    with pytest.raises(
        ColorError,
        match="cannot be empty",
    ):
        resolve_palette(
            (),
            {},
        )


def test_resolve_palette_rejects_string_as_sequence() -> None:
    """
    A single string is not treated as a sequence of color names.
    """

    with pytest.raises(
        ColorError,
        match="sequence of strings",
    ):
        resolve_palette(
            "red",  # type: ignore[arg-type]
            {},
        )


def test_resolve_palette_rejects_duplicate_names() -> None:
    """
    Semantic palette color identities must be unique.
    """

    with pytest.raises(
        ColorError,
        match="Duplicate palette color",
    ):
        resolve_palette(
            (
                "red",
                "red",
            ),
            {},
        )


# =========================================================
# Lab conversion
# =========================================================


def test_rgb_to_lab_black() -> None:
    """
    Black converts to approximately zero lightness.
    """

    lightness, a, b = rgb_to_lab(
        (
            0,
            0,
            0,
        )
    )

    assert lightness == pytest.approx(
        0.0,
        abs=1e-9,
    )

    assert a == pytest.approx(
        0.0,
        abs=1e-9,
    )

    assert b == pytest.approx(
        0.0,
        abs=1e-9,
    )


def test_rgb_to_lab_white() -> None:
    """
    D65 white converts to approximately L*=100 and neutral chroma.
    """

    lightness, a, b = rgb_to_lab(
        (
            255,
            255,
            255,
        )
    )

    assert lightness == pytest.approx(
        100.0,
        abs=0.001,
    )

    assert a == pytest.approx(
        0.0,
        abs=0.001,
    )

    assert b == pytest.approx(
        0.0,
        abs=0.001,
    )


# =========================================================
# Color distance
# =========================================================


def test_color_distance_identical_colors_is_zero() -> None:
    """
    Identical colors have zero perceptual distance.
    """

    assert color_distance(
        (
            20,
            40,
            60,
        ),
        (
            20,
            40,
            60,
        ),
    ) == pytest.approx(0.0)


def test_color_distance_is_symmetric() -> None:
    """
    Perceptual color distance is symmetric.
    """

    first = (
        220,
        40,
        30,
    )

    second = (
        10,
        20,
        30,
    )

    assert color_distance(
        first,
        second,
    ) == pytest.approx(
        color_distance(
            second,
            first,
        )
    )


def test_color_distance_distinguishes_colors() -> None:
    """
    Different colors have positive perceptual distance.
    """

    assert (
        color_distance(
            (
                255,
                0,
                0,
            ),
            (
                0,
                0,
                0,
            ),
        )
        > 0.0
    )


# =========================================================
# Color assignment
# =========================================================


def test_assign_colors_assigns_exact_matches() -> None:
    """
    Exact measured colors map to their matching palette colors.
    """

    assignments = assign_colors(
        (
            MeasuredColor(
                index=1,
                rgb=(
                    255,
                    255,
                    255,
                ),
            ),
            MeasuredColor(
                index=2,
                rgb=(
                    255,
                    0,
                    0,
                ),
            ),
            MeasuredColor(
                index=3,
                rgb=(
                    0,
                    0,
                    0,
                ),
            ),
        ),
        (
            PaletteColor(
                name="red",
                rgb=(
                    255,
                    0,
                    0,
                ),
            ),
            PaletteColor(
                name="black",
                rgb=(
                    0,
                    0,
                    0,
                ),
            ),
            PaletteColor(
                name="white",
                rgb=(
                    255,
                    255,
                    255,
                ),
            ),
        ),
    )

    assert tuple(assignment.color.name for assignment in assignments) == (
        "white",
        "red",
        "black",
    )

    assert all(assignment.distance == pytest.approx(0.0) for assignment in assignments)


def test_assign_colors_preserves_measured_order() -> None:
    """
    Assignment results remain in measured-color order.
    """

    measured = (
        MeasuredColor(
            index=7,
            rgb=(
                0,
                0,
                0,
            ),
        ),
        MeasuredColor(
            index=3,
            rgb=(
                255,
                255,
                255,
            ),
        ),
    )

    assignments = assign_colors(
        measured,
        (
            PaletteColor(
                name="white",
                rgb=(
                    255,
                    255,
                    255,
                ),
            ),
            PaletteColor(
                name="black",
                rgb=(
                    0,
                    0,
                    0,
                ),
            ),
        ),
    )

    assert tuple(assignment.measured.index for assignment in assignments) == (
        7,
        3,
    )

    assert tuple(assignment.color.name for assignment in assignments) == (
        "black",
        "white",
    )


def test_assign_colors_uses_nearest_perceptual_matches() -> None:
    """
    Near matches map to the perceptually closest palette colors.
    """

    assignments = assign_colors(
        (
            MeasuredColor(
                index=1,
                rgb=(
                    240,
                    20,
                    20,
                ),
            ),
            MeasuredColor(
                index=2,
                rgb=(
                    15,
                    15,
                    15,
                ),
            ),
            MeasuredColor(
                index=3,
                rgb=(
                    245,
                    245,
                    245,
                ),
            ),
        ),
        (
            PaletteColor(
                name="black",
                rgb=(
                    0,
                    0,
                    0,
                ),
            ),
            PaletteColor(
                name="white",
                rgb=(
                    255,
                    255,
                    255,
                ),
            ),
            PaletteColor(
                name="red",
                rgb=(
                    255,
                    0,
                    0,
                ),
            ),
        ),
    )

    assert tuple(assignment.color.name for assignment in assignments) == (
        "red",
        "black",
        "white",
    )


def test_assign_colors_is_one_to_one() -> None:
    """
    Each palette color is assigned exactly once.
    """

    assignments = assign_colors(
        (
            MeasuredColor(
                index=1,
                rgb=(
                    250,
                    10,
                    10,
                ),
            ),
            MeasuredColor(
                index=2,
                rgb=(
                    200,
                    20,
                    20,
                ),
            ),
        ),
        (
            PaletteColor(
                name="red",
                rgb=(
                    255,
                    0,
                    0,
                ),
            ),
            PaletteColor(
                name="black",
                rgb=(
                    0,
                    0,
                    0,
                ),
            ),
        ),
    )

    names = [assignment.color.name for assignment in assignments]

    assert sorted(names) == [
        "black",
        "red",
    ]


def test_assign_colors_finds_global_minimum(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Assignment minimizes total distance rather than greedily assigning
    each measured color to its nearest currently available color.
    """

    measured = (
        MeasuredColor(
            index=1,
            rgb=(
                1,
                0,
                0,
            ),
        ),
        MeasuredColor(
            index=2,
            rgb=(
                2,
                0,
                0,
            ),
        ),
    )

    palette = (
        PaletteColor(
            name="first",
            rgb=(
                10,
                0,
                0,
            ),
        ),
        PaletteColor(
            name="second",
            rgb=(
                20,
                0,
                0,
            ),
        ),
    )

    distances = {
        (
            measured[0].rgb,
            palette[0].rgb,
        ): 1.0,
        (
            measured[0].rgb,
            palette[1].rgb,
        ): 2.0,
        (
            measured[1].rgb,
            palette[0].rgb,
        ): 1.1,
        (
            measured[1].rgb,
            palette[1].rgb,
        ): 100.0,
    }

    def fake_color_distance(
        first: tuple[
            int,
            int,
            int,
        ],
        second: tuple[
            int,
            int,
            int,
        ],
    ) -> float:
        return distances[
            (
                first,
                second,
            )
        ]

    monkeypatch.setattr(
        "lowkey_artifact_builder.colors.color_distance",
        fake_color_distance,
    )

    assignments = assign_colors(
        measured,
        palette,
    )

    #
    # Greedy assignment would choose:
    #
    #     measured 1 -> first   (1.0)
    #     measured 2 -> second  (100.0)
    #
    # total = 101.0
    #
    # The global optimum is:
    #
    #     measured 1 -> second  (2.0)
    #     measured 2 -> first   (1.1)
    #
    # total = 3.1
    #

    assert tuple(assignment.color.name for assignment in assignments) == (
        "second",
        "first",
    )

    assert sum(assignment.distance for assignment in assignments) == pytest.approx(3.1)


def test_assign_colors_rejects_empty_measured_colors() -> None:
    """
    At least one measured color is required.
    """

    with pytest.raises(
        ColorError,
        match="Measured colors cannot be empty",
    ):
        assign_colors(
            (),
            (
                PaletteColor(
                    name="red",
                    rgb=(
                        255,
                        0,
                        0,
                    ),
                ),
            ),
        )


def test_assign_colors_rejects_empty_palette() -> None:
    """
    At least one palette color is required.
    """

    with pytest.raises(
        ColorError,
        match="Palette colors cannot be empty",
    ):
        assign_colors(
            (
                MeasuredColor(
                    index=1,
                    rgb=(
                        255,
                        0,
                        0,
                    ),
                ),
            ),
            (),
        )


def test_assign_colors_rejects_different_counts() -> None:
    """
    One-to-one assignment requires equal color counts.
    """

    with pytest.raises(
        ColorError,
        match="Measured color count must equal palette color count",
    ):
        assign_colors(
            (
                MeasuredColor(
                    index=1,
                    rgb=(
                        255,
                        0,
                        0,
                    ),
                ),
            ),
            (
                PaletteColor(
                    name="red",
                    rgb=(
                        255,
                        0,
                        0,
                    ),
                ),
                PaletteColor(
                    name="black",
                    rgb=(
                        0,
                        0,
                        0,
                    ),
                ),
            ),
        )


def test_assign_colors_rejects_duplicate_measured_indexes() -> None:
    """
    Measured-color indexes identify distinct inputs.
    """

    with pytest.raises(
        ColorError,
        match="Duplicate measured color index",
    ):
        assign_colors(
            (
                MeasuredColor(
                    index=1,
                    rgb=(
                        255,
                        0,
                        0,
                    ),
                ),
                MeasuredColor(
                    index=1,
                    rgb=(
                        0,
                        0,
                        0,
                    ),
                ),
            ),
            (
                PaletteColor(
                    name="red",
                    rgb=(
                        255,
                        0,
                        0,
                    ),
                ),
                PaletteColor(
                    name="black",
                    rgb=(
                        0,
                        0,
                        0,
                    ),
                ),
            ),
        )


def test_assign_colors_rejects_duplicate_palette_names() -> None:
    """
    Palette colors must have distinct semantic identities.
    """

    with pytest.raises(
        ColorError,
        match="Duplicate palette color",
    ):
        assign_colors(
            (
                MeasuredColor(
                    index=1,
                    rgb=(
                        255,
                        0,
                        0,
                    ),
                ),
                MeasuredColor(
                    index=2,
                    rgb=(
                        0,
                        0,
                        0,
                    ),
                ),
            ),
            (
                PaletteColor(
                    name="red",
                    rgb=(
                        255,
                        0,
                        0,
                    ),
                ),
                PaletteColor(
                    name="red",
                    rgb=(
                        200,
                        0,
                        0,
                    ),
                ),
            ),
        )


# =========================================================
# Nearest color matching
# =========================================================


def test_match_color_selects_exact_match() -> None:
    """
    An exact RGB match selects the corresponding candidate.
    """

    requested = PaletteColor(
        name="requested",
        rgb=(255, 0, 0),
    )

    candidates = (
        PaletteColor(
            name="blue",
            rgb=(0, 0, 255),
        ),
        PaletteColor(
            name="red",
            rgb=(255, 0, 0),
        ),
    )

    match = match_color(
        requested,
        candidates,
    )

    assert match.requested is requested
    assert match.color is candidates[1]
    assert match.distance == pytest.approx(0.0)


def test_match_color_selects_nearest_perceptual_match() -> None:
    """
    Matching selects the candidate with the smallest perceptual distance.
    """

    requested = PaletteColor(
        name="requested",
        rgb=(240, 20, 20),
    )

    candidates = (
        PaletteColor(
            name="black",
            rgb=(0, 0, 0),
        ),
        PaletteColor(
            name="red",
            rgb=(255, 0, 0),
        ),
        PaletteColor(
            name="white",
            rgb=(255, 255, 255),
        ),
    )

    match = match_color(
        requested,
        candidates,
    )

    assert match.color is candidates[1]
    assert match.distance == pytest.approx(
        color_distance(
            requested.rgb,
            candidates[1].rgb,
        )
    )


def test_match_color_accepts_single_candidate() -> None:
    """
    Matching works when only one candidate is available.
    """

    requested = PaletteColor(
        name="requested",
        rgb=(100, 120, 140),
    )

    candidate = PaletteColor(
        name="only",
        rgb=(10, 20, 30),
    )

    match = match_color(
        requested,
        (candidate,),
    )

    assert match.requested is requested
    assert match.color is candidate
    assert match.distance == pytest.approx(
        color_distance(
            requested.rgb,
            candidate.rgb,
        )
    )


def test_match_color_accepts_many_candidates() -> None:
    """
    Matching supports arbitrary candidate-set sizes.
    """

    requested = PaletteColor(
        name="requested",
        rgb=(250, 250, 250),
    )

    candidates = (
        PaletteColor(
            name="red",
            rgb=(255, 0, 0),
        ),
        PaletteColor(
            name="green",
            rgb=(0, 255, 0),
        ),
        PaletteColor(
            name="blue",
            rgb=(0, 0, 255),
        ),
        PaletteColor(
            name="black",
            rgb=(0, 0, 0),
        ),
        PaletteColor(
            name="white",
            rgb=(255, 255, 255),
        ),
    )

    match = match_color(
        requested,
        candidates,
    )

    assert match.color is candidates[4]


def test_match_color_preserves_semantic_identity() -> None:
    """
    Matching preserves requested and candidate semantic identities.
    """

    requested = PaletteColor(
        name="artwork-red",
        rgb=(250, 10, 10),
    )

    candidate = PaletteColor(
        name="fire-engine-red",
        rgb=(255, 0, 0),
    )

    match = match_color(
        requested,
        (candidate,),
    )

    assert match.requested is requested
    assert match.requested.name == "artwork-red"
    assert match.color is candidate
    assert match.color.name == "fire-engine-red"


def test_match_color_returns_perceptual_distance() -> None:
    """
    Matching exposes the established perceptual color distance.
    """

    requested = PaletteColor(
        name="requested",
        rgb=(200, 30, 40),
    )

    candidate = PaletteColor(
        name="candidate",
        rgb=(220, 20, 30),
    )

    match = match_color(
        requested,
        (candidate,),
    )

    assert match.distance == pytest.approx(
        color_distance(
            requested.rgb,
            candidate.rgb,
        )
    )


def test_match_color_preserves_candidate_order_for_equal_distance() -> None:
    """
    Equal-distance matches select the earliest candidate.
    """

    requested = PaletteColor(
        name="requested",
        rgb=(100, 100, 100),
    )

    first = PaletteColor(
        name="first",
        rgb=(100, 100, 100),
    )

    second = PaletteColor(
        name="second",
        rgb=(100, 100, 100),
    )

    match = match_color(
        requested,
        (
            first,
            second,
        ),
    )

    assert match.color is first


def test_match_color_rejects_empty_candidates() -> None:
    """
    Matching requires at least one candidate color.
    """

    with pytest.raises(
        ColorError,
        match="cannot be empty",
    ):
        match_color(
            PaletteColor(
                name="requested",
                rgb=(255, 0, 0),
            ),
            (),
        )
