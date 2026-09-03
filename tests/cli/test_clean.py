"""
Tests for the artifact clean command.
"""
# File: tests/cli/test_clean.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path
from typing import Any

from click.testing import CliRunner

import lowkey_artifact_builder.cli.cmd_clean as cmd_clean
from lowkey_artifact_builder.cli._main import cli

# =========================================================
# Helpers
# =========================================================


def _invoke(
    *args: str,
) -> Any:
    """
    Invoke the artifact clean command.
    """

    runner = CliRunner()

    return runner.invoke(
        cli,
        [
            "clean",
            *args,
        ],
    )


# =========================================================
# Argument validation
# =========================================================


def test_clean_requires_artifact_id() -> None:
    """
    Artifact cleaning requires exactly one artifact ID.
    """

    result = _invoke()

    assert result.exit_code != 0
    assert "artifact" in result.output.lower()


def test_clean_rejects_multiple_artifact_ids() -> None:
    """
    Artifact cleaning operates on one artifact at a time.
    """

    result = _invoke(
        "skippy",
        "scooby",
    )

    assert result.exit_code != 0


# =========================================================
# Artifact existence
# =========================================================


def test_clean_rejects_undefined_artifact(
    monkeypatch,
) -> None:
    """
    Cleaning requires an existing persistent artifact definition.
    """

    monkeypatch.setattr(
        cmd_clean,
        "load_artifact_config",
        lambda *args, **kwargs: {},
    )

    result = _invoke(
        "skippy",
    )

    assert result.exit_code != 0
    assert "not defined" in result.output.lower()


# =========================================================
# Cleaning
# =========================================================


def test_clean_delegates_to_artifact_api(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    The CLI delegates cleaning to the artifact lifecycle API.

    Filesystem ownership and deletion semantics belong below the CLI
    boundary.
    """

    calls: list[tuple[str, Path]] = []

    monkeypatch.chdir(tmp_path)

    monkeypatch.setattr(
        cmd_clean,
        "load_artifact_config",
        lambda *args, **kwargs: {
            "model": "artwork",
        },
    )

    monkeypatch.setattr(
        cmd_clean,
        "clean_artifact",
        lambda artifact_id, *, project_root: calls.append(
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
    assert calls == [
        (
            "skippy",
            tmp_path,
        ),
    ]
