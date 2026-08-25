"""
Persistent product freshness.

Freshness determines whether a valid completed persistent product
represents the current build context.

This module defines fingerprint representation, deterministic
build-context fingerprint generation, and pure freshness comparison.

It does not inspect the filesystem, gather product evidence, persist
completion metadata, construct execution plans, emit execution events,
or execute stages.

Fingerprint persistence and integration with product-state evaluation
are introduced by later Phase 9 slices.
"""
# File: src/lowkey_artifact_builder/engine/freshness.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import hashlib
import json
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
# Fingerprint generation
# =========================================================


def create_product_fingerprint(
    *,
    parameters: dict[str, object],
    inputs: dict[str, str],
    operation: str,
) -> ProductFingerprint:
    """
    Create a deterministic fingerprint for one product build context.

    The build context consists of three distinct semantic namespaces:

    operation
        Identity of the operation responsible for producing the product.

    parameters
        Resolved parameter values relevant to the operation.

    inputs
        Logical input identities mapped to their fingerprints.

    Mappings are serialized with deterministic key ordering while
    sequence ordering remains significant.

    Values must be JSON serializable. Unsupported values fail rather
    than being converted through unstable string representations.
    """

    payload = {
        "inputs": inputs,
        "operation": operation,
        "parameters": parameters,
    }

    serialized = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )

    digest = hashlib.sha256(
        serialized.encode(
            "utf-8",
        )
    ).hexdigest()

    return ProductFingerprint(
        algorithm="sha256",
        value=digest,
    )


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
    "create_product_fingerprint",
    "product_is_fresh",
]
