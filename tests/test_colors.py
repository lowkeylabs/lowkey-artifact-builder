"""
Tests for general color resolution and assignment utilities.
"""
# File: tests/test_colors.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import pytest

from lowkey_artifact_builder.colors import (
    ColorAssignmentResult,
    ColorError,
    MeasuredColor,
    PaletteColor,
    assign_colors,
    color_distance,
    css_rgb,
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


def test_assign_colors_returns_public_assignment_result() -> None:
    """
    Color assignment returns the public aggregate assignment result.
    """

    result = assign_colors(
        (
            MeasuredColor(
                index=1,
                rgb=(250, 10, 10),
            ),
        ),
        (
            PaletteColor(
                name="red",
                rgb=(255, 0, 0),
            ),
        ),
    )

    assert isinstance(
        result,
        ColorAssignmentResult,
    )


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
    Near matches map to the perceptually closest distinct palette colors.
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
    Distinct measured colors receive distinct palette identities.
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

    names = [assignment.color.name for assignment in result.assignments]

    assert sorted(names) == [
        "black",
        "red",
    ]


def test_assign_colors_finds_global_minimum(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Assignment minimizes aggregate distance rather than greedily assigning
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

    assert result.distance == pytest.approx(3.1)


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

    assert result.distance == pytest.approx(3.1)


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


# =========================================================
# Color assignment validation
# =========================================================


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
