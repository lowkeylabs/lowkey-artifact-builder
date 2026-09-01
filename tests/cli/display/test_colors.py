"""
Tests for Artwork color analysis presentation.
"""
# File: tests/cli/display/test_colors.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from lowkey_artifact_builder.cli.display import (
    display_color_matches,
)
from lowkey_artifact_builder.colors import (
    ColorMatch,
    PaletteColor,
)
from lowkey_artifact_builder.model.models.artwork.color_analysis import (
    ArtworkColorMatch,
)


def test_color_report_displays_structured_artwork_matches(
    capsys,
) -> None:
    """
    The color report presents structured Artwork color analysis.
    """

    artwork = PaletteColor(
        name="artwork-red",
        rgb=(250, 10, 10),
    )

    matches = (
        ArtworkColorMatch(
            artwork=artwork,
            printer=ColorMatch(
                requested=artwork,
                color=PaletteColor(
                    name="fire-engine-red",
                    rgb=(220, 20, 30),
                ),
                distance=4.25,
            ),
            library=ColorMatch(
                requested=artwork,
                color=PaletteColor(
                    name="brick-red",
                    rgb=(190, 50, 40),
                ),
                distance=7.5,
            ),
            catalog=ColorMatch(
                requested=artwork,
                color=PaletteColor(
                    name="red",
                    rgb=(240, 0, 0),
                ),
                distance=2.75,
            ),
        ),
    )

    display_color_matches(matches)

    output = capsys.readouterr().out

    assert "Artwork" in output
    assert "Printer" in output
    assert "Library" in output
    assert "Catalog" in output

    assert "artwork-red" in output
    assert "fire-engine-red" in output
    assert "brick-red" in output
    assert "red" in output


def test_color_report_displays_match_distances(
    capsys,
) -> None:
    """
    The color report exposes perceptual match distances.
    """

    artwork = PaletteColor(
        name="artwork-red",
        rgb=(250, 10, 10),
    )

    matches = (
        ArtworkColorMatch(
            artwork=artwork,
            printer=ColorMatch(
                requested=artwork,
                color=PaletteColor(
                    name="printer-red",
                    rgb=(220, 20, 30),
                ),
                distance=4.25,
            ),
            library=ColorMatch(
                requested=artwork,
                color=PaletteColor(
                    name="library-red",
                    rgb=(190, 50, 40),
                ),
                distance=7.5,
            ),
            catalog=ColorMatch(
                requested=artwork,
                color=PaletteColor(
                    name="catalog-red",
                    rgb=(240, 0, 0),
                ),
                distance=2.75,
            ),
        ),
    )

    display_color_matches(matches)

    output = capsys.readouterr().out

    assert "4.25" in output
    assert "7.50" in output
    assert "2.75" in output


def test_color_report_displays_every_artwork_color(
    capsys,
) -> None:
    """
    The color report includes every structured Artwork color match.
    """

    artwork_colors = (
        PaletteColor(
            name="artwork-red",
            rgb=(250, 10, 10),
        ),
        PaletteColor(
            name="artwork-green",
            rgb=(10, 250, 10),
        ),
        PaletteColor(
            name="artwork-blue",
            rgb=(10, 10, 250),
        ),
    )

    matches = tuple(
        ArtworkColorMatch(
            artwork=artwork,
            printer=ColorMatch(
                requested=artwork,
                color=PaletteColor(
                    name=f"printer-{artwork.name}",
                    rgb=artwork.rgb,
                ),
                distance=1.0,
            ),
            library=ColorMatch(
                requested=artwork,
                color=PaletteColor(
                    name=f"library-{artwork.name}",
                    rgb=artwork.rgb,
                ),
                distance=2.0,
            ),
            catalog=ColorMatch(
                requested=artwork,
                color=PaletteColor(
                    name=f"catalog-{artwork.name}",
                    rgb=artwork.rgb,
                ),
                distance=3.0,
            ),
        )
        for artwork in artwork_colors
    )

    display_color_matches(matches)

    output = capsys.readouterr().out

    assert "artwork-red" in output
    assert "artwork-green" in output
    assert "artwork-blue" in output


def test_color_report_preserves_structured_analysis_order(
    capsys,
) -> None:
    """
    Color report ordering follows the structured Artwork analysis order.
    """

    artwork_colors = (
        PaletteColor(
            name="first",
            rgb=(10, 20, 30),
        ),
        PaletteColor(
            name="second",
            rgb=(40, 50, 60),
        ),
        PaletteColor(
            name="third",
            rgb=(70, 80, 90),
        ),
    )

    matches = tuple(
        ArtworkColorMatch(
            artwork=artwork,
            printer=ColorMatch(
                requested=artwork,
                color=PaletteColor(
                    name=f"p-{artwork.name}",
                    rgb=artwork.rgb,
                ),
                distance=1.0,
            ),
            library=ColorMatch(
                requested=artwork,
                color=PaletteColor(
                    name=f"l-{artwork.name}",
                    rgb=artwork.rgb,
                ),
                distance=2.0,
            ),
            catalog=ColorMatch(
                requested=artwork,
                color=PaletteColor(
                    name=f"c-{artwork.name}",
                    rgb=artwork.rgb,
                ),
                distance=3.0,
            ),
        )
        for artwork in artwork_colors
    )

    display_color_matches(matches)

    output = capsys.readouterr().out

    assert output.index("first") < output.index("second")
    assert output.index("second") < output.index("third")
