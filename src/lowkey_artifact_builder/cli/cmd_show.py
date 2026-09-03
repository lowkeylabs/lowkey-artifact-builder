"""
Artifact inspection command.

Displays the resolved configuration of an existing artifact without
modifying persistent artifact state.
"""
# File: src/lowkey_artifact_builder/cli/cmd_show.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path

import click

from lowkey_artifact_builder.cli.display import (
    display_artifact_config,
)
from lowkey_artifact_builder.config import (
    ConfigError,
    get_resolver,
    load_artifact_config,
)
from lowkey_artifact_builder.model import (
    build_model_registry,
)

# =========================================================
# CLI
# =========================================================


@click.command("show")
@click.argument(
    "artifact_ids",
    nargs=-1,
)
def cli(
    artifact_ids: tuple[str, ...],
) -> None:
    """
    Display an existing artifact's resolved configuration.
    """

    if not artifact_ids:
        raise click.UsageError("Artifact inspection requires an artifact ID.")

    if len(artifact_ids) != 1:
        raise click.UsageError("Artifact inspection requires exactly one artifact ID.")

    artifact_id = artifact_ids[0]
    project_root = Path.cwd()

    existing = load_artifact_config(
        artifact_id,
        project_root=project_root,
    )

    if not existing:
        raise click.ClickException(f"Artifact {artifact_id!r} is not defined.")

    _display_artifact(
        artifact_id,
        project_root=project_root,
    )


# =========================================================
# Artifact display
# =========================================================


def _display_artifact(
    artifact_id: str,
    *,
    project_root: Path,
) -> None:
    """
    Display an artifact's resolved configuration.

    The artifact must already be defined.
    """

    try:
        resolver = get_resolver(
            artifact_id,
            project_root=project_root,
        )

        model_name = resolver("model")

        registry = build_model_registry()
        model = registry.get_model(
            model_name,
        )

    except (
        ConfigError,
        KeyError,
    ) as exc:
        raise click.ClickException(str(exc)) from exc

    display_artifact_config(
        artifact_id,
        model,
        resolver,
    )


if __name__ == "__main__":
    cli()
