"""
Tests for persistent product state semantics.

Product state describes the relationship between a declared persistent
product and the evidence available for a particular realization.

These tests establish the Phase 9 state vocabulary independently of
filesystem inspection, completion metadata, dependency evaluation, and
build execution.
"""
# File: tests/engine/test_product_state.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from lowkey_artifact_builder.engine import (
    ProductState,
)

# =========================================================
# Product state vocabulary
# =========================================================


def test_product_state_defines_absent() -> None:
    """
    ABSENT means no persistent product materialization is available.
    """

    assert ProductState.ABSENT.value == "absent"


def test_product_state_defines_incomplete() -> None:
    """
    INCOMPLETE means production began but did not complete successfully.
    """

    assert ProductState.INCOMPLETE.value == "incomplete"


def test_product_state_defines_invalid() -> None:
    """
    INVALID means a completed product exists but fails validity checks.
    """

    assert ProductState.INVALID.value == "invalid"


def test_product_state_defines_stale() -> None:
    """
    STALE means a valid completed product no longer represents current inputs.
    """

    assert ProductState.STALE.value == "stale"


def test_product_state_defines_current() -> None:
    """
    CURRENT means a valid completed product represents current inputs.
    """

    assert ProductState.CURRENT.value == "current"


def test_product_state_contains_only_declared_states() -> None:
    """
    The initial product-state contract has exactly five semantic states.
    """

    assert tuple(ProductState) == (
        ProductState.ABSENT,
        ProductState.INCOMPLETE,
        ProductState.INVALID,
        ProductState.STALE,
        ProductState.CURRENT,
    )


# =========================================================
# Serialization semantics
# =========================================================


def test_product_state_values_are_stable_strings() -> None:
    """
    Product states expose simple stable values suitable for metadata.
    """

    assert {state.value for state in ProductState} == {
        "absent",
        "incomplete",
        "invalid",
        "stale",
        "current",
    }


def test_product_state_round_trips_from_value() -> None:
    """
    A serialized product-state value reconstructs the semantic state.
    """

    for state in ProductState:
        assert ProductState(state.value) is state


# =========================================================
# State classification
# =========================================================


def test_absent_product_is_not_available() -> None:
    """
    ABSENT products are not available for reuse.
    """

    assert not ProductState.ABSENT.available


def test_incomplete_product_is_not_available() -> None:
    """
    INCOMPLETE products are not available for reuse.
    """

    assert not ProductState.INCOMPLETE.available


def test_invalid_product_is_not_available() -> None:
    """
    INVALID products are not available for reuse.
    """

    assert not ProductState.INVALID.available


def test_stale_product_is_available_but_not_reusable() -> None:
    """
    STALE products physically exist but must not satisfy current work.
    """

    assert ProductState.STALE.available
    assert not ProductState.STALE.reusable


def test_current_product_is_available_and_reusable() -> None:
    """
    CURRENT products may satisfy requested work without rebuilding.
    """

    assert ProductState.CURRENT.available
    assert ProductState.CURRENT.reusable


def test_only_current_product_is_reusable() -> None:
    """
    CURRENT is the only state that may satisfy current requested work.
    """

    assert {state for state in ProductState if state.reusable} == {
        ProductState.CURRENT,
    }


# =========================================================
# Rebuild semantics
# =========================================================


def test_absent_product_requires_build() -> None:
    """
    ABSENT products require production when requested.
    """

    assert ProductState.ABSENT.requires_build


def test_incomplete_product_requires_build() -> None:
    """
    INCOMPLETE products require production when requested.
    """

    assert ProductState.INCOMPLETE.requires_build


def test_invalid_product_requires_build() -> None:
    """
    INVALID products require production when requested.
    """

    assert ProductState.INVALID.requires_build


def test_stale_product_requires_build() -> None:
    """
    STALE products require production when requested.
    """

    assert ProductState.STALE.requires_build


def test_current_product_does_not_require_build() -> None:
    """
    CURRENT products do not require production merely because requested.
    """

    assert not ProductState.CURRENT.requires_build


def test_reusable_and_requires_build_are_complementary() -> None:
    """
    Initial product-state semantics make reuse and rebuilding exclusive.
    """

    for state in ProductState:
        assert state.reusable is not state.requires_build
