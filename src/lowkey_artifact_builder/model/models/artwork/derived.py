"""
Derived configuration values for the artwork model.

Derived values are calculated from resolved artifact configuration.
They are not stored in parameters.toml.

Each derivation receives the artifact Resolver and may consume values
from any resolved configuration scope.

Explicitly configured values take precedence over derivations.
"""
# File: src/lowkey_artifact_builder/model/models/artwork/derived.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lowkey_artifact_builder.config import Resolver


# =========================================================
# Derivations
# =========================================================


def derive_artifact_color_count(
    resolver: Resolver,
) -> int:
    """
    Derive the default Artifact color count from printer capacity.

    Each configured printer color represents an available printer
    position and therefore contributes to the default trace cardinality.

    Duplicate semantic colors are intentional and still represent
    distinct printer positions.

    An explicitly configured artifact_color_count value overrides this
    derivation through normal configuration resolution.
    """

    printer_colors = resolver(
        "printer_colors",
    )

    if not isinstance(
        printer_colors,
        list | tuple,
    ):
        raise ValueError(
            "printer_colors must be a list or tuple.",
        )

    if not printer_colors:
        raise ValueError(
            "printer_colors cannot be empty.",
        )

    for color in printer_colors:
        if (
            not isinstance(
                color,
                str,
            )
            or not color.strip()
        ):
            raise ValueError(
                "printer_colors must contain non-empty color names.",
            )

    return len(printer_colors)


# =========================================================
# Registry
# =========================================================


DERIVED = {
    "artifact_color_count": derive_artifact_color_count,
}


# =========================================================
# Exports
# =========================================================


__all__ = [
    "DERIVED",
    "derive_artifact_color_count",
]
