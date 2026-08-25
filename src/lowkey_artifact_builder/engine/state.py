"""
Persistent product state.

Product state describes whether a declared persistent product is
available for reuse or requires production for the current build
context.

State evaluation is intentionally separate from the state vocabulary.
Filesystem inspection, completion metadata, dependency evaluation, and
configuration currency are introduced by later Phase 9 slices.
"""
# File: src/lowkey_artifact_builder/engine/state.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

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
# Exports
# =========================================================


__all__ = [
    "ProductState",
]
