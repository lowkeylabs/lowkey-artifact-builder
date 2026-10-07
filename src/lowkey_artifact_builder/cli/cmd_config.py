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

from lowkey_artifact_builder.application.configuration import (
    inspect_realization_configuration,
)
from lowkey_artifact_builder.cli.bindings import (
    parse_parameter_bindings,
)
from lowkey_artifact_builder.cli.display import (
    display_artifact_definition,
    display_realization_configuration,
)
from lowkey_artifact_builder.config import (
    ConfigError,
    configure_realization,
    configure_realization_across_artifacts,
    create_realization,
    create_realization_across_artifacts,
    get_realization_names,
    list_artifacts,
    load_artifact_config,
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
    "--realization",
    type=str,
    help="Inspect or customize one Artifact Realization.",
)
@click.option(
    "--create",
    is_flag=True,
    help="Create an additional named Artifact Realization.",
)
@click.option(
    "--parameters",
    multiple=True,
    metavar="NAME=VALUE",
    help="Customize a parameter for the selected Realization.",
)
def cli(
    artifact_ids: tuple[str, ...],
    realization: str | None,
    create: bool,
    parameters: tuple[str, ...],
) -> None:
    """
    Manage configuration for an existing artifact.

    Positional arguments are artifact IDs.

    Artifact creation is performed by ``artifact create``.
    """

    # =====================================================
    # Artifact option validation
    # =====================================================

    if create and realization is None:
        raise click.UsageError("--create requires --realization.")

    if parameters and realization is None:
        raise click.UsageError("--parameters requires --realization.")

    project_root = Path.cwd()

    # =====================================================
    # Bulk Realization configuration
    # =====================================================

    if not artifact_ids:
        if realization is None:
            raise click.UsageError("Artifact configuration requires an artifact ID.")

        try:
            parsed_parameters = parse_parameter_bindings(
                parameters,
            )
        except ValueError as exc:
            raise click.ClickException(str(exc)) from exc

        if create:
            variant = parsed_parameters.pop(
                "variant",
                None,
            )

            if not isinstance(variant, str) or not variant:
                raise click.UsageError(
                    "--create requires variant=<model>.<variant> in --parameters."
                )

            _create_realization_scope(
                artifact_ids,
                realization,
                variant,
                parsed_parameters,
                project_root=project_root,
            )
            return

        if not parsed_parameters:
            raise click.UsageError("Realization configuration requires --parameters.")

        _configure_realization_scope(
            artifact_ids,
            realization,
            parsed_parameters,
            project_root=project_root,
        )
        return

    # =====================================================
    # Single Artifact
    # =====================================================

    if len(artifact_ids) != 1:
        raise click.UsageError("Artifact configuration requires exactly one artifact ID.")

    artifact_id = artifact_ids[0]

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

            if create:
                variant = parsed_parameters.pop(
                    "variant",
                    None,
                )

                if not isinstance(variant, str) or not variant:
                    raise click.UsageError(
                        "--create requires variant=<model>.<variant> in --parameters."
                    )

                _create_realization(
                    artifact_id,
                    realization,
                    variant,
                    parsed_parameters,
                    project_root=project_root,
                )
                return

            _configure_realization(
                artifact_id,
                realization,
                parsed_parameters,
                project_root=project_root,
            )
            return

        if create:
            raise click.UsageError("--create requires variant=<model>.<variant> in --parameters.")

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
    Display effective construction configuration for one Realization.

    Configuration resolution and provenance belong to the application
    layer. The CLI only delegates inspection and presents the result.
    """

    try:
        configuration = inspect_realization_configuration(
            artifact_id,
            realization,
            project_root=project_root,
        )
    except ConfigError as exc:
        raise click.ClickException(str(exc)) from exc

    display_realization_configuration(
        configuration,
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


# =========================================================
# Realization creation
# =========================================================


def _create_realization(
    artifact_id: str,
    realization: str,
    variant: str,
    parameters: dict[str, object],
    *,
    project_root: Path,
) -> None:
    """
    Create an additional named Artifact Realization.
    """

    try:
        create_realization(
            artifact_id,
            realization,
            variant=variant,
            parameters=parameters,
            project_root=project_root,
        )
    except ConfigError as exc:
        raise click.ClickException(str(exc)) from exc


# =========================================================
# Bulk Realization configuration
# =========================================================


def _configure_realization_scope(
    artifact_ids: tuple[str, ...],
    realization: str,
    parameters: dict[str, object],
    *,
    project_root: Path,
) -> None:
    """
    Customize an existing Realization across an Artifact scope.

    An empty explicit scope selects all existing Artifacts.
    """

    selected_artifacts = artifact_ids

    if not selected_artifacts:
        selected_artifacts = tuple(
            list_artifacts(
                project_root=project_root,
            )
        )

    try:
        configure_realization_across_artifacts(
            selected_artifacts,
            realization,
            parameters=parameters,
            project_root=project_root,
        )
    except ConfigError as exc:
        raise click.ClickException(str(exc)) from exc


def _create_realization_scope(
    artifact_ids: tuple[str, ...],
    realization: str,
    variant: str,
    parameters: dict[str, object],
    *,
    project_root: Path,
) -> None:
    """
    Create an additional named Realization across an Artifact scope.

    An empty explicit scope selects all existing Artifacts.
    """

    selected_artifacts = artifact_ids

    if not selected_artifacts:
        selected_artifacts = tuple(
            list_artifacts(
                project_root=project_root,
            )
        )

    try:
        create_realization_across_artifacts(
            selected_artifacts,
            realization,
            variant=variant,
            parameters=parameters,
            project_root=project_root,
        )
    except ConfigError as exc:
        raise click.ClickException(str(exc)) from exc


if __name__ == "__main__":
    cli()
