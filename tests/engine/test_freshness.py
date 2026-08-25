"""
Tests for persistent product freshness.

Freshness determines whether a valid completed persistent product
represents the current build context.

These tests establish fingerprint representation and comparison
independently of fingerprint calculation, filesystem evidence gathering,
completion persistence, execution-plan construction, and stage execution.
"""
# File: tests/engine/test_freshness.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from lowkey_artifact_builder.engine import (
    ProductFingerprint,
    product_is_fresh,
)

# =========================================================
# Helpers
# =========================================================


def _fingerprint(
    value: str = "abc123",
) -> ProductFingerprint:
    """
    Create representative product freshness metadata.
    """

    return ProductFingerprint(
        algorithm="sha256",
        value=value,
    )


# =========================================================
# Fingerprint representation
# =========================================================


def test_product_fingerprint_carries_algorithm() -> None:
    """
    A fingerprint identifies the algorithm used to produce its value.
    """

    fingerprint = _fingerprint()

    assert fingerprint.algorithm == "sha256"


def test_product_fingerprint_carries_value() -> None:
    """
    A fingerprint carries its deterministic comparison value.
    """

    fingerprint = _fingerprint(
        "deadbeef",
    )

    assert fingerprint.value == "deadbeef"


def test_product_fingerprint_is_immutable() -> None:
    """
    Recorded freshness evidence cannot be mutated after construction.
    """

    fingerprint = _fingerprint()

    with pytest.raises(
        FrozenInstanceError,
    ):
        fingerprint.value = "other"  # type: ignore[misc]


def test_product_fingerprints_compare_by_value() -> None:
    """
    Equivalent fingerprints support deterministic value comparison.
    """

    assert ProductFingerprint(
        algorithm="sha256",
        value="abc123",
    ) == ProductFingerprint(
        algorithm="sha256",
        value="abc123",
    )


def test_different_fingerprint_values_compare_differently() -> None:
    """
    Different fingerprint values represent different build contexts.
    """

    assert ProductFingerprint(
        algorithm="sha256",
        value="abc123",
    ) != ProductFingerprint(
        algorithm="sha256",
        value="def456",
    )


def test_different_fingerprint_algorithms_compare_differently() -> None:
    """
    Fingerprints produced by different algorithms are not equivalent.
    """

    assert ProductFingerprint(
        algorithm="sha256",
        value="abc123",
    ) != ProductFingerprint(
        algorithm="other",
        value="abc123",
    )


# =========================================================
# Freshness comparison
# =========================================================


def test_matching_fingerprints_are_fresh() -> None:
    """
    Identical recorded and required fingerprints prove freshness.
    """

    recorded = _fingerprint(
        "abc123",
    )

    required = _fingerprint(
        "abc123",
    )

    assert product_is_fresh(
        recorded=recorded,
        required=required,
    )


def test_different_fingerprint_values_are_stale() -> None:
    """
    Different fingerprint values do not represent the same build context.
    """

    recorded = _fingerprint(
        "abc123",
    )

    required = _fingerprint(
        "def456",
    )

    assert not product_is_fresh(
        recorded=recorded,
        required=required,
    )


def test_different_fingerprint_algorithms_are_stale() -> None:
    """
    Fingerprints from different algorithms cannot prove freshness.
    """

    recorded = ProductFingerprint(
        algorithm="sha256",
        value="abc123",
    )

    required = ProductFingerprint(
        algorithm="other",
        value="abc123",
    )

    assert not product_is_fresh(
        recorded=recorded,
        required=required,
    )


# =========================================================
# Missing evidence
# =========================================================


def test_missing_recorded_fingerprint_is_not_fresh() -> None:
    """
    A product without recorded provenance cannot be proven current.
    """

    assert not product_is_fresh(
        recorded=None,
        required=_fingerprint(),
    )


def test_missing_required_fingerprint_is_not_fresh() -> None:
    """
    Freshness cannot be established without the current required context.
    """

    assert not product_is_fresh(
        recorded=_fingerprint(),
        required=None,
    )


def test_missing_both_fingerprints_is_not_fresh() -> None:
    """
    Absence of provenance on both sides does not imply freshness.
    """

    assert not product_is_fresh(
        recorded=None,
        required=None,
    )


# =========================================================
# Conservative freshness
# =========================================================


@pytest.mark.parametrize(
    (
        "recorded",
        "required",
        "expected",
    ),
    [
        (
            ProductFingerprint(
                algorithm="sha256",
                value="same",
            ),
            ProductFingerprint(
                algorithm="sha256",
                value="same",
            ),
            True,
        ),
        (
            ProductFingerprint(
                algorithm="sha256",
                value="old",
            ),
            ProductFingerprint(
                algorithm="sha256",
                value="new",
            ),
            False,
        ),
        (
            ProductFingerprint(
                algorithm="sha256",
                value="same",
            ),
            ProductFingerprint(
                algorithm="other",
                value="same",
            ),
            False,
        ),
        (
            None,
            ProductFingerprint(
                algorithm="sha256",
                value="same",
            ),
            False,
        ),
        (
            ProductFingerprint(
                algorithm="sha256",
                value="same",
            ),
            None,
            False,
        ),
        (
            None,
            None,
            False,
        ),
    ],
)
def test_product_freshness_decision_table(
    recorded: ProductFingerprint | None,
    required: ProductFingerprint | None,
    expected: bool,
) -> None:
    """
    Freshness is proven only by matching explicit fingerprint evidence.
    """

    assert (
        product_is_fresh(
            recorded=recorded,
            required=required,
        )
        is expected
    )
