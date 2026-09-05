"""
Public artifact-build orchestration.

This module provides the application-level engine boundary for building a
configured artifact.

Callers identify the artifact they want built. The engine owns build-plan
creation, dependency-aware orchestration, persistent-state-aware incremental
execution, and production of the requested artifact.

Callers do not construct BuildPlans or select an execution strategy.
"""
# File: src/lowkey_artifact_builder/engine/artifact_build.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path

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
    create_build_plans,
)

# =========================================================
# Public interface
# =========================================================


def execute_artifact_build(
    artifact_id: str,
    *,
    model_name: str | None = None,
    realization: str | None = None,
    project_root: Path | None = None,
    event_sink: EventSink | None = None,
) -> tuple[ExecutionPlan, ...]:
    """
    Build one or more realized workflows for one configured artifact.

    The artifact identity and optional realization are the ordinary public
    inputs to this orchestration boundary.

    Model and realization may also be supplied together as the decomposed
    identity of a qualified Variant. The Model selects the Variant namespace
    and realization carries its local Variant name.

    When realization is omitted, every configured realization is built.
    When realization is supplied, only that realization is built.

    Build-plan creation and execution strategy remain engine responsibilities.

    Each realized BuildPlan is executed through dependency-aware orchestration.
    That orchestration determines required producer work, reuses persistent
    products when valid, and incrementally executes the requested artifact.

    Structured execution events are forwarded unchanged to the supplied
    presentation-independent event sink.

    Return the execution plan produced for each selected artifact realization
    in build-plan order.
    """

    planning_options = {}

    if model_name is not None:
        planning_options["model_name"] = model_name

    if realization is not None:
        planning_options["realization"] = realization

    plans = create_build_plans(
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
    "execute_artifact_build",
]
