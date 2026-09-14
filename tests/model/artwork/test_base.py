"""
Tests for Artwork Base Feature configuration and participation.

Base is an optional standalone Artwork Feature. Its participation is
determined by the effective artwork_base_raise rather than by a separate
boolean Feature-selection mechanism.
"""
# File: tests/model/artwork/test_base.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path

import pytest

from lowkey_artifact_builder.config import (
    ConfigError,
    get_resolver,
    write_artifact_config,
)
from lowkey_artifact_builder.model.validation import (
    get_named_model_validators,
    validate_configuration,
)


class StubResolver:
    """
    Minimal resolved-configuration source for Base validation tests.
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


def _validate_base(
    *,
    raise_: object = 0.0,
) -> None:
    """
    Apply Artwork validators relevant to Base configuration.
    """

    resolver = StubResolver(
        {
            "artwork_base_raise": raise_,
        }
    )

    validators = tuple(
        validator
        for validator in get_named_model_validators("artwork")
        if "artwork_base_raise" in validator.parameters
    )

    validate_configuration(
        resolver,
        validators=validators,
    )


# =========================================================
# Configuration resolution
# =========================================================


def test_base_parameters_are_artwork_parameters(
    tmp_path: Path,
) -> None:
    """
    Base configuration uses ordinary Artwork parameters.

    Base raise has a Model default. Base color may instead be supplied
    explicitly or resolved later from Registered Artwork and Loop state.
    """

    resolver = get_resolver(
        "example",
        model="artwork",
        project_root=tmp_path,
    )

    assert resolver("artwork_base_raise") is not None
    assert not resolver.has("artwork_base_color")


def test_base_is_disabled_by_default(
    tmp_path: Path,
) -> None:
    """
    Ordinary Artwork does not participate in the Base Feature.

    Participation is disabled by an effective Base raise of zero.
    """

    resolver = get_resolver(
        "example",
        model="artwork",
        project_root=tmp_path,
    )

    assert resolver("artwork_base_raise") == 0.0


def test_ordinary_artwork_realization_may_customize_base(
    tmp_path: Path,
) -> None:
    """
    An Artifact may enable and configure Base directly on an ordinary
    Artwork Realization without requiring a specialized Variant.
    """

    write_artifact_config(
        "example",
        {
            "realizations": {
                "custom": {
                    "model": "artwork",
                    "variant": "default",
                    "parameters": {
                        "artwork_base_raise": 1.5,
                        "artwork_base_color": "black",
                    },
                },
            },
        },
        project_root=tmp_path,
    )

    resolver = get_resolver(
        "example",
        realization="custom",
        project_root=tmp_path,
    )

    assert resolver("model") == "artwork"
    assert resolver("variant") == "default"

    assert resolver("artwork_base_raise") == 1.5
    assert resolver("artwork_base_color") == "black"


# =========================================================
# Participation and validation
# =========================================================


def test_zero_base_raise_is_valid_and_disables_base() -> None:
    """
    Zero Base raise is the defined disabled state for Base.
    """

    _validate_base(
        raise_=0.0,
    )


@pytest.mark.parametrize(
    "raise_",
    [
        0.1,
        1.0,
        2.5,
    ],
)
def test_positive_base_raise_is_valid_and_enables_base(
    raise_: float,
) -> None:
    """
    Base participates for any positive physical Base raise.
    """

    _validate_base(
        raise_=raise_,
    )


@pytest.mark.parametrize(
    "raise_",
    [
        -0.1,
        -1.0,
    ],
)
def test_negative_base_raise_is_invalid(
    raise_: float,
) -> None:
    """
    Base physical raise cannot be negative.
    """

    with pytest.raises(
        ConfigError,
        match="artwork_base_raise",
    ):
        _validate_base(
            raise_=raise_,
        )
