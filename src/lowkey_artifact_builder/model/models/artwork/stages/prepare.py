"""
Artwork prepare stage.

The prepare stage analyzes materialized raster artwork before converting
it into a multicolor SVG trace.

Preparation establishes the physical artwork envelope and preserves
source color information for tracing. Pixels outside the physical
envelope are excluded from the prepared raster.

The stage produces:

    trace.svg
        Multicolor SVG trace of the prepared source Artwork.

    envelope.svg
        SVG containing only the closed outer boundary of the Artwork.

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
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, cast

import numpy as np
from PIL import Image
from scipy import ndimage

from lowkey_artifact_builder.engine import (
    StageContext,
)
from lowkey_artifact_builder.logging_config import get_logger
from lowkey_artifact_builder.tools.inkscape import (
    InkscapeError,
    run,
)

# =========================================================
# Errors
# =========================================================

logger = get_logger(__name__)


class PrepareError(RuntimeError):
    """
    Raised when artwork preparation cannot be completed.
    """


COMPLEX_EXTERIOR_WARNING = (
    "Artwork has a complex exterior background. "
    "Shrink-wrap may produce an inaccurate envelope. "
    "Consider removing the background or replacing it with "
    "transparency or a uniform color."
)

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

DEFAULT_ENVELOPE_MODE = "alpha"

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
# Maximum Euclidean RGB distance from the inferred exterior-background
# color for a pixel to remain a background candidate.
#
# This tolerance accommodates small raster variation in visually uniform
# backgrounds without making it part of the public Artwork configuration.
#
DEFAULT_SHRINK_WRAP_BACKGROUND_DISTANCE = 12.0

#
# Minimum RGB component value for a pixel to be considered near-white
# background when a transparent crop exposes no meaningful exterior
# boundary color.
#
DEFAULT_SHRINK_WRAP_WHITE_MINIMUM = 240

# =========================================================
# Helpers
# =========================================================


def _has_complex_opaque_exterior(
    rgba: np.ndarray,
    meaningful: np.ndarray,
) -> bool:
    """
    Return whether an opaque source boundary is too diverse for reliable
    single-color exterior-background inference.
    """

    boundary = np.zeros(
        meaningful.shape,
        dtype=bool,
    )

    boundary[0, :] = True
    boundary[-1, :] = True
    boundary[:, 0] = True
    boundary[:, -1] = True

    boundary_meaningful = boundary & meaningful

    #
    # Transparency provides an explicit exterior-background signal.
    # Complexity detection is needed only when the complete source
    # boundary is meaningful.
    #
    if not np.all(
        meaningful[boundary],
    ):
        return False

    boundary_rgb = rgba[
        boundary_meaningful,
        :3,
    ].astype(
        np.float64,
    )

    if boundary_rgb.size == 0:
        return False

    representative_rgb = np.median(
        boundary_rgb,
        axis=0,
    )

    distances = np.linalg.norm(
        boundary_rgb - representative_rgb,
        axis=1,
    )

    return bool(np.any(distances > DEFAULT_SHRINK_WRAP_BACKGROUND_DISTANCE))


# =========================================================
# Public interface
# =========================================================


def execute(
    context: StageContext,
) -> None:
    """
    Execute the Artwork prepare stage.

    Preparation establishes the physical Artwork envelope and produces
    a multicolor SVG trace from source color information.

    Processing:

        1. Load the source PNG.
        2. Resolve the requested Artifact color count.
        3. Identify meaningful visible source Artwork.
        4. Construct the physical Artwork envelope.
        5. Write envelope.svg.
        6. Preserve source colors within the physical envelope.
        7. Trace the prepared raster using artifact_color_count colors.
        8. Clip the resulting trace to the physical envelope.

    Physical printer-color selection and assignment are not Prepare
    responsibilities.

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

    artifact_color_count = context.resolver(
        "artifact_color_count",
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
    # Determine the configured envelope strategy and construct the
    # physical Artwork envelope.
    #
    try:
        envelope_mode = context.resolver(
            "artwork_envelope_mode",
        )

    except KeyError:
        envelope_mode = DEFAULT_ENVELOPE_MODE

    envelope = _derive_envelope(
        image,
        mode=envelope_mode,
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
    # Preserve source color information within the physical envelope.
    # Pixels outside the envelope remain transparent.
    #
    prepared = _prepare_source_image(
        image,
        envelope,
    )

    #
    # The prepared raster is an implementation detail rather than a
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

        prepared.save(
            temporary_path,
            format="PNG",
        )

        #
        # Discover the requested number of intrinsic Artifact colors
        # directly from the prepared source raster.
        #
        _trace_multicolor(
            temporary_path,
            trace_output,
            colors=artifact_color_count,
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


def _derive_envelope(
    image: Image.Image,
    *,
    mode: str,
) -> np.ndarray:
    """
    Derive the Artwork envelope using the configured model strategy.
    """

    if mode == "alpha":
        foreground = _foreground_mask(
            image,
        )

        return _build_envelope(
            foreground,
        )

    if mode == "shrink-wrap":
        foreground, exterior = _shrink_wrap_foreground_mask(
            image,
        )

        return _build_envelope(
            foreground,
            excluded=exterior,
        )

    raise PrepareError(f"Unsupported artwork envelope mode: {mode!r}.")


def _shrink_wrap_foreground_mask(
    image: Image.Image,
) -> tuple[
    np.ndarray,
    np.ndarray,
]:
    """
    Return shrink-wrap foreground and known exterior background.

    Exterior background is classified first from source appearance and
    ordinary exterior connectivity. This preserves legitimate concavities
    and narrow crevices in the Artwork boundary.

    A second geometric pass identifies exterior-connected background
    intrusions that enter through a narrow passage and penetrate
    disproportionately deeply into the Artwork domain. Those intrusions are
    removed from the exterior classification so subsequent envelope
    construction can bridge and fill them.

    The geometric correction affects only exterior classification. It does
    not directly modify source Artwork pixels.
    """

    rgba = np.asarray(
        image,
        dtype=np.uint8,
    )

    if rgba.ndim != 3 or rgba.shape[2] != 4:
        raise PrepareError("Shrink-wrap source image must be RGBA.")

    height, width = rgba.shape[:2]

    if height < 1 or width < 1:
        raise PrepareError("Shrink-wrap source image cannot be empty.")

    alpha = rgba[
        :,
        :,
        3,
    ]

    meaningful = alpha >= DEFAULT_ALPHA_THRESHOLD

    if _has_complex_opaque_exterior(
        rgba,
        meaningful,
    ):
        logger.warning(
            COMPLEX_EXTERIOR_WARNING,
        )

    transparent = ~meaningful

    #
    # Collect the rectangular source boundary.
    #
    boundary_rgba = np.concatenate(
        (
            rgba[
                0,
                :,
                :,
            ],
            rgba[
                height - 1,
                :,
                :,
            ],
            rgba[
                :,
                0,
                :,
            ],
            rgba[
                :,
                width - 1,
                :,
            ],
        ),
        axis=0,
    )

    boundary_meaningful = (
        boundary_rgba[
            :,
            3,
        ]
        >= DEFAULT_ALPHA_THRESHOLD
    )

    if np.any(
        boundary_meaningful,
    ):
        #
        # Infer ordinary exterior background color from meaningful pixels
        # on the rectangular source boundary.
        #
        background_rgb = np.median(
            boundary_rgba[
                boundary_meaningful,
                :3,
            ].astype(
                np.float64,
            ),
            axis=0,
        )

        rgb = rgba[
            :,
            :,
            :3,
        ].astype(
            np.float64,
        )

        difference = rgb - background_rgb

        background_distance = np.sqrt(
            np.sum(
                difference * difference,
                axis=2,
            )
        )

        background_like = meaningful & (
            background_distance <= DEFAULT_SHRINK_WRAP_BACKGROUND_DISTANCE
        )

    else:
        #
        # RGB values beneath transparent pixels are not reliable. For a
        # transparent crop, visible near-white pixels may nevertheless be
        # connected to the transparent exterior and therefore constitute
        # clean exterior background.
        #
        rgb = rgba[
            :,
            :,
            :3,
        ]

        background_like = (
            meaningful
            & (
                rgb[
                    :,
                    :,
                    0,
                ]
                >= DEFAULT_SHRINK_WRAP_WHITE_MINIMUM
            )
            & (
                rgb[
                    :,
                    :,
                    1,
                ]
                >= DEFAULT_SHRINK_WRAP_WHITE_MINIMUM
            )
            & (
                rgb[
                    :,
                    :,
                    2,
                ]
                >= DEFAULT_SHRINK_WRAP_WHITE_MINIMUM
            )
        )

    background_candidate = transparent | background_like

    #
    # First determine exterior background using the unmodified connectivity
    # domain. This is intentionally the detailed behavior: narrow exterior
    # crevices remain reachable at this stage.
    #
    boundary_seed = np.zeros(
        (
            height,
            width,
        ),
        dtype=bool,
    )

    boundary_seed[
        0,
        :,
    ] = background_candidate[
        0,
        :,
    ]

    boundary_seed[
        height - 1,
        :,
    ] = background_candidate[
        height - 1,
        :,
    ]

    boundary_seed[
        :,
        0,
    ] |= background_candidate[
        :,
        0,
    ]

    boundary_seed[
        :,
        width - 1,
    ] |= background_candidate[
        :,
        width - 1,
    ]

    exterior = np.asarray(
        ndimage.binary_propagation(
            boundary_seed,
            mask=background_candidate,
        ),
        dtype=bool,
    )

    #
    # Construct a second exterior classification in which small breaks in
    # visible Artwork temporarily act as closed barriers.
    #
    # The difference between the ordinary exterior and this protected
    # exterior identifies background reached only through such narrow
    # passages.
    #
    foreground_candidate = meaningful & ~background_like

    structure = _disk_structure(
        DEFAULT_ENVELOPE_CLOSE_PIXELS,
    )

    connectivity_barrier = np.asarray(
        ndimage.binary_closing(
            foreground_candidate,
            structure=structure,
        ),
        dtype=bool,
    )

    protected_background = np.asarray(
        background_candidate & ~connectivity_barrier,
        dtype=bool,
    )

    protected_seed = np.zeros(
        (
            height,
            width,
        ),
        dtype=bool,
    )

    protected_seed[
        0,
        :,
    ] = protected_background[
        0,
        :,
    ]

    protected_seed[
        height - 1,
        :,
    ] = protected_background[
        height - 1,
        :,
    ]

    protected_seed[
        :,
        0,
    ] |= protected_background[
        :,
        0,
    ]

    protected_seed[
        :,
        width - 1,
    ] |= protected_background[
        :,
        width - 1,
    ]

    protected_exterior = np.asarray(
        ndimage.binary_propagation(
            protected_seed,
            mask=protected_background,
        ),
        dtype=bool,
    )

    #
    # Pixels reachable normally but not through the protected connectivity
    # domain are potential narrow-mouth concavities.
    #
    intrusion = np.asarray(
        exterior & ~protected_exterior,
        dtype=bool,
    )

    #
    # Analyze each potential intrusion independently.
    #
    # Closing contributes a thin bridge at the mouth itself. We do not want
    # that bridge alone to cause an ordinary shallow crevice to be repaired.
    # Only a connected intrusion whose depth is disproportionately large
    # relative to the closing scale is removed from exterior classification.
    #
    label_result = cast(
        tuple[Any, int],
        ndimage.label(
            intrusion,
        ),
    )

    intrusion_labels = np.asarray(
        label_result[0],
        dtype=np.intp,
    )

    intrusion_count = label_result[1]

    repaired_exterior = exterior.copy()

    minimum_deep_intrusion = DEFAULT_ENVELOPE_CLOSE_PIXELS * 4

    for label in range(
        1,
        intrusion_count + 1,
    ):
        region = intrusion_labels == label

        coordinates = np.argwhere(
            region,
        )

        if coordinates.size == 0:
            continue

        #
        # Estimate geometric depth using the larger span of the connected
        # intrusion. For the narrow-passage cases targeted here, the mouth
        # width is bounded by the closing scale while the intrusion extends
        # substantially farther along its penetration axis.
        #
        minimum_y = int(
            coordinates[
                :,
                0,
            ].min()
        )
        maximum_y = int(
            coordinates[
                :,
                0,
            ].max()
        )
        minimum_x = int(
            coordinates[
                :,
                1,
            ].min()
        )
        maximum_x = int(
            coordinates[
                :,
                1,
            ].max()
        )

        span_y = maximum_y - minimum_y + 1
        span_x = maximum_x - minimum_x + 1

        depth = max(
            span_x,
            span_y,
        )

        if depth >= minimum_deep_intrusion:
            repaired_exterior[region] = False

    exterior = np.asarray(
        repaired_exterior,
        dtype=bool,
    )

    foreground = np.asarray(
        meaningful & ~exterior,
        dtype=bool,
    )

    return (
        foreground,
        exterior,
    )


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
    *,
    excluded: np.ndarray | None = None,
) -> np.ndarray:
    """
    Derive a solid artwork envelope from meaningful source foreground.

    Processing consists of:

        1. Remove insignificant connected foreground regions.
        2. Bridge small gaps in the remaining silhouette.
        3. Fill enclosed regions.
        4. Exclude any source regions already classified as exterior
           background.
        5. Retain the primary physical envelope.

    excluded identifies known exterior background that envelope morphology
    must not reintroduce. Ordinary enclosed holes remain fillable.
    """

    if foreground.ndim != 2:
        raise PrepareError("Artwork foreground mask must be two-dimensional.")

    if excluded is not None:
        if excluded.ndim != 2:
            raise PrepareError("Excluded background mask must be two-dimensional.")

        if excluded.shape != foreground.shape:
            raise PrepareError(
                "Excluded background dimensions do not match the artwork foreground."
            )

        protected = np.asarray(
            excluded,
            dtype=bool,
        )

    else:
        protected = np.zeros_like(
            foreground,
            dtype=bool,
        )

    cleaned = _remove_small_components(
        foreground,
        minimum_pixels=DEFAULT_ENVELOPE_MIN_PIXELS,
    )

    if not np.any(
        cleaned,
    ):
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

    #
    # Morphological closing may bridge small breaks across known exterior
    # background. Restore that classification before determining enclosed
    # regions.
    #
    closed &= ~protected

    filled = np.asarray(
        ndimage.binary_fill_holes(
            closed,
        ),
        dtype=bool,
    )

    #
    # Hole filling operates only on mask topology and cannot distinguish a
    # genuine interior hole from source pixels already known to be exterior
    # background. Preserve the source classification explicitly.
    #
    filled &= ~protected

    envelope = _retain_primary_envelope(
        filled,
    )

    #
    # Keep the invariant explicit at the returned boundary as well:
    # classified exterior background can never belong to the envelope.
    #
    envelope &= ~protected

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


def _prepare_source_image(
    image: Image.Image,
    envelope: np.ndarray,
) -> Image.Image:
    """
    Prepare source Artwork for multicolor tracing.

    Source RGBA values are preserved within the physical Artwork
    envelope. Pixels outside the envelope are fully transparent.

    Prepare does not assign physical printer colors or synthesize a
    configured Artwork fill color.
    """

    rgba = np.asarray(
        image,
        dtype=np.uint8,
    )

    if envelope.shape != rgba.shape[:2]:
        raise PrepareError("Artwork envelope dimensions do not match the source image.")

    result = np.zeros_like(
        rgba,
        dtype=np.uint8,
    )

    result[envelope,] = rgba[envelope,]

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
