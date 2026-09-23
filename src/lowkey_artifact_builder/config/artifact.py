"""
High-level artifact configuration and lifecycle services.

This module owns artifact-level operations that combine persistent
configuration, artifact-owned input ingestion, artifact discovery, and
derived-product lifecycle management.

Callers describe artifacts in terms of logical configuration and
lifecycle operations. They do not need to know the physical artifact
workspace layout or canonical names used for ingested inputs.
"""
# File: src/lowkey_artifact_builder/config/artifact.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import shutil
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from lowkey_artifact_builder.model import build_model_registry

from .config import (
    ConfigError,
    artifact_config_path,
    get_realization_names,
    load_artifact_config,
    update_artifact_config,
    write_artifact_config,
)

# =========================================================
# Constants
# =========================================================


_ARTWORK_INPUT = "artwork"
_ARTWORK_FILENAME = "artifact.png"
_ORIGINALS_DIRECTORY = "originals"
_ORIGINAL_SUFFIX = ".png"


# =========================================================
# Artifact state
# =========================================================


@dataclass(frozen=True)
class ArtifactState:
    """
    Discovered project state for one ingested Artifact.

    Artifact identity is established by its canonical preserved original.

    Materialization describes only the baseline Artifact workspace. An
    Artifact is materialized when its Artifact directory, artifact.toml,
    and artifact.png all exist.

    Generated Model, Realization, Stage, and Product state does not
    participate in Artifact materialization. That state is owned by the
    planning and execution engine.
    """

    artifact_id: str
    original_path: Path
    materialized: bool


# =========================================================
# Public interface
# =========================================================


def discover_artifacts(
    *,
    project_root: Path | None = None,
) -> tuple[ArtifactState, ...]:
    """
    Return the ingested Artifacts known to the project.

    Canonical preserved PNGs under ``originals/`` establish Artifact
    identity and therefore define the authoritative Artifact inventory.

    For each ingested Artifact, discovery also reports whether its
    baseline Artifact workspace has been materialized.

    Materialization requires all of:

        artifacts/<artifact_id>/
        artifacts/<artifact_id>/artifact.toml
        artifacts/<artifact_id>/artifact.png

    Generated Product state is intentionally not inspected here. Once an
    Artifact is materialized, Product freshness and required production
    are determined by the planning engine.
    """

    root = project_root if project_root is not None else Path.cwd()
    originals_root = root / _ORIGINALS_DIRECTORY

    if not originals_root.is_dir():
        return ()

    artifacts = [
        ArtifactState(
            artifact_id=original.stem,
            original_path=original,
            materialized=_artifact_is_materialized(
                original.stem,
                project_root=root,
            ),
        )
        for original in originals_root.iterdir()
        if original.is_file() and original.suffix.lower() == _ORIGINAL_SUFFIX
    ]

    return tuple(
        sorted(
            artifacts,
            key=lambda artifact: artifact.artifact_id,
        )
    )


def list_artifacts(
    *,
    project_root: Path | None = None,
) -> tuple[str, ...]:
    """
    Return the IDs of ingested Artifacts known to the project.

    Artifact identity is established by canonical preserved originals
    under ``originals/``. Materialization of the Artifact workspace is
    not required for an Artifact to be listed.
    """

    return tuple(
        artifact.artifact_id
        for artifact in discover_artifacts(
            project_root=project_root,
        )
    )


def configure_artifact(
    artifact_id: str,
    *,
    values: Mapping[str, Any] | None = None,
    input_files: Mapping[str, Path] | None = None,
    project_root: Path | None = None,
) -> None:
    """
    Create or update artifact configuration.

    Explicit configuration values are merged into the existing artifact
    definition.

    External input files are ingested into artifact-owned storage.
    Callers identify inputs by semantic role and do not need to know
    their physical artifact paths or canonical filenames.

    Currently supported input roles are:

        artwork

    Supplying artwork persists the artifact-owned artwork location as
    the ``source`` configuration value.

    Values omitted from this call remain unchanged and continue to
    resolve through the normal configuration stack.
    """

    root = project_root if project_root is not None else Path.cwd()

    updates = dict(values or {})

    for name, source in (input_files or {}).items():
        _configure_input(
            artifact_id,
            name,
            source,
            updates,
            project_root=root,
        )

    if not updates:
        return

    update_artifact_config(
        artifact_id,
        updates,
        project_root=root,
    )


def realization_3mf_filename(
    realization_name: str,
) -> str:
    """
    Return the Artifact-level convenience 3MF filename for a Realization.

    Realization identity is preserved verbatim. A period is introduced only
    to separate the Realization name from the 3MF extension.
    """

    return f"{realization_name}.3mf"


def clean_artifact(
    artifact_id: str,
    *,
    project_root: Path | None = None,
) -> None:
    """
    Remove derived products for an Artifact.

    Persistent Artifact configuration and Artifact-owned source inputs
    are preserved.

    Complete generated Model silos are removed for every Model discovered
    by the Model subsystem. Artifact-level convenience 3MF copies belonging
    to effective Realizations are also removed.

    Unknown Artifact-owned files and directories are preserved.
    """

    root = project_root if project_root is not None else Path.cwd()

    config_path = artifact_config_path(
        artifact_id,
        project_root=root,
    )

    if not config_path.is_file():
        raise ConfigError(f"Artifact {artifact_id!r} is not defined.")

    artifact_dir = config_path.parent

    realization_names = get_realization_names(
        artifact_id,
        project_root=root,
    )

    registry = build_model_registry()

    generated_paths = [artifact_dir / model.name for model in registry.all_models()]

    generated_paths.extend(
        artifact_dir / realization_3mf_filename(realization_name)
        for realization_name in realization_names
    )

    for generated_path in generated_paths:
        if not generated_path.exists():
            continue

        try:
            if generated_path.is_dir():
                shutil.rmtree(
                    generated_path,
                )
            else:
                generated_path.unlink()

        except OSError as exc:
            raise ConfigError(
                f"Cannot clean artifact {artifact_id!r}: {generated_path}: {exc}"
            ) from exc


# =========================================================
# Artifact discovery
# =========================================================


def _artifact_is_materialized(
    artifact_id: str,
    *,
    project_root: Path,
) -> bool:
    """
    Return whether baseline Artifact workspace state is materialized.

    Materialization is deliberately independent of generated Product
    state. Product existence and freshness are planning-engine concerns.
    """

    config_path = artifact_config_path(
        artifact_id,
        project_root=project_root,
    )

    artifact_dir = config_path.parent
    artwork_path = artifact_dir / _ARTWORK_FILENAME

    return artifact_dir.is_dir() and config_path.is_file() and artwork_path.is_file()


# =========================================================
# Input configuration
# =========================================================


def _configure_input(
    artifact_id: str,
    name: str,
    source: Path,
    updates: dict[str, Any],
    *,
    project_root: Path,
) -> None:
    """
    Configure one semantic artifact input.
    """

    if name == _ARTWORK_INPUT:
        _configure_artwork_input(
            artifact_id,
            source,
            updates,
            project_root=project_root,
        )
        return

    raise ConfigError(f"Unknown artifact input {name!r}.")


def _configure_artwork_input(
    artifact_id: str,
    source: Path,
    updates: dict[str, Any],
    *,
    project_root: Path,
) -> None:
    """
    Ingest artwork and persist its Artifact-owned source location.

    Artwork is an Artifact input. It does not select a Model, Variant,
    or Realization.

    Persistent Artifact paths are stored relative to the project root so
    Artifact definitions remain portable with the project.
    """

    destination = _artifact_input_path(
        artifact_id,
        _ARTWORK_FILENAME,
        project_root=project_root,
    )

    _ingest_file(
        source,
        destination,
        input_name=_ARTWORK_INPUT,
    )

    updates["source"] = str(destination.relative_to(project_root))


# =========================================================
# Artifact-owned input paths
# =========================================================


def _artifact_input_path(
    artifact_id: str,
    filename: str,
    *,
    project_root: Path,
) -> Path:
    """
    Return an artifact-owned input path.

    The artifact directory is derived from the public configuration path
    service so this module does not independently define the artifact
    workspace hierarchy.
    """

    config_path = artifact_config_path(
        artifact_id,
        project_root=project_root,
    )

    return config_path.parent / filename


# =========================================================
# Input ingestion
# =========================================================


def _ingest_file(
    source: Path,
    destination: Path,
    *,
    input_name: str,
) -> None:
    """
    Copy one external file into artifact-owned storage.
    """

    source = source.expanduser()

    if not source.is_absolute():
        source = Path.cwd() / source

    if not source.exists():
        raise ConfigError(f"Artifact input {input_name!r} does not exist: {source}")

    if not source.is_file():
        raise ConfigError(f"Artifact input {input_name!r} is not a regular file: {source}")

    try:
        destination.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        if source.resolve() == destination.resolve():
            return

        shutil.copy2(
            source,
            destination,
        )

    except OSError as exc:
        raise ConfigError(
            f"Cannot ingest artifact input {input_name!r} from {source} to {destination}: {exc}"
        ) from exc


def materialize_artifact(
    artifact_id: str,
    *,
    project_root: Path | None = None,
) -> None:
    """
    Materialize baseline workspace state for one Artifact.

    A canonical preserved original under ``originals/`` establishes an
    Artifact entering through the Artwork ingestion workflow and is the
    authoritative source for Artwork materialization.

    Persistent Artifact configuration may independently establish an
    Artifact whose inputs do not require Artifact-owned Artwork. Such an
    Artifact requires no Artwork materialization and is left unchanged.

    If an ingested Artifact workspace is absent, materialization creates:

        artifacts/<artifact_id>/artifact.toml
        artifacts/<artifact_id>/artifact.png

    An already-materialized Artifact is left unchanged.

    A partially existing ingested Artifact workspace is inconsistent
    baseline state and is rejected rather than silently repaired or
    replaced.

    Generated Model, Realization, Stage, and Product state is outside this
    operation and remains the responsibility of the planning and execution
    engine.
    """

    root = project_root if project_root is not None else Path.cwd()

    original_path = root / _ORIGINALS_DIRECTORY / f"{artifact_id}{_ORIGINAL_SUFFIX}"

    config_path = artifact_config_path(
        artifact_id,
        project_root=root,
    )

    artifact_dir = config_path.parent
    artwork_path = artifact_dir / _ARTWORK_FILENAME

    # Persistent configuration independently establishes an Artifact when
    # there is no preserved Artwork original. Nothing needs to be
    # materialized at the Artifact-owned Artwork boundary in that case.
    if config_path.is_file() and not original_path.is_file():
        return

    if not original_path.is_file():
        raise ConfigError(f"Artifact {artifact_id!r} has no preserved original.")

    if _artifact_is_materialized(
        artifact_id,
        project_root=root,
    ):
        return

    if artifact_dir.exists():
        raise ConfigError(f"Artifact {artifact_id!r} has incomplete materialized state.")

    source_value = str(artwork_path.relative_to(root))
    original_value = str(original_path.relative_to(root))

    try:
        artifact_dir.mkdir(
            parents=True,
        )

        shutil.copy2(
            original_path,
            artwork_path,
        )

        write_artifact_config(
            artifact_id,
            {
                "source": source_value,
                "original": original_value,
            },
            project_root=root,
        )

    except (OSError, ConfigError) as exc:
        try:
            if artifact_dir.exists():
                shutil.rmtree(
                    artifact_dir,
                )
        except OSError:
            pass

        if isinstance(exc, ConfigError):
            raise

        raise ConfigError(f"Cannot materialize artifact {artifact_id!r}: {exc}") from exc


def configure_realization(
    artifact_id: str,
    realization: str,
    *,
    parameters: Mapping[str, Any],
    project_root: Path | None = None,
) -> None:
    """
    Customize parameters for an existing effective Artifact
    Realization.

    Canonical Realizations may be customized without first being
    declared in artifact.toml.

    Updating one Realization preserves unrelated Artifact configuration,
    unrelated Realizations, and existing parameters of the selected
    Realization.

    This operation does not create additional named Realizations.
    """

    root = project_root if project_root is not None else Path.cwd()

    existing = load_artifact_config(
        artifact_id,
        project_root=root,
    )

    if not existing:
        raise ConfigError(f"Artifact {artifact_id!r} is not defined.")

    realizations = get_realization_names(
        artifact_id,
        project_root=root,
    )

    if realization not in realizations:
        raise ConfigError(
            f"Realization {realization!r} is not defined for Artifact {artifact_id!r}."
        )

    authored_realizations = existing.get(
        "realizations",
        {},
    )

    if not isinstance(
        authored_realizations,
        Mapping,
    ):
        raise ConfigError("The [realizations] section in artifact.toml must be a TOML table.")

    updated_realizations = {
        name: dict(value) if isinstance(value, Mapping) else value
        for name, value in authored_realizations.items()
    }

    authored_realization = authored_realizations.get(
        realization,
        {},
    )

    if not isinstance(
        authored_realization,
        Mapping,
    ):
        raise ConfigError(f"Realization {realization!r} must be a TOML table.")

    updated_realization = dict(
        authored_realization,
    )

    authored_parameters = authored_realization.get(
        "parameters",
        {},
    )

    if not isinstance(
        authored_parameters,
        Mapping,
    ):
        raise ConfigError(
            f"The [realizations.{realization}.parameters] section "
            "in artifact.toml must be a TOML table."
        )

    updated_parameters = dict(
        authored_parameters,
    )

    updated_parameters.update(
        parameters,
    )

    updated_realization["parameters"] = updated_parameters
    updated_realizations[realization] = updated_realization

    update_artifact_config(
        artifact_id,
        {
            "realizations": updated_realizations,
        },
        project_root=root,
    )


def create_realization(
    artifact_id: str,
    realization: str,
    *,
    variant: str,
    parameters: Mapping[str, Any],
    project_root: Path | None = None,
) -> None:
    """
    Define an additional named Artifact Realization.

    The new Realization originates from the supplied qualified Variant
    and may provide Artifact-specific parameter customization.

    Existing Artifact configuration and unrelated Realization
    declarations are preserved.

    Creation requires a registered qualified Variant and does not
    overwrite an already-authored Realization.
    """

    root = project_root if project_root is not None else Path.cwd()

    existing = load_artifact_config(
        artifact_id,
        project_root=root,
    )

    if not existing:
        raise ConfigError(f"Artifact {artifact_id!r} is not defined.")

    authored_realizations = existing.get(
        "realizations",
        {},
    )

    if not isinstance(
        authored_realizations,
        Mapping,
    ):
        raise ConfigError("The [realizations] section in artifact.toml must be a TOML table.")

    existing_realizations = get_realization_names(
        artifact_id,
        project_root=root,
    )

    if realization in existing_realizations:
        raise ConfigError(
            f"Realization {realization!r} is already defined for Artifact {artifact_id!r}."
        )

    registry = build_model_registry()

    variant_exists = any(
        variant == f"{model.name}.{candidate.name}"
        for model in registry.all_models()
        for candidate in model.variants
    )

    if not variant_exists:
        raise ConfigError(f"Unknown qualified Variant {variant!r}.")

    updated_realizations = {
        name: dict(value) if isinstance(value, Mapping) else value
        for name, value in authored_realizations.items()
    }

    updated_realizations[realization] = {
        "variant": variant,
        "parameters": dict(parameters),
    }

    update_artifact_config(
        artifact_id,
        {
            "realizations": updated_realizations,
        },
        project_root=root,
    )


def create_realization_across_artifacts(
    artifact_ids: tuple[str, ...],
    realization: str,
    *,
    variant: str,
    parameters: Mapping[str, Any],
    project_root: Path | None = None,
) -> None:
    """
    Define the same additional named Realization across Artifacts.

    The complete Artifact scope is validated before any persistent
    configuration is changed. If any Artifact cannot accept the new
    Realization, the operation fails without mutating any Artifact.
    """

    root = project_root if project_root is not None else Path.cwd()

    # -----------------------------------------------------
    # Preflight the complete scope
    # -----------------------------------------------------

    registry = build_model_registry()

    variant_exists = any(
        variant == f"{model.name}.{candidate.name}"
        for model in registry.all_models()
        for candidate in model.variants
    )

    if not variant_exists:
        raise ConfigError(f"Unknown qualified Variant {variant!r}.")

    for artifact_id in artifact_ids:
        existing = load_artifact_config(
            artifact_id,
            project_root=root,
        )

        if not existing:
            raise ConfigError(f"Artifact {artifact_id!r} is not defined.")

        existing_realizations = get_realization_names(
            artifact_id,
            project_root=root,
        )

        if realization in existing_realizations:
            raise ConfigError(
                f"Realization {realization!r} is already defined for Artifact {artifact_id!r}."
            )

    # -----------------------------------------------------
    # Mutate only after successful preflight
    # -----------------------------------------------------

    for artifact_id in artifact_ids:
        create_realization(
            artifact_id,
            realization,
            variant=variant,
            parameters=parameters,
            project_root=root,
        )


def configure_realization_across_artifacts(
    artifact_ids: tuple[str, ...],
    realization: str,
    *,
    parameters: Mapping[str, Any],
    project_root: Path | None = None,
) -> None:
    """
    Customize the same existing Realization across Artifacts.

    The complete Artifact scope is validated before any persistent
    configuration is changed. If any Artifact does not provide the
    requested Realization, the operation fails without mutating any
    Artifact.
    """

    root = project_root if project_root is not None else Path.cwd()

    # -----------------------------------------------------
    # Preflight the complete scope
    # -----------------------------------------------------

    for artifact_id in artifact_ids:
        existing = load_artifact_config(
            artifact_id,
            project_root=root,
        )

        if not existing:
            raise ConfigError(f"Artifact {artifact_id!r} is not defined.")

        existing_realizations = get_realization_names(
            artifact_id,
            project_root=root,
        )

        if realization not in existing_realizations:
            raise ConfigError(
                f"Realization {realization!r} is not defined for Artifact {artifact_id!r}."
            )

    # -----------------------------------------------------
    # Mutate only after successful preflight
    # -----------------------------------------------------

    for artifact_id in artifact_ids:
        configure_realization(
            artifact_id,
            realization,
            parameters=parameters,
            project_root=root,
        )


__all__ = [
    "ArtifactState",
    "clean_artifact",
    "configure_artifact",
    "configure_realization",
    "create_realization",
    "configure_realization_across_artifacts",
    "create_realization_across_artifacts",
    "discover_artifacts",
    "list_artifacts",
    "materialize_artifact",
    "realization_3mf_filename",
]
