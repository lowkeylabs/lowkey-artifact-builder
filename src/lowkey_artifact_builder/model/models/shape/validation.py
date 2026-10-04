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


def _validate_inner_ridge_width(
    resolver: ConfigurationResolver,
) -> None:
    """
    Require inner-ridge width to be nonnegative.
    """

    ridge_width = resolver(
        "shape_inner_ridge_width",
    )

    if not isinstance(
        ridge_width,
        int | float,
    ):
        raise ConfigError("shape_inner_ridge_width must be numeric.")

    if ridge_width < 0:
        raise ConfigError("shape_inner_ridge_width must be greater than or equal to 0.")


def _validate_inner_ridge_raise(
    resolver: ConfigurationResolver,
) -> None:
    """
    Require inner-ridge raise to be nonnegative.
    """

    ridge_raise = resolver("shape_inner_ridge_raise")

    if not isinstance(ridge_raise, (int | float)):
        raise ConfigError(
            "shape_inner_ridge_raise must be numeric.",
        )

    if ridge_raise < 0:
        raise ConfigError(
            "shape_inner_ridge_raise must be greater than or equal to zero.",
        )


def _validate_inner_to_outer_ridge_dist(
    resolver: ConfigurationResolver,
) -> None:
    """
    Require inner-ridge positioning distance to be nonnegative.
    """

    ridge_distance = resolver(
        "shape_inner_to_outer_ridge_dist",
    )

    if not isinstance(
        ridge_distance,
        int | float,
    ):
        raise ConfigError("shape_inner_to_outer_ridge_dist must be numeric.")

    if ridge_distance < 0:
        raise ConfigError("shape_inner_to_outer_ridge_dist must be greater than or equal to 0.")


def _validate_inner_ridge_color(
    resolver: ConfigurationResolver,
) -> None:
    """
    Require the inner-ridge color to be a nonempty semantic color name.
    """

    ridge_color = resolver(
        "shape_inner_ridge_color",
    )

    if (
        not isinstance(
            ridge_color,
            str,
        )
        or not ridge_color.strip()
    ):
        raise ConfigError("shape_inner_ridge_color must be a nonempty color name.")


def _border_label_participates(
    text: object,
) -> bool:
    """
    Return whether Border Label text causes the label to participate.
    """

    return isinstance(text, str) and bool(text.strip())


def _validate_border_label_width(
    resolver: ConfigurationResolver,
) -> None:
    """
    Require Border Label clear-border width to be nonnegative.
    """

    width = resolver(
        "shape_border_label_width",
    )

    if not isinstance(
        width,
        int | float,
    ):
        raise ConfigError("shape_border_label_width must be numeric.")

    if width < 0:
        raise ConfigError("shape_border_label_width must be greater than or equal to zero.")


def _validate_border_label_max_glyph_height(
    resolver: ConfigurationResolver,
) -> None:
    """
    Require positive maximum glyph height when a Border Label participates.
    """

    top_text = resolver(
        "shape_top_border_label_text",
    )
    bottom_text = resolver(
        "shape_bottom_border_label_text",
    )

    if not (_border_label_participates(top_text) or _border_label_participates(bottom_text)):
        return

    max_glyph_height = resolver(
        "shape_border_label_max_glyph_height",
    )

    if not isinstance(
        max_glyph_height,
        int | float,
    ):
        raise ConfigError("shape_border_label_max_glyph_height must be numeric.")

    if max_glyph_height <= 0:
        raise ConfigError("shape_border_label_max_glyph_height must be greater than zero.")


def _validate_border_label_arc_degrees(
    resolver: ConfigurationResolver,
) -> None:
    """
    Require Border Label maximum span to be greater than zero and less than 180 degrees.
    """

    arc_degrees = resolver(
        "shape_border_label_arc_degrees",
    )

    if not isinstance(
        arc_degrees,
        int | float,
    ):
        raise ConfigError("shape_border_label_arc_degrees must be numeric.")

    if arc_degrees <= 0 or arc_degrees >= 180:
        raise ConfigError(
            "shape_border_label_arc_degrees must be greater than zero and less than 180."
        )


def _validate_border_label_end_margin(
    resolver: ConfigurationResolver,
) -> None:
    """
    Require Border Label end margin to be nonnegative.
    """

    end_margin = resolver(
        "shape_border_label_end_margin",
    )

    if not isinstance(
        end_margin,
        int | float,
    ):
        raise ConfigError("shape_border_label_end_margin must be numeric.")

    if end_margin < 0:
        raise ConfigError("shape_border_label_end_margin must be greater than or equal to zero.")


def _validate_hole_diameter(
    resolver: ConfigurationResolver,
) -> None:
    """
    Require Hole diameter to be nonnegative.

    Zero disables Hole participation.
    """

    diameter = resolver(
        "shape_hole_diameter",
    )

    if isinstance(
        diameter,
        bool,
    ) or not isinstance(
        diameter,
        int | float,
    ):
        raise ConfigError("shape_hole_diameter must be numeric.")

    if diameter < 0:
        raise ConfigError("shape_hole_diameter must be greater than or equal to zero.")


def _validate_hole_position(
    resolver: ConfigurationResolver,
) -> None:
    """
    Require a participating Hole to use a supported cardinal position.
    """

    diameter = resolver(
        "shape_hole_diameter",
    )

    if diameter == 0:
        return

    position = resolver(
        "shape_hole_position",
    )

    if (
        isinstance(
            position,
            bool,
        )
        or not isinstance(
            position,
            int,
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
            "shape_hole_position must be one of 0, 90, 180, or -90 when the Hole participates."
        )


def _validate_hole_edge_distance(
    resolver: ConfigurationResolver,
) -> None:
    """
    Require a participating Hole to remain at least 0.4 mm from the Shape edge.
    """

    diameter = resolver(
        "shape_hole_diameter",
    )

    if diameter == 0:
        return

    edge_distance = resolver(
        "shape_hole_edge_distance",
    )

    if isinstance(
        edge_distance,
        bool,
    ) or not isinstance(
        edge_distance,
        int | float,
    ):
        raise ConfigError("shape_hole_edge_distance must be numeric.")

    if edge_distance < 0.4:
        raise ConfigError(
            "shape_hole_edge_distance must be greater than or equal to 0.4 "
            "when the Hole participates."
        )


def _validate_loop_inner_diameter(
    resolver: ConfigurationResolver,
) -> None:
    """
    Require Loop inner diameter to be nonnegative.

    Zero disables Loop participation.
    """

    diameter = resolver(
        "shape_loop_inner_diameter",
    )

    if isinstance(
        diameter,
        bool,
    ) or not isinstance(
        diameter,
        int | float,
    ):
        raise ConfigError("shape_loop_inner_diameter must be numeric.")

    if diameter < 0:
        raise ConfigError("shape_loop_inner_diameter must be greater than or equal to zero.")


def _validate_loop_width(
    resolver: ConfigurationResolver,
) -> None:
    """
    Require a participating Loop to have positive radial width.
    """

    diameter = resolver(
        "shape_loop_inner_diameter",
    )

    if diameter == 0:
        return

    width = resolver(
        "shape_loop_width",
    )

    if isinstance(
        width,
        bool,
    ) or not isinstance(
        width,
        int | float,
    ):
        raise ConfigError("shape_loop_width must be numeric.")

    if width <= 0:
        raise ConfigError("shape_loop_width must be greater than zero when the Loop participates.")


def _validate_loop_position(
    resolver: ConfigurationResolver,
) -> None:
    """
    Require a participating Loop to use a supported cardinal position.
    """

    diameter = resolver(
        "shape_loop_inner_diameter",
    )

    if diameter == 0:
        return

    position = resolver(
        "shape_loop_position",
    )

    if (
        isinstance(
            position,
            bool,
        )
        or not isinstance(
            position,
            int,
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
            "shape_loop_position must be one of 0, 90, 180, or -90 when the Loop participates."
        )


def _validate_raise_style(
    resolver: ConfigurationResolver,
) -> None:
    """
    Require Shape raise style to be one of the supported styles.
    """

    raise_style = resolver(
        "shape_raise_style",
    )

    if raise_style not in (
        "raised",
        "inlaid",
    ):
        raise ConfigError("shape_raise_style must be one of: raised, inlaid.")


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
        parameters=(
            "shape_base_raise",
            "shape_inner_ridge_raise",
        ),
        validate=_validate_inner_ridge_raise,
    ),
    ConfigurationValidator(
        parameters=("shape_outer_ridge_width",),
        validate=_validate_outer_ridge_width,
    ),
    ConfigurationValidator(
        parameters=("shape_inner_ridge_width",),
        validate=_validate_inner_ridge_width,
    ),
    ConfigurationValidator(
        parameters=("shape_inner_to_outer_ridge_dist",),
        validate=_validate_inner_to_outer_ridge_dist,
    ),
    ConfigurationValidator(
        parameters=("shape_outer_ridge_style",),
        validate=_validate_outer_ridge_style,
    ),
    ConfigurationValidator(
        parameters=("shape_raise_style",),
        validate=_validate_raise_style,
    ),
    ConfigurationValidator(
        parameters=("shape_base_color",),
        validate=_validate_base_color,
    ),
    ConfigurationValidator(
        parameters=("shape_outer_ridge_color",),
        validate=_validate_outer_ridge_color,
    ),
    ConfigurationValidator(
        parameters=("shape_inner_ridge_color",),
        validate=_validate_inner_ridge_color,
    ),
    ConfigurationValidator(
        parameters=("shape_border_label_width",),
        validate=_validate_border_label_width,
    ),
    ConfigurationValidator(
        parameters=(
            "shape_top_border_label_text",
            "shape_bottom_border_label_text",
            "shape_border_label_max_glyph_height",
        ),
        validate=_validate_border_label_max_glyph_height,
    ),
    ConfigurationValidator(
        parameters=("shape_border_label_arc_degrees",),
        validate=_validate_border_label_arc_degrees,
    ),
    ConfigurationValidator(
        parameters=("shape_border_label_end_margin",),
        validate=_validate_border_label_end_margin,
    ),
    ConfigurationValidator(
        parameters=("shape_hole_diameter",),
        validate=_validate_hole_diameter,
    ),
    ConfigurationValidator(
        parameters=(
            "shape_hole_diameter",
            "shape_hole_position",
        ),
        validate=_validate_hole_position,
    ),
    ConfigurationValidator(
        parameters=(
            "shape_hole_diameter",
            "shape_hole_edge_distance",
        ),
        validate=_validate_hole_edge_distance,
    ),
    ConfigurationValidator(
        parameters=("shape_loop_inner_diameter",),
        validate=_validate_loop_inner_diameter,
    ),
    ConfigurationValidator(
        parameters=(
            "shape_loop_inner_diameter",
            "shape_loop_width",
        ),
        validate=_validate_loop_width,
    ),
    ConfigurationValidator(
        parameters=(
            "shape_loop_inner_diameter",
            "shape_loop_position",
        ),
        validate=_validate_loop_position,
    ),
)


__all__ = [
    "VALIDATORS",
]
