"""
Artifact creation command.

Creates new persistent artifact definitions from source artwork.

Model defaults and Variant configuration are registered reusable
configuration. Artifact creation therefore collects only the source PNG
required to define the Artifact.
"""
# File: src/lowkey_artifact_builder/cli/cmd_create.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

import click

from lowkey_artifact_builder.cli.display import (
    console,
)
from lowkey_artifact_builder.config import (
    ConfigError,
    configure_artifact,
    list_artifacts,
    load_artifact_config,
)

# =========================================================
# CLI
# =========================================================


@click.command("create")
@click.argument(
    "artifact_ids",
    nargs=-1,
)
@click.option(
    "--source",
    type=str,
    help="Use the specified PNG as the Artifact source.",
)
@click.option(
    "--clean",
    is_flag=True,
    help="Remove verified duplicate PNGs from the batch intake queue.",
)
def cli(
    artifact_ids: tuple[str, ...],
    source: str | None,
    clean: bool,
) -> None:
    """
    Create new Artifacts from PNG source artwork.
    """

    project_root = Path.cwd()

    if not artifact_ids:
        _create_intake_batch(
            source=source,
            clean=clean,
            project_root=project_root,
        )
        return

    if len(artifact_ids) != 1:
        raise click.UsageError("Artifact creation accepts at most one explicit artifact ID.")

    if clean:
        raise click.UsageError("--clean applies only to bare batch intake.")

    _create_artifact(
        artifact_ids[0],
        source=source,
        project_root=project_root,
    )


# =========================================================
# Creation
# =========================================================


def _create_intake_batch(
    *,
    source: str | None,
    clean: bool,
    project_root: Path,
) -> None:
    """
    Create Artifacts from the root-level PNG intake queue.

    Root-level intake PNGs are owned by the batch workflow. The complete
    intake queue is preflighted before any persistent project state is
    modified.

    Verified duplicates are reported and left in the intake queue unless
    --clean requests their removal.
    """

    if source is not None:
        raise click.UsageError("--source requires an explicit artifact ID.")

    sources = _discover_sources(project_root)

    new_sources, duplicate_sources = _preflight_intake_batch(
        sources,
        project_root=project_root,
    )

    for source_path in new_sources:
        artifact_id = source_path.stem

        _create_artifact_from_source(
            artifact_id,
            source_path=source_path,
            project_root=project_root,
        )

        _preserve_intake_original(
            source_path,
            project_root=project_root,
        )

    for source_path in duplicate_sources:
        if clean or _confirm_duplicate_cleanup(source_path):
            _remove_duplicate_intake(
                source_path,
            )


def _preflight_intake_batch(
    sources: list[Path],
    *,
    project_root: Path,
) -> tuple[list[Path], list[Path]]:
    """
    Classify the complete intake queue before persistent mutation.

    New sources and verified duplicates are returned separately. Incomplete,
    inconsistent, or conflicting existing state aborts the complete batch
    before mutation.

    Artifact identity comparisons are case-insensitive so intake behavior
    remains portable across filesystems. Proposed Artifact identities are
    also checked against one another so a single intake batch cannot create
    ambiguous Artifact IDs.
    """

    existing_artifacts = {
        artifact_id.casefold(): artifact_id
        for artifact_id in list_artifacts(
            project_root=project_root,
        )
    }

    new_sources: list[Path] = []
    duplicate_sources: list[Path] = []
    proposed_artifacts: dict[str, str] = {}

    for source_path in sources:
        artifact_id = source_path.stem
        identity = artifact_id.casefold()

        existing_artifact = existing_artifacts.get(identity)

        if existing_artifact is not None:
            if _preflight_existing_artifact(
                source_path,
                artifact_id=existing_artifact,
                project_root=project_root,
            ):
                duplicate_sources.append(source_path)

            continue

        proposed_artifact = proposed_artifacts.get(identity)

        if proposed_artifact is not None:
            raise click.ClickException(
                f"Intake PNGs infer conflicting Artifact IDs "
                f"{proposed_artifact!r} and {artifact_id!r}."
            )

        proposed_artifacts[identity] = artifact_id

        original_path = project_root / "originals" / source_path.name

        if original_path.exists():
            raise click.ClickException(f"Original PNG {source_path.name!r} already exists.")

        new_sources.append(source_path)

    return new_sources, duplicate_sources


def _preflight_existing_artifact(
    source_path: Path,
    *,
    artifact_id: str,
    project_root: Path,
) -> bool:
    """
    Classify one incoming source that maps to an existing Artifact.

    Return True when the source is a verified duplicate. A verified duplicate
    must match both the preserved original and the Artifact-managed source
    byte-for-byte. Any incomplete, inconsistent, or conflicting state is an
    error.
    """

    original_path = project_root / "originals" / source_path.name
    managed_path = project_root / "artifacts" / artifact_id / "artifact.png"

    if not original_path.is_file():
        raise click.ClickException(
            f"Artifact {artifact_id!r} is incomplete: "
            f"preserved original {original_path.name!r} is missing."
        )

    if not managed_path.is_file():
        raise click.ClickException(
            f"Artifact {artifact_id!r} is incomplete: managed source 'artifact.png' is missing."
        )

    incoming_digest = _sha256(source_path)
    original_digest = _sha256(original_path)
    managed_digest = _sha256(managed_path)

    matches_original = incoming_digest == original_digest
    matches_managed = incoming_digest == managed_digest

    if matches_original and matches_managed:
        console.print(f"{source_path.name} [bold]DUPLICATE[/bold]")
        return True

    if matches_original:
        raise click.ClickException(f"Artifact {artifact_id!r} has inconsistent managed source.")

    if matches_managed:
        raise click.ClickException(f"Artifact {artifact_id!r} has inconsistent preserved original.")

    raise click.ClickException(
        f"Incoming PNG {source_path.name!r} conflicts with existing Artifact {artifact_id!r}."
    )


def _confirm_duplicate_cleanup(
    source_path: Path,
) -> bool:
    """
    Ask whether one verified duplicate should be removed from the intake queue.

    The safe default is to retain the duplicate.
    """

    return click.confirm(
        (
            f"{source_path.name} has already been ingested and is a "
            "verified duplicate.\n\n"
            "Remove the duplicate PNG from the intake directory?"
        ),
        default=False,
    )


def _remove_duplicate_intake(
    source_path: Path,
) -> None:
    """
    Remove one positively verified duplicate from the intake queue.

    This operation is performed only after complete batch preflight and
    successful ingestion of all NEW sources.
    """

    try:
        source_path.unlink()
    except OSError as exc:
        raise click.ClickException(
            f"Could not remove duplicate PNG {source_path.name!r}: {exc}"
        ) from exc


def _preserve_intake_original(
    source_path: Path,
    *,
    project_root: Path,
) -> None:
    """
    Preserve and consume one successfully ingested batch-owned source.

    Moving the source establishes the preserved original and removes the
    successfully processed PNG from the root intake queue as one filesystem
    operation.
    """

    originals_dir = project_root / "originals"
    originals_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    destination = originals_dir / source_path.name

    try:
        shutil.move(
            source_path,
            destination,
        )
    except OSError as exc:
        raise click.ClickException(
            f"Could not preserve original PNG {source_path.name!r}: {exc}"
        ) from exc


def _copy_original(
    source_path: Path,
    *,
    project_root: Path,
) -> None:
    """
    Preserve a caller-owned source without consuming the original file.
    """

    originals_dir = project_root / "originals"
    originals_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    destination = originals_dir / source_path.name

    if destination.exists():
        raise click.ClickException(f"Original PNG {source_path.name!r} already exists.")

    try:
        shutil.copy2(
            source_path,
            destination,
        )
    except OSError as exc:
        raise click.ClickException(
            f"Could not preserve original PNG {source_path.name!r}: {exc}"
        ) from exc


def _preflight_original_destination(
    source_path: Path,
    *,
    project_root: Path,
) -> None:
    """
    Verify that preserving the selected source will not overwrite an existing
    original.
    """

    destination = project_root / "originals" / source_path.name

    if destination.exists():
        raise click.ClickException(f"Original PNG {source_path.name!r} already exists.")


def _create_artifact(
    artifact_id: str,
    *,
    source: str | None,
    project_root: Path,
) -> None:
    """
    Create one explicitly named Artifact.

    Explicit creation treats the selected source as caller-owned. The source
    remains in place while an independent original is preserved in
    project-owned storage.
    """

    existing_artifacts = {
        existing_id.casefold(): existing_id
        for existing_id in list_artifacts(
            project_root=project_root,
        )
    }

    existing_artifact = existing_artifacts.get(artifact_id.casefold())

    if existing_artifact is not None:
        raise click.ClickException(
            f"Artifact {artifact_id!r} conflicts with existing Artifact {existing_artifact!r}."
        )

    source_path = _resolve_source(
        source,
        project_root=project_root,
    )

    _preflight_original_destination(
        source_path,
        project_root=project_root,
    )

    _create_artifact_from_source(
        artifact_id,
        source_path=source_path,
        project_root=project_root,
    )

    _copy_original(
        source_path,
        project_root=project_root,
    )


def _create_artifact_from_source(
    artifact_id: str,
    *,
    source_path: Path,
    project_root: Path,
) -> None:
    """
    Persist one Artifact from an already resolved PNG source.
    """

    try:
        configure_artifact(
            artifact_id,
            values={
                "original": str(Path("originals") / source_path.name),
            },
            input_files={
                "artwork": source_path,
            },
            project_root=project_root,
        )

    except ConfigError as exc:
        raise click.ClickException(str(exc)) from exc

    _display_artifact(
        artifact_id,
        project_root=project_root,
    )


# =========================================================
# Source
# =========================================================


def _discover_sources(
    project_root: Path,
) -> list[Path]:
    """
    Discover root-level PNG source files in deterministic order.
    """

    return sorted(
        path for path in project_root.iterdir() if path.is_file() and path.suffix.lower() == ".png"
    )


def _resolve_source(
    source: str | None,
    *,
    project_root: Path,
) -> Path:
    """
    Resolve the PNG source selected for an explicitly named Artifact.

    An explicitly supplied source is validated directly. Otherwise the user
    selects from PNG files present in the project root.
    """

    if source is not None:
        return _validate_source(
            project_root / source,
        )

    sources = _discover_sources(project_root)

    if not sources:
        raise click.ClickException(f"No PNG source files were found in {project_root}.")

    console.print()
    console.print("[bold]Available PNG sources[/bold]")

    for index, candidate in enumerate(
        sources,
        start=1,
    ):
        console.print(f"  {index}. {candidate.name}")

    console.print()

    choice = click.prompt(
        "Source",
        type=click.IntRange(
            1,
            len(sources),
        ),
    )

    return sources[choice - 1]


def _validate_source(
    source: Path,
) -> Path:
    """
    Validate an explicitly selected Artifact source.
    """

    if source.suffix.lower() != ".png":
        raise click.ClickException("Artifact source must be a PNG file.")

    if not source.is_file():
        raise click.ClickException(f"Artifact source PNG {source.name!r} does not exist.")

    return source


# =========================================================
# Fingerprints
# =========================================================


def _sha256(
    path: Path,
) -> str:
    """
    Return the SHA-256 fingerprint of one file.
    """

    digest = hashlib.sha256()

    with path.open("rb") as stream:
        for chunk in iter(
            lambda: stream.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


# =========================================================
# Artifact display
# =========================================================


def _display_artifact(
    artifact_id: str,
    *,
    project_root: Path,
) -> None:
    """
    Display the newly created Artifact definition.
    """

    existing = load_artifact_config(
        artifact_id,
        project_root=project_root,
    )

    if not existing:
        raise click.ClickException(f"Artifact {artifact_id!r} is not defined.")

    console.print()
    console.print(f"[bold]Created artifact:[/bold] {artifact_id}")


if __name__ == "__main__":
    cli()
