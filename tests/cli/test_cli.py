"""Tests for the main artifact CLI entry point."""

from click.testing import CliRunner

from lowkey_artifact_builder.cli._main import cli


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


def test_cli_config_help() -> None:
    """The config command displays help successfully."""

    runner = CliRunner()

    result = runner.invoke(
        cli,
        ["config", "--help"],
    )

    assert result.exit_code == 0
    assert "Usage:" in result.output
