"""
Artifact listing command.

Lists persistent artifact definitions available in the current project.
"""
# File: src/lowkey_artifact_builder/cli/cmd_list.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path

import click

from lowkey_artifact_builder.config import (
    list_artifacts,
)

# =========================================================
# CLI
# =========================================================


@click.command("list")
@click.argument(
    "artifact_ids",
    nargs=-1,
)
def cli(
    artifact_ids: tuple[str, ...],
) -> None:
    """
    List artifacts defined in the current project.
    """

    if artifact_ids:
        raise click.UsageError("Artifact listing does not accept artifact IDs.")

    project_root = Path.cwd()

    artifact_ids = tuple(
        list_artifacts(
            project_root=project_root,
        )
    )

    for artifact_id in artifact_ids:
        click.echo(artifact_id)


if __name__ == "__main__":
    cli()
