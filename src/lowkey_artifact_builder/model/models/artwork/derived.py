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
    Derive the artwork fill color.

    White is the default physical fill/background color when it is
    available in the artwork palette.

    The fill color is used to receive any unassigned geometry inside
    the artwork envelope.
    """

    artwork_colors = resolver("artwork_colors")

    if not isinstance(
        artwork_colors,
        list | tuple,
    ):
        raise ValueError("artwork_colors must be a list or tuple.")

    if not artwork_colors:
        raise ValueError("artwork_colors cannot be empty.")

    for color in artwork_colors:
        if color == "white":
            return color

    raise ValueError("artwork_colors must contain 'white' to derive artwork_fill_color.")


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
