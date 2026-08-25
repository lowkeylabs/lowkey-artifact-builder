"""
Persistent product evidence gathering and state resolution.

Product evidence gathering inspects one expected persistent product and
the completion metadata of its producing stage.

Filesystem evidence establishes materialization and baseline validity.
Completion metadata establishes whether the producing stage recorded the
logical product as successfully produced and whether that completion
belongs to the expected artifact, model, realization, and stage.

Persisted fingerprint provenance is compared with the fingerprint required
by the current build context to establish freshness.

Product-state resolution composes evidence gathering with semantic state
evaluation while preserving the separation between those concerns.

This module does not construct execution plans, emit execution events, or
execute stages.
"""
# File: src/lowkey_artifact_builder/engine/evidence.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from .completion import (
    StageCompletion,
    read_stage_completion,
)
from .freshness import (
    ProductFingerprint,
    product_is_fresh,
)
from .state import (
    ProductEvidence,
    ProductState,
    evaluate_product_state,
)

# =========================================================
# Product-state resolution
# =========================================================


type PersistentProductStateResolver = Callable[
    [
        str,
        Path,
    ],
    ProductState,
]


# =========================================================
# Product evidence gathering
# =========================================================


def gather_product_evidence(
    *,
    working_dir: Path,
    product_name: str,
    product_path: Path,
    required_fingerprint: ProductFingerprint | None = None,
    artifact_id: str | None = None,
    model_name: str | None = None,
    realization: str | None = None,
    stage_name: str | None = None,
) -> ProductEvidence:
    """
    Gather persistent evidence for one declared product.

    product_path is interpreted relative to the producing stage's working
    directory.

    A materialization exists when something occupies the expected path.
    Baseline validity requires that materialization to be a regular file.

    Completion evidence applies only when valid stage completion metadata
    explicitly lists the requested logical product.

    When expected completion identity is supplied, the completion record
    must also belong to the expected artifact, model, realization, and
    stage. A structurally valid completion record belonging to some other
    producer therefore cannot prove successful completion for this
    product.

    Freshness requires a valid materialization, applicable completion
    evidence, and matching recorded and required fingerprints. Missing
    provenance never proves freshness.

    Invalid completion metadata is allowed to propagate as ValueError so
    corrupt metadata remains distinguishable from absent or inapplicable
    metadata.
    """

    path = working_dir / product_path

    exists = path.exists()
    valid = path.is_file()

    completion = read_stage_completion(
        working_dir,
    )

    completion_applies = completion is not None and _completion_identity_matches(
        completion,
        artifact_id=artifact_id,
        model_name=model_name,
        realization=realization,
        stage_name=stage_name,
    )

    completion_exists = (
        completion_applies and completion is not None and product_name in completion.products
    )

    recorded_fingerprint = (
        completion.fingerprint if completion is not None and completion_exists else None
    )

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
# Completion identity
# =========================================================


def _completion_identity_matches(
    completion: StageCompletion,
    *,
    artifact_id: str | None,
    model_name: str | None,
    realization: str | None,
    stage_name: str | None,
) -> bool:
    """
    Return whether completion metadata belongs to the expected producer.

    None means that the caller did not constrain that identity field.
    This preserves the lower-level evidence API for callers that do not
    possess realized build-plan identity while allowing execution-state
    resolution to enforce the complete producer identity.

    Every supplied identity field must match.
    """

    if artifact_id is not None and completion.artifact_id != artifact_id:
        return False

    if model_name is not None and completion.model_name != model_name:
        return False

    if realization is not None and completion.realization != realization:
        return False

    if stage_name is not None and completion.stage_name != stage_name:
        return False

    return True


# =========================================================
# Product-state resolver
# =========================================================


def create_product_state_resolver(
    *,
    working_dir: Path,
    required_fingerprints: dict[str, ProductFingerprint],
    artifact_id: str | None = None,
    model_name: str | None = None,
    realization: str | None = None,
    stage_name: str | None = None,
) -> PersistentProductStateResolver:
    """
    Create a resolver for persistent products in one stage working directory.

    The resolver gathers normalized evidence for each requested product,
    supplies the fingerprint required by the current build context when
    available, and converts that evidence into semantic ProductState.

    When expected completion identity is supplied, persistent completion
    metadata must identify the same artifact, model, realization, and
    stage before it can establish successful completion.

    Missing required fingerprint provenance cannot prove freshness and
    therefore cannot produce CURRENT state.

    Filesystem inspection and completion metadata interpretation remain
    delegated to gather_product_evidence. Semantic classification remains
    delegated to evaluate_product_state.
    """

    def resolve(
        product_name: str,
        product_path: Path,
    ) -> ProductState:
        evidence = gather_product_evidence(
            working_dir=working_dir,
            product_name=product_name,
            product_path=product_path,
            required_fingerprint=required_fingerprints.get(
                product_name,
            ),
            artifact_id=artifact_id,
            model_name=model_name,
            realization=realization,
            stage_name=stage_name,
        )

        return evaluate_product_state(
            evidence,
        )

    return resolve


# =========================================================
# Exports
# =========================================================


__all__ = [
    "PersistentProductStateResolver",
    "create_product_state_resolver",
    "gather_product_evidence",
]
