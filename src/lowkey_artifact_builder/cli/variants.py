"""
Variant-oriented CLI helpers.

Public Variant references are normalized at the CLI boundary to the
decomposed Model and local Variant-name coordinates used by the engine.
"""
# File: src/lowkey_artifact_builder/cli/variants.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import click


def parse_variant_reference(
    reference: str,
) -> tuple[str | None, str]:
    """
    Parse a public Variant reference.

    A bare reference identifies a local Variant name. A qualified
    reference identifies a Model and its local Variant name.
    """

    parts = reference.split(".")

    if len(parts) == 1 and parts[0]:
        return (
            None,
            parts[0],
        )

    if len(parts) == 2 and parts[0] and parts[1]:
        return (
            parts[0],
            parts[1],
        )

    raise click.UsageError(f"Invalid Variant reference: {reference!r}.")


__all__ = [
    "parse_variant_reference",
]
