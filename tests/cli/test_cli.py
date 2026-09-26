"""Tests for the main artifact CLI entry point."""
# File: tests/cli/test_cli.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

import pytest
from click.testing import CliRunner

from lowkey_artifact_builder.cli._main import cli

# =========================================================
# Main CLI
# =========================================================


def test_cli_help() -> None:
    """The artifact CLI displays help successfully."""

    runner = CliRunner()

    result = runner.invoke(
        cli,
        ["--help"],
    )

    assert result.exit_code == 0
    assert "Usage:" in result.output


def test_cli_lists_config_command() -> None:
    """The artifact CLI exposes the config command."""

    runner = CliRunner()

    result = runner.invoke(
        cli,
        ["--help"],
    )

    assert result.exit_code == 0
    assert "config" in result.output


# =========================================================
# Config CLI
# =========================================================


def test_cli_config_help() -> None:
    """The config command displays help successfully."""

    runner = CliRunner()

    result = runner.invoke(
        cli,
        ["config", "--help"],
    )

    assert result.exit_code == 0
    assert "Usage:" in result.output


def test_cli_config_help_lists_model_option() -> None:
    """The config command exposes model listing."""

    runner = CliRunner()

    result = runner.invoke(
        cli,
        ["config", "--help"],
    )

    assert result.exit_code == 0
    assert "--list-models" in result.output


# =========================================================
# Model listing
# =========================================================


def test_cli_config_list_models() -> None:
    """Config lists the registered artifact models."""

    runner = CliRunner()

    result = runner.invoke(
        cli,
        [
            "config",
            "--list-models",
        ],
    )

    assert result.exit_code == 0

    assert "Available Models" in result.output


def test_cli_config_list_models_dump() -> None:
    """Config can dump complete registered model definitions."""

    runner = CliRunner()

    result = runner.invoke(
        cli,
        [
            "config",
            "--list-models",
            "--dump",
        ],
    )

    assert result.exit_code == 0

    assert "Features" in result.output
    assert "Stages" in result.output


def test_cli_config_list_models_rejects_artifact_ids() -> None:
    """Model listing cannot be combined with artifact IDs."""

    runner = CliRunner()

    result = runner.invoke(
        cli,
        [
            "config",
            "example",
            "--list-models",
        ],
    )

    assert result.exit_code != 0

    assert "--list-models cannot be used with artifact IDs." in result.output


def test_cli_uses_default_logging_without_verbose(
    monkeypatch,
) -> None:
    """The root CLI uses default logging when verbosity is not requested."""

    configured_levels: list[object] = []

    def configure(level=None) -> None:
        configured_levels.append(level)

    monkeypatch.setattr(
        "lowkey_artifact_builder.cli._main.configure_logging",
        configure,
    )

    runner = CliRunner()

    result = runner.invoke(
        cli,
        [],
    )

    assert result.exit_code == 0
    assert configured_levels == [None]


# =========================================================
# Semantic verbosity and diagnostic logging
# =========================================================


def test_cli_verbose_sets_semantic_verbosity_without_changing_logging(
    monkeypatch,
) -> None:
    """
    -v selects manufacturing-progress messaging independently of logging.
    """

    configured_levels: list[object] = []

    monkeypatch.setattr(
        "lowkey_artifact_builder.cli._main.configure_logging",
        configured_levels.append,
    )

    runner = CliRunner()

    result = runner.invoke(
        cli,
        ["-v"],
    )

    assert result.exit_code == 0
    assert configured_levels == [None]


def test_cli_very_verbose_sets_semantic_verbosity_without_changing_logging(
    monkeypatch,
) -> None:
    """
    -vv selects semantic diagnostics independently of logging.
    """

    configured_levels: list[object] = []

    monkeypatch.setattr(
        "lowkey_artifact_builder.cli._main.configure_logging",
        configured_levels.append,
    )

    runner = CliRunner()

    result = runner.invoke(
        cli,
        ["-vv"],
    )

    assert result.exit_code == 0
    assert configured_levels == [None]


def test_cli_log_level_controls_diagnostic_logging(
    monkeypatch,
) -> None:
    """
    --log-level explicitly controls Python diagnostic logging.
    """

    configured_levels: list[object] = []

    monkeypatch.setattr(
        "lowkey_artifact_builder.cli._main.configure_logging",
        configured_levels.append,
    )

    runner = CliRunner()

    result = runner.invoke(
        cli,
        ["--log-level=DEBUG"],
    )

    assert result.exit_code == 0
    assert configured_levels == ["DEBUG"]


def test_cli_quiet_does_not_change_diagnostic_logging(
    monkeypatch,
) -> None:
    """
    --quiet affects semantic messaging only.
    """

    configured_levels: list[object] = []

    monkeypatch.setattr(
        "lowkey_artifact_builder.cli._main.configure_logging",
        configured_levels.append,
    )

    runner = CliRunner()

    result = runner.invoke(
        cli,
        [
            "--quiet",
            "--log-level=INFO",
        ],
    )

    assert result.exit_code == 0
    assert configured_levels == ["INFO"]


@pytest.mark.parametrize(
    "args",
    [
        ["--verbose"],
        ["--very-verbose"],
        ["--quiet"],
    ],
)
def test_cli_accepts_semantic_messaging_options(args) -> None:
    runner = CliRunner()

    result = runner.invoke(
        cli,
        args,
    )

    assert result.exit_code == 0


@pytest.mark.parametrize(
    "args",
    [
        ["--quiet", "--verbose"],
        ["--quiet", "--very-verbose"],
        ["--verbose", "--very-verbose"],
    ],
)
def test_cli_rejects_conflicting_semantic_messaging_options(args) -> None:
    runner = CliRunner()

    result = runner.invoke(
        cli,
        args,
    )

    assert result.exit_code != 0
