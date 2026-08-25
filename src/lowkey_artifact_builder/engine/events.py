"""
Structured execution observation.

Execution events expose semantic execution facts without coupling the
engine to logging, command-line presentation, progress rendering, or
concurrency.

Observation is optional. Event sinks receive immutable execution events
and cannot influence execution through their return values.

The common event contract may be specialized by typed semantic events.
Concrete build and stage lifecycle instrumentation is introduced
separately.
"""
# File: src/lowkey_artifact_builder/engine/events.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from .state import ProductState

# =========================================================
# Execution events
# =========================================================


@dataclass(
    frozen=True,
    slots=True,
    kw_only=True,
)
class ExecutionEvent:
    """
    One immutable semantic execution observation.

    kind identifies the semantic event type.

    The remaining fields identify the execution scope relevant to the
    event. Fields not applicable to a particular event may remain None.

    message may provide additional semantic explanatory information. It
    is not preformatted terminal output or a logging message.
    """

    kind: str
    artifact_id: str | None = None
    model_name: str | None = None
    realization: str | None = None
    stage_name: str | None = None
    product_name: str | None = None
    message: str | None = None


# =========================================================
# Product-state events
# =========================================================


@dataclass(
    frozen=True,
    slots=True,
    kw_only=True,
)
class ProductStateEvent(ExecutionEvent):
    """
    Structured observation of one persistent product-state decision.

    Product state is carried as typed semantic data rather than encoded
    into a message or another presentation-oriented field.
    """

    state: ProductState

    kind: str = field(
        default="product.state",
        init=False,
    )


# =========================================================
# Observation contract
# =========================================================


type EventSink = Callable[
    [ExecutionEvent],
    object,
]


def emit_event(
    sink: EventSink | None,
    event: ExecutionEvent,
) -> None:
    """
    Deliver one execution event to an optional observer.

    Observation is a side channel only. The observer's return value is
    deliberately ignored and cannot participate in execution decisions.
    """

    if sink is None:
        return

    sink(
        event,
    )


# =========================================================
# Exports
# =========================================================


__all__ = [
    "EventSink",
    "ExecutionEvent",
    "ProductStateEvent",
    "emit_event",
]
