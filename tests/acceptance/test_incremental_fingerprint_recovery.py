"""
End-to-end acceptance tests for incremental fingerprint recovery.

These tests verify that structurally valid completion metadata cannot prove
persistent-product reuse when its recorded build-context fingerprint differs
from the fingerprint required by the current realization.

A fingerprint mismatch invalidates the affected producing stage without
changing the required provenance of otherwise unchanged downstream stages.
Successful incremental execution records current provenance and restores a
fully reusable realization.
"""
# File: tests/acceptance/test_incremental_fingerprint_recovery.py
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
    ProductFingerprint,
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


def _replace_recorded_fingerprint(
    *,
    plan: BuildPlan,
    stage: PlannedStage,
) -> ProductFingerprint:
    """
    Replace one valid completion record's fingerprint with a mismatch.

    All completion identity and product metadata remain valid. Only the
    recorded build-context fingerprint is changed.
    """

    working_dir = _stage_working_dir(
        stage,
    )

    completion = read_stage_completion(
        working_dir,
    )

    assert completion is not None
    assert completion.fingerprint is not None

    original = completion.fingerprint

    replacement = ProductFingerprint(
        algorithm=original.algorithm,
        value="0" * len(original.value),
    )

    assert replacement != original

    write_stage_completion(
        working_dir,
        StageCompletion(
            artifact_id=completion.artifact_id,
            model_name=completion.model_name,
            realization=completion.realization,
            stage_name=completion.stage_name,
            products=completion.products,
            fingerprint=replacement,
        ),
    )

    return original


# =========================================================
# Fingerprint mismatch
# =========================================================


@pytest.mark.slow
def test_mismatched_recorded_fingerprint_requires_stage_execution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Valid completion metadata with stale provenance is not reusable.
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

    _replace_recorded_fingerprint(
        plan=plan,
        stage=stage,
    )

    required = _required_stage_names(
        plan,
    )

    assert stage.name in required


@pytest.mark.slow
def test_mismatched_recorded_fingerprint_does_not_invalidate_downstream_context(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Recorded provenance damage does not change downstream requirements.

    The affected stage must execute because its recorded fingerprint does
    not prove freshness. Required fingerprints themselves are unchanged,
    so otherwise-current downstream products remain reusable.
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

    _replace_recorded_fingerprint(
        plan=plan,
        stage=stage,
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
# Fingerprint recovery
# =========================================================


@pytest.mark.slow
def test_mismatched_recorded_fingerprint_real_rebuild_reconverges(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Rebuilding stale recorded provenance restores current completion state.
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

    original = _replace_recorded_fingerprint(
        plan=plan,
        stage=stage,
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
    assert completion.fingerprint == original

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
