"""
Artifact creation command.

Creates a new persistent artifact definition.

Artifact creation is distinct from configuration of an existing
artifact. Command-line configuration supplies initial setup values, and
interactive setup collects only configuration that remains unresolved.
"""
# File: src/lowkey_artifact_builder/cli/cmd_create.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path
from typing import Any

import click

from lowkey_artifact_builder.cli.bindings import (
    BindingError,
    parse_parameter_bindings,
)
from lowkey_artifact_builder.cli.display import (
    display_artifact_config,
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


@click.command("create")
@click.argument(
    "artifact_ids",
    nargs=-1,
)
@click.option(
    "--param",
    "parameter_bindings",
    metavar="NAME=VALUE",
    multiple=True,
    help="Supply an initial artifact configuration value.",
)
def cli(
    artifact_ids: tuple[str, ...],
    parameter_bindings: tuple[str, ...],
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
    # Initial configuration
    # =====================================================

    try:
        initial_values = parse_parameter_bindings(
            parameter_bindings,
        )

    except BindingError as exc:
        raise click.ClickException(str(exc)) from exc

    # =====================================================
    # Setup completion
    # =====================================================

    registry = build_model_registry()

    setup = setup_artifact(
        artifact_id,
        registry,
        values=initial_values,
        project_root=project_root,
    )

    setup_values = dict(setup.values)

    input_files = _extract_input_files(
        setup_values,
        project_root=project_root,
    )

    values = _default_realization_values(
        setup.model,
        setup_values,
    )

    # =====================================================
    # Persistence
    # =====================================================

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
    # Result
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
    Extract external inputs collected during artifact setup.

    External source parameters are translated into semantic input roles
    understood by the high-level artifact configuration API.

    Extracted source parameters are removed from values so external
    filesystem paths are not persisted directly as configuration.
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


def _default_realization_values(
    model: str,
    values: dict[str, Any],
) -> dict[str, Any]:
    """
    Translate completed setup values into persistent realization structure.

    Newly created artifacts explicitly define an ordinary realization
    named default. Model identity belongs to that realization, and
    completed model configuration is persisted as its parameters.

    The setup model value is structural identity rather than a model
    parameter and is therefore not duplicated beneath parameters.
    """

    parameters = dict(values)
    parameters.pop(
        "model",
        None,
    )

    default: dict[str, Any] = {
        "model": model,
    }

    if parameters:
        default["parameters"] = parameters

    return {
        "realizations": {
            "default": default,
        },
    }


# =========================================================
# Artifact display
# =========================================================


def _display_artifact(
    artifact_id: str,
    *,
    project_root: Path,
) -> None:
    """
    Display the newly created artifact's resolved configuration.
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
