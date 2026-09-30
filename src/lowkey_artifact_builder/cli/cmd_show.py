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
from rich import box
from rich.console import Console
from rich.table import Table

from lowkey_artifact_builder.application import (
    ArtifactManufacturingStatus,
    ManufacturingState,
    WorkspaceManufacturingStatus,
    inspect_artifact_manufacturing,
    inspect_workspace_manufacturing,
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
    Show manufacturing status.

    Without an Artifact ID, show manufacturing status for the discovered
    workspace.

    With an Artifact ID, show every effective Realization for that Artifact.

    --realization narrows Artifact inspection to one effective Realization.
    """

    project_root = Path.cwd()

    if not artifact_ids:
        status = inspect_workspace_manufacturing(
            project_root=project_root,
        )

        _display_workspace_manufacturing_status(
            status,
        )

        return

    if len(artifact_ids) != 1:
        raise click.UsageError("Artifact inspection requires exactly one artifact ID.")

    artifact_id = artifact_ids[0]

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


def _display_workspace_manufacturing_status(
    status: WorkspaceManufacturingStatus,
) -> None:
    """
    Display a compact operator-oriented workspace manufacturing summary.

    Each Artifact occupies one row. Materialization is reported independently
    from the effective Realizations and their manufacturing states.
    """

    console = Console()

    if not status.artifacts:
        console.print(
            "No Artifacts found in ./originals or ./artifacts.",
        )
        return

    table = Table(
        box=box.SIMPLE_HEAD,
    )

    table.add_column(
        "Artifact",
    )
    table.add_column(
        "Materialized",
    )
    table.add_column(
        "Realizations",
        justify="right",
    )
    table.add_column(
        "Current",
        justify="right",
    )
    table.add_column(
        "Stale",
        justify="right",
    )
    table.add_column(
        "Not Built",
        justify="right",
    )

    for artifact in status.artifacts:
        manufacturing = artifact.manufacturing

        if manufacturing is None:
            continue

        realizations = manufacturing.realizations

        table.add_row(
            artifact.artifact_id,
            "yes" if artifact.materialized else "no",
            str(
                len(realizations),
            ),
            str(
                sum(realization.state is ManufacturingState.CURRENT for realization in realizations)
            ),
            str(sum(realization.state is ManufacturingState.STALE for realization in realizations)),
            str(
                sum(
                    realization.state is ManufacturingState.NOT_BUILT
                    for realization in realizations
                )
            ),
        )

    console.print(
        table,
    )


def _display_path(
    path: Path,
) -> str:
    """
    Return an operator-facing path relative to the current directory when
    possible.
    """

    try:
        return str(
            path.relative_to(Path.cwd()),
        )
    except ValueError:
        return str(path)


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
        box=box.SIMPLE_HEAD,
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
            (_display_path(realization.product) if realization.product is not None else "-"),
        )

    console.print(
        table,
    )


if __name__ == "__main__":
    cli()
