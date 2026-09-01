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


def _validate_outer_ridge_style(
    resolver: ConfigurationResolver,
) -> None:
    """
    Require outer-ridge style to be one of the supported styles.
    """

    ridge_style = resolver(
        "shape_outer_ridge_style",
    )

    if ridge_style not in (
        "integrated",
        "separate",
    ):
        raise ConfigError("shape_outer_ridge_style must be one of: integrated, separate.")


def _validate_geometry(
    resolver: ConfigurationResolver,
) -> None:
    """
    Require Shape geometry to be one of the supported geometry types.
    """

    geometry = resolver(
        "shape_geometry",
    )

    if geometry not in (
        "circle",
        "square",
        "polygon",
    ):
        raise ConfigError("shape_geometry must be one of: circle, square, polygon.")


def _validate_outer_ridge_width(
    resolver: ConfigurationResolver,
) -> None:
    """
    Require outer-ridge width to be nonnegative.
    """

    ridge_width = resolver(
        "shape_outer_ridge_width",
    )

    if not isinstance(
        ridge_width,
        int | float,
    ):
        raise ConfigError("shape_outer_ridge_width must be numeric.")

    if ridge_width < 0:
        raise ConfigError("shape_outer_ridge_width must be greater than or equal to 0.")


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


def _validate_polygon_sides(
    resolver: ConfigurationResolver,
) -> None:
    """
    Require polygon geometry to use at least three integer sides.
    """

    geometry = resolver(
        "shape_geometry",
    )

    sides = resolver(
        "shape_sides",
    )

    if geometry != "polygon":
        return

    if (
        not isinstance(
            sides,
            int,
        )
        or isinstance(
            sides,
            bool,
        )
        or sides < 3
    ):
        raise ConfigError(
            "shape_sides must be an integer greater than or equal to 3 "
            "when shape_geometry is 'polygon'."
        )


def _validate_outer_ridge_color(
    resolver: ConfigurationResolver,
) -> None:
    """
    Require the outer-ridge color to be a nonempty semantic color name.
    """

    ridge_color = resolver(
        "shape_outer_ridge_color",
    )

    if (
        not isinstance(
            ridge_color,
            str,
        )
        or not ridge_color.strip()
    ):
        raise ConfigError("shape_outer_ridge_color must be a nonempty color name.")


def _validate_base_color(
    resolver: ConfigurationResolver,
) -> None:
    """
    Require the base color to be a nonempty semantic color name.
    """

    base_color = resolver(
        "shape_base_color",
    )

    if (
        not isinstance(
            base_color,
            str,
        )
        or not base_color.strip()
    ):
        raise ConfigError("shape_base_color must be a nonempty color name.")


VALIDATORS = (
    ConfigurationValidator(
        parameters=("shape_geometry",),
        validate=_validate_geometry,
    ),
    ConfigurationValidator(
        parameters=(
            "shape_geometry",
            "shape_sides",
        ),
        validate=_validate_polygon_sides,
    ),
    ConfigurationValidator(
        parameters=(
            "shape_base_raise",
            "shape_outer_ridge_raise",
        ),
        validate=_validate_outer_ridge_raise,
    ),
    ConfigurationValidator(
        parameters=("shape_outer_ridge_width",),
        validate=_validate_outer_ridge_width,
    ),
    ConfigurationValidator(
        parameters=("shape_outer_ridge_style",),
        validate=_validate_outer_ridge_style,
    ),
    ConfigurationValidator(
        parameters=("shape_base_color",),
        validate=_validate_base_color,
    ),
    ConfigurationValidator(
        parameters=("shape_outer_ridge_color",),
        validate=_validate_outer_ridge_color,
    ),
)


__all__ = [
    "VALIDATORS",
]
