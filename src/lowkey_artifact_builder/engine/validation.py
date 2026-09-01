"""
Execution-scoped configuration validation support.

Configuration validation follows required execution rather than the complete
realized build plan.

This module determines which resolved configuration parameters participate in
validation for a particular execution plan. Model-specific validation policy
and validator execution remain owned by the model validation boundary.
"""
# File: src/lowkey_artifact_builder/engine/validation.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from .execution import ExecutionPlan
from .specs import BuildPlan

# =========================================================
# Required configuration
# =========================================================


def required_configuration_parameters(
    build_plan: BuildPlan,
    execution_plan: ExecutionPlan,
) -> tuple[str, ...]:
    """
    Return configuration parameters participating in required execution.

    The build plan contains the realized stages selected for the requested
    build. The execution plan determines which of those stages actually
    require execution after persistent product state has been evaluated.

    Only parameters declared by stages requiring execution participate in
    execution-scoped configuration validation.

    Parameter order follows realized stage order and each stage's parameter
    declaration order. A parameter consumed by more than one required stage
    is returned only once, at its first occurrence.

    This operation observes execution decisions but does not alter them,
    resolve configuration values, execute validators, inspect persistent
    state, materialize inputs, or execute stages.
    """

    required_stage_names = {stage.stage_name for stage in execution_plan.required_stages}

    parameters: list[str] = []
    seen: set[str] = set()

    for stage in build_plan.stages:
        if stage.name not in required_stage_names:
            continue

        for parameter in stage.spec.parameters:
            if parameter in seen:
                continue

            seen.add(parameter)
            parameters.append(parameter)

    return tuple(parameters)


# =========================================================
# Exports
# =========================================================


__all__ = [
    "required_configuration_parameters",
]
