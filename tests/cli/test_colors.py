"""
Tests for the color-analysis CLI command.
"""
# File: tests/cli/test_colors.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from click.testing import CliRunner

from lowkey_artifact_builder.cli._main import cli


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


def test_colors_command_analyzes_and_displays_artifact(
    monkeypatch,
) -> None:
    """
    The colors command obtains structured analysis and displays it.
    """

    analyzed: list[str] = []
    displayed: list[object] = []

    expected_matches = object()

    def fake_analyze_artifact_colors(
        artifact_id: str,
    ) -> object:
        analyzed.append(artifact_id)
        return expected_matches

    def fake_display_color_matches(
        matches: object,
    ) -> None:
        displayed.append(matches)

    monkeypatch.setattr(
        "lowkey_artifact_builder.cli.cmd_color.analyze_artifact_colors",
        fake_analyze_artifact_colors,
    )
    monkeypatch.setattr(
        "lowkey_artifact_builder.cli.cmd_color.display_color_matches",
        fake_display_color_matches,
    )

    runner = CliRunner()

    result = runner.invoke(
        cli,
        ["colors", "nydeli"],
    )

    assert result.exit_code == 0
    assert analyzed == ["nydeli"]
    assert displayed == [expected_matches]
