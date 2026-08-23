"""Tests for the main artifact CLI entry point."""

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
