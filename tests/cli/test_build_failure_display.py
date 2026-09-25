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
    realization: str,
    project_root: Path,
    event_sink=None,
) -> None:
    """
    Emit representative semantic failure events and fail execution.

    The engine-facing event channel remains available even though routine
    CLI presentation does not narrate the build or Stage lifecycle.
    """

    assert artifact_id == "skippy"
    assert realization == "artwork_default"
    assert event_sink is not None

    event_sink(
        ExecutionEvent(
            kind="build.started",
            artifact_id="skippy",
            model_name="artwork",
            realization="artwork_default",
        )
    )

    event_sink(
        ExecutionEvent(
            kind="stage.started",
            artifact_id="skippy",
            model_name="artwork",
            realization="artwork_default",
            stage_name="raster",
        )
    )

    event_sink(
        ExecutionEvent(
            kind="stage.failed",
            artifact_id="skippy",
            model_name="artwork",
            realization="artwork_default",
            stage_name="raster",
        )
    )

    event_sink(
        ExecutionEvent(
            kind="build.failed",
            artifact_id="skippy",
            model_name="artwork",
            realization="artwork_default",
        )
    )

    raise BuildError("raster execution failed")


def _invoke_failed_build(
    monkeypatch: pytest.MonkeyPatch,
):
    """
    Invoke one explicitly selected CLI Realization build whose execution fails.
    """

    monkeypatch.setattr(
        cmd_build,
        "materialize_artifact",
        lambda artifact_id, *, project_root: None,
    )

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
            "--realization",
            "artwork_default",
        ],
    )


# =========================================================
# Failure presentation
# =========================================================


def test_failed_build_reports_authoritative_diagnostic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Routine BUILD failure presents the authoritative execution diagnostic.
    """

    result = _invoke_failed_build(
        monkeypatch,
    )

    assert result.exit_code != 0
    assert "raster execution failed" in result.output


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


def test_failed_build_does_not_narrate_execution_lifecycle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Routine BUILD failure does not narrate internal execution lifecycle events.

    Semantic execution events remain available to observers, but normal CLI
    output stays focused on the actionable failure diagnostic.
    """

    result = _invoke_failed_build(
        monkeypatch,
    )

    assert result.exit_code != 0

    assert "Building skippy" not in result.output
    assert "Stage started: raster" not in result.output
    assert "Stage failed: raster" not in result.output
    assert "Build failed: skippy" not in result.output


def test_failed_build_does_not_report_successful_manufacturing_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Failed execution never appears to produce a successful manufacturing result.
    """

    result = _invoke_failed_build(
        monkeypatch,
    )

    assert result.exit_code != 0

    assert "Stage completed: raster" not in result.output
    assert "Build completed: skippy" not in result.output
    assert " built " not in result.output
    assert " current " not in result.output
    assert "artwork_default.3mf" not in result.output
