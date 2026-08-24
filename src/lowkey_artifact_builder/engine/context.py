"""
Independent stage context construction.

This module resolves the execution context for one declared model stage
without constructing a BuildPlan or traversing stage dependencies.

Independent context construction uses the same artifact configuration,
model definitions, artifact-owned external input locations, canonical
product locations, and working-directory semantics as graph-driven
build execution.

Construction is side-effect free. It does not create directories,
materialize external inputs, validate prerequisite file existence, or
execute the requested stage or any dependency.
"""
# File: src/lowkey_artifact_builder/engine/context.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import os
from pathlib import Path

from lowkey_artifact_builder.config import (
    get_resolver,
)
from lowkey_artifact_builder.engine.product_resolver import (
    ProductResolver,
)
from lowkey_artifact_builder.engine.specs import (
    StageContext,
    StageContextError,
)
from lowkey_artifact_builder.model import (
    ModelNotFoundError,
    ModelSpec,
    StageSpec,
    build_model_registry,
)

# =========================================================
# Public interface
# =========================================================


def create_stage_context(
    artifact_id: str,
    *,
    stage_name: str,
    realization: str | None = None,
    project_root: Path | None = None,
) -> StageContext:
    """
    Construct the execution context for one declared artifact stage.

    Configuration is resolved for the requested artifact realization.
    The resulting Resolver is retained unchanged by StageContext.

    The requested stage is resolved from the configured model.

    Explicit external inputs refer to their canonical artifact-owned
    locations. Direct dependency products are exposed using qualified
    names of the form '<stage>.<product>'. Outputs use their declarative
    product names and canonical product locations.

    This function performs resolution only. It does not create the
    workspace, materialize external inputs, check whether filesystem
    inputs exist, execute dependencies, or execute the requested stage.
    """

    root = project_root if project_root is not None else Path.cwd()

    resolver = get_resolver(
        artifact_id,
        realization=realization,
        project_root=root,
    )

    model_name = resolver(
        "model",
    )

    if not isinstance(
        model_name,
        str,
    ):
        raise StageContextError("Artifact model must resolve to a string.")

    realization_name = resolver(
        "realization",
    )

    if not isinstance(
        realization_name,
        str,
    ):
        raise StageContextError("Artifact realization must resolve to a string.")

    registry = build_model_registry()

    try:
        model = registry.get_model(
            model_name,
        )

    except ModelNotFoundError as exc:
        raise StageContextError(f"Unknown model {model_name!r}.") from exc

    stage = _find_stage(
        model,
        stage_name,
    )

    product_resolver = ProductResolver(
        project_root=root,
    )

    artifact_dir = product_resolver.artifact_dir(
        artifact_id,
    )

    inputs = _stage_inputs(
        artifact_id=artifact_id,
        model=model,
        realization_name=realization_name,
        stage=stage,
        resolver=resolver,
        project_root=root,
        artifact_dir=artifact_dir,
        product_resolver=product_resolver,
    )

    outputs = _stage_outputs(
        artifact_id=artifact_id,
        model_name=model.name,
        realization_name=realization_name,
        stage=stage,
        product_resolver=product_resolver,
    )

    return _create_resolved_stage_context(
        artifact_id=artifact_id,
        model_name=model.name,
        stage_name=stage.name,
        project_root=root,
        artifact_dir=artifact_dir,
        resolver=resolver,
        inputs=inputs,
        outputs=outputs,
    )


# =========================================================
# Resolved context construction
# =========================================================


def _create_resolved_stage_context(
    *,
    artifact_id: str,
    model_name: str,
    stage_name: str,
    project_root: Path,
    artifact_dir: Path,
    resolver,
    inputs: dict[str, Path],
    outputs: dict[str, Path],
) -> StageContext:
    """
    Construct StageContext from already-resolved execution values.

    This is the common context-construction boundary used by both
    independent stage resolution and graph-driven build execution.

    Callers remain responsible for resolving semantic stage inputs and
    outputs. This function owns the final execution-facing context
    representation and working-directory semantics.

    Construction is side-effect free.
    """

    working_dir = _stage_working_directory(
        artifact_dir,
        outputs,
    )

    return StageContext(
        artifact_id=artifact_id,
        model_name=model_name,
        stage_name=stage_name,
        project_root=project_root,
        artifact_dir=artifact_dir,
        working_dir=working_dir,
        resolver=resolver,
        inputs=inputs,
        outputs=outputs,
    )


# =========================================================
# Stage resolution
# =========================================================


def _find_stage(
    model: ModelSpec,
    stage_name: str,
) -> StageSpec:
    """
    Return one declared stage from a model.

    Independent execution identifies stages by their semantic names.
    """

    for stage in model.stages:
        if stage.name == stage_name:
            return stage

    raise StageContextError(f"Unknown stage {stage_name!r} for model {model.name!r}.")


# =========================================================
# Stage inputs
# =========================================================


def _stage_inputs(
    *,
    artifact_id: str,
    model: ModelSpec,
    realization_name: str,
    stage: StageSpec,
    resolver,
    project_root: Path,
    artifact_dir: Path,
    product_resolver: ProductResolver,
) -> dict[str, Path]:
    """
    Resolve all filesystem inputs exposed to one stage.

    Explicit inputs use their declarative names.

    Products from direct dependency stages use qualified names such as
    'raster.manifest'.

    Only direct dependencies are exposed. Transitive dependency
    traversal remains a planning concern.
    """

    inputs: dict[str, Path] = {}

    _add_explicit_inputs(
        artifact_id=artifact_id,
        stage=stage,
        resolver=resolver,
        project_root=project_root,
        artifact_dir=artifact_dir,
        inputs=inputs,
    )

    _add_dependency_inputs(
        artifact_id=artifact_id,
        model=model,
        realization_name=realization_name,
        stage=stage,
        product_resolver=product_resolver,
        inputs=inputs,
    )

    return inputs


def _add_explicit_inputs(
    *,
    artifact_id: str,
    stage: StageSpec,
    resolver,
    project_root: Path,
    artifact_dir: Path,
    inputs: dict[str, Path],
) -> None:
    """
    Add artifact-owned locations for explicitly declared inputs.

    The configured external source path is resolved to validate the same
    configuration contract used during build planning, but independent
    StageContext construction exposes only the artifact-owned path to
    the stage.
    """

    for input_spec in stage.inputs:
        value = resolver(
            input_spec.parameter,
        )

        if not isinstance(
            value,
            str,
        ):
            raise StageContextError(
                f"Input parameter "
                f"{input_spec.parameter!r} "
                f"for artifact {artifact_id!r} "
                "must resolve to a string path."
            )

        source_path = Path(
            value,
        )

        if not source_path.is_absolute():
            source_path = project_root / source_path

        # Resolve the external source location for semantic parity with
        # normal planning. Existence is intentionally not checked here.
        _ = source_path

        _add_input(
            artifact_id=artifact_id,
            stage=stage,
            inputs=inputs,
            name=input_spec.name,
            path=artifact_dir / input_spec.path,
        )


def _add_dependency_inputs(
    *,
    artifact_id: str,
    model: ModelSpec,
    realization_name: str,
    stage: StageSpec,
    product_resolver: ProductResolver,
    inputs: dict[str, Path],
) -> None:
    """
    Add canonical products supplied by direct dependency stages.
    """

    stages = {candidate.name: candidate for candidate in model.stages}

    for dependency_name in stage.dependencies:
        try:
            dependency = stages[dependency_name]

        except KeyError as exc:
            raise StageContextError(
                f"Cannot construct context for stage "
                f"{stage.name!r} "
                f"of artifact {artifact_id!r}: "
                f"dependency {dependency_name!r} "
                f"is not declared by model {model.name!r}."
            ) from exc

        for product in dependency.products:
            name = f"{dependency.name}.{product.name}"

            path = product_resolver.product_path(
                artifact=artifact_id,
                model=model.name,
                realization=realization_name,
                stage=dependency,
                product=product,
            )

            _add_input(
                artifact_id=artifact_id,
                stage=stage,
                inputs=inputs,
                name=name,
                path=path,
            )


def _add_input(
    *,
    artifact_id: str,
    stage: StageSpec,
    inputs: dict[str, Path],
    name: str,
    path: Path,
) -> None:
    """
    Add one execution-facing filesystem input.

    Input names must remain unambiguous within StageContext.
    """

    if name in inputs:
        raise StageContextError(
            f"Cannot construct context for stage "
            f"{stage.name!r} "
            f"of artifact {artifact_id!r}: "
            f"duplicate input name {name!r}."
        )

    inputs[name] = path


# =========================================================
# Stage outputs
# =========================================================


def _stage_outputs(
    *,
    artifact_id: str,
    model_name: str,
    realization_name: str,
    stage: StageSpec,
    product_resolver: ProductResolver,
) -> dict[str, Path]:
    """
    Resolve canonical locations of all products declared by a stage.
    """

    return {
        product.name: product_resolver.product_path(
            artifact=artifact_id,
            model=model_name,
            realization=realization_name,
            stage=stage,
            product=product,
        )
        for product in stage.products
    }


# =========================================================
# Stage working directory
# =========================================================


def _stage_working_directory(
    artifact_dir: Path,
    outputs: dict[str, Path],
) -> Path:
    """
    Determine the working directory for independent stage execution.

    A stage with declared products executes from the common parent
    directory containing those products.

    A stage without declared products executes from the artifact
    directory.
    """

    if not outputs:
        return artifact_dir

    parents = [path.parent for path in outputs.values()]

    return Path(
        os.path.commonpath(
            parents,
        )
    )


# =========================================================
# Exports
# =========================================================


__all__ = [
    "create_stage_context",
]
