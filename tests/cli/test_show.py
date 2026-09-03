"""
Tests for the artifact show command.
"""
# File: tests/cli/test_show.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path
from typing import Any

from click.testing import CliRunner

import lowkey_artifact_builder.cli.cmd_show as cmd_show
from lowkey_artifact_builder.cli._main import cli

# =========================================================
# Helpers
# =========================================================


def _invoke(
    *args: str,
) -> Any:
    """
    Invoke the artifact show command.
    """

    runner = CliRunner()

    return runner.invoke(
        cli,
        [
            "show",
            *args,
        ],
    )


# =========================================================
# Argument validation
# =========================================================


def test_show_requires_artifact_id() -> None:
    """
    Artifact inspection requires exactly one artifact ID.
    """

    result = _invoke()

    assert result.exit_code != 0
    assert "artifact" in result.output.lower()


def test_show_rejects_multiple_artifact_ids() -> None:
    """
    Artifact inspection operates on one artifact at a time.
    """

    result = _invoke(
        "skippy",
        "scooby",
    )

    assert result.exit_code != 0


# =========================================================
# Artifact existence
# =========================================================


def test_show_rejects_undefined_artifact(
    monkeypatch,
) -> None:
    """
    Artifact inspection requires an existing artifact definition.
    """

    monkeypatch.setattr(
        cmd_show,
        "load_artifact_config",
        lambda *args, **kwargs: {},
    )

    result = _invoke(
        "skippy",
    )

    assert result.exit_code != 0
    assert "not defined" in result.output.lower()


# =========================================================
# Artifact inspection
# =========================================================


def test_show_displays_existing_artifact(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    Show displays resolved configuration for an existing artifact.
    """

    displayed: list[tuple[str, Path]] = []

    monkeypatch.chdir(tmp_path)

    monkeypatch.setattr(
        cmd_show,
        "load_artifact_config",
        lambda *args, **kwargs: {
            "model": "artwork",
        },
    )

    monkeypatch.setattr(
        cmd_show,
        "_display_artifact",
        lambda artifact_id, *, project_root: displayed.append(
            (
                artifact_id,
                project_root,
            )
        ),
    )

    result = _invoke(
        "skippy",
    )

    assert result.exit_code == 0
    assert displayed == [
        (
            "skippy",
            tmp_path,
        ),
    ]
