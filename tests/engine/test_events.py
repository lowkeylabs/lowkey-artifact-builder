"""
Tests for structured execution observation.

Execution events expose semantic execution facts without coupling the
engine to logging, command-line presentation, progress rendering, or
concurrency.

These tests establish the minimal observation contract independently of
build and stage instrumentation.
"""
# File: tests/engine/test_events.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from lowkey_artifact_builder.engine import (
    EventSink,
    ExecutionEvent,
    emit_event,
)

# =========================================================
# Helpers
# =========================================================


def _event() -> ExecutionEvent:
    """
    Create a representative execution event.
    """

    return ExecutionEvent(
        kind="stage.started",
        artifact_id="example",
        model_name="artwork",
        realization="default",
        stage_name="vector",
        product_name=None,
        message=None,
    )


# =========================================================
# Event semantics
# =========================================================


def test_execution_event_carries_semantic_identity() -> None:
    """
    An event carries stable semantic execution identities.
    """

    event = _event()

    assert event.kind == "stage.started"
    assert event.artifact_id == "example"
    assert event.model_name == "artwork"
    assert event.realization == "default"
    assert event.stage_name == "vector"
    assert event.product_name is None
    assert event.message is None


def test_execution_event_allows_partial_identity() -> None:
    """
    Events may describe execution scopes smaller or larger than a stage.
    """

    event = ExecutionEvent(
        kind="build.started",
        artifact_id="example",
    )

    assert event.kind == "build.started"
    assert event.artifact_id == "example"
    assert event.model_name is None
    assert event.realization is None
    assert event.stage_name is None
    assert event.product_name is None
    assert event.message is None


def test_execution_event_allows_product_identity() -> None:
    """
    Product events may identify both their stage and semantic product.
    """

    event = ExecutionEvent(
        kind="product.state",
        artifact_id="example",
        model_name="artwork",
        realization="default",
        stage_name="vector",
        product_name="manifest",
    )

    assert event.stage_name == "vector"
    assert event.product_name == "manifest"


def test_execution_event_is_immutable() -> None:
    """
    Published execution facts cannot be mutated by observers.
    """

    event = _event()

    with pytest.raises(
        FrozenInstanceError,
    ):
        event.stage_name = "raster"  # type: ignore[misc]


def test_execution_events_compare_by_value() -> None:
    """
    Events support deterministic value comparison in tests and consumers.
    """

    assert _event() == _event()


# =========================================================
# Event sink contract
# =========================================================


def test_event_sink_accepts_execution_event() -> None:
    """
    An event sink consumes one structured execution event.
    """

    received: list[ExecutionEvent] = []

    sink: EventSink = received.append

    event = _event()

    sink(
        event,
    )

    assert received == [
        event,
    ]


def test_emit_event_delivers_event_to_sink() -> None:
    """
    Emitting an event delivers the exact event to the observer.
    """

    received: list[ExecutionEvent] = []

    event = _event()

    emit_event(
        received.append,
        event,
    )

    assert received == [
        event,
    ]

    assert received[0] is event


def test_emit_event_without_sink_is_noop() -> None:
    """
    Observation is optional.
    """

    event = _event()

    assert (
        emit_event(
            None,
            event,
        )
        is None
    )


def test_emit_event_returns_none() -> None:
    """
    Event delivery does not participate in execution decisions.
    """

    event = _event()

    result = emit_event(
        lambda received: None,
        event,
    )

    assert result is None


def test_emit_event_does_not_interpret_sink_return_value() -> None:
    """
    Observer return values cannot control engine behavior.
    """

    event = _event()

    result = emit_event(
        lambda received: False,
        event,
    )

    assert result is None


# =========================================================
# Contract independence
# =========================================================


def test_event_contains_no_presentation_state() -> None:
    """
    The minimal event contract contains no CLI presentation policy.
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
