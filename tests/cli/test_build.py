"""
Tests for the artifact build command.
"""

# File: tests/cli/test_build.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

import lowkey_artifact_builder.cli.cmd_build as cmd_build
from lowkey_artifact_builder.cli._main import cli
from lowkey_artifact_builder.config import ConfigError
from lowkey_artifact_builder.engine import (
    ExecutionPlan,
    PlannedStageExecution,
    ProductState,
)

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
# Build discovery
# =========================================================


def test_build_artifact_executes_each_effective_realization(
    monkeypatch,
) -> None:
    """
    A named Artifact builds each of its effective Realizations.

    Normal build execution addresses Artifact + Realization rather than
    Artifact + Variant.
    """

    realizations = (
        "artwork_default",
        "shape_default",
        "shape_ornament",
    )

    monkeypatch.setattr(
        cmd_build,
        "get_realization_names",
        lambda artifact_id, *, project_root: realizations,
    )

    executed: list[tuple[str, str]] = []

    def execute_artifact(
        artifact_id: str,
        *,
        realization: str,
        project_root: Path,
        event_sink=None,
    ) -> None:
        executed.append(
            (
                artifact_id,
                realization,
            )
        )

    monkeypatch.setattr(
        cmd_build,
        "execute_artifact_build",
        execute_artifact,
    )

    result = _invoke(
        "skippy",
    )

    assert result.exit_code == 0

    assert executed == [
        (
            "skippy",
            "artwork_default",
        ),
        (
            "skippy",
            "shape_default",
        ),
        (
            "skippy",
            "shape_ornament",
        ),
    ]


def test_build_multiple_artifacts_executes_effective_realizations_in_argument_order(
    monkeypatch,
) -> None:
    """
    Multiple named Artifacts build their effective Realizations in
    Artifact argument order and Realization discovery order.
    """

    realizations_by_artifact = {
        "skippy": (
            "artwork_default",
            "shape_default",
        ),
        "scooby": (
            "artwork_default",
            "shape_ornament",
        ),
    }

    monkeypatch.setattr(
        cmd_build,
        "get_realization_names",
        lambda artifact_id, *, project_root: realizations_by_artifact[artifact_id],
    )

    executed: list[tuple[str, str]] = []

    def execute_artifact(
        artifact_id: str,
        *,
        realization: str,
        project_root: Path,
        event_sink=None,
    ) -> None:
        executed.append(
            (
                artifact_id,
                realization,
            )
        )

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
        ("skippy", "artwork_default"),
        ("skippy", "shape_default"),
        ("scooby", "artwork_default"),
        ("scooby", "shape_ornament"),
    ]


def test_build_artifact_dry_run_plans_each_effective_realization(
    monkeypatch,
) -> None:
    """
    An unqualified Artifact dry-run plans each effective Realization
    without executing it.
    """

    realizations = (
        "artwork_default",
        "shape_default",
    )

    monkeypatch.setattr(
        cmd_build,
        "get_realization_names",
        lambda artifact_id, *, project_root: realizations,
    )

    plans = {
        "artwork_default": object(),
        "shape_default": object(),
    }

    planned: list[tuple[str, str]] = []
    prepared: list[object] = []
    displayed: list[object] = []
    executed: list[str] = []

    def create_plans(
        artifact_id: str,
        *,
        realization: str,
        project_root: Path,
    ) -> tuple[object, ...]:
        planned.append(
            (
                artifact_id,
                realization,
            )
        )
        return (plans[realization],)

    monkeypatch.setattr(
        cmd_build,
        "create_artifact_build_plans",
        create_plans,
    )

    monkeypatch.setattr(
        cmd_build,
        "prepare_incremental_build",
        lambda plan: prepared.append(plan),
    )

    monkeypatch.setattr(
        cmd_build,
        "display_build_plan",
        displayed.append,
    )

    monkeypatch.setattr(
        cmd_build,
        "execute_artifact_build",
        lambda artifact_id, **kwargs: executed.append(artifact_id),
    )

    result = _invoke(
        "skippy",
        "--dry-run",
    )

    assert result.exit_code == 0

    assert planned == [
        ("skippy", "artwork_default"),
        ("skippy", "shape_default"),
    ]
    assert prepared == [
        plans["artwork_default"],
        plans["shape_default"],
    ]
    assert displayed == [
        plans["artwork_default"],
        plans["shape_default"],
    ]
    assert executed == []


# =========================================================
# Build execution
# =========================================================


def test_build_passes_project_root(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    Explicit Artifact execution receives the current project root.
    """

    roots: list[Path] = []

    def execute_artifact(
        artifact_id: str,
        *,
        realization: str,
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
        "--realization",
        "shape_ornament",
    )

    assert result.exit_code == 0
    assert roots == [tmp_path]


# =========================================================
# Dry run
# =========================================================


def test_build_dry_run_prepares_plan_before_display(
    monkeypatch,
) -> None:
    """
    An explicitly selected dry run validates persistent execution state
    before displaying a plan.
    """

    plan = object()

    operations: list[tuple[str, object]] = []

    monkeypatch.setattr(
        cmd_build,
        "create_artifact_build_plans",
        lambda artifact_id, *, realization, project_root: (plan,),
    )

    def prepare(
        candidate: object,
    ) -> object:
        operations.append(
            (
                "prepare",
                candidate,
            )
        )

        return object()

    monkeypatch.setattr(
        cmd_build,
        "prepare_incremental_build",
        prepare,
        raising=False,
    )

    def display(
        candidate: object,
    ) -> None:
        operations.append(
            (
                "display",
                candidate,
            )
        )

    monkeypatch.setattr(
        cmd_build,
        "display_build_plan",
        display,
    )

    result = _invoke(
        "skippy",
        "--realization",
        "shape_ornament",
        "--dry-run",
    )

    assert result.exit_code == 0

    assert operations == [
        (
            "prepare",
            plan,
        ),
        (
            "display",
            plan,
        ),
    ]


# =========================================================
# Errors
# =========================================================


def test_build_plan_error_is_reported(
    monkeypatch,
) -> None:
    """
    Explicit dry-run BuildPlan errors are presented as Click command errors.
    """

    def create_plans(
        artifact_id: str,
        *,
        realization: str,
        project_root: Path,
    ):
        raise cmd_build.BuildPlanError("cannot create build plan")

    monkeypatch.setattr(
        cmd_build,
        "create_artifact_build_plans",
        create_plans,
    )

    result = _invoke(
        "skippy",
        "--realization",
        "shape_ornament",
        "--dry-run",
    )

    assert result.exit_code != 0
    assert "cannot create build plan" in result.output


def test_build_dry_run_configuration_error_is_reported_before_display(
    monkeypatch,
) -> None:
    """
    Explicit dry-run configuration validation failures are presented as
    Click command errors before the invalid plan is displayed.
    """

    plan = object()

    monkeypatch.setattr(
        cmd_build,
        "create_artifact_build_plans",
        lambda artifact_id, *, realization, project_root: (plan,),
    )

    def prepare(
        candidate: object,
    ) -> object:
        assert candidate is plan

        raise ConfigError(
            "required configuration is invalid",
        )

    monkeypatch.setattr(
        cmd_build,
        "prepare_incremental_build",
        prepare,
        raising=False,
    )

    displayed: list[object] = []

    monkeypatch.setattr(
        cmd_build,
        "display_build_plan",
        displayed.append,
    )

    result = _invoke(
        "skippy",
        "--realization",
        "shape_ornament",
        "--dry-run",
    )

    assert result.exit_code != 0
    assert "required configuration is invalid" in result.output
    assert displayed == []


def test_build_execution_error_is_reported(
    monkeypatch,
) -> None:
    """
    Explicit Artifact build errors are presented as Click command errors.
    """

    def execute_artifact(
        artifact_id: str,
        *,
        realization: str,
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
        "--realization",
        "shape_ornament",
    )

    assert result.exit_code != 0
    assert "cannot execute build" in result.output


def test_build_artifact_accepts_selected_realization(
    monkeypatch,
) -> None:
    """
    A selected Realization narrows normal build execution to that
    Artifact + Realization pair.
    """

    executed: list[tuple[str, str]] = []

    def execute_artifact(
        artifact_id: str,
        *,
        realization: str,
        project_root: Path,
        event_sink=None,
    ) -> None:
        executed.append(
            (
                artifact_id,
                realization,
            )
        )

    monkeypatch.setattr(
        cmd_build,
        "execute_artifact_build",
        execute_artifact,
    )

    result = _invoke(
        "skippy",
        "--realization",
        "shape_ornament",
    )

    assert result.exit_code == 0
    assert executed == [
        (
            "skippy",
            "shape_ornament",
        )
    ]


# =========================================================
# Independent stage execution
# =========================================================


def test_build_stage_accepts_selected_realization(
    monkeypatch,
) -> None:
    """
    Independent Stage execution may select an Artifact Realization.
    """

    executed: list[tuple[str, str, str | None]] = []

    def execute_stage(
        artifact_id: str,
        *,
        stage_name: str,
        realization: str | None = None,
        project_root: Path,
        input_paths=None,
        parameter_values=None,
        output_paths=None,
    ) -> None:
        executed.append(
            (
                artifact_id,
                stage_name,
                realization,
            )
        )

    monkeypatch.setattr(
        cmd_build,
        "execute_artifact_stage",
        execute_stage,
    )

    result = _invoke(
        "skippy",
        "--stage",
        "structure",
        "--realization",
        "alternate",
    )

    assert result.exit_code == 0

    assert executed == [
        (
            "skippy",
            "structure",
            "alternate",
        )
    ]


# =========================================================
# Explicit Variant selection
# =========================================================


# =========================================================
# All-Variant selection
# =========================================================


# =========================================================
# Planning integration
# =========================================================


def test_bare_build_reports_project_status_without_execution(
    monkeypatch,
) -> None:
    """
    Bare build is a read-only project-status operation.

    It does not require an Artifact ID and does not request build execution.
    """

    executed: list[str] = []

    def fail_if_executed(*args: object, **kwargs: object) -> None:
        executed.append("build")

    monkeypatch.setattr(
        cmd_build,
        "execute_artifact_build",
        fail_if_executed,
    )

    result = _invoke()

    assert result.exit_code == 0
    assert executed == []


def test_bare_build_discovers_project_artifacts(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    Bare build discovers persistent Artifacts in the current project.

    Artifact discovery is project-owned and occurs without requesting
    build execution.
    """

    artifact_dir = tmp_path / "artifacts" / "dog"
    artifact_dir.mkdir(parents=True)
    (artifact_dir / "artifact.toml").write_text(
        'source = "artifacts/dog/artifact.png"\n',
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)

    build_plan = object()

    monkeypatch.setattr(
        cmd_build,
        "create_artifact_build_plans",
        lambda artifact_id, *, realization, project_root: (build_plan,),
    )

    execution_plan = ExecutionPlan(
        artifact_id="dog",
        model_name="artwork",
        realization="artwork_default",
        stages=(),
    )

    monkeypatch.setattr(
        cmd_build,
        "prepare_incremental_build",
        lambda plan: execution_plan,
    )

    result = _invoke()

    assert result.exit_code == 0
    assert "dog" in result.output


def test_bare_build_reports_effective_realizations(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    Bare build reports status in terms of Artifact Realizations.

    Realization discovery is delegated to configuration rather than
    reconstructed from Variants by the CLI.
    """

    artifact_dir = tmp_path / "artifacts" / "dog"
    artifact_dir.mkdir(parents=True)
    (artifact_dir / "artifact.toml").write_text(
        'source = "artifacts/dog/artifact.png"\n',
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)

    realizations = (
        "artwork_default",
        "shape_default",
        "shape_ornament",
    )

    monkeypatch.setattr(
        cmd_build,
        "get_realization_names",
        lambda artifact_id, *, project_root: realizations,
    )

    build_plan = object()

    monkeypatch.setattr(
        cmd_build,
        "create_artifact_build_plans",
        lambda artifact_id, *, realization, project_root: (build_plan,),
    )

    monkeypatch.setattr(
        cmd_build,
        "prepare_incremental_build",
        lambda plan: ExecutionPlan(
            artifact_id="dog",
            model_name="artwork",
            realization="default",
            stages=(),
        ),
    )

    result = _invoke()

    assert result.exit_code == 0
    assert "dog" in result.output
    assert "artwork_default" in result.output
    assert "shape_default" in result.output
    assert "shape_ornament" in result.output


def test_bare_build_includes_canonical_realizations_not_in_artifact_config(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    Canonical Realizations participate in status without being serialized
    into artifact.toml.
    """

    artifact_dir = tmp_path / "artifacts" / "dog"
    artifact_dir.mkdir(parents=True)
    (artifact_dir / "artifact.toml").write_text(
        'source = "artifacts/dog/artifact.png"\n',
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)

    planned_realizations: list[str] = []

    build_plan = object()

    def create_plans(
        artifact_id: str,
        *,
        realization: str,
        project_root: Path,
    ) -> tuple[object, ...]:
        planned_realizations.append(realization)
        return (build_plan,)

    monkeypatch.setattr(
        cmd_build,
        "create_artifact_build_plans",
        create_plans,
    )

    monkeypatch.setattr(
        cmd_build,
        "prepare_incremental_build",
        lambda plan: ExecutionPlan(
            artifact_id="dog",
            model_name="artwork",
            realization="default",
            stages=(),
        ),
    )

    result = _invoke()

    assert result.exit_code == 0

    assert "artwork_default" in planned_realizations
    assert "shape_default" in planned_realizations
    assert "shape_ornament" in planned_realizations

    assert "artwork_default" in result.output
    assert "shape_default" in result.output
    assert "shape_ornament" in result.output


def test_bare_build_reports_earliest_noncurrent_product_state(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    Bare build reports the earliest non-current persistent product state
    in execution-plan order.
    """

    artifact_dir = tmp_path / "artifacts" / "dog"
    artifact_dir.mkdir(parents=True)
    (artifact_dir / "artifact.toml").write_text(
        'source = "artifacts/dog/artifact.png"\n',
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path)

    monkeypatch.setattr(
        cmd_build,
        "get_realization_names",
        lambda artifact_id, *, project_root: ("artwork_default",),
    )

    build_plan = object()

    monkeypatch.setattr(
        cmd_build,
        "create_artifact_build_plans",
        lambda artifact_id, *, realization, project_root: (build_plan,),
    )

    execution_plan = ExecutionPlan(
        artifact_id="dog",
        model_name="artwork",
        realization="artwork_default",
        stages=(
            PlannedStageExecution(
                stage_name="prepare",
                product_states=(ProductState.CURRENT,),
            ),
            PlannedStageExecution(
                stage_name="raster",
                product_states=(ProductState.STALE,),
            ),
            PlannedStageExecution(
                stage_name="vector",
                product_states=(ProductState.ABSENT,),
            ),
        ),
    )

    monkeypatch.setattr(
        cmd_build,
        "prepare_incremental_build",
        lambda plan: execution_plan,
        raising=False,
    )

    result = _invoke()

    assert result.exit_code == 0
    assert "dog" in result.output
    assert "artwork_default" in result.output
    assert "stale" in result.output


def test_execution_plan_status_is_current_when_all_persistent_products_are_current() -> None:
    """
    A Realization is current when every persistent product is current.
    """

    execution_plan = ExecutionPlan(
        artifact_id="dog",
        model_name="artwork",
        realization="artwork_default",
        stages=(
            PlannedStageExecution(
                stage_name="prepare",
                product_states=(ProductState.CURRENT,),
            ),
            PlannedStageExecution(
                stage_name="raster",
                product_states=(ProductState.CURRENT,),
            ),
            PlannedStageExecution(
                stage_name="vector",
                product_states=(ProductState.CURRENT,),
            ),
        ),
    )

    assert cmd_build._execution_plan_status(execution_plan) is ProductState.CURRENT


@pytest.mark.parametrize(
    "state",
    (
        ProductState.STALE,
        ProductState.INVALID,
        ProductState.INCOMPLETE,
        ProductState.ABSENT,
    ),
)
def test_execution_plan_status_preserves_earliest_noncurrent_product_state(
    state: ProductState,
) -> None:
    """
    Realization status preserves the engine's diagnostic ProductState
    vocabulary without applying a CLI severity ordering.
    """

    execution_plan = ExecutionPlan(
        artifact_id="dog",
        model_name="artwork",
        realization="artwork_default",
        stages=(
            PlannedStageExecution(
                stage_name="prepare",
                product_states=(ProductState.CURRENT,),
            ),
            PlannedStageExecution(
                stage_name="raster",
                product_states=(state,),
            ),
            PlannedStageExecution(
                stage_name="vector",
                product_states=(ProductState.STALE,),
            ),
        ),
    )

    assert cmd_build._execution_plan_status(execution_plan) is state


def test_build_realization_executes_across_project_artifacts(
    monkeypatch,
) -> None:
    """
    A Realization selected without Artifact IDs builds that Realization
    across the project Artifacts.
    """

    monkeypatch.setattr(
        cmd_build,
        "list_artifacts",
        lambda *, project_root: (
            "skippy",
            "scooby",
        ),
    )

    executed: list[tuple[str, str]] = []

    def execute_artifact(
        artifact_id: str,
        *,
        realization: str,
        project_root: Path,
        event_sink=None,
    ) -> None:
        executed.append(
            (
                artifact_id,
                realization,
            )
        )

    monkeypatch.setattr(
        cmd_build,
        "execute_artifact_build",
        execute_artifact,
    )

    result = _invoke(
        "--realization",
        "shape_ornament",
    )

    assert result.exit_code == 0
    assert executed == [
        (
            "skippy",
            "shape_ornament",
        ),
        (
            "scooby",
            "shape_ornament",
        ),
    ]


def test_build_all_executes_effective_realizations_across_project(
    monkeypatch,
) -> None:
    """
    --build-all builds every effective Realization of every project Artifact.
    """

    monkeypatch.setattr(
        cmd_build,
        "list_artifacts",
        lambda *, project_root: (
            "skippy",
            "scooby",
        ),
    )

    realizations = {
        "skippy": (
            "artwork_default",
            "shape_default",
            "shape_ornament",
        ),
        "scooby": (
            "artwork_default",
            "shape_ornament",
        ),
    }

    monkeypatch.setattr(
        cmd_build,
        "get_realization_names",
        lambda artifact_id, *, project_root: realizations[artifact_id],
    )

    executed: list[tuple[str, str]] = []

    def execute_artifact(
        artifact_id: str,
        *,
        realization: str,
        project_root: Path,
        event_sink=None,
    ) -> None:
        executed.append(
            (
                artifact_id,
                realization,
            )
        )

    monkeypatch.setattr(
        cmd_build,
        "execute_artifact_build",
        execute_artifact,
    )

    result = _invoke(
        "--build-all",
    )

    assert result.exit_code == 0
    assert executed == [
        (
            "skippy",
            "artwork_default",
        ),
        (
            "skippy",
            "shape_default",
        ),
        (
            "skippy",
            "shape_ornament",
        ),
        (
            "scooby",
            "artwork_default",
        ),
        (
            "scooby",
            "shape_ornament",
        ),
    ]


def test_build_artifact_realization_rebuilds_selected_scope(
    monkeypatch,
) -> None:
    """
    --rebuild forces the selected Artifact + Realization through rebuild.
    """

    rebuilt: list[tuple[str, str]] = []

    def rebuild_artifact(
        artifact_id: str,
        *,
        realization: str,
        project_root: Path,
        event_sink=None,
    ) -> None:
        rebuilt.append(
            (
                artifact_id,
                realization,
            )
        )

    monkeypatch.setattr(
        cmd_build,
        "rebuild_artifact",
        rebuild_artifact,
    )

    result = _invoke(
        "skippy",
        "--realization",
        "shape_ornament",
        "--rebuild",
    )

    assert result.exit_code == 0
    assert rebuilt == [
        (
            "skippy",
            "shape_ornament",
        ),
    ]


def test_build_artifact_rebuilds_all_effective_realizations(
    monkeypatch,
) -> None:
    """
    --rebuild without --realization rebuilds every effective Realization
    of the selected Artifact.
    """

    rebuilt: list[tuple[str, str]] = []

    monkeypatch.setattr(
        cmd_build,
        "get_realization_names",
        lambda artifact_id, *, project_root: (
            "artwork_default",
            "shape_default",
            "shape_ornament",
        ),
    )

    def rebuild_artifact(
        artifact_id: str,
        *,
        realization: str,
        project_root: Path,
        event_sink=None,
    ) -> None:
        rebuilt.append(
            (
                artifact_id,
                realization,
            )
        )

    monkeypatch.setattr(
        cmd_build,
        "rebuild_artifact",
        rebuild_artifact,
    )

    result = _invoke(
        "skippy",
        "--rebuild",
    )

    assert result.exit_code == 0
    assert rebuilt == [
        (
            "skippy",
            "artwork_default",
        ),
        (
            "skippy",
            "shape_default",
        ),
        (
            "skippy",
            "shape_ornament",
        ),
    ]


def test_build_realization_rebuilds_across_project_artifacts(
    monkeypatch,
) -> None:
    """
    --realization with --rebuild rebuilds that Realization across
    the applicable project Artifacts.
    """

    rebuilt: list[tuple[str, str]] = []

    monkeypatch.setattr(
        cmd_build,
        "list_artifacts",
        lambda *, project_root: (
            "alpha",
            "beta",
        ),
    )

    def rebuild_artifact(
        artifact_id: str,
        *,
        realization: str,
        project_root: Path,
        event_sink=None,
    ) -> None:
        rebuilt.append(
            (
                artifact_id,
                realization,
            )
        )

    monkeypatch.setattr(
        cmd_build,
        "rebuild_artifact",
        rebuild_artifact,
    )

    result = _invoke(
        "--realization",
        "shape_ornament",
        "--rebuild",
    )

    assert result.exit_code == 0
    assert rebuilt == [
        (
            "alpha",
            "shape_ornament",
        ),
        (
            "beta",
            "shape_ornament",
        ),
    ]


def test_rebuild_all_rebuilds_effective_realizations_across_project(
    monkeypatch,
) -> None:
    """
    --rebuild-all rebuilds every effective Realization of every
    project Artifact.
    """

    rebuilt: list[tuple[str, str]] = []

    monkeypatch.setattr(
        cmd_build,
        "list_artifacts",
        lambda *, project_root: (
            "alpha",
            "beta",
        ),
    )

    def get_realization_names(
        artifact_id: str,
        *,
        project_root: Path,
    ) -> tuple[str, ...]:
        if artifact_id == "alpha":
            return (
                "artwork_default",
                "shape_default",
            )

        return (
            "shape_default",
            "shape_ornament",
        )

    monkeypatch.setattr(
        cmd_build,
        "get_realization_names",
        get_realization_names,
    )

    def rebuild_artifact(
        artifact_id: str,
        *,
        realization: str,
        project_root: Path,
        event_sink=None,
    ) -> None:
        rebuilt.append(
            (
                artifact_id,
                realization,
            )
        )

    monkeypatch.setattr(
        cmd_build,
        "rebuild_artifact",
        rebuild_artifact,
    )

    result = _invoke(
        "--rebuild-all",
    )

    assert result.exit_code == 0
    assert rebuilt == [
        ("alpha", "artwork_default"),
        ("alpha", "shape_default"),
        ("beta", "shape_default"),
        ("beta", "shape_ornament"),
    ]


def test_build_all_rejects_rebuild_all(
    monkeypatch,
) -> None:
    """
    --build-all and --rebuild-all are mutually exclusive.
    """

    executed = False
    rebuilt = False

    def execute_realizations(
        artifact_ids: tuple[str, ...],
        *,
        dry_run: bool,
    ) -> None:
        nonlocal executed
        executed = True

    def rebuild_all(
        artifact_ids: tuple[str, ...],
    ) -> None:
        nonlocal rebuilt
        rebuilt = True

    monkeypatch.setattr(
        cmd_build,
        "list_artifacts",
        lambda *, project_root: ("alpha",),
    )
    monkeypatch.setattr(
        cmd_build,
        "_execute_realizations",
        execute_realizations,
    )
    monkeypatch.setattr(
        cmd_build,
        "_rebuild_all",
        rebuild_all,
    )

    result = _invoke(
        "--build-all",
        "--rebuild-all",
    )

    assert result.exit_code == 2
    assert "--build-all and --rebuild-all cannot be used together." in result.output
    assert executed is False
    assert rebuilt is False


def test_bare_rebuild_does_not_imply_project_wide_scope(
    monkeypatch,
) -> None:
    """
    Bare --rebuild is invalid even when the project contains one Artifact.

    Project-wide forced rebuilding requires --rebuild-all.
    """

    rebuilt: list[tuple[str, str]] = []

    monkeypatch.setattr(
        cmd_build,
        "list_artifacts",
        lambda *, project_root: ("alpha",),
    )

    monkeypatch.setattr(
        cmd_build,
        "get_realization_names",
        lambda artifact_id, *, project_root: ("shape_default",),
    )

    def rebuild_artifact(
        artifact_id: str,
        *,
        realization: str,
        project_root: Path,
        event_sink=None,
    ) -> None:
        rebuilt.append(
            (
                artifact_id,
                realization,
            )
        )

    monkeypatch.setattr(
        cmd_build,
        "rebuild_artifact",
        rebuild_artifact,
    )

    result = _invoke(
        "--rebuild",
    )

    assert result.exit_code == 2
    assert "--rebuild requires a narrowed build scope." in result.output
    assert rebuilt == []


def test_build_all_rejects_artifact_scope(
    monkeypatch,
) -> None:
    """
    --build-all is project-wide and cannot be narrowed by Artifact ID.
    """

    executed = False

    def execute_realizations(
        artifact_ids: tuple[str, ...],
        *,
        dry_run: bool,
    ) -> None:
        nonlocal executed
        executed = True

    monkeypatch.setattr(
        cmd_build,
        "_execute_realizations",
        execute_realizations,
    )

    result = _invoke(
        "skippy",
        "--build-all",
    )

    assert result.exit_code == 2
    assert "--build-all cannot be combined with Artifact IDs." in result.output
    assert executed is False


def test_rebuild_all_rejects_artifact_scope(
    monkeypatch,
) -> None:
    """
    --rebuild-all is project-wide and cannot be narrowed by Artifact ID.
    """

    rebuilt = False

    def rebuild_all(
        artifact_ids: tuple[str, ...],
    ) -> None:
        nonlocal rebuilt
        rebuilt = True

    monkeypatch.setattr(
        cmd_build,
        "_rebuild_all",
        rebuild_all,
    )

    result = _invoke(
        "skippy",
        "--rebuild-all",
    )

    assert result.exit_code == 2
    assert "--rebuild-all cannot be combined with Artifact IDs." in result.output
    assert rebuilt is False


def test_build_all_rejects_realization_scope(
    monkeypatch,
) -> None:
    """
    --build-all is project-wide and cannot be narrowed by Realization.
    """

    executed = False

    def execute_realizations(
        artifact_ids: tuple[str, ...],
        *,
        dry_run: bool,
    ) -> None:
        nonlocal executed
        executed = True

    monkeypatch.setattr(
        cmd_build,
        "list_artifacts",
        lambda *, project_root: ("alpha",),
    )
    monkeypatch.setattr(
        cmd_build,
        "_execute_realizations",
        execute_realizations,
    )

    result = _invoke(
        "--realization",
        "shape_ornament",
        "--build-all",
    )

    assert result.exit_code == 2
    assert "--build-all cannot be combined with --realization." in result.output
    assert executed is False


def test_rebuild_all_rejects_realization_scope(
    monkeypatch,
) -> None:
    """
    --rebuild-all is project-wide and cannot be narrowed by Realization.
    """

    rebuilt = False

    def rebuild_all(
        artifact_ids: tuple[str, ...],
    ) -> None:
        nonlocal rebuilt
        rebuilt = True

    monkeypatch.setattr(
        cmd_build,
        "list_artifacts",
        lambda *, project_root: ("alpha",),
    )
    monkeypatch.setattr(
        cmd_build,
        "_rebuild_all",
        rebuild_all,
    )

    result = _invoke(
        "--realization",
        "shape_ornament",
        "--rebuild-all",
    )

    assert result.exit_code == 2
    assert "--rebuild-all cannot be combined with --realization." in result.output
    assert rebuilt is False


def test_build_rejects_variant_option() -> None:
    """
    Variant selection is not a normal build execution coordinate.
    """

    result = _invoke(
        "skippy",
        "--variant",
        "shape.ornament",
    )

    assert result.exit_code == 2
    assert "No such option '--variant'" in result.output


def test_build_rejects_all_variants_option() -> None:
    """
    Variant enumeration is not a normal build execution coordinate.
    """

    result = _invoke(
        "skippy",
        "--all-variants",
    )

    assert result.exit_code == 2
    assert "No such option '--all-variants'" in result.output


def test_build_realization_continues_after_independent_artifact_failure(
    monkeypatch,
) -> None:
    """
    Failure building one Artifact does not prevent an independently
    requested Artifact from attempting the same Realization.

    The command reports failure after all requested independent builds
    have been attempted.
    """

    attempted: list[tuple[str, str]] = []

    def execute_artifact(
        artifact_id: str,
        *,
        realization: str,
        project_root: Path,
        event_sink=None,
    ) -> None:
        attempted.append(
            (
                artifact_id,
                realization,
            )
        )

        if artifact_id == "smith-dog":
            raise cmd_build.BuildError(
                "smith-dog build failed",
            )

    monkeypatch.setattr(
        cmd_build,
        "execute_artifact_build",
        execute_artifact,
    )

    result = _invoke(
        "smith-dog",
        "jones-dog",
        "--realization",
        "shape_ornament",
    )

    assert attempted == [
        (
            "smith-dog",
            "shape_ornament",
        ),
        (
            "jones-dog",
            "shape_ornament",
        ),
    ]

    assert result.exit_code != 0
    assert "smith-dog build failed" in result.output


def test_build_realization_reports_each_independent_artifact_failure(
    monkeypatch,
) -> None:
    """
    Failures from multiple independently requested Artifact builds remain
    visible after all requested work has been attempted.
    """

    attempted: list[str] = []

    def execute_artifact(
        artifact_id: str,
        *,
        realization: str,
        project_root: Path,
        event_sink=None,
    ) -> None:
        attempted.append(
            artifact_id,
        )

        raise cmd_build.BuildError(
            f"{artifact_id} build failed",
        )

    monkeypatch.setattr(
        cmd_build,
        "execute_artifact_build",
        execute_artifact,
    )

    result = _invoke(
        "smith-dog",
        "jones-dog",
        "--realization",
        "shape_ornament",
    )

    assert attempted == [
        "smith-dog",
        "jones-dog",
    ]

    assert result.exit_code != 0
    assert "smith-dog build failed" in result.output
    assert "jones-dog build failed" in result.output


def test_build_realization_dry_run_continues_after_independent_artifact_failure(
    monkeypatch,
) -> None:
    """
    A dry-run planning failure for one Artifact does not prevent an
    independently requested Artifact from being planned and displayed.

    The command reports failure after all requested independent dry-run
    work has been attempted.
    """

    plans = {
        "jones-dog": object(),
    }

    attempted: list[tuple[str, str]] = []
    displayed: list[object] = []

    def create_plans(
        artifact_id: str,
        *,
        realization: str,
        project_root: Path,
    ) -> tuple[object, ...]:
        attempted.append(
            (
                artifact_id,
                realization,
            )
        )

        if artifact_id == "smith-dog":
            raise cmd_build.BuildPlanError(
                "smith-dog planning failed",
            )

        return (plans[artifact_id],)

    monkeypatch.setattr(
        cmd_build,
        "create_artifact_build_plans",
        create_plans,
    )

    monkeypatch.setattr(
        cmd_build,
        "prepare_incremental_build",
        lambda plan: object(),
    )

    monkeypatch.setattr(
        cmd_build,
        "display_build_plan",
        displayed.append,
    )

    result = _invoke(
        "smith-dog",
        "jones-dog",
        "--realization",
        "shape_ornament",
        "--dry-run",
    )

    assert attempted == [
        (
            "smith-dog",
            "shape_ornament",
        ),
        (
            "jones-dog",
            "shape_ornament",
        ),
    ]

    assert displayed == [
        plans["jones-dog"],
    ]

    assert result.exit_code != 0
    assert "smith-dog planning failed" in result.output


def test_build_artifact_continues_after_independent_realization_failure(
    monkeypatch,
) -> None:
    """
    Failure building one effective Realization does not prevent another
    independent Realization of the same Artifact from being attempted.

    The command reports failure after all requested independent
    Realizations have been attempted.
    """

    realizations = (
        "artwork_default",
        "shape_default",
    )

    monkeypatch.setattr(
        cmd_build,
        "get_realization_names",
        lambda artifact_id, *, project_root: realizations,
    )

    attempted: list[tuple[str, str]] = []

    def execute_artifact(
        artifact_id: str,
        *,
        realization: str,
        project_root: Path,
        event_sink=None,
    ) -> None:
        attempted.append(
            (
                artifact_id,
                realization,
            )
        )

        if realization == "artwork_default":
            raise cmd_build.BuildError(
                "artwork_default build failed",
            )

    monkeypatch.setattr(
        cmd_build,
        "execute_artifact_build",
        execute_artifact,
    )

    result = _invoke(
        "smith-dog",
    )

    assert attempted == [
        (
            "smith-dog",
            "artwork_default",
        ),
        (
            "smith-dog",
            "shape_default",
        ),
    ]

    assert result.exit_code != 0
    assert "artwork_default build failed" in result.output


def test_build_artifact_reports_each_independent_realization_failure(
    monkeypatch,
) -> None:
    """
    Failures from multiple independent Realizations of one Artifact remain
    visible after all requested Realizations have been attempted.
    """

    realizations = (
        "artwork_default",
        "shape_default",
    )

    monkeypatch.setattr(
        cmd_build,
        "get_realization_names",
        lambda artifact_id, *, project_root: realizations,
    )

    attempted: list[str] = []

    def execute_artifact(
        artifact_id: str,
        *,
        realization: str,
        project_root: Path,
        event_sink=None,
    ) -> None:
        attempted.append(
            realization,
        )

        raise cmd_build.BuildError(
            f"{realization} build failed",
        )

    monkeypatch.setattr(
        cmd_build,
        "execute_artifact_build",
        execute_artifact,
    )

    result = _invoke(
        "smith-dog",
    )

    assert attempted == [
        "artwork_default",
        "shape_default",
    ]

    assert result.exit_code != 0
    assert "artwork_default build failed" in result.output
    assert "shape_default build failed" in result.output


def test_build_artifacts_continue_after_realization_failure_in_prior_artifact(
    monkeypatch,
) -> None:
    """
    Failure of a Realization in one Artifact does not prevent independently
    requested Realizations of a later Artifact from being attempted.
    """

    realizations_by_artifact = {
        "smith-dog": (
            "artwork_default",
            "shape_default",
        ),
        "jones-dog": (
            "artwork_default",
            "shape_ornament",
        ),
    }

    monkeypatch.setattr(
        cmd_build,
        "get_realization_names",
        lambda artifact_id, *, project_root: realizations_by_artifact[artifact_id],
    )

    attempted: list[tuple[str, str]] = []

    def execute_artifact(
        artifact_id: str,
        *,
        realization: str,
        project_root: Path,
        event_sink=None,
    ) -> None:
        attempted.append(
            (
                artifact_id,
                realization,
            )
        )

        if artifact_id == "smith-dog" and realization == "shape_default":
            raise cmd_build.BuildError(
                "smith-dog shape_default build failed",
            )

    monkeypatch.setattr(
        cmd_build,
        "execute_artifact_build",
        execute_artifact,
    )

    result = _invoke(
        "smith-dog",
        "jones-dog",
    )

    assert attempted == [
        ("smith-dog", "artwork_default"),
        ("smith-dog", "shape_default"),
        ("jones-dog", "artwork_default"),
        ("jones-dog", "shape_ornament"),
    ]

    assert result.exit_code != 0
    assert "smith-dog shape_default build failed" in result.output


def test_rebuild_realization_continues_after_independent_artifact_failure(
    monkeypatch,
) -> None:
    """
    Failure rebuilding one Artifact does not prevent an independently
    requested Artifact from rebuilding the same Realization.

    The command reports failure after all requested independent rebuilds
    have been attempted.
    """

    attempted: list[tuple[str, str]] = []

    def rebuild_artifact(
        artifact_id: str,
        *,
        realization: str,
        project_root: Path,
        event_sink=None,
    ) -> None:
        attempted.append(
            (
                artifact_id,
                realization,
            )
        )

        if artifact_id == "smith-dog":
            raise cmd_build.BuildError(
                "smith-dog rebuild failed",
            )

    monkeypatch.setattr(
        cmd_build,
        "rebuild_artifact",
        rebuild_artifact,
    )

    result = _invoke(
        "smith-dog",
        "jones-dog",
        "--realization",
        "shape_ornament",
        "--rebuild",
    )

    assert attempted == [
        (
            "smith-dog",
            "shape_ornament",
        ),
        (
            "jones-dog",
            "shape_ornament",
        ),
    ]

    assert result.exit_code != 0
    assert "smith-dog rebuild failed" in result.output


def test_rebuild_realization_reports_each_independent_artifact_failure(
    monkeypatch,
) -> None:
    """
    Failures from multiple independently requested Artifact rebuilds remain
    visible after all requested work has been attempted.
    """

    attempted: list[str] = []

    def rebuild_artifact(
        artifact_id: str,
        *,
        realization: str,
        project_root: Path,
        event_sink=None,
    ) -> None:
        attempted.append(
            artifact_id,
        )

        raise cmd_build.BuildError(
            f"{artifact_id} rebuild failed",
        )

    monkeypatch.setattr(
        cmd_build,
        "rebuild_artifact",
        rebuild_artifact,
    )

    result = _invoke(
        "smith-dog",
        "jones-dog",
        "--realization",
        "shape_ornament",
        "--rebuild",
    )

    assert attempted == [
        "smith-dog",
        "jones-dog",
    ]

    assert result.exit_code != 0
    assert "smith-dog rebuild failed" in result.output
    assert "jones-dog rebuild failed" in result.output


def test_rebuild_artifact_continues_after_independent_realization_failure(
    monkeypatch,
) -> None:
    """
    Failure rebuilding one effective Realization does not prevent another
    independent Realization of the same Artifact from being attempted.

    The command reports failure after all requested independent
    Realizations have been attempted.
    """

    realizations = (
        "artwork_default",
        "shape_default",
    )

    monkeypatch.setattr(
        cmd_build,
        "get_realization_names",
        lambda artifact_id, *, project_root: realizations,
    )

    attempted: list[tuple[str, str]] = []

    def rebuild_artifact(
        artifact_id: str,
        *,
        realization: str,
        project_root: Path,
        event_sink=None,
    ) -> None:
        attempted.append(
            (
                artifact_id,
                realization,
            )
        )

        if realization == "artwork_default":
            raise cmd_build.BuildError(
                "artwork_default rebuild failed",
            )

    monkeypatch.setattr(
        cmd_build,
        "rebuild_artifact",
        rebuild_artifact,
    )

    result = _invoke(
        "smith-dog",
        "--rebuild",
    )

    assert attempted == [
        (
            "smith-dog",
            "artwork_default",
        ),
        (
            "smith-dog",
            "shape_default",
        ),
    ]

    assert result.exit_code != 0
    assert "artwork_default rebuild failed" in result.output


def test_rebuild_artifact_reports_each_independent_realization_failure(
    monkeypatch,
) -> None:
    """
    Failures from multiple independent Realizations of one Artifact remain
    visible after all requested Realizations have been attempted.
    """

    realizations = (
        "artwork_default",
        "shape_default",
    )

    monkeypatch.setattr(
        cmd_build,
        "get_realization_names",
        lambda artifact_id, *, project_root: realizations,
    )

    attempted: list[str] = []

    def rebuild_artifact(
        artifact_id: str,
        *,
        realization: str,
        project_root: Path,
        event_sink=None,
    ) -> None:
        attempted.append(
            realization,
        )

        raise cmd_build.BuildError(
            f"{realization} rebuild failed",
        )

    monkeypatch.setattr(
        cmd_build,
        "rebuild_artifact",
        rebuild_artifact,
    )

    result = _invoke(
        "smith-dog",
        "--rebuild",
    )

    assert attempted == [
        "artwork_default",
        "shape_default",
    ]

    assert result.exit_code != 0
    assert "artwork_default rebuild failed" in result.output
    assert "shape_default rebuild failed" in result.output


def test_rebuild_all_continues_after_independent_realization_failure(
    monkeypatch,
) -> None:
    """
    A project-wide rebuild continues independent Realizations and Artifacts
    after an individual rebuild failure.

    The command reports failure after all requested independent rebuilds
    have been attempted.
    """

    artifacts = (
        "smith-dog",
        "jones-dog",
    )

    realizations_by_artifact = {
        "smith-dog": (
            "artwork_default",
            "shape_default",
        ),
        "jones-dog": (
            "artwork_default",
            "shape_ornament",
        ),
    }

    monkeypatch.setattr(
        cmd_build,
        "list_artifacts",
        lambda *, project_root: artifacts,
    )

    monkeypatch.setattr(
        cmd_build,
        "get_realization_names",
        lambda artifact_id, *, project_root: (realizations_by_artifact[artifact_id]),
    )

    attempted: list[tuple[str, str]] = []

    def rebuild_artifact(
        artifact_id: str,
        *,
        realization: str,
        project_root: Path,
        event_sink=None,
    ) -> None:
        attempted.append(
            (
                artifact_id,
                realization,
            )
        )

        if artifact_id == "smith-dog" and realization == "shape_default":
            raise cmd_build.BuildError(
                "smith-dog shape_default rebuild failed",
            )

    monkeypatch.setattr(
        cmd_build,
        "rebuild_artifact",
        rebuild_artifact,
    )

    result = _invoke(
        "--rebuild-all",
    )

    assert attempted == [
        (
            "smith-dog",
            "artwork_default",
        ),
        (
            "smith-dog",
            "shape_default",
        ),
        (
            "jones-dog",
            "artwork_default",
        ),
        (
            "jones-dog",
            "shape_ornament",
        ),
    ]

    assert result.exit_code != 0
    assert "smith-dog shape_default rebuild failed" in result.output


def test_rebuild_all_continues_after_artifact_realization_discovery_failure(
    monkeypatch,
) -> None:
    """
    Failure discovering Realizations for one Artifact does not prevent
    later project Artifacts from being rebuilt.
    """

    artifacts = (
        "smith-dog",
        "jones-dog",
    )

    monkeypatch.setattr(
        cmd_build,
        "list_artifacts",
        lambda *, project_root: artifacts,
    )

    discovered: list[str] = []

    def get_realizations(
        artifact_id: str,
        *,
        project_root: Path,
    ) -> tuple[str, ...]:
        discovered.append(
            artifact_id,
        )

        if artifact_id == "smith-dog":
            raise cmd_build.ConfigError(
                "smith-dog configuration failed",
            )

        return ("shape_default",)

    monkeypatch.setattr(
        cmd_build,
        "get_realization_names",
        get_realizations,
    )

    attempted: list[tuple[str, str]] = []

    def rebuild_artifact(
        artifact_id: str,
        *,
        realization: str,
        project_root: Path,
        event_sink=None,
    ) -> None:
        attempted.append(
            (
                artifact_id,
                realization,
            )
        )

    monkeypatch.setattr(
        cmd_build,
        "rebuild_artifact",
        rebuild_artifact,
    )

    result = _invoke(
        "--rebuild-all",
    )

    assert discovered == [
        "smith-dog",
        "jones-dog",
    ]

    assert attempted == [
        (
            "jones-dog",
            "shape_default",
        ),
    ]

    assert result.exit_code != 0
    assert "smith-dog configuration failed" in result.output


def test_build_all_rejects_rebuild() -> None:
    """
    Project-wide incremental build and narrowed rebuild are distinct modes.
    """

    result = _invoke(
        "--build-all",
        "--rebuild",
    )

    assert result.exit_code == 2
    assert "--build-all and --rebuild cannot be used together." in result.output


def test_rebuild_all_rejects_rebuild() -> None:
    """
    Project-wide rebuild and narrowed rebuild cannot be requested together.
    """

    result = _invoke(
        "--rebuild-all",
        "--rebuild",
    )

    assert result.exit_code == 2
    assert "--rebuild-all and --rebuild cannot be used together." in result.output


def test_build_requested_realization_does_not_fall_back_to_available_realization(
    monkeypatch,
) -> None:
    """
    A requested Realization remains the execution coordinate for every
    selected Artifact.

    The CLI must not substitute another available Realization when the
    requested one is unavailable for an Artifact.
    """

    artifacts = (
        "smith-dog",
        "jones-dog",
    )

    monkeypatch.setattr(
        cmd_build,
        "list_artifacts",
        lambda *, project_root: artifacts,
    )

    attempted: list[tuple[str, str]] = []

    def execute_artifact_build(
        artifact_id: str,
        *,
        realization: str,
        project_root: Path,
        event_sink=None,
    ) -> None:
        attempted.append(
            (
                artifact_id,
                realization,
            )
        )

        if artifact_id == "smith-dog":
            raise cmd_build.ConfigError(
                "Realization 'shape_ornament' is not available for Artifact 'smith-dog'."
            )

    monkeypatch.setattr(
        cmd_build,
        "execute_artifact_build",
        execute_artifact_build,
    )

    result = _invoke(
        "--realization",
        "shape_ornament",
    )

    assert attempted == [
        (
            "smith-dog",
            "shape_ornament",
        ),
        (
            "jones-dog",
            "shape_ornament",
        ),
    ]

    assert result.exit_code != 0
    assert (
        "Realization 'shape_ornament' is not available for Artifact 'smith-dog'."
    ) in result.output


def test_build_all_rejects_stage_execution() -> None:
    """
    Project-wide incremental build cannot be combined with independent
    stage execution.
    """

    result = _invoke(
        "--build-all",
        "--stage",
        "extrude",
    )

    assert result.exit_code == 2
    assert "--build-all cannot be combined with --stage." in result.output


def test_rebuild_all_rejects_stage_execution() -> None:
    """
    Project-wide rebuild cannot be combined with independent stage
    execution.
    """

    result = _invoke(
        "--rebuild-all",
        "--stage",
        "extrude",
    )

    assert result.exit_code == 2
    assert "--rebuild-all cannot be combined with --stage." in result.output


def test_rebuild_rejects_stage_execution() -> None:
    """
    Narrowed rebuild cannot be combined with independent stage execution.
    """

    result = _invoke(
        "skippy",
        "--stage",
        "extrude",
        "--rebuild",
    )

    assert result.exit_code == 2
    assert "--rebuild cannot be combined with --stage." in result.output


def test_realization_rebuild_rejects_stage_execution() -> None:
    """
    Realization-scoped rebuild cannot be combined with independent
    stage execution.
    """

    result = _invoke(
        "skippy",
        "--realization",
        "shape_ornament",
        "--stage",
        "extrude",
        "--rebuild",
    )

    assert result.exit_code == 2
    assert "--rebuild cannot be combined with --stage." in result.output


def test_rebuild_rejects_dry_run() -> None:
    """
    Narrowed rebuild must not silently perform work when --dry-run is
    requested.
    """

    result = _invoke(
        "skippy",
        "--rebuild",
        "--dry-run",
    )

    assert result.exit_code == 2
    assert "--rebuild cannot be combined with --dry-run." in result.output


def test_realization_rebuild_rejects_dry_run() -> None:
    """
    Realization-scoped rebuild must not silently perform work when
    --dry-run is requested.
    """

    result = _invoke(
        "skippy",
        "--realization",
        "shape_ornament",
        "--rebuild",
        "--dry-run",
    )

    assert result.exit_code == 2
    assert "--rebuild cannot be combined with --dry-run." in result.output


def test_rebuild_all_rejects_dry_run() -> None:
    """
    Project-wide rebuild must not silently perform work when --dry-run is
    requested.
    """

    result = _invoke(
        "--rebuild-all",
        "--dry-run",
    )

    assert result.exit_code == 2
    assert "--rebuild-all cannot be combined with --dry-run." in result.output
