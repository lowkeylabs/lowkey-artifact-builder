"""
Execution planning policy.

Execution planning determines whether realized stages require execution
for the current build context.

This module contains pure execution-decision policy. It does not inspect
the filesystem, gather product evidence, evaluate product freshness,
emit execution events, construct stage contexts, or execute stages.

Higher-level Phase 9 planning will combine persistent product-state
evaluation with these policies to construct concrete execution plans.
"""
# File: src/lowkey_artifact_builder/engine/execution.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

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
# Exports
# =========================================================


__all__ = [
    "stage_requires_execution",
]
