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
from lowkey_artifact_builder.config import materialize_artifact
from lowkey_artifact_builder.engine import (
    BuildPlan,
    PlannedStage,
    create_build_plans,
    execute_dependency_build,
    plan_dependency_build,
)
from lowkey_artifact_builder.model.specs import ProductRef

# =========================================================
# Helpers
# =========================================================


def _configure_artifact(
    *,
    project_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Create and materialize the acceptance Artifact.

    The repository's known-good nydeli artwork is copied into the
    isolated project, ingested through the public CREATE workflow, and
    then materialized into its baseline Artifact workspace before direct
    engine planning.
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

    create_result = runner.invoke(
        cli,
        [
            "create",
            "--artifact-id=nydeli",
            "--source=nydeli-clean.png",
        ],
    )

    assert create_result.exit_code == 0, (
        f"Artifact creation failed:\n{create_result.output}\n{create_result.exception!r}"
    )

    materialize_artifact(
        "nydeli",
        project_root=project_root,
    )


def _create_plan(
    project_root: Path,
) -> BuildPlan:
    """
    Return the BuildPlan targeting the canonical Artwork vector manifest.
    """

    target = ProductRef(
        artifact="nydeli",
        model="artwork",
        realization="artwork_default",
        stage="package",
        product="artifact",
    )

    plans = create_build_plans(
        "nydeli",
        realization="artwork_default",
        targets=(target,),
        project_root=project_root,
    )

    assert len(plans) == 1

    plan = plans[0]

    assert plan.artifact_id == "nydeli"
    assert plan.model_name == "artwork"
    assert plan.realization_name == "artwork_default"

    return plan


def _required_stage_names(
    plan: BuildPlan,
) -> tuple[str, ...]:
    """
    Return stages requiring dependency-aware incremental execution.
    """

    execution_plan = plan_dependency_build(
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
    Override artwork_size through Artifact configuration and return a new plan.

    The default Artwork Realization receives artwork_size from the Artwork
    Model defaults. This helper adds an Artifact-specific override to the
    canonical default Realization so the subsequent BuildPlan resolves a
    different build context.
    """

    artifact_toml = project_root / "artifacts" / "nydeli" / "artifact.toml"

    assert artifact_toml.is_file(), f"Artifact configuration does not exist: {artifact_toml}"

    original = artifact_toml.read_text(
        encoding="utf-8",
    )

    assert "[realizations.artwork_default]" not in original

    artifact_toml.write_text(
        original.rstrip()
        + """

[realizations.artwork_default]
artwork_size = 75.0
""",
        encoding="utf-8",
    )

    changed_plan = _create_plan(
        project_root,
    )

    assert changed_plan.resolver("artwork_size") == 75.0
    assert changed_plan.resolver.source("artwork_size") == "realization 'artwork_default'"

    return changed_plan


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

    execute_dependency_build(
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
    Changing artwork_size invalidates downstream geometry without
    invalidating the upstream vector Product.

    Product-targeted BuildPlans do not necessarily contain their
    upstream producer Stages. Verify upstream reuse through a
    separately targeted vector BuildPlan.
    """

    project_root = tmp_path

    _configure_artifact(
        project_root=project_root,
        monkeypatch=monkeypatch,
    )

    original_plan = _create_plan(
        project_root,
    )

    execute_dependency_build(
        original_plan,
    )

    vector_target = ProductRef(
        artifact="nydeli",
        model="artwork",
        realization="artwork_default",
        stage="vector",
        product="manifest",
    )

    vector_plans = create_build_plans(
        "nydeli",
        realization="artwork_default",
        targets=(vector_target,),
        project_root=project_root,
    )

    assert len(vector_plans) == 1

    vector_plan = vector_plans[0]

    assert vector_plan.stages
    assert _required_stage_names(vector_plan) == ()

    changed_plan = _change_artwork_size(
        project_root,
    )

    # The changed parameter belongs to downstream geometry.
    declaring_stages = _stages_declaring_parameter(
        changed_plan,
        "artwork_size",
    )

    assert declaring_stages

    downstream_required = set(
        _required_stage_names(
            changed_plan,
        )
    )

    for stage in declaring_stages:
        assert stage.name in downstream_required

    # Replan the upstream Product against the changed configuration.
    # Its fingerprint must remain valid because artwork_size is not
    # part of its declared build context.
    changed_vector_plans = create_build_plans(
        "nydeli",
        realization="artwork_default",
        targets=(vector_target,),
        project_root=project_root,
    )

    assert len(changed_vector_plans) == 1

    changed_vector_plan = changed_vector_plans[0]

    assert changed_vector_plan.stages

    assert _required_stage_names(changed_vector_plan) == ()

    # Dependency-aware execution must reuse the upstream Product.
    reused = execute_dependency_build(
        changed_vector_plan,
    )

    assert reused.required_stages == ()


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

    execute_dependency_build(
        original_plan,
    )

    changed_plan = _change_artwork_size(
        project_root,
    )

    required_before = _required_stage_names(
        changed_plan,
    )

    assert required_before

    rebuilt = execute_dependency_build(
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

    second = execute_dependency_build(
        changed_plan,
    )

    assert second.required_stages == ()
