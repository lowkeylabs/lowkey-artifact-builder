"""
Tests for CLI presentation of artifact build failures.
"""
# File: tests/cli/test_build_failure_display.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

import lowkey_artifact_builder.cli.cmd_build as cmd_build
from lowkey_artifact_builder.cli._main import cli
from lowkey_artifact_builder.engine import (
    BuildError,
    ExecutionEvent,
)

# =========================================================
# Helpers
# =========================================================


def _emit_failed_build(
    artifact_id: str,
    *,
    realization: str | None = None,
    project_root: Path,
    event_sink=None,
) -> None:
    """
    Emit representative failure lifecycle events and fail execution.
    """

    assert artifact_id == "skippy"
    assert event_sink is not None

    event_sink(
        ExecutionEvent(
            kind="build.started",
            artifact_id="skippy",
            model_name="artwork",
            realization="default",
        )
    )

    event_sink(
        ExecutionEvent(
            kind="stage.started",
            artifact_id="skippy",
            model_name="artwork",
            realization="default",
            stage_name="raster",
        )
    )

    event_sink(
        ExecutionEvent(
            kind="stage.failed",
            artifact_id="skippy",
            model_name="artwork",
            realization="default",
            stage_name="raster",
        )
    )

    event_sink(
        ExecutionEvent(
            kind="build.failed",
            artifact_id="skippy",
            model_name="artwork",
            realization="default",
        )
    )

    raise BuildError("raster execution failed")


def _invoke_failed_build(
    monkeypatch: pytest.MonkeyPatch,
):
    """
    Invoke one CLI build whose artifact execution fails.
    """

    monkeypatch.setattr(
        cmd_build,
        "execute_artifact_build",
        _emit_failed_build,
    )

    return CliRunner().invoke(
        cli,
        [
            "build",
            "skippy",
        ],
    )


# =========================================================
# Failure presentation
# =========================================================


def test_failed_build_reports_stage_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Stage failure is visible before command termination.
    """

    result = _invoke_failed_build(
        monkeypatch,
    )

    assert result.exit_code != 0
    assert "Stage failed: raster" in result.output


def test_failed_build_reports_build_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Artifact build failure is visible before command termination.
    """

    result = _invoke_failed_build(
        monkeypatch,
    )

    assert result.exit_code != 0
    assert "Build failed: skippy" in result.output


def test_failed_build_reports_diagnostic_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    The authoritative execution diagnostic is reported exactly once.
    """

    result = _invoke_failed_build(
        monkeypatch,
    )

    assert result.exit_code != 0

    assert result.output.count("raster execution failed") == 1


def test_failed_build_does_not_report_completion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Failed execution never appears to complete successfully.
    """

    result = _invoke_failed_build(
        monkeypatch,
    )

    assert result.exit_code != 0

    assert "Stage completed: raster" not in result.output
    assert "Build completed: skippy" not in result.output


def test_failed_build_preserves_lifecycle_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    CLI output preserves the semantic failure lifecycle order.
    """

    result = _invoke_failed_build(
        monkeypatch,
    )

    assert result.exit_code != 0

    output = result.output

    build_started = output.index("Building skippy")
    stage_started = output.index("Stage started: raster")
    stage_failed = output.index("Stage failed: raster")
    build_failed = output.index("Build failed: skippy")
    diagnostic = output.index("raster execution failed")

    assert build_started < stage_started < stage_failed < build_failed < diagnostic
