"""
Tests for execution event sink behavior.

Event sinks are optional observers of engine execution. Observer failure
must not alter the engine operation being observed.
"""
# File: tests/engine/test_events_sink.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from lowkey_artifact_builder.engine.events import (
    ExecutionEvent,
    emit_event,
)

# =========================================================
# Event sink behavior
# =========================================================


def _event() -> ExecutionEvent:
    """
    Return a representative execution event.
    """

    return ExecutionEvent(
        kind="build.started",
        artifact_id="example",
        model_name="artwork",
        realization="default",
    )


def test_emit_event_accepts_no_sink() -> None:
    """
    Missing observation is a supported no-op.
    """

    emit_event(
        None,
        _event(),
    )


def test_emit_event_delivers_event_to_sink() -> None:
    """
    Event delivery supplies the original event to the observer.
    """

    event = _event()

    observed: list[ExecutionEvent] = []

    emit_event(
        observed.append,
        event,
    )

    assert observed == [
        event,
    ]


def test_emit_event_suppresses_sink_failure() -> None:
    """
    Observer failure does not propagate through engine execution.
    """

    event = _event()

    class ObserverFailure(Exception):
        """
        Expected observer failure.
        """

    def fail(
        observed: ExecutionEvent,
    ) -> None:
        assert observed is event

        raise ObserverFailure("observer failed")

    emit_event(
        fail,
        event,
    )


def test_emit_event_attempts_only_one_delivery() -> None:
    """
    Failed observation is not retried by the event boundary.
    """

    event = _event()

    attempts = 0

    def fail(
        observed: ExecutionEvent,
    ) -> None:
        nonlocal attempts

        assert observed is event

        attempts += 1

        raise RuntimeError("observer failed")

    emit_event(
        fail,
        event,
    )

    assert attempts == 1
