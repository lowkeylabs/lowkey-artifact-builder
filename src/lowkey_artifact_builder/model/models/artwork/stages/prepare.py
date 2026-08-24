"""
Artwork prepare stage.

The prepare stage analyzes and normalizes materialized raster artwork
before converting it into a multicolor SVG trace.

Preparation establishes the physical artwork envelope. Pixels outside
that envelope are transparent. Pixels inside the envelope are made
opaque: existing artwork is preserved while transparent or
insufficiently opaque pixels are filled using the configured white
artwork color.

The stage produces:

    trace.svg
        Multicolor SVG trace of the normalized artwork.

    envelope.svg
        SVG containing only the closed outer boundary of the artwork.

Filesystem layout and configuration resolution are responsibilities of
the build engine. This implementation consumes only the inputs,
parameters, and outputs supplied through StageContext.
"""
# File: src/lowkey_artifact_builder/model/models/artwork/stages/prepare.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import xml.etree.ElementTree as ET
from collections import defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, cast

import numpy as np
from PIL import Image
from scipy import ndimage

from lowkey_artifact_builder.engine import (
    StageContext,
)
from lowkey_artifact_builder.tools.inkscape import (
    InkscapeError,
    run,
)

# =========================================================
# Errors
# =========================================================


class PrepareError(RuntimeError):
    """
    Raised when artwork preparation cannot be completed.
    """


# =========================================================
# Defaults
# =========================================================


DEFAULT_SPECKLES = 2
DEFAULT_SMOOTH_CORNERS = 1.0
DEFAULT_OPTIMIZE = 0.2

#
# Pixels below this alpha value are not considered meaningful source
# artwork when deriving the physical envelope.
#
DEFAULT_ALPHA_THRESHOLD = 128

#
# Small connected foreground regions below this size are treated as
# source-image noise during envelope construction.
#
DEFAULT_ENVELOPE_MIN_PIXELS = 16

#
# Radius of the morphology operation used to bridge small breaks in
# the visible artwork silhouette.
#
DEFAULT_ENVELOPE_CLOSE_PIXELS = 4


#
# Maximum local half-width of a palette region that may be treated as
# a thin quantization artifact.
#
# A value of 2 targets approximately 1-2 pixel-wide features while
# preserving broader artwork geometry.
#

DEFAULT_THIN_FEATURE_PIXELS = 2

# =========================================================
# Public interface
# =========================================================

# =========================================================
# Public interface
# =========================================================


def execute(
    context: StageContext,
) -> None:
    """
    Execute the artwork prepare stage.

    Preparation establishes the physical artwork envelope and produces
    a normalized, palette-quantized multicolor SVG trace.

    Processing:

        1. Load the source PNG.
        2. Resolve the configured artwork palette.
        3. Identify meaningful visible source artwork.
        4. Construct the physical artwork envelope.
        5. Write envelope.svg.
        6. Fill transparent regions inside the envelope with white.
        7. Quantize all pixels inside the envelope to exact configured
           artwork colors.
        8. Trace the quantized raster with Inkscape.
        9. Clip the resulting trace to the physical envelope.

    Pixels outside the envelope remain transparent.
    """

    source = context.input(
        "source",
    )

    trace_output = context.output(
        "trace",
    )

    envelope_output = context.output(
        "envelope",
    )

    #
    # Resolve the configured artwork palette.
    #
    colors = _require_colors(
        context.resolver(
            "artwork_colors",
        )
    )

    palette = _resolve_palette(
        context,
        colors,
    )

    fill_color = _require_fill_color(
        palette,
    )

    #
    # Validate inputs and outputs.
    #
    _require_source(
        source,
    )

    _require_svg_output(
        source,
        trace_output,
        label="Trace",
    )

    _require_svg_output(
        source,
        envelope_output,
        label="Envelope",
    )

    if trace_output.resolve() == envelope_output.resolve():
        raise PrepareError("Trace and envelope outputs must differ.")

    trace_output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    envelope_output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    #
    # Load the source raster.
    #
    image = _load_source_image(
        source,
    )

    #
    # Determine meaningful source foreground and construct the
    # physical artwork envelope.
    #
    foreground = _foreground_mask(
        image,
    )

    envelope = _build_envelope(
        foreground,
    )

    if not np.any(envelope):
        raise PrepareError("Could not derive an artwork envelope from the source image.")

    #
    # Write the envelope as a first-class diagnostic product.
    #
    _write_envelope_svg(
        envelope,
        envelope_output,
    )

    #
    # Normalize the source relative to the envelope.
    #
    # Outside:
    #     transparent
    #
    # Inside:
    #     opaque, with transparent source regions filled using the
    #     configured white artwork color
    #
    normalized = _normalize_image(
        image,
        envelope,
        fill_color=fill_color,
    )

    #
    # Collapse the normalized raster onto the exact configured
    # filament palette before tracing.
    #
    # This removes antialiased intermediate colors before Inkscape
    # attempts to discover vector geometry.
    #
    quantized = _quantize_image(
        normalized,
        envelope,
        palette=palette,
    )

    #
    # Remove weakly supported palette assignments introduced when
    # antialiased source pixels were collapsed onto the exact artwork
    # palette.
    #

    quantized = _cleanup_quantized_image(
        quantized,
        envelope,
        palette=palette,
        radius=1,
        minimum_support=3,
    )

    #
    # Remove long, geometrically thin palette regions that survive
    # neighbor-support cleanup because they have substantial support along
    # their length.
    #
    quantized = _cleanup_thin_features(
        quantized,
        envelope,
        palette=palette,
        maximum_radius=DEFAULT_THIN_FEATURE_PIXELS,
        replacement_radius=2,
    )

    #
    # The quantized raster is an implementation detail rather than a
    # persistent stage product.
    #
    temporary_path: Path | None = None

    try:
        with NamedTemporaryFile(
            prefix="artwork-prepared-",
            suffix=".png",
            dir=trace_output.parent,
            delete=False,
        ) as temporary:
            temporary_path = Path(
                temporary.name,
            )

        quantized.save(
            temporary_path,
            format="PNG",
        )

        #
        # Trace only exact configured artwork colors.
        #
        _trace_multicolor(
            temporary_path,
            trace_output,
            colors=len(palette),
        )

        #
        # The physical envelope remains authoritative. Clip any
        # page-sized or otherwise extraneous traced geometry back to
        # that envelope.
        #
        _clip_trace_to_envelope(
            trace_output,
            envelope,
        )

    except PrepareError:
        raise

    except (
        OSError,
        ValueError,
        TypeError,
    ) as exc:
        raise PrepareError(f"Could not prepare source artwork: {source}") from exc

    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink(
                    missing_ok=True,
                )

            except OSError:
                pass


# =========================================================
# Configuration
# =========================================================


def _require_colors(
    value: Any,
) -> tuple[str, ...]:
    """
    Return a validated sequence of artwork color names.
    """

    if isinstance(
        value,
        str | bytes,
    ) or not isinstance(
        value,
        Sequence,
    ):
        raise PrepareError("artwork_colors must be a sequence of color names.")

    colors: list[str] = []

    for color in value:
        if (
            not isinstance(
                color,
                str,
            )
            or not color.strip()
        ):
            raise PrepareError("artwork_colors must contain non-empty color names.")

        colors.append(color.strip())

    if len(colors) < 2:
        raise PrepareError("artwork_colors must contain at least two colors.")

    if len(set(colors)) != len(colors):
        raise PrepareError("artwork_colors must contain unique color names.")

    return tuple(colors)


def _resolve_palette(
    context: StageContext,
    colors: tuple[str, ...],
) -> tuple[tuple[str, tuple[int, int, int]], ...]:
    """
    Resolve configured artwork colors to exact catalog RGB values.

    The returned palette preserves artwork_colors ordering.
    """

    palette: list[
        tuple[
            str,
            tuple[int, int, int],
        ]
    ] = []

    for name in colors:
        value = context.resolver.color(
            name,
        )

        if not isinstance(
            value,
            Mapping,
        ):
            raise PrepareError(
                f"Configured artwork color {name!r} has no valid catalog definition."
            )

        rgb = value.get(
            "rgb",
        )

        if (
            isinstance(
                rgb,
                str | bytes,
            )
            or not isinstance(
                rgb,
                Sequence,
            )
            or len(rgb) != 3
        ):
            raise PrepareError(
                f"Configured artwork color {name!r} must define a three-component RGB value."
            )

        components: list[int] = []

        for component in rgb:
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
                raise PrepareError(
                    f"Configured artwork color {name!r} contains an invalid RGB component."
                )

            components.append(component)

        palette.append(
            (
                name,
                (
                    components[0],
                    components[1],
                    components[2],
                ),
            )
        )

    return tuple(palette)


def _quantize_image(
    image: Image.Image,
    envelope: np.ndarray,
    *,
    palette: tuple[
        tuple[
            str,
            tuple[int, int, int],
        ],
        ...,
    ],
) -> Image.Image:
    """
    Quantize artwork inside the envelope to exact configured colors.

    Quantization is performed in two passes.

    First, every pixel inside the artwork envelope is assigned to its
    nearest configured palette color.

    Second, suspicious boundary assignments are reconsidered using
    palette colors established in the surrounding neighborhood. This
    prevents antialiased transitions between two colors from producing
    thin regions of an unrelated third palette color.

    Pixels outside the envelope remain fully transparent.
    """

    rgba = np.asarray(
        image,
        dtype=np.uint8,
    )

    if envelope.shape != rgba.shape[:2]:
        raise PrepareError("Artwork envelope dimensions do not match the normalized image.")

    if not palette:
        raise PrepareError("Artwork palette cannot be empty.")

    palette_rgb = np.asarray(
        [rgb for _name, rgb in palette],
        dtype=np.int32,
    )

    source_rgb = rgba[
        :,
        :,
        :3,
    ].astype(
        np.int32,
    )

    pixels = source_rgb[envelope]

    if pixels.size == 0:
        raise PrepareError("Artwork envelope contains no pixels.")

    #
    # First pass:
    #
    # Assign every artwork pixel to its nearest configured palette
    # color.
    #
    differences = (
        pixels[
            :,
            None,
            :,
        ]
        - palette_rgb[
            None,
            :,
            :,
        ]
    )

    distances = np.sum(
        differences * differences,
        axis=2,
    )

    nearest = np.argmin(
        distances,
        axis=1,
    )

    #
    # Store palette indexes separately from the final image.
    #
    # -1 identifies pixels outside the artwork envelope.
    #
    labels = np.full(
        envelope.shape,
        -1,
        dtype=np.intp,
    )

    labels[envelope] = nearest.astype(
        np.intp,
    )

    #
    # Repair palette assignments that appear to be artifacts of an
    # antialiased boundary between other established colors.
    #
    labels = _repair_quantized_boundaries(
        source_rgb,
        labels,
        envelope,
        palette_rgb,
        radius=2,
        minimum_support=4,
    )

    #
    # Construct the exact-palette RGBA image.
    #
    result = np.zeros_like(
        rgba,
        dtype=np.uint8,
    )

    result[
        envelope,
        :3,
    ] = palette_rgb[labels[envelope]].astype(
        np.uint8,
    )

    result[
        envelope,
        3,
    ] = 255

    return Image.fromarray(
        result,
        mode="RGBA",
    )


def _repair_quantized_boundaries(
    source_rgb: np.ndarray,
    labels: np.ndarray,
    envelope: np.ndarray,
    palette_rgb: np.ndarray,
    *,
    radius: int = 2,
    minimum_support: int = 4,
) -> np.ndarray:
    """
    Repair unsupported palette assignments along color boundaries.

    Antialiased source pixels between two established artwork colors
    can sometimes be closer to an unrelated third palette color.

    For each palette color, measure its support in the surrounding
    neighborhood. Pixels whose assigned color has weak local support
    are reconsidered using only palette colors with meaningful local
    support.

    Among those supported colors, the source pixel is assigned to the
    nearest RGB value.

    The center pixel does not count as support for itself.
    """

    if radius < 1:
        raise PrepareError("Boundary repair radius must be positive.")

    if minimum_support < 1:
        raise PrepareError("Boundary repair minimum support must be positive.")

    if labels.shape != envelope.shape:
        raise PrepareError("Quantized label dimensions do not match the artwork envelope.")

    if source_rgb.shape[:2] != envelope.shape:
        raise PrepareError("Source RGB dimensions do not match the artwork envelope.")

    palette_count = int(palette_rgb.shape[0])

    size = 2 * radius + 1

    kernel = np.ones(
        (
            size,
            size,
        ),
        dtype=np.int16,
    )

    #
    # Do not let the current pixel provide evidence for itself.
    #
    kernel[
        radius,
        radius,
    ] = 0

    support = np.zeros(
        (
            palette_count,
            *envelope.shape,
        ),
        dtype=np.int16,
    )

    for index in range(palette_count):
        support[index] = ndimage.convolve(
            (labels == index).astype(
                np.int16,
            ),
            kernel,
            mode="constant",
            cval=0,
        )

    current_support = np.zeros(
        envelope.shape,
        dtype=np.int16,
    )

    for index in range(palette_count):
        current = labels == index

        current_support[current] = support[index][current]

    #
    # Only reconsider assignments that lack meaningful local support.
    #
    weak = envelope & (current_support < minimum_support)

    if not np.any(weak):
        return labels.copy()

    repaired = labels.copy()

    #
    # Determine RGB distance to every palette color.
    #
    differences = (
        source_rgb[
            :,
            :,
            None,
            :,
        ]
        - palette_rgb[
            None,
            None,
            :,
            :,
        ]
    )

    distances = np.sum(
        differences * differences,
        axis=3,
    )

    #
    # Colors without sufficient neighborhood support are not valid
    # replacement candidates.
    #
    supported = np.moveaxis(
        support >= minimum_support,
        0,
        2,
    )

    distances = np.where(
        supported,
        distances,
        np.iinfo(
            np.int64,
        ).max,
    )

    replacement = np.argmin(
        distances,
        axis=2,
    )

    has_replacement = np.any(
        supported,
        axis=2,
    )

    replace = weak & has_replacement

    repaired[replace] = replacement[replace]

    return repaired


def _cleanup_quantized_image(
    image: Image.Image,
    envelope: np.ndarray,
    *,
    palette: tuple[
        tuple[
            str,
            tuple[int, int, int],
        ],
        ...,
    ],
    radius: int = 1,
    minimum_support: int = 2,
) -> Image.Image:
    """
    Remove weakly supported palette assignments from quantized artwork.

    Quantization can convert antialiased boundary pixels into narrow
    bands of an otherwise unrelated palette color. Because the input
    image has already been quantized, every opaque pixel inside the
    envelope belongs to exactly one configured palette color.

    For each pixel, inspect the surrounding neighborhood. If the
    pixel's current color has insufficient local support, replace it
    with the most common neighboring palette color.

    A radius of 1 examines a 3x3 neighborhood. The center pixel is not
    counted as support for itself.

    This operation is intentionally conservative. It removes isolated
    or very weakly supported color assignments without applying
    erosion or dilation to legitimate narrow artwork geometry.

    Pixels outside the envelope remain transparent.
    """

    if radius < 1:
        raise PrepareError("Palette cleanup radius must be positive.")

    if minimum_support < 0:
        raise PrepareError("Palette cleanup minimum support cannot be negative.")

    rgba = np.asarray(
        image,
        dtype=np.uint8,
    )

    if envelope.shape != rgba.shape[:2]:
        raise PrepareError("Artwork envelope dimensions do not match the quantized image.")

    if not palette:
        raise PrepareError("Artwork palette cannot be empty.")

    palette_rgb = np.asarray(
        [rgb for _name, rgb in palette],
        dtype=np.uint8,
    )

    height, width = envelope.shape

    #
    # Convert the exact RGB raster into palette indexes.
    #
    labels = np.full(
        (
            height,
            width,
        ),
        -1,
        dtype=np.intp,
    )

    for index, rgb in enumerate(palette_rgb):
        matches = envelope & np.all(
            rgba[
                :,
                :,
                :3,
            ]
            == rgb,
            axis=2,
        )

        labels[matches] = index

    if np.any(envelope & (labels < 0)):
        raise PrepareError("Quantized artwork contains a color outside the configured palette.")

    #
    # Count neighboring pixels belonging to each palette color.
    #
    size = 2 * radius + 1

    kernel = np.ones(
        (
            size,
            size,
        ),
        dtype=np.int16,
    )

    #
    # Do not allow the center pixel to count as evidence supporting
    # its own current color.
    #
    kernel[
        radius,
        radius,
    ] = 0

    support = np.zeros(
        (
            len(palette),
            height,
            width,
        ),
        dtype=np.int16,
    )

    for index in range(len(palette)):
        layer = labels == index

        support[index] = ndimage.convolve(
            layer.astype(
                np.int16,
            ),
            kernel,
            mode="constant",
            cval=0,
        )

    #
    # Obtain support for each pixel's currently assigned color.
    #
    current_support = np.zeros(
        (
            height,
            width,
        ),
        dtype=np.int16,
    )

    for index in range(len(palette)):
        current = labels == index

        current_support[current] = support[index,][current]

    weak = envelope & (current_support < minimum_support)

    if not np.any(weak):
        return image.copy()

    #
    # Determine the locally dominant palette color.
    #
    replacement = np.argmax(
        support,
        axis=0,
    )

    replacement_support = np.max(
        support,
        axis=0,
    )

    #
    # A weak pixel is changed only when there is actual neighboring
    # evidence for another palette color.
    #
    replace = weak & (replacement_support > current_support)

    cleaned_labels = labels.copy()

    cleaned_labels[replace] = replacement[replace]

    #
    # Reconstruct an exact-palette RGBA image.
    #
    result = np.zeros_like(
        rgba,
        dtype=np.uint8,
    )

    for index, rgb in enumerate(palette_rgb):
        matches = envelope & (cleaned_labels == index)

        result[
            matches,
            :3,
        ] = rgb

        result[
            matches,
            3,
        ] = 255

    return Image.fromarray(
        result,
        mode="RGBA",
    )


def _thin_feature_mask(
    mask: np.ndarray,
    *,
    maximum_radius: int,
) -> np.ndarray:
    """
    Return pixels belonging to geometrically thin regions.

    The Euclidean distance transform measures each foreground pixel's
    distance from the nearest background pixel. Pixels whose distance
    does not exceed maximum_radius are therefore near a boundary.

    A candidate thin feature must be unable to contain an interior
    region farther than maximum_radius from its boundary.

    This helper operates on one palette-color mask at a time.
    """

    if mask.ndim != 2:
        raise PrepareError("Thin-feature mask must be two-dimensional.")

    if maximum_radius < 1:
        raise PrepareError("Thin-feature maximum radius must be positive.")

    if not np.any(mask):
        return np.zeros_like(
            mask,
            dtype=bool,
        )

    distance = np.asarray(
        ndimage.distance_transform_edt(
            mask,
        ),
        dtype=np.float64,
    )

    #
    # Pixels within this distance of the region boundary are potential
    # members of thin geometry.
    #
    boundary_band = mask & (distance <= float(maximum_radius))

    #
    # Determine connected components of the palette region. A whole
    # component is considered thin only when it contains no pixel with
    # a distance greater than maximum_radius.
    #
    structure = np.ones(
        (
            3,
            3,
        ),
        dtype=bool,
    )

    label_result = cast(
        tuple[Any, int],
        ndimage.label(
            mask,
            structure=structure,
        ),
    )

    labels = np.asarray(
        label_result[0],
        dtype=np.intp,
    )

    count = label_result[1]

    result = np.zeros_like(
        mask,
        dtype=bool,
    )

    for label in range(
        1,
        count + 1,
    ):
        component = labels == label

        if not np.any(component):
            continue

        maximum_distance = float(
            np.max(
                distance[component],
            )
        )

        if maximum_distance <= float(maximum_radius):
            result |= component & boundary_band

    return result


def _cleanup_thin_features(
    image: Image.Image,
    envelope: np.ndarray,
    *,
    palette: tuple[
        tuple[
            str,
            tuple[int, int, int],
        ],
        ...,
    ],
    maximum_radius: int = DEFAULT_THIN_FEATURE_PIXELS,
    replacement_radius: int = 2,
) -> Image.Image:
    """
    Replace geometrically thin palette regions with neighboring colors.

    This pass targets long, narrow palette regions that survive the
    local-support cleanup because they have substantial support along
    their length.

    Each configured palette color is examined independently. Connected
    components that never become thicker than maximum_radius are
    considered thin-feature candidates.

    Candidate pixels are reassigned to the most strongly represented
    *different* palette color in the surrounding neighborhood.

    Pixels outside the artwork envelope remain transparent.
    """

    if maximum_radius < 1:
        raise PrepareError("Thin-feature maximum radius must be positive.")

    if replacement_radius < 1:
        raise PrepareError("Thin-feature replacement radius must be positive.")

    rgba = np.asarray(
        image,
        dtype=np.uint8,
    )

    if envelope.shape != rgba.shape[:2]:
        raise PrepareError("Artwork envelope dimensions do not match the quantized image.")

    if not palette:
        raise PrepareError("Artwork palette cannot be empty.")

    palette_rgb = np.asarray(
        [rgb for _name, rgb in palette],
        dtype=np.uint8,
    )

    height, width = envelope.shape

    #
    # Convert exact RGB values to palette indexes.
    #
    labels = np.full(
        (
            height,
            width,
        ),
        -1,
        dtype=np.intp,
    )

    for index, rgb in enumerate(palette_rgb):
        matches = envelope & np.all(
            rgba[
                :,
                :,
                :3,
            ]
            == rgb,
            axis=2,
        )

        labels[matches] = index

    if np.any(envelope & (labels < 0)):
        raise PrepareError("Quantized artwork contains a color outside the configured palette.")

    #
    # Find geometrically thin components for every palette color.
    #
    thin = np.zeros(
        (
            len(palette),
            height,
            width,
        ),
        dtype=bool,
    )

    for index in range(len(palette)):
        thin[index] = _thin_feature_mask(
            labels == index,
            maximum_radius=maximum_radius,
        )

    #
    # Count nearby support for every palette color.
    #
    size = 2 * replacement_radius + 1

    kernel = np.ones(
        (
            size,
            size,
        ),
        dtype=np.int16,
    )

    kernel[
        replacement_radius,
        replacement_radius,
    ] = 0

    support = np.zeros(
        (
            len(palette),
            height,
            width,
        ),
        dtype=np.int16,
    )

    for index in range(len(palette)):
        support[index] = ndimage.convolve(
            (labels == index).astype(
                np.int16,
            ),
            kernel,
            mode="constant",
            cval=0,
        )

    cleaned_labels = labels.copy()

    #
    # Replace thin pixels with the strongest neighboring *other*
    # palette color.
    #
    for index in range(len(palette)):
        candidates = thin[index] & envelope

        if not np.any(candidates):
            continue

        alternative_support = support.copy()

        #
        # The current color cannot replace itself.
        #
        alternative_support[index] = -1

        replacement = np.argmax(
            alternative_support,
            axis=0,
        )

        replacement_support = np.max(
            alternative_support,
            axis=0,
        )

        replace = candidates & (replacement_support > 0)

        cleaned_labels[replace] = replacement[replace]

    #
    # Reconstruct an exact-palette RGBA raster.
    #
    result = np.zeros_like(
        rgba,
        dtype=np.uint8,
    )

    for index, rgb in enumerate(palette_rgb):
        matches = envelope & (cleaned_labels == index)

        result[
            matches,
            :3,
        ] = rgb

        result[
            matches,
            3,
        ] = 255

    return Image.fromarray(
        result,
        mode="RGBA",
    )


def _require_fill_color(
    palette: tuple[
        tuple[
            str,
            tuple[int, int, int],
        ],
        ...,
    ],
) -> tuple[int, int, int]:
    """
    Return the configured white artwork color.

    White is used to make transparent regions inside the physical
    artwork envelope printable.
    """

    for name, rgb in palette:
        if name == "white":
            return rgb

    raise PrepareError(
        "Artwork preparation requires 'white' in artwork_colors "
        "to fill transparent regions inside the artwork envelope."
    )


def _resolve_fill_color(
    context: StageContext,
    colors: tuple[str, ...],
) -> tuple[int, int, int]:
    """
    Resolve the white artwork color used to fill the envelope interior.

    The RGB value comes from the artifact resolver's color catalog.
    """

    if "white" not in colors:
        raise PrepareError(
            "Artwork preparation requires 'white' in artwork_colors to fill the artwork envelope."
        )

    value = context.resolver.color(
        "white",
    )

    if not isinstance(
        value,
        Mapping,
    ):
        raise PrepareError("Configured white color has no valid catalog definition.")

    rgb = value.get(
        "rgb",
    )

    if (
        isinstance(
            rgb,
            str | bytes,
        )
        or not isinstance(
            rgb,
            Sequence,
        )
        or len(rgb) != 3
    ):
        raise PrepareError("Configured white color must define a three-component RGB value.")

    components: list[int] = []

    for component in rgb:
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
            raise PrepareError("Configured white color contains an invalid RGB component.")

        components.append(component)

    return (
        components[0],
        components[1],
        components[2],
    )


# =========================================================
# Validation
# =========================================================


def _require_source(
    source: Path,
) -> None:
    """
    Validate the source raster artwork.
    """

    if not source.is_file():
        raise PrepareError(f"Source artwork does not exist: {source}")

    if source.suffix.lower() != ".png":
        raise PrepareError(f"Source artwork must be a PNG file: {source}")


def _require_svg_output(
    source: Path,
    output: Path,
    *,
    label: str,
) -> None:
    """
    Validate one SVG output path.
    """

    if output.suffix.lower() != ".svg":
        raise PrepareError(f"{label} output must be an SVG file: {output}")

    if source.resolve() == output.resolve():
        raise PrepareError(f"{label} output must differ from the source artwork.")


# =========================================================
# Source loading
# =========================================================


def _load_source_image(
    source: Path,
) -> Image.Image:
    """
    Load source artwork as RGBA.
    """

    try:
        with Image.open(
            source,
        ) as image:
            return image.convert(
                "RGBA",
            )

    except OSError as exc:
        raise PrepareError(f"Could not read source artwork: {source}") from exc


# =========================================================
# Foreground detection
# =========================================================


def _foreground_mask(
    image: Image.Image,
) -> np.ndarray:
    """
    Return a binary mask of meaningful visible source artwork.

    Very low-alpha pixels are ignored so antialiasing residue and
    nearly transparent source noise do not influence the physical
    artwork envelope.
    """

    rgba = np.asarray(
        image,
        dtype=np.uint8,
    )

    alpha = rgba[
        :,
        :,
        3,
    ]

    return alpha >= DEFAULT_ALPHA_THRESHOLD


# =========================================================
# Envelope construction
# =========================================================


def _build_envelope(
    foreground: np.ndarray,
) -> np.ndarray:
    """
    Derive a solid artwork envelope from meaningful source foreground.

    Processing consists of:

        1. Remove insignificant connected foreground regions.
        2. Bridge small gaps in the remaining silhouette.
        3. Fill all enclosed regions.

    The result is a solid binary mask representing the physical domain
    of the artwork.
    """

    if foreground.ndim != 2:
        raise PrepareError("Artwork foreground mask must be two-dimensional.")

    cleaned = _remove_small_components(
        foreground,
        minimum_pixels=DEFAULT_ENVELOPE_MIN_PIXELS,
    )

    if not np.any(cleaned):
        raise PrepareError("No meaningful foreground remains after envelope cleanup.")

    structure = _disk_structure(
        DEFAULT_ENVELOPE_CLOSE_PIXELS,
    )

    closed = np.asarray(
        ndimage.binary_closing(
            cleaned,
            structure=structure,
        ),
        dtype=bool,
    )

    filled = np.asarray(
        ndimage.binary_fill_holes(
            closed,
        ),
        dtype=bool,
    )

    envelope = _retain_primary_envelope(
        filled,
    )

    return np.asarray(
        envelope,
        dtype=bool,
    )


def _remove_small_components(
    mask: np.ndarray,
    *,
    minimum_pixels: int,
) -> np.ndarray:
    """
    Remove insignificant disconnected foreground components.

    Unlike selecting only the largest component, this retains every
    meaningful source component and removes only small source noise.
    """

    if minimum_pixels < 1:
        raise PrepareError("Envelope minimum component size must be positive.")

    structure = np.ones(
        (
            3,
            3,
        ),
        dtype=bool,
    )

    label_result = cast(
        tuple[Any, int],
        ndimage.label(
            mask,
            structure=structure,
        ),
    )

    labels = np.asarray(
        label_result[0],
        dtype=np.intp,
    )

    count = label_result[1]

    if count == 0:
        return np.zeros_like(
            mask,
            dtype=bool,
        )

    sizes = np.bincount(
        labels.ravel(),
    )

    keep = sizes >= minimum_pixels

    keep[0] = False

    return np.asarray(
        keep[labels],
        dtype=bool,
    )


def _retain_primary_envelope(
    mask: np.ndarray,
) -> np.ndarray:
    """
    Retain the primary connected physical envelope.

    Noise removal and closing occur before this operation. At this
    point the intended artwork is expected to form one dominant
    physical domain.

    If several regions remain, the largest is treated as the physical
    artifact envelope.
    """

    structure = np.ones(
        (
            3,
            3,
        ),
        dtype=bool,
    )

    label_result = cast(
        tuple[Any, int],
        ndimage.label(
            mask,
            structure=structure,
        ),
    )

    labels = np.asarray(
        label_result[0],
        dtype=np.intp,
    )

    count = label_result[1]

    if count == 0:
        return np.zeros_like(
            mask,
            dtype=bool,
        )

    if count == 1:
        return np.asarray(
            mask,
            dtype=bool,
        )

    sizes = np.bincount(
        labels.ravel(),
    )

    sizes[0] = 0

    largest = int(sizes.argmax())

    return np.asarray(
        labels == largest,
        dtype=bool,
    )


def _disk_structure(
    radius: int,
) -> np.ndarray:
    """
    Return a circular binary morphology structure.
    """

    if radius < 1:
        return np.ones(
            (
                1,
                1,
            ),
            dtype=bool,
        )

    coordinates = np.arange(
        -radius,
        radius + 1,
    )

    y, x = np.meshgrid(
        coordinates,
        coordinates,
        indexing="ij",
    )

    return (x * x + y * y) <= radius * radius


# =========================================================
# Raster normalization
# =========================================================


def _normalize_image(
    image: Image.Image,
    envelope: np.ndarray,
    *,
    fill_color: tuple[int, int, int],
) -> Image.Image:
    """
    Normalize source artwork against its physical envelope.

    Outside the envelope:
        Pixels are fully transparent.

    Inside the envelope:
        Meaningful source pixels retain their source RGB value and
        become fully opaque.

        Pixels below the meaningful-alpha threshold become the
        configured fill color and are fully opaque.

    Palette quantization is performed separately after normalization.
    """

    rgba = np.asarray(
        image,
        dtype=np.uint8,
    )

    if envelope.shape != rgba.shape[:2]:
        raise PrepareError("Artwork envelope dimensions do not match the source image.")

    alpha = rgba[
        :,
        :,
        3,
    ]

    meaningful = envelope & (alpha >= DEFAULT_ALPHA_THRESHOLD)

    result = np.zeros_like(
        rgba,
        dtype=np.uint8,
    )

    #
    # Everything inside the envelope initially becomes the configured
    # fill color.
    #
    result[
        envelope,
        0,
    ] = fill_color[0]

    result[
        envelope,
        1,
    ] = fill_color[1]

    result[
        envelope,
        2,
    ] = fill_color[2]

    result[
        envelope,
        3,
    ] = 255

    #
    # Preserve source RGB for meaningful artwork pixels.
    #
    result[
        meaningful,
        :3,
    ] = rgba[
        meaningful,
        :3,
    ]

    return Image.fromarray(
        result,
        mode="RGBA",
    )


# =========================================================
# Envelope boundary extraction
# =========================================================


Point = tuple[int, int]
Edge = tuple[Point, Point]


def _envelope_path_data(
    envelope: np.ndarray,
) -> str:
    """
    Return SVG path data for the exterior artwork envelope.

    The envelope is expected to describe one physical artwork domain.
    If pixel topology produces multiple loops, the loop enclosing the
    greatest absolute area is treated as the exterior boundary.
    """

    if envelope.ndim != 2:
        raise PrepareError("Artwork envelope must be two-dimensional.")

    edges = _boundary_edges(
        envelope,
    )

    if not edges:
        raise PrepareError("Artwork envelope has no boundary.")

    loops = _boundary_loops(
        edges,
    )

    if not loops:
        raise PrepareError("Could not construct a closed artwork envelope boundary.")

    exterior = max(
        loops,
        key=lambda loop: abs(
            _signed_area(
                loop,
            )
        ),
    )

    exterior = _simplify_loop(
        exterior,
    )

    if len(exterior) < 4:
        raise PrepareError("Artwork envelope boundary contains insufficient geometry.")

    return _svg_path_data(
        exterior,
    )


def _write_envelope_svg(
    envelope: np.ndarray,
    output: Path,
) -> None:
    """
    Write the exterior artwork envelope as a border-only SVG.

    The SVG is intentionally diagnostic geometry: it contains no fill
    and represents only the physical outer boundary of the artwork.
    """

    if envelope.ndim != 2:
        raise PrepareError("Artwork envelope must be two-dimensional.")

    height, width = envelope.shape

    if width < 1 or height < 1:
        raise PrepareError("Artwork envelope has invalid dimensions.")

    path_data = _envelope_path_data(
        envelope,
    )

    svg = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<svg xmlns="http://www.w3.org/2000/svg"\n'
        f'     width="{width}"\n'
        f'     height="{height}"\n'
        f'     viewBox="0 0 {width} {height}">\n'
        f'  <path d="{path_data}"\n'
        '        fill="none"\n'
        '        stroke="#000000"\n'
        '        stroke-width="1"/>\n'
        "</svg>\n"
    )

    try:
        output.write_text(
            svg,
            encoding="utf-8",
        )

    except OSError as exc:
        raise PrepareError(f"Could not write artwork envelope: {output}") from exc


def _boundary_edges(
    mask: np.ndarray,
) -> list[Edge]:
    """
    Return oriented pixel edges forming the mask boundary.

    Edges are oriented consistently around filled pixels.
    """

    height, width = mask.shape

    edges: list[Edge] = []

    for y in range(height):
        for x in range(width):
            if not mask[
                y,
                x,
            ]:
                continue

            #
            # Top
            #
            if (
                y == 0
                or not mask[
                    y - 1,
                    x,
                ]
            ):
                edges.append(
                    (
                        (x, y),
                        (x + 1, y),
                    )
                )

            #
            # Right
            #
            if (
                x == width - 1
                or not mask[
                    y,
                    x + 1,
                ]
            ):
                edges.append(
                    (
                        (x + 1, y),
                        (x + 1, y + 1),
                    )
                )

            #
            # Bottom
            #
            if (
                y == height - 1
                or not mask[
                    y + 1,
                    x,
                ]
            ):
                edges.append(
                    (
                        (x + 1, y + 1),
                        (x, y + 1),
                    )
                )

            #
            # Left
            #
            if (
                x == 0
                or not mask[
                    y,
                    x - 1,
                ]
            ):
                edges.append(
                    (
                        (x, y + 1),
                        (x, y),
                    )
                )

    return edges


def _boundary_loops(
    edges: list[Edge],
) -> list[list[Point]]:
    """
    Assemble oriented boundary edges into closed loops.
    """

    outgoing: dict[
        Point,
        list[Point],
    ] = defaultdict(
        list,
    )

    for start, end in edges:
        outgoing[start].append(end)

    unused: set[Edge] = set(edges)

    loops: list[list[Point]] = []

    while unused:
        first = next(iter(unused))

        start, current = first

        unused.remove(first)

        loop = [
            start,
            current,
        ]

        while current != start:
            candidates = [
                end
                for end in outgoing.get(
                    current,
                    (),
                )
                if (
                    current,
                    end,
                )
                in unused
            ]

            if not candidates:
                raise PrepareError("Artwork envelope contains an open boundary.")

            next_point = candidates[0]

            unused.remove(
                (
                    current,
                    next_point,
                )
            )

            loop.append(next_point)

            current = next_point

        loops.append(loop)

    return loops


def _simplify_loop(
    points: list[Point],
) -> list[Point]:
    """
    Remove redundant collinear points from a closed boundary loop.
    """

    if len(points) < 4:
        return points

    #
    # The loop returned by _boundary_loops repeats its first point at
    # the end. Work on the unique points and restore closure afterward.
    #
    unique = points[:-1]

    if len(unique) < 3:
        return points

    simplified: list[Point] = []

    count = len(unique)

    for index, current in enumerate(unique):
        previous = unique[(index - 1) % count]

        following = unique[(index + 1) % count]

        if _collinear(
            previous,
            current,
            following,
        ):
            continue

        simplified.append(current)

    if not simplified:
        return points

    simplified.append(simplified[0])

    return simplified


def _collinear(
    first: Point,
    second: Point,
    third: Point,
) -> bool:
    """
    Return whether three points lie on one straight line.
    """

    return (second[0] - first[0]) * (third[1] - second[1]) == (second[1] - first[1]) * (
        third[0] - second[0]
    )


def _signed_area(
    points: list[Point],
) -> float:
    """
    Return the signed area enclosed by a closed polygon.
    """

    if len(points) < 4:
        return 0.0

    area = 0.0

    for first, second in zip(
        points,
        points[1:],
        strict=False,
    ):
        area += first[0] * second[1] - second[0] * first[1]

    return area / 2.0


def _svg_path_data(
    points: list[Point],
) -> str:
    """
    Convert a closed point sequence into SVG path data.
    """

    first = points[0]

    commands = [f"M {first[0]} {first[1]}"]

    for point in points[1:-1]:
        commands.append(f"L {point[0]} {point[1]}")

    commands.append("Z")

    return " ".join(commands)


# =========================================================
# Trace clipping
# =========================================================


SVG_NAMESPACE = "http://www.w3.org/2000/svg"


def _clip_trace_to_envelope(
    trace: Path,
    envelope: np.ndarray,
) -> None:
    """
    Constrain all traced artwork geometry to the physical envelope.

    Inkscape's multicolor bitmap trace may represent transparent raster
    background as a page-sized color region. The physical artwork
    envelope is authoritative, so all traced geometry is clipped to
    that envelope.

    The resulting trace remains self-contained: the envelope geometry
    is embedded in a clipPath rather than referenced from envelope.svg.
    """

    if not trace.is_file():
        raise PrepareError(f"Trace does not exist: {trace}")

    path_data = _envelope_path_data(
        envelope,
    )

    try:
        tree = ET.parse(
            trace,
        )

    except (
        OSError,
        ET.ParseError,
    ) as exc:
        raise PrepareError(f"Could not read trace SVG: {trace}") from exc

    root = tree.getroot()

    if (
        _local_name(
            root.tag,
        )
        != "svg"
    ):
        raise PrepareError(f"Trace does not contain an SVG root element: {trace}")

    ET.register_namespace(
        "",
        SVG_NAMESPACE,
    )

    defs = ET.Element(
        _svg_tag(
            "defs",
        )
    )

    clip_path = ET.SubElement(
        defs,
        _svg_tag(
            "clipPath",
        ),
        {
            "id": "artwork-envelope",
            "clipPathUnits": "userSpaceOnUse",
        },
    )

    ET.SubElement(
        clip_path,
        _svg_tag(
            "path",
        ),
        {
            "d": path_data,
        },
    )

    #
    # Keep metadata and definitions at the SVG root. Move all drawable
    # root-level content into one clipped group.
    #
    drawable: list[ET.Element] = []

    for child in list(
        root,
    ):
        if _local_name(
            child.tag,
        ) in {
            "defs",
            "metadata",
            "namedview",
            "title",
            "desc",
        }:
            continue

        drawable.append(child)

    if not drawable:
        raise PrepareError(f"Trace contains no drawable geometry: {trace}")

    root.insert(
        0,
        defs,
    )

    group = ET.Element(
        _svg_tag(
            "g",
        ),
        {
            "id": "artwork",
            "clip-path": "url(#artwork-envelope)",
        },
    )

    for child in drawable:
        root.remove(
            child,
        )

        group.append(child)

    root.append(
        group,
    )

    try:
        tree.write(
            trace,
            encoding="utf-8",
            xml_declaration=True,
        )

    except OSError as exc:
        raise PrepareError(f"Could not write clipped trace SVG: {trace}") from exc


def _svg_tag(
    name: str,
) -> str:
    """
    Return an SVG-qualified XML element name.
    """

    return f"{{{SVG_NAMESPACE}}}{name}"


def _local_name(
    tag: str,
) -> str:
    """
    Return the local portion of an XML element name.
    """

    return tag.rsplit(
        "}",
        1,
    )[-1]


# =========================================================
# Multicolor tracing
# =========================================================


def _trace_multicolor(
    source: Path,
    output: Path,
    *,
    colors: int,
    smooth: bool = True,
    stack: bool = True,
    remove_background: bool = False,
    speckles: int = DEFAULT_SPECKLES,
    smooth_corners: float = DEFAULT_SMOOTH_CORNERS,
    optimize: float = DEFAULT_OPTIMIZE,
) -> None:
    """
    Trace a normalized PNG into an inspectable multicolor SVG.
    """

    source = Path(
        source,
    )

    output = Path(
        output,
    ).resolve()

    _require_source(
        source,
    )

    _require_svg_output(
        source,
        output,
        label="Trace",
    )

    if colors < 2:
        raise PrepareError("Trace color count must be at least two.")

    if speckles < 0:
        raise PrepareError("Trace speckle size cannot be negative.")

    if smooth_corners < 0:
        raise PrepareError("Trace corner smoothing cannot be negative.")

    if optimize < 0:
        raise PrepareError("Trace optimization tolerance cannot be negative.")

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    trace_parameters = ",".join(
        (
            str(
                colors,
            ),
            _bool_value(
                smooth,
            ),
            _bool_value(
                stack,
            ),
            _bool_value(
                remove_background,
            ),
            str(
                speckles,
            ),
            str(
                smooth_corners,
            ),
            str(
                optimize,
            ),
        )
    )

    actions = (
        "select-all",
        f"object-trace:{trace_parameters}",
        "export-type:svg",
        f"export-filename:{output}",
        "export-area-page",
        "export-do",
    )

    try:
        run(
            source,
            actions=actions,
        )

    except InkscapeError as exc:
        raise PrepareError(f"Could not trace source artwork: {source}") from exc

    if not output.is_file():
        raise PrepareError(f"Inkscape did not create the expected trace output: {output}")


# =========================================================
# Helpers
# =========================================================


def _bool_value(
    value: bool,
) -> str:
    """
    Return the boolean representation expected by Inkscape's
    object-trace action.
    """

    return "true" if value else "false"


__all__ = [
    "PrepareError",
    "execute",
]
