"""
Persistent product evidence gathering.

Product evidence gathering inspects one expected persistent product and
the completion metadata of its producing stage.

Filesystem evidence establishes materialization and baseline validity.
Completion metadata establishes whether the producing stage recorded the
logical product as successfully produced. Persisted fingerprint provenance
is compared with the fingerprint required by the current build context to
establish freshness.

This module gathers normalized ProductEvidence only. It does not evaluate
ProductState, construct execution plans, emit execution events, or execute
stages.
"""
# File: src/lowkey_artifact_builder/engine/evidence.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path

from .completion import (
    read_stage_completion,
)
from .freshness import (
    ProductFingerprint,
    product_is_fresh,
)
from .state import (
    ProductEvidence,
)

# =========================================================
# Product evidence gathering
# =========================================================


def gather_product_evidence(
    *,
    working_dir: Path,
    product_name: str,
    product_path: Path,
    required_fingerprint: ProductFingerprint | None = None,
) -> ProductEvidence:
    """
    Gather persistent evidence for one declared product.

    product_path is interpreted relative to the producing stage's working
    directory.

    A materialization exists when something occupies the expected path.
    Baseline validity requires that materialization to be a regular file.

    Completion evidence applies only when valid stage completion metadata
    explicitly lists the requested logical product.

    Freshness requires a valid materialization, applicable completion
    evidence, and matching recorded and required fingerprints. Missing
    provenance never proves freshness.

    Invalid completion metadata is allowed to propagate as ValueError so
    corrupt metadata remains distinguishable from absent metadata.
    """

    path = working_dir / product_path

    exists = path.exists()
    valid = path.is_file()

    completion = read_stage_completion(
        working_dir,
    )

    completion_exists = completion is not None and product_name in completion.products

    recorded_fingerprint = completion.fingerprint if completion is not None else None

    fresh = (
        valid
        and completion_exists
        and product_is_fresh(
            recorded=recorded_fingerprint,
            required=required_fingerprint,
        )
    )

    return ProductEvidence(
        exists=exists,
        completion_exists=completion_exists,
        valid=valid,
        fresh=fresh,
    )


# =========================================================
# Exports
# =========================================================


__all__ = [
    "gather_product_evidence",
]
