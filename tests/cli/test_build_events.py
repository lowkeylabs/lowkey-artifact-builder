"""
Tests for build-command execution observation.

Normal graph-driven CLI builds delegate artifact orchestration to the
artifact-level engine boundary and supply its semantic execution-event
observer. Dry-run remains planning-only.
"""
# File: tests/cli/test_build_events.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from click.testing import CliRunner

import lowkey_artifact_builder.cli.cmd_build as cmd_build
from lowkey_artifact_builder.cli._main import cli

# =========================================================
# Helpers
# =========================================================


def _plan(
    artifact_id: str = "example",
):
    """
    Return the minimal realized-plan identity needed by dry-run display.
    """

    return SimpleNamespace(
        artifact_id=artifact_id,
        model_name="artwork",
        realization_name="default",
    )


def _install_plans(
    monkeypatch: pytest.MonkeyPatch,
    *plans,
) -> None:
    """
    Replace dry-run planning with deterministic realized plans.
    """

    def create_build_plans(
        artifact_id: str,
        *,
        project_root: Path,
    ):
        assert artifact_id == "example"

        return plans

    monkeypatch.setattr(
        cmd_build,
        "create_build_plans",
        create_build_plans,
    )


# =========================================================
# Artifact execution
# =========================================================


def test_build_command_delegates_artifact_execution_to_engine(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Normal CLI builds delegate artifact orchestration to the engine.
    """

    monkeypatch.chdir(
        tmp_path,
    )

    executed: list[str] = []

    def execute_artifact_build(
        artifact_id: str,
        *,
        project_root: Path,
        event_sink=None,
    ):
        executed.append(
            artifact_id,
        )

    monkeypatch.setattr(
        cmd_build,
        "execute_artifact_build",
        execute_artifact_build,
    )

    result = CliRunner().invoke(
        cli,
        [
            "build",
            "example",
        ],
    )

    assert result.exit_code == 0, result.output or repr(result.exception)

    assert executed == [
        "example",
    ]


def test_build_command_does_not_expose_lower_level_build_executors() -> None:
    """
    Normal CLI builds do not depend on lower-level build executors.
    """

    assert not hasattr(
        cmd_build,
        "execute_builds",
    )

    assert not hasattr(
        cmd_build,
        "execute_incremental_artifact_build",
    )


def test_build_command_supplies_event_sink_to_artifact_execution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Artifact execution receives the CLI execution-event observer.
    """

    monkeypatch.chdir(
        tmp_path,
    )

    observed_sink = None

    def execute_artifact_build(
        artifact_id: str,
        *,
        project_root: Path,
        event_sink=None,
    ):
        nonlocal observed_sink

        assert artifact_id == "example"
        assert project_root == tmp_path

        observed_sink = event_sink

    monkeypatch.setattr(
        cmd_build,
        "execute_artifact_build",
        execute_artifact_build,
    )

    result = CliRunner().invoke(
        cli,
        [
            "build",
            "example",
        ],
    )

    assert result.exit_code == 0, result.output or repr(result.exception)

    assert observed_sink is not None


# =========================================================
# Dry run
# =========================================================


def test_dry_run_does_not_execute_artifact_build(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Dry-run remains planning-only at the artifact execution boundary.
    """

    monkeypatch.chdir(
        tmp_path,
    )

    plan = _plan()

    _install_plans(
        monkeypatch,
        plan,
    )

    executed = False

    def execute_artifact_build(
        artifact_id: str,
        *,
        project_root: Path,
        event_sink=None,
    ):
        nonlocal executed

        executed = True

    monkeypatch.setattr(
        cmd_build,
        "execute_artifact_build",
        execute_artifact_build,
    )

    monkeypatch.setattr(
        cmd_build,
        "display_build_plan",
        lambda plan: None,
    )

    result = CliRunner().invoke(
        cli,
        [
            "build",
            "example",
            "--dry-run",
        ],
    )

    assert result.exit_code == 0, result.output or repr(result.exception)

    assert not executed
