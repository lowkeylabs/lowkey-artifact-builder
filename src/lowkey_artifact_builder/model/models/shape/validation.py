"""
Shape model configuration validation.

Shape configuration validators express semantic invariants owned by
the Shape model.
"""
# File: src/lowkey_artifact_builder/model/models/shape/validation.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from lowkey_artifact_builder.config import ConfigError
from lowkey_artifact_builder.model.validation import (
    ConfigurationResolver,
    ConfigurationValidator,
)


def _validate_outer_ridge_raise(
    resolver: ConfigurationResolver,
) -> None:
    """
    Require the outer-ridge top to remain at or above the base bottom.
    """

    base_raise = resolver(
        "shape_base_raise",
    )

    ridge_raise = resolver(
        "shape_outer_ridge_raise",
    )

    if not isinstance(
        base_raise,
        int | float,
    ):
        raise ConfigError("shape_base_raise must be numeric.")

    if not isinstance(
        ridge_raise,
        int | float,
    ):
        raise ConfigError("shape_outer_ridge_raise must be numeric.")

    if ridge_raise < -base_raise:
        raise ConfigError(
            "shape_outer_ridge_raise must be greater than or equal to -shape_base_raise."
        )


VALIDATORS = (
    ConfigurationValidator(
        parameters=(
            "shape_base_raise",
            "shape_outer_ridge_raise",
        ),
        validate=_validate_outer_ridge_raise,
    ),
)


__all__ = [
    "VALIDATORS",
]
