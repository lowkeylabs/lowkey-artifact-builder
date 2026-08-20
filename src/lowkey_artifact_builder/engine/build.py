"""
Artifact build execution.

This module executes concrete artifact build plans.

Build planning is performed separately by the planning subsystem.
Execution consumes an already-resolved BuildPlan and performs the
declared workflow stages.

The build engine owns the artifact workspace and stage execution
environment. Model-specific stage implementations receive a
StageContext containing the resolved parameters, dependency products,
declared outputs, and filesystem locations required by the stage.

The engine does not interpret model-specific parameters or product
contents.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path

from .specs import (
    BuildPlan,
    PlannedStage,
    StageContext,
)

# =========================================================
# Types
# =========================================================


StageImplementation = Callable[
    [StageContext],
    None,
]


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

    Stages execute in planned order. Before each stage executes, the
    engine constructs its StageContext and changes the process working
    directory to the stage working directory.

    The previous working directory is restored after stage execution,
    including when execution fails.

    After a stage completes, all of its declared products must exist.
    Failure to execute a stage or produce its declared products stops
    the build immediately.
    """

    _prepare_workspace(plan)

    for stage in plan.stages:
        context = _create_stage_context(
            plan,
            stage,
        )

        _execute_stage(context)

        _verify_products(context)


# =========================================================
# Workspace preparation
# =========================================================


def _prepare_workspace(
    plan: BuildPlan,
) -> None:
    """
    Create the complete declared artifact workspace.

    The artifact directory and the parent directories of every declared
    stage product are created before stage execution begins.

    Model-specific stages may create additional private temporary or
    diagnostic directories when needed, but declared product directory
    structure is owned by the engine.
    """

    directories = {
        plan.artifact_dir,
    }

    for stage in plan.stages:
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
# Stage context construction
# =========================================================


def _create_stage_context(
    plan: BuildPlan,
    stage: PlannedStage,
) -> StageContext:
    """
    Construct the execution context for one planned stage.

    Parameters are exposed by their resolved parameter names.

    Inputs contain every declared product of every direct dependency.
    Input names are qualified by dependency stage name, for example:

        prepare.trace
        raster.manifest

    Outputs contain the current stage's declared products keyed by their
    declarative product names.
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
    Collect declared products from the stage's direct dependencies.

    Dependency products are exposed using qualified names of the form:

        <stage>.<product>
    """

    planned_stages = {planned_stage.name: planned_stage for planned_stage in plan.stages}

    inputs: dict[
        str,
        Path,
    ] = {}

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

            if name in inputs:
                raise BuildError(
                    f"Cannot execute stage {stage.name!r} "
                    f"for artifact {plan.artifact_id!r}: "
                    f"duplicate input name {name!r}."
                )

            inputs[name] = product.path

    return inputs


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
) -> None:
    """
    Execute one model-specific stage.

    Model implementation lookup is isolated from the generic execution
    loop so the dispatch mechanism may evolve independently of build
    execution.
    """

    implementation = _get_stage_implementation(
        context.model_name,
        context.stage_name,
    )

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


def _get_stage_implementation(
    model_name: str,
    stage_name: str,
) -> StageImplementation:
    """
    Return the implementation for a model stage.

    Model-specific stage registration has not yet been introduced.

    This function intentionally isolates implementation lookup from the
    generic execution machinery. The first artwork stage implementation
    will establish the concrete registration or dispatch mechanism.
    """

    raise BuildError(
        f"No implementation is registered for model {model_name!r}, stage {stage_name!r}."
    )


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

    missing = [(name, path) for name, path in context.outputs.items() if not path.exists()]

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
