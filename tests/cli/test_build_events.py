"""
Tests for build-command execution observation.

Explicit graph-driven CLI builds delegate artifact orchestration to the
artifact-level engine boundary and supply its semantic execution-event
observer. Dry-run prepares and validates explicitly selected Realization
execution without entering artifact execution.
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
    Return the minimal realized-plan identity needed by CLI boundary tests.
    """

    return SimpleNamespace(
        artifact_id=artifact_id,
        model_name="artwork",
        realization_name="artwork_default",
    )


def _install_plans(
    monkeypatch: pytest.MonkeyPatch,
    *plans,
) -> None:
    """
    Replace dry-run artifact build-plan creation with deterministic
    realized plans.
    """

    def create_artifact_build_plans(
        artifact_id: str,
        *,
        realization: str,
        project_root: Path,
    ):
        assert artifact_id == "example"
        assert realization == "artwork_default"

        return plans

    monkeypatch.setattr(
        cmd_build,
        "create_artifact_build_plans",
        create_artifact_build_plans,
    )


# =========================================================
# Artifact execution
# =========================================================


def test_build_command_delegates_artifact_execution_to_engine(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Explicit CLI builds delegate Artifact + Realization orchestration
    to the engine.
    """

    monkeypatch.chdir(
        tmp_path,
    )

    executed: list[tuple[str, str]] = []

    def execute_artifact_build(
        artifact_id: str,
        *,
        realization: str,
        project_root: Path,
        event_sink=None,
    ) -> None:
        executed.append(
            (
                artifact_id,
                realization,
            )
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
            "--realization",
            "artwork_default",
        ],
    )

    assert result.exit_code == 0, result.output or repr(result.exception)

    assert executed == [
        (
            "example",
            "artwork_default",
        ),
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
    Explicit Artifact + Realization execution receives the CLI
    execution-event observer.
    """

    monkeypatch.chdir(
        tmp_path,
    )

    observed_sink = None

    def execute_artifact_build(
        artifact_id: str,
        *,
        realization: str,
        project_root: Path,
        event_sink=None,
    ) -> None:
        nonlocal observed_sink

        assert artifact_id == "example"
        assert realization == "artwork_default"
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
            "--realization",
            "artwork_default",
        ],
    )

    assert result.exit_code == 0, result.output or repr(result.exception)

    assert observed_sink is not None


# =========================================================
# Dry run
# =========================================================


def test_dry_run_prepares_build_without_executing_artifact_build(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Explicit Realization dry-run prepares the realized build without
    executing it.
    """

    monkeypatch.chdir(
        tmp_path,
    )

    plan = _plan()

    _install_plans(
        monkeypatch,
        plan,
    )

    prepared: list[object] = []
    executed = False

    def prepare_incremental_build(
        build_plan: object,
    ) -> object:
        prepared.append(
            build_plan,
        )

        return object()

    monkeypatch.setattr(
        cmd_build,
        "prepare_incremental_build",
        prepare_incremental_build,
    )

    def execute_artifact_build(
        artifact_id: str,
        *,
        realization: str,
        project_root: Path,
        event_sink=None,
    ) -> None:
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
            "--realization",
            "artwork_default",
            "--dry-run",
        ],
    )

    assert result.exit_code == 0, result.output or repr(result.exception)

    assert prepared == [
        plan,
    ]

    assert not executed
