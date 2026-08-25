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


def test_build_creates_plans_for_artifact(
    monkeypatch,
) -> None:
    """
    Building an artifact delegates planning to the plural build-plan API.
    """

    planned: list[str] = []
    plans = (
        object(),
        object(),
    )

    def create_plans(
        artifact_id: str,
        *,
        project_root: Path,
    ) -> tuple[object, ...]:
        planned.append(artifact_id)
        return plans

    monkeypatch.setattr(
        cmd_build,
        "create_build_plans",
        create_plans,
    )

    monkeypatch.setattr(
        cmd_build,
        "execute_incremental_artifact_build",
        lambda plan, *, event_sink=None: None,
    )

    result = _invoke(
        "skippy",
    )

    assert result.exit_code == 0
    assert planned == ["skippy"]


def test_build_executes_all_artifact_plans(
    monkeypatch,
) -> None:
    """
    All realization plans returned for an artifact are executed.
    """

    plans = (
        object(),
        object(),
    )

    executed: list[object] = []

    monkeypatch.setattr(
        cmd_build,
        "create_build_plans",
        lambda artifact_id, *, project_root: plans,
    )

    def execute(
        plan: object,
        *,
        event_sink=None,
    ) -> None:
        executed.append(plan)

    monkeypatch.setattr(
        cmd_build,
        "execute_incremental_artifact_build",
        execute,
    )

    result = _invoke(
        "skippy",
    )

    assert result.exit_code == 0
    assert executed == [
        plans[0],
        plans[1],
    ]


def test_build_passes_project_root(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    Build planning uses the current project root.
    """

    roots: list[Path] = []

    def create_plans(
        artifact_id: str,
        *,
        project_root: Path,
    ) -> tuple[object, ...]:
        roots.append(project_root)
        return ()

    monkeypatch.chdir(tmp_path)

    monkeypatch.setattr(
        cmd_build,
        "create_build_plans",
        create_plans,
    )

    monkeypatch.setattr(
        cmd_build,
        "execute_incremental_artifact_build",
        lambda plan, *, event_sink=None: None,
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
        plan: object,
        *,
        event_sink=None,
    ) -> None:
        raise AssertionError("dry run entered incremental execution")

    monkeypatch.setattr(
        cmd_build,
        "execute_incremental_artifact_build",
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

    executed: list[object] = []

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

    def execute(
        plan: object,
        *,
        event_sink=None,
    ) -> None:
        executed.append(plan)

    monkeypatch.setattr(
        cmd_build,
        "execute_incremental_artifact_build",
        execute,
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
    Multiple artifact IDs are planned and executed in argument order.
    """

    planned: list[str] = []
    executed: list[str] = []

    skippy = object()
    scooby = object()

    plans_by_artifact = {
        "skippy": (skippy,),
        "scooby": (scooby,),
    }

    artifact_by_plan = {
        id(skippy): "skippy",
        id(scooby): "scooby",
    }

    def create_plans(
        artifact_id: str,
        *,
        project_root: Path,
    ) -> tuple[object, ...]:
        planned.append(artifact_id)
        return plans_by_artifact[artifact_id]

    def execute(
        plan: object,
        *,
        event_sink=None,
    ) -> None:
        try:
            artifact_id = artifact_by_plan[id(plan)]
        except KeyError as exc:
            raise AssertionError("unexpected build plan") from exc

        executed.append(artifact_id)

    monkeypatch.setattr(
        cmd_build,
        "create_build_plans",
        create_plans,
    )

    monkeypatch.setattr(
        cmd_build,
        "execute_incremental_artifact_build",
        execute,
    )

    result = _invoke(
        "skippy",
        "scooby",
    )

    assert result.exit_code == 0

    assert planned == [
        "skippy",
        "scooby",
    ]

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
        plan: object,
        *,
        event_sink=None,
    ) -> None:
        raise AssertionError("dry run entered incremental execution")

    monkeypatch.setattr(
        cmd_build,
        "execute_incremental_artifact_build",
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
    Build planning errors are presented as Click command errors.
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
    )

    assert result.exit_code != 0
    assert "cannot create build plan" in result.output


def test_build_execution_error_is_reported(
    monkeypatch,
) -> None:
    """
    Incremental build execution errors are presented as Click command errors.
    """

    plans = (object(),)

    monkeypatch.setattr(
        cmd_build,
        "create_build_plans",
        lambda artifact_id, *, project_root: plans,
    )

    def execute(
        plan: object,
        *,
        event_sink=None,
    ) -> None:
        raise cmd_build.BuildError("cannot execute build")

    monkeypatch.setattr(
        cmd_build,
        "execute_incremental_artifact_build",
        execute,
    )

    result = _invoke(
        "skippy",
    )

    assert result.exit_code != 0
    assert "cannot execute build" in result.output
