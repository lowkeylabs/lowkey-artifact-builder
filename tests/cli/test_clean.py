"""
Tests for the artifact clean command.
"""
# File: tests/cli/test_clean.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path
from typing import Any

from click.testing import CliRunner

import lowkey_artifact_builder.cli.cmd_clean as cmd_clean
from lowkey_artifact_builder.cli._main import cli

# =========================================================
# Helpers
# =========================================================


def _invoke(
    *args: str,
    input: str | None = None,
) -> Any:
    """
    Invoke the artifact clean command.
    """

    runner = CliRunner()

    return runner.invoke(
        cli,
        [
            "clean",
            *args,
        ],
        input=input,
    )


# =========================================================
# Argument validation
# =========================================================


def test_clean_without_scope_requires_confirmation_before_cleaning(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    Bare clean requires confirmation before generated Products are removed
    across the project.
    """

    calls: list[tuple[str, Path]] = []

    monkeypatch.chdir(tmp_path)

    monkeypatch.setattr(
        cmd_clean,
        "list_artifacts",
        lambda *, project_root: (
            "skippy",
            "scooby",
        ),
    )

    def fake_clean_artifact(
        artifact_id: str,
        *,
        realization: str | None = None,
        project_root: Path,
    ) -> None:
        calls.append(
            (
                artifact_id,
                project_root,
            )
        )

    monkeypatch.setattr(
        cmd_clean,
        "clean_artifact",
        fake_clean_artifact,
    )

    result = _invoke(
        input="n\n",
    )

    assert result.exit_code != 0
    assert "Clean generated Products for all Artifacts?" in result.output
    assert calls == []


def test_clean_force_cleans_all_artifacts_without_confirmation(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    --force permits unattended project-wide cleaning without prompting.
    """

    calls: list[tuple[str, Path]] = []

    monkeypatch.chdir(tmp_path)

    monkeypatch.setattr(
        cmd_clean,
        "list_artifacts",
        lambda *, project_root: (
            "skippy",
            "scooby",
        ),
    )

    def fake_clean_artifact(
        artifact_id: str,
        *,
        realization: str | None = None,
        project_root: Path,
    ) -> None:
        calls.append(
            (
                artifact_id,
                project_root,
            )
        )

    monkeypatch.setattr(
        cmd_clean,
        "clean_artifact",
        fake_clean_artifact,
    )

    result = _invoke(
        "--force",
    )

    assert result.exit_code == 0
    assert calls == [
        (
            "skippy",
            tmp_path,
        ),
        (
            "scooby",
            tmp_path,
        ),
    ]


def test_clean_rejects_multiple_artifact_ids() -> None:
    """
    Artifact cleaning operates on one artifact at a time.
    """

    result = _invoke(
        "skippy",
        "scooby",
    )

    assert result.exit_code != 0


# =========================================================
# Artifact existence
# =========================================================


def test_clean_rejects_undefined_artifact(
    monkeypatch,
) -> None:
    """
    Cleaning requires an existing persistent artifact definition.
    """

    monkeypatch.setattr(
        cmd_clean,
        "load_artifact_config",
        lambda *args, **kwargs: {},
    )

    result = _invoke(
        "skippy",
    )

    assert result.exit_code != 0
    assert "not defined" in result.output.lower()


# =========================================================
# Cleaning
# =========================================================


def test_clean_delegates_to_artifact_api(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    The CLI delegates cleaning to the artifact lifecycle API.

    Filesystem ownership and deletion semantics belong below the CLI
    boundary.
    """

    calls: list[tuple[str, Path]] = []

    monkeypatch.chdir(tmp_path)

    monkeypatch.setattr(
        cmd_clean,
        "load_artifact_config",
        lambda *args, **kwargs: {
            "model": "artwork",
        },
    )

    monkeypatch.setattr(
        cmd_clean,
        "clean_artifact",
        lambda artifact_id, *, realization=None, project_root: calls.append(
            (
                artifact_id,
                project_root,
            )
        ),
    )

    result = _invoke(
        "skippy",
    )

    assert result.exit_code == 0
    assert calls == [
        (
            "skippy",
            tmp_path,
        ),
    ]


def test_clean_realization_delegates_to_artifact_api(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    The CLI delegates Realization-scoped cleaning to the Artifact lifecycle API.

    Filesystem ownership and deletion semantics belong below the CLI
    boundary.
    """

    calls: list[tuple[str, str | None, Path]] = []

    monkeypatch.chdir(tmp_path)

    monkeypatch.setattr(
        cmd_clean,
        "load_artifact_config",
        lambda *args, **kwargs: {
            "model": "artwork",
        },
    )

    def fake_clean_artifact(
        artifact_id: str,
        *,
        realization: str | None = None,
        project_root: Path,
    ) -> None:
        calls.append(
            (
                artifact_id,
                realization,
                project_root,
            )
        )

    monkeypatch.setattr(
        cmd_clean,
        "clean_artifact",
        fake_clean_artifact,
    )

    result = _invoke(
        "skippy",
        "--realization",
        "shape_ornament",
    )

    assert result.exit_code == 0
    assert calls == [
        (
            "skippy",
            "shape_ornament",
            tmp_path,
        ),
    ]


def test_clean_realization_without_artifact_ids_delegates_bulk_scope(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    clean --realization delegates the complete Artifact scope to the
    validation-atomic bulk cleaning service.
    """

    calls: list[tuple[tuple[str, ...], str, Path]] = []

    monkeypatch.chdir(tmp_path)

    monkeypatch.setattr(
        cmd_clean,
        "list_artifacts",
        lambda *, project_root: (
            "skippy",
            "scooby",
        ),
    )

    def fake_clean_realization_across_artifacts(
        artifact_ids: tuple[str, ...],
        realization: str,
        *,
        project_root: Path,
    ) -> None:
        calls.append(
            (
                artifact_ids,
                realization,
                project_root,
            )
        )

    monkeypatch.setattr(
        cmd_clean,
        "clean_realization_across_artifacts",
        fake_clean_realization_across_artifacts,
    )

    result = _invoke(
        "--realization",
        "shape_ornament",
    )

    assert result.exit_code == 0
    assert calls == [
        (
            (
                "skippy",
                "scooby",
            ),
            "shape_ornament",
            tmp_path,
        ),
    ]


def test_clean_without_scope_cleans_all_artifacts_after_confirmation(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    Bare clean removes generated Products across all Artifacts after
    explicit confirmation.
    """

    calls: list[tuple[str, Path]] = []

    monkeypatch.chdir(tmp_path)

    monkeypatch.setattr(
        cmd_clean,
        "list_artifacts",
        lambda *, project_root: (
            "skippy",
            "scooby",
        ),
    )

    def fake_clean_artifact(
        artifact_id: str,
        *,
        realization: str | None = None,
        project_root: Path,
    ) -> None:
        calls.append(
            (
                artifact_id,
                project_root,
            )
        )

    monkeypatch.setattr(
        cmd_clean,
        "clean_artifact",
        fake_clean_artifact,
    )

    result = _invoke(
        input="y\n",
    )

    assert result.exit_code == 0
    assert "Clean generated Products for all Artifacts?" in result.output
    assert calls == [
        (
            "skippy",
            tmp_path,
        ),
        (
            "scooby",
            tmp_path,
        ),
    ]
