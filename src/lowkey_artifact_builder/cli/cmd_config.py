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
from typing import Any

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
    ConfigError,
    configure_artifact,
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

    if not artifact_ids:
        raise click.UsageError("Artifact configuration requires an artifact ID.")

    if len(artifact_ids) != 1:
        raise click.UsageError("Artifact configuration requires exactly one artifact ID.")

    artifact_id = artifact_ids[0]
    project_root = Path.cwd()

    # =====================================================
    # Configuration dump
    # =====================================================

    if dump:
        _display_artifact(
            artifact_id,
            project_root=project_root,
        )
        return

    # =====================================================
    # Existing artifact
    # =====================================================

    existing = load_artifact_config(
        artifact_id,
        project_root=project_root,
    )

    if existing:
        _display_artifact(
            artifact_id,
            project_root=project_root,
        )
        return

    # =====================================================
    # Interactive configuration
    # =====================================================

    registry = build_model_registry()

    setup = setup_artifact(
        artifact_id,
        registry,
        project_root=project_root,
    )

    values = dict(setup.values)

    input_files = _extract_input_files(
        values,
        project_root=project_root,
    )

    values["model"] = setup.model

    try:
        configure_artifact(
            artifact_id,
            values=values,
            input_files=input_files,
            project_root=project_root,
        )

    except ConfigError as exc:
        raise click.ClickException(str(exc)) from exc

    # =====================================================
    # Artifact display
    # =====================================================

    _display_artifact(
        artifact_id,
        project_root=project_root,
    )


# =========================================================
# Setup translation
# =========================================================


def _extract_input_files(
    values: dict[str, Any],
    *,
    project_root: Path,
) -> dict[str, Path]:
    """
    Extract external inputs collected by interactive setup.

    Setup collects model parameter values but does not persist them or
    materialize external files.

    External source parameters are translated here into semantic input
    roles understood by the high-level artifact configuration API.

    Extracted source parameters are removed from values so external
    filesystem paths are not persisted directly by the CLI.
    """

    input_files: dict[str, Path] = {}

    source = values.pop(
        "source",
        None,
    )

    if source is not None:
        if not isinstance(
            source,
            str,
        ):
            raise click.ClickException("Artifact source must be a path string.")

        input_files["artwork"] = project_root / source

    return input_files


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
        model = registry.get_model(model_name)

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
