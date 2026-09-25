"""
Public artifact-build orchestration.

This module provides the application-level engine boundary for planning and
building a configured artifact.

Callers identify the artifact they want planned or built. The engine owns
build-plan creation, Variant selection, dependency-aware orchestration,
persistent-state-aware incremental execution, production of the requested
artifact, and publication of an accessible manufacturing result.

Callers do not construct BuildPlans or select an execution strategy.
"""

# File: src/lowkey_artifact_builder/engine/artifact_build.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import shutil
from pathlib import Path

from lowkey_artifact_builder.config import (
    get_resolver,
)
from lowkey_artifact_builder.model import (
    build_model_registry,
)

from .dependency_build import (
    execute_dependency_build,
)
from .events import (
    EventSink,
)
from .execution import (
    ExecutionPlan,
)
from .plan import (
    BuildPlan,
    create_build_plans,
)
from .product_resolver import (
    ProductResolver,
)

# =========================================================
# Publication
# =========================================================


def _publish_manufacturing_product(
    plan: BuildPlan,
) -> None:
    """
    Publish the current package Product for one Artifact Realization.

    The canonical package Product remains the persistent Product authority.
    Publication creates a Realization-named convenience copy beside the
    Artifact configuration so an operator can retrieve the manufacturing
    result without navigating the Stage workspace.

    Publication is a postcondition of successful artifact-level execution.
    It is independent of whether the package Stage executed during the
    current invocation. A current canonical package Product may therefore
    restore a missing convenience publication without rerunning package
    production.

    A BuildPlan without a package Stage has no manufacturing Product to
    publish and is left unchanged.
    """

    package_stage = next(
        (stage for stage in plan.stages if stage.name == "package"),
        None,
    )

    if package_stage is None:
        return

    if not package_stage.products:
        return

    package_product = package_stage.products[0]

    if not package_product.path.is_file():
        return

    published = plan.artifact_dir / f"{plan.realization_name}.3mf"

    try:
        shutil.copy2(
            package_product.path,
            published,
        )
    except OSError as exc:
        raise RuntimeError(
            f"Could not publish manufacturing Product {package_product.path} to {published}: {exc}"
        ) from exc


# =========================================================
# Public interface
# =========================================================


def create_artifact_build_plans(
    artifact_id: str,
    *,
    model_name: str | None = None,
    variant_name: str | None = None,
    realization: str | None = None,
    all_variants: bool = False,
    project_root: Path | None = None,
) -> tuple[BuildPlan, ...]:
    """
    Create the selected BuildPlans for one configured artifact.

    Variant and Realization are distinct selection coordinates.

    A Variant is identified by its Model and local Variant name. Artifact
    planning resolves that Variant selection to the Artifact Realization that
    applies it.

    A caller may select one Variant, one Realization, or all Variants, but those
    selection modes are mutually exclusive.

    When all_variants is true, every Variant owned by the applicable Model is
    planned through its canonical Artifact Realization.

    When neither Variant nor Realization is explicitly selected, the Artifact's
    effective Model is resolved and that Model's default Variant is selected.
    Planning resolves that Variant to its canonical Artifact Realization.

    When a local Variant name is supplied without a Model, the Artifact's
    effective Model supplies the Model coordinate for that Variant selection.
    """

    if variant_name is not None and all_variants:
        raise ValueError("variant_name and all_variants cannot be used together")

    if realization is not None and all_variants:
        raise ValueError("realization and all_variants cannot be used together")

    if variant_name is not None and realization is not None:
        raise ValueError("variant_name and realization cannot be used together")

    if all_variants:
        if model_name is None:
            resolver = get_resolver(
                artifact_id,
                project_root=project_root,
            )
        else:
            resolver = get_resolver(
                artifact_id,
                model=model_name,
                project_root=project_root,
            )

        resolved_model_name = resolver("model")

        registry = build_model_registry()

        model = registry.get_model(
            resolved_model_name,
        )

        return tuple(
            plan
            for variant in model.variants
            for plan in create_build_plans(
                artifact_id,
                model_name=resolved_model_name,
                variant_name=variant.name,
                project_root=project_root,
            )
        )

    if realization is not None:
        return create_build_plans(
            artifact_id,
            model_name=model_name,
            realization=realization,
            project_root=project_root,
        )

    if model_name is None:
        resolver = get_resolver(
            artifact_id,
            project_root=project_root,
        )

        model_name = resolver("model")

    if variant_name is None:
        variant_name = "default"

    return create_build_plans(
        artifact_id,
        model_name=model_name,
        variant_name=variant_name,
        project_root=project_root,
    )


def execute_artifact_build(
    artifact_id: str,
    *,
    model_name: str | None = None,
    variant_name: str | None = None,
    realization: str | None = None,
    all_variants: bool = False,
    project_root: Path | None = None,
    event_sink: EventSink | None = None,
) -> tuple[ExecutionPlan, ...]:
    """
    Build one or more selected workflows for one configured artifact.

    Build-plan selection is shared with non-executing callers such as dry-run.
    Each selected BuildPlan is executed through dependency-aware orchestration.

    After successful execution, any current canonical package Product is
    published as the Realization-named convenience 3MF. Publication is
    independent of whether package production executed during this invocation.

    Return the execution plan produced for each selected build plan in
    planning order.
    """

    plans = create_artifact_build_plans(
        artifact_id,
        model_name=model_name,
        variant_name=variant_name,
        realization=realization,
        all_variants=all_variants,
        project_root=project_root,
    )

    execution_plans: list[ExecutionPlan] = []

    for plan in plans:
        execution_plan = execute_dependency_build(
            plan,
            event_sink=event_sink,
        )

        _publish_manufacturing_product(
            plan,
        )

        execution_plans.append(
            execution_plan,
        )

    return tuple(
        execution_plans,
    )


def rebuild_artifact(
    artifact_id: str,
    *,
    realization: str,
    project_root: Path | None = None,
    event_sink: EventSink | None = None,
) -> tuple[ExecutionPlan, ...]:
    """
    Rebuild one selected Artifact Realization.

    The selected Realization's generated products are removed before
    dependency-aware execution. Generated products belonging to sibling
    Realizations are preserved.

    After successful execution, any current canonical package Product is
    published as the Realization-named convenience 3MF.
    """

    root = project_root if project_root is not None else Path.cwd()

    plans = create_artifact_build_plans(
        artifact_id,
        realization=realization,
        project_root=root,
    )

    product_resolver = ProductResolver(
        project_root=root,
    )

    for plan in plans:
        realization_dir = product_resolver.realization_dir(
            artifact=plan.artifact_id,
            model=plan.model_name,
            realization=plan.realization_name,
        )

        if realization_dir.exists():
            shutil.rmtree(
                realization_dir,
            )

    execution_plans: list[ExecutionPlan] = []

    for plan in plans:
        execution_plan = execute_dependency_build(
            plan,
            event_sink=event_sink,
        )

        _publish_manufacturing_product(
            plan,
        )

        execution_plans.append(
            execution_plan,
        )

    return tuple(
        execution_plans,
    )


__all__ = [
    "create_artifact_build_plans",
    "execute_artifact_build",
    "rebuild_artifact",
]
