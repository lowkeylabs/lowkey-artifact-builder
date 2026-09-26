"""
Semantic application messaging.

Semantic messaging presents structured application and execution facts to
an operator without coupling those facts to diagnostic logging or a
particular execution engine.

Messaging verbosity is application policy:

    quiet        suppress semantic messages
    normal       present routine results
    verbose      present manufacturing progress
    very verbose present semantic execution diagnostics

Python diagnostic logging is configured independently.
"""
# File: src/lowkey_artifact_builder/messaging.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from .engine import (
    ExecutionEvent,
    ProductStateEvent,
)

# =========================================================
# Semantic verbosity
# =========================================================


QUIET = -1
NORMAL = 0
VERBOSE = 1
VERY_VERBOSE = 2


# =========================================================
# Message sink
# =========================================================


type MessageSink = Callable[
    [str],
    object,
]


# =========================================================
# Paths
# =========================================================


def display_path(
    path: Path,
    *,
    project_root: Path,
) -> str:
    """
    Return an operator-facing filesystem path.

    Paths within the project are displayed relative to the project root.
    Paths outside the project remain absolute.
    """

    try:
        return str(
            path.relative_to(
                project_root,
            )
        )
    except ValueError:
        return str(path)


# =========================================================
# Semantic messenger
# =========================================================


class SemanticMessenger:
    """
    Present structured semantic application messages.

    The messenger owns semantic verbosity policy and translation of
    structured execution events into operator-facing terminology.

    It does not configure or emit Python diagnostic logging.
    """

    def __init__(
        self,
        *,
        verbosity: int = NORMAL,
        sink: MessageSink,
    ) -> None:
        self._verbosity = verbosity
        self._sink = sink

    @property
    def verbosity(self) -> int:
        """
        Return the configured semantic verbosity.
        """

        return self._verbosity

    def message(
        self,
        message: str,
        *,
        verbosity: int = NORMAL,
    ) -> None:
        """
        Present one semantic message when its verbosity is enabled.
        """

        if self._verbosity < verbosity:
            return

        self._sink(
            message,
        )

    def execution_event(
        self,
        event: ExecutionEvent,
    ) -> None:
        """
        Present one structured execution event according to verbosity.

        Normal semantic output does not narrate execution events.

        Verbose output presents manufacturing progress and reuse.

        Very-verbose output additionally presents typed Product-state
        diagnostics.
        """

        if self._verbosity < VERBOSE:
            return

        if isinstance(
            event,
            ProductStateEvent,
        ):
            if self._verbosity < VERY_VERBOSE:
                return

            self._display_product_state(
                event,
            )
            return

        if event.kind == "stage.started":
            self.message(
                f"{event.stage_name} executing",
                verbosity=VERBOSE,
            )
            return

        if event.kind == "stage.completed":
            self.message(
                f"{event.stage_name} completed",
                verbosity=VERBOSE,
            )
            return

        if event.kind == "stage.skipped":
            self.message(
                f"{event.stage_name} reused",
                verbosity=VERBOSE,
            )
            return

        if event.kind == "stage.failed":
            self.message(
                f"{event.stage_name} failed",
                verbosity=VERBOSE,
            )

    def _display_product_state(
        self,
        event: ProductStateEvent,
    ) -> None:
        """
        Present one typed persistent Product-state observation.
        """

        scope = event.stage_name or event.product_name or "product"

        self.message(
            f"{scope} state: {event.state.value}",
            verbosity=VERY_VERBOSE,
        )


# =========================================================
# Exports
# =========================================================


__all__ = [
    "MessageSink",
    "NORMAL",
    "QUIET",
    "SemanticMessenger",
    "VERBOSE",
    "VERY_VERBOSE",
    "display_path",
]
