"""
Tests for persistent product-state evaluation.

Product-state evaluation converts explicit evidence about one persistent
product into the semantic ProductState vocabulary.

These tests establish the state decision table independently of filesystem
inspection, completion-record parsing, freshness fingerprint generation,
build planning, and execution.
"""
# File: tests/engine/test_product_state_evaluation.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import pytest

from lowkey_artifact_builder.engine import (
    ProductEvidence,
    ProductState,
    evaluate_product_state,
)

# =========================================================
# Helpers
# =========================================================


def _evidence(
    *,
    exists: bool = True,
    completion_exists: bool = True,
    valid: bool = True,
    fresh: bool = True,
) -> ProductEvidence:
    """
    Create representative explicit product evidence.
    """

    return ProductEvidence(
        exists=exists,
        completion_exists=completion_exists,
        valid=valid,
        fresh=fresh,
    )


# =========================================================
# Evidence semantics
# =========================================================


def test_product_evidence_records_state_inputs() -> None:
    """
    Product evidence carries the facts required for state evaluation.
    """

    evidence = _evidence()

    assert evidence.exists
    assert evidence.completion_exists
    assert evidence.valid
    assert evidence.fresh


def test_product_evidence_is_immutable() -> None:
    """
    State evaluation evidence is immutable.
    """

    evidence = _evidence()

    with pytest.raises(
        AttributeError,
    ):
        evidence.exists = False  # type: ignore[misc]


def test_product_evidence_compares_by_value() -> None:
    """
    Evidence supports deterministic value comparison.
    """

    assert _evidence() == _evidence()


# =========================================================
# ABSENT
# =========================================================


def test_absent_product_without_completion_is_absent() -> None:
    """
    No product and no completion evidence means the product is ABSENT.
    """

    evidence = _evidence(
        exists=False,
        completion_exists=False,
        valid=False,
        fresh=False,
    )

    assert (
        evaluate_product_state(
            evidence,
        )
        is ProductState.ABSENT
    )


# =========================================================
# INCOMPLETE
# =========================================================


def test_existing_product_without_completion_is_incomplete() -> None:
    """
    Materialization without successful completion evidence is INCOMPLETE.
    """

    evidence = _evidence(
        exists=True,
        completion_exists=False,
        valid=True,
        fresh=True,
    )

    assert (
        evaluate_product_state(
            evidence,
        )
        is ProductState.INCOMPLETE
    )


def test_incomplete_state_precedes_validity() -> None:
    """
    Without completion evidence, validity does not establish completion.
    """

    evidence = _evidence(
        exists=True,
        completion_exists=False,
        valid=False,
        fresh=False,
    )

    assert (
        evaluate_product_state(
            evidence,
        )
        is ProductState.INCOMPLETE
    )


# =========================================================
# INVALID
# =========================================================


def test_completion_without_product_is_invalid() -> None:
    """
    Completion metadata claiming a missing product is INVALID.
    """

    evidence = _evidence(
        exists=False,
        completion_exists=True,
        valid=False,
        fresh=False,
    )

    assert (
        evaluate_product_state(
            evidence,
        )
        is ProductState.INVALID
    )


def test_completed_invalid_product_is_invalid() -> None:
    """
    A completed materialization that fails validation is INVALID.
    """

    evidence = _evidence(
        exists=True,
        completion_exists=True,
        valid=False,
        fresh=True,
    )

    assert (
        evaluate_product_state(
            evidence,
        )
        is ProductState.INVALID
    )


def test_invalid_state_precedes_freshness() -> None:
    """
    Freshness cannot make an invalid completed product reusable.
    """

    evidence = _evidence(
        exists=True,
        completion_exists=True,
        valid=False,
        fresh=False,
    )

    assert (
        evaluate_product_state(
            evidence,
        )
        is ProductState.INVALID
    )


# =========================================================
# STALE
# =========================================================


def test_completed_valid_stale_product_is_stale() -> None:
    """
    A valid completed product that is not fresh is STALE.
    """

    evidence = _evidence(
        exists=True,
        completion_exists=True,
        valid=True,
        fresh=False,
    )

    assert (
        evaluate_product_state(
            evidence,
        )
        is ProductState.STALE
    )


# =========================================================
# CURRENT
# =========================================================


def test_completed_valid_fresh_product_is_current() -> None:
    """
    A valid completed product with current freshness evidence is CURRENT.
    """

    evidence = _evidence(
        exists=True,
        completion_exists=True,
        valid=True,
        fresh=True,
    )

    assert (
        evaluate_product_state(
            evidence,
        )
        is ProductState.CURRENT
    )


# =========================================================
# Decision precedence
# =========================================================


@pytest.mark.parametrize(
    (
        "evidence",
        "expected",
    ),
    [
        (
            ProductEvidence(
                exists=False,
                completion_exists=False,
                valid=False,
                fresh=False,
            ),
            ProductState.ABSENT,
        ),
        (
            ProductEvidence(
                exists=True,
                completion_exists=False,
                valid=False,
                fresh=False,
            ),
            ProductState.INCOMPLETE,
        ),
        (
            ProductEvidence(
                exists=False,
                completion_exists=True,
                valid=False,
                fresh=False,
            ),
            ProductState.INVALID,
        ),
        (
            ProductEvidence(
                exists=True,
                completion_exists=True,
                valid=False,
                fresh=False,
            ),
            ProductState.INVALID,
        ),
        (
            ProductEvidence(
                exists=True,
                completion_exists=True,
                valid=True,
                fresh=False,
            ),
            ProductState.STALE,
        ),
        (
            ProductEvidence(
                exists=True,
                completion_exists=True,
                valid=True,
                fresh=True,
            ),
            ProductState.CURRENT,
        ),
    ],
)
def test_product_state_decision_table(
    evidence: ProductEvidence,
    expected: ProductState,
) -> None:
    """
    Product state follows the architectural evidence precedence.
    """

    assert (
        evaluate_product_state(
            evidence,
        )
        is expected
    )
