"""
End-to-end acceptance tests for the public production workflow.

These tests protect the Phase 1 operator value chain through public CLI
surfaces:

    incoming artwork
        -> create
        -> build
        -> accessible manufacturing 3MF

They also verify that a current manufacturing result is reused and that
cleaning selected generated work leaves the Artifact ready to rebuild.

The tests intentionally do not call Artifact materialization, planning, or
execution services directly. The public CLI must compose those operations
into a usable production workflow.
"""

# File: tests/acceptance/test_production_workflow.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import shutil
import zipfile
from pathlib import Path

import pytest
from click.testing import CliRunner

from lowkey_artifact_builder.cli._main import cli

# =========================================================
# Helpers
# =========================================================


def _install_source(
    project_root: Path,
) -> Path:
    """
    Copy the repository's known-good acceptance artwork into the project.
    """

    repository_root = Path(__file__).resolve().parents[2]

    fixture_source = repository_root / "tests" / "assets" / "nydeli-clean.png"

    assert fixture_source.is_file(), f"Acceptance artwork does not exist: {fixture_source}"

    source = project_root / "nydeli-clean.png"

    shutil.copy2(
        fixture_source,
        source,
    )

    return source


def _create_artifact(
    runner: CliRunner,
) -> None:
    """
    Create the acceptance Artifact through the public CLI.
    """

    result = runner.invoke(
        cli,
        [
            "create",
            "--artifact-id=nydeli",
            "--source=nydeli-clean.png",
        ],
    )

    assert result.exit_code == 0, (
        f"Artifact creation failed:\n{result.output}\n{result.exception!r}"
    )


def _build_artifact(
    runner: CliRunner,
):
    """
    Build the acceptance Realization through the public CLI.
    """

    return runner.invoke(
        cli,
        [
            "build",
            "nydeli",
            "--realization",
            "artwork_default",
        ],
    )


def _published_3mf(
    project_root: Path,
) -> Path:
    """
    Return the operator-accessible manufacturing result.
    """

    return project_root / "artifacts" / "nydeli" / "artwork_default.3mf"


def _assert_valid_3mf(
    path: Path,
) -> None:
    """
    Assert that a path contains a nonempty structurally valid 3MF archive.
    """

    assert path.is_file(), f"Expected published manufacturing 3MF does not exist: {path}"

    assert path.stat().st_size > 0

    assert zipfile.is_zipfile(
        path,
    )

    with zipfile.ZipFile(
        path,
    ) as archive:
        names = set(
            archive.namelist(),
        )

    assert "[Content_Types].xml" in names

    assert any(name.startswith("3D/") and name.endswith(".model") for name in names)


def _canonical_product_mtimes(
    project_root: Path,
) -> dict[Path, int]:
    """
    Return mtimes for persistent generated files in the selected Realization.

    The Artifact-level convenience publication is intentionally excluded.
    These paths represent canonical generated state whose preservation proves
    that a current public BUILD reused existing manufacturing work.
    """

    realization_dir = project_root / "artifacts" / "nydeli" / "artwork" / "artwork_default"

    assert realization_dir.is_dir()

    products = tuple(sorted(path for path in realization_dir.rglob("*") if path.is_file()))

    assert products

    return {path: path.stat().st_mtime_ns for path in products}


def _establish_built_artifact(
    *,
    project_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[CliRunner, Path]:
    """
    Establish a built Artifact entirely through the public production CLI.
    """

    _install_source(
        project_root,
    )

    monkeypatch.chdir(
        project_root,
    )

    runner = CliRunner()

    _create_artifact(
        runner,
    )

    result = _build_artifact(
        runner,
    )

    assert result.exit_code == 0, f"Artifact build failed:\n{result.output}\n{result.exception!r}"

    published = _published_3mf(
        project_root,
    )

    _assert_valid_3mf(
        published,
    )

    return runner, published


# =========================================================
# Create -> build -> manufacturing result
# =========================================================


@pytest.mark.slow
def test_create_then_build_produces_accessible_3mf(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Incoming artwork can travel through the public production workflow
    to an operator-accessible printable 3MF.
    """

    project_root = tmp_path

    _install_source(
        project_root,
    )

    monkeypatch.chdir(
        project_root,
    )

    runner = CliRunner()

    _create_artifact(
        runner,
    )

    result = _build_artifact(
        runner,
    )

    assert result.exit_code == 0, f"Artifact build failed:\n{result.output}\n{result.exception!r}"

    published = _published_3mf(
        project_root,
    )

    _assert_valid_3mf(
        published,
    )

    assert "nydeli" in result.output
    assert "artwork_default" in result.output
    assert "built" in result.output
    assert "artwork_default.3mf" in result.output


# =========================================================
# Current manufacturing result
# =========================================================


@pytest.mark.slow
def test_second_public_build_reuses_current_manufacturing_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Repeating an unchanged public BUILD reuses current canonical Products
    and reports the accessible manufacturing result as current.
    """

    project_root = tmp_path

    runner, published = _establish_built_artifact(
        project_root=project_root,
        monkeypatch=monkeypatch,
    )

    before = _canonical_product_mtimes(
        project_root,
    )

    result = _build_artifact(
        runner,
    )

    assert result.exit_code == 0, (
        f"Second Artifact build failed:\n{result.output}\n{result.exception!r}"
    )

    after = _canonical_product_mtimes(
        project_root,
    )

    assert after == before

    _assert_valid_3mf(
        published,
    )

    assert "nydeli" in result.output
    assert "artwork_default" in result.output
    assert "current" in result.output
    assert "artwork_default.3mf" in result.output

    assert "Stage started:" not in result.output
    assert "Stage completed:" not in result.output
    assert "Stage skipped:" not in result.output
    assert "Build started:" not in result.output
    assert "Build completed:" not in result.output


# =========================================================
# Clean -> build -> regenerated manufacturing result
# =========================================================


@pytest.mark.slow
def test_public_clean_then_build_regenerates_manufacturing_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Public CLEAN removes selected generated manufacturing state while
    preserving the Artifact, and public BUILD regenerates its 3MF.
    """

    project_root = tmp_path

    runner, published = _establish_built_artifact(
        project_root=project_root,
        monkeypatch=monkeypatch,
    )

    artifact_dir = project_root / "artifacts" / "nydeli"

    config_path = artifact_dir / "artifact.toml"
    source_path = artifact_dir / "artifact.png"

    config_before = config_path.read_bytes()
    source_before = source_path.read_bytes()

    clean_result = runner.invoke(
        cli,
        [
            "clean",
            "nydeli",
            "--realization",
            "artwork_default",
        ],
    )

    assert clean_result.exit_code == 0, (
        f"Artifact clean failed:\n{clean_result.output}\n{clean_result.exception!r}"
    )

    assert not published.exists()

    assert config_path.is_file()
    assert config_path.read_bytes() == config_before

    assert source_path.is_file()
    assert source_path.read_bytes() == source_before

    result = _build_artifact(
        runner,
    )

    assert result.exit_code == 0, f"Artifact rebuild failed:\n{result.output}\n{result.exception!r}"

    _assert_valid_3mf(
        published,
    )

    assert "nydeli" in result.output
    assert "artwork_default" in result.output
    assert "built" in result.output
    assert "artwork_default.3mf" in result.output
