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
