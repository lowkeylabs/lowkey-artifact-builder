"""
Artifact creation command.

Ingests source artwork into the project's preserved-original registry.

CREATE owns source ingestion only. Model defaults and Variant configuration
are registered reusable configuration. Artifact workspace materialization and
Product realization are responsibilities of BUILD.
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
    Ingest Artifact source artwork into originals/.
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
    Ingest the root-level PNG intake queue.

    Root-level intake PNGs are owned by the batch workflow. The complete
    intake queue is preflighted before any persistent project state is
    modified.

    Successfully ingested sources are moved into the authoritative originals/
    registry. Verified duplicates are reported and left in the intake queue
    unless --clean requests their removal.

    CREATE does not materialize Artifact workspaces.
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

        _preserve_intake_original(
            source_path,
            artifact_id=artifact_id,
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
    Classify the complete root-level intake queue before mutation.

    originals/ is the authoritative registry of ingested Artifact identities.

    Artifact identities are case-insensitive. Incoming content may identify a
    verified duplicate only when its fingerprint matches exactly one preserved
    original. Multiple preserved originals may legitimately contain identical
    content; an incoming PNG matching more than one is ambiguous.

    The complete intake queue is classified before any persistent mutation.
    """

    originals = _discover_originals(project_root)

    originals_by_identity: dict[str, Path] = {}
    originals_by_digest: dict[str, list[Path]] = {}

    for original in originals:
        artifact_id = original.stem
        identity = artifact_id.casefold()

        existing_original = originals_by_identity.get(identity)

        if existing_original is not None:
            raise click.ClickException(
                f"Preserved originals define conflicting Artifact IDs "
                f"{existing_original.stem!r} and {artifact_id!r}."
            )

        originals_by_identity[identity] = original

        digest = _sha256(original)
        originals_by_digest.setdefault(
            digest,
            [],
        ).append(original)

    proposed_ids: dict[str, Path] = {}
    new_sources: list[Path] = []
    duplicate_sources: list[Path] = []

    for source_path in sources:
        artifact_id = source_path.stem
        identity = artifact_id.casefold()

        previous_source = proposed_ids.get(identity)

        if previous_source is not None:
            raise click.ClickException(
                f"Artifact ID {artifact_id!r} conflicts with intake {previous_source.name!r}."
            )

        proposed_ids[identity] = source_path

        source_digest = _sha256(source_path)
        existing_original = originals_by_identity.get(identity)

        if existing_original is not None:
            if _sha256(existing_original) == source_digest:
                console.print(
                    f"{source_path.name} [bold]DUPLICATE[/bold] "
                    f"of Artifact {existing_original.stem!r}"
                )

                duplicate_sources.append(source_path)
                continue

            raise click.ClickException(
                f"Incoming PNG {source_path.name!r} conflicts with "
                f"existing Artifact {existing_original.stem!r}."
            )

        matching_originals = originals_by_digest.get(
            source_digest,
            [],
        )

        if len(matching_originals) == 1:
            matching_original = matching_originals[0]

            console.print(
                f"{source_path.name} [bold]DUPLICATE[/bold] of Artifact {matching_original.stem!r}"
            )

            duplicate_sources.append(source_path)
            continue

        if len(matching_originals) > 1:
            matching_ids = sorted(original.stem for original in matching_originals)
            matches = ", ".join(repr(artifact_id) for artifact_id in matching_ids)

            raise click.ClickException(
                f"Intake PNG {source_path.name!r} is ambiguous: its content "
                f"matches multiple Artifacts: {matches}."
            )

        new_sources.append(source_path)

    return new_sources, duplicate_sources


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
    artifact_id: str,
    project_root: Path,
) -> None:
    """
    Preserve and consume one successfully ingested batch-owned source.

    The Artifact ID determines the canonical preserved filename independently
    of the incoming filename spelling.
    """

    originals_dir = project_root / "originals"
    originals_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    destination = originals_dir / f"{artifact_id}.png"

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
    artifact_id: str,
    project_root: Path,
) -> None:
    """
    Preserve a caller-owned source under its canonical Artifact identity.

    Explicit ingestion does not consume the caller-owned source.
    """

    originals_dir = project_root / "originals"
    originals_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    destination = originals_dir / f"{artifact_id}.png"

    if destination.exists():
        raise click.ClickException(f"Original PNG for Artifact {artifact_id!r} already exists.")

    try:
        shutil.copy2(
            source_path,
            destination,
        )
    except OSError as exc:
        raise click.ClickException(
            f"Could not preserve original PNG for Artifact {artifact_id!r}: {exc}"
        ) from exc


def _preflight_original_destination(
    artifact_id: str,
    *,
    project_root: Path,
) -> None:
    """
    Verify that ingestion will not overwrite the canonical preserved original.
    """

    destination = project_root / "originals" / f"{artifact_id}.png"

    if destination.exists():
        raise click.ClickException(f"Original PNG for Artifact {artifact_id!r} already exists.")


def _create_artifact(
    artifact_id: str,
    *,
    source: str | None,
    project_root: Path,
) -> None:
    """
    Ingest one explicitly named Artifact source.

    Explicit creation treats the selected source as caller-owned. The source
    remains in place while an independent canonical original is preserved in
    project-owned storage.

    CREATE does not materialize the Artifact workspace.
    """

    originals = _discover_originals(project_root)

    existing_originals = {original.stem.casefold(): original for original in originals}

    existing_original = existing_originals.get(
        artifact_id.casefold(),
    )

    if existing_original is not None:
        raise click.ClickException(
            f"Artifact {artifact_id!r} conflicts with existing Artifact {existing_original.stem!r}."
        )

    source_path = _resolve_source(
        source,
        project_root=project_root,
    )

    _preflight_original_destination(
        artifact_id,
        project_root=project_root,
    )

    _copy_original(
        source_path,
        artifact_id=artifact_id,
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
        (
            path
            for path in project_root.iterdir()
            if path.is_file() and path.suffix.lower() == ".png"
        ),
        key=lambda path: path.name.casefold(),
    )


def _discover_originals(
    project_root: Path,
) -> list[Path]:
    """
    Discover preserved Artifact originals in deterministic order.

    Preserved PNG filenames establish ingested Artifact identities.
    """

    originals_dir = project_root / "originals"

    if not originals_dir.is_dir():
        return []

    return sorted(
        (
            path
            for path in originals_dir.iterdir()
            if path.is_file() and path.suffix.lower() == ".png"
        ),
        key=lambda path: path.name.casefold(),
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


if __name__ == "__main__":
    cli()
