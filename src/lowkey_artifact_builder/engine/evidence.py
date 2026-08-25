"""
Persistent product evidence gathering.

Product evidence gathering inspects one expected persistent product and
the completion metadata of its producing stage.

This module gathers filesystem and completion evidence only. It does not
determine freshness, evaluate ProductState, construct execution plans,
emit execution events, or execute stages.

Freshness remains false until later Phase 9 slices introduce sufficient
provenance or fingerprint evidence to prove that a completed product
represents the current build context.
"""
# File: src/lowkey_artifact_builder/engine/evidence.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path

from .completion import (
    read_stage_completion,
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
) -> ProductEvidence:
    """
    Gather persistent evidence for one declared product.

    product_path is interpreted relative to the producing stage's working
    directory.

    A materialization exists when something occupies the expected path.
    Baseline validity requires that materialization to be a regular file.

    Completion evidence applies only when valid stage completion metadata
    explicitly lists the requested logical product.

    Freshness is deliberately not inferred from filesystem or completion
    evidence alone. Until provenance or fingerprint evidence is available,
    gathered products cannot be proven CURRENT.
    """

    path = working_dir / product_path

    exists = path.exists()
    valid = path.is_file()

    completion = read_stage_completion(
        working_dir,
    )

    completion_exists = completion is not None and product_name in completion.products

    return ProductEvidence(
        exists=exists,
        completion_exists=completion_exists,
        valid=valid,
        fresh=False,
    )


# =========================================================
# Exports
# =========================================================


__all__ = [
    "gather_product_evidence",
]
