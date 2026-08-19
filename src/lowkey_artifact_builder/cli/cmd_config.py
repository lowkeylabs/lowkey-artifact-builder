"""
Configuration command.

Provides configuration inspection and management for artifacts.

Positional arguments to this command are reserved for artifact IDs.
Additional configuration operations are exposed through command-line
options.
"""

from __future__ import annotations

import click

from lowkey_artifact_builder.cli.display import (
    display_models,
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
def cli(
    artifact_ids: tuple[str, ...],
    list_models: bool,
    dump: bool,
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

        registry = build_model_registry()

        display_models(
            registry.all_models(),
            dump=dump,
        )

        return

    # =====================================================
    # Artifact configuration
    # =====================================================

    #
    # Artifact configuration handling will be implemented as
    # the configuration subsystem is developed.
    #

    if artifact_ids:
        click.echo("Artifact configuration is not yet implemented.")

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
