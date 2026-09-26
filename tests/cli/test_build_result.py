"""
Tests for successful BUILD manufacturing-result presentation.

A routine selected-Realization build exists to make the requested
manufacturing Product current and leave the operator with an accessible
3MF.

These tests protect the CLI/application boundary rather than Stage or
incremental-engine mechanics. Engine tests independently protect canonical
Product state, package publication, and semantic execution events.
"""

# File: tests/cli/test_build_result.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

import lowkey_artifact_builder.cli.cmd_build as cmd_build
from lowkey_artifact_builder.cli._main import cli
from lowkey_artifact_builder.engine import (
    ExecutionEvent,
    ExecutionPlan,
    PlannedStageExecution,
    ProductState,
    ProductStateEvent,
)

# =========================================================
# Helpers
# =========================================================


ARTIFACT_ID = "skippy"
REALIZATION = "shape_ornament"
MODEL_NAME = "shape"


def _invoke(
    *args: str,
    cli_args: tuple[str, ...] = (),
) -> Any:
    """
    Invoke the artifact build command.

    cli_args contains root-command options such as -v, -vv, and --quiet.
    """

    return CliRunner().invoke(
        cli,
        [
            *cli_args,
            "build",
            *args,
        ],
    )


def _artifact_dir(
    project_root: Path,
) -> Path:
    """
    Return the materialized Artifact directory used by these tests.
    """

    return project_root / "artifacts" / ARTIFACT_ID


def _canonical_3mf(
    project_root: Path,
) -> Path:
    """
    Return the canonical package Product path for the selected Realization.
    """

    return _artifact_dir(project_root) / MODEL_NAME / REALIZATION / "40-package" / "artifact.3mf"


def _published_3mf(
    project_root: Path,
) -> Path:
    """
    Return the operator-facing Realization-named convenience 3MF.
    """

    return _artifact_dir(project_root) / f"{REALIZATION}.3mf"


def _relative_published_3mf(
    project_root: Path,
) -> Path:
    """
    Return the operator-facing 3MF path relative to the project root.
    """

    return _published_3mf(
        project_root,
    ).relative_to(
        project_root,
    )


def _install_materialization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Keep these tests focused on BUILD result behavior.

    Artifact materialization itself is protected elsewhere.
    """

    monkeypatch.setattr(
        cmd_build,
        "materialize_artifact",
        lambda artifact_id, *, project_root: None,
    )


def _product_state_event(
    state: ProductState,
    *,
    stage_name: str = "package",
    product_name: str = "artifact",
) -> ProductStateEvent:
    """
    Return one representative persistent Product-state observation.
    """

    return ProductStateEvent(
        artifact_id=ARTIFACT_ID,
        model_name=MODEL_NAME,
        realization=REALIZATION,
        stage_name=stage_name,
        product_name=product_name,
        state=state,
    )


def _execution_event(
    kind: str,
    *,
    stage_name: str | None = None,
) -> ExecutionEvent:
    """
    Return one representative execution lifecycle event.
    """

    return ExecutionEvent(
        kind=kind,
        artifact_id=ARTIFACT_ID,
        model_name=MODEL_NAME,
        realization=REALIZATION,
        stage_name=stage_name,
    )


def _execution_plan(
    state: ProductState,
) -> ExecutionPlan:
    """
    Return a representative execution result for the selected Realization.

    ExecutionPlan preserves the persistent Product state observed before
    execution. A non-current package Product therefore means manufacturing
    work was required, while a CURRENT package Product means the existing
    manufacturing result was reusable.
    """

    return ExecutionPlan(
        artifact_id=ARTIFACT_ID,
        model_name=MODEL_NAME,
        realization=REALIZATION,
        stages=(
            PlannedStageExecution(
                stage_name="package",
                product_states=(state,),
            ),
        ),
    )


def _emit_built_realization(
    artifact_id: str,
    *,
    realization: str,
    project_root: Path,
    event_sink=None,
) -> tuple[ExecutionPlan, ...]:
    """
    Simulate successful execution that had manufacturing work to perform.

    The fake application boundary preserves both contracts exposed by
    execute_artifact_build(): semantic execution observation and the
    ExecutionPlan returned for each selected build.
    """

    assert artifact_id == ARTIFACT_ID
    assert realization == REALIZATION
    assert event_sink is not None

    canonical = _canonical_3mf(
        project_root,
    )
    published = _published_3mf(
        project_root,
    )

    event_sink(
        _execution_event(
            "build.started",
        )
    )

    event_sink(
        _product_state_event(
            ProductState.ABSENT,
        )
    )

    event_sink(
        _execution_event(
            "stage.started",
            stage_name="package",
        )
    )

    canonical.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    canonical.write_bytes(
        b"new packaged 3mf",
    )

    published.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    published.write_bytes(
        canonical.read_bytes(),
    )

    event_sink(
        _execution_event(
            "stage.completed",
            stage_name="package",
        )
    )

    event_sink(
        _execution_event(
            "build.completed",
        )
    )

    return (
        _execution_plan(
            ProductState.ABSENT,
        ),
    )


def _emit_current_realization(
    artifact_id: str,
    *,
    realization: str,
    project_root: Path,
    event_sink=None,
) -> tuple[ExecutionPlan, ...]:
    """
    Simulate successful execution whose manufacturing Product is current.

    No Stage performs manufacturing work. The returned ExecutionPlan records
    the CURRENT persistent Product state observed by incremental planning.
    """

    assert artifact_id == ARTIFACT_ID
    assert realization == REALIZATION
    assert event_sink is not None

    event_sink(
        _execution_event(
            "build.started",
        )
    )

    event_sink(
        _product_state_event(
            ProductState.CURRENT,
        )
    )

    event_sink(
        _execution_event(
            "stage.skipped",
            stage_name="package",
        )
    )

    event_sink(
        _execution_event(
            "build.completed",
        )
    )

    return (
        _execution_plan(
            ProductState.CURRENT,
        ),
    )


def _install_existing_manufacturing_result(
    project_root: Path,
) -> tuple[Path, Path]:
    """
    Install representative current canonical and published 3MF Products.
    """

    canonical = _canonical_3mf(
        project_root,
    )
    published = _published_3mf(
        project_root,
    )

    canonical.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    canonical.write_bytes(
        b"existing packaged 3mf",
    )

    published.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    published.write_bytes(
        b"existing packaged 3mf",
    )

    return canonical, published


def _invoke_selected_realization(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    execute: Callable[..., tuple[ExecutionPlan, ...]],
    *,
    cli_args: tuple[str, ...] = (),
) -> Any:
    """
    Invoke one selected-Realization build with deterministic execution.
    """

    monkeypatch.chdir(
        tmp_path,
    )

    _install_materialization(
        monkeypatch,
    )

    monkeypatch.setattr(
        cmd_build,
        "execute_artifact_build",
        execute,
    )

    return _invoke(
        ARTIFACT_ID,
        "--realization",
        REALIZATION,
        cli_args=cli_args,
    )


# =========================================================
# Built result
# =========================================================


def test_build_reports_built_manufacturing_result(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """
    A selected Realization that required work reports a built result.

    Routine BUILD output identifies the Artifact, Realization, resulting
    state, and accessible manufacturing 3MF.
    """

    result = _invoke_selected_realization(
        monkeypatch,
        tmp_path,
        _emit_built_realization,
    )

    if result.exception is not None:
        raise result.exception

    assert result.exit_code == 0, result.output or repr(result.exception)

    published = _published_3mf(
        tmp_path,
    )
    relative_published = _relative_published_3mf(
        tmp_path,
    )

    assert published.is_file()

    output = result.output

    assert ARTIFACT_ID in output
    assert REALIZATION in output
    assert "built" in output.lower()
    assert str(relative_published) in output
    assert str(published) not in output


def test_build_result_reports_published_3mf_not_internal_canonical_product(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """
    Routine BUILD presents the operator-facing 3MF.

    The canonical Stage Product remains authoritative internally, but the
    operator should not need to navigate the Stage workspace to retrieve
    the manufacturing result.
    """

    result = _invoke_selected_realization(
        monkeypatch,
        tmp_path,
        _emit_built_realization,
    )

    assert result.exit_code == 0, result.output or repr(result.exception)

    published = _published_3mf(
        tmp_path,
    )
    relative_published = _relative_published_3mf(
        tmp_path,
    )
    canonical = _canonical_3mf(
        tmp_path,
    )

    assert canonical.is_file()
    assert published.is_file()

    assert str(relative_published) in result.output
    assert str(published) not in result.output
    assert str(canonical) not in result.output


# =========================================================
# Current result
# =========================================================


def test_build_reports_current_manufacturing_result_without_rebuilding(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """
    An already-current selected Realization remains a successful BUILD.

    BUILD means make the requested manufacturing Product current; it does
    not require manufacturing work to occur on every invocation.
    """

    canonical, published = _install_existing_manufacturing_result(
        tmp_path,
    )

    result = _invoke_selected_realization(
        monkeypatch,
        tmp_path,
        _emit_current_realization,
    )

    assert result.exit_code == 0, result.output or repr(result.exception)

    assert canonical.read_bytes() == b"existing packaged 3mf"
    assert published.read_bytes() == b"existing packaged 3mf"

    relative_published = _relative_published_3mf(
        tmp_path,
    )

    output = result.output

    assert ARTIFACT_ID in output
    assert REALIZATION in output
    assert "current" in output.lower()
    assert str(relative_published) in output
    assert str(published) not in output


def test_current_build_is_not_reported_as_built(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """
    BUILD distinguishes reuse of a current Product from newly built work.
    """

    _install_existing_manufacturing_result(
        tmp_path,
    )

    result = _invoke_selected_realization(
        monkeypatch,
        tmp_path,
        _emit_current_realization,
    )

    assert result.exit_code == 0, result.output or repr(result.exception)

    assert "current" in result.output.lower()
    assert "built" not in result.output.lower()


# =========================================================
# Lean routine presentation
# =========================================================


def test_build_default_output_does_not_narrate_stage_execution(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """
    Routine successful BUILD output emphasizes the manufacturing result.

    Semantic Stage events remain available to observers, but default CLI
    presentation does not require the operator to interpret the Stage
    lifecycle.
    """

    result = _invoke_selected_realization(
        monkeypatch,
        tmp_path,
        _emit_built_realization,
    )

    assert result.exit_code == 0, result.output or repr(result.exception)

    output = result.output

    assert "Stage started:" not in output
    assert "Stage completed:" not in output
    assert "Stage skipped:" not in output


def test_current_build_default_output_does_not_narrate_stage_reuse(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """
    Routine current-Product reuse is summarized as a manufacturing result.

    The operator does not need one skipped-Stage message per reusable Stage.
    """

    _install_existing_manufacturing_result(
        tmp_path,
    )

    result = _invoke_selected_realization(
        monkeypatch,
        tmp_path,
        _emit_current_realization,
    )

    assert result.exit_code == 0, result.output or repr(result.exception)

    assert "Stage skipped:" not in result.output


# =========================================================
# Semantic messaging
# =========================================================


def test_verbose_build_reports_stage_completion(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """
    -v reports manufacturing Stage progress.
    """

    result = _invoke_selected_realization(
        monkeypatch,
        tmp_path,
        _emit_built_realization,
        cli_args=("-v",),
    )

    assert result.exit_code == 0, result.output or repr(result.exception)

    output = result.output.lower()

    assert "package" in output
    assert "completed" in output


def test_verbose_build_reports_current_stage_as_reused(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """
    -v describes reuse of a current Stage Product in operator terminology.
    """

    _install_existing_manufacturing_result(
        tmp_path,
    )

    result = _invoke_selected_realization(
        monkeypatch,
        tmp_path,
        _emit_current_realization,
        cli_args=("-v",),
    )

    assert result.exit_code == 0, result.output or repr(result.exception)

    output = result.output.lower()

    assert "package" in output
    assert "reused" in output
    assert "skipped" not in output


def test_very_verbose_build_reports_product_state(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """
    -vv adds semantic Product-state diagnostics.
    """

    result = _invoke_selected_realization(
        monkeypatch,
        tmp_path,
        _emit_built_realization,
        cli_args=("-vv",),
    )

    assert result.exit_code == 0, result.output or repr(result.exception)

    output = result.output.lower()

    assert "package" in output
    assert "absent" in output


def test_quiet_build_suppresses_semantic_output(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """
    --quiet suppresses execution progress and the manufacturing result.
    """

    result = _invoke_selected_realization(
        monkeypatch,
        tmp_path,
        _emit_built_realization,
        cli_args=("--quiet",),
    )

    assert result.exit_code == 0, result.output or repr(result.exception)

    assert result.output == ""
