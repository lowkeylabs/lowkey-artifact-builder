"""
Persistent-state-aware incremental execution planning.

Incremental planning composes required build-context fingerprint
generation, persistent product-state resolution, and execution-plan
construction.

The caller supplies only a realized BuildPlan. Required fingerprints are
derived from that plan, persistent product evidence is resolved against
those fingerprints, and the resulting ExecutionPlan identifies which
realized stages require execution.

This module performs planning only. It does not execute stages, modify
persistent products, write completion metadata, or emit execution events.
"""
# File: src/lowkey_artifact_builder/engine/incremental.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from .execution import (
    ExecutionPlan,
    create_execution_plan,
)
from .execution_state import (
    create_execution_state_resolver,
)
from .fingerprint_plan import (
    create_required_fingerprints,
)
from .specs import (
    BuildPlan,
    PlannedStage,
)

# =========================================================
# Incremental execution planning
# =========================================================


def plan_incremental_execution(
    build_plan: BuildPlan,
) -> ExecutionPlan:
    """
    Construct a persistent-state-aware execution plan.

    Required fingerprints are derived from the realized BuildPlan,
    including declared parameters, external input contents, and upstream
    dependency fingerprints.

    Persistent product state is then evaluated against those required
    fingerprints. The resulting ExecutionPlan preserves every realized
    stage while identifying the subset whose products cannot be reused.

    Fingerprints are calculated once for the complete realized plan and
    subsequently resolved by stage identity.
    """

    fingerprints = create_required_fingerprints(
        build_plan,
    )

    def required_fingerprint(
        stage: PlannedStage,
    ):
        try:
            return fingerprints[stage.name]
        except KeyError as exc:
            raise ValueError(
                f"Required fingerprint for stage {stage.name!r} is unavailable"
            ) from exc

    product_state = create_execution_state_resolver(
        build_plan,
        required_fingerprint=required_fingerprint,
    )

    return create_execution_plan(
        build_plan,
        product_state=product_state,
    )


# =========================================================
# Exports
# =========================================================


__all__ = [
    "plan_incremental_execution",
]
