"""
End-to-end acceptance tests for incremental completion identity.

These tests verify that structurally valid completion metadata cannot prove
persistent-product reuse when the record does not identify the realized
stage whose products are being evaluated.

A completion identity mismatch requires the affected stage to execute even
when its persistent products remain materialized and its recorded
fingerprint otherwise represents the current build context.

Successful incremental execution replaces mismatched completion metadata
with current stage identity and restores a fully reusable realization.
"""
# File: tests/acceptance/test_incremental_completion_identity.py
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
    StageCompletion,
    create_build_plans,
    execute_incremental_artifact_build,
    plan_incremental_execution,
    read_stage_completion,
    write_stage_completion,
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
            "config",
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


def _stage_working_dir(
    stage: PlannedStage,
) -> Path:
    """
    Return the common persistent-product directory for one stage.
    """

    assert stage.products

    working_dirs = {product.path.parent for product in stage.products}

    assert len(working_dirs) == 1

    return next(
        iter(
            working_dirs,
        )
    )


def _replace_stage_identity(
    stage: PlannedStage,
) -> StageCompletion:
    """
    Replace valid completion metadata with the wrong stage identity.

    All other completion fields, including the recorded fingerprint,
    remain unchanged.
    """

    working_dir = _stage_working_dir(
        stage,
    )

    completion = read_stage_completion(
        working_dir,
    )

    assert completion is not None
    assert completion.fingerprint is not None

    replacement = StageCompletion(
        artifact_id=completion.artifact_id,
        model_name=completion.model_name,
        realization=completion.realization,
        stage_name="not-the-current-stage",
        products=completion.products,
        fingerprint=completion.fingerprint,
    )

    write_stage_completion(
        working_dir,
        replacement,
    )

    return completion


# =========================================================
# Completion identity mismatch
# =========================================================


@pytest.mark.slow
def test_mismatched_completion_stage_identity_requires_execution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Completion metadata for another stage cannot prove product reuse.
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

    _replace_stage_identity(
        stage,
    )

    required = _required_stage_names(
        plan,
    )

    assert stage.name in required


@pytest.mark.slow
def test_mismatched_completion_stage_identity_preserves_downstream_reuse(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Completion identity damage does not change downstream build context.
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

    _replace_stage_identity(
        stage,
    )

    required = set(
        _required_stage_names(
            plan,
        )
    )

    assert stage.name in required
    assert "extrude" not in required
    assert "package" not in required


# =========================================================
# Completion identity recovery
# =========================================================


@pytest.mark.slow
def test_mismatched_completion_stage_identity_rebuild_reconverges(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Rebuilding replaces mismatched identity and restores full reuse.
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

    original = _replace_stage_identity(
        stage,
    )

    required_before = _required_stage_names(
        plan,
    )

    assert stage.name in required_before

    rebuilt = execute_incremental_artifact_build(
        plan,
    )

    rebuilt_names = tuple(execution.stage_name for execution in rebuilt.required_stages)

    assert rebuilt_names == required_before

    completion = read_stage_completion(
        _stage_working_dir(
            stage,
        ),
    )

    assert completion is not None

    assert completion.artifact_id == original.artifact_id
    assert completion.model_name == original.model_name
    assert completion.realization == original.realization
    assert completion.stage_name == original.stage_name
    assert completion.products == original.products
    assert completion.fingerprint == original.fingerprint

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
