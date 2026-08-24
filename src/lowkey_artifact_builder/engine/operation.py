"""
Independent artifact stage operations.

This module composes stage context resolution, input readiness
validation, and model-specific stage execution into the engine-level
operation used for explicit independent stage execution.

The operation executes exactly the requested stage. It does not create
a BuildPlan, traverse dependencies, materialize external inputs, or
execute prerequisite stages.
"""
# File: src/lowkey_artifact_builder/engine/operation.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path

from .context import (
    create_stage_context,
)
from .stage import (
    execute_stage,
    validate_stage_inputs,
)

# =========================================================
# Public interface
# =========================================================


def execute_artifact_stage(
    artifact_id: str,
    *,
    stage_name: str,
    realization: str | None = None,
    project_root: Path | None = None,
) -> None:
    """
    Execute exactly one configured artifact stage independently.

    The requested artifact, realization, and stage are first resolved
    into a StageContext. Every resolved filesystem input must already
    exist and be ready for execution. The resolved stage is then
    dispatched through the common stage execution boundary.

    This operation does not construct a BuildPlan, traverse stage
    dependencies, materialize external inputs, realize missing
    dependency products, or execute prerequisite stages.

    Missing inputs therefore cause validation to fail rather than
    causing additional stages to run.
    """

    context = create_stage_context(
        artifact_id,
        stage_name=stage_name,
        realization=realization,
        project_root=project_root,
    )

    validate_stage_inputs(
        context,
    )

    execute_stage(
        context,
    )


# =========================================================
# Exports
# =========================================================


__all__ = [
    "execute_artifact_stage",
]
