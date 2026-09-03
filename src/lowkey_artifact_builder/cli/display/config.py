"""
Artifact configuration display.

This module contains CLI presentation for resolved artifact
configuration.
"""
# File: src/lowkey_artifact_builder/cli/display/config.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

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
# Artifact configuration
# =========================================================


def display_artifact_config(
    artifact_id: str,
    model: ModelSpec,
    resolver: Resolver,
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

        table.add_row(
            name,
            format_value(value),
            source,
        )

    console.print(table)


__all__ = [
    "display_artifact_config",
]
