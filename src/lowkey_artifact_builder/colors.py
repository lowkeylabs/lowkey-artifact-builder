"""
Color resolution and matching utilities.

This module owns general color semantics used by artifact models.

It provides:

1. Palette resolution

   Resolve configured color names into concrete RGB colors.

   Explicit entries in a configured color palette take precedence.
   Standard CSS color names may be used without explicit palette
   entries.

2. Perceptual color comparison

   Convert sRGB colors to CIE L*a*b* and calculate perceptual color
   distance.

3. Color assignment

   Assign measured colors to configured palette colors using a
   one-to-one assignment that minimizes total perceptual color
   distance.

This module contains no artifact-model, file-format, build-engine,
printer, or filament-specific behavior.
"""

from __future__ import annotations

import itertools
import math
from collections.abc import (
    Mapping,
    Sequence,
)
from dataclasses import dataclass
from typing import Any

from PIL import ImageColor

# =========================================================
# Types
# =========================================================


RGB = tuple[
    int,
    int,
    int,
]

Lab = tuple[
    float,
    float,
    float,
]


# =========================================================
# Errors
# =========================================================


class ColorError(RuntimeError):
    """
    Raised for invalid color configuration or color matching.
    """


# =========================================================
# Specifications
# =========================================================


@dataclass(
    frozen=True,
    slots=True,
)
class PaletteColor:
    """
    One named palette color.

    name:
        Configuration name used to reference the color.

    rgb:
        RGB representation used for color matching.
    """

    name: str

    rgb: RGB


@dataclass(
    frozen=True,
    slots=True,
)
class MeasuredColor:
    """
    One measured color requiring assignment.

    index:
        Stable caller-defined index identifying the color.

    rgb:
        Measured RGB representation.
    """

    index: int

    rgb: RGB


@dataclass(
    frozen=True,
    slots=True,
)
class ColorAssignment:
    """
    Assignment of one measured color to one palette color.

    distance:
        Perceptual distance between the measured and assigned colors.
    """

    measured: MeasuredColor

    color: PaletteColor

    distance: float


# =========================================================
# Validation
# =========================================================


def _require_rgb(
    value: Any,
    *,
    name: str = "rgb",
) -> RGB:
    """
    Validate and normalize an RGB value.

    Accepted forms are three-element integer sequences such as:

        [255, 128, 0]

    or:

        (255, 128, 0)
    """

    if (
        isinstance(
            value,
            str | bytes,
        )
        or not isinstance(
            value,
            Sequence,
        )
        or len(value) != 3
    ):
        raise ColorError(f"{name} must contain exactly three RGB components.")

    result: list[int] = []

    for component in value:
        if (
            isinstance(
                component,
                bool,
            )
            or not isinstance(
                component,
                int,
            )
            or component < 0
            or component > 255
        ):
            raise ColorError(f"{name} components must be integers between 0 and 255.")

        result.append(component)

    return (
        result[0],
        result[1],
        result[2],
    )


def _require_color_name(
    value: Any,
) -> str:
    """
    Validate and normalize a configured color name.
    """

    if (
        not isinstance(
            value,
            str,
        )
        or not value.strip()
    ):
        raise ColorError("Color name must be a non-empty string.")

    return value.strip()


# =========================================================
# CSS colors
# =========================================================


def css_rgb(
    name: str,
) -> RGB:
    """
    Resolve a standard CSS color name.

    Pillow's ImageColor parser supplies the CSS named-color
    vocabulary without requiring another dependency.
    """

    name = _require_color_name(name)

    try:
        value = ImageColor.getrgb(name)

    except ValueError as exc:
        raise ColorError(
            f"Color is not configured and is not a recognized CSS color name: {name}"
        ) from exc

    if len(value) < 3:
        raise ColorError(f"Could not resolve RGB value for color: {name}")

    return (
        int(value[0]),
        int(value[1]),
        int(value[2]),
    )


# =========================================================
# Palette resolution
# =========================================================


def resolve_palette_color(
    name: str,
    palette: Mapping[
        str,
        Any,
    ],
) -> PaletteColor:
    """
    Resolve one named palette color.

    Resolution order:

        1. palette.<name>.rgb
        2. CSS named-color RGB

    A configured palette entry does not need an explicit RGB value
    when its name is a standard CSS color name.
    """

    name = _require_color_name(name)

    if not isinstance(
        palette,
        Mapping,
    ):
        raise ColorError("palette must be a mapping.")

    configured = palette.get(name)

    if configured is None:
        return PaletteColor(
            name=name,
            rgb=css_rgb(name),
        )

    if not isinstance(
        configured,
        Mapping,
    ):
        raise ColorError(f"palette.{name} must be a table.")

    if "rgb" in configured:
        rgb = _require_rgb(
            configured["rgb"],
            name=f"palette.{name}.rgb",
        )

    else:
        rgb = css_rgb(name)

    return PaletteColor(
        name=name,
        rgb=rgb,
    )


def resolve_palette(
    names: Sequence[str],
    palette: Mapping[
        str,
        Any,
    ],
) -> tuple[
    PaletteColor,
    ...,
]:
    """
    Resolve an ordered sequence of palette color names.

    Duplicate color names are rejected because one-to-one assignment
    requires each palette color to have a distinct semantic identity.
    """

    if isinstance(
        names,
        str | bytes,
    ):
        raise ColorError("Color names must be a sequence of strings.")

    if not names:
        raise ColorError("Color names cannot be empty.")

    resolved: list[PaletteColor] = []

    seen: set[str] = set()

    for name in names:
        normalized = _require_color_name(name)

        if normalized in seen:
            raise ColorError(f"Duplicate palette color: {normalized}")

        seen.add(normalized)

        resolved.append(
            resolve_palette_color(
                normalized,
                palette,
            )
        )

    return tuple(resolved)


# =========================================================
# Perceptual color conversion
# =========================================================


def _srgb_channel_to_linear(
    value: float,
) -> float:
    """
    Convert one normalized sRGB component to linear RGB.
    """

    if value <= 0.04045:
        return value / 12.92

    return ((value + 0.055) / 1.055) ** 2.4


def _rgb_to_xyz(
    rgb: RGB,
) -> tuple[
    float,
    float,
    float,
]:
    """
    Convert sRGB to CIE XYZ using a D65 white point.
    """

    red = _srgb_channel_to_linear(rgb[0] / 255.0)

    green = _srgb_channel_to_linear(rgb[1] / 255.0)

    blue = _srgb_channel_to_linear(rgb[2] / 255.0)

    x = red * 0.4124564 + green * 0.3575761 + blue * 0.1804375

    y = red * 0.2126729 + green * 0.7151522 + blue * 0.0721750

    z = red * 0.0193339 + green * 0.1191920 + blue * 0.9503041

    return (
        x,
        y,
        z,
    )


def _lab_function(
    value: float,
) -> float:
    """
    Return the CIE Lab conversion helper value.
    """

    delta = 6.0 / 29.0

    if value > (delta**3):
        return value ** (1.0 / 3.0)

    return value / (3.0 * delta * delta) + 4.0 / 29.0


def rgb_to_lab(
    rgb: RGB,
) -> Lab:
    """
    Convert an RGB color to CIE L*a*b*.

    The conversion uses the standard D65 reference white.
    """

    rgb = _require_rgb(rgb)

    x, y, z = _rgb_to_xyz(rgb)

    #
    # D65 reference white.
    #

    reference_x = 0.95047
    reference_y = 1.00000
    reference_z = 1.08883

    fx = _lab_function(x / reference_x)

    fy = _lab_function(y / reference_y)

    fz = _lab_function(z / reference_z)

    lightness = 116.0 * fy - 16.0

    a = 500.0 * (fx - fy)

    b = 200.0 * (fy - fz)

    return (
        lightness,
        a,
        b,
    )


# =========================================================
# Color distance
# =========================================================


def color_distance(
    first: RGB,
    second: RGB,
) -> float:
    """
    Return perceptual distance between two RGB colors.

    Distance is Euclidean distance in CIE L*a*b* space.
    """

    first_lab = rgb_to_lab(first)

    second_lab = rgb_to_lab(second)

    return math.sqrt(
        sum(
            (left - right) ** 2
            for left, right in zip(
                first_lab,
                second_lab,
                strict=True,
            )
        )
    )


# =========================================================
# Color assignment
# =========================================================


def assign_colors(
    measured: Sequence[MeasuredColor],
    palette: Sequence[PaletteColor],
) -> tuple[
    ColorAssignment,
    ...,
]:
    """
    Assign measured colors to palette colors.

    Assignment is one-to-one and minimizes total perceptual color
    distance across all assignments.

    The number of measured colors must equal the number of palette
    colors.

    This exhaustive assignment is intentionally simple. Artifact
    palettes are expected to contain only a small number of colors;
    five colors require only 120 permutations.
    """

    if not measured:
        raise ColorError("Measured colors cannot be empty.")

    if not palette:
        raise ColorError("Palette colors cannot be empty.")

    if len(measured) != len(palette):
        raise ColorError(
            "Measured color count must equal palette color count. "
            f"Measured {len(measured)}, palette {len(palette)}."
        )

    measured_colors = tuple(measured)

    palette_colors = tuple(palette)

    _validate_measured_colors(measured_colors)

    _validate_palette_colors(palette_colors)

    best_palette: (
        tuple[
            PaletteColor,
            ...,
        ]
        | None
    ) = None

    best_distances: (
        tuple[
            float,
            ...,
        ]
        | None
    ) = None

    best_total: float | None = None

    for candidate in itertools.permutations(palette_colors):
        distances = tuple(
            color_distance(
                layer.rgb,
                color.rgb,
            )
            for layer, color in zip(
                measured_colors,
                candidate,
                strict=True,
            )
        )

        total = sum(distances)

        if best_total is None or total < best_total:
            best_total = total
            best_palette = candidate
            best_distances = distances

    if best_palette is None or best_distances is None:
        raise ColorError("Could not determine a color assignment.")

    return tuple(
        ColorAssignment(
            measured=layer,
            color=color,
            distance=distance,
        )
        for layer, color, distance in zip(
            measured_colors,
            best_palette,
            best_distances,
            strict=True,
        )
    )


def _validate_measured_colors(
    colors: tuple[
        MeasuredColor,
        ...,
    ],
) -> None:
    """
    Validate measured color specifications.
    """

    indexes: set[int] = set()

    for color in colors:
        if (
            isinstance(
                color.index,
                bool,
            )
            or not isinstance(
                color.index,
                int,
            )
            or color.index < 1
        ):
            raise ColorError("Measured color indexes must be positive integers.")

        if color.index in indexes:
            raise ColorError(f"Duplicate measured color index: {color.index}")

        indexes.add(color.index)

        _require_rgb(
            color.rgb,
            name=(f"measured color {color.index} RGB"),
        )


def _validate_palette_colors(
    colors: tuple[
        PaletteColor,
        ...,
    ],
) -> None:
    """
    Validate palette color specifications.
    """

    names: set[str] = set()

    for color in colors:
        name = _require_color_name(color.name)

        if name in names:
            raise ColorError(f"Duplicate palette color: {name}")

        names.add(name)

        _require_rgb(
            color.rgb,
            name=(f"palette color {name!r} RGB"),
        )


__all__ = [
    "ColorAssignment",
    "ColorError",
    "Lab",
    "MeasuredColor",
    "PaletteColor",
    "RGB",
    "assign_colors",
    "color_distance",
    "css_rgb",
    "resolve_palette",
    "resolve_palette_color",
    "rgb_to_lab",
]
