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


def _validate_loop_inner_diameter(
    resolver: ConfigurationResolver,
) -> None:
    """
    Require Loop inner diameter to be disabled or physically usable.

    Zero disables Loop participation. A participating Loop requires an
    inner diameter of at least 0.5 mm.
    """

    inner_diameter = resolver(
        "loop_inner_diameter",
    )

    if not isinstance(
        inner_diameter,
        int | float,
    ) or isinstance(
        inner_diameter,
        bool,
    ):
        raise ConfigError(
            "loop_inner_diameter must be a number.",
        )

    if inner_diameter < 0:
        raise ConfigError(
            "loop_inner_diameter cannot be negative.",
        )

    if 0 < inner_diameter < 0.5:
        raise ConfigError(
            "loop_inner_diameter must be zero or at least 0.5 mm.",
        )


def _validate_loop_width(
    resolver: ConfigurationResolver,
) -> None:
    """
    Require positive radial material width for a participating Loop.
    """

    inner_diameter = resolver(
        "loop_inner_diameter",
    )
    width = resolver(
        "loop_width",
    )

    if inner_diameter == 0:
        return

    if (
        not isinstance(
            width,
            int | float,
        )
        or isinstance(
            width,
            bool,
        )
        or width <= 0
    ):
        raise ConfigError(
            "loop_width must be positive when Loop participates.",
        )


def _validate_loop_position(
    resolver: ConfigurationResolver,
) -> None:
    """
    Require Loop attachment at one of Artwork's cardinal positions.
    """

    inner_diameter = resolver(
        "loop_inner_diameter",
    )

    if inner_diameter == 0:
        return

    position = resolver(
        "loop_position",
    )

    if (
        not isinstance(
            position,
            int,
        )
        or isinstance(
            position,
            bool,
        )
        or position
        not in (
            0,
            90,
            180,
            -90,
        )
    ):
        raise ConfigError(
            "loop_position must be one of 0, 90, 180, or -90.",
        )


def _validate_artwork_hole_diameter(
    resolver: ConfigurationResolver,
) -> None:
    """
    Require Artwork Hole diameter to be nonnegative.

    Zero disables Hole participation. Any positive value enables Hole
    participation and determines the physical diameter of the opening.
    """

    diameter = resolver(
        "artwork_hole_diameter",
    )

    if not isinstance(
        diameter,
        int | float,
    ) or isinstance(
        diameter,
        bool,
    ):
        raise ConfigError(
            "artwork_hole_diameter must be a number.",
        )

    if diameter < 0:
        raise ConfigError(
            "artwork_hole_diameter cannot be negative.",
        )


def _validate_artwork_hole_edge_distance(
    resolver: ConfigurationResolver,
) -> None:
    """
    Require minimum remaining material for a participating Hole.

    A participating Hole must leave at least 0.4 mm between the Hole
    edge and the applicable outer Artwork boundary.
    """

    diameter = resolver(
        "artwork_hole_diameter",
    )

    if diameter == 0:
        return

    edge_distance = resolver(
        "artwork_hole_edge_distance",
    )

    if (
        not isinstance(
            edge_distance,
            int | float,
        )
        or isinstance(
            edge_distance,
            bool,
        )
        or edge_distance < 0.4
    ):
        raise ConfigError(
            "artwork_hole_edge_distance must be at least 0.4 mm when Hole participates.",
        )


def _validate_artwork_hole_position(
    resolver: ConfigurationResolver,
) -> None:
    """
    Require a participating Hole at one of Artwork's cardinal positions.
    """

    diameter = resolver(
        "artwork_hole_diameter",
    )

    if diameter == 0:
        return

    position = resolver(
        "artwork_hole_position",
    )

    if (
        not isinstance(
            position,
            int,
        )
        or isinstance(
            position,
            bool,
        )
        or position
        not in (
            0,
            90,
            180,
            -90,
        )
    ):
        raise ConfigError(
            "artwork_hole_position must be one of 0, 90, 180, or -90.",
        )


def _validate_artwork_base_raise(
    resolver: ConfigurationResolver,
) -> None:
    """
    Require Artwork Base raise to be nonnegative.

    Zero disables Base participation. A positive value enables Base and
    determines its physical height.
    """

    base_raise = resolver(
        "artwork_base_raise",
    )

    if not isinstance(
        base_raise,
        int | float,
    ) or isinstance(
        base_raise,
        bool,
    ):
        raise ConfigError(
            "artwork_base_raise must be a number.",
        )

    if base_raise < 0:
        raise ConfigError(
            "artwork_base_raise cannot be negative.",
        )


def _validate_artwork_outer_ridge_width(
    resolver: ConfigurationResolver,
) -> None:
    """
    Require Artwork Outer Ridge width to be physically valid.

    Zero disables Outer Ridge participation. A positive value enables
    Outer Ridge and reserves that width around the size-controlling
    Artwork extent.

    A participating Outer Ridge must leave a positive Artwork interior,
    so twice the ridge width must be strictly less than artwork_size.
    """

    ridge_width = resolver(
        "artwork_outer_ridge_width",
    )

    if not isinstance(
        ridge_width,
        int | float,
    ) or isinstance(
        ridge_width,
        bool,
    ):
        raise ConfigError(
            "artwork_outer_ridge_width must be a number.",
        )

    if ridge_width < 0:
        raise ConfigError(
            "artwork_outer_ridge_width cannot be negative.",
        )

    if ridge_width == 0:
        return

    artwork_size = resolver(
        "artwork_size",
    )

    if not isinstance(
        artwork_size,
        int | float,
    ) or isinstance(
        artwork_size,
        bool,
    ):
        raise ConfigError(
            "artwork_size must be a number.",
        )

    if 2.0 * ridge_width >= artwork_size:
        raise ConfigError(
            "artwork_outer_ridge_width must be less than half of artwork_size.",
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
    ConfigurationValidator(
        parameters=("loop_inner_diameter",),
        validate=_validate_loop_inner_diameter,
    ),
    ConfigurationValidator(
        parameters=(
            "loop_inner_diameter",
            "loop_width",
        ),
        validate=_validate_loop_width,
    ),
    ConfigurationValidator(
        parameters=(
            "loop_inner_diameter",
            "loop_position",
        ),
        validate=_validate_loop_position,
    ),
    ConfigurationValidator(
        parameters=("artwork_base_raise",),
        validate=_validate_artwork_base_raise,
    ),
    ConfigurationValidator(
        parameters=(
            "artwork_outer_ridge_width",
            "artwork_size",
        ),
        validate=_validate_artwork_outer_ridge_width,
    ),
    ConfigurationValidator(
        parameters=("artwork_hole_diameter",),
        validate=_validate_artwork_hole_diameter,
    ),
    ConfigurationValidator(
        parameters=(
            "artwork_hole_diameter",
            "artwork_hole_edge_distance",
        ),
        validate=_validate_artwork_hole_edge_distance,
    ),
    ConfigurationValidator(
        parameters=(
            "artwork_hole_diameter",
            "artwork_hole_position",
        ),
        validate=_validate_artwork_hole_position,
    ),
)


__all__ = [
    "VALIDATORS",
]
