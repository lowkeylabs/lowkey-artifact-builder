"""
Public artifact-build orchestration.

This module provides the application-level engine boundary for planning and
building a configured artifact.

Callers identify the artifact they want planned or built. The engine owns
build-plan creation, Variant selection, dependency-aware orchestration,
persistent-state-aware incremental execution, and production of the requested
artifact.

Callers do not construct BuildPlans or select an execution strategy.
"""
# File: src/lowkey_artifact_builder/engine/artifact_build.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

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

    Model, Variant, all-Variant, and Artifact Realization selection remain
    distinct coordinates.

    A caller may select one Variant or all Variants, but not both.

    When all_variants is true, every Variant owned by the applicable Model
    is planned independently. Variant enumeration does not create or select
    Artifact Realizations.

    Otherwise ordinary build planning preserves explicit Model, Variant, and
    Artifact Realization selection while leaving omitted selections implicit.
    """

    if variant_name is not None and all_variants:
        raise ValueError("variant_name and all_variants cannot be used together")

    if all_variants:
        resolver_options = {}

        if model_name is not None:
            resolver_options["model"] = model_name

        if realization is not None:
            resolver_options["realization"] = realization

        resolver = get_resolver(
            artifact_id,
            project_root=project_root,
            **resolver_options,
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
                realization=realization,
                project_root=project_root,
            )
        )

    planning_options = {}

    if model_name is not None:
        planning_options["model_name"] = model_name

    if variant_name is not None:
        planning_options["variant_name"] = variant_name

    if realization is not None:
        planning_options["realization"] = realization

    return create_build_plans(
        artifact_id,
        project_root=project_root,
        **planning_options,
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
    Each selected BuildPlan is then executed through dependency-aware
    orchestration.

    Return the execution plan produced for each selected build plan in
    planning order.
    """

    planning_options = {}

    if model_name is not None:
        planning_options["model_name"] = model_name

    if variant_name is not None:
        planning_options["variant_name"] = variant_name

    if realization is not None:
        planning_options["realization"] = realization

    if all_variants:
        planning_options["all_variants"] = True

    plans = create_artifact_build_plans(
        artifact_id,
        project_root=project_root,
        **planning_options,
    )

    return tuple(
        execute_dependency_build(
            plan,
            event_sink=event_sink,
        )
        for plan in plans
    )


__all__ = [
    "create_artifact_build_plans",
    "execute_artifact_build",
]
