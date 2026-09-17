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
    display_build_plan,
)
from lowkey_artifact_builder.config import (
    ConfigError,
    get_realization_names,
    list_artifacts,
)
from lowkey_artifact_builder.engine import (
    BuildError,
    BuildPlanError,
    ExecutionEvent,
    ExecutionPlan,
    ProductState,
    create_artifact_build_plans,
    execute_artifact_build,
    execute_artifact_stage,
    prepare_incremental_build,
    rebuild_artifact,
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
@click.option(
    "--build-all",
    is_flag=True,
    help="Incrementally build every effective Realization of every project Artifact.",
)
@click.option(
    "--rebuild",
    is_flag=True,
    help="Clean and rebuild the selected Artifact Realization.",
)
@click.option(
    "--rebuild-all",
    is_flag=True,
    help="Clean and rebuild every effective Realization of every project Artifact.",
)
def cli(
    artifact_ids: tuple[str, ...],
    stage: str | None,
    realization: str | None,
    input_bindings: tuple[str, ...],
    parameter_bindings: tuple[str, ...],
    output_bindings: tuple[str, ...],
    dry_run: bool,
    build_all: bool,
    rebuild: bool,
    rebuild_all: bool,
) -> None:
    """
    Build configured artifacts.

    Bare ``artifact build`` is a read-only project-status operation.

    Positional arguments are artifact IDs.

    Without --stage, --variant selects one Variant for incremental
    execution and --all-variants selects all applicable Variants.
    When neither selection is supplied for explicitly named Artifacts,
    the command displays the available Variants without requesting
    execution.

    With --stage, exactly one declared stage is executed independently.
    An optional --realization selects the Artifact Realization for that
    stage. Explicit input, parameter, and output bindings apply only to
    this independent stage execution mode.
    """

    if build_all and rebuild_all:
        raise click.UsageError("--build-all and --rebuild-all cannot be used together.")

    if build_all and artifact_ids:
        raise click.UsageError("--build-all cannot be combined with Artifact IDs.")

    if build_all and realization is not None:
        raise click.UsageError("--build-all cannot be combined with --realization.")

    if rebuild_all and artifact_ids:
        raise click.UsageError("--rebuild-all cannot be combined with Artifact IDs.")

    if rebuild_all and realization is not None:
        raise click.UsageError("--rebuild-all cannot be combined with --realization.")

    if rebuild and not artifact_ids and realization is None:
        raise click.UsageError("--rebuild requires a narrowed build scope.")

    if not artifact_ids and realization is None and not build_all and not rebuild_all:
        _display_build_status()
        return

    if not artifact_ids:
        artifact_ids = list_artifacts(
            project_root=Path.cwd(),
        )

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

    if input_bindings:
        raise click.UsageError("--input requires --stage.")

    if parameter_bindings:
        raise click.UsageError("--parameter requires --stage.")

    if output_bindings:
        raise click.UsageError("--output requires --stage.")

    if build_all:
        _execute_realizations(
            artifact_ids,
            dry_run=dry_run,
        )
        return

    if rebuild_all:
        _rebuild_all(
            artifact_ids,
        )
        return

    if rebuild:
        if realization is not None:
            _rebuild_realization(
                artifact_ids,
                realization=realization,
            )
            return

        if len(artifact_ids) != 1:
            raise click.UsageError("--rebuild requires one Artifact when --realization is omitted.")

        _rebuild_realizations(
            artifact_ids[0],
        )
        return

    if realization is not None:
        _execute_realization(
            artifact_ids,
            realization=realization,
            dry_run=dry_run,
        )
        return

    _execute_realizations(
        artifact_ids,
        dry_run=dry_run,
    )


# =========================================================
# Variant discovery
# =========================================================


def _display_build_status() -> None:
    """
    Display read-only build status for the current project.

    Status is organized by persistent Artifact and effective Realization.
    Realization discovery is delegated to configuration so canonical and
    Artifact-declared Realizations follow the same semantics used by normal
    engine planning.

    Status is derived from the prepared ExecutionPlan rather than persisted
    separately. The earliest non-current persistent product state in build
    order describes the Realization; a Realization whose persistent products
    are all current is current.
    """

    project_root = Path.cwd()

    artifacts = list_artifacts(
        project_root=project_root,
    )

    for artifact_id in artifacts:
        try:
            realizations = get_realization_names(
                artifact_id,
                project_root=project_root,
            )

            for realization in realizations:
                plans = create_artifact_build_plans(
                    artifact_id,
                    realization=realization,
                    project_root=project_root,
                )

                for plan in plans:
                    execution_plan = prepare_incremental_build(
                        plan,
                    )

                    status = _execution_plan_status(
                        execution_plan,
                    )

                    click.echo(f"{artifact_id} {realization} {status.value}")

        except (
            ConfigError,
            BuildPlanError,
        ) as exc:
            raise click.ClickException(str(exc)) from exc


def _execution_plan_status(
    execution_plan: ExecutionPlan,
) -> ProductState:
    """
    Return the earliest non-current persistent product state in build order.

    Stages without persistent products contribute no state. If every
    persistent product is current, the Realization is current.
    """

    for stage in execution_plan.stages:
        for state in stage.product_states:
            if state is not ProductState.CURRENT:
                return state

    return ProductState.CURRENT


def _execute_realization(
    artifact_ids: tuple[str, ...],
    *,
    realization: str,
    dry_run: bool,
) -> None:
    """
    Build one selected Realization for the selected Artifacts.

    Independent Artifact builds continue after individual failures. After
    all requested Artifacts have been attempted, any failures are reported
    together as command failure.
    """

    project_root = Path.cwd()

    failures: list[str] = []

    for artifact_id in artifact_ids:
        try:
            if dry_run:
                plans = create_artifact_build_plans(
                    artifact_id,
                    realization=realization,
                    project_root=project_root,
                )

                for plan in plans:
                    prepare_incremental_build(
                        plan,
                    )
                    display_build_plan(
                        plan,
                    )

                continue

            execute_artifact_build(
                artifact_id,
                realization=realization,
                project_root=project_root,
                event_sink=_display_execution_event,
            )

        except (
            ConfigError,
            BuildPlanError,
            BuildError,
        ) as exc:
            failures.append(
                str(exc),
            )

    if failures:
        raise click.ClickException(
            "\n".join(
                failures,
            )
        )


def _rebuild_realization(
    artifact_ids: tuple[str, ...],
    *,
    realization: str,
) -> None:
    """
    Rebuild one selected Realization for the selected Artifacts.

    Independent Artifact rebuilds continue after individual failures.
    After all requested Artifacts have been attempted, any failures are
    reported together as command failure.
    """

    project_root = Path.cwd()

    failures: list[str] = []

    for artifact_id in artifact_ids:
        try:
            rebuild_artifact(
                artifact_id,
                realization=realization,
                project_root=project_root,
                event_sink=_display_execution_event,
            )

        except (
            ConfigError,
            BuildPlanError,
            BuildError,
        ) as exc:
            failures.append(
                str(exc),
            )

    if failures:
        raise click.ClickException(
            "\n".join(
                failures,
            )
        )


def _rebuild_realizations(
    artifact_id: str,
) -> None:
    """
    Rebuild every effective Realization of one Artifact.

    Independent Realization rebuilds continue after individual failures.
    After all requested Realizations have been attempted, any failures are
    reported together as command failure.
    """

    project_root = Path.cwd()

    try:
        realizations = get_realization_names(
            artifact_id,
            project_root=project_root,
        )
    except ConfigError as exc:
        raise click.ClickException(
            str(exc),
        ) from exc

    failures: list[str] = []

    for realization in realizations:
        try:
            rebuild_artifact(
                artifact_id,
                realization=realization,
                project_root=project_root,
                event_sink=_display_execution_event,
            )

        except (
            ConfigError,
            BuildPlanError,
            BuildError,
        ) as exc:
            failures.append(
                str(exc),
            )

    if failures:
        raise click.ClickException(
            "\n".join(
                failures,
            )
        )


def _execute_realizations(
    artifact_ids: tuple[str, ...],
    *,
    dry_run: bool,
) -> None:
    """
    Build every effective Realization for the selected Artifacts.

    Normal build execution addresses Artifact + Realization. Effective
    Realization discovery remains owned by configuration.

    Independent Realization builds continue after individual failures.
    After all requested independent builds have been attempted, any
    failures are reported together as command failure.
    """

    project_root = Path.cwd()

    failures: list[str] = []

    for artifact_id in artifact_ids:
        try:
            realizations = get_realization_names(
                artifact_id,
                project_root=project_root,
            )
        except ConfigError as exc:
            failures.append(
                str(exc),
            )
            continue

        for realization in realizations:
            try:
                if dry_run:
                    plans = create_artifact_build_plans(
                        artifact_id,
                        realization=realization,
                        project_root=project_root,
                    )

                    for plan in plans:
                        prepare_incremental_build(
                            plan,
                        )
                        display_build_plan(
                            plan,
                        )

                    continue

                execute_artifact_build(
                    artifact_id,
                    realization=realization,
                    project_root=project_root,
                    event_sink=_display_execution_event,
                )

            except (
                ConfigError,
                BuildPlanError,
                BuildError,
            ) as exc:
                failures.append(
                    str(exc),
                )

    if failures:
        raise click.ClickException(
            "\n".join(
                failures,
            )
        )


def _rebuild_all(
    artifact_ids: tuple[str, ...],
) -> None:
    """
    Rebuild every effective Realization of the selected Artifacts.
    """

    project_root = Path.cwd()

    try:
        for artifact_id in artifact_ids:
            realizations = get_realization_names(
                artifact_id,
                project_root=project_root,
            )

            for realization in realizations:
                rebuild_artifact(
                    artifact_id,
                    realization=realization,
                    project_root=project_root,
                    event_sink=_display_execution_event,
                )

    except (
        ConfigError,
        BuildPlanError,
        BuildError,
    ) as exc:
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
