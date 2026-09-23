"""
Artifact cleaning command.

Removes derived products while preserving persistent Artifact configuration
and Artifact-owned inputs.
"""
# File: src/lowkey_artifact_builder/cli/cmd_clean.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path

import click

from lowkey_artifact_builder.config import (
    ConfigError,
    clean_artifact,
    clean_realization_across_artifacts,
    list_artifacts,
    load_artifact_config,
)

# =========================================================
# CLI
# =========================================================


@click.command("clean")
@click.argument(
    "artifact_ids",
    nargs=-1,
)
@click.option(
    "--realization",
    type=str,
    default=None,
    help="Clean generated Products for one Realization.",
)
@click.option(
    "-f",
    "--force",
    is_flag=True,
    help="Clean all Artifacts without confirmation.",
)
def cli(
    artifact_ids: tuple[str, ...],
    realization: str | None,
    force: bool,
) -> None:
    """
    Remove derived Products while preserving persistent Artifact state.

    With an Artifact ID, clean generated Products for that Artifact.

    When --realization is provided with an Artifact ID, clean only generated
    Products belonging to that Realization.

    When --realization is provided without an Artifact ID, clean that
    Realization across all existing Artifacts.

    With no Artifact ID or Realization, clean all existing Artifacts after
    confirmation. Use --force to permit unattended project-wide cleaning.
    """

    project_root = Path.cwd()

    # =====================================================
    # All-Artifact scope
    # =====================================================

    if not artifact_ids:
        selected_artifacts = tuple(
            list_artifacts(
                project_root=project_root,
            )
        )

        # -------------------------------------------------
        # One Realization across all Artifacts
        # -------------------------------------------------

        if realization is not None:
            try:
                clean_realization_across_artifacts(
                    selected_artifacts,
                    realization,
                    project_root=project_root,
                )

            except ConfigError as exc:
                raise click.ClickException(str(exc)) from exc

            return

        # -------------------------------------------------
        # All generated Products across all Artifacts
        # -------------------------------------------------

        if not force:
            click.confirm(
                "Clean generated Products for all Artifacts?",
                abort=True,
            )

        try:
            for artifact_id in selected_artifacts:
                clean_artifact(
                    artifact_id,
                    project_root=project_root,
                )

        except ConfigError as exc:
            raise click.ClickException(str(exc)) from exc

        return

    # =====================================================
    # Single Artifact scope
    # =====================================================

    if len(artifact_ids) != 1:
        raise click.UsageError("Artifact cleaning requires exactly one artifact ID.")

    artifact_id = artifact_ids[0]

    existing = load_artifact_config(
        artifact_id,
        project_root=project_root,
    )

    if not existing:
        raise click.ClickException(f"Artifact {artifact_id!r} is not defined.")

    try:
        clean_artifact(
            artifact_id,
            realization=realization,
            project_root=project_root,
        )

    except ConfigError as exc:
        raise click.ClickException(str(exc)) from exc


if __name__ == "__main__":
    cli()
