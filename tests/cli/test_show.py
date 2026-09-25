"""
Tests for the artifact show command.

These tests protect only the generic command-line contract that remains
independent of SHOW's manufacturing presentation. Manufacturing overview,
Realization selection, state, and 3MF presentation are covered separately
by test_show_manufacturing.py.
"""
# File: tests/cli/test_show.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import Any

from click.testing import CliRunner

from lowkey_artifact_builder.cli._main import cli

# =========================================================
# Helpers
# =========================================================


def _invoke(
    *args: str,
) -> Any:
    """
    Invoke the artifact show command.
    """

    runner = CliRunner()

    return runner.invoke(
        cli,
        [
            "show",
            *args,
        ],
    )


# =========================================================
# Argument validation
# =========================================================


def test_show_requires_artifact_id() -> None:
    """
    Artifact inspection requires exactly one Artifact ID.
    """

    result = _invoke()

    assert result.exit_code != 0
    assert "artifact" in result.output.lower()


def test_show_rejects_multiple_artifact_ids() -> None:
    """
    Artifact inspection operates on one Artifact at a time.
    """

    result = _invoke(
        "skippy",
        "scooby",
    )

    assert result.exit_code != 0
