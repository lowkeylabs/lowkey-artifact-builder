"""
Configuration command.

Provides configuration inspection and management for artifacts.

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
from lowkey_artifact_builder.cli.setup import (
    setup_artifact,
)
from lowkey_artifact_builder.config import (
    get_resolver,
    update_artifact_config,
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
    Manage artifact configuration.

    Positional arguments are artifact IDs.
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

    # =====================================================
    # Artifact configuration
    # =====================================================

    if artifact_ids:
        if len(artifact_ids) != 1:
            raise click.UsageError("Artifact configuration requires exactly one artifact ID.")

        artifact_id = artifact_ids[0]
        project_root = Path.cwd()

        registry = build_model_registry()

        # -------------------------------------------------
        # Configuration dump
        # -------------------------------------------------

        if dump:
            resolver = get_resolver(
                artifact_id,
                project_root=project_root,
            )

            model_name = resolver("model")

            model = registry.get_model(model_name)

            display_artifact_config(
                artifact_id,
                model,
                resolver,
            )

            return

        # -------------------------------------------------
        # Interactive configuration
        # -------------------------------------------------

        setup = setup_artifact(
            artifact_id,
            registry,
            project_root=project_root,
        )

        values = dict(setup.values)

        values["model"] = setup.model

        update_artifact_config(
            artifact_id,
            values,
            project_root=project_root,
        )

        return

    # =====================================================
    # Configuration dump
    # =====================================================

    if dump:
        click.echo("Configuration dump is not yet implemented.")

        return

    # =====================================================
    # Configuration summary
    # =====================================================

    click.echo("Configuration management is not yet implemented.")


if __name__ == "__main__":
    cli()
