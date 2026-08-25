"""
Persistent product state.

Product state describes whether a declared persistent product is
available for reuse or requires production for the current build
context.

State evaluation operates on explicit normalized evidence. Filesystem
inspection, completion metadata, dependency evaluation, and configuration
currency are responsible for producing that evidence in later Phase 9
slices.
"""
# File: src/lowkey_artifact_builder/engine/state.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

# =========================================================
# Product state
# =========================================================


class ProductState(StrEnum):
    """
    Persistent state of one declared product.

    ABSENT
        No persistent product materialization is available.

    INCOMPLETE
        Product generation began but did not complete successfully.

    INVALID
        A completed product exists but fails validity checks.

    STALE
        A valid completed product exists but no longer represents the
        current inputs, configuration, or dependencies.

    CURRENT
        A valid completed product represents the current inputs,
        configuration, and dependencies.
    """

    ABSENT = "absent"
    INCOMPLETE = "incomplete"
    INVALID = "invalid"
    STALE = "stale"
    CURRENT = "current"

    @property
    def available(
        self,
    ) -> bool:
        """
        Return whether a valid completed materialization exists.
        """

        return self in {
            ProductState.STALE,
            ProductState.CURRENT,
        }

    @property
    def reusable(
        self,
    ) -> bool:
        """
        Return whether the product may satisfy current requested work.
        """

        return self is ProductState.CURRENT

    @property
    def requires_build(
        self,
    ) -> bool:
        """
        Return whether the product requires production when requested.
        """

        return not self.reusable


# =========================================================
# Product evidence
# =========================================================


@dataclass(
    frozen=True,
    slots=True,
)
class ProductEvidence:
    """
    Normalized evidence used to determine persistent product state.

    exists
        The expected persistent product materialization exists.

    completion_exists
        Successful completion metadata exists for the producing stage.

    valid
        The existing completed product satisfies its validity checks.

    fresh
        The existing valid completed product corresponds to the current
        inputs, dependencies, configuration, and operation versions.

    Evidence gathering is intentionally separate from state evaluation.
    """

    exists: bool
    completion_exists: bool
    valid: bool
    fresh: bool


# =========================================================
# State evaluation
# =========================================================


def evaluate_product_state(
    evidence: ProductEvidence,
) -> ProductState:
    """
    Determine persistent product state from normalized evidence.

    Completion evidence establishes the boundary between work that never
    successfully completed and work that claims successful completion.

    Validity is meaningful only after successful completion is recorded,
    and freshness is meaningful only for an existing valid completed
    product.
    """

    if not evidence.completion_exists:
        if evidence.exists:
            return ProductState.INCOMPLETE

        return ProductState.ABSENT

    if not evidence.exists:
        return ProductState.INVALID

    if not evidence.valid:
        return ProductState.INVALID

    if not evidence.fresh:
        return ProductState.STALE

    return ProductState.CURRENT


# =========================================================
# Exports
# =========================================================


__all__ = [
    "ProductEvidence",
    "ProductState",
    "evaluate_product_state",
]
