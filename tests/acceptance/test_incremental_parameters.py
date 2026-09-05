"""
End-to-end acceptance tests for parameter-driven incremental invalidation.

These tests verify that changing resolved artifact configuration invalidates
the stage whose declared parameters changed and the downstream stages whose
required provenance depends on that stage.

Persistent upstream work whose build context is unchanged remains reusable.
Successful incremental rebuilding restores a fully reusable realization.
"""
# File: tests/acceptance/test_incremental_parameters.py
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

    return tuple(stage.stage_name for stage in execution_plan.required_stages)


def _stages_declaring_parameter(
    plan: BuildPlan,
    parameter: str,
) -> tuple[PlannedStage, ...]:
    """
    Return realized stages declaring one fingerprinted parameter.
    """

    matches = tuple(stage for stage in plan.stages if parameter in stage.spec.parameters)

    assert matches, f"No realized stage declares {parameter!r}."

    return matches


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


def _change_artwork_size(
    project_root: Path,
) -> BuildPlan:
    """
    Change artwork_size through artifact configuration and return a new plan.

    The original acceptance configuration uses 70 mm. This helper changes
    that configured value directly in artifact.toml so the subsequent
    BuildPlan resolves a different build context.
    """

    artifact_toml = project_root / "artifacts" / "nydeli" / "artifact.toml"

    assert artifact_toml.is_file(), f"Artifact configuration does not exist: {artifact_toml}"

    original = artifact_toml.read_text(
        encoding="utf-8",
    )

    assert "70" in original

    changed = original.replace(
        "70",
        "75",
        1,
    )

    assert changed != original

    artifact_toml.write_text(
        changed,
        encoding="utf-8",
    )

    return _create_plan(
        project_root,
    )


# =========================================================
# Parameter invalidation
# =========================================================


@pytest.mark.slow
def test_changed_artwork_size_invalidates_declaring_stages_and_descendants(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Changed artwork size invalidates every declaring stage and its
    dependent descendants.
    """

    project_root = tmp_path

    _configure_artifact(
        project_root=project_root,
        monkeypatch=monkeypatch,
    )

    original_plan = _create_plan(
        project_root,
    )

    execute_incremental_artifact_build(
        original_plan,
    )

    assert (
        _required_stage_names(
            original_plan,
        )
        == ()
    )

    changed_plan = _change_artwork_size(
        project_root,
    )

    declaring_stages = _stages_declaring_parameter(
        changed_plan,
        "artwork_size",
    )

    required = set(
        _required_stage_names(
            changed_plan,
        )
    )

    expected: set[str] = set()

    for declaring_stage in declaring_stages:
        expected.add(
            declaring_stage.name,
        )

        expected.update(
            _descendant_stage_names(
                changed_plan,
                declaring_stage.name,
            )
        )

    assert expected

    for stage_name in expected:
        assert stage_name in required


@pytest.mark.slow
def test_changed_artwork_size_preserves_unaffected_upstream_stages(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Stages preceding every use of the changed parameter remain reusable.
    """

    project_root = tmp_path

    _configure_artifact(
        project_root=project_root,
        monkeypatch=monkeypatch,
    )

    original_plan = _create_plan(
        project_root,
    )

    execute_incremental_artifact_build(
        original_plan,
    )

    changed_plan = _change_artwork_size(
        project_root,
    )

    declaring_stages = _stages_declaring_parameter(
        changed_plan,
        "artwork_size",
    )

    declaring_names = {stage.name for stage in declaring_stages}

    earliest_index = next(
        index
        for index, stage in enumerate(
            changed_plan.stages,
        )
        if stage.name in declaring_names
    )

    upstream = changed_plan.stages[:earliest_index]

    assert upstream

    required = set(
        _required_stage_names(
            changed_plan,
        )
    )

    for stage in upstream:
        assert stage.name not in required


# =========================================================
# Parameter rebuilding
# =========================================================


@pytest.mark.slow
def test_changed_artwork_size_real_rebuild_reconverges(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Rebuilding after a parameter change restores full reuse.
    """

    project_root = tmp_path

    _configure_artifact(
        project_root=project_root,
        monkeypatch=monkeypatch,
    )

    original_plan = _create_plan(
        project_root,
    )

    execute_incremental_artifact_build(
        original_plan,
    )

    changed_plan = _change_artwork_size(
        project_root,
    )

    required_before = _required_stage_names(
        changed_plan,
    )

    assert required_before

    rebuilt = execute_incremental_artifact_build(
        changed_plan,
    )

    rebuilt_names = tuple(stage.stage_name for stage in rebuilt.required_stages)

    assert rebuilt_names == required_before

    assert (
        _required_stage_names(
            changed_plan,
        )
        == ()
    )

    second = execute_incremental_artifact_build(
        changed_plan,
    )

    assert second.required_stages == ()
