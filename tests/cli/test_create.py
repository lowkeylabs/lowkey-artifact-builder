"""
Tests for the artifact create command.
"""
# File: tests/cli/test_create.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path
from typing import Any

from click.testing import CliRunner

import lowkey_artifact_builder.cli.cmd_create as cmd_create
from lowkey_artifact_builder.cli._main import cli
from lowkey_artifact_builder.cli.setup import ArtifactSetup


def _invoke(
    *args: str,
) -> Any:
    """
    Invoke the artifact create command.
    """

    runner = CliRunner()

    return runner.invoke(
        cli,
        [
            "create",
            *args,
        ],
    )


# =========================================================
# Command
# =========================================================


def test_create_is_a_top_level_command() -> None:
    """
    Artifact creation is exposed as a distinct lifecycle operation.
    """

    runner = CliRunner()

    result = runner.invoke(
        cli,
        ["--help"],
    )

    assert result.exit_code == 0
    assert "create" in result.output


def test_create_requires_exactly_one_artifact_id() -> None:
    """
    Artifact creation operates on one explicitly named artifact.
    """

    missing = _invoke()

    assert missing.exit_code != 0

    multiple = _invoke(
        "skippy",
        "scooby",
    )

    assert multiple.exit_code != 0


# =========================================================
# Lifecycle
# =========================================================


def test_create_rejects_existing_artifact(
    monkeypatch,
) -> None:
    """
    Creation does not silently become configuration of an existing artifact.
    """

    monkeypatch.setattr(
        cmd_create,
        "load_artifact_config",
        lambda *args, **kwargs: {
            "model": "artwork",
        },
    )

    def unexpected_setup(
        *args: Any,
        **kwargs: Any,
    ) -> None:
        raise AssertionError("existing artifact must not enter creation setup")

    monkeypatch.setattr(
        cmd_create,
        "setup_artifact",
        unexpected_setup,
    )

    result = _invoke(
        "skippy",
    )

    assert result.exit_code != 0
    assert "already" in result.output.lower()
    assert "defined" in result.output.lower()


# =========================================================
# Setup
# =========================================================


def test_create_without_parameters_enters_setup_with_no_initial_values(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    Creation without command-line configuration delegates unresolved
    configuration to setup.
    """

    monkeypatch.chdir(
        tmp_path,
    )

    monkeypatch.setattr(
        cmd_create,
        "load_artifact_config",
        lambda *args, **kwargs: {},
    )

    setup_calls: list[
        tuple[
            str,
            dict[str, object],
            Path,
        ]
    ] = []

    def setup(
        artifact_id: str,
        registry,
        *,
        values: dict[str, object],
        project_root: Path,
    ) -> ArtifactSetup:
        setup_calls.append(
            (
                artifact_id,
                values,
                project_root,
            )
        )

        return ArtifactSetup(
            artifact_id=artifact_id,
            model="artwork",
            values={
                "source": "skippy.png",
                "artwork_size": 70.0,
            },
        )

    monkeypatch.setattr(
        cmd_create,
        "setup_artifact",
        setup,
    )

    monkeypatch.setattr(
        cmd_create,
        "configure_artifact",
        lambda *args, **kwargs: None,
    )

    monkeypatch.setattr(
        cmd_create,
        "_display_artifact",
        lambda *args, **kwargs: None,
    )

    result = _invoke(
        "skippy",
    )

    assert result.exit_code == 0

    assert setup_calls == [
        (
            "skippy",
            {},
            tmp_path,
        ),
    ]


def test_create_passes_supplied_parameters_to_setup(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    Command-line configuration is initial setup configuration.

    Setup remains responsible for resolving that configuration and
    collecting anything still required.
    """

    monkeypatch.chdir(
        tmp_path,
    )

    monkeypatch.setattr(
        cmd_create,
        "load_artifact_config",
        lambda *args, **kwargs: {},
    )

    supplied: list[dict[str, object]] = []

    def setup(
        artifact_id: str,
        registry,
        *,
        values: dict[str, object],
        project_root: Path,
    ) -> ArtifactSetup:
        supplied.append(dict(values))

        return ArtifactSetup(
            artifact_id=artifact_id,
            model="artwork",
            values={
                **values,
                "source": "skippy.png",
            },
        )

    monkeypatch.setattr(
        cmd_create,
        "setup_artifact",
        setup,
    )

    monkeypatch.setattr(
        cmd_create,
        "configure_artifact",
        lambda *args, **kwargs: None,
    )

    monkeypatch.setattr(
        cmd_create,
        "_display_artifact",
        lambda *args, **kwargs: None,
    )

    result = _invoke(
        "skippy",
        "--param",
        "model=artwork",
        "--param",
        "artwork_size=70",
    )

    assert result.exit_code == 0

    assert supplied == [
        {
            "model": "artwork",
            "artwork_size": 70,
        },
    ]


def test_create_complete_parameters_require_no_additional_configuration(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    Complete command-line configuration can pass through setup without
    requiring additional values.
    """

    source = tmp_path / "skippy.png"
    source.write_bytes(
        b"artwork",
    )

    monkeypatch.chdir(
        tmp_path,
    )

    monkeypatch.setattr(
        cmd_create,
        "load_artifact_config",
        lambda *args, **kwargs: {},
    )

    setup_calls: list[dict[str, object]] = []

    def setup(
        artifact_id: str,
        registry,
        *,
        values: dict[str, object],
        project_root: Path,
    ) -> ArtifactSetup:
        setup_calls.append(dict(values))

        return ArtifactSetup(
            artifact_id=artifact_id,
            model="artwork",
            values=dict(values),
        )

    monkeypatch.setattr(
        cmd_create,
        "setup_artifact",
        setup,
    )

    configured: list[
        tuple[
            dict[str, Any],
            dict[str, Path],
        ]
    ] = []

    def configure(
        artifact_id: str,
        *,
        values: dict[str, Any],
        input_files: dict[str, Path],
        project_root: Path,
    ) -> None:
        configured.append(
            (
                values,
                input_files,
            )
        )

    monkeypatch.setattr(
        cmd_create,
        "configure_artifact",
        configure,
    )

    monkeypatch.setattr(
        cmd_create,
        "_display_artifact",
        lambda *args, **kwargs: None,
    )

    result = _invoke(
        "skippy",
        "--param",
        "model=artwork",
        "--param",
        "source=skippy.png",
        "--param",
        "artwork_size=70",
    )

    assert result.exit_code == 0

    assert setup_calls == [
        {
            "model": "artwork",
            "source": "skippy.png",
            "artwork_size": 70,
        },
    ]

    assert configured == [
        (
            {
                "artwork_size": 70,
                "model": "artwork",
            },
            {
                "artwork": source,
            },
        ),
    ]


# =========================================================
# Parameter bindings
# =========================================================


def test_create_rejects_invalid_parameter_binding(
    monkeypatch,
) -> None:
    """
    Invalid creation parameter syntax is reported as a command error.
    """

    monkeypatch.setattr(
        cmd_create,
        "load_artifact_config",
        lambda *args, **kwargs: {},
    )

    result = _invoke(
        "skippy",
        "--param",
        "artwork_size",
    )

    assert result.exit_code != 0
    assert "NAME=VALUE" in result.output
