"""
Tests for CLI presentation of incremental execution events.
"""
# File: tests/cli/test_build_event_display.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import click
from click.testing import CliRunner

from lowkey_artifact_builder.cli.cmd_build import (
    _display_execution_event,
)
from lowkey_artifact_builder.engine import (
    ExecutionEvent,
)

# =========================================================
# Helpers
# =========================================================


def _event(
    kind: str,
    *,
    stage_name: str | None = None,
) -> ExecutionEvent:
    """
    Construct one representative CLI execution event.
    """

    return ExecutionEvent(
        kind=kind,
        artifact_id="skippy",
        model_name="artwork",
        realization="default",
        stage_name=stage_name,
    )


def _display(
    event: ExecutionEvent,
) -> str:
    """
    Capture presentation of one execution event.
    """

    runner = CliRunner()

    with runner.isolated_filesystem():
        result = runner.invoke(
            _display_command,
            obj=event,
        )

    assert result.exit_code == 0, result.output or repr(result.exception)

    return result.output


@click.command()
@click.pass_obj
def _display_command(
    event: ExecutionEvent,
) -> None:
    """
    Invoke the event display boundary under Click capture.
    """

    _display_execution_event(
        event,
    )


# =========================================================
# Build events
# =========================================================


def test_build_started_is_displayed() -> None:
    """
    Build start identifies the artifact realization being built.
    """

    output = _display(
        _event(
            "build.started",
        )
    )

    assert "skippy" in output
    assert "artwork" in output
    assert "default" in output


def test_build_completed_is_displayed() -> None:
    """
    Build completion identifies the completed artifact realization.
    """

    output = _display(
        _event(
            "build.completed",
        )
    )

    assert "skippy" in output
    assert "completed" in output.lower()


# =========================================================
# Stage events
# =========================================================


def test_stage_started_is_displayed() -> None:
    """
    Stage start identifies the stage being executed.
    """

    output = _display(
        _event(
            "stage.started",
            stage_name="raster",
        )
    )

    assert "raster" in output


def test_stage_completed_is_displayed() -> None:
    """
    Stage completion identifies the completed stage.
    """

    output = _display(
        _event(
            "stage.completed",
            stage_name="raster",
        )
    )

    assert "raster" in output
    assert "completed" in output.lower()


def test_stage_skipped_is_displayed() -> None:
    """
    Reusable stages are visibly distinguished from executed stages.
    """

    output = _display(
        _event(
            "stage.skipped",
            stage_name="raster",
        )
    )

    assert "raster" in output
    assert "skipped" in output.lower()
