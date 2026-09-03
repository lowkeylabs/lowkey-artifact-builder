"""
Tests for high-level artifact configuration services.
"""
# File: tests/config/test_artifact.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path

from lowkey_artifact_builder.config import (
    artifact_config_path,
    configure_artifact,
    get_resolver,
    load_artifact_config,
)

# =========================================================
# Helpers
# =========================================================


def _write_artwork(
    path: Path,
    content: bytes = b"test artwork",
) -> None:
    """
    Write a stand-in artwork input.

    Artifact configuration materializes the input but does not interpret
    its image contents, so valid PNG encoding is unnecessary here.
    """

    path.write_bytes(content)


def _resolved_source_path(
    artifact_id: str,
    *,
    project_root: Path,
) -> Path:
    """
    Return the resolved artifact-owned source path.

    The test deliberately derives the artifact directory through the
    public configuration API rather than assuming the artifact tree
    layout.
    """

    resolver = get_resolver(
        artifact_id,
        project_root=project_root,
    )

    source = Path(resolver("source"))

    if source.is_absolute():
        return source

    config_path = artifact_config_path(
        artifact_id,
        project_root=project_root,
    )

    return config_path.parent / source


# =========================================================
# Artifact configuration
# =========================================================


def test_configure_artifact_creates_configuration(
    tmp_path: Path,
) -> None:
    """
    Configuring an artifact creates persistent artifact configuration.
    """

    source = tmp_path / "skippy.png"

    _write_artwork(source)

    configure_artifact(
        "skippy",
        input_files={
            "artwork": source,
        },
        project_root=tmp_path,
    )

    config_path = artifact_config_path(
        "skippy",
        project_root=tmp_path,
    )

    assert config_path.is_file()


def test_configure_artifact_materializes_input_artwork(
    tmp_path: Path,
) -> None:
    """
    External artwork becomes an artifact-owned input.
    """

    source = tmp_path / "skippy.png"
    content = b"skippy artwork"

    _write_artwork(
        source,
        content,
    )

    configure_artifact(
        "skippy",
        input_files={
            "artwork": source,
        },
        project_root=tmp_path,
    )

    materialized = _resolved_source_path(
        "skippy",
        project_root=tmp_path,
    )

    assert materialized.is_file()
    assert materialized.read_bytes() == content


def test_configure_artifact_does_not_depend_on_external_artwork(
    tmp_path: Path,
) -> None:
    """
    A configured artifact remains self-contained after its original
    external artwork is removed.
    """

    source = tmp_path / "skippy.png"
    content = b"skippy artwork"

    _write_artwork(
        source,
        content,
    )

    configure_artifact(
        "skippy",
        input_files={
            "artwork": source,
        },
        project_root=tmp_path,
    )

    source.unlink()

    materialized = _resolved_source_path(
        "skippy",
        project_root=tmp_path,
    )

    assert materialized.is_file()
    assert materialized.read_bytes() == content


def test_configure_artifact_uses_artwork_model(
    tmp_path: Path,
) -> None:
    """
    Artwork input selects the artwork model for minimal configuration.
    """

    source = tmp_path / "skippy.png"

    _write_artwork(source)

    configure_artifact(
        "skippy",
        input_files={
            "artwork": source,
        },
        project_root=tmp_path,
    )

    resolver = get_resolver(
        "skippy",
        project_root=tmp_path,
    )

    assert resolver("model") == "artwork"


def test_configure_artifact_supports_default_realization(
    tmp_path: Path,
) -> None:
    """
    Minimal artifact configuration resolves through the implicit
    default realization.
    """

    source = tmp_path / "skippy.png"

    _write_artwork(source)

    configure_artifact(
        "skippy",
        input_files={
            "artwork": source,
        },
        project_root=tmp_path,
    )

    resolver = get_resolver(
        "skippy",
        realization="default",
        project_root=tmp_path,
    )

    assert resolver("model") == "artwork"


def test_configure_artifact_persists_sparse_configuration(
    tmp_path: Path,
) -> None:
    """
    Configuration does not persist values supplied by implicit
    realization or variant defaults.
    """

    source = tmp_path / "skippy.png"

    _write_artwork(source)

    configure_artifact(
        "skippy",
        input_files={
            "artwork": source,
        },
        project_root=tmp_path,
    )

    config = load_artifact_config(
        "skippy",
        project_root=tmp_path,
    )

    assert config["model"] == "artwork"
    assert "source" in config

    assert "variant" not in config
    assert "realization" not in config


def test_configure_artifact_replaces_materialized_artwork(
    tmp_path: Path,
) -> None:
    """
    Reconfiguring an artifact replaces its artifact-owned artwork.
    """

    first = tmp_path / "first.png"
    second = tmp_path / "second.png"

    _write_artwork(
        first,
        b"first artwork",
    )

    _write_artwork(
        second,
        b"second artwork",
    )

    configure_artifact(
        "skippy",
        input_files={
            "artwork": first,
        },
        project_root=tmp_path,
    )

    configure_artifact(
        "skippy",
        input_files={
            "artwork": second,
        },
        project_root=tmp_path,
    )

    materialized = _resolved_source_path(
        "skippy",
        project_root=tmp_path,
    )

    assert materialized.read_bytes() == b"second artwork"


def test_configure_artifact_accepts_configuration_values(
    tmp_path: Path,
) -> None:
    """
    Explicit artifact values are persisted alongside materialized
    inputs.
    """

    source = tmp_path / "skippy.png"

    _write_artwork(source)

    configure_artifact(
        "skippy",
        values={
            "artwork_size": 75.0,
        },
        input_files={
            "artwork": source,
        },
        project_root=tmp_path,
    )

    config = load_artifact_config(
        "skippy",
        project_root=tmp_path,
    )

    assert config["artwork_size"] == 75.0


def test_configure_artifact_preserves_existing_values(
    tmp_path: Path,
) -> None:
    """
    Reconfiguring one aspect of an artifact preserves unrelated
    artifact-specific configuration.
    """

    source = tmp_path / "skippy.png"

    _write_artwork(source)

    configure_artifact(
        "skippy",
        values={
            "artwork_size": 75.0,
        },
        input_files={
            "artwork": source,
        },
        project_root=tmp_path,
    )

    configure_artifact(
        "skippy",
        values={
            "artwork_size": 90.0,
        },
        project_root=tmp_path,
    )

    config = load_artifact_config(
        "skippy",
        project_root=tmp_path,
    )

    assert config["artwork_size"] == 90.0
    assert config["model"] == "artwork"
    assert "source" in config


def test_configure_artifact_persists_explicit_default_realization(
    tmp_path: Path,
) -> None:
    """
    Explicit default realization configuration remains realization-scoped.

    Newly generated artifact configuration may represent default as an
    ordinary named realization rather than relying on the legacy
    implicit-default representation.
    """

    configure_artifact(
        "skippy",
        values={
            "realizations": {
                "default": {
                    "model": "artwork",
                    "parameters": {
                        "artwork_size": 75.0,
                    },
                },
            },
        },
        project_root=tmp_path,
    )

    config = load_artifact_config(
        "skippy",
        project_root=tmp_path,
    )

    assert config == {
        "realizations": {
            "default": {
                "model": "artwork",
                "parameters": {
                    "artwork_size": 75.0,
                },
            },
        },
    }


def test_configure_artifact_preserves_explicit_default_when_materializing_artwork(
    tmp_path: Path,
) -> None:
    """
    Materializing artifact-owned Artwork does not flatten an explicit
    default realization into legacy artifact-level model configuration.
    """

    source = tmp_path / "skippy.png"

    _write_artwork(source)

    configure_artifact(
        "skippy",
        values={
            "realizations": {
                "default": {
                    "model": "artwork",
                    "parameters": {
                        "artwork_size": 75.0,
                    },
                },
            },
        },
        input_files={
            "artwork": source,
        },
        project_root=tmp_path,
    )

    config = load_artifact_config(
        "skippy",
        project_root=tmp_path,
    )

    assert config["realizations"] == {
        "default": {
            "model": "artwork",
            "parameters": {
                "artwork_size": 75.0,
            },
        },
    }

    assert "model" not in config
    assert "artwork_size" not in config


def test_explicit_default_realization_is_selected_implicitly_and_explicitly(
    tmp_path: Path,
) -> None:
    """
    Explicit default is the ordinary realization selected when no
    realization is requested.
    """

    configure_artifact(
        "skippy",
        values={
            "realizations": {
                "default": {
                    "model": "artwork",
                    "parameters": {
                        "artwork_size": 75.0,
                    },
                },
            },
        },
        project_root=tmp_path,
    )

    implicit = get_resolver(
        "skippy",
        project_root=tmp_path,
    )

    explicit = get_resolver(
        "skippy",
        realization="default",
        project_root=tmp_path,
    )

    assert implicit("realization") == "default"
    assert explicit("realization") == "default"

    assert implicit("model") == explicit("model") == "artwork"
    assert implicit("artwork_size") == explicit("artwork_size") == 75.0
