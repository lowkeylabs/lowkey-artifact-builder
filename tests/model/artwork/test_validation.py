"""
Tests for Artwork model configuration validation.

Artwork owns the semantic invariant relating its configured fill color
to its ordered artwork color palette.
"""
# File: tests/model/artwork/test_validation.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import pytest

from lowkey_artifact_builder.config import ConfigError
from lowkey_artifact_builder.model.validation import (
    get_named_model_validators,
    validate_configuration,
)


class StubResolver:
    """
    Minimal resolved-configuration source for Artwork validation tests.
    """

    def __init__(
        self,
        values: dict[str, object],
    ) -> None:
        self._values = values

    def __call__(
        self,
        name: str,
    ) -> object:
        return self._values[name]


def _validate_artwork(
    *,
    colors: object,
    fill_color: object,
) -> None:
    """
    Apply the Artwork model's declared configuration validators.
    """

    resolver = StubResolver(
        {
            "artwork_colors": colors,
            "artwork_fill_color": fill_color,
        }
    )

    validate_configuration(
        resolver,
        validators=get_named_model_validators(
            "artwork",
        ),
    )


def test_artwork_declares_fill_color_membership_validator() -> None:
    """
    Artwork owns a validator governing its palette/fill-color invariant.
    """

    validators = get_named_model_validators(
        "artwork",
    )

    assert tuple(validator.parameters for validator in validators) == (
        (
            "artwork_colors",
            "artwork_fill_color",
        ),
    )


def test_artwork_fill_color_may_be_non_white_palette_member() -> None:
    """
    Artwork accepts an explicitly configured non-white fill color when
    that color belongs to the configured palette.
    """

    _validate_artwork(
        colors=(
            "red",
            "blue",
        ),
        fill_color="red",
    )


def test_artwork_palette_does_not_require_white() -> None:
    """
    White has no special membership requirement in the Artwork palette.
    """

    _validate_artwork(
        colors=(
            "red",
            "blue",
        ),
        fill_color="blue",
    )


def test_artwork_fill_color_must_belong_to_palette() -> None:
    """
    Artwork rejects a resolved fill color absent from artwork_colors.
    """

    with pytest.raises(
        ConfigError,
        match="artwork_fill_color",
    ):
        _validate_artwork(
            colors=(
                "red",
                "blue",
            ),
            fill_color="green",
        )


def test_artwork_default_white_fill_color_is_valid_palette_member() -> None:
    """
    Artwork accepts the default white fill color when white belongs to
    the configured palette.
    """

    _validate_artwork(
        colors=(
            "white",
            "black",
        ),
        fill_color="white",
    )


def test_artwork_fill_color_membership_uses_semantic_color_name() -> None:
    """
    Artwork fill-color membership is determined by semantic color identity.
    """

    with pytest.raises(
        ConfigError,
        match="artwork_fill_color",
    ):
        _validate_artwork(
            colors=(
                "white",
                "black",
            ),
            fill_color="test-white",
        )
