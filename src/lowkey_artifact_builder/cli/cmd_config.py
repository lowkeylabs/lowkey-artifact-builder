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
from typing import Any

import click

from lowkey_artifact_builder.cli.bindings import (
    parse_parameter_bindings,
)
from lowkey_artifact_builder.cli.display import (
    display_artifact_definition,
    display_model_workplans,
    display_models,
    display_realization_definition,
)
from lowkey_artifact_builder.config import (
    ConfigError,
    configure_realization,
    get_realization_names,
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
@click.option(
    "--realization",
    type=str,
    help="Inspect or customize one Artifact Realization.",
)
@click.option(
    "--parameters",
    multiple=True,
    metavar="NAME=VALUE",
    help="Customize a parameter for the selected Realization.",
)
def cli(
    artifact_ids: tuple[str, ...],
    list_models: bool,
    dump: bool,
    workplan: bool,
    realization: str | None,
    parameters: tuple[str, ...],
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

        if realization is not None:
            raise click.UsageError("--realization cannot be used with --list-models.")

        if parameters:
            raise click.UsageError("--parameters cannot be used with --list-models.")

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

    if parameters and realization is None:
        raise click.UsageError("--parameters requires --realization.")

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
    # Realization configuration
    # =====================================================

    if realization is not None:
        if parameters:
            try:
                parsed_parameters = parse_parameter_bindings(
                    parameters,
                )
            except ValueError as exc:
                raise click.ClickException(str(exc)) from exc

            _configure_realization(
                artifact_id,
                realization,
                parsed_parameters,
                project_root=project_root,
            )
            return

        _display_realization(
            artifact_id,
            realization,
            project_root=project_root,
        )
        return

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
    Display an Artifact's authored configuration and effective
    Realization catalog.

    The Artifact must already be defined.
    """

    existing = load_artifact_config(
        artifact_id,
        project_root=project_root,
    )

    if not existing:
        raise click.ClickException(f"Artifact {artifact_id!r} is not defined.")

    try:
        realizations = get_realization_names(
            artifact_id,
            project_root=project_root,
        )
    except ConfigError as exc:
        raise click.ClickException(str(exc)) from exc

    display_artifact_definition(
        artifact_id,
        existing,
        realizations,
    )


# =========================================================
# Realization display
# =========================================================


def _display_realization(
    artifact_id: str,
    realization: str,
    *,
    project_root: Path,
) -> None:
    """
    Display Artifact-authored customization for one effective
    Realization.

    Canonical Realizations need not have an authored configuration
    entry. In that case the authored customization is empty.
    """

    existing = load_artifact_config(
        artifact_id,
        project_root=project_root,
    )

    if not existing:
        raise click.ClickException(f"Artifact {artifact_id!r} is not defined.")

    try:
        realizations = get_realization_names(
            artifact_id,
            project_root=project_root,
        )
    except ConfigError as exc:
        raise click.ClickException(str(exc)) from exc

    if realization not in realizations:
        raise click.ClickException(
            f"Realization {realization!r} is not defined for Artifact {artifact_id!r}."
        )

    authored_realizations = existing.get("realizations", {})

    authored: dict[str, Any] = {}
    if isinstance(authored_realizations, dict):
        candidate = authored_realizations.get(realization, {})
        if isinstance(candidate, dict):
            authored = candidate

    display_realization_definition(
        artifact_id,
        realization,
        authored,
    )


# =========================================================
# Realization customization
# =========================================================


def _configure_realization(
    artifact_id: str,
    realization: str,
    parameters: dict[str, object],
    *,
    project_root: Path,
) -> None:
    """
    Customize parameters for an existing effective Artifact
    Realization.
    """

    try:
        configure_realization(
            artifact_id,
            realization,
            parameters=parameters,
            project_root=project_root,
        )
    except ConfigError as exc:
        raise click.ClickException(str(exc)) from exc


if __name__ == "__main__":
    cli()
