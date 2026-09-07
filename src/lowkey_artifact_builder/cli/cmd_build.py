"""
Build command.

Builds explicitly selected artifact Variants from their declared model
workflows. An unqualified build request discovers and displays the
Variants available to the Artifact without requesting execution.

A configured artifact may also execute exactly one declared stage
independently, with optional explicit input, parameter, and output
bindings.
"""

# File: src/lowkey_artifact_builder/cli/cmd_build.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path

import click

from lowkey_artifact_builder.cli.bindings import (
    BindingError,
    parse_parameter_bindings,
    parse_path_bindings,
)
from lowkey_artifact_builder.cli.display import (
    display_available_variants,
    display_build_plan,
)
from lowkey_artifact_builder.cli.variants import (
    parse_variant_reference,
)
from lowkey_artifact_builder.config import ConfigError
from lowkey_artifact_builder.engine import (
    BuildError,
    BuildPlanError,
    ExecutionEvent,
    create_artifact_build_plans,
    execute_artifact_build,
    execute_artifact_stage,
    prepare_incremental_build,
)
from lowkey_artifact_builder.model import (
    build_model_registry,
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
    type=str,
    default=None,
    help="Execute exactly one declared stage independently.",
)
@click.option(
    "--realization",
    type=str,
    default=None,
    help="Select one artifact realization for independent stage execution.",
)
@click.option(
    "--variant",
    type=str,
    default=None,
    help="Select one artifact Variant.",
)
@click.option(
    "--all-variants",
    is_flag=True,
    help="Select all applicable artifact Variants.",
)
@click.option(
    "--input",
    "input_bindings",
    metavar="NAME=PATH",
    multiple=True,
    help="Bind a declared stage input to a filesystem path.",
)
@click.option(
    "--parameter",
    "parameter_bindings",
    metavar="NAME=VALUE",
    multiple=True,
    help="Bind a declared stage parameter to an explicit value.",
)
@click.option(
    "--output",
    "output_bindings",
    metavar="NAME=PATH",
    multiple=True,
    help="Bind a declared stage output to a filesystem path.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Display build plans without performing any work.",
)
def cli(
    artifact_ids: tuple[str, ...],
    stage: str | None,
    realization: str | None,
    variant: str | None,
    all_variants: bool,
    input_bindings: tuple[str, ...],
    parameter_bindings: tuple[str, ...],
    output_bindings: tuple[str, ...],
    dry_run: bool,
) -> None:
    """
    Build configured artifacts.

    Positional arguments are artifact IDs.

    Without --stage, --variant selects one Variant for incremental
    execution and --all-variants selects all applicable Variants.
    When neither selection is supplied, the command displays the
    available Variants without requesting execution.

    With --stage, exactly one declared stage is executed independently.
    An optional --realization selects the Artifact Realization for that
    stage. Explicit input, parameter, and output bindings apply only to
    this independent stage execution mode.
    """

    if not artifact_ids:
        raise click.UsageError("At least one artifact ID is required.")

    if stage is not None:
        _execute_stage(
            artifact_ids,
            stage_name=stage,
            realization=realization,
            input_bindings=input_bindings,
            parameter_bindings=parameter_bindings,
            output_bindings=output_bindings,
            dry_run=dry_run,
        )
        return

    if realization is not None:
        raise click.UsageError("--realization requires --stage.")

    if input_bindings:
        raise click.UsageError("--input requires --stage.")

    if parameter_bindings:
        raise click.UsageError("--parameter requires --stage.")

    if output_bindings:
        raise click.UsageError("--output requires --stage.")

    if variant is not None and all_variants:
        raise click.UsageError("--variant and --all-variants cannot be used together.")

    if variant is None and not all_variants:
        _display_available_variants(
            artifact_ids,
        )
        return

    model_name: str | None = None
    variant_name: str | None = None

    if variant is not None:
        model_name, variant_name = parse_variant_reference(
            variant,
        )

    _execute_build(
        artifact_ids,
        model_name=model_name,
        variant_name=variant_name,
        all_variants=all_variants,
        dry_run=dry_run,
    )


# =========================================================
# Variant discovery
# =========================================================


def get_available_variant_names(
    artifact_id: str,
    *,
    project_root: Path,
) -> tuple[str, ...]:
    """
    Return the qualified Model Variants available to an Artifact.

    Variant availability is Model-owned. Artifact configuration need
    not enumerate the registered Variant catalog merely to make those
    Variants discoverable.

    The Artifact and project-root arguments establish an Artifact-level
    discovery boundary even though the current Variant catalog is
    entirely Model-owned.
    """

    del artifact_id
    del project_root

    registry = build_model_registry()

    return tuple(
        f"{model.name}.{variant.name}"
        for model in registry.all_models()
        for variant in model.variants
    )


def _display_available_variants(
    artifact_ids: tuple[str, ...],
) -> None:
    """
    Discover and display available Variants without requesting execution.
    """

    project_root = Path.cwd()

    for artifact_id in artifact_ids:
        try:
            variants = get_available_variant_names(
                artifact_id,
                project_root=project_root,
            )

            display_available_variants(
                artifact_id,
                variants,
            )

        except ConfigError as exc:
            raise click.ClickException(str(exc)) from exc


# =========================================================
# Build observation
# =========================================================


def _display_execution_event(
    event: ExecutionEvent,
) -> None:
    """
    Present one semantic incremental execution event.

    Build events identify the realized artifact build. Stage events
    identify whether a stage is executing, completed successfully,
    reused from persistent state, or failed.
    """

    if event.kind == "build.started":
        click.echo(f"Building {event.artifact_id} ({event.model_name}/{event.realization})")
        return

    if event.kind == "build.completed":
        click.echo(f"Build completed: {event.artifact_id}")
        return

    if event.kind == "build.failed":
        click.echo(f"Build failed: {event.artifact_id}")
        return

    if event.kind == "stage.started":
        click.echo(f"Stage started: {event.stage_name}")
        return

    if event.kind == "stage.completed":
        click.echo(f"Stage completed: {event.stage_name}")
        return

    if event.kind == "stage.skipped":
        click.echo(f"Stage skipped: {event.stage_name}")
        return

    if event.kind == "stage.failed":
        click.echo(f"Stage failed: {event.stage_name}")


# =========================================================
# Graph-driven build
# =========================================================


def _execute_build(
    artifact_ids: tuple[str, ...],
    *,
    model_name: str | None,
    variant_name: str | None,
    all_variants: bool,
    dry_run: bool,
) -> None:
    """
    Execute explicitly selected graph-driven artifact builds.

    Normal execution delegates artifact orchestration to the engine.
    Model and Variant selection are normal-build selection coordinates.

    This boundary is entered only after execution has been explicitly
    requested through one-Variant or all-Variant selection. Unqualified
    Artifact build requests are handled as discovery before reaching
    this boundary.

    Artifact Realization selection is reserved for independent Stage
    execution and is not a normal-build selection coordinate.

    All-Variant selection is accepted at this command boundary. Variant
    enumeration is delegated to engine planning rather than represented
    as an Artifact Realization.

    Dry-run uses the same artifact-level plan selection as normal execution,
    prepares each selected BuildPlan's persistent-state-aware ExecutionPlan,
    and validates the configuration required by that execution scope before
    displaying the BuildPlan. No stages are executed during dry-run.
    """

    project_root = Path.cwd()

    for artifact_id in artifact_ids:
        try:
            planning_options = {}

            if model_name is not None:
                planning_options["model_name"] = model_name

            if variant_name is not None:
                planning_options["variant_name"] = variant_name

            if dry_run:
                dry_run_options = dict(
                    planning_options,
                )

                if all_variants:
                    dry_run_options["all_variants"] = True

                plans = create_artifact_build_plans(
                    artifact_id,
                    project_root=project_root,
                    **dry_run_options,
                )

                for plan in plans:
                    prepare_incremental_build(
                        plan,
                    )

                    display_build_plan(
                        plan,
                    )

                continue

            execution_options = dict(
                planning_options,
            )

            if all_variants:
                execution_options["all_variants"] = True

            execute_artifact_build(
                artifact_id,
                project_root=project_root,
                event_sink=_display_execution_event,
                **execution_options,
            )

        except (
            ConfigError,
            BuildPlanError,
            BuildError,
        ) as exc:
            raise click.ClickException(str(exc)) from exc


# =========================================================
# Independent stage execution
# =========================================================


def _execute_stage(
    artifact_ids: tuple[str, ...],
    *,
    stage_name: str,
    realization: str | None,
    input_bindings: tuple[str, ...],
    parameter_bindings: tuple[str, ...],
    output_bindings: tuple[str, ...],
    dry_run: bool,
) -> None:
    """
    Execute exactly one declared artifact stage independently.

    Command-line bindings are translated into the typed mappings
    consumed by the engine. Stage-specific semantic validation remains
    the responsibility of the engine.
    """

    if len(artifact_ids) != 1:
        raise click.UsageError("Independent stage execution requires a single artifact.")

    if dry_run:
        raise click.UsageError("--dry-run is not supported with --stage.")

    artifact_id = artifact_ids[0]
    project_root = Path.cwd()

    try:
        input_paths = parse_path_bindings(
            input_bindings,
            project_root=project_root,
        )

        parameter_values = parse_parameter_bindings(
            parameter_bindings,
        )

        output_paths = parse_path_bindings(
            output_bindings,
            project_root=project_root,
        )

        execute_artifact_stage(
            artifact_id,
            stage_name=stage_name,
            realization=realization,
            project_root=project_root,
            input_paths=input_paths or None,
            parameter_values=parameter_values or None,
            output_paths=output_paths or None,
        )

    except (
        BindingError,
        BuildError,
    ) as exc:
        raise click.ClickException(str(exc)) from exc


if __name__ == "__main__":
    cli()
