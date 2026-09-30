"""
Reusable printer-color reconciliation.

This module owns application-level recolor policy used to translate a set of
required physical colors into the printer's existing physical color slots.

The current printer_colors sequence represents the colors physically installed
on the printer, in printer-slot order.

Reconciliation minimizes filament changes:

1. Required colors already installed remain in their existing slots.
2. Missing required colors replace colors that are not required.
3. Replacement begins with the first available printer slot.
4. Printer slots that do not need to change remain unchanged.
5. The number and order of physical printer slots are preserved.

This module does not perform color assignment. Model color analysis determines
which physical colors are required. This module only reconciles those selected
colors with the printer's current physical state.

This module does not read or write configuration. Persistence belongs to the
calling workflow. In particular, recolor mutations are persisted in an
Artifact's artifact.toml at Artifact or Realization scope, never in system
parameters.toml.
"""

# File: src/lowkey_artifact_builder/application/recolor.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations


class PrinterColorReconciliationError(ValueError):
    """
    Required physical colors cannot be reconciled with printer color slots.
    """


def reconcile_printer_colors(
    current_printer_colors: tuple[str, ...],
    required_colors: tuple[str, ...],
) -> tuple[str, ...]:
    """
    Reconcile required physical colors with the printer's installed colors.

    ``current_printer_colors`` represents physical printer slots in slot order.

    ``required_colors`` represents the physical colors selected for the
    Artifact by upstream color analysis. Their order does not represent printer
    slot order.

    A required color already installed remains in its existing slot. Each
    missing required color replaces the first installed color whose slot is not
    required by the Artifact.

    Slots that are not needed for a replacement remain unchanged. The returned
    tuple therefore has exactly the same cardinality and physical slot ordering
    as ``current_printer_colors``, except for the minimum replacements needed
    to make every required color available.

    Raises:
        PrinterColorReconciliationError:
            If the required colors exceed the available physical printer slots
            or cannot be reconciled with the installed physical printer slots.
        ValueError:
            If required_colors contains duplicate physical colors.
    """

    if len(set(required_colors)) != len(required_colors):
        raise ValueError("Required printer colors must be distinct.")

    if len(required_colors) > len(current_printer_colors):
        raise PrinterColorReconciliationError(
            "Required printer colors exceed the available physical printer slots."
        )

    required = set(
        required_colors,
    )

    installed = set(
        current_printer_colors,
    )

    missing = [color for color in required_colors if color not in installed]

    if not missing:
        return current_printer_colors

    preserved_required: set[str] = set()

    replaceable_slots: list[int] = []

    for index, color in enumerate(current_printer_colors):
        if color in required and color not in preserved_required:
            preserved_required.add(color)
            continue

        replaceable_slots.append(index)

    if len(replaceable_slots) < len(missing):
        raise PrinterColorReconciliationError(
            "Required printer colors cannot be reconciled with the available "
            "physical printer slots."
        )

    reconciled = list(
        current_printer_colors,
    )

    for index, color in zip(
        replaceable_slots,
        missing,
        strict=False,
    ):
        reconciled[index] = color

    return tuple(
        reconciled,
    )


__all__ = [
    "PrinterColorReconciliationError",
    "reconcile_printer_colors",
]
