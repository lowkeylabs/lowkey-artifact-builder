"""
End-to-end acceptance tests for incremental product recovery.

These tests verify that persistent products cannot be reused when their
materialized filesystem state no longer agrees with successful completion
metadata.

Missing or invalid persistent products require their producing stage to
execute again. Downstream stages whose required build context is unchanged
remain reusable when their own persistent state remains valid.

Successful incremental execution repairs the damaged realization and
restores full reuse.
"""
# File: tests/acceptance/test_incremental_product_recovery.py
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

    return tuple(stage.stage_name for stage in execution_plan.required_stages)


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


# =========================================================
# Missing product detection
# =========================================================


@pytest.mark.slow
def test_missing_persistent_product_requires_producing_stage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    A missing persistent product invalidates its producing stage.
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

    assert stage.products

    missing = stage.products[0].path

    assert missing.is_file()

    missing.unlink()

    required = _required_stage_names(
        plan,
    )

    assert stage.name in required


# =========================================================
# Recovery scope
# =========================================================


@pytest.mark.slow
def test_missing_product_does_not_invalidate_unchanged_downstream_context(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Product loss alone does not change required downstream provenance.

    The producing stage must execute because its persistent product is
    absent, while downstream stages remain reusable when their own
    products and required fingerprints remain current.
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

    assert stage.products

    stage.products[0].path.unlink()

    required = _required_stage_names(
        plan,
    )

    assert stage.name in required

    descendants = {
        candidate.name
        for candidate in plan.stages
        if candidate.name
        in {
            "extrude",
            "package",
        }
    }

    assert descendants

    for descendant in descendants:
        assert descendant not in required


# =========================================================
# Product recovery
# =========================================================


@pytest.mark.slow
def test_missing_product_real_rebuild_repairs_and_reconverges(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Incremental execution recreates a missing product and restores reuse.
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

    assert stage.products

    missing = stage.products[0].path

    assert missing.is_file()

    missing.unlink()

    required_before = _required_stage_names(
        plan,
    )

    assert stage.name in required_before

    rebuilt = execute_incremental_artifact_build(
        plan,
    )

    rebuilt_names = tuple(execution.stage_name for execution in rebuilt.required_stages)

    assert rebuilt_names == required_before

    assert missing.is_file()

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
