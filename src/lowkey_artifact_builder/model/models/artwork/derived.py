"""
Derived configuration values for the artwork model.

Derived values are calculated from resolved artifact configuration.
They are not stored in parameters.toml.

Each derivation receives the artifact Resolver and may consume values
from any resolved configuration scope.

Explicitly configured values take precedence over derivations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lowkey_artifact_builder.config import Resolver


# =========================================================
# Derivations
# =========================================================


def derive_artwork_colors(
    resolver: Resolver,
) -> int:
    """
    Derive the number of artwork colors available for tracing.

    Each configured printer color represents one available printer
    color position. Duplicate colors are intentional and therefore
    count independently.

    For example:

        printer_colors = [
            "black",
            "white",
            "red",
            "red",
        ]

    produces:

        artwork_colors = 4
    """

    printer_colors = resolver("printer_colors")

    if not isinstance(
        printer_colors,
        list | tuple,
    ):
        raise ValueError("printer_colors must be a list or tuple.")

    if not printer_colors:
        raise ValueError("printer_colors cannot be empty.")

    return len(printer_colors)


# =========================================================
# Registry
# =========================================================


DERIVED = {
    "artwork_colors": derive_artwork_colors,
}


# =========================================================
# Exports
# =========================================================


__all__ = [
    "DERIVED",
    "derive_artwork_colors",
]
