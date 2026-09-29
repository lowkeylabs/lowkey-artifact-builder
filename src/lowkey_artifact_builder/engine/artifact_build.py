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
    ProductRef,
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
    Construct manufacturing build plans for one configured Artifact.

    Artifact-build planning owns selection of the Artifact Realization or
    Realizations requested by the caller. Generic build planning first resolves
    those selections to concrete Realizations.

    Manufacturing then targets each selected Realization's packaged artifact
    Product. Explicit Product targeting lets the generic planner select only
    the stages and Product dependencies required to manufacture that Product,
    rather than eagerly realizing every participating stage in the Model.

    The package/artifact Product is an artifact-build convention, not a
    privileged Product in ModelSpec. Other engine operations remain free to
    request any declared Product directly.

    A caller may select one Realization, one Model Variant, or all Variants of
    the effective Model. Variant and Realization selection remain delegated to
    generic planning.
    """

    if realization is not None and all_variants:
        raise ValueError(
            "realization and all_variants cannot be used together",
        )

    if variant_name is not None and all_variants:
        raise ValueError(
            "variant_name and all_variants cannot be used together",
        )

    root = project_root if project_root is not None else Path.cwd()

    selected_plans: tuple[BuildPlan, ...]

    if all_variants:
        resolver = get_resolver(
            artifact_id,
            project_root=root,
        )

        resolved_model_name = model_name
        if resolved_model_name is None:
            resolved_model_name = resolver("model")

        if not isinstance(
            resolved_model_name,
            str,
        ):
            raise ValueError("Artifact model must resolve to a string.")

        registry = build_model_registry()
        model = registry.get_model(
            resolved_model_name,
        )

        selected: list[BuildPlan] = []

        for variant in model.variants:
            selected.extend(
                create_build_plans(
                    artifact_id,
                    model_name=resolved_model_name,
                    variant_name=variant.name,
                    project_root=root,
                )
            )

        selected_plans = tuple(selected)

    elif realization is not None:
        selected_plans = create_build_plans(
            artifact_id,
            model_name=model_name,
            realization=realization,
            project_root=root,
        )

    else:
        resolved_model_name = model_name

        if resolved_model_name is None:
            resolver = get_resolver(
                artifact_id,
                project_root=root,
            )

            resolved_model = resolver("model")

            if not isinstance(
                resolved_model,
                str,
            ):
                raise ValueError("Artifact model must resolve to a string.")

            resolved_model_name = resolved_model

        selected_plans = create_build_plans(
            artifact_id,
            model_name=resolved_model_name,
            variant_name=variant_name or "default",
            project_root=root,
        )

    manufacturing_plans: list[BuildPlan] = []

    for selected_plan in selected_plans:
        target = ProductRef(
            artifact=selected_plan.artifact_id,
            model=selected_plan.model_name,
            realization=selected_plan.realization_name,
            stage="package",
            product="artifact",
        )

        manufacturing_plans.extend(
            create_build_plans(
                artifact_id,
                model_name=selected_plan.model_name,
                realization=selected_plan.realization_name,
                targets=(target,),
                project_root=root,
            )
        )

    return tuple(manufacturing_plans)


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
