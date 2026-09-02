"""
Artwork model configuration validation.

Artwork configuration validators express semantic invariants owned by
the Artwork model.
"""
# File: src/lowkey_artifact_builder/model/models/artwork/validation.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import Protocol, runtime_checkable

from lowkey_artifact_builder.config import ConfigError
from lowkey_artifact_builder.model.validation import (
    ConfigurationResolver,
    ConfigurationValidator,
)


@runtime_checkable
class _ColorCatalogResolver(Protocol):
    """
    Resolver capability providing shared color catalog membership.
    """

    def has_color(
        self,
        name: str,
    ) -> bool: ...


def _require_color_catalog(
    resolver: ConfigurationResolver,
) -> _ColorCatalogResolver:
    """
    Require color catalog access for color-availability validation.
    """

    if not isinstance(
        resolver,
        _ColorCatalogResolver,
    ):
        raise TypeError("Artwork color availability validation requires color catalog access.")

    return resolver


def _validate_artifact_color_count(
    resolver: ConfigurationResolver,
) -> None:
    """
    Require artifact_color_count to be a positive integer.
    """

    color_count = resolver(
        "artifact_color_count",
    )

    if (
        not isinstance(
            color_count,
            int,
        )
        or isinstance(
            color_count,
            bool,
        )
        or color_count <= 0
    ):
        raise ConfigError("artifact_color_count must be a positive integer.")


def _validate_envelope_mode(
    resolver: ConfigurationResolver,
) -> None:
    """
    Require a supported Artwork envelope derivation mode.
    """

    envelope_mode = resolver(
        "artwork_envelope_mode",
    )

    if not isinstance(
        envelope_mode,
        str,
    ):
        raise ConfigError("artwork_envelope_mode must be a mode name.")

    if envelope_mode not in (
        "alpha",
        "shrink-wrap",
    ):
        raise ConfigError("artwork_envelope_mode must be 'alpha' or 'shrink-wrap'.")


def _validate_printer_colors(
    resolver: ConfigurationResolver,
) -> None:
    """
    Require printer_colors to reference known catalog colors.
    """

    colors = resolver(
        "printer_colors",
    )

    if not isinstance(
        colors,
        list | tuple,
    ) or not all(
        isinstance(
            color,
            str,
        )
        for color in colors
    ):
        raise ConfigError("printer_colors must be a sequence of color names.")

    catalog = _require_color_catalog(
        resolver,
    )

    unknown_colors = tuple(
        color
        for color in colors
        if not catalog.has_color(
            color,
        )
    )

    if unknown_colors:
        raise ConfigError(
            "printer_colors must reference known catalog colors: "
            + ", ".join(repr(color) for color in unknown_colors)
            + "."
        )


def _validate_library_colors(
    resolver: ConfigurationResolver,
) -> None:
    """
    Require library_colors to reference known catalog colors.
    """

    colors = resolver(
        "library_colors",
    )

    if not isinstance(
        colors,
        list | tuple,
    ) or not all(
        isinstance(
            color,
            str,
        )
        for color in colors
    ):
        raise ConfigError("library_colors must be a sequence of color names.")

    catalog = _require_color_catalog(
        resolver,
    )

    unknown_colors = tuple(
        color
        for color in colors
        if not catalog.has_color(
            color,
        )
    )

    if unknown_colors:
        raise ConfigError(
            "library_colors must reference known catalog colors: "
            + ", ".join(repr(color) for color in unknown_colors)
            + "."
        )


VALIDATORS = (
    ConfigurationValidator(
        parameters=("artifact_color_count",),
        validate=_validate_artifact_color_count,
    ),
    ConfigurationValidator(
        parameters=("artwork_envelope_mode",),
        validate=_validate_envelope_mode,
    ),
    ConfigurationValidator(
        parameters=("printer_colors",),
        validate=_validate_printer_colors,
    ),
    ConfigurationValidator(
        parameters=("library_colors",),
        validate=_validate_library_colors,
    ),
)


__all__ = [
    "VALIDATORS",
]
