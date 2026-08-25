"""
End-to-end acceptance tests for incremental artifact production.
"""
# File: tests/acceptance/test_incremental_build.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import shutil
import zipfile
from pathlib import Path

import pytest
from click.testing import CliRunner

from lowkey_artifact_builder.cli._main import cli
from lowkey_artifact_builder.engine import (
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
):
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


def _artifact_output(
    plan,
) -> Path:
    """
    Return the realized final artifact product.
    """

    package_stage = next(stage for stage in plan.stages if stage.name == "package")

    artifact_product = next(
        product for product in package_stage.products if product.name == "artifact"
    )

    return artifact_product.path


def _required_stage_names(
    plan,
) -> tuple[str, ...]:
    """
    Return stages currently requiring incremental execution.
    """

    execution_plan = plan_incremental_execution(
        plan,
    )

    return tuple(stage.stage_name for stage in execution_plan.required_stages)


# =========================================================
# Initial incremental build
# =========================================================


@pytest.mark.slow
def test_incremental_build_produces_complete_3mf(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Incremental execution can produce a complete real 3MF artifact.
    """

    project_root = tmp_path

    _configure_artifact(
        project_root=project_root,
        monkeypatch=monkeypatch,
    )

    plan = _create_plan(
        project_root,
    )

    execution_plan = execute_incremental_artifact_build(
        plan,
    )

    assert execution_plan.required_stages

    output = _artifact_output(
        plan,
    )

    assert output.is_relative_to(
        project_root,
    )

    assert output.is_file(), f"Incremental build did not produce the expected 3MF: {output}"

    assert output.stat().st_size > 0

    assert zipfile.is_zipfile(
        output,
    )

    with zipfile.ZipFile(
        output,
    ) as archive:
        names = set(
            archive.namelist(),
        )

    assert "[Content_Types].xml" in names

    assert any(name.startswith("3D/") and name.endswith(".model") for name in names)


# =========================================================
# Convergence
# =========================================================


@pytest.mark.slow
def test_incremental_build_converges_after_real_execution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    A successful real incremental build leaves no stage requiring work.
    """

    project_root = tmp_path

    _configure_artifact(
        project_root=project_root,
        monkeypatch=monkeypatch,
    )

    plan = _create_plan(
        project_root,
    )

    first = execute_incremental_artifact_build(
        plan,
    )

    assert first.required_stages

    assert (
        _required_stage_names(
            plan,
        )
        == ()
    )


@pytest.mark.slow
def test_second_incremental_build_requires_no_execution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    An unchanged second incremental build reuses the completed artifact.
    """

    project_root = tmp_path

    _configure_artifact(
        project_root=project_root,
        monkeypatch=monkeypatch,
    )

    plan = _create_plan(
        project_root,
    )

    first = execute_incremental_artifact_build(
        plan,
    )

    assert first.required_stages

    second = execute_incremental_artifact_build(
        plan,
    )

    assert second.required_stages == ()


# =========================================================
# Source invalidation
# =========================================================


@pytest.mark.slow
def test_changed_artwork_invalidates_incremental_build(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Changing artifact-owned artwork invalidates its dependent workflow.
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

    input_stage = next(stage for stage in plan.stages if stage.inputs)

    assert input_stage.inputs

    artwork_input = input_stage.inputs[0]

    original = artwork_input.path.read_bytes()

    artwork_input.path.write_bytes(
        original + b"\n",
    )

    required = _required_stage_names(
        plan,
    )

    assert input_stage.name in required


# =========================================================
# Rebuild convergence
# =========================================================


@pytest.mark.slow
def test_changed_artwork_rebuild_reconverges(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Rebuilding invalidated real artwork restores full reuse.
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

    input_stage = next(stage for stage in plan.stages if stage.inputs)

    artwork_input = input_stage.inputs[0]

    original = artwork_input.path.read_bytes()

    artwork_input.path.write_bytes(
        original + b"\n",
    )

    invalidated = plan_incremental_execution(
        plan,
    )

    assert invalidated.required_stages

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
