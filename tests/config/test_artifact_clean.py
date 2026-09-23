"""
Tests for artifact cleaning lifecycle services.
"""
# File: tests/config/test_artifact_clean.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

import pytest

import lowkey_artifact_builder.config.artifact as artifact_services
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


def test_clean_removes_generated_silos_for_discovered_models(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Cleaning derives generated model silo names from model discovery.
    """

    artifact_dir = _define_artifact(
        tmp_path,
        "skippy",
    )

    generated = _write_product(
        artifact_dir,
        "future-model/default/10-build/product.dat",
    )

    model = Mock()
    model.name = "future-model"

    registry = Mock()
    registry.all_models.return_value = [
        model,
    ]

    monkeypatch.setattr(
        artifact_services,
        "build_model_registry",
        lambda: registry,
    )

    clean_artifact(
        "skippy",
        project_root=tmp_path,
    )

    assert not generated.exists()
    assert not (artifact_dir / "future-model").exists()


def test_clean_preserves_non_generated_artifact_owned_files(
    tmp_path: Path,
) -> None:
    """
    Cleaning generated model silos does not remove artifact-owned files.
    """

    artifact_dir = _define_artifact(
        tmp_path,
        "skippy",
    )

    source = artifact_dir / "artifact.png"
    source.write_bytes(b"source")

    other_input = artifact_dir / "reference.svg"
    other_input.write_bytes(b"reference")

    clean_artifact(
        "skippy",
        project_root=tmp_path,
    )

    assert source.read_bytes() == b"source"
    assert other_input.read_bytes() == b"reference"


def test_clean_preserves_unknown_artifact_directories(
    tmp_path: Path,
) -> None:
    """
    Cleaning does not treat arbitrary artifact directories as model silos.
    """

    artifact_dir = _define_artifact(
        tmp_path,
        "skippy",
    )

    persistent = _write_product(
        artifact_dir,
        "reference-data/reference.svg",
    )

    clean_artifact(
        "skippy",
        project_root=tmp_path,
    )

    assert persistent.is_file()


def test_clean_realization_removes_only_selected_realization_products(
    tmp_path: Path,
) -> None:
    """
    Realization-scoped cleaning removes generated Products belonging to
    the selected Realization while preserving unrelated Realizations.
    """

    artifact_dir = _define_artifact(
        tmp_path,
        "skippy",
    )

    default_product = _write_product(
        artifact_dir,
        "shape/shape_default/40-package/artifact.3mf",
    )

    ornament_product = _write_product(
        artifact_dir,
        "shape/shape_ornament/40-package/artifact.3mf",
    )

    clean_artifact(
        "skippy",
        realization="shape_ornament",
        project_root=tmp_path,
    )

    assert default_product.is_file()
    assert not ornament_product.exists()


def test_clean_named_realization_uses_realization_identity(
    tmp_path: Path,
) -> None:
    """
    Realization-scoped cleaning uses the Realization's own identity.

    An additional named Realization may originate from a Variant whose name
    differs from the Realization name. Cleaning that Realization removes its
    generated Products without removing Products belonging to the canonical
    Realization of the same Variant.
    """

    artifact_dir = _define_artifact(
        tmp_path,
        "skippy",
    )

    config_path = artifact_dir / "artifact.toml"
    config_path.write_text(
        "\n".join(
            (
                'model = "artwork"',
                "",
                "[realizations.large-ornament]",
                'variant = "shape.ornament"',
                "",
            )
        ),
        encoding="utf-8",
    )

    canonical_product = _write_product(
        artifact_dir,
        "shape/shape_ornament/40-package/artifact.3mf",
    )

    named_product = _write_product(
        artifact_dir,
        "shape/large-ornament/40-package/artifact.3mf",
    )

    clean_artifact(
        "skippy",
        realization="large-ornament",
        project_root=tmp_path,
    )

    assert canonical_product.is_file()
    assert not named_product.exists()


def test_clean_realization_removes_only_selected_published_3mf(
    tmp_path: Path,
) -> None:
    """
    Realization-scoped cleaning removes the selected Realization's published
    convenience 3MF while preserving published 3MFs belonging to unrelated
    Realizations.
    """

    artifact_dir = _define_artifact(
        tmp_path,
        "skippy",
    )

    selected = artifact_dir / "shape_ornament.3mf"
    selected.write_bytes(b"ornament")

    unrelated = artifact_dir / "shape_default.3mf"
    unrelated.write_bytes(b"default")

    clean_artifact(
        "skippy",
        realization="shape_ornament",
        project_root=tmp_path,
    )

    assert not selected.exists()
    assert unrelated.read_bytes() == b"default"
