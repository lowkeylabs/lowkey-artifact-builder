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
from pathlib import Path
from typing import Any

from .config import (
    ConfigError,
    artifact_config_path,
    update_artifact_config,
)

# =========================================================
# Constants
# =========================================================


_ARTWORK_INPUT = "artwork"
_ARTWORK_MODEL = "artwork"
_ARTWORK_FILENAME = "artifact.png"

_GENERATED_MODEL_DIRECTORIES = (
    "artwork",
    "shape",
)


# =========================================================
# Public interface
# =========================================================


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

    Supplying artwork selects the ``artwork`` model and persists the
    artifact-owned artwork location as the ``source`` configuration
    value.

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


def list_artifacts(
    *,
    project_root: Path | None = None,
) -> tuple[str, ...]:
    """
    Return the IDs of persistent artifacts defined in the project.

    An artifact is discoverable when its artifact directory contains its
    persistent ``artifact.toml`` definition.

    Derived product directories without persistent artifact
    configuration are not treated as artifact definitions.
    """

    root = project_root if project_root is not None else Path.cwd()
    artifacts_root = root / "artifacts"

    if not artifacts_root.is_dir():
        return ()

    artifact_ids = [
        path.name
        for path in artifacts_root.iterdir()
        if path.is_dir()
        and artifact_config_path(
            path.name,
            project_root=root,
        ).is_file()
    ]

    return tuple(sorted(artifact_ids))


def clean_artifact(
    artifact_id: str,
    *,
    project_root: Path | None = None,
) -> None:
    """
    Remove derived products for an artifact.

    Persistent artifact configuration and artifact-owned source inputs
    are preserved.

    The initial cleaning contract removes complete generated model
    directories beneath the artifact silo. More specific product-level
    cleaning may be introduced later without changing the public
    lifecycle operation.
    """

    root = project_root if project_root is not None else Path.cwd()

    config_path = artifact_config_path(
        artifact_id,
        project_root=root,
    )

    if not config_path.is_file():
        raise ConfigError(f"Artifact {artifact_id!r} is not defined.")

    artifact_dir = config_path.parent

    for directory_name in _GENERATED_MODEL_DIRECTORIES:
        generated_dir = artifact_dir / directory_name

        if not generated_dir.exists():
            continue

        try:
            if generated_dir.is_dir():
                shutil.rmtree(
                    generated_dir,
                )
            else:
                generated_dir.unlink()

        except OSError as exc:
            raise ConfigError(
                f"Cannot clean artifact {artifact_id!r}: {generated_dir}: {exc}"
            ) from exc


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
    Ingest artwork and add its required configuration values.
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

    updates["model"] = _ARTWORK_MODEL
    updates["source"] = str(destination.resolve())


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


__all__ = [
    "clean_artifact",
    "configure_artifact",
    "list_artifacts",
]
