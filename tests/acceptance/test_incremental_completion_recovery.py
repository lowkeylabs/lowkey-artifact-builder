"""
End-to-end acceptance tests for incremental completion-metadata recovery.

These tests verify that persistent products are not considered reusable
when their successful completion metadata is missing.

Missing completion provenance requires the affected stage to execute again
even when its declared products remain materialized. Successful incremental
execution restores completion metadata and a fully reusable realization.

Malformed completion metadata is treated as persistent-state corruption and
fails explicitly rather than being silently interpreted as missing state.
"""
# File: tests/acceptance/test_incremental_completion_recovery.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from click.testing import CliRunner

from lowkey_artifact_builder.cli._main import cli
from lowkey_artifact_builder.engine import (
    BuildPlan,
    PlannedStage,
    completion_path,
    create_build_plans,
    execute_incremental_artifact_build,
    plan_incremental_execution,
)

# =========================================================
# Helpers
# =========================================================


def _configure_artifact(
    *,
    project_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Configure the acceptance artifact through the public CLI.
    """

    repository_root = Path(__file__).resolve().parents[2]

    fixture_source = repository_root / "tests" / "assets" / "nydeli-clean.png"

    assert fixture_source.is_file(), f"Acceptance artwork does not exist: {fixture_source}"

    source = project_root / "nydeli-clean.png"

    shutil.copy2(
        fixture_source,
        source,
    )

    monkeypatch.chdir(
        project_root,
    )

    runner = CliRunner()

    config_result = runner.invoke(
        cli,
        [
            "create",
            "nydeli",
        ],
        input=("1\n1\n70\n"),
    )

    assert config_result.exit_code == 0, (
        f"Artifact configuration failed:\n{config_result.output}\n{config_result.exception!r}"
    )


def _create_plan(
    project_root: Path,
) -> BuildPlan:
    """
    Return the single realized acceptance BuildPlan.
    """

    plans = create_build_plans(
        "nydeli",
        project_root=project_root,
    )

    assert len(plans) == 1

    plan = plans[0]

    assert plan.artifact_id == "nydeli"
    assert plan.model_name == "artwork"
    assert plan.realization_name == "default"

    return plan


def _required_stage_names(
    plan: BuildPlan,
) -> tuple[str, ...]:
    """
    Return stages currently requiring incremental execution.
    """

    execution_plan = plan_incremental_execution(
        plan,
    )

    return tuple(execution.stage_name for execution in execution_plan.required_stages)


def _stage(
    plan: BuildPlan,
    name: str,
) -> PlannedStage:
    """
    Return one realized stage by name.
    """

    matches = tuple(stage for stage in plan.stages if stage.name == name)

    assert len(matches) == 1, f"Expected exactly one stage named {name!r}, found {len(matches)}."

    return matches[0]


def _completion_file(
    stage: PlannedStage,
) -> Path:
    """
    Return completion metadata path for one persistent stage.
    """

    assert stage.products

    working_dirs = {product.path.parent for product in stage.products}

    assert len(working_dirs) == 1

    working_dir = next(
        iter(
            working_dirs,
        )
    )

    return completion_path(
        working_dir,
    )


# =========================================================
# Missing completion metadata
# =========================================================


@pytest.mark.slow
def test_missing_completion_metadata_requires_stage_execution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Materialized products without completion provenance are not reusable.
    """

    project_root = tmp_path

    _configure_artifact(
        project_root=project_root,
        monkeypatch=monkeypatch,
    )

    plan = _create_plan(
        project_root,
    )

    execute_incremental_artifact_build(
        plan,
    )

    assert (
        _required_stage_names(
            plan,
        )
        == ()
    )

    stage = _stage(
        plan,
        "vector",
    )

    completion = _completion_file(
        stage,
    )

    assert completion.is_file()

    products = tuple(product.path for product in stage.products)

    assert products
    assert all(product.is_file() for product in products)

    completion.unlink()

    required = _required_stage_names(
        plan,
    )

    assert stage.name in required

    # Product materialization alone must not prove reuse.
    assert all(product.is_file() for product in products)


# =========================================================
# Invalid completion metadata
# =========================================================


@pytest.mark.slow
def test_invalid_completion_metadata_fails_incremental_planning(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Invalid completion metadata fails rather than being silently ignored.
    """

    project_root = tmp_path

    _configure_artifact(
        project_root=project_root,
        monkeypatch=monkeypatch,
    )

    plan = _create_plan(
        project_root,
    )

    execute_incremental_artifact_build(
        plan,
    )

    assert (
        _required_stage_names(
            plan,
        )
        == ()
    )

    stage = _stage(
        plan,
        "vector",
    )

    completion = _completion_file(
        stage,
    )

    assert completion.is_file()

    completion.write_text(
        "this is not valid completion metadata\n",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="Invalid stage completion metadata",
    ):
        plan_incremental_execution(
            plan,
        )


# =========================================================
# Completion recovery
# =========================================================


@pytest.mark.slow
def test_missing_completion_metadata_real_rebuild_reconverges(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Incremental execution recreates completion provenance and restores reuse.
    """

    project_root = tmp_path

    _configure_artifact(
        project_root=project_root,
        monkeypatch=monkeypatch,
    )

    plan = _create_plan(
        project_root,
    )

    execute_incremental_artifact_build(
        plan,
    )

    stage = _stage(
        plan,
        "vector",
    )

    completion = _completion_file(
        stage,
    )

    assert completion.is_file()

    completion.unlink()

    required_before = _required_stage_names(
        plan,
    )

    assert stage.name in required_before

    rebuilt = execute_incremental_artifact_build(
        plan,
    )

    rebuilt_names = tuple(execution.stage_name for execution in rebuilt.required_stages)

    assert rebuilt_names == required_before

    assert completion.is_file()

    assert (
        _required_stage_names(
            plan,
        )
        == ()
    )

    second = execute_incremental_artifact_build(
        plan,
    )

    assert second.required_stages == ()
