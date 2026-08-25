"""
Persistent product freshness.

Freshness determines whether a valid completed persistent product
represents the current build context.

This module defines fingerprint representation and pure freshness
comparison only. It does not calculate fingerprints, inspect the
filesystem, gather product evidence, persist completion metadata,
construct execution plans, emit execution events, or execute stages.

Fingerprint calculation and persistence are introduced by later
Phase 9 slices.
"""
# File: src/lowkey_artifact_builder/engine/freshness.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from dataclasses import dataclass

# =========================================================
# Product fingerprint
# =========================================================


@dataclass(
    frozen=True,
    slots=True,
)
class ProductFingerprint:
    """
    Deterministic fingerprint of one product build context.

    algorithm identifies the fingerprint algorithm.

    value contains the deterministic value produced by that algorithm.

    The representation is intentionally independent of how fingerprints
    are calculated and which build-context inputs participate in them.
    """

    algorithm: str
    value: str


# =========================================================
# Freshness evaluation
# =========================================================


def product_is_fresh(
    *,
    recorded: ProductFingerprint | None,
    required: ProductFingerprint | None,
) -> bool:
    """
    Return whether recorded provenance proves product freshness.

    Freshness requires both recorded and currently required fingerprints
    to exist and compare equal.

    Missing fingerprint evidence never proves that a product is current.
    """

    if recorded is None:
        return False

    if required is None:
        return False

    return recorded == required


# =========================================================
# Exports
# =========================================================


__all__ = [
    "ProductFingerprint",
    "product_is_fresh",
]
