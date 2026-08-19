"""
Build command.

Builds configured artifacts from their declared model workflows.

The build command resolves artifact configuration, constructs the
artifact's execution plan, and either displays that plan or executes
it.
"""

from __future__ import annotations

from pathlib import Path

import click

from lowkey_artifact_builder.build import (
    create_build_plan,
    execute_build,
)
from lowkey_artifact_builder.cli.display import (
    display_build_plan,
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
    help="Display the build plan without performing any work.",
)
def cli(
    artifact_ids: tuple[str, ...],
    dry_run: bool,
) -> None:
    """
    Build configured artifacts.

    Positional arguments are artifact IDs.
    """

    # =====================================================
    # Argument validation
    # =====================================================

    if not artifact_ids:
        raise click.UsageError("At least one artifact ID is required.")

    project_root = Path.cwd()

    # =====================================================
    # Artifact builds
    # =====================================================

    for index, artifact_id in enumerate(artifact_ids):
        if index:
            click.echo()

        plan = create_build_plan(
            artifact_id,
            project_root=project_root,
        )

        # -------------------------------------------------
        # Dry run
        # -------------------------------------------------

        if dry_run:
            display_build_plan(
                plan,
            )

            continue

        # -------------------------------------------------
        # Build
        # -------------------------------------------------

        execute_build(
            plan,
        )


if __name__ == "__main__":
    cli()
