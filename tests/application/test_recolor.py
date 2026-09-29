"""
Tests for reusable printer-color reconciliation.
"""

# File: tests/application/test_recolor.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import pytest

from lowkey_artifact_builder.application.recolor import (
    PrinterColorReconciliationError,
    reconcile_printer_colors,
)


def test_reconcile_printer_colors_replaces_first_unneeded_slot() -> None:
    """
    Missing required colors replace unneeded installed colors beginning with
    the first available physical printer slot.

    Required colors already installed retain their existing physical slots,
    and unrelated slots remain unchanged when no replacement is needed there.
    """

    current_printer_colors = (
        "black",
        "blue",
        "white",
        "silver",
        "brown",
    )

    required_colors = (
        "black",
        "fire-engine-red",
        "white",
    )

    result = reconcile_printer_colors(
        current_printer_colors,
        required_colors,
    )

    assert result == (
        "black",
        "fire-engine-red",
        "white",
        "silver",
        "brown",
    )


def test_reconcile_printer_colors_preserves_installed_required_colors_regardless_of_order() -> None:
    """
    Required-color ordering does not rearrange colors that are already
    installed.

    When every required color is already present, reconciliation requires no
    filament changes and therefore returns the existing physical printer-slot
    arrangement unchanged.
    """

    current_printer_colors = (
        "black",
        "blue",
        "white",
        "silver",
        "brown",
    )

    required_colors = (
        "brown",
        "white",
        "black",
    )

    result = reconcile_printer_colors(
        current_printer_colors,
        required_colors,
    )

    assert result == current_printer_colors


def test_reconcile_printer_colors_replaces_multiple_unneeded_slots_from_first_to_last() -> None:
    """
    Multiple missing required colors replace unneeded installed colors in
    physical printer-slot order.

    Existing required colors remain fixed while missing required colors are
    installed into the earliest replaceable slots.
    """

    current_printer_colors = (
        "black",
        "blue",
        "white",
        "silver",
        "brown",
    )

    required_colors = (
        "black",
        "fire-engine-red",
        "white",
        "orange",
    )

    result = reconcile_printer_colors(
        current_printer_colors,
        required_colors,
    )

    assert result == (
        "black",
        "fire-engine-red",
        "white",
        "orange",
        "brown",
    )


def test_reconcile_printer_colors_rejects_more_required_colors_than_slots() -> None:
    """
    Reconciliation rejects a required palette that cannot physically fit on
    the printer rather than changing printer-slot cardinality.
    """

    with pytest.raises(
        PrinterColorReconciliationError,
        match="exceed the available physical printer slots",
    ):
        reconcile_printer_colors(
            (
                "black",
                "blue",
                "white",
                "silver",
                "brown",
            ),
            (
                "black",
                "white",
                "red",
                "orange",
                "green",
                "yellow",
            ),
        )


def test_reconcile_printer_colors_rejects_duplicate_required_colors() -> None:
    """
    Required physical colors are a set of distinct filament requirements.

    Duplicate requirements would make slot reconciliation ambiguous and do
    not represent a valid upstream one-to-one color assignment.
    """

    with pytest.raises(
        ValueError,
        match="Required printer colors must be distinct",
    ):
        reconcile_printer_colors(
            (
                "black",
                "blue",
                "white",
                "silver",
                "brown",
            ),
            (
                "black",
                "white",
                "black",
            ),
        )


def test_reconcile_printer_colors_rejects_unreconcilable_installed_slots() -> None:
    """
    Required colors that fit printer capacity but cannot be reconciled with
    the installed slot state are an expected recolor-domain failure.
    """

    with pytest.raises(
        PrinterColorReconciliationError,
    ):
        reconcile_printer_colors(
            (
                "Black",
                "Black",
            ),
            (
                "Black",
                "White",
            ),
        )
