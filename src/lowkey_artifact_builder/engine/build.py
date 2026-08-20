"""
Artifact build execution.

This module executes concrete artifact build plans.

Build planning is performed separately by the planning subsystem.
Execution consumes an already-resolved BuildPlan and performs the
declared workflow stages.

The build engine owns the artifact workspace, external input
materialization, and stage execution environment. Model-specific stage
implementations receive a StageContext containing resolved parameters,
artifact-owned filesystem inputs, dependency products, declared
outputs, and filesystem locations required by the stage.

The engine does not interpret model-specific parameters, resolve
configuration, resolve external input paths, or interpret product
contents.
"""

from __future__ import annotations

import os
import shutil
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from .bootstrap import build_stage_registry
from .registry import (
    StageImplementationNotFoundError,
    StageRegistry,
)
from .specs import (
    BuildPlan,
    PlannedInput,
    PlannedStage,
    StageContext,
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

    A stage implementation registry is constructed once for the build.

    Stages execute in planned order. Before each stage executes, the
    engine constructs its StageContext and changes the process working
    directory to the stage working directory.

    The previous working directory is restored after stage execution,
    including when execution fails.

    After a stage completes, all of its declared products must exist.
    Failure to prepare the workspace, materialize an input, locate an
    implementation, execute a stage, or produce its declared products
    stops the build immediately.
    """

    registry = build_stage_registry()

    _prepare_workspace(plan)

    _materialize_inputs(plan)

    for stage in plan.stages:
        context = _create_stage_context(
            plan,
            stage,
        )

        _execute_stage(
            context,
            registry,
        )

        _verify_products(context)


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

    materialized: set[tuple[Path, Path]] = set()

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
        f"Cannot materialize input {planned_input.name!r} "
        f"for stage {stage.name!r} of artifact "
        f"{plan.artifact_id!r}: artifact path "
        f"{planned_input.path} is already assigned to "
        f"external source {previous_source}."
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
            f"Cannot materialize input {planned_input.name!r} "
            f"for stage {stage.name!r} of artifact "
            f"{plan.artifact_id!r}: external source "
            f"{source} does not exist."
        )

    if not source.is_file():
        raise BuildError(
            f"Cannot materialize input {planned_input.name!r} "
            f"for stage {stage.name!r} of artifact "
            f"{plan.artifact_id!r}: external source "
            f"{source} is not a regular file."
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
            f"Cannot materialize input {planned_input.name!r} "
            f"for stage {stage.name!r} of artifact "
            f"{plan.artifact_id!r} from {source} "
            f"to {destination}: {exc}"
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

    Parameters are exposed by their resolved parameter names.

    Inputs contain both:

        explicitly declared filesystem inputs
            These use their declarative input names and refer to
            artifact-owned materialized resources.

        products from direct dependency stages
            These use qualified names of the form
            '<stage>.<product>'.

    Outputs contain the current stage's declared products keyed by their
    declarative product names.

    Model-specific implementations do not resolve project or artifact
    filesystem layout themselves.
    """

    parameters = {parameter.name: parameter.value for parameter in stage.parameters}

    inputs = _collect_stage_inputs(
        plan,
        stage,
    )

    outputs = {product.name: product.path for product in stage.products}

    working_dir = _stage_working_directory(
        plan,
        stage,
    )

    return StageContext(
        artifact_id=plan.artifact_id,
        model_name=plan.model_name,
        stage_name=stage.name,
        project_root=plan.project_root,
        artifact_dir=plan.artifact_dir,
        working_dir=working_dir,
        parameters=parameters,
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
                f"Cannot execute stage {stage.name!r} "
                f"for artifact {plan.artifact_id!r}: "
                f"dependency {dependency_name!r} "
                "is not present in the build plan."
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
            f"Cannot execute stage {stage.name!r} "
            f"for artifact {plan.artifact_id!r}: "
            f"duplicate input name {name!r}."
        )

    inputs[name] = path


# =========================================================
# Stage working directories
# =========================================================


def _stage_working_directory(
    plan: BuildPlan,
    stage: PlannedStage,
) -> Path:
    """
    Determine the working directory for a stage.

    A stage with declared products executes from the common parent
    directory containing those products.

    A stage without declared products executes from the artifact
    working directory.

    Working-directory selection is an engine concern. Stage
    implementations should not change directories themselves.
    """

    if not stage.products:
        return plan.artifact_dir

    parents = [product.path.parent for product in stage.products]

    common = Path(os.path.commonpath(parents))

    return common


@contextmanager
def _working_directory(
    path: Path,
) -> Iterator[None]:
    """
    Temporarily change the process working directory.

    The previous working directory is restored regardless of whether
    stage execution succeeds or raises an exception.
    """

    previous = Path.cwd()

    try:
        os.chdir(path)

        yield

    finally:
        os.chdir(previous)


# =========================================================
# Stage execution
# =========================================================


def _execute_stage(
    context: StageContext,
    registry: StageRegistry,
) -> None:
    """
    Execute one model-specific stage.

    The executable implementation is obtained from the completed stage
    registry using the model and stage names carried by StageContext.

    The generic build engine does not know which models, features, or
    plugins supplied the implementation.
    """

    try:
        implementation = registry.get(
            context.model_name,
            context.stage_name,
        )

    except StageImplementationNotFoundError as exc:
        raise BuildError(
            f"No implementation is registered for "
            f"model {context.model_name!r}, "
            f"stage {context.stage_name!r}."
        ) from exc

    try:
        with _working_directory(context.working_dir):
            implementation(context)

    except BuildError:
        raise

    except Exception as exc:
        raise BuildError(
            f"Stage {context.stage_name!r} failed "
            f"for artifact {context.artifact_id!r} "
            f"using model {context.model_name!r}: "
            f"{exc}"
        ) from exc


# =========================================================
# Product verification
# =========================================================


def _verify_products(
    context: StageContext,
) -> None:
    """
    Verify that every declared stage product exists.

    Product contents and semantics are model-specific and are not
    interpreted by the generic build engine.
    """

    missing = [
        (
            name,
            path,
        )
        for name, path in context.outputs.items()
        if not path.exists()
    ]

    if not missing:
        return

    details = ", ".join(f"{name!r} ({path})" for name, path in missing)

    raise BuildError(
        f"Stage {context.stage_name!r} "
        f"for artifact {context.artifact_id!r} "
        f"did not produce declared product"
        f"{'s' if len(missing) != 1 else ''}: "
        f"{details}."
    )


__all__ = [
    "BuildError",
    "execute_build",
]
