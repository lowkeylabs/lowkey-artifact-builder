"""
Tests for model-owned configuration validation.
"""
# File: tests/model/test_validation.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import pytest

from lowkey_artifact_builder.config import ConfigError
from lowkey_artifact_builder.model.validation import (
    ConfigurationResolver,
    validate_configuration,
)

# =========================================================
# Test support
# =========================================================


class StubResolver:
    """
    Minimal resolved-configuration source for validation tests.
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


def _require_string(
    value: object,
) -> str:
    """
    Narrow a resolved test value to a string.
    """

    if not isinstance(value, str):
        raise TypeError("Expected a string.")

    return value


def _require_string_collection(
    value: object,
) -> tuple[str, ...]:
    """
    Narrow a resolved test value to a collection of strings.
    """

    if not isinstance(value, list | tuple):
        raise TypeError("Expected a list or tuple.")

    if not all(isinstance(item, str) for item in value):
        raise TypeError("Expected only strings.")

    return tuple(value)


# =========================================================
# Model validation
# =========================================================


def test_model_with_no_validators_is_valid() -> None:
    """
    Models are not required to define configuration validators.
    """

    resolver = StubResolver({})

    validate_configuration(
        resolver,
        validators=(),
    )


def test_model_validator_can_inspect_multiple_resolved_values() -> None:
    """
    Model validators may express cross-parameter invariants.
    """

    observed: list[tuple[object, object]] = []

    def validate_pair(
        resolver: ConfigurationResolver,
    ) -> None:
        observed.append(
            (
                resolver("left"),
                resolver("right"),
            )
        )

    resolver = StubResolver(
        {
            "left": "alpha",
            "right": "beta",
        }
    )

    validate_configuration(
        resolver,
        validators=(validate_pair,),
    )

    assert observed == [
        (
            "alpha",
            "beta",
        )
    ]


def test_valid_model_configuration_passes_validation() -> None:
    """
    A satisfied model invariant allows validation to complete.
    """

    def validate_membership(
        resolver: ConfigurationResolver,
    ) -> None:
        selected = _require_string(
            resolver("selected"),
        )
        allowed = _require_string_collection(
            resolver("allowed"),
        )

        if selected not in allowed:
            raise ConfigError("selected must belong to allowed.")

    resolver = StubResolver(
        {
            "selected": "red",
            "allowed": ("red", "blue"),
        }
    )

    validate_configuration(
        resolver,
        validators=(validate_membership,),
    )


def test_invalid_model_configuration_raises_config_error() -> None:
    """
    A violated model invariant fails configuration validation.
    """

    def validate_membership(
        resolver: ConfigurationResolver,
    ) -> None:
        selected = _require_string(
            resolver("selected"),
        )
        allowed = _require_string_collection(
            resolver("allowed"),
        )

        if selected not in allowed:
            raise ConfigError("selected must belong to allowed.")

    resolver = StubResolver(
        {
            "selected": "green",
            "allowed": ("red", "blue"),
        }
    )

    with pytest.raises(
        ConfigError,
        match="selected must belong to allowed",
    ):
        validate_configuration(
            resolver,
            validators=(validate_membership,),
        )
