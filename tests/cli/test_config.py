"""
Tests for the artifact config command.
"""
# File: tests/cli/test_config.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path
from typing import Any

from click.testing import CliRunner

import lowkey_artifact_builder.cli.cmd_config as cmd_config
from lowkey_artifact_builder.cli._main import cli
from lowkey_artifact_builder.cli.setup import (
    ArtifactSetup,
)

# =========================================================
# Helpers
# =========================================================


def _invoke(
    *args: str,
) -> Any:
    """
    Invoke the artifact config command.
    """

    runner = CliRunner()

    return runner.invoke(
        cli,
        [
            "config",
            *args,
        ],
    )


# =========================================================
# Argument validation
# =========================================================


def test_config_requires_artifact_id() -> None:
    """
    Artifact configuration requires an artifact ID unless performing
    model inspection.
    """

    result = _invoke()

    assert result.exit_code != 0
    assert "artifact" in result.output.lower()


def test_config_rejects_multiple_artifact_ids() -> None:
    """
    Artifact configuration operates on exactly one artifact at a time.
    """

    result = _invoke(
        "skippy",
        "scooby",
    )

    assert result.exit_code != 0


# =========================================================
# Existing artifact
# =========================================================


def test_config_displays_existing_artifact(
    monkeypatch,
) -> None:
    """
    Supplying an existing artifact ID displays its configuration
    without invoking interactive setup.
    """

    displayed: list[str] = []

    monkeypatch.setattr(
        cmd_config,
        "load_artifact_config",
        lambda *args, **kwargs: {
            "model": "artwork",
        },
    )

    def unexpected_setup(
        *args: Any,
        **kwargs: Any,
    ) -> None:
        raise AssertionError("interactive setup must not be invoked")

    monkeypatch.setattr(
        cmd_config,
        "setup_artifact",
        unexpected_setup,
    )

    monkeypatch.setattr(
        cmd_config,
        "_display_artifact",
        lambda artifact_id, **kwargs: displayed.append(artifact_id),
    )

    result = _invoke(
        "skippy",
    )

    assert result.exit_code == 0
    assert displayed == ["skippy"]


# =========================================================
# Interactive configuration
# =========================================================


def test_config_new_artifact_uses_interactive_setup(
    monkeypatch,
) -> None:
    """
    An undefined artifact delegates configuration discovery to the
    interactive setup service.
    """

    setup_calls: list[str] = []

    monkeypatch.setattr(
        cmd_config,
        "load_artifact_config",
        lambda *args, **kwargs: {},
    )

    def setup(
        artifact_id: str,
        registry,
        *,
        project_root: Path,
    ) -> ArtifactSetup:
        setup_calls.append(artifact_id)

        return ArtifactSetup(
            artifact_id=artifact_id,
            model="artwork",
            values={},
        )

    monkeypatch.setattr(
        cmd_config,
        "setup_artifact",
        setup,
    )

    monkeypatch.setattr(
        cmd_config,
        "configure_artifact",
        lambda *args, **kwargs: None,
    )

    monkeypatch.setattr(
        cmd_config,
        "_display_artifact",
        lambda *args, **kwargs: None,
    )

    result = _invoke(
        "skippy",
    )

    assert result.exit_code == 0
    assert setup_calls == ["skippy"]


def test_config_passes_project_root_to_setup(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    Interactive setup uses the current project root.
    """

    roots: list[Path] = []

    monkeypatch.chdir(tmp_path)

    monkeypatch.setattr(
        cmd_config,
        "load_artifact_config",
        lambda *args, **kwargs: {},
    )

    def setup(
        artifact_id: str,
        registry,
        *,
        project_root: Path,
    ) -> ArtifactSetup:
        roots.append(project_root)

        return ArtifactSetup(
            artifact_id=artifact_id,
            model="artwork",
            values={},
        )

    monkeypatch.setattr(
        cmd_config,
        "setup_artifact",
        setup,
    )

    monkeypatch.setattr(
        cmd_config,
        "configure_artifact",
        lambda *args, **kwargs: None,
    )

    monkeypatch.setattr(
        cmd_config,
        "_display_artifact",
        lambda *args, **kwargs: None,
    )

    result = _invoke(
        "skippy",
    )

    assert result.exit_code == 0
    assert roots == [tmp_path]


# =========================================================
# Setup translation
# =========================================================


def test_config_translates_setup_to_artifact_api(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    Setup values are delegated to the high-level artifact API.

    The selected model is persisted as configuration while the external
    source is translated into the semantic artwork input.
    """

    source = tmp_path / "skippy.png"
    source.write_bytes(b"artwork")

    monkeypatch.chdir(tmp_path)

    monkeypatch.setattr(
        cmd_config,
        "load_artifact_config",
        lambda *args, **kwargs: {},
    )

    monkeypatch.setattr(
        cmd_config,
        "setup_artifact",
        lambda *args, **kwargs: ArtifactSetup(
            artifact_id="skippy",
            model="artwork",
            values={
                "source": "skippy.png",
                "artwork_size": 70.0,
            },
        ),
    )

    calls: list[
        tuple[
            str,
            dict[str, Any],
            dict[str, Path],
            Path,
        ]
    ] = []

    def configure(
        artifact_id: str,
        *,
        values: dict[str, Any],
        input_files: dict[str, Path],
        project_root: Path,
    ) -> None:
        calls.append(
            (
                artifact_id,
                values,
                input_files,
                project_root,
            )
        )

    monkeypatch.setattr(
        cmd_config,
        "configure_artifact",
        configure,
    )

    monkeypatch.setattr(
        cmd_config,
        "_display_artifact",
        lambda *args, **kwargs: None,
    )

    result = _invoke(
        "skippy",
    )

    assert result.exit_code == 0

    assert calls == [
        (
            "skippy",
            {
                "artwork_size": 70.0,
                "model": "artwork",
            },
            {
                "artwork": source,
            },
            tmp_path,
        ),
    ]


def test_config_source_is_not_persisted_as_value(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    An external source collected by setup is passed as an artifact input
    rather than persisted directly as a configuration value.
    """

    source = tmp_path / "skippy.png"
    source.write_bytes(b"artwork")

    monkeypatch.chdir(tmp_path)

    monkeypatch.setattr(
        cmd_config,
        "load_artifact_config",
        lambda *args, **kwargs: {},
    )

    monkeypatch.setattr(
        cmd_config,
        "setup_artifact",
        lambda *args, **kwargs: ArtifactSetup(
            artifact_id="skippy",
            model="artwork",
            values={
                "source": "skippy.png",
                "artwork_size": 70.0,
            },
        ),
    )

    configured_values: list[dict[str, Any]] = []

    def configure(
        artifact_id: str,
        *,
        values: dict[str, Any],
        **kwargs: Any,
    ) -> None:
        configured_values.append(values)

    monkeypatch.setattr(
        cmd_config,
        "configure_artifact",
        configure,
    )

    monkeypatch.setattr(
        cmd_config,
        "_display_artifact",
        lambda *args, **kwargs: None,
    )

    result = _invoke(
        "skippy",
    )

    assert result.exit_code == 0

    assert configured_values == [
        {
            "artwork_size": 70.0,
            "model": "artwork",
        },
    ]

    assert "source" not in configured_values[0]


def test_config_without_source_passes_no_input_files(
    monkeypatch,
) -> None:
    """
    Setup results without an external source require no input
    materialization.
    """

    monkeypatch.setattr(
        cmd_config,
        "load_artifact_config",
        lambda *args, **kwargs: {},
    )

    monkeypatch.setattr(
        cmd_config,
        "setup_artifact",
        lambda *args, **kwargs: ArtifactSetup(
            artifact_id="skippy",
            model="artwork",
            values={
                "artwork_size": 70.0,
            },
        ),
    )

    inputs: list[dict[str, Path]] = []

    def configure(
        artifact_id: str,
        *,
        input_files: dict[str, Path],
        **kwargs: Any,
    ) -> None:
        inputs.append(input_files)

    monkeypatch.setattr(
        cmd_config,
        "configure_artifact",
        configure,
    )

    monkeypatch.setattr(
        cmd_config,
        "_display_artifact",
        lambda *args, **kwargs: None,
    )

    result = _invoke(
        "skippy",
    )

    assert result.exit_code == 0
    assert inputs == [{}]


# =========================================================
# Result display
# =========================================================


def test_config_displays_new_artifact_after_configuration(
    monkeypatch,
) -> None:
    """
    A newly configured artifact is displayed after persistence.
    """

    displayed: list[str] = []

    monkeypatch.setattr(
        cmd_config,
        "load_artifact_config",
        lambda *args, **kwargs: {},
    )

    monkeypatch.setattr(
        cmd_config,
        "setup_artifact",
        lambda *args, **kwargs: ArtifactSetup(
            artifact_id="skippy",
            model="artwork",
            values={},
        ),
    )

    monkeypatch.setattr(
        cmd_config,
        "configure_artifact",
        lambda *args, **kwargs: None,
    )

    monkeypatch.setattr(
        cmd_config,
        "_display_artifact",
        lambda artifact_id, **kwargs: displayed.append(artifact_id),
    )

    result = _invoke(
        "skippy",
    )

    assert result.exit_code == 0
    assert displayed == ["skippy"]


# =========================================================
# Configuration errors
# =========================================================


def test_config_api_error_is_reported(
    monkeypatch,
) -> None:
    """
    Configuration API errors are presented as Click command errors.
    """

    monkeypatch.setattr(
        cmd_config,
        "load_artifact_config",
        lambda *args, **kwargs: {},
    )

    monkeypatch.setattr(
        cmd_config,
        "setup_artifact",
        lambda *args, **kwargs: ArtifactSetup(
            artifact_id="skippy",
            model="artwork",
            values={},
        ),
    )

    def configure(
        *args: Any,
        **kwargs: Any,
    ) -> None:
        raise cmd_config.ConfigError("cannot configure artifact")

    monkeypatch.setattr(
        cmd_config,
        "configure_artifact",
        configure,
    )

    result = _invoke(
        "skippy",
    )

    assert result.exit_code != 0
    assert "cannot configure artifact" in result.output


def test_config_rejects_undefined_artifact(
    monkeypatch,
) -> None:
    """
    Configuration does not implicitly create an undefined artifact.

    Artifact creation is a distinct lifecycle operation owned by
    `artifact create`.
    """

    monkeypatch.setattr(
        cmd_config,
        "load_artifact_config",
        lambda *args, **kwargs: {},
    )

    def unexpected_setup(
        *args: Any,
        **kwargs: Any,
    ) -> None:
        raise AssertionError("config must not create an artifact")

    monkeypatch.setattr(
        cmd_config,
        "setup_artifact",
        unexpected_setup,
    )

    result = _invoke(
        "skippy",
    )

    assert result.exit_code != 0
    assert "not defined" in result.output.lower()
