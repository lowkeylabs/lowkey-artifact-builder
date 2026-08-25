"""
Tests for stage execution decisions.

Execution decisions determine whether a realized stage must execute from
the persistent state of its declared products.

These tests establish the pure decision contract independently of
filesystem evidence gathering, execution-plan construction, dependency
propagation, event emission, and stage execution.
"""
# File: tests/engine/test_execution_decision.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import pytest

from lowkey_artifact_builder.engine import (
    ProductState,
    stage_requires_execution,
)

# =========================================================
# Current products
# =========================================================


def test_stage_with_one_current_product_does_not_require_execution() -> None:
    """
    A stage may be skipped when its only persistent product is current.
    """

    assert not stage_requires_execution((ProductState.CURRENT,))


def test_stage_with_all_current_products_does_not_require_execution() -> None:
    """
    A stage may be skipped when every persistent product is current.
    """

    assert not stage_requires_execution(
        (
            ProductState.CURRENT,
            ProductState.CURRENT,
            ProductState.CURRENT,
        )
    )


# =========================================================
# Products requiring production
# =========================================================


@pytest.mark.parametrize(
    "state",
    (
        ProductState.ABSENT,
        ProductState.INCOMPLETE,
        ProductState.INVALID,
        ProductState.STALE,
    ),
)
def test_stage_with_noncurrent_product_requires_execution(
    state: ProductState,
) -> None:
    """
    Every non-current product state requires its producing stage to run.
    """

    assert stage_requires_execution((state,))


@pytest.mark.parametrize(
    "state",
    (
        ProductState.ABSENT,
        ProductState.INCOMPLETE,
        ProductState.INVALID,
        ProductState.STALE,
    ),
)
def test_one_noncurrent_product_requires_whole_stage_execution(
    state: ProductState,
) -> None:
    """
    One non-current product requires execution even when sibling products
    are current.
    """

    assert stage_requires_execution(
        (
            ProductState.CURRENT,
            state,
            ProductState.CURRENT,
        )
    )


def test_multiple_noncurrent_products_require_execution() -> None:
    """
    A stage executes once regardless of how many products require rebuilding.
    """

    assert stage_requires_execution(
        (
            ProductState.ABSENT,
            ProductState.STALE,
            ProductState.INVALID,
        )
    )


# =========================================================
# Product-state semantics
# =========================================================


@pytest.mark.parametrize(
    "state",
    list(ProductState),
)
def test_stage_execution_decision_agrees_with_product_state(
    state: ProductState,
) -> None:
    """
    A single-product stage follows the product state's rebuild semantics.
    """

    assert stage_requires_execution((state,)) is state.requires_build


# =========================================================
# Stages without persistent products
# =========================================================


def test_stage_without_persistent_products_requires_execution() -> None:
    """
    A realized stage without persistent products cannot prove prior work
    reusable and therefore requires execution.
    """

    assert stage_requires_execution(())
