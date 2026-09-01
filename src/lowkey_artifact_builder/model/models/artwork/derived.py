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

from lowkey_artifact_builder.colors import (
    PaletteColor,
    match_color,
    resolve_palette,
)

if TYPE_CHECKING:
    from lowkey_artifact_builder.config import Resolver


# =========================================================
# Derivations
# =========================================================


def derive_artwork_colors(
    resolver: Resolver,
) -> tuple[str, ...]:
    """
    Derive artwork colors from the configured printer colors.

    By default, artwork may use every color configured for the printer.

    Printer color order is preserved.

    Duplicate printer colors are intentional and are also preserved.
    For example:

        printer_colors = [
            "black",
            "white",
            "red",
            "red",
        ]

    produces:

        artwork_colors = (
            "black",
            "white",
            "red",
            "red",
        )

    An explicitly configured artwork_colors value overrides this
    derivation through normal configuration resolution.
    """

    printer_colors = resolver(
        "printer_colors",
    )

    if not isinstance(
        printer_colors,
        list | tuple,
    ):
        raise ValueError("printer_colors must be a list or tuple.")

    if not printer_colors:
        raise ValueError("printer_colors cannot be empty.")

    colors: list[str] = []

    for color in printer_colors:
        if (
            not isinstance(
                color,
                str,
            )
            or not color.strip()
        ):
            raise ValueError("printer_colors must contain non-empty color names.")

        colors.append(
            color.strip(),
        )

    return tuple(colors)


def derive_artwork_fill_color(
    resolver: Resolver,
) -> str:
    """
    Derive the Artwork fill color from configured printer colors.

    The default fill is the configured printer color perceptually
    closest to ideal RGB white.

    Matching uses the shared generic color infrastructure. The selected
    printer color's semantic identity is preserved.

    Duplicate printer colors are collapsed for matching because multiple
    printer heads may intentionally contain the same semantic color.
    First-occurrence printer order is preserved, providing deterministic
    selection when candidates have equal perceptual distance.

    An explicitly configured artwork_fill_color value overrides this
    derivation through normal configuration resolution.
    """

    printer_colors = derive_artwork_colors(
        resolver,
    )

    candidate_names = tuple(
        dict.fromkeys(
            printer_colors,
        )
    )

    candidates = resolve_palette(
        candidate_names,
        resolver.colors,
    )

    ideal_white = PaletteColor(
        name="ideal-white",
        rgb=(255, 255, 255),
    )

    match = match_color(
        ideal_white,
        candidates,
    )

    return match.color.name


# =========================================================
# Registry
# =========================================================


DERIVED = {
    "artwork_colors": derive_artwork_colors,
    "artwork_fill_color": derive_artwork_fill_color,
}


# =========================================================
# Exports
# =========================================================


__all__ = [
    "DERIVED",
    "derive_artwork_colors",
    "derive_artwork_fill_color",
]
