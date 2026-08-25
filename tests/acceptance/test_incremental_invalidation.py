"""
End-to-end acceptance tests for incremental artifact invalidation.

These tests verify that changing artifact-owned source artwork invalidates
the appropriate realized workflow after a successful incremental build,
that invalidation does not itself destroy persistent products, and that
real incremental execution restores a fully reusable realization.
"""
# File: tests/acceptance/test_incremental_invalidation.py
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

    The repository's known-good nydeli artwork is copied into the
    isolated project before interactive configuration.
    """

    repository_root = Path(__file__).resolve().parents[2]

    fixture_source = repository_root / "projects" / "nydeli-clean.png"

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


def _input_stage(
    plan: BuildPlan,
) -> PlannedStage:
    """
    Return the realized stage consuming artifact-owned source artwork.
    """

    for stage in plan.stages:
        if stage.inputs:
            return stage

    raise AssertionError("Acceptance build plan contains no stage with external inputs.")


def _change_artwork(
    plan: BuildPlan,
) -> PlannedStage:
    """
    Change artifact-owned source bytes without changing its pathname.

    Bytes are appended after the PNG payload so content provenance changes
    while the source remains readable by the real artwork pipeline.
    """

    stage = _input_stage(
        plan,
    )

    assert stage.inputs

    artwork_input = stage.inputs[0]

    original = artwork_input.path.read_bytes()

    artwork_input.path.write_bytes(
        original + b"\n",
    )

    return stage


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


def _descendant_stage_names(
    plan: BuildPlan,
    stage_name: str,
) -> tuple[str, ...]:
    """
    Return realized stages transitively depending on stage_name.
    """

    descendants: list[str] = []

    reached = {
        stage_name,
    }

    for stage in plan.stages:
        if any(dependency in reached for dependency in stage.spec.dependencies):
            reached.add(
                stage.name,
            )

            descendants.append(
                stage.name,
            )

    return tuple(
        descendants,
    )


# =========================================================
# Source invalidation
# =========================================================


@pytest.mark.slow
def test_changed_artwork_invalidates_real_incremental_build(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Changed artwork invalidates its consuming stage and descendants.
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

    input_stage = _change_artwork(
        plan,
    )

    required = _required_stage_names(
        plan,
    )

    assert input_stage.name in required

    descendants = _descendant_stage_names(
        plan,
        input_stage.name,
    )

    assert descendants

    for descendant in descendants:
        assert descendant in required


@pytest.mark.slow
def test_changed_artwork_preserves_existing_products_until_rebuild(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Provenance invalidation does not itself modify persistent products.
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

    products = tuple(product for stage in plan.stages for product in stage.products)

    assert products

    before = {product.path: product.path.read_bytes() for product in products}

    _change_artwork(
        plan,
    )

    assert _required_stage_names(
        plan,
    )

    for product in products:
        assert product.path.is_file()

        assert product.path.read_bytes() == before[product.path]


# =========================================================
# Source rebuilding
# =========================================================


@pytest.mark.slow
def test_changed_artwork_real_rebuild_executes_invalidated_chain(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Real incremental execution rebuilds exactly the required workflow.
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

    _change_artwork(
        plan,
    )

    required_before = _required_stage_names(
        plan,
    )

    assert required_before

    rebuilt = execute_incremental_artifact_build(
        plan,
    )

    rebuilt_names = tuple(stage.stage_name for stage in rebuilt.required_stages)

    assert rebuilt_names == required_before


@pytest.mark.slow
def test_changed_artwork_real_rebuild_reconverges(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Successful rebuilding after source invalidation restores full reuse.
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

    _change_artwork(
        plan,
    )

    assert _required_stage_names(
        plan,
    )

    rebuilt = execute_incremental_artifact_build(
        plan,
    )

    assert rebuilt.required_stages

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
