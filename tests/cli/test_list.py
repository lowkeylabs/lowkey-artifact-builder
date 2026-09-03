"""
Tests for the artifact list command.
"""
# File: tests/cli/test_list.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path
from typing import Any

from click.testing import CliRunner

import lowkey_artifact_builder.cli.cmd_list as cmd_list
from lowkey_artifact_builder.cli._main import cli

# =========================================================
# Helpers
# =========================================================


def _invoke(
    *args: str,
) -> Any:
    """
    Invoke the artifact list command.
    """

    runner = CliRunner()

    return runner.invoke(
        cli,
        [
            "list",
            *args,
        ],
    )


# =========================================================
# Argument validation
# =========================================================


def test_list_rejects_artifact_ids() -> None:
    """
    Artifact listing is workspace-wide and accepts no artifact ID.
    """

    result = _invoke(
        "skippy",
    )

    assert result.exit_code != 0


# =========================================================
# Discovery
# =========================================================


def test_list_discovers_artifacts_from_project_root(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    Artifact listing delegates workspace discovery to the artifact API.
    """

    roots: list[Path] = []

    monkeypatch.chdir(tmp_path)

    def discover(
        *,
        project_root: Path,
    ) -> tuple[str, ...]:
        roots.append(project_root)

        return (
            "skippy",
            "scooby",
        )

    monkeypatch.setattr(
        cmd_list,
        "list_artifacts",
        discover,
    )

    result = _invoke()

    assert result.exit_code == 0
    assert roots == [tmp_path]


def test_list_displays_discovered_artifact_ids(
    monkeypatch,
) -> None:
    """
    Every discovered artifact ID is presented to the user.
    """

    monkeypatch.setattr(
        cmd_list,
        "list_artifacts",
        lambda **kwargs: (
            "skippy",
            "scooby",
        ),
    )

    result = _invoke()

    assert result.exit_code == 0
    assert "skippy" in result.output
    assert "scooby" in result.output


def test_list_succeeds_when_no_artifacts_exist(
    monkeypatch,
) -> None:
    """
    An empty workspace is a valid artifact-listing result.
    """

    monkeypatch.setattr(
        cmd_list,
        "list_artifacts",
        lambda **kwargs: (),
    )

    result = _invoke()

    assert result.exit_code == 0
