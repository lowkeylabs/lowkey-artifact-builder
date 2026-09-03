"""
Tests for artifact cleaning lifecycle services.
"""
# File: tests/config/test_artifact_clean.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path

import pytest

from lowkey_artifact_builder.config import (
    ConfigError,
    clean_artifact,
)

# =========================================================
# Helpers
# =========================================================


def _define_artifact(
    project_root: Path,
    artifact_id: str,
) -> Path:
    """
    Create a minimal persistent artifact definition.
    """

    artifact_dir = project_root / "artifacts" / artifact_id

    artifact_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    (artifact_dir / "artifact.toml").write_text(
        'model = "artwork"\n',
        encoding="utf-8",
    )

    return artifact_dir


def _write_product(
    artifact_dir: Path,
    relative_path: str,
) -> Path:
    """
    Create one representative generated product.
    """

    path = artifact_dir / relative_path

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_bytes(b"generated")

    return path


# =========================================================
# Persistent artifact state
# =========================================================


def test_clean_preserves_artifact_configuration(
    tmp_path: Path,
) -> None:
    """
    Cleaning preserves the persistent artifact definition.
    """

    artifact_dir = _define_artifact(
        tmp_path,
        "skippy",
    )

    config_path = artifact_dir / "artifact.toml"

    original = config_path.read_bytes()

    clean_artifact(
        "skippy",
        project_root=tmp_path,
    )

    assert config_path.is_file()
    assert config_path.read_bytes() == original


def test_clean_preserves_artifact_owned_inputs(
    tmp_path: Path,
) -> None:
    """
    Cleaning preserves artifact-owned source inputs.
    """

    artifact_dir = _define_artifact(
        tmp_path,
        "skippy",
    )

    source = artifact_dir / "artifact.png"
    source.write_bytes(b"source artwork")

    clean_artifact(
        "skippy",
        project_root=tmp_path,
    )

    assert source.is_file()
    assert source.read_bytes() == b"source artwork"


# =========================================================
# Generated products
# =========================================================


def test_clean_removes_generated_artwork_silo(
    tmp_path: Path,
) -> None:
    """
    Cleaning removes generated Artwork products.
    """

    artifact_dir = _define_artifact(
        tmp_path,
        "skippy",
    )

    product = _write_product(
        artifact_dir,
        "artwork/default/50-package/artifact.3mf",
    )

    clean_artifact(
        "skippy",
        project_root=tmp_path,
    )

    assert not product.exists()
    assert not (artifact_dir / "artwork").exists()


def test_clean_removes_generated_shape_silo(
    tmp_path: Path,
) -> None:
    """
    Cleaning removes generated Shape products.
    """

    artifact_dir = _define_artifact(
        tmp_path,
        "skippy",
    )

    product = _write_product(
        artifact_dir,
        "shape/default/40-package/artifact.3mf",
    )

    clean_artifact(
        "skippy",
        project_root=tmp_path,
    )

    assert not product.exists()
    assert not (artifact_dir / "shape").exists()


def test_clean_removes_all_generated_model_silos(
    tmp_path: Path,
) -> None:
    """
    Cleaning removes generated products from every supported model silo.
    """

    artifact_dir = _define_artifact(
        tmp_path,
        "skippy",
    )

    artwork_product = _write_product(
        artifact_dir,
        "artwork/default/50-package/artifact.3mf",
    )

    shape_product = _write_product(
        artifact_dir,
        "shape/default/40-package/artifact.3mf",
    )

    clean_artifact(
        "skippy",
        project_root=tmp_path,
    )

    assert not artwork_product.exists()
    assert not shape_product.exists()
    assert not (artifact_dir / "artwork").exists()
    assert not (artifact_dir / "shape").exists()


# =========================================================
# Safe repeated cleaning
# =========================================================


def test_clean_succeeds_when_no_generated_products_exist(
    tmp_path: Path,
) -> None:
    """
    Cleaning an already-clean artifact is a successful no-op.
    """

    artifact_dir = _define_artifact(
        tmp_path,
        "skippy",
    )

    clean_artifact(
        "skippy",
        project_root=tmp_path,
    )

    assert (artifact_dir / "artifact.toml").is_file()


def test_clean_is_idempotent(
    tmp_path: Path,
) -> None:
    """
    Repeated cleaning leaves the same persistent artifact state.
    """

    artifact_dir = _define_artifact(
        tmp_path,
        "skippy",
    )

    _write_product(
        artifact_dir,
        "artwork/default/50-package/artifact.3mf",
    )

    clean_artifact(
        "skippy",
        project_root=tmp_path,
    )

    clean_artifact(
        "skippy",
        project_root=tmp_path,
    )

    assert (artifact_dir / "artifact.toml").is_file()

    assert not (artifact_dir / "artwork").exists()


# =========================================================
# Artifact isolation
# =========================================================


def test_clean_does_not_modify_other_artifacts(
    tmp_path: Path,
) -> None:
    """
    Cleaning one artifact does not remove products belonging to another.
    """

    skippy_dir = _define_artifact(
        tmp_path,
        "skippy",
    )

    scooby_dir = _define_artifact(
        tmp_path,
        "scooby",
    )

    skippy_product = _write_product(
        skippy_dir,
        "artwork/default/50-package/artifact.3mf",
    )

    scooby_product = _write_product(
        scooby_dir,
        "artwork/default/50-package/artifact.3mf",
    )

    clean_artifact(
        "skippy",
        project_root=tmp_path,
    )

    assert not skippy_product.exists()
    assert scooby_product.is_file()


# =========================================================
# Undefined artifacts
# =========================================================


def test_clean_rejects_undefined_artifact(
    tmp_path: Path,
) -> None:
    """
    Cleaning requires a persistent artifact definition.
    """

    with pytest.raises(
        ConfigError,
        match="not defined",
    ):
        clean_artifact(
            "skippy",
            project_root=tmp_path,
        )
