"""
Execution-scoped configuration validation support.

Configuration validation follows required execution rather than the complete
realized build plan.

This module determines which resolved configuration parameters participate in
validation for a particular execution plan and applies only model-owned
validators relevant to that required configuration.
"""
# File: src/lowkey_artifact_builder/engine/validation.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from lowkey_artifact_builder.model.validation import (
    ConfigurationResolver,
    ConfigurationValidator,
    validate_configuration,
)

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
# Execution-scoped validation
# =========================================================


def validate_required_configuration(
    resolver: ConfigurationResolver,
    *,
    required_parameters: tuple[str, ...],
    validators: tuple[ConfigurationValidator, ...],
) -> None:
    """
    Validate model configuration relevant to required execution.

    Required parameters describe the configuration consumed by stages that
    must execute.

    A model validator participates when at least one parameter governed by
    that validator is required by execution. This permits one validator to
    express a cross-parameter invariant while allowing already-current stages
    and their historical configuration to remain outside validation scope.

    Relevant validators retain their model declaration order.

    This operation does not determine execution state, alter the execution
    plan, materialize inputs, or execute stages.
    """

    required = set(required_parameters)

    relevant_validators = tuple(
        validator for validator in validators if required.intersection(validator.parameters)
    )

    validate_configuration(
        resolver,
        validators=relevant_validators,
    )


# =========================================================
# Exports
# =========================================================


__all__ = [
    "required_configuration_parameters",
    "validate_required_configuration",
]
