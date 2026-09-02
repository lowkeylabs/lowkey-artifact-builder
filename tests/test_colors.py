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
    recommend_palette,
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

    result = assign_colors(
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

    assignments = result.assignments

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

    result = assign_colors(
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

    assignments = result.assignments

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

    result = assign_colors(
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

    assignments = result.assignments

    assert tuple(assignment.color.name for assignment in assignments) == (
        "red",
        "black",
        "white",
    )


def test_assign_colors_is_one_to_one() -> None:
    """
    Each palette color is assigned exactly once.
    """

    result = assign_colors(
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

    assignments = result.assignments
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

    result = assign_colors(
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

    assignments = result.assignments

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


def test_assign_colors_selects_one_color_from_multiple_candidates() -> None:
    """
    One measured color selects its best match from a larger candidate set.
    """

    result = assign_colors(
        (
            MeasuredColor(
                index=7,
                rgb=(
                    250,
                    10,
                    10,
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
                name="red",
                rgb=(
                    255,
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

    assignments = result.assignments

    assert len(assignments) == 1
    assert assignments[0].measured.index == 7
    assert assignments[0].color.name == "red"


def test_assign_colors_selects_best_subset_from_larger_candidate_set() -> None:
    """
    Assignment selects only the globally best distinct candidate subset.

    Candidate colors that are not needed for the optimal assignment remain
    unused.
    """

    result = assign_colors(
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
                    10,
                    10,
                    250,
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
                name="red",
                rgb=(
                    255,
                    0,
                    0,
                ),
            ),
            PaletteColor(
                name="green",
                rgb=(
                    0,
                    255,
                    0,
                ),
            ),
            PaletteColor(
                name="blue",
                rgb=(
                    0,
                    0,
                    255,
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

    assignments = result.assignments

    assert tuple(assignment.color.name for assignment in assignments) == (
        "red",
        "blue",
    )


def test_assign_colors_rejects_insufficient_candidates() -> None:
    """
    Every measured color requires one distinct candidate identity.
    """

    with pytest.raises(
        ColorError,
        match="Palette color count cannot be smaller than measured color count",
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
                        255,
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


# =========================================================
# Palette recommendation
# =========================================================


def test_recommend_palette_honors_requested_palette_size() -> None:
    """
    Palette recommendation returns the requested number of colors.
    """

    requested = (
        PaletteColor(
            name="artwork-red",
            rgb=(255, 0, 0),
        ),
        PaletteColor(
            name="artwork-green",
            rgb=(0, 255, 0),
        ),
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
    )

    recommendation = recommend_palette(
        requested,
        candidates,
        palette_size=2,
    )

    assert len(recommendation.colors) == 2


def test_recommend_palette_includes_mandatory_colors() -> None:
    """
    Mandatory colors are always included in the recommended palette.
    """

    requested = (
        PaletteColor(
            name="artwork-red",
            rgb=(255, 0, 0),
        ),
        PaletteColor(
            name="artwork-green",
            rgb=(0, 255, 0),
        ),
    )

    white = PaletteColor(
        name="white",
        rgb=(255, 255, 255),
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
        white,
    )

    recommendation = recommend_palette(
        requested,
        candidates,
        palette_size=2,
        mandatory=(white,),
    )

    assert white in recommendation.colors
    assert len(recommendation.colors) == 2


def test_recommend_palette_contains_no_duplicate_colors() -> None:
    """
    Recommended palettes contain distinct semantic color identities.
    """

    requested = (
        PaletteColor(
            name="artwork-red",
            rgb=(255, 0, 0),
        ),
        PaletteColor(
            name="artwork-green",
            rgb=(0, 255, 0),
        ),
        PaletteColor(
            name="artwork-blue",
            rgb=(0, 0, 255),
        ),
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
    )

    recommendation = recommend_palette(
        requested,
        candidates,
        palette_size=2,
    )

    names = tuple(color.name for color in recommendation.colors)

    assert len(names) == len(set(names))


def test_recommend_palette_prefers_globally_better_palette(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Recommendation minimizes representation error across all requested colors.

    The best complete palette can differ from colors obtained by considering
    requested colors independently.
    """

    requested = (
        PaletteColor(
            name="artwork-first",
            rgb=(1, 0, 0),
        ),
        PaletteColor(
            name="artwork-second",
            rgb=(2, 0, 0),
        ),
        PaletteColor(
            name="artwork-third",
            rgb=(3, 0, 0),
        ),
    )

    first = PaletteColor(
        name="first",
        rgb=(10, 0, 0),
    )

    second = PaletteColor(
        name="second",
        rgb=(20, 0, 0),
    )

    compromise = PaletteColor(
        name="compromise",
        rgb=(30, 0, 0),
    )

    candidates = (
        first,
        second,
        compromise,
    )

    distances = {
        (requested[0].rgb, first.rgb): 0.0,
        (requested[0].rgb, second.rgb): 100.0,
        (requested[0].rgb, compromise.rgb): 10.0,
        (requested[1].rgb, first.rgb): 100.0,
        (requested[1].rgb, second.rgb): 0.0,
        (requested[1].rgb, compromise.rgb): 10.0,
        (requested[2].rgb, first.rgb): 100.0,
        (requested[2].rgb, second.rgb): 100.0,
        (requested[2].rgb, compromise.rgb): 10.0,
    }

    def fake_color_distance(
        left: tuple[int, int, int],
        right: tuple[int, int, int],
    ) -> float:
        return distances[
            (
                left,
                right,
            )
        ]

    monkeypatch.setattr(
        "lowkey_artifact_builder.colors.color_distance",
        fake_color_distance,
    )

    recommendation = recommend_palette(
        requested,
        candidates,
        palette_size=1,
    )

    #
    # Independent nearest matches use all three candidate identities:
    #
    #     first  -> first       0
    #     second -> second      0
    #     third  -> compromise 10
    #
    # A one-color printer cannot use all three. Across the complete Artwork,
    # compromise is the best single palette:
    #
    #     compromise = 10 + 10 + 10 = 30
    #     first      = 0 + 100 + 100 = 200
    #     second     = 100 + 0 + 100 = 200
    #

    assert recommendation.colors == (compromise,)
    assert recommendation.score == pytest.approx(30.0)


def test_recommend_palette_exposes_aggregate_score() -> None:
    """
    Palette recommendations expose total representation distance.
    """

    requested = (
        PaletteColor(
            name="artwork-red",
            rgb=(240, 20, 20),
        ),
        PaletteColor(
            name="artwork-blue",
            rgb=(20, 20, 240),
        ),
    )

    red = PaletteColor(
        name="red",
        rgb=(255, 0, 0),
    )

    blue = PaletteColor(
        name="blue",
        rgb=(0, 0, 255),
    )

    recommendation = recommend_palette(
        requested,
        (
            red,
            blue,
        ),
        palette_size=2,
    )

    expected_score = color_distance(
        requested[0].rgb,
        red.rgb,
    ) + color_distance(
        requested[1].rgb,
        blue.rgb,
    )

    assert recommendation.score == pytest.approx(expected_score)


def test_recommend_palette_is_deterministic_for_equal_scores(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Equal-scoring palettes preserve deterministic candidate ordering.
    """

    requested = (
        PaletteColor(
            name="artwork",
            rgb=(1, 0, 0),
        ),
    )

    first = PaletteColor(
        name="first",
        rgb=(10, 0, 0),
    )

    second = PaletteColor(
        name="second",
        rgb=(20, 0, 0),
    )

    def fake_color_distance(
        left: tuple[int, int, int],
        right: tuple[int, int, int],
    ) -> float:
        return 1.0

    monkeypatch.setattr(
        "lowkey_artifact_builder.colors.color_distance",
        fake_color_distance,
    )

    recommendation = recommend_palette(
        requested,
        (
            first,
            second,
        ),
        palette_size=1,
    )

    assert recommendation.colors == (first,)
    assert recommendation.score == pytest.approx(1.0)


# =========================================================
# Palette recommendation validation
# =========================================================


def test_recommend_palette_rejects_empty_requested_colors() -> None:
    """
    Palette recommendation requires at least one requested color.
    """

    with pytest.raises(
        ColorError,
        match="Requested colors cannot be empty",
    ):
        recommend_palette(
            (),
            (
                PaletteColor(
                    name="red",
                    rgb=(255, 0, 0),
                ),
            ),
            palette_size=1,
        )


def test_recommend_palette_rejects_empty_candidates() -> None:
    """
    Palette recommendation requires at least one candidate color.
    """

    with pytest.raises(
        ColorError,
        match="Candidate colors cannot be empty",
    ):
        recommend_palette(
            (
                PaletteColor(
                    name="artwork-red",
                    rgb=(255, 0, 0),
                ),
            ),
            (),
            palette_size=1,
        )


@pytest.mark.parametrize(
    "palette_size",
    [
        0,
        -1,
        True,
    ],
)
def test_recommend_palette_rejects_invalid_palette_size(
    palette_size: object,
) -> None:
    """
    Palette size must be a positive integer.
    """

    with pytest.raises(
        ColorError,
        match="Palette size must be a positive integer",
    ):
        recommend_palette(
            (
                PaletteColor(
                    name="artwork-red",
                    rgb=(255, 0, 0),
                ),
            ),
            (
                PaletteColor(
                    name="red",
                    rgb=(255, 0, 0),
                ),
            ),
            palette_size=palette_size,  # type: ignore[arg-type]
        )


def test_recommend_palette_rejects_palette_larger_than_candidates() -> None:
    """
    Requested palette size cannot exceed the available candidate colors.
    """

    with pytest.raises(
        ColorError,
        match="Palette size cannot exceed candidate color count",
    ):
        recommend_palette(
            (
                PaletteColor(
                    name="artwork-red",
                    rgb=(255, 0, 0),
                ),
            ),
            (
                PaletteColor(
                    name="red",
                    rgb=(255, 0, 0),
                ),
            ),
            palette_size=2,
        )


def test_recommend_palette_rejects_too_many_mandatory_colors() -> None:
    """
    Mandatory colors cannot exceed the requested palette size.
    """

    red = PaletteColor(
        name="red",
        rgb=(255, 0, 0),
    )

    white = PaletteColor(
        name="white",
        rgb=(255, 255, 255),
    )

    with pytest.raises(
        ColorError,
        match="Mandatory color count cannot exceed palette size",
    ):
        recommend_palette(
            (
                PaletteColor(
                    name="artwork-red",
                    rgb=(255, 0, 0),
                ),
            ),
            (
                red,
                white,
            ),
            palette_size=1,
            mandatory=(
                red,
                white,
            ),
        )


def test_recommend_palette_rejects_mandatory_color_not_in_candidates() -> None:
    """
    Every mandatory color must identify an available candidate color.
    """

    with pytest.raises(
        ColorError,
        match="Mandatory color is not a candidate",
    ):
        recommend_palette(
            (
                PaletteColor(
                    name="artwork-red",
                    rgb=(255, 0, 0),
                ),
            ),
            (
                PaletteColor(
                    name="red",
                    rgb=(255, 0, 0),
                ),
            ),
            palette_size=1,
            mandatory=(
                PaletteColor(
                    name="white",
                    rgb=(255, 255, 255),
                ),
            ),
        )


def test_assign_colors_finds_global_minimum_from_larger_candidate_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Assignment selects the globally optimal distinct subset and pairing
    when more candidates than measured colors are available.
    """

    measured = (
        MeasuredColor(
            index=1,
            rgb=(1, 0, 0),
        ),
        MeasuredColor(
            index=2,
            rgb=(2, 0, 0),
        ),
    )

    first = PaletteColor(
        name="first",
        rgb=(10, 0, 0),
    )
    second = PaletteColor(
        name="second",
        rgb=(20, 0, 0),
    )
    unused = PaletteColor(
        name="unused",
        rgb=(30, 0, 0),
    )

    distances = {
        (measured[0].rgb, first.rgb): 1.0,
        (measured[0].rgb, second.rgb): 2.0,
        (measured[0].rgb, unused.rgb): 50.0,
        (measured[1].rgb, first.rgb): 1.1,
        (measured[1].rgb, second.rgb): 100.0,
        (measured[1].rgb, unused.rgb): 50.0,
    }

    def fake_color_distance(
        left: tuple[int, int, int],
        right: tuple[int, int, int],
    ) -> float:
        return distances[(left, right)]

    monkeypatch.setattr(
        "lowkey_artifact_builder.colors.color_distance",
        fake_color_distance,
    )

    result = assign_colors(
        measured,
        (
            first,
            second,
            unused,
        ),
    )

    assignments = result.assignments

    assert tuple(assignment.color.name for assignment in assignments) == (
        "second",
        "first",
    )

    assert tuple(assignment.distance for assignment in assignments) == pytest.approx(
        (
            2.0,
            1.1,
        )
    )


def test_assign_colors_preserves_candidate_order_for_equal_optima(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Equal-scoring assignments deterministically prefer candidate input order.
    """

    measured = (
        MeasuredColor(
            index=1,
            rgb=(1, 0, 0),
        ),
    )

    first = PaletteColor(
        name="first",
        rgb=(10, 0, 0),
    )
    second = PaletteColor(
        name="second",
        rgb=(20, 0, 0),
    )
    third = PaletteColor(
        name="third",
        rgb=(30, 0, 0),
    )

    monkeypatch.setattr(
        "lowkey_artifact_builder.colors.color_distance",
        lambda left, right: 1.0,
    )

    result = assign_colors(
        measured,
        (
            first,
            second,
            third,
        ),
    )

    assignments = result.assignments

    assert assignments[0].color is first
    assert assignments[0].distance == pytest.approx(1.0)


def test_assign_colors_exposes_aggregate_distance() -> None:
    """
    A complete color assignment exposes its aggregate perceptual distance.
    """

    result = assign_colors(
        (
            MeasuredColor(
                index=1,
                rgb=(250, 10, 10),
            ),
            MeasuredColor(
                index=2,
                rgb=(10, 10, 250),
            ),
        ),
        (
            PaletteColor(
                name="red",
                rgb=(255, 0, 0),
            ),
            PaletteColor(
                name="blue",
                rgb=(0, 0, 255),
            ),
            PaletteColor(
                name="white",
                rgb=(255, 255, 255),
            ),
        ),
    )

    assert result.distance == pytest.approx(
        sum(assignment.distance for assignment in result.assignments)
    )
