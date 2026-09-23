"""
Tests for high-level artifact configuration services.
"""
# File: tests/config/test_artifact.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path

import pytest

import lowkey_artifact_builder.config.artifact as artifact_config
from lowkey_artifact_builder.config import (
    ConfigError,
    artifact_config_path,
    clean_artifact,
    configure_artifact,
    configure_realization,
    configure_realization_across_artifacts,
    create_realization,
    create_realization_across_artifacts,
    discover_artifacts,
    get_resolver,
    list_artifacts,
    load_artifact_config,
    materialize_artifact,
    write_artifact_config,
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


def _configured_source_path(
    artifact_id: str,
    *,
    project_root: Path,
) -> Path:
    """
    Return the Artifact-owned source path from persistent configuration.

    Artifact input ownership is independent of Model, Variant, and
    Realization selection. Persisted Artifact paths are resolved relative
    to the project root.
    """

    config = load_artifact_config(
        artifact_id,
        project_root=project_root,
    )

    source = Path(config["source"])

    if source.is_absolute():
        return source

    return project_root / source


def _preserve_original(
    project_root: Path,
    artifact_id: str,
    *,
    content: bytes = b"artwork",
) -> Path:
    """
    Preserve one canonical ingested Artifact original.
    """

    originals = project_root / "originals"
    originals.mkdir(
        parents=True,
        exist_ok=True,
    )

    original = originals / f"{artifact_id}.png"
    original.write_bytes(content)

    return original


def _write_materialized_artifact(
    project_root: Path,
    artifact_id: str,
    *,
    artwork: bytes = b"artwork",
) -> None:
    """
    Write the complete baseline state of one materialized Artifact.
    """

    artifact_dir = project_root / "artifacts" / artifact_id
    artifact_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    (artifact_dir / "artifact.toml").write_text(
        "\n".join(
            (
                f'source = "artifacts/{artifact_id}/artifact.png"',
                f'original = "originals/{artifact_id}.png"',
                "",
            )
        ),
        encoding="utf-8",
    )

    (artifact_dir / "artifact.png").write_bytes(artwork)


# =========================================================
# Artifact discovery
# =========================================================


def test_artifact_discovery_uses_preserved_originals_as_inventory(
    tmp_path: Path,
) -> None:
    """
    Preserved originals establish the Artifact identities known to a project.

    Artifact discovery does not require the Artifact workspace to have been
    materialized.
    """

    _preserve_original(
        tmp_path,
        "dog",
        content=b"dog artwork",
    )

    assert list_artifacts(
        project_root=tmp_path,
    ) == ("dog",)


def test_artifact_discovery_ignores_workspace_without_preserved_original(
    tmp_path: Path,
) -> None:
    """
    Materialized workspace state does not independently establish an
    ingested Artifact identity.

    The authoritative Artifact inventory is originals/.
    """

    _write_materialized_artifact(
        tmp_path,
        "orphan",
        artwork=b"orphan artwork",
    )

    assert (
        list_artifacts(
            project_root=tmp_path,
        )
        == ()
    )


def test_discover_artifacts_reports_unmaterialized_artifact(
    tmp_path: Path,
) -> None:
    """
    An ingested Artifact without baseline workspace state is not materialized.
    """

    original = _preserve_original(
        tmp_path,
        "dog",
        content=b"dog artwork",
    )

    artifacts = discover_artifacts(
        project_root=tmp_path,
    )

    assert len(artifacts) == 1

    artifact = artifacts[0]

    assert artifact.artifact_id == "dog"
    assert artifact.original_path == original
    assert artifact.materialized is False


def test_discover_artifacts_reports_complete_baseline_as_materialized(
    tmp_path: Path,
) -> None:
    """
    An ingested Artifact is materialized when its Artifact directory,
    artifact.toml, and artifact.png all exist.
    """

    original = _preserve_original(
        tmp_path,
        "dog",
        content=b"dog artwork",
    )

    _write_materialized_artifact(
        tmp_path,
        "dog",
        artwork=b"dog artwork",
    )

    artifacts = discover_artifacts(
        project_root=tmp_path,
    )

    assert len(artifacts) == 1

    artifact = artifacts[0]

    assert artifact.artifact_id == "dog"
    assert artifact.original_path == original
    assert artifact.materialized is True


def test_discover_artifacts_requires_complete_materialization_baseline(
    tmp_path: Path,
) -> None:
    """
    Partial Artifact workspace state is not materialized.

    Materialization requires the Artifact directory, artifact.toml, and
    artifact.png. Generated Product state is outside this predicate.
    """

    _preserve_original(
        tmp_path,
        "missing_workspace",
    )

    _preserve_original(
        tmp_path,
        "missing_config",
    )

    missing_config_dir = tmp_path / "artifacts" / "missing_config"
    missing_config_dir.mkdir(
        parents=True,
    )
    (missing_config_dir / "artifact.png").write_bytes(
        b"artwork",
    )

    _preserve_original(
        tmp_path,
        "missing_artwork",
    )

    missing_artwork_dir = tmp_path / "artifacts" / "missing_artwork"
    missing_artwork_dir.mkdir(
        parents=True,
    )
    (missing_artwork_dir / "artifact.toml").write_text(
        'source = "artifacts/missing_artwork/artifact.png"\n',
        encoding="utf-8",
    )

    states = {
        artifact.artifact_id: artifact.materialized
        for artifact in discover_artifacts(
            project_root=tmp_path,
        )
    }

    assert states == {
        "missing_artwork": False,
        "missing_config": False,
        "missing_workspace": False,
    }


def test_artifact_materialization_does_not_depend_on_generated_products(
    tmp_path: Path,
) -> None:
    """
    Product realization is independent of Artifact materialization.

    A complete baseline Artifact is materialized even when no generated
    Model, Realization, Stage, or Product directories exist.
    """

    _preserve_original(
        tmp_path,
        "dog",
        content=b"dog artwork",
    )

    _write_materialized_artifact(
        tmp_path,
        "dog",
        artwork=b"dog artwork",
    )

    artifact_dir = tmp_path / "artifacts" / "dog"

    assert {path.name for path in artifact_dir.iterdir()} == {
        "artifact.png",
        "artifact.toml",
    }

    artifact = discover_artifacts(
        project_root=tmp_path,
    )[0]

    assert artifact.materialized is True


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
    External artwork becomes an Artifact-owned input.
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

    materialized = _configured_source_path(
        "skippy",
        project_root=tmp_path,
    )

    assert materialized.is_file()
    assert materialized.read_bytes() == content


def test_configure_artifact_does_not_depend_on_external_artwork(
    tmp_path: Path,
) -> None:
    """
    A configured Artifact remains self-contained after its original
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

    materialized = _configured_source_path(
        "skippy",
        project_root=tmp_path,
    )

    assert materialized.is_file()
    assert materialized.read_bytes() == content


def test_configure_artifact_artwork_does_not_select_model(
    tmp_path: Path,
) -> None:
    """
    Artifact artwork is an Artifact input, not Model selection.

    Model and Variant identity come from the selected Realization rather
    than from the presence of source artwork.
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

    assert "model" not in config


def test_configured_source_is_resolved_relative_to_project_root(
    tmp_path: Path,
) -> None:
    """
    Persisted Artifact source metadata identifies the managed input relative
    to the project root rather than relative to artifact.toml.
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

    config = load_artifact_config(
        "skippy",
        project_root=tmp_path,
    )

    configured_source = tmp_path / config["source"]

    assert configured_source == (tmp_path / "artifacts" / "skippy" / "artifact.png")

    assert configured_source.read_bytes() == content


def test_configure_artifact_persists_project_relative_source(
    tmp_path: Path,
) -> None:
    """
    Artifact-owned source metadata is persisted relative to the project root.

    Persistent Artifact configuration must remain portable when the complete
    project is moved to another filesystem location.
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

    assert config == {
        "source": "artifacts/skippy/artifact.png",
    }


def test_configure_artifact_replaces_materialized_artwork(
    tmp_path: Path,
) -> None:
    """
    Reconfiguring an Artifact replaces its Artifact-owned artwork.
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

    materialized = _configured_source_path(
        "skippy",
        project_root=tmp_path,
    )

    assert materialized.read_bytes() == b"second artwork"


def test_configure_artifact_accepts_configuration_values(
    tmp_path: Path,
) -> None:
    """
    Explicit Artifact values are persisted alongside materialized inputs.
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
    Reconfiguring one aspect of an Artifact preserves unrelated
    Artifact-specific configuration.
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
    assert "source" in config
    assert "model" not in config


def test_configure_artifact_persists_explicit_default_realization(
    tmp_path: Path,
) -> None:
    """
    Explicit default realization configuration remains realization-scoped.

    Historical explicitly authored Realization configuration remains
    persistent configuration rather than being flattened into Artifact-level
    Model configuration.
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
    Materializing Artifact-owned artwork preserves explicitly authored
    Realization configuration without creating Artifact-level Model state.
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

    assert "source" in config
    assert "model" not in config
    assert "artwork_size" not in config


def test_explicit_default_realization_is_selected_implicitly_and_explicitly(
    tmp_path: Path,
) -> None:
    """
    Historical explicitly authored default Realization configuration remains
    selectable implicitly and explicitly.
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


def test_materialize_artifact_creates_baseline_from_preserved_original(
    tmp_path: Path,
) -> None:
    """
    Materializing an ingested Artifact creates exactly the baseline state
    required before Product planning.
    """

    original = _preserve_original(
        tmp_path,
        "dog",
        content=b"dog artwork",
    )

    materialize_artifact(
        "dog",
        project_root=tmp_path,
    )

    artifact_dir = tmp_path / "artifacts" / "dog"
    artifact_png = artifact_dir / "artifact.png"
    config_path = artifact_dir / "artifact.toml"

    assert original.read_bytes() == b"dog artwork"
    assert artifact_png.read_bytes() == b"dog artwork"

    assert config_path.read_text() == (
        'source = "artifacts/dog/artifact.png"\noriginal = "originals/dog.png"\n'
    )

    assert {path.name for path in artifact_dir.iterdir()} == {
        "artifact.png",
        "artifact.toml",
    }

    state = discover_artifacts(
        project_root=tmp_path,
    )[0]

    assert state.artifact_id == "dog"
    assert state.materialized is True


def test_materialize_artifact_requires_preserved_original(
    tmp_path: Path,
) -> None:
    """
    BUILD materialization cannot invent an Artifact that has not been
    ingested into the preserved-original registry.
    """

    with pytest.raises(
        ConfigError,
        match="dog",
    ):
        materialize_artifact(
            "dog",
            project_root=tmp_path,
        )

    assert not (tmp_path / "artifacts" / "dog").exists()


@pytest.mark.parametrize(
    "existing",
    [
        "directory-only",
        "config-only",
        "artwork-only",
    ],
)
def test_materialize_artifact_rejects_partial_existing_workspace(
    tmp_path: Path,
    existing: str,
) -> None:
    """
    Materialization creates absent baseline state; it does not silently
    repair or replace a partially materialized Artifact workspace.
    """

    _preserve_original(
        tmp_path,
        "dog",
        content=b"dog artwork",
    )

    artifact_dir = tmp_path / "artifacts" / "dog"
    artifact_dir.mkdir(parents=True)

    if existing == "config-only":
        (artifact_dir / "artifact.toml").write_text(
            'source = "artifacts/dog/artifact.png"\noriginal = "originals/dog.png"\n'
        )

    if existing == "artwork-only":
        (artifact_dir / "artifact.png").write_bytes(
            b"existing artwork",
        )

    before = {
        path.name: (path.read_bytes() if path.is_file() else None)
        for path in artifact_dir.iterdir()
    }

    with pytest.raises(
        ConfigError,
        match="dog",
    ):
        materialize_artifact(
            "dog",
            project_root=tmp_path,
        )

    after = {
        path.name: (path.read_bytes() if path.is_file() else None)
        for path in artifact_dir.iterdir()
    }

    assert after == before


def test_materialize_artifact_does_not_replace_materialized_workspace(
    tmp_path: Path,
) -> None:
    """
    Materialization is not an implicit source-replacement operation.
    """

    _preserve_original(
        tmp_path,
        "dog",
        content=b"preserved original",
    )

    artifact_dir = tmp_path / "artifacts" / "dog"
    artifact_dir.mkdir(parents=True)

    config_path = artifact_dir / "artifact.toml"
    config_path.write_text(
        'source = "artifacts/dog/artifact.png"\n'
        'original = "originals/dog.png"\n'
        "\n"
        "[realizations.custom]\n"
        'variant = "shape.ornament"\n'
    )

    artifact_png = artifact_dir / "artifact.png"
    artifact_png.write_bytes(
        b"existing managed artwork",
    )

    materialize_artifact(
        "dog",
        project_root=tmp_path,
    )

    assert artifact_png.read_bytes() == b"existing managed artwork"
    assert config_path.read_text() == (
        'source = "artifacts/dog/artifact.png"\n'
        'original = "originals/dog.png"\n'
        "\n"
        "[realizations.custom]\n"
        'variant = "shape.ornament"\n'
    )


# =========================================================
# Artifact cleaning
# =========================================================


def test_clean_artifact_removes_published_3mf_convenience_copies(
    tmp_path: Path,
) -> None:
    """
    Cleaning an Artifact removes its derived convenience 3MF copies.

    Persistent Artifact configuration and managed source state survive.
    Convenience copies belonging to effective Realizations are derived build
    materializations and must not survive after their authoritative generated
    Products are cleaned.

    Unrelated Artifact-owned 3MF files are preserved.
    """

    _preserve_original(
        tmp_path,
        "dog",
    )

    materialize_artifact(
        "dog",
        project_root=tmp_path,
    )

    configure_artifact(
        "dog",
        values={
            "realizations": {
                "christmas_ornament": {
                    "variant": "shape.ornament",
                },
            },
        },
        project_root=tmp_path,
    )

    artifact_dir = tmp_path / "artifacts" / "dog"

    published = (
        artifact_dir / "artwork_default.3mf",
        artifact_dir / "shape_default.3mf",
        artifact_dir / "shape_ornament.3mf",
        artifact_dir / "christmas_ornament.3mf",
    )

    for path in published:
        path.write_bytes(b"published 3mf")

    unrelated = artifact_dir / "reference.3mf"
    unrelated.write_bytes(b"user-owned 3mf")

    clean_artifact(
        "dog",
        project_root=tmp_path,
    )

    assert (artifact_dir / "artifact.toml").is_file()
    assert (artifact_dir / "artifact.png").is_file()

    assert all(not path.exists() for path in published)

    assert unrelated.read_bytes() == b"user-owned 3mf"


def test_materialize_artifact_accepts_configured_artifact_without_preserved_original(
    tmp_path: Path,
) -> None:
    """
    An already-configured Artifact does not require a preserved Artwork original.

    Preserved originals establish Artifacts entering through the Artwork
    ingestion workflow. Persistent Artifact configuration may independently
    establish an Artifact whose inputs are supplied through Product
    dependencies rather than Artifact-owned Artwork.
    """

    write_artifact_config(
        "shape-example",
        {
            "product_dependencies": {
                "manifest": {
                    "model": "artwork",
                    "stage": "vector",
                    "product": "manifest",
                    "artifact": "artwork-example",
                    "realization": "artwork_default",
                },
            },
        },
        project_root=tmp_path,
    )

    config_path = artifact_config_path(
        "shape-example",
        project_root=tmp_path,
    )

    before = config_path.read_text(
        encoding="utf-8",
    )

    materialize_artifact(
        "shape-example",
        project_root=tmp_path,
    )

    assert (
        config_path.read_text(
            encoding="utf-8",
        )
        == before
    )

    assert not (tmp_path / "originals" / "shape-example.png").exists()

    assert not (tmp_path / "artifacts" / "shape-example" / "artifact.png").exists()


# =========================================================
# Realization configuration
# =========================================================


def test_configure_realization_materializes_canonical_customization(
    tmp_path: Path,
) -> None:
    """
    Customizing a canonical Realization materializes only its
    Artifact-specific parameter overrides.
    """

    configure_artifact(
        "skippy",
        values={
            "source": "artifacts/skippy/artifact.png",
        },
        project_root=tmp_path,
    )

    configure_realization(
        "skippy",
        "shape_ornament",
        parameters={
            "shape_size": 110,
        },
        project_root=tmp_path,
    )

    config = load_artifact_config(
        "skippy",
        project_root=tmp_path,
    )

    assert config == {
        "source": "artifacts/skippy/artifact.png",
        "realizations": {
            "shape_ornament": {
                "parameters": {
                    "shape_size": 110,
                },
            },
        },
    }


def test_configure_realization_preserves_unrelated_realizations(
    tmp_path: Path,
) -> None:
    """
    Updating one Realization preserves unrelated authored
    Realization declarations.
    """

    configure_artifact(
        "skippy",
        values={
            "source": "artifacts/skippy/artifact.png",
            "realizations": {
                "artwork_default": {
                    "parameters": {
                        "artwork_size": 75,
                    },
                },
                "shape_ornament": {
                    "parameters": {
                        "shape_base_height": 2,
                    },
                },
            },
        },
        project_root=tmp_path,
    )

    configure_realization(
        "skippy",
        "shape_ornament",
        parameters={
            "shape_size": 110,
        },
        project_root=tmp_path,
    )

    config = load_artifact_config(
        "skippy",
        project_root=tmp_path,
    )

    assert config["realizations"] == {
        "artwork_default": {
            "parameters": {
                "artwork_size": 75,
            },
        },
        "shape_ornament": {
            "parameters": {
                "shape_base_height": 2,
                "shape_size": 110,
            },
        },
    }


def test_configure_realization_rejects_unknown_realization(
    tmp_path: Path,
) -> None:
    """
    Customization cannot implicitly create a noncanonical
    Realization.
    """

    configure_artifact(
        "skippy",
        values={
            "source": "artifacts/skippy/artifact.png",
        },
        project_root=tmp_path,
    )

    with pytest.raises(
        ConfigError,
        match="shape_typo",
    ):
        configure_realization(
            "skippy",
            "shape_typo",
            parameters={
                "shape_size": 110,
            },
            project_root=tmp_path,
        )


# =========================================================
# Additional named Realizations
# =========================================================


def test_create_realization_defines_named_realization(
    tmp_path: Path,
) -> None:
    """
    An Artifact may define an additional named Realization from a
    registered qualified Variant.
    """

    configure_artifact(
        "skippy",
        values={
            "source": "artifacts/skippy/artifact.png",
        },
        project_root=tmp_path,
    )

    create_realization(
        "skippy",
        "large-ornament",
        variant="shape.ornament",
        parameters={
            "shape_size": 125,
        },
        project_root=tmp_path,
    )

    config = load_artifact_config(
        "skippy",
        project_root=tmp_path,
    )

    assert config["realizations"]["large-ornament"] == {
        "variant": "shape.ornament",
        "parameters": {
            "shape_size": 125,
        },
    }


def test_create_realization_preserves_unrelated_realizations(
    tmp_path: Path,
) -> None:
    """
    Defining an additional named Realization preserves existing
    Realization declarations.
    """

    configure_artifact(
        "skippy",
        values={
            "source": "artifacts/skippy/artifact.png",
            "realizations": {
                "artwork_default": {
                    "parameters": {
                        "artwork_size": 75,
                    },
                },
            },
        },
        project_root=tmp_path,
    )

    create_realization(
        "skippy",
        "large-ornament",
        variant="shape.ornament",
        parameters={
            "shape_size": 125,
        },
        project_root=tmp_path,
    )

    config = load_artifact_config(
        "skippy",
        project_root=tmp_path,
    )

    assert config["realizations"] == {
        "artwork_default": {
            "parameters": {
                "artwork_size": 75,
            },
        },
        "large-ornament": {
            "variant": "shape.ornament",
            "parameters": {
                "shape_size": 125,
            },
        },
    }


def test_create_realization_rejects_unknown_variant(
    tmp_path: Path,
) -> None:
    """
    An additional named Realization must originate from a registered
    qualified Variant.
    """

    configure_artifact(
        "skippy",
        values={
            "source": "artifacts/skippy/artifact.png",
        },
        project_root=tmp_path,
    )

    with pytest.raises(
        ConfigError,
        match="shape\\.typo",
    ):
        create_realization(
            "skippy",
            "large-ornament",
            variant="shape.typo",
            parameters={
                "shape_size": 125,
            },
            project_root=tmp_path,
        )

    config = load_artifact_config(
        "skippy",
        project_root=tmp_path,
    )

    assert "large-ornament" not in config.get(
        "realizations",
        {},
    )


def test_create_realization_rejects_existing_named_realization(
    tmp_path: Path,
) -> None:
    """
    Creation does not overwrite an already-authored named
    Realization.
    """

    configure_artifact(
        "skippy",
        values={
            "source": "artifacts/skippy/artifact.png",
            "realizations": {
                "large-ornament": {
                    "variant": "shape.ornament",
                    "parameters": {
                        "shape_size": 110,
                    },
                },
            },
        },
        project_root=tmp_path,
    )

    with pytest.raises(
        ConfigError,
        match="large-ornament",
    ):
        create_realization(
            "skippy",
            "large-ornament",
            variant="shape.ornament",
            parameters={
                "shape_size": 125,
            },
            project_root=tmp_path,
        )

    config = load_artifact_config(
        "skippy",
        project_root=tmp_path,
    )

    assert config["realizations"]["large-ornament"] == {
        "variant": "shape.ornament",
        "parameters": {
            "shape_size": 110,
        },
    }


def test_create_realization_rejects_canonical_realization(
    tmp_path: Path,
) -> None:
    """
    Canonical Realizations already exist and cannot be created
    as additional named Realizations.
    """

    configure_artifact(
        "skippy",
        values={
            "source": "artifacts/skippy/artifact.png",
        },
        project_root=tmp_path,
    )

    with pytest.raises(
        ConfigError,
        match="shape_ornament",
    ):
        create_realization(
            "skippy",
            "shape_ornament",
            variant="shape.ornament",
            parameters={
                "shape_size": 125,
            },
            project_root=tmp_path,
        )

    config = load_artifact_config(
        "skippy",
        project_root=tmp_path,
    )

    assert "shape_ornament" not in config.get(
        "realizations",
        {},
    )


def test_create_realization_across_artifacts_preflights_before_mutation(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    Bulk Realization creation validates the complete Artifact scope
    before mutating any Artifact.
    """

    configure_artifact(
        "skippy",
        values={
            "source": "artifacts/skippy/artifact.png",
        },
        project_root=tmp_path,
    )

    configure_artifact(
        "scooby",
        values={
            "source": "artifacts/scooby/artifact.png",
            "realizations": {
                "large-ornament": {
                    "variant": "shape.ornament",
                    "parameters": {
                        "shape_size": 110,
                    },
                },
            },
        },
        project_root=tmp_path,
    )

    with pytest.raises(
        ConfigError,
        match="large-ornament",
    ):
        create_realization_across_artifacts(
            (
                "skippy",
                "scooby",
            ),
            "large-ornament",
            variant="shape.ornament",
            parameters={
                "shape_size": 125,
            },
            project_root=tmp_path,
        )

    skippy = load_artifact_config(
        "skippy",
        project_root=tmp_path,
    )

    assert "large-ornament" not in skippy.get(
        "realizations",
        {},
    )


def test_configure_realization_across_artifacts_preflights_before_mutation(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    Bulk Realization customization validates the complete Artifact scope
    before mutating any Artifact.
    """

    configure_artifact(
        "skippy",
        values={
            "source": "artifacts/skippy/artifact.png",
        },
        project_root=tmp_path,
    )

    configure_artifact(
        "scooby",
        values={
            "source": "artifacts/scooby/artifact.png",
        },
        project_root=tmp_path,
    )

    def fake_get_realization_names(
        artifact_id: str,
        **kwargs,
    ) -> tuple[str, ...]:
        if artifact_id == "scooby":
            return (
                "artwork_default",
                "shape_default",
            )

        return (
            "artwork_default",
            "shape_default",
            "shape_ornament",
        )

    monkeypatch.setattr(
        artifact_config,
        "get_realization_names",
        fake_get_realization_names,
    )

    before = load_artifact_config(
        "skippy",
        project_root=tmp_path,
    )

    with pytest.raises(
        ConfigError,
        match="shape_ornament",
    ):
        configure_realization_across_artifacts(
            (
                "skippy",
                "scooby",
            ),
            "shape_ornament",
            parameters={
                "shape_size": 125,
            },
            project_root=tmp_path,
        )

    after = load_artifact_config(
        "skippy",
        project_root=tmp_path,
    )

    assert after == before
