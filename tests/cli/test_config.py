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

# =========================================================
# Helpers
# =========================================================


def _invoke(
    *args: str,
) -> Any:
    """
    Invoke the artifact CLI.
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
# Artifact inspection
# =========================================================


def test_config_requires_artifact_id() -> None:
    """
    Artifact configuration requires an artifact ID unless performing
    model inspection.
    """

    result = _invoke()

    assert result.exit_code != 0
    assert "artifact" in result.output.lower()


def test_config_displays_existing_artifact(
    monkeypatch,
) -> None:
    """
    Supplying only an artifact ID displays its configuration.
    """

    displayed: list[str] = []

    monkeypatch.setattr(
        cmd_config,
        "_display_artifact",
        lambda artifact_id, **kwargs: displayed.append(
            artifact_id,
        ),
    )

    result = _invoke(
        "skippy",
    )

    assert result.exit_code == 0
    assert displayed == ["skippy"]


def test_config_missing_artifact_reports_error(
    monkeypatch,
) -> None:
    """
    An undefined artifact produces a user-facing error.
    """

    def missing_artifact(
        artifact_id: str,
        **kwargs: Any,
    ) -> None:
        raise cmd_config.click.ClickException(f"Artifact {artifact_id!r} is not defined.")

    monkeypatch.setattr(
        cmd_config,
        "_display_artifact",
        missing_artifact,
    )

    result = _invoke(
        "skippy",
    )

    assert result.exit_code != 0
    assert "Artifact 'skippy' is not defined." in result.output


# =========================================================
# Artifact configuration
# =========================================================


def test_config_input_artwork_delegates_to_api(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    --input-artwork-file delegates artifact configuration to the
    high-level configuration API.
    """

    source = tmp_path / "skippy.png"
    source.write_bytes(b"artwork")

    calls: list[
        tuple[
            str,
            dict[str, Path],
        ]
    ] = []

    def configure(
        artifact_id: str,
        *,
        input_files: dict[str, Path],
        project_root: Path,
        **kwargs: Any,
    ) -> None:
        calls.append(
            (
                artifact_id,
                input_files,
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
        "--input-artwork-file",
        str(source),
    )

    assert result.exit_code == 0

    assert calls == [
        (
            "skippy",
            {
                "artwork": source,
            },
        ),
    ]


def test_config_input_artwork_displays_result(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    Artifact configuration is displayed after an update.
    """

    source = tmp_path / "skippy.png"
    source.write_bytes(b"artwork")

    displayed: list[str] = []

    monkeypatch.setattr(
        cmd_config,
        "configure_artifact",
        lambda *args, **kwargs: None,
    )

    monkeypatch.setattr(
        cmd_config,
        "_display_artifact",
        lambda artifact_id, **kwargs: displayed.append(
            artifact_id,
        ),
    )

    result = _invoke(
        "skippy",
        "--input-artwork-file",
        str(source),
    )

    assert result.exit_code == 0
    assert displayed == ["skippy"]


def test_config_input_artwork_passes_project_root(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    Artifact configuration uses the current project root.
    """

    source = tmp_path / "skippy.png"
    source.write_bytes(b"artwork")

    roots: list[Path] = []

    def configure(
        artifact_id: str,
        *,
        input_files: dict[str, Path],
        project_root: Path,
        **kwargs: Any,
    ) -> None:
        roots.append(project_root)

    monkeypatch.chdir(tmp_path)

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
        "--input-artwork-file",
        str(source),
    )

    assert result.exit_code == 0
    assert roots == [tmp_path]


def test_config_input_artwork_does_not_use_interactive_setup(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    Supplying an artwork input does not invoke interactive artifact
    setup.
    """

    source = tmp_path / "skippy.png"
    source.write_bytes(b"artwork")

    def unexpected_setup(
        *args: Any,
        **kwargs: Any,
    ) -> None:
        raise AssertionError("interactive setup must not be invoked")

    monkeypatch.setattr(
        cmd_config,
        "setup_artifact",
        unexpected_setup,
        raising=False,
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
        "--input-artwork-file",
        str(source),
    )

    assert result.exit_code == 0


# =========================================================
# Argument validation
# =========================================================


def test_config_rejects_multiple_artifact_ids() -> None:
    """
    Artifact configuration operates on exactly one artifact at a time.
    """

    result = _invoke(
        "skippy",
        "scooby",
    )

    assert result.exit_code != 0


def test_config_input_artwork_requires_existing_file(
    tmp_path: Path,
) -> None:
    """
    Click rejects a nonexistent external artwork file before invoking
    configuration.
    """

    source = tmp_path / "missing.png"

    result = _invoke(
        "skippy",
        "--input-artwork-file",
        str(source),
    )

    assert result.exit_code != 0
    assert "does not exist" in result.output.lower()
