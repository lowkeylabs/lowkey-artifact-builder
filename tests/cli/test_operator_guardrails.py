"""
Public CLI operator guard-rail tests.

The command-line interface is an operator boundary.

Normal empty state must be explained rather than represented by silence or an
empty presentation. Expected operator/configuration failures must be translated
into concise CLI errors rather than exposing Python tracebacks.

These tests protect that common public contract. Command-specific semantics
remain covered by the individual CLI test modules.
"""

# File: tests/cli/test_operator_guardrails.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

import lowkey_artifact_builder.cli.cmd_color as cmd_color
from lowkey_artifact_builder.cli._main import cli
from lowkey_artifact_builder.config import ConfigError

# =========================================================
# Helpers
# =========================================================


def _invoke(
    *args: str,
) -> Any:
    """
    Invoke the public artifact CLI.
    """

    runner = CliRunner()

    return runner.invoke(
        cli,
        list(args),
    )


def _assert_explanatory_empty_result(
    result: Any,
) -> None:
    """
    Assert that a successful empty result explains the empty state.

    An empty collection is normal operator state, but the CLI must not make
    the operator infer that state from silence or an empty table.
    """

    assert result.exit_code == 0, result.output
    assert result.output.strip()
    assert "no " in result.output.lower()
    assert "traceback" not in result.output.lower()


def _assert_expected_cli_error(
    result: Any,
    *expected_text: str,
) -> None:
    """
    Assert that an expected operator failure is translated at the CLI boundary.
    """

    assert result.exit_code != 0
    assert result.output.strip()

    output = result.output.lower()

    assert "error" in output
    assert "traceback" not in output

    for text in expected_text:
        assert text.lower() in output


# =========================================================
# Empty workspace
# =========================================================


def test_create_explains_empty_workspace(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """
    Bare CREATE explains that there is currently nothing to act on.

    Empty Artifact and incoming-source collections must not be represented
    only by empty tables.
    """

    monkeypatch.chdir(
        tmp_path,
    )

    result = _invoke(
        "create",
    )

    _assert_explanatory_empty_result(
        result,
    )

    output = result.output.lower()

    assert "artifact" in output
    assert "png" in output


def test_list_explains_empty_workspace(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """
    LIST explains an empty managed-Artifact collection.
    """

    monkeypatch.chdir(
        tmp_path,
    )

    result = _invoke(
        "list",
    )

    _assert_explanatory_empty_result(
        result,
    )

    assert "artifact" in result.output.lower()


def test_colors_explains_empty_workspace(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """
    Bare COLORS explains that there are no Artifacts to analyze.

    A broad operation over an empty workspace is normal empty state rather
    than an internal configuration or planning failure.
    """

    monkeypatch.chdir(
        tmp_path,
    )

    result = _invoke(
        "colors",
    )

    _assert_explanatory_empty_result(
        result,
    )

    assert "artifact" in result.output.lower()


# =========================================================
# Explicit missing Artifact
# =========================================================


@pytest.mark.parametrize(
    "arguments",
    (
        (
            "show",
            "missing",
        ),
        (
            "config",
            "missing",
        ),
        (
            "colors",
            "missing",
        ),
        (
            "clean",
            "missing",
        ),
    ),
)
def test_explicit_missing_artifact_is_concise_operator_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    arguments: tuple[str, ...],
) -> None:
    """
    Explicitly naming an unavailable Artifact is an operator-facing error.

    Public commands must not expose a Python traceback for this expected
    failure.
    """

    monkeypatch.chdir(
        tmp_path,
    )

    result = _invoke(
        *arguments,
    )

    _assert_expected_cli_error(
        result,
        "missing",
        "artifact",
    )


# =========================================================
# Expected configuration/application failures
# =========================================================


def test_colors_translates_expected_configuration_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    COLORS translates expected configuration failures at the CLI boundary.

    Color analysis may legitimately discover invalid or inconsistent
    persistent Artifact state while resolving manufacturing inputs. Such
    failures are operator problems, not Python tracebacks.
    """

    def fail_colors(
        artifact_id: str | None,
        *,
        realization: str | None = None,
        recolor: str | None = None,
    ) -> object:
        raise ConfigError("Artifact 'broken' has no configured source.")

    monkeypatch.setattr(
        cmd_color,
        "list_artifacts",
        lambda *, project_root: ("broken",),
    )
    monkeypatch.setattr(
        cmd_color,
        "run_colors",
        fail_colors,
    )

    result = _invoke(
        "colors",
        "broken",
    )

    _assert_expected_cli_error(
        result,
        "broken",
        "source",
    )


# =========================================================
# Usage errors
# =========================================================


@pytest.mark.parametrize(
    "arguments",
    (
        ("show",),
        ("config",),
        (
            "list",
            "unexpected",
        ),
        (
            "create",
            "--all-sources",
            "--source",
            "source.png",
        ),
        (
            "colors",
            "artifact",
            "--realization",
            "shape_ornament",
            "--recolor",
            "reset-all-realizations",
        ),
    ),
)
def test_incorrect_command_usage_is_concise_cli_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    arguments: tuple[str, ...],
) -> None:
    """
    Invalid command/option combinations are reported by the CLI without
    exposing implementation tracebacks.
    """

    monkeypatch.chdir(
        tmp_path,
    )

    result = _invoke(
        *arguments,
    )

    assert result.exit_code != 0
    assert result.output.strip()

    output = result.output.lower()

    assert "error" in output
    assert "traceback" not in output
