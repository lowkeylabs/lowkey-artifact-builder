"""
Tests for read-only artifact build status.
"""

# File: tests/cli/test_build_status.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from click.testing import CliRunner

import lowkey_artifact_builder.cli.cmd_build as cmd_build
from lowkey_artifact_builder.cli._main import cli
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


def _preserve_original(
    project_root: Path,
    artifact_id: str,
    *,
    content: bytes = b"artwork",
) -> Path:
    """
    Establish one ingested Artifact source in originals/.
    """

    originals = project_root / "originals"
    originals.mkdir(
        parents=True,
        exist_ok=True,
    )

    original = originals / f"{artifact_id}.png"
    original.write_bytes(content)

    return original


def _materialize_artifact(
    project_root: Path,
    artifact_id: str,
    *,
    content: bytes = b"artwork",
) -> Path:
    """
    Establish baseline materialized Artifact state for status tests.

    The Artifact identity is first established in originals/, then the
    corresponding workspace receives its baseline configuration and managed
    source.
    """

    original = _preserve_original(
        project_root,
        artifact_id,
        content=content,
    )

    artifact_dir = project_root / "artifacts" / artifact_id
    artifact_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    (artifact_dir / "artifact.toml").write_text(
        f'source = "artifacts/{artifact_id}/artifact.png"\n'
        f'original = "originals/{artifact_id}.png"\n',
        encoding="utf-8",
    )

    (artifact_dir / "artifact.png").write_bytes(content)

    return original


# =========================================================
# Bare build
# =========================================================


def test_bare_build_reports_project_status_without_execution(
    monkeypatch,
) -> None:
    """
    Bare build is a read-only project-status operation.

    It does not require an Artifact ID and does not request build execution.
    """

    executed: list[str] = []

    def fail_if_executed(
        *args: object,
        **kwargs: object,
    ) -> None:
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
    Bare build discovers ingested, materialized Artifacts in the project.

    Artifact discovery occurs without requesting build execution.
    """

    _materialize_artifact(
        tmp_path,
        "dog",
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

    _materialize_artifact(
        tmp_path,
        "dog",
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

    _materialize_artifact(
        tmp_path,
        "dog",
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

    _materialize_artifact(
        tmp_path,
        "dog",
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


# =========================================================
# Ingested but unmaterialized Artifacts
# =========================================================


def test_bare_build_discovers_ingested_unmaterialized_artifact(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    Bare build includes an Artifact known through originals/ even when its
    materialized Artifact workspace does not yet exist.

    Reporting status is read-only and must not materialize the Artifact.
    """

    original = _preserve_original(
        tmp_path,
        "dog",
        content=b"dog artwork",
    )

    monkeypatch.chdir(tmp_path)

    executed: list[str] = []

    monkeypatch.setattr(
        cmd_build,
        "execute_artifact_build",
        lambda artifact_id, **kwargs: executed.append(artifact_id),
    )

    result = _invoke()

    assert result.exit_code == 0

    assert "dog" in result.output
    assert "material" in result.output.lower()

    # Bare build remains read-only.
    assert executed == []
    assert original.read_bytes() == b"dog artwork"

    assert not (tmp_path / "artifacts" / "dog").exists()


def test_bare_build_reports_materialized_and_unmaterialized_artifacts(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    Bare build reports the complete ingested Artifact universe.

    A materialized Artifact continues through normal Realization/Product
    status reporting, while an ingested-only Artifact is reported as needing
    Artifact materialization.
    """

    _materialize_artifact(
        tmp_path,
        "cat",
        content=b"cat artwork",
    )

    dog_original = _preserve_original(
        tmp_path,
        "dog",
        content=b"dog artwork",
    )

    monkeypatch.chdir(tmp_path)

    realization_requests: list[str] = []

    def get_realizations(
        artifact_id: str,
        *,
        project_root: Path,
    ) -> tuple[str, ...]:
        realization_requests.append(artifact_id)

        assert artifact_id == "cat"

        return ("artwork_default",)

    monkeypatch.setattr(
        cmd_build,
        "get_realization_names",
        get_realizations,
    )

    build_plan = object()

    planned_artifacts: list[str] = []

    def create_plans(
        artifact_id: str,
        *,
        realization: str,
        project_root: Path,
    ) -> tuple[object, ...]:
        planned_artifacts.append(artifact_id)

        assert artifact_id == "cat"
        assert realization == "artwork_default"

        return (build_plan,)

    monkeypatch.setattr(
        cmd_build,
        "create_artifact_build_plans",
        create_plans,
    )

    execution_plan = ExecutionPlan(
        artifact_id="cat",
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

    assert "cat" in result.output
    assert "artwork_default" in result.output

    assert "dog" in result.output
    assert "material" in result.output.lower()

    # An unmaterialized Artifact cannot yet participate in ordinary
    # Realization or Product-state resolution.
    assert realization_requests == [
        "cat",
    ]
    assert planned_artifacts == [
        "cat",
    ]

    # Status inspection remains read-only.
    assert dog_original.read_bytes() == b"dog artwork"

    assert not (tmp_path / "artifacts" / "dog").exists()


# =========================================================
# Realization status derivation
# =========================================================


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
