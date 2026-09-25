"""
Artifact manufacturing inspection command.

Displays operator-oriented manufacturing status for an existing Artifact
without modifying persistent Artifact state.
"""

# File: src/lowkey_artifact_builder/cli/cmd_show.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from lowkey_artifact_builder.application import (
    ArtifactManufacturingStatus,
    inspect_artifact_manufacturing,
)
from lowkey_artifact_builder.config import (
    ConfigError,
)

# =========================================================
# CLI
# =========================================================


@click.command("show")
@click.argument(
    "artifact_ids",
    nargs=-1,
)
@click.option(
    "--realization",
    type=str,
    default=None,
    help="Select one Artifact Realization.",
)
def cli(
    artifact_ids: tuple[str, ...],
    realization: str | None,
) -> None:
    """
    Show manufacturing status for one Artifact.

    Without --realization, every effective Realization is shown.

    --realization narrows inspection to one effective Realization.
    """

    if not artifact_ids:
        raise click.UsageError("Artifact inspection requires an artifact ID.")

    if len(artifact_ids) != 1:
        raise click.UsageError("Artifact inspection requires exactly one artifact ID.")

    artifact_id = artifact_ids[0]
    project_root = Path.cwd()

    try:
        status = inspect_artifact_manufacturing(
            artifact_id,
            realization=realization,
            project_root=project_root,
        )

    except ConfigError as exc:
        raise click.ClickException(str(exc)) from exc

    _display_manufacturing_status(
        status,
    )


# =========================================================
# Manufacturing display
# =========================================================


def _display_manufacturing_status(
    status: ArtifactManufacturingStatus,
) -> None:
    """
    Display operator-oriented manufacturing status.

    Routine SHOW output deliberately exposes only manufacturing concepts:

        Realization
        Type
        State
        accessible 3MF

    Engine Stages, resolver details, dependency state, fingerprints, and
    canonical internal Product locations remain below the presentation
    boundary.
    """

    console = Console()

    table = Table(
        title=status.artifact_id,
    )

    table.add_column(
        "Realization",
    )
    table.add_column(
        "Type",
    )
    table.add_column(
        "State",
    )
    table.add_column(
        "3MF",
    )

    for realization in status.realizations:
        table.add_row(
            realization.realization,
            realization.realization_type.value,
            realization.state.value,
            (str(realization.product) if realization.product is not None else "-"),
        )

    console.print(
        table,
    )


if __name__ == "__main__":
    cli()
