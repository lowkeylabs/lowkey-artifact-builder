"""
Artifact cleaning command.

Removes derived products for an existing artifact while preserving its
persistent configuration and artifact-owned inputs.
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
def cli(
    artifact_ids: tuple[str, ...],
) -> None:
    """
    Remove derived products for an existing artifact.
    """

    if not artifact_ids:
        raise click.UsageError("Artifact cleaning requires an artifact ID.")

    if len(artifact_ids) != 1:
        raise click.UsageError("Artifact cleaning requires exactly one artifact ID.")

    artifact_id = artifact_ids[0]
    project_root = Path.cwd()

    existing = load_artifact_config(
        artifact_id,
        project_root=project_root,
    )

    if not existing:
        raise click.ClickException(f"Artifact {artifact_id!r} is not defined.")

    try:
        clean_artifact(
            artifact_id,
            project_root=project_root,
        )

    except ConfigError as exc:
        raise click.ClickException(str(exc)) from exc


if __name__ == "__main__":
    cli()
