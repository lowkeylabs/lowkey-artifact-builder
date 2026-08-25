"""
Execution planning policy.

Execution planning determines whether realized stages require execution
for the current build context.

This module contains pure execution-decision policy and execution-plan
representation. It does not inspect the filesystem, gather product
evidence, evaluate product freshness, emit execution events, construct
stage contexts, or execute stages.

Higher-level Phase 9 planning will combine persistent product-state
evaluation with these policies to construct concrete execution plans.
"""
# File: src/lowkey_artifact_builder/engine/execution.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from dataclasses import dataclass

from .state import (
    ProductState,
)

# =========================================================
# Stage execution decisions
# =========================================================


def stage_requires_execution(
    states: tuple[ProductState, ...],
) -> bool:
    """
    Return whether a realized stage requires execution.

    A stage without persistent products requires execution because no
    persistent product state exists that can prove its previous work
    reusable.

    A stage with persistent products may be skipped only when every
    declared product is CURRENT.

    Any product state requiring production therefore requires execution
    of the whole producing stage.
    """

    if not states:
        return True

    return any(state.requires_build for state in states)


# =========================================================
# Planned stage execution
# =========================================================


@dataclass(
    frozen=True,
    slots=True,
)
class PlannedStageExecution:
    """
    Execution decision for one realized stage.

    product_states contains the evaluated persistent state of the stage's
    declared products.

    requires_execution is derived from those states so the execution
    decision cannot contradict the underlying product-state evidence.
    """

    stage_name: str
    product_states: tuple[ProductState, ...]

    @property
    def requires_execution(
        self,
    ) -> bool:
        """
        Return whether this realized stage must execute.
        """

        return stage_requires_execution(
            self.product_states,
        )


# =========================================================
# Execution plan
# =========================================================


@dataclass(
    frozen=True,
    slots=True,
)
class ExecutionPlan:
    """
    Concrete execution decisions for one artifact realization.

    stages preserves the complete ordered realized workflow, including
    stages whose persistent products are already reusable.

    required_stages exposes the ordered subset that must actually execute
    for the current build context.
    """

    artifact_id: str
    model_name: str
    realization: str
    stages: tuple[PlannedStageExecution, ...]

    @property
    def required_stages(
        self,
    ) -> tuple[PlannedStageExecution, ...]:
        """
        Return the ordered stages that require execution.
        """

        return tuple(stage for stage in self.stages if stage.requires_execution)


# =========================================================
# Exports
# =========================================================


__all__ = [
    "ExecutionPlan",
    "PlannedStageExecution",
    "stage_requires_execution",
]
