"""
Artifact build subsystem.

The build subsystem materializes configured artifact models into
concrete build plans and executes those plans.

Planning is intentionally separate from execution so build workflows
may be inspected and validated without modifying filesystem products.

Execution owns artifact workspace creation, external input
materialization, stage dispatch, execution contexts, and verification
of declared products.

Independent stage execution uses the same resolved StageContext and
model-specific stage implementation boundary as graph-driven builds.
Stage input readiness may be validated independently before execution.
"""
# File: src/lowkey_artifact_builder/engine/__init__.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from .build import (
    BuildError,
    execute_artifact_stage,
    execute_build,
    execute_builds,
)
from .context import (
    create_stage_context,
)
from .plan import (
    BuildPlanError,
    create_build_plan,
    create_build_plans,
)
from .specs import (
    BuildPlan,
    PlannedInput,
    PlannedProduct,
    PlannedStage,
    StageContext,
    StageContextError,
)
from .stage import (
    StageExecutionError,
    StageInputError,
    execute_stage,
    validate_stage_inputs,
)

__all__ = [
    "BuildError",
    "BuildPlan",
    "BuildPlanError",
    "PlannedInput",
    "PlannedProduct",
    "PlannedStage",
    "StageContext",
    "StageContextError",
    "StageExecutionError",
    "StageInputError",
    "create_build_plan",
    "create_build_plans",
    "create_stage_context",
    "execute_artifact_stage",
    "execute_build",
    "execute_builds",
    "execute_stage",
    "validate_stage_inputs",
]
