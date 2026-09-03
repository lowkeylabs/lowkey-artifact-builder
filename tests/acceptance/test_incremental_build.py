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
from lowkey_artifact_builder.config import (
    clean_artifact,
)
from lowkey_artifact_builder.engine import (
    BuildPlan,
    create_build_plans,
    execute_incremental_artifact_build,
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
    Create the acceptance artifact through the public CLI.

    The repository's known-good nydeli artwork is copied into the
    isolated project before interactive creation.
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
            "nydeli",
        ],
        input=("1\n1\n70\n"),
    )

    assert create_result.exit_code == 0, (
        f"Artifact creation failed:\n{create_result.output}\n{create_result.exception!r}"
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


def _artifact_output(
    plan: BuildPlan,
) -> Path:
    """
    Return the realized final artifact product.
    """

    package_stage = next(stage for stage in plan.stages if stage.name == "package")

    artifact_product = next(
        product for product in package_stage.products if product.name == "artifact"
    )

    return artifact_product.path


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
# Reuse
# =========================================================


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


@pytest.mark.slow
def test_second_incremental_build_preserves_product_mtimes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Reusable persistent products are not rewritten by an unchanged build.
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

    before = {product.path: product.path.stat().st_mtime_ns for product in products}

    second = execute_incremental_artifact_build(
        plan,
    )

    assert second.required_stages == ()

    after = {product.path: product.path.stat().st_mtime_ns for product in products}

    assert after == before


# =========================================================
# Clean and rebuild
# =========================================================


@pytest.mark.slow
def test_cleaned_artifact_can_be_rebuilt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Cleaning removes derived products without preventing a subsequent
    build from reproducing the artifact.
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

    output = _artifact_output(
        plan,
    )

    assert output.is_file()

    artifact_dir = project_root / "artifacts" / "nydeli"

    config_path = artifact_dir / "artifact.toml"
    source_path = artifact_dir / "artifact.png"
    model_dir = artifact_dir / "artwork"

    assert config_path.is_file()
    assert source_path.is_file()
    assert model_dir.is_dir()

    clean_artifact(
        "nydeli",
        project_root=project_root,
    )

    assert config_path.is_file()
    assert source_path.is_file()
    assert not model_dir.exists()
    assert not output.exists()

    rebuilt_plan = _create_plan(
        project_root,
    )

    second = execute_incremental_artifact_build(
        rebuilt_plan,
    )

    assert second.required_stages

    rebuilt_output = _artifact_output(
        rebuilt_plan,
    )

    assert rebuilt_output.is_file()
    assert rebuilt_output.stat().st_size > 0
    assert zipfile.is_zipfile(
        rebuilt_output,
    )
