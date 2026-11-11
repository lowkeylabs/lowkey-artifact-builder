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
    Publish Realization-named manufacturing convenience files.

    The canonical Stage Products remain authoritative.

    The packaged 3MF is published whenever the package Product exists,
    preserving the existing artifact-build behavior.

    For SHAPE, an enabled shape_svg_enabled setting additionally publishes
    the canonical Compose SVG. This publication is independent of whether
    Compose executed during the current build.

    Publication settings do not change Stage dependencies, fingerprints,
    or canonical Products. Disabling SVG publication does not delete a
    previously published convenience file.
    """
    package_stage = next(
        (stage for stage in plan.stages if stage.name == "package"),
        None,
    )

    if package_stage is None or not package_stage.products:
        return

    package_product = package_stage.products[0]

    if not package_product.path.is_file():
        return

    published_3mf = plan.artifact_dir / f"{plan.realization_name}.3mf"

    try:
        shutil.copy2(
            package_product.path,
            published_3mf,
        )
    except OSError as exc:
        raise RuntimeError(
            f"Could not publish manufacturing Product "
            f"{package_product.path} to {published_3mf}: {exc}"
        ) from exc

    # SVG publication is currently a SHAPE-specific policy.
    # Other Models retain their existing publication behavior.

    if plan.model_name != "shape":
        return

    if not plan.resolver("shape_svg_enabled"):
        return

    compose_stage = next(
        (stage for stage in plan.stages if stage.name == "compose"),
        None,
    )

    if compose_stage is None:
        raise RuntimeError(
            f"Cannot publish SVG for Shape Realization "
            f"{plan.realization_name!r}: "
            "Compose Stage is missing from the BuildPlan."
        )

    svg_product = next(
        (product for product in compose_stage.products if product.spec.name == "artifact"),
        None,
    )

    if svg_product is None:
        raise RuntimeError(
            f"Cannot publish SVG for Shape Realization "
            f"{plan.realization_name!r}: "
            "Compose Stage does not declare an artifact Product."
        )

    if not svg_product.path.is_file():
        raise RuntimeError(
            f"Cannot publish SVG for Shape Realization "
            f"{plan.realization_name!r}: "
            f"canonical Product is missing: {svg_product.path}"
        )

    published_svg = plan.artifact_dir / f"{plan.realization_name}.svg"

    try:
        shutil.copy2(
            svg_product.path,
            published_svg,
        )
    except OSError as exc:
        raise RuntimeError(
            f"Could not publish manufacturing Product {svg_product.path} to {published_svg}: {exc}"
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
    product: str = "3mf",
    project_root: Path | None = None,
) -> tuple[BuildPlan, ...]:
    """
    Construct manufacturing build plans for configured Artifact Realizations.

    The caller may explicitly request a SHAPE SVG or the established
    packaged 3MF. The default remains 3MF for compatibility.

    Product selection determines the terminal ProductRef. Generic planning
    owns the required Stage and Product dependency closure.
    """

    if product not in {"svg", "3mf"}:
        raise ValueError(
            f"Unsupported manufacturing product: {product!r}. Expected 'svg' or '3mf'."
        )

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
        if product == "svg":
            if selected_plan.model_name != "shape":
                raise ValueError(
                    "SVG manufacturing is currently supported only for SHAPE Realizations."
                )

            stage_name = "compose"
        else:
            stage_name = "package"

        target = ProductRef(
            artifact=selected_plan.artifact_id,
            model=selected_plan.model_name,
            realization=selected_plan.realization_name,
            stage=stage_name,
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
    product: str = "3mf",
    project_root: Path | None = None,
    event_sink: EventSink | None = None,
) -> tuple[ExecutionPlan, ...]:
    """
    Build one or more selected manufacturing Products for an Artifact.

    The default manufacturing Product remains the packaged 3MF.

    An explicit SVG request targets the canonical SHAPE Compose artifact
    Product without requiring SHAPE Extrude or Package.

    Build-plan selection is shared with non-executing callers such as
    dry-run. Each selected BuildPlan is executed through dependency-aware
    orchestration.

    Existing 3MF convenience publication remains unchanged. SVG-only
    builds produce the canonical Compose SVG; convenient SVG publication
    is outside this slice.

    Return the execution plan produced for each selected build plan in
    planning order.
    """

    plans = create_artifact_build_plans(
        artifact_id,
        model_name=model_name,
        variant_name=variant_name,
        realization=realization,
        all_variants=all_variants,
        product=product,
        project_root=project_root,
    )

    execution_plans: list[ExecutionPlan] = []

    for plan in plans:
        execution_plan = execute_dependency_build(
            plan,
            event_sink=event_sink,
        )

        if product == "3mf":
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
