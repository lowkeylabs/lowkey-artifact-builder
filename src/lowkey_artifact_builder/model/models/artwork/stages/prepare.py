"""
Artwork prepare stage.

The prepare stage analyzes materialized source Artwork and produces
manufacturing-ready SVG geometry and a physical Artwork envelope.

PNG sources are normalized and traced according to the effective
Artifact color count:

    1 color:
        Single-color tracing of meaningful foreground occupancy
        into one compound SVG path.

    2 or more colors:
        Inkscape multicolor tracing, preserving source color
        regions for downstream Artwork registration.

Native SVG sources preserve authored vector geometry and colors
without raster tracing.

The stage produces:

    trace.svg
        SVG geometry representing prepared source Artwork.

    envelope.svg
        SVG containing the physical Artwork envelope boundary.

For PNG sources, the physical envelope constrains the resulting
trace geometry. Pixels outside that envelope are excluded from
the prepared raster.

Filesystem layout and configuration resolution are responsibilities
of the build engine. This implementation consumes only the inputs,
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

    PNG sources are normalized and traced into SVG geometry.

    The resolved artifact_color_count is the maximum permitted
    number of meaningful foreground colors. Fewer discovered
    colors are preserved; excess colors are reduced by multicolor
    tracing when the effective maximum is at least two.

    Native SVG sources preserve authored vector geometry and
    colors without raster tracing.

    Both source formats produce trace.svg and envelope.svg.
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

    try:
        envelope_mode = context.resolver(
            "artwork_envelope_mode",
        )
    except KeyError:
        envelope_mode = DEFAULT_ENVELOPE_MODE

    if source.suffix.lower() == ".svg":
        _prepare_svg_source(
            source,
            trace_output,
            envelope_output,
            envelope_mode=envelope_mode,
        )
        return

    # The configuration layer supplies an explicit or derived
    # maximum, validated against available printer positions.
    maximum_color_count = context.resolver(
        "artifact_color_count",
    )

    if (
        isinstance(maximum_color_count, bool)
        or not isinstance(maximum_color_count, int)
        or maximum_color_count < 1
    ):
        raise PrepareError("artifact_color_count must be a positive integer.")

    image = _load_source_image(
        source,
    )

    envelope = _derive_envelope(
        image,
        mode=envelope_mode,
    )

    if not np.any(envelope):
        raise PrepareError("Could not derive an artwork envelope from the source image.")

    _write_envelope_svg(
        envelope,
        envelope_output,
    )

    prepared = _prepare_source_image(
        image,
        envelope,
    )

    discovered_color_count = _discover_png_color_count(
        prepared,
    )

    effective_color_count = min(
        discovered_color_count,
        maximum_color_count,
    )

    if discovered_color_count > maximum_color_count and maximum_color_count == 1:
        raise PrepareError(
            "ARTWORK: Reducing multicolor artwork to one color "
            "is not supported by the current single-color tracer."
        )

    logger.info(
        "ARTWORK: Discovered %d foreground colors; maximum=%d; effective tracing count=%d.",
        discovered_color_count,
        maximum_color_count,
        effective_color_count,
    )

    if discovered_color_count > maximum_color_count:
        logger.info(
            "ARTWORK: Reducing source artwork from %d to "
            "at most %d colors through Inkscape tracing.",
            discovered_color_count,
            effective_color_count,
        )

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

        if effective_color_count == 1:
            _trace_single_color(
                temporary_path,
                trace_output,
            )
        else:
            _trace_multicolor(
                temporary_path,
                trace_output,
                colors=effective_color_count,
            )

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
    Validate the source Artwork file.

    PNG and SVG are supported source formats.
    """

    if not source.is_file():
        raise PrepareError(f"Source artwork does not exist: {source}")

    if source.suffix.lower() not in {".png", ".svg"}:
        raise PrepareError(f"Source artwork must be a PNG or SVG file: {source}")


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


def _derive_svg_envelope(
    source: Path,
    output: Path,
    *,
    mode: str,
) -> None:
    """
    Derive the physical envelope of native SVG artwork.

    Preserve every visible component, including disconnected regions
    and interior holes. Native SVG geometry is authoritative and is
    not subjected to raster noise removal, morphological closing,
    hole filling, or primary-component selection.

    Rendering is used only to obtain the visible silhouette.
    The authored vector geometry remains unchanged in trace.svg.
    """

    if mode not in {"alpha", "shrink-wrap"}:
        raise PrepareError(f"Unsupported artwork envelope mode: {mode!r}.")

    temporary_path: Path | None = None

    try:
        with NamedTemporaryFile(
            prefix="artwork-svg-envelope-",
            suffix=".png",
            dir=output.parent,
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)

        actions = (
            "export-area-page",
            "export-background-opacity:0",
            "export-type:png",
            f"export-filename:{temporary_path}",
            "export-do",
        )

        try:
            run(source, actions=actions)
        except InkscapeError as exc:
            raise PrepareError(f"Could not render SVG for envelope derivation: {source}") from exc

        if not temporary_path.is_file():
            raise PrepareError(f"SVG envelope rendering did not produce an image: {source}")

        try:
            with Image.open(temporary_path) as rendered:
                image = rendered.convert("RGBA")
                envelope = _foreground_mask(image)
        except OSError as exc:
            raise PrepareError(f"Could not read rendered SVG envelope: {source}") from exc

        if not np.any(envelope):
            raise PrepareError("Could not derive an artwork envelope from the SVG source.")

        _write_envelope_svg(
            envelope,
            output,
            preserve_all=True,
        )

    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass


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
) -> tuple[np.ndarray, np.ndarray]:
    """
    Return shrink-wrap foreground and known exterior background.

    Exterior background is classified first from source appearance and
    ordinary exterior connectivity. This preserves legitimate concavities
    and narrow crevices in the Artwork boundary.

    Transparent boundary pixels establish exterior background directly.
    Meaningful boundary pixels are used to infer an additional opaque
    background color only when they provide sufficiently consistent
    evidence of an exterior background.

    A second geometric pass identifies exterior-connected background
    intrusions that enter through a narrow passage and penetrate
    disproportionately deeply into the Artwork domain. Those intrusions
    are removed from exterior classification so subsequent envelope
    construction can bridge and fill them.

    The geometric correction affects only exterior classification. It
    does not directly modify source Artwork pixels.
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

    alpha = rgba[:, :, 3]
    meaningful = alpha >= DEFAULT_ALPHA_THRESHOLD
    transparent = ~meaningful

    if _has_complex_opaque_exterior(rgba, meaningful):
        logger.warning(COMPLEX_EXTERIOR_WARNING)

    #
    # Collect the rectangular source boundary.
    #
    boundary_rgba = np.concatenate(
        (
            rgba[0, :, :],
            rgba[height - 1, :, :],
            rgba[:, 0, :],
            rgba[:, width - 1, :],
        ),
        axis=0,
    )

    boundary_meaningful = boundary_rgba[:, 3] >= DEFAULT_ALPHA_THRESHOLD

    #
    # Infer a possible opaque exterior background color.
    #
    # Transparent pixels themselves establish exterior background.
    # Opaque pixels touching the boundary are not necessarily
    # background: they may be legitimate Artwork.
    #
    # In particular, a black cross on transparent background can
    # touch all four boundaries. Its black pixels must not become
    # background merely because they appear at the raster edge.
    #
    boundary_rgb = boundary_rgba[
        boundary_meaningful,
        :3,
    ].astype(np.float64)

    boundary_count = len(boundary_rgba)
    meaningful_count = len(boundary_rgb)

    meaningful_fraction = meaningful_count / boundary_count

    #
    # Require a substantial meaningful boundary before treating its
    # color as an exterior-background candidate.
    #
    # This avoids interpreting sparse boundary-touching Artwork as
    # background while retaining inference for predominantly opaque
    # source images.
    #
    infer_opaque_background = meaningful_count > 0 and meaningful_fraction >= 0.5

    if infer_opaque_background:
        background_rgb = np.median(
            boundary_rgb,
            axis=0,
        )

        #
        # Check whether the inferred color is representative of the
        # meaningful boundary rather than an arbitrary foreground
        # color appearing at a few edge locations.
        #
        boundary_difference = boundary_rgb - background_rgb

        boundary_distance = np.sqrt(
            np.sum(
                boundary_difference * boundary_difference,
                axis=1,
            )
        )

        consistent_fraction = float(
            np.mean(boundary_distance <= DEFAULT_SHRINK_WRAP_BACKGROUND_DISTANCE)
        )

        infer_opaque_background = consistent_fraction >= 0.5

    if infer_opaque_background:
        rgb = rgba[:, :, :3].astype(np.float64)

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
        # A predominantly transparent source boundary may surround
        # an opaque white crop containing legitimate Artwork.
        #
        # Treat near-white pixels as possible exterior background,
        # but exclude them only when connected to the source exterior.
        #
        # Enclosed opaque white Artwork remains foreground.
        #
        rgb = rgba[:, :, :3]

        background_like = meaningful & np.all(
            rgb >= DEFAULT_SHRINK_WRAP_WHITE_MINIMUM,
            axis=2,
        )

    background_candidate = transparent | background_like

    #
    # First determine exterior background using the unmodified
    # connectivity domain. Narrow exterior crevices remain reachable.
    #
    boundary_seed = np.zeros(
        (height, width),
        dtype=bool,
    )

    boundary_seed[0, :] = background_candidate[0, :]
    boundary_seed[height - 1, :] = background_candidate[height - 1, :]
    boundary_seed[:, 0] |= background_candidate[:, 0]
    boundary_seed[:, width - 1] |= background_candidate[:, width - 1]

    exterior = np.asarray(
        ndimage.binary_propagation(
            boundary_seed,
            mask=background_candidate,
        ),
        dtype=bool,
    )

    #
    # Construct a second exterior classification in which small
    # breaks in visible Artwork temporarily act as closed barriers.
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
        (height, width),
        dtype=bool,
    )

    protected_seed[0, :] = protected_background[0, :]
    protected_seed[height - 1, :] = protected_background[height - 1, :]
    protected_seed[:, 0] |= protected_background[:, 0]
    protected_seed[:, width - 1] |= protected_background[:, width - 1]

    protected_exterior = np.asarray(
        ndimage.binary_propagation(
            protected_seed,
            mask=protected_background,
        ),
        dtype=bool,
    )

    #
    # Pixels reachable normally but not through protected
    # connectivity are potential narrow-mouth concavities.
    #
    intrusion = np.asarray(
        exterior & ~protected_exterior,
        dtype=bool,
    )

    label_result = cast(
        tuple[Any, int],
        ndimage.label(intrusion),
    )

    intrusion_labels = np.asarray(
        label_result[0],
        dtype=np.intp,
    )

    intrusion_count = label_result[1]

    repaired_exterior = exterior.copy()

    minimum_deep_intrusion = DEFAULT_ENVELOPE_CLOSE_PIXELS * 4

    for label in range(1, intrusion_count + 1):
        region = intrusion_labels == label

        coordinates = np.argwhere(region)

        if coordinates.size == 0:
            continue

        #
        # Estimate geometric depth using the larger span of the
        # connected intrusion.
        #
        minimum_y = int(coordinates[:, 0].min())
        maximum_y = int(coordinates[:, 0].max())
        minimum_x = int(coordinates[:, 1].min())
        maximum_x = int(coordinates[:, 1].max())

        span_y = maximum_y - minimum_y + 1
        span_x = maximum_x - minimum_x + 1

        depth = max(span_x, span_y)

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

    Meaningful foreground may touch any source raster boundary.
    Morphological closing must preserve that foreground without
    requiring transparent padding in the source Artwork.

    excluded identifies known exterior background that envelope
    morphology must not reintroduce. Ordinary enclosed holes remain
    fillable.
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

    #
    # Remove insignificant connected foreground components.
    #
    cleaned = _remove_small_components(
        foreground,
        minimum_pixels=DEFAULT_ENVELOPE_MIN_PIXELS,
    )

    if not np.any(cleaned):
        raise PrepareError("No meaningful foreground remains after envelope cleanup.")

    #
    # Construct the closing element.
    #
    structure = _disk_structure(
        DEFAULT_ENVELOPE_CLOSE_PIXELS,
    )

    #
    # Morphological closing may erode foreground touching the source
    # raster boundary because pixels outside the array are treated
    # as background.
    #
    # Pad the mask before closing, then crop the result back to its
    # original dimensions. This preserves boundary-touching Artwork
    # without changing source dimensions or registration.
    #
    padding = DEFAULT_ENVELOPE_CLOSE_PIXELS

    padded = np.pad(
        cleaned,
        pad_width=padding,
        mode="constant",
        constant_values=False,
    )

    padded_closed = np.asarray(
        ndimage.binary_closing(
            padded,
            structure=structure,
        ),
        dtype=bool,
    )

    closed = np.asarray(
        padded_closed[
            padding:-padding,
            padding:-padding,
        ],
        dtype=bool,
    )

    #
    # Morphological closing may bridge small breaks across known
    # exterior background. Restore that classification before
    # determining enclosed regions.
    #

    closed &= ~protected

    #
    # Preserve meaningful source foreground at the raster boundary,
    # but do not allow closing to introduce new boundary pixels.
    #
    closed[0, :] = cleaned[0, :]
    closed[-1, :] = cleaned[-1, :]
    closed[:, 0] = cleaned[:, 0]
    closed[:, -1] = cleaned[:, -1]

    #
    # Fill enclosed regions in the resulting silhouette.
    #
    filled = np.asarray(
        ndimage.binary_fill_holes(
            closed,
        ),
        dtype=bool,
    )

    #
    # Hole filling operates only on mask topology and cannot
    # distinguish a genuine interior hole from source pixels
    # already known to be exterior background.
    #
    # Preserve the source classification explicitly.
    #
    filled &= ~protected

    #
    # Retain the primary physical envelope.
    #
    envelope = _retain_primary_envelope(
        filled,
    )

    #
    # Keep the invariant explicit at the returned boundary:
    # classified exterior background can never belong to
    # the envelope.
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


def _prepare_svg_source(
    source: Path,
    trace_output: Path,
    envelope_output: Path,
    *,
    envelope_mode: str,
) -> None:
    """
    Prepare native SVG artwork without retracing its geometry.

    Validate the SVG source, normalize circles into paths, assign
    deterministic IDs, and derive the physical envelope independently.

    Preserve authored geometry, groups, transforms, colors, and
    fill rules in the normalized trace product.
    """

    try:
        tree = ET.parse(
            source,
        )

    except (
        OSError,
        ET.ParseError,
    ) as exc:
        raise PrepareError(f"Could not parse source SVG: {source}") from exc

    root = tree.getroot()

    if _local_name(root.tag) != "svg":
        raise PrepareError(f"Source does not contain an SVG root element: {source}")

    for element in root.iter():
        if _local_name(element.tag) == "image":
            raise PrepareError("Embedded raster images are unsupported in native SVG artwork.")

    _normalize_native_svg_circles(root)

    _assign_native_svg_path_ids(root)

    _derive_svg_envelope(
        source,
        envelope_output,
        mode=envelope_mode,
    )

    ET.register_namespace(
        "",
        SVG_NAMESPACE,
    )

    try:
        tree.write(
            trace_output,
            encoding="utf-8",
            xml_declaration=True,
        )

    except OSError as exc:
        raise PrepareError(f"Could not write native SVG trace: {trace_output}") from exc


def _normalize_native_svg_circles(
    root: ET.Element,
) -> None:
    """
    Replace native SVG circles with equivalent closed paths.

    Preserve authored IDs, presentation attributes, styles,
    transforms, parent groups, and sibling order.

    Leave ID generation to _assign_native_svg_path_ids().
    """

    for parent in root.iter():
        for index, element in enumerate(list(parent)):
            if _local_name(element.tag) != "circle":
                continue

            try:
                cx = float(element.get("cx", "0"))
                cy = float(element.get("cy", "0"))
                radius = float(element.get("r", "0"))

            except ValueError as exc:
                raise PrepareError("Native SVG circle has invalid numeric geometry.") from exc

            if not all(np.isfinite(value) for value in (cx, cy, radius)):
                raise PrepareError("Native SVG circle geometry must be finite.")

            if radius <= 0:
                raise PrepareError("Native SVG circle radius must be positive.")

            def number(value: float) -> str:
                return f"{value:g}"

            right = number(cx + radius)
            left = number(cx - radius)
            center_y = number(cy)
            r = number(radius)

            path_data = (
                f"M {right} {center_y} "
                f"A {r} {r} 0 1 0 {left} {center_y} "
                f"A {r} {r} 0 1 0 {right} {center_y} Z"
            )

            attributes = {
                name: value
                for name, value in element.attrib.items()
                if name not in {"cx", "cy", "r"}
            }

            attributes["d"] = path_data

            path = ET.Element(
                _svg_tag("path"),
                attributes,
            )

            path.tail = element.tail

            parent.remove(element)
            parent.insert(index, path)


def _assign_native_svg_path_ids(
    root: ET.Element,
) -> None:
    """
    Assign deterministic, globally unique IDs to unnamed SVG paths.

    Preserve all authored IDs. Reject duplicate authored IDs and
    reserve IDs belonging to every SVG element, including groups
    and definitions.

    Generated IDs follow document order and use the path-NNN
    naming convention.
    """

    reserved_ids: set[str] = set()

    # Collect and validate authored IDs across the entire document.
    for element in root.iter():
        authored_id = element.get("id")

        if authored_id is None:
            continue

        if authored_id in reserved_ids:
            raise PrepareError(f"Duplicate SVG element ID: {authored_id!r}")

        reserved_ids.add(authored_id)

    next_index = 1

    # Assign IDs only to paths that do not already have one.
    for element in root.iter():
        if _local_name(element.tag) != "path":
            continue

        if element.get("id") is not None:
            continue

        while True:
            generated_id = f"path-{next_index:03d}"
            next_index += 1

            if generated_id not in reserved_ids:
                break

        element.set(
            "id",
            generated_id,
        )

        reserved_ids.add(generated_id)


def _discover_png_color_count(
    image: Image.Image,
) -> int:
    """
    Discover meaningful foreground colors in PNG artwork.

    Transparent pixels do not contribute Artifact colors.

    Discrete authored colors are inferred primarily from locally
    stable source-color regions. Intermediate RGB values occurring
    only along antialiased boundaries do not introduce additional
    Artifact colors.

    Preserve black and all other visible authored colors as
    foreground, independently of their RGB values.

    Continuous gradients remain ambiguous and are rejected rather
    than silently quantized.

    This function discovers color count only. It does not alter
    source pixels, assign physical printer colors, or quantize
    the image for tracing.
    """
    rgba = np.asarray(
        image.convert("RGBA"),
        dtype=np.uint8,
    )

    alpha_image = rgba[:, :, 3]

    meaningful = alpha_image >= DEFAULT_ALPHA_THRESHOLD

    if not np.any(meaningful):
        raise PrepareError("Cannot discover Artifact colors: no meaningful foreground pixels.")

    rgb_image = rgba[:, :, :3].astype(
        np.float64,
    )

    # -----------------------------------------------------
    # Continuous-gradient ambiguity detection
    # -----------------------------------------------------
    #
    # Preserve the existing gradient contract.
    #
    # A sufficiently long sequence of gradual RGB
    # transitions with substantial cumulative displacement
    # is evidence of an authored gradient rather than
    # discrete-color artwork.
    #
    minimum_step = 2.0
    maximum_step = 24.0
    minimum_run_steps = 12
    minimum_total_displacement = 96.0

    opaque = alpha_image == 255

    def contains_gradient_run(
        pixels: np.ndarray,
        valid: np.ndarray,
    ) -> bool:
        """
        Detect long, gradual color transitions along rows.
        """
        for row_pixels, row_valid in zip(
            pixels,
            valid,
            strict=True,
        ):
            run_start: int | None = None

            for index in range(
                1,
                len(row_pixels),
            ):
                if row_valid[index - 1] and row_valid[index]:
                    step = float(np.linalg.norm(row_pixels[index] - row_pixels[index - 1]))
                else:
                    step = 0.0

                gradual = minimum_step <= step <= maximum_step

                if gradual:
                    if run_start is None:
                        run_start = index - 1

                    run_steps = index - run_start

                    if run_steps >= minimum_run_steps:
                        displacement = float(
                            np.linalg.norm(row_pixels[index] - row_pixels[run_start])
                        )

                        if displacement >= minimum_total_displacement:
                            return True

                else:
                    run_start = None

        return False

    horizontal_gradient = contains_gradient_run(
        rgb_image,
        opaque,
    )

    vertical_gradient = contains_gradient_run(
        np.transpose(
            rgb_image,
            (1, 0, 2),
        ),
        opaque.T,
    )

    if horizontal_gradient or vertical_gradient:
        message = (
            "ARTWORK: Ambiguous continuous color gradient "
            "detected during automatic source-color discovery. "
            "Provide discrete-color artwork instead. "
            "An explicit artifact_color_count does not "
            "authorize silent color quantization."
        )

        logger.warning(
            message,
        )

        raise PrepareError(
            message,
        )

    # -----------------------------------------------------
    # Identify locally stable source-color regions
    # -----------------------------------------------------
    #
    # A pixel is a strong candidate for an authored color
    # when its surrounding neighborhood contains only
    # small RGB variations.
    #
    # Antialiased boundary pixels generally fail this test
    # because their neighbors belong to different colors.
    #
    # Use a 3x3 neighborhood. This is deliberately small
    # enough to retain detail while excluding most narrow
    # transition bands.
    #
    neighborhood_size = 3
    stability_tolerance = 18.0

    local_minimum = ndimage.minimum_filter(
        rgb_image,
        size=(neighborhood_size, neighborhood_size, 1),
        mode="nearest",
    )

    local_maximum = ndimage.maximum_filter(
        rgb_image,
        size=(neighborhood_size, neighborhood_size, 1),
        mode="nearest",
    )

    local_range = np.linalg.norm(
        local_maximum - local_minimum,
        axis=2,
    )

    # A stable color neighborhood must also consist
    # entirely of meaningful foreground pixels.
    #
    # This prevents transparent exterior RGB values
    # from influencing candidate selection.
    #
    neighborhood_foreground = ndimage.minimum_filter(
        meaningful.astype(np.uint8),
        size=neighborhood_size,
        mode="constant",
        cval=0,
    ).astype(bool)

    stable = meaningful & neighborhood_foreground & (local_range <= stability_tolerance)

    # -----------------------------------------------------
    # Select authored color representatives
    # -----------------------------------------------------
    #
    # Prefer stable pixels with the strongest alpha.
    #
    # Nearby RGB values are considered variations of
    # an existing authored color.
    #
    # Unlike the previous algorithm, intermediate
    # antialiasing colors do not become representatives
    # merely because their RGB distance exceeds the
    # clustering tolerance.
    #
    color_tolerance = 28.0

    representatives: list[np.ndarray] = []

    def add_colors(
        pixels: np.ndarray,
    ) -> None:
        """
        Register distinct candidate colors in descending
        pixel-frequency order.
        """
        if pixels.size == 0:
            return

        colors, counts = np.unique(
            pixels,
            axis=0,
            return_counts=True,
        )

        order = np.argsort(
            -counts,
            kind="stable",
        )

        for index in order:
            candidate = colors[index].astype(
                np.float64,
            )

            if any(
                np.linalg.norm(candidate - representative) <= color_tolerance
                for representative in representatives
            ):
                continue

            representatives.append(
                candidate,
            )

    # -----------------------------------------------------
    # Strongest stable color evidence first
    # -----------------------------------------------------

    stable_alpha = alpha_image[stable]

    if stable_alpha.size:
        maximum_stable_alpha = int(
            np.max(
                stable_alpha,
            )
        )

        stable_rgb = rgba[:, :, :3][stable]

        add_colors(
            stable_rgb[stable_alpha == maximum_stable_alpha],
        )

        # Preserve distinct translucent authored regions.
        #
        # Only locally stable lower-opacity pixels are
        # considered; arbitrary alpha-edge RGB variation
        # does not introduce additional colors.
        #
        add_colors(
            stable_rgb[stable_alpha < maximum_stable_alpha],
        )

    # -----------------------------------------------------
    # Fallback for very small or thin artwork
    # -----------------------------------------------------
    #
    # Some legitimate artwork may have no complete 3x3
    # stable neighborhood, such as very thin strokes.
    #
    # In that case retain the original color-discovery
    # behavior rather than reporting zero colors.
    #
    if not representatives:
        rgb = rgba[:, :, :3][meaningful]
        alpha = alpha_image[meaningful]

        maximum_alpha = int(
            np.max(
                alpha,
            )
        )

        add_colors(
            rgb[alpha == maximum_alpha],
        )

        add_colors(
            rgb[alpha < maximum_alpha],
        )

    if not representatives:
        raise PrepareError("Cannot discover Artifact colors: no meaningful source colors.")

    logger.info(
        "ARTWORK: Discovered color representatives: %s",
        [tuple(int(channel) for channel in representative) for representative in representatives],
    )

    return len(
        representatives,
    )


def _prepare_source_image(
    image: Image.Image,
    envelope: np.ndarray,
) -> Image.Image:
    """
    Normalize raster source Artwork for subsequent SVG tracing.

    Preserve source RGBA values within the physical Artwork envelope.
    Make pixels outside that envelope fully transparent.

    The resulting raster supports both single-color foreground
    tracing and Inkscape multicolor tracing.

    Prepare does not assign physical printer colors or synthesize
    a configured Artwork fill color.
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
    *,
    preserve_all: bool = False,
) -> str:
    """
    Return SVG path data for the artwork envelope.

    PNG-derived artwork retains the existing primary-exterior
    behavior.

    Native SVG artwork preserves every boundary loop, including
    disconnected components and interior holes.

    The resulting compound path uses the nonzero fill rule.
    Boundary orientation distinguishes filled regions from holes.
    """

    if envelope.ndim != 2:
        raise PrepareError("Artwork envelope must be two-dimensional.")

    edges = _boundary_edges(envelope)

    if not edges:
        raise PrepareError("Artwork envelope has no boundary.")

    loops = _boundary_loops(edges)

    if not loops:
        raise PrepareError("Could not construct a closed artwork envelope boundary.")

    if preserve_all:
        paths: list[str] = []

        for loop in loops:
            simplified = _simplify_loop(loop)

            if len(simplified) < 4:
                raise PrepareError("Artwork envelope boundary contains insufficient geometry.")

            if _signed_area(simplified) == 0:
                raise PrepareError("Artwork envelope contains a degenerate boundary.")

            paths.append(_svg_path_data(simplified))

        return " ".join(paths)

    exterior = max(
        loops,
        key=lambda loop: abs(_signed_area(loop)),
    )

    exterior = _simplify_loop(exterior)

    if len(exterior) < 4:
        raise PrepareError("Artwork envelope boundary contains insufficient geometry.")

    return _svg_path_data(exterior)


def _write_envelope_svg(
    envelope: np.ndarray,
    output: Path,
    *,
    preserve_all: bool = False,
) -> None:
    """
    Write the physical artwork envelope as an SVG.

    PNG-derived envelopes retain their existing single-exterior
    diagnostic representation.

    Native SVG envelopes retain all disconnected boundaries and
    interior holes as one compound path.

    The SVG remains border-only for inspection. Downstream geometry
    consumers may import the closed contours as planar regions.
    """

    if envelope.ndim != 2:
        raise PrepareError("Artwork envelope must be two-dimensional.")

    height, width = envelope.shape

    if width < 1 or height < 1:
        raise PrepareError("Artwork envelope has invalid dimensions.")

    path_data = _envelope_path_data(
        envelope,
        preserve_all=preserve_all,
    )

    fill_rule = '        fill-rule="nonzero"\n' if preserve_all else ""

    svg = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<svg xmlns="http://www.w3.org/2000/svg"\n'
        f'     width="{width}"\n'
        f'     height="{height}"\n'
        f'     viewBox="0 0 {width} {height}">\n'
        f'  <path d="{path_data}"\n'
        f"{fill_rule}"
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
    Constrain traced artwork geometry to the physical envelope.

    Inkscape may represent transparent raster background as a
    page-sized color region. The physical envelope is authoritative,
    so all traced geometry is clipped to that envelope.

    Assign deterministic, globally unique path IDs after clipping
    so downstream Raster processing can identify every SVG path.
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

    if _local_name(root.tag) != "svg":
        raise PrepareError(f"Trace does not contain an SVG root element: {trace}")

    ET.register_namespace(
        "",
        SVG_NAMESPACE,
    )

    # Reserve IDs without colliding with IDs from the trace.
    reserved_ids = {
        element_id for element in root.iter() if (element_id := element.get("id")) is not None
    }

    def unique_id(base: str) -> str:
        candidate = base
        index = 1

        while candidate in reserved_ids:
            candidate = f"{base}-{index}"
            index += 1

        reserved_ids.add(candidate)
        return candidate

    envelope_id = unique_id("artwork-envelope")
    group_id = unique_id("artwork")

    defs = ET.Element(
        _svg_tag("defs"),
    )

    clip_path = ET.SubElement(
        defs,
        _svg_tag("clipPath"),
        {
            "id": envelope_id,
            "clipPathUnits": "userSpaceOnUse",
        },
    )

    ET.SubElement(
        clip_path,
        _svg_tag("path"),
        {
            "d": path_data,
        },
    )

    # Keep existing metadata and definitions at the root.
    # Move drawable root-level elements into the clipped group.
    drawable: list[ET.Element] = []

    for child in list(root):
        if _local_name(child.tag) in {
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
        _svg_tag("g"),
        {
            "id": group_id,
            "clip-path": f"url(#{envelope_id})",
        },
    )

    for child in drawable:
        root.remove(child)
        group.append(child)

    root.append(group)

    # Reuse native SVG normalization for deterministic IDs.
    # This covers traced paths and the clipping definition.
    _assign_native_svg_path_ids(
        root,
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
# Single color tracing
# =========================================================


def _trace_single_color(
    source: Path,
    output: Path,
) -> None:
    """
    Trace one foreground color into a compound SVG path.

    Preserve exact raster pixel boundaries, disconnected regions,
    enclosed holes, and source coordinate registration.

    Foreground occupancy is determined by the source alpha channel.
    Pixels below DEFAULT_ALPHA_THRESHOLD are excluded from both
    geometry and color interpretation.

    Derive the representative Artifact RGB from the most opaque
    foreground pixels, preferring fully opaque pixels when present.

    Meaningful foreground pixels may contain incidental RGB
    variations within the source-color discovery tolerance,
    regardless of opacity. Substantially different authored
    colors are rejected rather than merged.

    Partially transparent foreground pixels may have incidental
    RGB variation within a small color-distance tolerance.

    Substantially different foreground colors are rejected rather
    than silently merged into a single Artifact color.

    The representative source RGB becomes the SVG path fill.
    No background path is generated, leaving the background
    fully transparent.

    The resulting path uses the nonzero fill rule with oriented
    boundary loops to distinguish filled regions from holes.

    This operation does not perform brightness-based subject
    extraction, automatic color quantization, or multicolor tracing.
    """
    source = Path(source)
    output = Path(output).resolve()

    _require_source(source)

    if source.suffix.lower() != ".png":
        raise PrepareError(f"Single-color tracing requires a PNG source: {source}")

    _require_svg_output(
        source,
        output,
        label="Trace",
    )

    try:
        with Image.open(source) as image:
            rgba = np.asarray(
                image.convert("RGBA"),
                dtype=np.uint8,
            )

    except (OSError, ValueError) as exc:
        raise PrepareError(f"Could not load source artwork: {source}") from exc

    height, width = rgba.shape[:2]

    alpha = rgba[:, :, 3]

    foreground = np.asarray(
        alpha >= DEFAULT_ALPHA_THRESHOLD,
        dtype=bool,
    )

    if not np.any(foreground):
        raise PrepareError("Single-color tracing requires meaningful foreground pixels.")

    # Only meaningful foreground pixels contribute to Artifact color.
    # Transparent background RGB values are excluded.
    foreground_rgb = rgba[:, :, :3][foreground]

    foreground_alpha = alpha[foreground]

    # Use the same meaningful-color interpretation as automatic
    # discovery. An explicit single-color override must not
    # silently merge genuinely different authored colors.
    discovered_count = _discover_png_color_count(
        Image.fromarray(
            rgba,
            mode="RGBA",
        ),
    )

    if discovered_count != 1:
        raise PrepareError(
            "Single-color tracing requires exactly one foreground "
            f"RGB color; discovered {discovered_count}. "
            "Use multicolor tracing or provide uniform foreground artwork."
        )

    # Choose the dominant RGB among the most opaque pixels.
    # Minor opaque and translucent variations do not alter
    # the representative Artifact color.
    maximum_alpha = int(
        np.max(foreground_alpha),
    )

    strongest_pixels = foreground_rgb[foreground_alpha == maximum_alpha]

    colors, counts = np.unique(
        strongest_pixels,
        axis=0,
        return_counts=True,
    )

    representative_rgb = colors[int(np.argmax(counts))]

    red, green, blue = (int(channel) for channel in representative_rgb)

    fill_color = f"#{red:02x}{green:02x}{blue:02x}"

    # Geometry is determined solely by meaningful alpha occupancy.
    # RGB normalization must not alter the occupied region.
    edges = _boundary_edges(
        foreground,
    )

    loops = _boundary_loops(
        edges,
    )

    if not loops:
        raise PrepareError("Could not trace single-color foreground geometry.")

    paths: list[str] = []

    for loop in loops:
        simplified = _simplify_loop(
            loop,
        )

        if len(simplified) < 4:
            raise PrepareError("Single-color trace contains insufficient geometry.")

        if _signed_area(simplified) == 0:
            raise PrepareError("Single-color trace contains degenerate geometry.")

        paths.append(_svg_path_data(simplified))

    ET.register_namespace(
        "",
        SVG_NAMESPACE,
    )

    root = ET.Element(
        _svg_tag("svg"),
        {
            "width": str(width),
            "height": str(height),
            "viewBox": f"0 0 {width} {height}",
        },
    )

    ET.SubElement(
        root,
        _svg_tag("path"),
        {
            "d": " ".join(paths),
            "fill": fill_color,
            "fill-rule": "nonzero",
        },
    )

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    try:
        ET.ElementTree(root).write(
            output,
            encoding="utf-8",
            xml_declaration=True,
        )

    except OSError as exc:
        raise PrepareError(f"Could not write single-color trace: {output}") from exc


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

    source = Path(source)
    output = Path(output).resolve()

    _require_source(source)

    if source.suffix.lower() != ".png":
        raise PrepareError(f"Multicolor tracing requires a PNG source: {source}")

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
            str(colors),
            _bool_value(smooth),
            _bool_value(stack),
            _bool_value(remove_background),
            str(speckles),
            str(smooth_corners),
            str(optimize),
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
