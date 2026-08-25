"""
Tests for build-command incremental execution observation.

Normal graph-driven CLI builds should execute realized build plans through
the incremental artifact execution boundary and consume its semantic
execution events.
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
    Return the minimal realized-plan identity needed by this CLI slice.
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
    Replace graph planning with deterministic realized plans.
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
# Incremental artifact execution
# =========================================================


def test_build_command_executes_each_plan_incrementally(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Normal CLI builds execute each realized plan incrementally.
    """

    monkeypatch.chdir(
        tmp_path,
    )

    first = _plan(
        "example",
    )

    second = _plan(
        "example",
    )

    _install_plans(
        monkeypatch,
        first,
        second,
    )

    executed = []

    def execute_incremental_artifact_build(
        plan,
        *,
        event_sink=None,
    ):
        executed.append(
            plan,
        )

    monkeypatch.setattr(
        cmd_build,
        "execute_incremental_artifact_build",
        execute_incremental_artifact_build,
        raising=False,
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
        first,
        second,
    ]


def test_build_command_does_not_expose_legacy_build_executor() -> None:
    """
    Normal CLI builds no longer depend on the legacy build executor.
    """

    assert not hasattr(
        cmd_build,
        "execute_builds",
    )


def test_build_command_supplies_event_sink_to_incremental_execution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    CLI incremental execution supplies an execution-event observer.
    """

    monkeypatch.chdir(
        tmp_path,
    )

    plan = _plan()

    _install_plans(
        monkeypatch,
        plan,
    )

    observed_sink = None

    def execute_incremental_artifact_build(
        plan,
        *,
        event_sink=None,
    ):
        nonlocal observed_sink

        observed_sink = event_sink

    monkeypatch.setattr(
        cmd_build,
        "execute_incremental_artifact_build",
        execute_incremental_artifact_build,
        raising=False,
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


def test_dry_run_does_not_execute_incremental_build(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Dry-run remains planning-only after incremental migration.
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

    def execute_incremental_artifact_build(
        plan,
        *,
        event_sink=None,
    ):
        nonlocal executed

        executed = True

    monkeypatch.setattr(
        cmd_build,
        "execute_incremental_artifact_build",
        execute_incremental_artifact_build,
        raising=False,
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
