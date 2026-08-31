"""
Tests for the artifact build command.
"""
# File: tests/cli/test_build.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path
from typing import Any

from click.testing import CliRunner

import lowkey_artifact_builder.cli.cmd_build as cmd_build
from lowkey_artifact_builder.cli._main import cli

# =========================================================
# Helpers
# =========================================================


def _invoke(
    *args: str,
) -> Any:
    """
    Invoke the artifact build command.
    """

    runner = CliRunner()

    return runner.invoke(
        cli,
        [
            "build",
            *args,
        ],
    )


# =========================================================
# Build execution
# =========================================================


def test_build_delegates_artifact_execution_to_engine(
    monkeypatch,
) -> None:
    """
    Normal builds delegate artifact orchestration to the engine.
    """

    executed: list[str] = []

    def execute_artifact(
        artifact_id: str,
        *,
        project_root: Path,
        event_sink=None,
    ) -> None:
        executed.append(artifact_id)

    monkeypatch.setattr(
        cmd_build,
        "execute_artifact_build",
        execute_artifact,
    )

    result = _invoke(
        "skippy",
    )

    assert result.exit_code == 0
    assert executed == ["skippy"]


def test_build_does_not_create_build_plans(
    monkeypatch,
) -> None:
    """
    Normal execution leaves build-plan creation to the engine boundary.
    """

    def unexpected_planning(
        artifact_id: str,
        *,
        project_root: Path,
    ):
        raise AssertionError("normal CLI execution created build plans")

    monkeypatch.setattr(
        cmd_build,
        "create_build_plans",
        unexpected_planning,
    )

    monkeypatch.setattr(
        cmd_build,
        "execute_artifact_build",
        lambda artifact_id, *, project_root, event_sink=None: None,
    )

    result = _invoke(
        "skippy",
    )

    assert result.exit_code == 0


def test_build_passes_project_root(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    Artifact execution receives the current project root.
    """

    roots: list[Path] = []

    def execute_artifact(
        artifact_id: str,
        *,
        project_root: Path,
        event_sink=None,
    ) -> None:
        roots.append(project_root)

    monkeypatch.chdir(tmp_path)

    monkeypatch.setattr(
        cmd_build,
        "execute_artifact_build",
        execute_artifact,
    )

    result = _invoke(
        "skippy",
    )

    assert result.exit_code == 0
    assert roots == [tmp_path]


# =========================================================
# Dry run
# =========================================================


def test_build_dry_run_displays_all_plans(
    monkeypatch,
) -> None:
    """
    A dry run displays every realization plan for the artifact.
    """

    first = object()
    second = object()

    plans = (
        first,
        second,
    )

    displayed: list[object] = []

    monkeypatch.setattr(
        cmd_build,
        "create_build_plans",
        lambda artifact_id, *, project_root: plans,
    )

    monkeypatch.setattr(
        cmd_build,
        "display_build_plan",
        displayed.append,
    )

    def unexpected_execution(
        artifact_id: str,
        *,
        project_root: Path,
        event_sink=None,
    ) -> None:
        raise AssertionError("dry run entered artifact execution")

    monkeypatch.setattr(
        cmd_build,
        "execute_artifact_build",
        unexpected_execution,
    )

    result = _invoke(
        "skippy",
        "--dry-run",
    )

    assert result.exit_code == 0
    assert displayed == [
        first,
        second,
    ]


def test_build_dry_run_does_not_execute(
    monkeypatch,
) -> None:
    """
    A dry run performs planning and display but no execution.
    """

    plans = (
        object(),
        object(),
    )

    executed: list[str] = []

    monkeypatch.setattr(
        cmd_build,
        "create_build_plans",
        lambda artifact_id, *, project_root: plans,
    )

    monkeypatch.setattr(
        cmd_build,
        "display_build_plan",
        lambda plan: None,
    )

    def execute_artifact(
        artifact_id: str,
        *,
        project_root: Path,
        event_sink=None,
    ) -> None:
        executed.append(artifact_id)

    monkeypatch.setattr(
        cmd_build,
        "execute_artifact_build",
        execute_artifact,
    )

    result = _invoke(
        "skippy",
        "--dry-run",
    )

    assert result.exit_code == 0
    assert executed == []


# =========================================================
# Multiple artifacts
# =========================================================


def test_build_multiple_artifacts_in_argument_order(
    monkeypatch,
) -> None:
    """
    Multiple artifact IDs are delegated to the engine in argument order.
    """

    executed: list[str] = []

    def execute_artifact(
        artifact_id: str,
        *,
        project_root: Path,
        event_sink=None,
    ) -> None:
        executed.append(artifact_id)

    monkeypatch.setattr(
        cmd_build,
        "execute_artifact_build",
        execute_artifact,
    )

    result = _invoke(
        "skippy",
        "scooby",
    )

    assert result.exit_code == 0

    assert executed == [
        "skippy",
        "scooby",
    ]


def test_build_multiple_artifacts_dry_run_in_argument_order(
    monkeypatch,
) -> None:
    """
    Dry-run plans are displayed artifact-by-artifact in argument order.
    """

    skippy_first = object()
    skippy_second = object()
    scooby = object()

    plans_by_artifact = {
        "skippy": (
            skippy_first,
            skippy_second,
        ),
        "scooby": (scooby,),
    }

    displayed: list[object] = []

    monkeypatch.setattr(
        cmd_build,
        "create_build_plans",
        lambda artifact_id, *, project_root: plans_by_artifact[artifact_id],
    )

    monkeypatch.setattr(
        cmd_build,
        "display_build_plan",
        displayed.append,
    )

    def unexpected_execution(
        artifact_id: str,
        *,
        project_root: Path,
        event_sink=None,
    ) -> None:
        raise AssertionError("dry run entered artifact execution")

    monkeypatch.setattr(
        cmd_build,
        "execute_artifact_build",
        unexpected_execution,
    )

    result = _invoke(
        "skippy",
        "scooby",
        "--dry-run",
    )

    assert result.exit_code == 0

    assert displayed == [
        skippy_first,
        skippy_second,
        scooby,
    ]


# =========================================================
# Errors
# =========================================================


def test_build_plan_error_is_reported(
    monkeypatch,
) -> None:
    """
    Dry-run planning errors are presented as Click command errors.
    """

    def create_plans(
        artifact_id: str,
        *,
        project_root: Path,
    ):
        raise cmd_build.BuildPlanError("cannot create build plan")

    monkeypatch.setattr(
        cmd_build,
        "create_build_plans",
        create_plans,
    )

    result = _invoke(
        "skippy",
        "--dry-run",
    )

    assert result.exit_code != 0
    assert "cannot create build plan" in result.output


def test_build_execution_error_is_reported(
    monkeypatch,
) -> None:
    """
    Artifact build errors are presented as Click command errors.
    """

    def execute_artifact(
        artifact_id: str,
        *,
        project_root: Path,
        event_sink=None,
    ) -> None:
        raise cmd_build.BuildError("cannot execute build")

    monkeypatch.setattr(
        cmd_build,
        "execute_artifact_build",
        execute_artifact,
    )

    result = _invoke(
        "skippy",
    )

    assert result.exit_code != 0
    assert "cannot execute build" in result.output
