"""
Tests for observable product-state evaluation.

Product-state events expose state decisions as structured semantic data
without coupling the engine to logging, CLI formatting, progress rendering,
or build execution.

These tests establish the observation contract independently of filesystem
evidence gathering and execution integration.
"""
# File: tests/engine/test_state_events.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from lowkey_artifact_builder.engine import (
    EventSink,
    ExecutionEvent,
    ProductState,
    ProductStateEvent,
    emit_event,
)

# =========================================================
# Helpers
# =========================================================


def _event(
    state: ProductState = ProductState.CURRENT,
) -> ProductStateEvent:
    """
    Create a representative product-state event.
    """

    return ProductStateEvent(
        artifact_id="example",
        model_name="artwork",
        realization="default",
        stage_name="vector",
        product_name="colors",
        state=state,
    )


# =========================================================
# Event identity
# =========================================================


def test_product_state_event_is_execution_event() -> None:
    """
    Product-state observations participate in the common event contract.
    """

    event = _event()

    assert isinstance(
        event,
        ExecutionEvent,
    )


def test_product_state_event_has_semantic_kind() -> None:
    """
    Product-state observations have one stable semantic event kind.
    """

    event = _event()

    assert event.kind == "product.state"


def test_product_state_event_carries_execution_identity() -> None:
    """
    Product-state events identify the evaluated persistent product.
    """

    event = _event()

    assert event.artifact_id == "example"
    assert event.model_name == "artwork"
    assert event.realization == "default"
    assert event.stage_name == "vector"
    assert event.product_name == "colors"


# =========================================================
# Product state
# =========================================================


@pytest.mark.parametrize(
    "state",
    list(ProductState),
)
def test_product_state_event_carries_typed_state(
    state: ProductState,
) -> None:
    """
    Every product state is represented directly as semantic event data.
    """

    event = _event(
        state,
    )

    assert event.state is state


def test_product_state_is_not_encoded_as_message() -> None:
    """
    Product state remains typed data rather than presentation text.
    """

    event = _event(
        ProductState.STALE,
    )

    assert event.state is ProductState.STALE
    assert event.message is None


# =========================================================
# Value semantics
# =========================================================


def test_product_state_event_is_immutable() -> None:
    """
    Published product-state decisions cannot be mutated by observers.
    """

    event = _event()

    with pytest.raises(
        FrozenInstanceError,
    ):
        event.state = ProductState.STALE  # type: ignore[misc]


def test_product_state_events_compare_by_value() -> None:
    """
    Product-state events support deterministic value comparison.
    """

    assert _event() == _event()


def test_different_product_states_compare_differently() -> None:
    """
    State participates in product-state event value identity.
    """

    assert _event(
        ProductState.CURRENT,
    ) != _event(
        ProductState.STALE,
    )


# =========================================================
# Observation
# =========================================================


def test_product_state_event_uses_common_event_sink() -> None:
    """
    Product-state observations require no specialized observer contract.
    """

    received: list[ExecutionEvent] = []

    sink: EventSink = received.append

    event = _event()

    emit_event(
        sink,
        event,
    )

    assert received == [
        event,
    ]


def test_product_state_event_without_sink_is_noop() -> None:
    """
    Product-state observation remains optional.
    """

    event = _event()

    assert (
        emit_event(
            None,
            event,
        )
        is None
    )


def test_product_state_event_sink_return_value_is_ignored() -> None:
    """
    Observing a state decision cannot control subsequent execution.
    """

    event = _event()

    result = emit_event(
        lambda received: False,
        event,
    )

    assert result is None


# =========================================================
# Presentation independence
# =========================================================


def test_product_state_event_contains_no_presentation_policy() -> None:
    """
    Product-state observations contain no rendering or verbosity policy.
    """

    event = _event()

    assert not hasattr(
        event,
        "verbosity",
    )

    assert not hasattr(
        event,
        "log_level",
    )

    assert not hasattr(
        event,
        "formatted_message",
    )

    assert not hasattr(
        event,
        "progress",
    )
