"""
Artifact build execution.

This module executes concrete artifact build plans.

Build planning is performed separately by the planning subsystem.
Execution consumes an already-resolved BuildPlan and performs the
declared workflow stages.

The build engine owns the artifact workspace, external input
materialization, and stage execution environment. Model-specific stage
implementations receive a StageContext containing the artifact-specific
configuration Resolver, artifact-owned filesystem inputs, dependency
products, declared outputs, and filesystem locations required by the
stage.

The Resolver retained by BuildPlan is the single runtime authority for
artifact configuration. The same Resolver instance is supplied to every
StageContext in the build.

The engine does not interpret model-specific parameters, resolve
configuration, resolve external input paths, or interpret product
contents.
"""
# File: src/lowkey_artifact_builder/engine/build.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import shutil
from collections.abc import Iterable, Mapping
from pathlib import Path

from .context import (
    _create_resolved_stage_context,
)
from .operation import (
    execute_artifact_stage as _execute_artifact_stage,
)
from .specs import (
    BuildPlan,
    PlannedInput,
    PlannedStage,
    StageContext,
    StageContextError,
)
from .stage import (
    StageExecutionError,
    execute_stage,
)

# =========================================================
# Errors
# =========================================================


class BuildError(RuntimeError):
    """
    Raised when an artifact build cannot be completed.
    """


# =========================================================
# Public interface
# =========================================================


def execute_build(
    plan: BuildPlan,
) -> None:
    """
    Execute an artifact build plan.

    The complete declared artifact workspace is created before any
    stage executes.

    External filesystem inputs are then materialized into their
    artifact-owned locations.

    Stages execute in planned order. Before each stage executes, the
    engine constructs its StageContext using the same artifact-specific
    Resolver retained by BuildPlan.

    Stage implementation dispatch, working-directory management,
    implementation execution, and declared-product verification are
    delegated to the common independent stage execution boundary.

    Failure to prepare the workspace, materialize an input, construct
    an execution context, execute a stage, or produce its declared
    products stops the build immediately.
    """

    _prepare_workspace(plan)

    _materialize_inputs(plan)

    for stage in plan.stages:
        context = _create_stage_context(
            plan,
            stage,
        )

        try:
            execute_stage(
                context,
            )

        except StageExecutionError as exc:
            raise BuildError(str(exc)) from exc


def execute_builds(
    plans: Iterable[BuildPlan],
) -> None:
    """
    Execute multiple build plans in iteration order.

    Each plan is executed through the existing single-build execution
    boundary. Execution stops immediately if any build fails.
    """

    for plan in plans:
        execute_build(plan)


def execute_artifact_stage(
    artifact_id: str,
    *,
    stage_name: str,
    realization: str | None = None,
    project_root: Path | None = None,
    input_paths: Mapping[str, Path] | None = None,
) -> None:
    """
    Execute exactly one configured artifact stage independently.

    Independent stage execution resolves the requested StageContext,
    including any explicit physical bindings for declared filesystem
    inputs, validates that all resolved inputs already exist, and
    executes exactly the requested stage.

    Explicit input bindings may replace only inputs declared by the
    resolved stage context. They do not introduce new semantic inputs.

    Missing dependency products are not realized automatically and
    prerequisite stages are not executed.

    Stage resolution, readiness, and execution failures are translated
    to the common BuildError boundary exposed to build-command callers.
    """

    try:
        _execute_artifact_stage(
            artifact_id,
            stage_name=stage_name,
            realization=realization,
            project_root=project_root,
            input_paths=input_paths,
        )

    except (
        StageContextError,
        StageExecutionError,
    ) as exc:
        raise BuildError(str(exc)) from exc


# =========================================================
# Workspace preparation
# =========================================================


def _prepare_workspace(
    plan: BuildPlan,
) -> None:
    """
    Create the complete declared artifact workspace.

    The artifact directory, parent directories of all materialized
    external inputs, and parent directories of every declared stage
    product are created before stage execution begins.

    Model-specific stages may create additional private temporary or
    diagnostic directories when needed, but declared artifact
    filesystem structure is owned by the engine.
    """

    directories = {
        plan.artifact_dir,
    }

    for stage in plan.stages:
        for planned_input in stage.inputs:
            directories.add(planned_input.path.parent)

        for product in stage.products:
            directories.add(product.path.parent)

    try:
        for directory in sorted(
            directories,
            key=_directory_sort_key,
        ):
            directory.mkdir(
                parents=True,
                exist_ok=True,
            )

    except OSError as exc:
        raise BuildError(
            f"Cannot prepare workspace for artifact {plan.artifact_id!r}: {exc}"
        ) from exc


def _directory_sort_key(
    path: Path,
) -> tuple[int, str]:
    """
    Return a deterministic ordering key for workspace directories.

    Parent directories sort before deeper descendants.
    """

    return (
        len(path.parts),
        str(path),
    )


# =========================================================
# Input materialization
# =========================================================


def _materialize_inputs(
    plan: BuildPlan,
) -> None:
    """
    Materialize all external inputs into the artifact workspace.

    A configured external resource may be consumed by more than one
    stage. Each unique source/materialization pair is copied only once
    during a build.

    Input materialization occurs before any stage executes so every
    StageContext refers only to artifact-owned resources.

    The external source must exist and must be a regular file.
    """

    materialized: set[
        tuple[
            Path,
            Path,
        ]
    ] = set()

    destinations: dict[
        Path,
        Path,
    ] = {}

    for stage in plan.stages:
        for planned_input in stage.inputs:
            key = (
                planned_input.source_path,
                planned_input.path,
            )

            if key in materialized:
                continue

            _validate_input_destination(
                plan,
                stage,
                planned_input,
                destinations,
            )

            _materialize_input(
                plan,
                stage,
                planned_input,
            )

            destinations[planned_input.path] = planned_input.source_path

            materialized.add(key)


def _validate_input_destination(
    plan: BuildPlan,
    stage: PlannedStage,
    planned_input: PlannedInput,
    destinations: dict[Path, Path],
) -> None:
    """
    Ensure one artifact-local input path does not represent two sources.

    Multiple stages may consume the same materialized input, but two
    different external resources may not be materialized to the same
    artifact-local path during one build.
    """

    previous_source = destinations.get(planned_input.path)

    if previous_source is None:
        return

    if previous_source == planned_input.source_path:
        return

    raise BuildError(
        f"Cannot materialize input "
        f"{planned_input.name!r} "
        f"for stage {stage.name!r} "
        f"of artifact {plan.artifact_id!r}: "
        f"artifact path {planned_input.path} "
        f"is already assigned to external "
        f"source {previous_source}."
    )


def _materialize_input(
    plan: BuildPlan,
    stage: PlannedStage,
    planned_input: PlannedInput,
) -> None:
    """
    Materialize one external filesystem input.

    The original external resource is copied to its planned
    artifact-owned location. Metadata is preserved where supported by
    the filesystem.

    Model-specific stage implementations never receive source_path.
    """

    source = planned_input.source_path
    destination = planned_input.path

    if not source.exists():
        raise BuildError(
            f"Cannot materialize input "
            f"{planned_input.name!r} "
            f"for stage {stage.name!r} "
            f"of artifact {plan.artifact_id!r}: "
            f"external source {source} "
            "does not exist."
        )

    if not source.is_file():
        raise BuildError(
            f"Cannot materialize input "
            f"{planned_input.name!r} "
            f"for stage {stage.name!r} "
            f"of artifact {plan.artifact_id!r}: "
            f"external source {source} "
            "is not a regular file."
        )

    try:
        destination.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        if source.resolve() == destination.resolve():
            return

        shutil.copy2(
            source,
            destination,
        )

    except OSError as exc:
        raise BuildError(
            f"Cannot materialize input "
            f"{planned_input.name!r} "
            f"for stage {stage.name!r} "
            f"of artifact {plan.artifact_id!r} "
            f"from {source} to {destination}: "
            f"{exc}"
        ) from exc


# =========================================================
# Stage context construction
# =========================================================


def _create_stage_context(
    plan: BuildPlan,
    stage: PlannedStage,
) -> StageContext:
    """
    Construct the execution context for one planned stage.

    The artifact-specific Resolver retained by BuildPlan is supplied
    directly to StageContext.

    Graph-driven execution resolves its inputs and outputs from the
    already-resolved BuildPlan, then delegates final StageContext
    construction and working-directory semantics to the common context
    construction boundary shared with independent stage execution.
    """

    inputs = _collect_stage_inputs(
        plan,
        stage,
    )

    outputs = {product.name: product.path for product in stage.products}

    return _create_resolved_stage_context(
        artifact_id=plan.artifact_id,
        model_name=plan.model_name,
        stage_name=stage.name,
        project_root=plan.project_root,
        artifact_dir=plan.artifact_dir,
        resolver=plan.resolver,
        inputs=inputs,
        outputs=outputs,
    )


def _collect_stage_inputs(
    plan: BuildPlan,
    stage: PlannedStage,
) -> dict[str, Path]:
    """
    Collect all filesystem inputs available to a stage.

    Explicit stage inputs are exposed using their declarative names:

        source

    Products from direct dependencies are exposed using qualified names:

        prepare.trace
        raster.manifest

    Input names must be unique. A collision between an explicit input
    and a dependency product is treated as an invalid execution
    context rather than silently replacing either resource.
    """

    inputs: dict[
        str,
        Path,
    ] = {}

    _add_explicit_inputs(
        plan,
        stage,
        inputs,
    )

    _add_dependency_inputs(
        plan,
        stage,
        inputs,
    )

    return inputs


def _add_explicit_inputs(
    plan: BuildPlan,
    stage: PlannedStage,
    inputs: dict[str, Path],
) -> None:
    """
    Add the stage's explicitly declared filesystem inputs.

    Planned inputs contain both the original external source and its
    artifact-owned materialized location. Only the artifact-owned path
    is exposed to the stage.
    """

    for planned_input in stage.inputs:
        _add_stage_input(
            plan,
            stage,
            inputs,
            planned_input.name,
            planned_input.path,
        )


def _add_dependency_inputs(
    plan: BuildPlan,
    stage: PlannedStage,
    inputs: dict[str, Path],
) -> None:
    """
    Add products supplied by the stage's direct dependencies.
    """

    planned_stages = {planned_stage.name: planned_stage for planned_stage in plan.stages}

    for dependency_name in stage.dependencies:
        try:
            dependency = planned_stages[dependency_name]

        except KeyError as exc:
            raise BuildError(
                f"Cannot execute stage "
                f"{stage.name!r} "
                f"for artifact "
                f"{plan.artifact_id!r}: "
                f"dependency "
                f"{dependency_name!r} "
                "is not present in the "
                "build plan."
            ) from exc

        for product in dependency.products:
            name = f"{dependency.name}.{product.name}"

            _add_stage_input(
                plan,
                stage,
                inputs,
                name,
                product.path,
            )


def _add_stage_input(
    plan: BuildPlan,
    stage: PlannedStage,
    inputs: dict[str, Path],
    name: str,
    path: Path,
) -> None:
    """
    Add one filesystem input to a stage execution context.

    Duplicate execution-facing input names are rejected.
    """

    if name in inputs:
        raise BuildError(
            f"Cannot execute stage "
            f"{stage.name!r} "
            f"for artifact "
            f"{plan.artifact_id!r}: "
            f"duplicate input name "
            f"{name!r}."
        )

    inputs[name] = path


__all__ = [
    "BuildError",
    "execute_build",
    "execute_builds",
    "execute_artifact_stage",
]
