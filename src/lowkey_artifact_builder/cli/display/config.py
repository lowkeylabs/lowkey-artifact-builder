"""
Artifact configuration display.

This module contains CLI presentation for authored Artifact definitions
and resolved artifact configuration.
"""
# File: src/lowkey_artifact_builder/cli/display/config.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

from lowkey_artifact_builder.cli.display.common import (
    console,
    create_table,
    format_value,
)
from lowkey_artifact_builder.config import (
    Resolver,
)
from lowkey_artifact_builder.model import (
    ModelSpec,
)

# =========================================================
# Artifact definition
# =========================================================


def display_artifact_definition(
    artifact_id: str,
    configuration: Mapping[str, object],
    realizations: Sequence[str],
) -> None:
    """
    Display an Artifact's authored configuration and effective
    Realization catalog.
    """

    console.print(f"[bold]{artifact_id} Configuration[/bold]")

    console.print()

    summary = create_table(
        show_header=False,
    )

    summary.add_column(
        "Field",
        style="bold",
    )

    summary.add_column(
        "Value",
    )

    summary.add_row(
        "Artifact ID",
        artifact_id,
    )

    console.print(summary)

    console.print()
    console.print("[bold]Artifact configuration[/bold]")
    console.print()

    configuration_table = create_table()

    configuration_table.add_column(
        "Parameter",
    )

    configuration_table.add_column(
        "Value",
    )

    for name, value in configuration.items():
        configuration_table.add_row(
            name,
            _format_parameter_value(value),
        )

    console.print(configuration_table)

    console.print()
    console.print("[bold]Realizations[/bold]")
    console.print()

    realization_table = create_table()

    realization_table.add_column(
        "Realization",
    )

    for realization in realizations:
        realization_table.add_row(
            realization,
        )

    console.print(realization_table)


# =========================================================
# Resolved artifact configuration
# =========================================================


def _format_parameter_value(
    value: object,
) -> str:
    """
    Format a configuration value for display.

    Paths are displayed relative to the current working directory when
    possible. Other values use the standard CLI value formatting.
    """

    if isinstance(value, Path):
        try:
            value = value.relative_to(Path.cwd())
        except ValueError:
            pass

    return format_value(value)


def display_artifact_config(
    artifact_id: str,
    model: ModelSpec,
    resolver: Resolver,
    *,
    realization: str = "default",
) -> None:
    """
    Display complete resolved configuration information for an
    artifact.
    """

    console.print(f"[bold]{artifact_id} Configuration[/bold]")

    console.print()

    summary = create_table(
        show_header=False,
    )

    summary.add_column(
        "Field",
        style="bold",
    )

    summary.add_column(
        "Value",
    )

    summary.add_row(
        "Artifact ID",
        artifact_id,
    )

    summary.add_row(
        "Model",
        model.name,
    )

    summary.add_row(
        "Realization",
        realization,
    )

    console.print(summary)

    console.print()

    _display_artifact_parameters(
        model,
        resolver,
    )


# =========================================================
# Resolved parameters
# =========================================================


def _display_artifact_parameters(
    model: ModelSpec,
    resolver: Resolver,
) -> None:
    """
    Display resolved parameters required by an artifact model.
    """

    console.print("[bold]Resolved parameters[/bold]")

    console.print()

    table = create_table()

    table.add_column(
        "Parameter",
    )

    table.add_column(
        "Value",
    )

    table.add_column(
        "Source",
    )

    for name in model.parameters:
        value = resolver(name)

        source = resolver.source(name)

        if name == "source" and isinstance(value, str):
            try:
                value = str(
                    Path(value)
                    .resolve()
                    .relative_to(
                        Path.cwd().resolve(),
                    )
                )
            except ValueError:
                pass

        table.add_row(
            name,
            _format_parameter_value(value),
            source,
        )

    console.print(table)


# =========================================================
# Available Variants
# =========================================================


def display_available_variants(
    artifact_id: str,
    variants: Sequence[str],
) -> None:
    """
    Display the qualified Variants available to an Artifact.
    """

    console.print(f"[bold]{artifact_id} Available Variants[/bold]")
    console.print()

    table = create_table()

    table.add_column(
        "Variant",
    )

    for variant in variants:
        table.add_row(
            variant,
        )

    console.print(table)

    console.print()
    console.print(f"Build one with [bold]artifact build {artifact_id} --variant <variant>[/bold]")
    console.print(f"Build all with [bold]artifact build {artifact_id} --all-variants[/bold]")


__all__ = [
    "display_artifact_config",
    "display_artifact_definition",
    "display_available_variants",
]
