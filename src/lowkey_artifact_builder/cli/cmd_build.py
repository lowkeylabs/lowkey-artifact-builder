"""
Build command.

Builds configured artifacts from their declared model workflows.
"""
# File: src/lowkey_artifact_builder/cli/cmd_build.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path

import click

from lowkey_artifact_builder.cli.display import (
    display_build_plan,
)
from lowkey_artifact_builder.engine import (
    BuildError,
    BuildPlanError,
    create_build_plans,
    execute_builds,
)

# =========================================================
# CLI
# =========================================================


@click.command("build")
@click.argument(
    "artifact_ids",
    nargs=-1,
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Display build plans without performing any work.",
)
def cli(
    artifact_ids: tuple[str, ...],
    dry_run: bool,
) -> None:
    """
    Build configured artifacts.

    Positional arguments are artifact IDs.
    """

    if not artifact_ids:
        raise click.UsageError("At least one artifact ID is required.")

    project_root = Path.cwd()

    for artifact_id in artifact_ids:
        try:
            plans = create_build_plans(
                artifact_id,
                project_root=project_root,
            )

            if dry_run:
                for plan in plans:
                    display_build_plan(plan)

                continue

            execute_builds(
                plans,
            )

        except (
            BuildPlanError,
            BuildError,
        ) as exc:
            raise click.ClickException(str(exc)) from exc


if __name__ == "__main__":
    cli()
