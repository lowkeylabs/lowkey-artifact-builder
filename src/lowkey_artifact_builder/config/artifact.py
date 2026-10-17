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
    get_resolver,
    load_artifact_config,
    update_artifact_config,
    write_artifact_config,
)

# =========================================================
# Constants
# =========================================================


_ARTWORK_INPUT = "artwork"
_ARTWORK_FILENAME = "artifact"
_ORIGINALS_DIRECTORY = "originals"
_ORIGINAL_SUFFIXES = frozenset({".png", ".svg"})


# =========================================================
# Artifact state
# =========================================================


@dataclass(frozen=True)
class ArtifactState:
    """
    Discovered project state for one Artifact.

    Artifact identity may be established by a preserved registration or by
    its stable Artifact workspace directory.

    Materialization describes only persistent Artifact configuration. An
    Artifact is materialized when its Artifact directory contains
    artifact.toml. Artifact-owned Artwork is optional.

    Generated Model, Realization, Stage, and Product state does not
    participate in Artifact materialization. That state is owned by the
    planning and execution engine.
    """

    artifact_id: str
    original_path: Path | None
    materialized: bool


# =========================================================
# Public interface
# =========================================================


def discover_artifacts(
    *,
    project_root: Path | None = None,
) -> tuple[ArtifactState, ...]:
    """
    Return the Artifacts known to the project.

    Artifact identity is the union of preserved registrations under
    ``originals/`` and stable Artifact workspace directories under
    ``artifacts/``.

    Preserved PNGs and SVGs are source-backed registrations. ``.artifact``
    files are source-less registrations. An Artifact workspace directory
    independently establishes Artifact identity.

    Materialization requires artifact.toml. Artifact-owned Artwork and
    generated Product state do not participate in this predicate.
    """

    root = project_root if project_root is not None else Path.cwd()
    originals_root = root / _ORIGINALS_DIRECTORY
    artifacts_root = root / "artifacts"

    artifact_ids: set[str] = set()
    original_paths: dict[str, Path] = {}
    registrations: dict[str, Path] = {}

    if originals_root.is_dir():
        for registration in sorted(
            originals_root.iterdir(),
            key=lambda path: path.name.casefold(),
        ):
            if not registration.is_file():
                continue

            suffix = registration.suffix.lower()

            if suffix not in _ORIGINAL_SUFFIXES | {".artifact"}:
                continue

            artifact_id = registration.stem
            identity = artifact_id.casefold()

            previous = registrations.get(identity)

            if previous is not None:
                raise ConfigError(
                    f"Conflicting Artifact registrations "
                    f"{previous.name!r} and {registration.name!r}."
                )

            registrations[identity] = registration
            artifact_ids.add(artifact_id)

            if suffix in _ORIGINAL_SUFFIXES:
                original_paths[artifact_id] = registration

    if artifacts_root.is_dir():
        artifact_ids.update(
            artifact_dir.name for artifact_dir in artifacts_root.iterdir() if artifact_dir.is_dir()
        )

    return tuple(
        ArtifactState(
            artifact_id=artifact_id,
            original_path=original_paths.get(artifact_id),
            materialized=_artifact_is_materialized(
                artifact_id,
                project_root=root,
            ),
        )
        for artifact_id in sorted(artifact_ids)
    )


def list_artifacts(
    *,
    project_root: Path | None = None,
) -> tuple[str, ...]:
    """
    Return the IDs of Artifacts known to the project.

    Preserved registrations and stable Artifact workspace directories
    establish Artifact identity. Materialization is not required for an
    Artifact to be listed.
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


def realization_svg_filename(
    realization_name: str,
) -> str:
    """Return the Artifact-level convenience SVG filename for a Realization."""
    return f"{realization_name}.svg"


def clean_artifact(
    artifact_id: str,
    *,
    realization: str | None = None,
    project_root: Path | None = None,
) -> None:
    """
    Remove derived products for an Artifact or one Realization.

    Persistent Artifact configuration and Artifact-owned source inputs
    are preserved.

    When a Realization is selected, only generated Products belonging to
    that Realization are removed. Generated Products belonging to unrelated
    Realizations are preserved.

    Without a Realization selection, complete generated Model silos are
    removed for every Model discovered by the Model subsystem. Artifact-level
    convenience 3MF copies belonging to effective Realizations are also
    removed.

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

    # -----------------------------------------------------
    # Realization-scoped cleaning
    # -----------------------------------------------------

    if realization is not None:
        if realization not in realization_names:
            raise ConfigError(
                f"Realization {realization!r} is not defined for Artifact {artifact_id!r}."
            )

        resolver = get_resolver(
            artifact_id,
            realization=realization,
            project_root=root,
        )

        model_name = resolver("model")

        if not isinstance(model_name, str) or not model_name:
            raise ConfigError(
                f"Realization {realization!r} for Artifact "
                f"{artifact_id!r} does not resolve to a Model."
            )

        generated_paths = [
            artifact_dir / model_name / realization,
            artifact_dir / realization_3mf_filename(realization),
            artifact_dir / realization_svg_filename(realization),
        ]

    # -----------------------------------------------------
    # Artifact-scoped cleaning
    # -----------------------------------------------------

    else:
        registry = build_model_registry()

        generated_paths = [artifact_dir / model.name for model in registry.all_models()]

        generated_paths.extend(
            artifact_dir / realization_3mf_filename(realization_name)
            for realization_name in realization_names
        )

        generated_paths.extend(
            artifact_dir / realization_svg_filename(realization_name)
            for realization_name in realization_names
        )

    # -----------------------------------------------------
    # Remove generated state
    # -----------------------------------------------------

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


def clean_realization_across_artifacts(
    artifact_ids: tuple[str, ...],
    realization: str,
    *,
    project_root: Path | None = None,
) -> None:
    """
    Clean the same existing Realization across Artifacts.

    The complete Artifact scope is validated before any generated Products
    are removed. If any Artifact does not provide the requested Realization,
    the operation fails without cleaning any Artifact.
    """

    root = project_root if project_root is not None else Path.cwd()

    # -----------------------------------------------------
    # Preflight the complete scope
    # -----------------------------------------------------

    for artifact_id in artifact_ids:
        config_path = artifact_config_path(
            artifact_id,
            project_root=root,
        )

        if not config_path.is_file():
            raise ConfigError(f"Artifact {artifact_id!r} is not defined.")

        realization_names = get_realization_names(
            artifact_id,
            project_root=root,
        )

        if realization not in realization_names:
            raise ConfigError(
                f"Realization {realization!r} is not defined for Artifact {artifact_id!r}."
            )

    # -----------------------------------------------------
    # Clean only after successful preflight
    # -----------------------------------------------------

    for artifact_id in artifact_ids:
        clean_artifact(
            artifact_id,
            realization=realization,
            project_root=root,
        )


# =========================================================
# Artifact discovery
# =========================================================


def _artifact_is_materialized(
    artifact_id: str,
    *,
    project_root: Path,
) -> bool:
    """
    Return whether persistent Artifact workspace state is materialized.

    Materialization requires artifact.toml. Artifact-owned Artwork is
    optional, and generated Product existence and freshness are
    planning-engine concerns.
    """

    config_path = artifact_config_path(
        artifact_id,
        project_root=project_root,
    )

    return config_path.is_file()


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
    Ingest PNG or SVG Artwork and persist its Artifact-owned source location.

    Artwork is an Artifact input. It does not select a Model, Variant,
    or Realization.

    The source format is preserved without conversion. Persistent Artifact
    paths are stored relative to the project root.
    """

    suffix = source.suffix.lower()

    if suffix not in _ORIGINAL_SUFFIXES:
        raise ConfigError(
            f"Unsupported Artwork source format {source.suffix!r}; expected PNG or SVG."
        )

    destination = _artifact_input_path(
        artifact_id,
        f"{_ARTWORK_FILENAME}{suffix}",
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

    A preserved PNG or SVG original establishes a source-backed Artifact.
    Its native format is retained during materialization.

    Materialization creates:

        artifacts/<artifact_id>/artifact.toml
        artifacts/<artifact_id>/artifact.png or artifact.svg

    An already-materialized Artifact is left unchanged. Incomplete
    workspace state is rejected rather than silently repaired.

    Generated Model, Realization, Stage, and Product state remains
    the responsibility of the planning and execution engine.
    """

    root = project_root if project_root is not None else Path.cwd()
    originals_root = root / _ORIGINALS_DIRECTORY

    config_path = artifact_config_path(
        artifact_id,
        project_root=root,
    )

    artifact_dir = config_path.parent

    originals = (
        [
            path
            for path in originals_root.iterdir()
            if path.is_file()
            and path.stem.casefold() == artifact_id.casefold()
            and path.suffix.lower() in _ORIGINAL_SUFFIXES
        ]
        if originals_root.is_dir()
        else []
    )

    if len(originals) > 1:
        raise ConfigError(
            f"Artifact {artifact_id!r} has conflicting preserved originals: "
            + ", ".join(sorted(path.name for path in originals))
        )

    original_path = originals[0] if originals else None

    # Existing configuration may independently establish an Artifact
    # without a preserved Artwork original.
    if config_path.is_file() and original_path is None:
        return

    if original_path is None:
        raise ConfigError(f"Artifact {artifact_id!r} has no preserved original.")

    if _artifact_is_materialized(
        artifact_id,
        project_root=root,
    ):
        return

    if artifact_dir.exists():
        raise ConfigError(f"Artifact {artifact_id!r} has incomplete materialized state.")

    artwork_path = artifact_dir / (f"{_ARTWORK_FILENAME}{original_path.suffix.lower()}")

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
                shutil.rmtree(artifact_dir)
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
    "clean_realization_across_artifacts",
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
