"""
Tests for explicit single-stage artifact execution.
"""
# File: tests/cli/test_build_stage.py
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
# Explicit stage execution
# =========================================================


def test_build_stage_executes_requested_stage(
    monkeypatch,
) -> None:
    """
    An explicit stage request delegates to independent stage execution.
    """

    executed: list[
        tuple[
            str,
            str,
            str | None,
            Path | None,
        ]
    ] = []

    def execute(
        artifact_id: str,
        *,
        stage_name: str,
        realization: str | None = None,
        project_root: Path | None = None,
        input_paths=None,
        parameter_values=None,
        output_paths=None,
    ) -> None:
        assert input_paths is None
        assert parameter_values is None
        assert output_paths is None

        executed.append(
            (
                artifact_id,
                stage_name,
                realization,
                project_root,
            )
        )

    monkeypatch.setattr(
        cmd_build,
        "execute_artifact_stage",
        execute,
        raising=False,
    )

    result = _invoke(
        "skippy",
        "--stage",
        "vector",
    )

    assert result.exit_code == 0

    assert len(executed) == 1

    artifact_id, stage_name, realization, _ = executed[0]

    assert artifact_id == "skippy"
    assert stage_name == "vector"
    assert realization is None


def test_build_stage_passes_project_root(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    Explicit stage execution uses the current project root.
    """

    roots: list[Path | None] = []

    def execute(
        artifact_id: str,
        *,
        stage_name: str,
        realization: str | None = None,
        project_root: Path | None = None,
        input_paths=None,
        parameter_values=None,
        output_paths=None,
    ) -> None:
        assert input_paths is None
        assert parameter_values is None
        assert output_paths is None

        roots.append(
            project_root,
        )

    monkeypatch.chdir(
        tmp_path,
    )

    monkeypatch.setattr(
        cmd_build,
        "execute_artifact_stage",
        execute,
        raising=False,
    )

    result = _invoke(
        "skippy",
        "--stage",
        "vector",
    )

    assert result.exit_code == 0

    assert roots == [
        tmp_path,
    ]


def test_build_stage_passes_realization(
    monkeypatch,
) -> None:
    """
    An explicit realization is forwarded to stage execution.
    """

    realizations: list[str | None] = []

    def execute(
        artifact_id: str,
        *,
        stage_name: str,
        realization: str | None = None,
        project_root: Path | None = None,
        input_paths=None,
        parameter_values=None,
        output_paths=None,
    ) -> None:
        assert input_paths is None
        assert parameter_values is None
        assert output_paths is None

        realizations.append(
            realization,
        )

    monkeypatch.setattr(
        cmd_build,
        "execute_artifact_stage",
        execute,
        raising=False,
    )

    result = _invoke(
        "skippy",
        "--stage",
        "vector",
        "--realization",
        "portrait",
    )

    assert result.exit_code == 0

    assert realizations == [
        "portrait",
    ]


# =========================================================
# Orchestration isolation
# =========================================================


def test_build_stage_does_not_create_build_plans(
    monkeypatch,
) -> None:
    """
    Explicit stage execution does not enter graph-driven build planning.
    """

    def unexpected_planning(
        *args,
        **kwargs,
    ):
        raise AssertionError("explicit stage execution entered build planning")

    monkeypatch.setattr(
        cmd_build,
        "create_build_plans",
        unexpected_planning,
    )

    monkeypatch.setattr(
        cmd_build,
        "execute_artifact_stage",
        lambda *args, **kwargs: None,
        raising=False,
    )

    result = _invoke(
        "skippy",
        "--stage",
        "vector",
    )

    assert result.exit_code == 0


def test_build_stage_does_not_execute_artifact_build(
    monkeypatch,
) -> None:
    """
    Explicit stage execution does not enter artifact build orchestration.
    """

    def unexpected_execution(
        *args,
        **kwargs,
    ):
        raise AssertionError("explicit stage execution entered artifact build execution")

    monkeypatch.setattr(
        cmd_build,
        "execute_artifact_build",
        unexpected_execution,
    )

    monkeypatch.setattr(
        cmd_build,
        "execute_artifact_stage",
        lambda *args, **kwargs: None,
        raising=False,
    )

    result = _invoke(
        "skippy",
        "--stage",
        "vector",
    )

    assert result.exit_code == 0


# =========================================================
# Command constraints
# =========================================================


def test_build_stage_rejects_multiple_artifacts(
    monkeypatch,
) -> None:
    """
    Explicit stage execution identifies exactly one artifact.
    """

    monkeypatch.setattr(
        cmd_build,
        "execute_artifact_stage",
        lambda *args, **kwargs: None,
        raising=False,
    )

    result = _invoke(
        "skippy",
        "scooby",
        "--stage",
        "vector",
    )

    assert result.exit_code != 0

    assert "single artifact" in result.output.lower()


def test_build_stage_rejects_dry_run(
    monkeypatch,
) -> None:
    """
    Independent stage execution does not use build-plan dry-run semantics.
    """

    monkeypatch.setattr(
        cmd_build,
        "execute_artifact_stage",
        lambda *args, **kwargs: None,
        raising=False,
    )

    result = _invoke(
        "skippy",
        "--stage",
        "vector",
        "--dry-run",
    )

    assert result.exit_code != 0

    assert "dry-run" in result.output.lower()


def test_build_realization_requires_stage() -> None:
    """
    Realization selection belongs to explicit stage execution.
    """

    result = _invoke(
        "skippy",
        "--realization",
        "portrait",
    )

    assert result.exit_code != 0

    assert "realization" in result.output.lower()


def test_build_input_requires_stage() -> None:
    """
    Explicit input bindings belong to independent stage execution.
    """

    result = _invoke(
        "skippy",
        "--input",
        "source=source.png",
    )

    assert result.exit_code != 0
    assert "input" in result.output.lower()
    assert "stage" in result.output.lower()


def test_build_parameter_requires_stage() -> None:
    """
    Explicit parameter bindings belong to independent stage execution.
    """

    result = _invoke(
        "skippy",
        "--parameter",
        "artwork_size=90",
    )

    assert result.exit_code != 0
    assert "parameter" in result.output.lower()
    assert "stage" in result.output.lower()


def test_build_output_requires_stage() -> None:
    """
    Explicit output bindings belong to independent stage execution.
    """

    result = _invoke(
        "skippy",
        "--output",
        "manifest=products.json",
    )

    assert result.exit_code != 0
    assert "output" in result.output.lower()
    assert "stage" in result.output.lower()


# =========================================================
# Build error boundary
# =========================================================


def test_build_stage_input_failure_is_reported(
    monkeypatch,
) -> None:
    """
    Stage input failures cross the CLI boundary as build errors.
    """

    def execute(
        *args,
        **kwargs,
    ) -> None:
        raise cmd_build.BuildError("required input is missing")

    monkeypatch.setattr(
        cmd_build,
        "execute_artifact_stage",
        execute,
        raising=False,
    )

    result = _invoke(
        "skippy",
        "--stage",
        "vector",
    )

    assert result.exit_code != 0
    assert "required input is missing" in result.output


def test_build_stage_context_failure_is_reported(
    monkeypatch,
) -> None:
    """
    Stage context failures cross the CLI boundary as build errors.
    """

    def execute(
        *args,
        **kwargs,
    ) -> None:
        raise cmd_build.BuildError("cannot resolve requested stage")

    monkeypatch.setattr(
        cmd_build,
        "execute_artifact_stage",
        execute,
        raising=False,
    )

    result = _invoke(
        "skippy",
        "--stage",
        "missing",
    )

    assert result.exit_code != 0
    assert "cannot resolve requested stage" in result.output


def test_build_stage_execution_failure_is_reported(
    monkeypatch,
) -> None:
    """
    Stage execution failures cross the CLI boundary as build errors.
    """

    def execute(
        *args,
        **kwargs,
    ) -> None:
        raise cmd_build.BuildError("stage execution failed")

    monkeypatch.setattr(
        cmd_build,
        "execute_artifact_stage",
        execute,
        raising=False,
    )

    result = _invoke(
        "skippy",
        "--stage",
        "vector",
    )

    assert result.exit_code != 0
    assert "stage execution failed" in result.output


# =========================================================
# Explicit stage bindings
# =========================================================


def test_build_stage_passes_input_bindings(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    Explicit input bindings are forwarded to stage execution.
    """

    received = None

    def execute(
        artifact_id: str,
        *,
        stage_name: str,
        realization: str | None = None,
        project_root: Path | None = None,
        input_paths=None,
        parameter_values=None,
        output_paths=None,
    ) -> None:
        nonlocal received

        received = input_paths

    monkeypatch.chdir(
        tmp_path,
    )

    monkeypatch.setattr(
        cmd_build,
        "execute_artifact_stage",
        execute,
    )

    result = _invoke(
        "skippy",
        "--stage",
        "vector",
        "--input",
        "raster.manifest=external/products.json",
    )

    assert result.exit_code == 0

    assert received == {
        "raster.manifest": (tmp_path / "external" / "products.json"),
    }


def test_build_stage_passes_parameter_bindings(
    monkeypatch,
) -> None:
    """
    Explicit parameter bindings are forwarded as typed values.
    """

    received = None

    def execute(
        artifact_id: str,
        *,
        stage_name: str,
        realization: str | None = None,
        project_root: Path | None = None,
        input_paths=None,
        parameter_values=None,
        output_paths=None,
    ) -> None:
        nonlocal received

        received = parameter_values

    monkeypatch.setattr(
        cmd_build,
        "execute_artifact_stage",
        execute,
    )

    result = _invoke(
        "skippy",
        "--stage",
        "vector",
        "--parameter",
        "artwork_size=90",
    )

    assert result.exit_code == 0

    assert received == {
        "artwork_size": 90,
    }


def test_build_stage_passes_output_bindings(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    Explicit output bindings are forwarded to stage execution.
    """

    received = None

    def execute(
        artifact_id: str,
        *,
        stage_name: str,
        realization: str | None = None,
        project_root: Path | None = None,
        input_paths=None,
        parameter_values=None,
        output_paths=None,
    ) -> None:
        nonlocal received

        received = output_paths

    monkeypatch.chdir(
        tmp_path,
    )

    monkeypatch.setattr(
        cmd_build,
        "execute_artifact_stage",
        execute,
    )

    result = _invoke(
        "skippy",
        "--stage",
        "vector",
        "--output",
        "manifest=external/vector.json",
    )

    assert result.exit_code == 0

    assert received == {
        "manifest": (tmp_path / "external" / "vector.json"),
    }


def test_build_stage_passes_all_binding_types(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    Input, parameter, and output bindings may be used together.
    """

    received = None

    def execute(
        artifact_id: str,
        *,
        stage_name: str,
        realization: str | None = None,
        project_root: Path | None = None,
        input_paths=None,
        parameter_values=None,
        output_paths=None,
    ) -> None:
        nonlocal received

        received = (
            input_paths,
            parameter_values,
            output_paths,
        )

    monkeypatch.chdir(
        tmp_path,
    )

    monkeypatch.setattr(
        cmd_build,
        "execute_artifact_stage",
        execute,
    )

    result = _invoke(
        "skippy",
        "--stage",
        "vector",
        "--input",
        "raster.manifest=external/raster.json",
        "--parameter",
        "artwork_size=90.5",
        "--output",
        "manifest=external/vector.json",
    )

    assert result.exit_code == 0

    assert received == (
        {
            "raster.manifest": (tmp_path / "external" / "raster.json"),
        },
        {
            "artwork_size": 90.5,
        },
        {
            "manifest": (tmp_path / "external" / "vector.json"),
        },
    )


def test_build_stage_accepts_repeated_bindings(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    Binding options may be repeated for distinct semantic names.
    """

    received = None

    def execute(
        artifact_id: str,
        *,
        stage_name: str,
        realization: str | None = None,
        project_root: Path | None = None,
        input_paths=None,
        parameter_values=None,
        output_paths=None,
    ) -> None:
        nonlocal received

        received = (
            input_paths,
            parameter_values,
            output_paths,
        )

    monkeypatch.chdir(
        tmp_path,
    )

    monkeypatch.setattr(
        cmd_build,
        "execute_artifact_stage",
        execute,
    )

    result = _invoke(
        "skippy",
        "--stage",
        "prepare",
        "--input",
        "source=external/source.png",
        "--parameter",
        "first=1",
        "--parameter",
        "second=true",
        "--output",
        "trace=external/trace.svg",
        "--output",
        "envelope=external/envelope.svg",
    )

    assert result.exit_code == 0

    assert received == (
        {
            "source": (tmp_path / "external" / "source.png"),
        },
        {
            "first": 1,
            "second": True,
        },
        {
            "trace": (tmp_path / "external" / "trace.svg"),
            "envelope": (tmp_path / "external" / "envelope.svg"),
        },
    )


def test_build_stage_without_bindings_passes_none(
    monkeypatch,
) -> None:
    """
    Ordinary stage execution does not manufacture explicit bindings.
    """

    received = None

    def execute(
        artifact_id: str,
        *,
        stage_name: str,
        realization: str | None = None,
        project_root: Path | None = None,
        input_paths=None,
        parameter_values=None,
        output_paths=None,
    ) -> None:
        nonlocal received

        received = (
            input_paths,
            parameter_values,
            output_paths,
        )

    monkeypatch.setattr(
        cmd_build,
        "execute_artifact_stage",
        execute,
    )

    result = _invoke(
        "skippy",
        "--stage",
        "vector",
    )

    assert result.exit_code == 0

    assert received == (
        None,
        None,
        None,
    )


# =========================================================
# Binding errors
# =========================================================


def test_build_stage_reports_invalid_input_binding() -> None:
    """
    Invalid input binding syntax is presented as a CLI error.
    """

    result = _invoke(
        "skippy",
        "--stage",
        "vector",
        "--input",
        "raster.manifest",
    )

    assert result.exit_code != 0
    assert "name=path" in result.output.lower()


def test_build_stage_reports_invalid_parameter_binding() -> None:
    """
    Invalid parameter binding syntax is presented as a CLI error.
    """

    result = _invoke(
        "skippy",
        "--stage",
        "vector",
        "--parameter",
        "artwork_size",
    )

    assert result.exit_code != 0
    assert "name=value" in result.output.lower()


def test_build_stage_reports_duplicate_output_binding() -> None:
    """
    Duplicate output bindings are presented as a CLI error.
    """

    result = _invoke(
        "skippy",
        "--stage",
        "vector",
        "--output",
        "manifest=first.json",
        "--output",
        "manifest=second.json",
    )

    assert result.exit_code != 0
    assert "duplicate" in result.output.lower()
