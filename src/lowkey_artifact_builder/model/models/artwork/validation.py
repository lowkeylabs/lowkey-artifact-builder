"""
Artwork model configuration validation.

Artwork configuration validators express semantic invariants owned by
the Artwork model.
"""
# File: src/lowkey_artifact_builder/model/models/artwork/validation.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from lowkey_artifact_builder.config import ConfigError
from lowkey_artifact_builder.model.validation import (
    ConfigurationResolver,
    ConfigurationValidator,
)


def _validate_fill_color_membership(
    resolver: ConfigurationResolver,
) -> None:
    """
    Require artwork_fill_color to belong to artwork_colors.
    """

    colors = resolver(
        "artwork_colors",
    )

    fill_color = resolver(
        "artwork_fill_color",
    )

    if not isinstance(
        fill_color,
        str,
    ):
        raise ConfigError("artwork_fill_color must be a color name.")

    if not isinstance(
        colors,
        list | tuple,
    ) or not all(isinstance(color, str) for color in colors):
        raise ConfigError("artwork_colors must be a sequence of color names.")

    if fill_color not in colors:
        raise ConfigError("artwork_fill_color must be present in artwork_colors.")


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


VALIDATORS = (
    ConfigurationValidator(
        parameters=(
            "artwork_colors",
            "artwork_fill_color",
        ),
        validate=_validate_fill_color_membership,
    ),
    ConfigurationValidator(
        parameters=("artwork_envelope_mode",),
        validate=_validate_envelope_mode,
    ),
)


__all__ = [
    "VALIDATORS",
]
