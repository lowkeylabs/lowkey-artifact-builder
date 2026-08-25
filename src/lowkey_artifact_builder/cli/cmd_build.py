"""
Build command.

Builds configured artifacts from their declared model workflows or
executes one explicitly requested artifact stage independently.
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
    execute_artifact_stage,
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
    "--stage",
    "stage_name",
    metavar="STAGE",
    help="Execute exactly one stage independently.",
)
@click.option(
    "--realization",
    metavar="REALIZATION",
    help="Select the realization for independent stage execution.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Display build plans without performing any work.",
)
def cli(
    artifact_ids: tuple[str, ...],
    stage_name: str | None,
    realization: str | None,
    dry_run: bool,
) -> None:
    """
    Build configured artifacts.

    Positional arguments are artifact IDs.

    When --stage is supplied, exactly one stage of exactly one artifact
    is executed independently. Required stage inputs must already exist.
    """

    if not artifact_ids:
        raise click.UsageError("At least one artifact ID is required.")

    if stage_name is not None:
        _execute_stage(
            artifact_ids,
            stage_name=stage_name,
            realization=realization,
            dry_run=dry_run,
            project_root=Path.cwd(),
        )

        return

    if realization is not None:
        raise click.UsageError("--realization requires --stage.")

    _execute_builds(
        artifact_ids,
        dry_run=dry_run,
        project_root=Path.cwd(),
    )


# =========================================================
# Independent stage execution
# =========================================================


def _execute_stage(
    artifact_ids: tuple[str, ...],
    *,
    stage_name: str,
    realization: str | None,
    dry_run: bool,
    project_root: Path,
) -> None:
    """
    Execute one explicitly requested artifact stage.
    """

    if len(artifact_ids) != 1:
        raise click.UsageError("Explicit stage execution requires a single artifact.")

    if dry_run:
        raise click.UsageError("--dry-run cannot be used with --stage.")

    try:
        execute_artifact_stage(
            artifact_ids[0],
            stage_name=stage_name,
            realization=realization,
            project_root=project_root,
        )

    except BuildError as exc:
        raise click.ClickException(str(exc)) from exc


# =========================================================
# Graph-driven build execution
# =========================================================


def _execute_builds(
    artifact_ids: tuple[str, ...],
    *,
    dry_run: bool,
    project_root: Path,
) -> None:
    """
    Execute normal graph-driven artifact builds.
    """

    for artifact_id in artifact_ids:
        try:
            plans = create_build_plans(
                artifact_id,
                project_root=project_root,
            )

            if dry_run:
                for plan in plans:
                    display_build_plan(
                        plan,
                    )

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
