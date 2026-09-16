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

from pathlib import Path

import click

from lowkey_artifact_builder.cli.display import (
    console,
)
from lowkey_artifact_builder.config import (
    ConfigError,
    configure_artifact,
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
def cli(
    artifact_ids: tuple[str, ...],
    source: str | None,
) -> None:
    """
    Create new Artifacts from PNG source artwork.
    """

    project_root = Path.cwd()

    if not artifact_ids:
        _create_intake_batch(
            source=source,
            project_root=project_root,
        )
        return

    if len(artifact_ids) != 1:
        raise click.UsageError("Artifact creation accepts at most one explicit artifact ID.")

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
    project_root: Path,
) -> None:
    """
    Create Artifacts from the root-level PNG intake queue.
    """

    if source is not None:
        raise click.UsageError("--source requires an explicit artifact ID.")

    sources = _discover_sources(project_root)

    for source_path in sources:
        _create_artifact_from_source(
            source_path.stem,
            source_path=source_path,
            project_root=project_root,
        )


def _create_artifact(
    artifact_id: str,
    *,
    source: str | None,
    project_root: Path,
) -> None:
    """
    Create one explicitly named Artifact.
    """

    existing = load_artifact_config(
        artifact_id,
        project_root=project_root,
    )

    if existing:
        raise click.ClickException(f"Artifact {artifact_id!r} is already defined.")

    source_path = _resolve_source(
        source,
        project_root=project_root,
    )

    _create_artifact_from_source(
        artifact_id,
        source_path=source_path,
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
            values={},
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
