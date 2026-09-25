"""
Artifact creation command.

Registers Artifact identity in the project's preserved-original registry.

CREATE owns Artifact registration and source ingestion only. Source-backed
Artifacts are registered by a canonical PNG in originals/. Source-less
Artifacts are registered by a zero-content .artifact marker in originals/.

Source artwork presented to CREATE is intake material. Successful ingestion
consumes that source into the authoritative originals/ registry.

Artifact workspace materialization and Product realization are
responsibilities of BUILD.
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
    display_create_status,
)
from lowkey_artifact_builder.config import list_artifacts

# =========================================================
# CLI
# =========================================================


@click.command("create")
@click.option(
    "--artifact-id",
    type=str,
    help="Assign the Artifact ID explicitly.",
)
@click.option(
    "--source",
    type=str,
    help="Ingest the specified PNG as the Artifact source.",
)
@click.option(
    "--all-sources",
    is_flag=True,
    help="Ingest all root-level PNG sources.",
)
def cli(
    artifact_id: str | None,
    source: str | None,
    all_sources: bool,
) -> None:
    """
    Inspect intake state or explicitly register Artifact identity and sources.
    """

    project_root = Path.cwd()

    if all_sources:
        if source is not None:
            raise click.UsageError("--all-sources cannot be combined with --source.")

        if artifact_id is not None:
            raise click.UsageError("--all-sources cannot be combined with --artifact-id.")

        _create_all_sources(
            project_root=project_root,
        )
        return

    if source is not None:
        source_path = _validate_source(
            project_root / source,
        )

        resolved_artifact_id = artifact_id if artifact_id is not None else source_path.stem

        _create_source_artifact(
            resolved_artifact_id,
            source_path=source_path,
            project_root=project_root,
        )
        return

    if artifact_id is not None:
        _create_sourceless_artifact(
            artifact_id,
            project_root=project_root,
        )
        return

    artifact_ids = tuple(
        list_artifacts(
            project_root=project_root,
        )
    )

    sources = _discover_sources(project_root)

    display_create_status(
        artifact_ids,
        sources,
    )


# =========================================================
# Creation
# =========================================================


def _create_sourceless_artifact(
    artifact_id: str,
    *,
    project_root: Path,
) -> None:
    """
    Register one source-less Artifact.

    A zero-content .artifact marker establishes persistent Artifact identity
    without implying that source artwork or Artifact configuration exists.

    CREATE does not materialize the Artifact workspace.
    """

    _preflight_artifact_identity(
        artifact_id,
        project_root=project_root,
    )

    originals_dir = project_root / "originals"
    originals_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    marker = originals_dir / f"{artifact_id}.artifact"

    try:
        marker.touch(
            exist_ok=False,
        )
    except OSError as exc:
        raise click.ClickException(f"Could not register Artifact {artifact_id!r}: {exc}") from exc

    console.print(f"Registered source-less Artifact [bold]{artifact_id}[/bold].")


def _create_source_artifact(
    artifact_id: str,
    *,
    source_path: Path,
    project_root: Path,
) -> None:
    """
    Register one source-backed Artifact.

    The selected source is intake material and is consumed into originals/
    under the canonical Artifact identity.

    CREATE does not materialize the Artifact workspace.
    """

    _preflight_source_intake(
        ((artifact_id, source_path),),
        project_root=project_root,
    )

    _preserve_intake_original(
        source_path,
        artifact_id=artifact_id,
        project_root=project_root,
    )

    console.print(f"Created Artifact [bold]{artifact_id}[/bold] from {source_path.name}.")


def _create_all_sources(
    *,
    project_root: Path,
) -> None:
    """
    Register every eligible root-level PNG source.

    Artifact identities derive from source filename stems. The complete intake
    queue is preflighted before any persistent project state is modified.

    Successfully ingested sources are consumed into originals/. Verified
    duplicates are reported and remain in the intake queue; duplicate cleanup
    belongs to the CLEAN command.

    CREATE does not materialize Artifact workspaces.
    """

    sources = _discover_sources(project_root)

    if not sources:
        return

    requests = tuple((source_path.stem, source_path) for source_path in sources)

    new_requests, duplicate_sources = _preflight_source_intake(
        requests,
        project_root=project_root,
    )

    for artifact_id, source_path in new_requests:
        _preserve_intake_original(
            source_path,
            artifact_id=artifact_id,
            project_root=project_root,
        )

        console.print(f"Created Artifact [bold]{artifact_id}[/bold] from {source_path.name}.")

    for source_path in duplicate_sources:
        console.print(
            f"{source_path.name} remains in the intake queue; "
            "use artifact clean to remove verified duplicates."
        )


# =========================================================
# Intake preflight
# =========================================================


def _preflight_source_intake(
    requests: tuple[tuple[str, Path], ...],
    *,
    project_root: Path,
) -> tuple[list[tuple[str, Path]], list[Path]]:
    """
    Classify a complete source-ingestion request before mutation.

    originals/ is the authoritative registry of Artifact identities.

    Both preserved PNGs and source-less .artifact markers establish Artifact
    identity. Artifact identities are case-insensitive.

    Incoming content may identify a verified duplicate only when its
    fingerprint matches exactly one preserved original. Multiple preserved
    originals may legitimately contain identical content; an incoming PNG
    matching more than one is ambiguous.

    Source-less registrations participate in identity collision detection but
    cannot participate in content-based duplicate recognition.

    The complete request is classified before any persistent mutation.
    """

    registrations = _discover_registrations(project_root)

    registrations_by_identity: dict[str, Path] = {}
    originals_by_digest: dict[str, list[Path]] = {}

    for registration in registrations:
        artifact_id = registration.stem
        identity = artifact_id.casefold()

        existing_registration = registrations_by_identity.get(identity)

        if existing_registration is not None:
            raise click.ClickException(
                f"Artifact registrations define conflicting Artifact IDs "
                f"{existing_registration.stem!r} and {artifact_id!r}."
            )

        registrations_by_identity[identity] = registration

        if registration.suffix.lower() == ".png":
            digest = _sha256(registration)
            originals_by_digest.setdefault(
                digest,
                [],
            ).append(registration)

    proposed_ids: dict[str, Path] = {}
    new_requests: list[tuple[str, Path]] = []
    duplicate_sources: list[Path] = []

    for artifact_id, source_path in requests:
        identity = artifact_id.casefold()

        previous_source = proposed_ids.get(identity)

        if previous_source is not None:
            raise click.ClickException(
                f"Artifact ID {artifact_id!r} conflicts with intake {previous_source.name!r}."
            )

        proposed_ids[identity] = source_path

        source_digest = _sha256(source_path)
        existing_registration = registrations_by_identity.get(identity)

        if existing_registration is not None:
            if (
                existing_registration.suffix.lower() == ".png"
                and _sha256(existing_registration) == source_digest
            ):
                console.print(
                    f"{source_path.name} [bold]DUPLICATE[/bold] "
                    f"of Artifact {existing_registration.stem!r}"
                )

                duplicate_sources.append(source_path)
                continue

            raise click.ClickException(
                f"Incoming PNG {source_path.name!r} conflicts with "
                f"existing Artifact {existing_registration.stem!r}."
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
            matches = ", ".join(repr(matching_id) for matching_id in matching_ids)

            raise click.ClickException(
                f"Intake PNG {source_path.name!r} is ambiguous: its content "
                f"matches multiple Artifacts: {matches}."
            )

        new_requests.append(
            (
                artifact_id,
                source_path,
            )
        )

    return new_requests, duplicate_sources


def _preflight_artifact_identity(
    artifact_id: str,
    *,
    project_root: Path,
) -> None:
    """
    Verify that an Artifact identity is not already registered.

    Source-backed and source-less registrations occupy the same
    case-insensitive Artifact identity namespace.
    """

    identity = artifact_id.casefold()

    for registration in _discover_registrations(project_root):
        if registration.stem.casefold() == identity:
            raise click.ClickException(
                f"Artifact {artifact_id!r} conflicts with existing Artifact {registration.stem!r}."
            )


# =========================================================
# Persistence
# =========================================================


def _preserve_intake_original(
    source_path: Path,
    *,
    artifact_id: str,
    project_root: Path,
) -> None:
    """
    Preserve and consume one successfully ingested source.

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


# =========================================================
# Discovery
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


def _discover_registrations(
    project_root: Path,
) -> list[Path]:
    """
    Discover registered Artifact identities in deterministic order.

    A preserved PNG registers a source-backed Artifact. A zero-content
    .artifact marker registers a source-less Artifact.
    """

    originals_dir = project_root / "originals"

    if not originals_dir.is_dir():
        return []

    return sorted(
        (
            path
            for path in originals_dir.iterdir()
            if path.is_file()
            and path.suffix.lower()
            in {
                ".png",
                ".artifact",
            }
        ),
        key=lambda path: path.name.casefold(),
    )


def _discover_originals(
    project_root: Path,
) -> list[Path]:
    """
    Discover preserved source artwork in deterministic order.

    This helper remains source-specific. Use _discover_registrations when
    Artifact identity, rather than artwork availability, is the concern.
    """

    return [
        registration
        for registration in _discover_registrations(project_root)
        if registration.suffix.lower() == ".png"
    ]


# =========================================================
# Source validation
# =========================================================


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
