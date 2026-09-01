"""
Tests for the color-analysis CLI command.
"""
# File: tests/cli/test_colors.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from click.testing import CliRunner

from lowkey_artifact_builder.cli._main import cli
from lowkey_artifact_builder.cli.cmd_color import display_color_matches
from lowkey_artifact_builder.colors import ColorMatch, PaletteColor
from lowkey_artifact_builder.model.models.artwork.color_analysis import (
    ArtworkColorMatch,
)


def test_colors_is_a_top_level_command() -> None:
    """
    Color analysis is exposed through the standard artifact CLI.
    """

    runner = CliRunner()

    result = runner.invoke(
        cli,
        ["--help"],
    )

    assert result.exit_code == 0
    assert "colors" in result.output


def test_colors_requires_an_artifact_id() -> None:
    """
    Color analysis identifies the artifact whose prepared Artwork is analyzed.
    """

    runner = CliRunner()

    result = runner.invoke(
        cli,
        ["colors"],
    )

    assert result.exit_code != 0
    assert "ARTIFACT_ID" in result.output


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
