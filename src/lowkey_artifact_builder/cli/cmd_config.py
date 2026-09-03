"""
Configuration command.

Provides configuration inspection and management for existing artifacts.

Artifact creation is a distinct lifecycle operation owned by the
``artifact create`` command.

Positional arguments to this command are reserved for artifact IDs.
Additional configuration operations are exposed through command-line
options.
"""
# File: src/lowkey_artifact_builder/cli/cmd_config.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path

import click

from lowkey_artifact_builder.cli.display import (
    display_artifact_config,
    display_model_workplans,
    display_models,
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


@click.command("config")
@click.argument(
    "artifact_ids",
    nargs=-1,
)
@click.option(
    "--list-models",
    is_flag=True,
    help="List available artifact models.",
)
@click.option(
    "--dump",
    is_flag=True,
    help="Display complete configuration information.",
)
@click.option(
    "--workplan",
    is_flag=True,
    help="Display model stage workplans.",
)
def cli(
    artifact_ids: tuple[str, ...],
    list_models: bool,
    dump: bool,
    workplan: bool,
) -> None:
    """
    Manage configuration for an existing artifact.

    Positional arguments are artifact IDs.

    Artifact creation is performed by ``artifact create``.
    """

    # =====================================================
    # Model inspection
    # =====================================================

    if list_models:
        if artifact_ids:
            raise click.UsageError("--list-models cannot be used with artifact IDs.")

        if dump and workplan:
            raise click.UsageError("--dump and --workplan cannot be used together.")

        registry = build_model_registry()
        models = registry.all_models()

        if workplan:
            display_model_workplans(
                models,
            )
            return

        display_models(
            models,
            dump=dump,
        )
        return

    # =====================================================
    # Artifact option validation
    # =====================================================

    if workplan:
        raise click.UsageError("--workplan currently requires --list-models.")

    if not artifact_ids:
        raise click.UsageError("Artifact configuration requires an artifact ID.")

    if len(artifact_ids) != 1:
        raise click.UsageError("Artifact configuration requires exactly one artifact ID.")

    artifact_id = artifact_ids[0]
    project_root = Path.cwd()

    # =====================================================
    # Existing artifact
    # =====================================================

    existing = load_artifact_config(
        artifact_id,
        project_root=project_root,
    )

    if not existing:
        raise click.ClickException(f"Artifact {artifact_id!r} is not defined.")

    # =====================================================
    # Artifact display
    # =====================================================

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

    existing = load_artifact_config(
        artifact_id,
        project_root=project_root,
    )

    if not existing:
        raise click.ClickException(f"Artifact {artifact_id!r} is not defined.")

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
