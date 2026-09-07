"""
Artifact creation command.

Creates a new persistent artifact definition from source artwork.

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
    Create a new artifact.
    """

    if not artifact_ids:
        raise click.UsageError("Artifact creation requires an artifact ID.")

    if len(artifact_ids) != 1:
        raise click.UsageError("Artifact creation requires exactly one artifact ID.")

    artifact_id = artifact_ids[0]
    project_root = Path.cwd()

    # =====================================================
    # Existing artifact
    # =====================================================

    existing = load_artifact_config(
        artifact_id,
        project_root=project_root,
    )

    if existing:
        raise click.ClickException(f"Artifact {artifact_id!r} is already defined.")

    # =====================================================
    # Source
    # =====================================================

    source_path = _resolve_source(
        source,
        project_root=project_root,
    )

    # =====================================================
    # Persistence
    # =====================================================

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

    # =====================================================
    # Result
    # =====================================================

    _display_artifact(
        artifact_id,
        project_root=project_root,
    )


# =========================================================
# Source
# =========================================================


def _resolve_source(
    source: str | None,
    *,
    project_root: Path,
) -> Path:
    """
    Resolve the PNG source selected for a new Artifact.

    An explicitly supplied source is validated directly. Otherwise the user
    selects from PNG files present in the project root.
    """

    if source is not None:
        return _validate_source(
            project_root / source,
        )

    sources = sorted(
        path for path in project_root.iterdir() if path.is_file() and path.suffix.lower() == ".png"
    )

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
