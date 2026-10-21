"""
Shared Border Label operations for the Shape model.

This module provides stage-independent operations used to measure, fit,
and construct Shape Border Labels.

It intentionally does not own:

- Border Label participation policy;
- registered Shape boundary precedence;
- interaction with Outer Ridge or Inner Ridge;
- Artwork interior selection;
- extrusion or Z geometry;
- printer-color policy; or
- build-stage orchestration.

Those responsibilities remain with the appropriate Shape configuration,
Compose, Extrude, and Package boundaries.

Physical units
--------------

Public physical dimensions used by the fitting operations are
millimeters.

``glyph_height`` means the physical allocation for rendered glyph height,
not SVG/CSS ``font-size``. SVG font size is an implementation detail.

Font geometry scales linearly. Text is therefore measured once at a
reference SVG font size and converted to scale-independent metrics. The
fitting algorithm can then evaluate candidate glyph heights
arithmetically without repeatedly invoking Inkscape.

Circular geometry
-----------------

Circular path angles are measured relative to top-dead-center:

       0 degrees
           |
           |
    -90 ---+--- +90
           |
           |
       180 degrees

The Top Border Label path runs from upper-left to upper-right.

The Bottom Border Label path runs in the opposite direction around the
lower arc so left-to-right text remains upright.

The Shape Compose stage remains responsible for converting physical
Border Label geometry into the registered coordinate system used by
Shape composition.
"""

from __future__ import annotations

import math
import tempfile
import xml.etree.ElementTree as ET
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from lowkey_artifact_builder.tools.inkscape import (
    InkscapeError,
    export_text_to_path,
    query_all,
)

SVG_NS = "http://www.w3.org/2000/svg"

REFERENCE_FONT_SIZE = 10.0
REFERENCE_BASELINE_Y = 50.0

GLYPH_HEIGHT_TOLERANCE_MM = 0.001
GLYPH_HEIGHT_MAX_ITERATIONS = 100

XLINK_NS = "http://www.w3.org/1999/xlink"

REGISTERED_LABEL_PATH_ID = "border-label-baseline"
REGISTERED_LABEL_TEXT_ID = "border-label-text"


ET.register_namespace(
    "",
    SVG_NS,
)

ET.register_namespace(
    "xlink",
    XLINK_NS,
)


# =========================================================
# Errors
# =========================================================


class BorderLabelError(RuntimeError):
    """
    Raised when Border Label measurement or fitting fails.
    """


# =========================================================
# Data structures
# =========================================================


@dataclass(frozen=True)
class LabelMetrics:
    """
    Scale-independent metrics for one rendered label.

    ``width_per_height``:
        Rendered text width divided by rendered glyph height.

    ``font_size_per_height``:
        SVG/CSS font-size divided by rendered glyph height.

    ``above_baseline_per_height``:
        Distance from the SVG baseline to the top of the rendered glyph
        bounds, divided by rendered glyph height.

    ``below_baseline_per_height``:
        Distance from the SVG baseline to the bottom of the rendered
        glyph bounds, divided by rendered glyph height.

    All values are dimensionless.
    """

    width_per_height: float
    font_size_per_height: float
    above_baseline_per_height: float
    below_baseline_per_height: float


@dataclass(frozen=True)
class LabelMeasurement:
    """
    Physical measurement of one rendered label.

    ``width`` and ``height`` are millimeters.

    ``font_size`` is the SVG/CSS font-size required for the physical
    measurement. It is an implementation detail rather than Shape
    geometry.
    """

    width: float
    height: float
    font_size: float


@dataclass(frozen=True)
class LabelFit:
    """
    Fitted information for one participating Border Label.

    Each label has its own measured metrics and effective SVG font size.
    Both labels occupy the same resolved physical glyph-height allocation.
    """

    text: str
    metrics: LabelMetrics
    width: float
    rendered_height: float
    font_size: float


@dataclass(frozen=True)
class CircularBorderLabelFit:
    """
    Result of fitting participating labels to a circular Shape.

    ``glyph_height`` is the common physical lettering-band allocation.

    ``font_size`` is the common SVG/CSS font-size used by all
    participating labels.

    ``bottom_baseline_radius`` and ``top_baseline_radius`` identify the
    semantic baselines for the Bottom and Top Border Labels. For circular
    Border Labels they resolve to one shared physical radius:

        reference boundary
            ↓ border width
        outer edge of lettering band / shared construction path
            ↓ resolved common glyph-height allocation
        inner edge of lettering band
            ↓ border width
        Border Label inner boundary

    The shared construction path is not the typographic baseline of both
    labels. It is an SVG text-layout device. Position-specific offsets
    derived from the measured font metrics place the Top and Bottom glyph
    outlines into the common lettering band before Inkscape converts them
    to ordinary path geometry.

    A label entry is present only when that label participates.
    """

    glyph_height: float
    font_size: float
    bottom_baseline_radius: float
    top_baseline_radius: float
    inner_boundary_radius: float
    top: LabelFit | None
    bottom: LabelFit | None


# =========================================================
# Validation
# =========================================================


def _validate_text(
    text: str,
    font_family: str,
) -> None:
    """
    Validate inputs used for actual font measurement.

    Only participating labels should reach this operation.
    """

    if not text.strip():
        raise BorderLabelError("Border Label text cannot be empty.")

    if not font_family.strip():
        raise BorderLabelError("Border Label font family cannot be empty.")


def _validate_metrics(
    metrics: LabelMetrics,
) -> None:
    """
    Validate measured scale-independent font metrics.
    """

    if metrics.width_per_height <= 0:
        raise BorderLabelError("Border Label width-per-height metric must be greater than zero.")

    if metrics.font_size_per_height <= 0:
        raise BorderLabelError(
            "Border Label font-size-per-height metric must be greater than zero."
        )

    if metrics.above_baseline_per_height < 0:
        raise BorderLabelError("Border Label above-baseline metric cannot be negative.")

    if metrics.below_baseline_per_height < 0:
        raise BorderLabelError("Border Label below-baseline metric cannot be negative.")

    baseline_height = metrics.above_baseline_per_height + metrics.below_baseline_per_height

    if baseline_height <= 0:
        raise BorderLabelError(
            "Border Label baseline metrics must describe a positive glyph height."
        )


def _validate_circular_fit_inputs(
    *,
    reference_radius: float,
    border_width: float,
    max_glyph_height: float,
    arc_degrees: float,
    end_margin: float,
) -> None:
    """
    Validate circular fitting geometry.

    Participation itself is intentionally not decided here.
    """

    if reference_radius <= 0:
        raise BorderLabelError("Border Label reference radius must be greater than zero.")

    if border_width < 0:
        raise BorderLabelError("Border Label width cannot be negative.")

    if max_glyph_height <= 0:
        raise BorderLabelError("Border Label maximum glyph height must be greater than zero.")

    if not 0 < arc_degrees < 180:
        raise BorderLabelError(
            "Border Label arc degrees must be greater than zero and less than 180."
        )

    if end_margin < 0:
        raise BorderLabelError("Border Label end margin cannot be negative.")


# =========================================================
# Font measurement
# =========================================================


def _measurement_svg(
    *,
    text: str,
    font_family: str,
    font_size: float,
) -> ET.ElementTree:
    """
    Build a temporary SVG containing the actual label and a font
    vertical-reference string.

    Both objects use the same font, size, and baseline.

    The actual label provides its rendered width. The reference
    provides a consistent ascender/descender envelope independent
    of the characters in the actual label.

    The SVG uses millimeter-equivalent user coordinates so Inkscape
    measurements can be converted into physical font metrics.
    """

    root = ET.Element(
        f"{{{SVG_NS}}}svg",
        {
            "width": "500mm",
            "height": "100mm",
            "viewBox": "0 0 500 100",
        },
    )

    ET.SubElement(
        root,
        f"{{{SVG_NS}}}text",
        {
            "id": "measure-border-label",
            "x": "10",
            "y": f"{REFERENCE_BASELINE_Y:g}",
            "font-family": font_family,
            "font-size": f"{font_size:g}",
        },
    ).text = text

    ET.SubElement(
        root,
        f"{{{SVG_NS}}}text",
        {
            "id": "measure-border-label-reference",
            "x": "10",
            "y": f"{REFERENCE_BASELINE_Y:g}",
            "font-family": font_family,
            "font-size": f"{font_size:g}",
        },
    ).text = "Hgjpqy"

    return ET.ElementTree(root)


def _measure_at_font_size(
    *,
    text: str,
    font_family: str,
    font_size: float,
) -> tuple[
    float,
    float,
    float,
    float,
]:
    """
    Measure a label at one SVG/CSS font-size.

    Returns:

        (
            actual_label_width_mm,
            reference_height_mm,
            reference_above_baseline_mm,
            reference_below_baseline_mm,
        )

    The actual label determines horizontal extent.

    A fixed reference string determines the vertical font envelope,
    ensuring that labels without descenders reserve the same space
    as labels containing descenders.

    The operation invokes Inkscape exactly once.
    """

    _validate_text(
        text,
        font_family,
    )

    if font_size <= 0:
        raise BorderLabelError("Border Label font size must be greater than zero.")

    tree = _measurement_svg(
        text=text,
        font_family=font_family,
        font_size=font_size,
    )

    with tempfile.TemporaryDirectory() as directory:
        source = Path(directory) / "border-label-measurement.svg"

        tree.write(
            source,
            encoding="utf-8",
            xml_declaration=True,
        )

        try:
            bounds = query_all(source)

        except InkscapeError as exc:
            raise BorderLabelError("Could not measure Border Label text using Inkscape.") from exc

    try:
        actual = bounds["measure-border-label"]
        reference = bounds["measure-border-label-reference"]

        width = actual["width"]

        y = reference["y"]
        height = reference["height"]

    except KeyError as exc:
        raise BorderLabelError(
            "Inkscape did not return measurements for the Border Label. "
            f"Check that the selected font is available: {font_family}"
        ) from exc

    if width <= 0 or height <= 0:
        raise BorderLabelError("Inkscape returned invalid Border Label dimensions.")

    glyph_top = y
    glyph_bottom = y + height

    above_baseline = REFERENCE_BASELINE_Y - glyph_top
    below_baseline = glyph_bottom - REFERENCE_BASELINE_Y

    tolerance = 1e-9

    if above_baseline < -tolerance or below_baseline < -tolerance:
        raise BorderLabelError(
            "Inkscape returned Border Label glyph bounds that do not contain the text baseline."
        )

    above_baseline = max(
        0.0,
        above_baseline,
    )

    below_baseline = max(
        0.0,
        below_baseline,
    )

    return (
        width,
        height,
        above_baseline,
        below_baseline,
    )


def measure_label_metrics(
    *,
    text: str,
    font_family: str,
) -> LabelMetrics:
    """
    Measure one participating label and return scale-independent metrics.

    The actual label determines horizontal width.

    A fixed font reference determines the common vertical envelope,
    including ascender and descender allowances.

    Consequently, labels using the same font share identical
    font-size and baseline conversion metrics regardless of their
    characters.

    Inkscape is invoked exactly once for this operation.

    Subsequent fitting at different physical glyph heights can
    therefore be performed arithmetically.
    """

    (
        width,
        reference_height,
        reference_above_baseline,
        reference_below_baseline,
    ) = _measure_at_font_size(
        text=text,
        font_family=font_family,
        font_size=REFERENCE_FONT_SIZE,
    )

    metrics = LabelMetrics(
        width_per_height=(width / reference_height),
        font_size_per_height=(REFERENCE_FONT_SIZE / reference_height),
        above_baseline_per_height=(reference_above_baseline / reference_height),
        below_baseline_per_height=(reference_below_baseline / reference_height),
    )

    _validate_metrics(metrics)

    return metrics


def measure_participating_labels(
    labels: Mapping[str, str],
    *,
    font_family: str,
) -> dict[str, LabelMetrics]:
    """
    Measure each participating label exactly once.

    ``labels`` should contain only labels that participate. This module
    deliberately does not decide participation.

    The mapping keys are preserved so callers can use semantic names such
    as ``top`` and ``bottom``.
    """

    if not labels:
        raise BorderLabelError("At least one participating Border Label is required.")

    measured: dict[
        str,
        LabelMetrics,
    ] = {}

    for name, text in labels.items():
        measured[name] = measure_label_metrics(
            text=text,
            font_family=font_family,
        )

    return measured


# =========================================================
# Metric scaling
# =========================================================


def measurement_from_metrics(
    metrics: LabelMetrics,
    *,
    glyph_height: float,
) -> LabelMeasurement:
    """
    Scale measured metrics to a requested physical glyph height.

    This operation treats ``glyph_height`` as the actual rendered height
    for this individual label. Common-font fitting uses the lower-level
    common-font operations below instead.
    """

    _validate_metrics(metrics)

    if glyph_height <= 0:
        raise BorderLabelError("Border Label glyph height must be greater than zero.")

    return LabelMeasurement(
        width=(metrics.width_per_height * glyph_height),
        height=glyph_height,
        font_size=(metrics.font_size_per_height * glyph_height),
    )


def font_size_for_height(
    metrics: LabelMetrics,
    *,
    glyph_height: float,
) -> float:
    """
    Return the SVG/CSS font-size needed for one label to render at the
    requested physical glyph height.
    """

    return measurement_from_metrics(
        metrics,
        glyph_height=glyph_height,
    ).font_size


def write_registered_circular_label_svg(
    output: Path,
    *,
    text: str,
    font_family: str,
    font_size: float,
    metrics: LabelMetrics,
    rendered_height: float,
    baseline_path: str,
    shape_size: float,
    position: str,
) -> Path:
    """
    Materialize one fitted circular Border Label as registered SVG path geometry.

    ``baseline_path`` is the circular SVG construction path used by textPath.
    It is expressed in registered Shape coordinates.

    For circular Border Labels, Top and Bottom may use the same radial
    construction path while occupying the same physical lettering band from
    opposite sides. The construction path is not necessarily the final
    typographic baseline of the rendered glyphs.

    Measured above- and below-baseline font metrics are used to offset each
    label relative to the construction path so its complete rendered glyph
    bounds occupy the intended lettering band.

    Inkscape converts the positioned text to ordinary path geometry. The
    construction path is then removed; downstream stages consume only the
    materialized glyph outlines.

    ``font_size`` and ``rendered_height`` come from physical fitting and are
    converted to registered Shape coordinates here. Extrude remains responsible
    for physical dimensionalization.
    """

    output = Path(
        output,
    )

    if not text.strip():
        raise BorderLabelError("Border Label text cannot be empty.")

    if not font_family.strip():
        raise BorderLabelError("Border Label font family cannot be empty.")

    if shape_size <= 0:
        raise BorderLabelError("Shape size must be greater than zero.")

    if position not in {
        "top",
        "bottom",
    }:
        raise BorderLabelError(f"Unsupported Border Label position: {position!r}.")

    _validate_metrics(
        metrics,
    )

    if rendered_height <= 0:
        raise BorderLabelError("Rendered Border Label height must be greater than zero.")

    #
    # Font measurement uses an SVG whose user-coordinate system is
    # millimeter-equivalent: its physical dimensions and viewBox use the same
    # numeric dimensions. The fitted font size is therefore already expressed
    # in physical millimeter-equivalent user units.
    #
    # Compose converts that physical font size directly into registered Shape
    # coordinates. Extrude later restores the physical Shape dimensions.
    #

    registered_font_size = font_size / shape_size

    registered_rendered_height = rendered_height / shape_size

    registered_above_baseline = metrics.above_baseline_per_height * registered_rendered_height

    registered_below_baseline = metrics.below_baseline_per_height * registered_rendered_height

    #
    # SVG text is positioned relative to its typographic baseline, while the
    # supplied path represents the shared radial construction edge used to lay
    # out circular Border Labels.
    #
    # Offset each label according to its measured above-/below-baseline extent
    # so the complete rendered glyph bounds occupy the intended common lettering
    # band. Top and Bottom use opposite sides of their measured typographic
    # bounds when aligning to the shared construction path.
    #

    if position == "top":
        baseline_offset = registered_above_baseline
    else:
        baseline_offset = -registered_below_baseline

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    source = output.with_name(f"{output.stem}.text.svg")

    root = ET.Element(
        f"{{{SVG_NS}}}svg",
        {
            "viewBox": "-0.5 -0.5 1 1",
        },
    )

    ET.SubElement(
        root,
        f"{{{SVG_NS}}}path",
        {
            "id": REGISTERED_LABEL_PATH_ID,
            "d": baseline_path,
            "fill": "none",
        },
    )

    text_element = ET.SubElement(
        root,
        f"{{{SVG_NS}}}text",
        {
            "id": REGISTERED_LABEL_TEXT_ID,
            "font-family": font_family,
            "font-size": f"{registered_font_size:.12g}",
            "text-anchor": "middle",
        },
    )

    text_path = ET.SubElement(
        text_element,
        f"{{{SVG_NS}}}textPath",
        {
            "href": f"#{REGISTERED_LABEL_PATH_ID}",
            f"{{{XLINK_NS}}}href": (f"#{REGISTERED_LABEL_PATH_ID}"),
            "startOffset": "50%",
            "dy": f"{baseline_offset:.12g}",
        },
    )

    text_path.text = text

    ET.ElementTree(
        root,
    ).write(
        source,
        encoding="utf-8",
        xml_declaration=True,
    )

    try:
        export_text_to_path(
            source,
            output,
        )

    except InkscapeError as exc:
        raise BorderLabelError(f"Could not materialize Border Label path geometry: {exc}") from exc

    finally:
        try:
            source.unlink()
        except FileNotFoundError:
            pass

    if not output.is_file():
        raise BorderLabelError(f"Border Label path geometry was not created: {output}")

    #
    # The baseline is construction geometry. Inkscape preserves it while
    # converting the text to path outlines, but it is not part of the
    # manufacturing product consumed by Extrude.
    #

    try:
        output_tree = ET.parse(
            output,
        )
    except ET.ParseError as exc:
        raise BorderLabelError(
            f"Could not read materialized Border Label path geometry: {output}"
        ) from exc

    output_root = output_tree.getroot()

    baseline_removed = False

    for parent in output_root.iter():
        for child in list(
            parent,
        ):
            if child.get("id") == REGISTERED_LABEL_PATH_ID:
                parent.remove(
                    child,
                )
                baseline_removed = True

    if not baseline_removed:
        raise BorderLabelError(
            "Materialized Border Label geometry does not contain its construction baseline."
        )

    #
    # The persistent product must contain ordinary path geometry after the
    # construction baseline has been removed.
    #

    manufacturing_paths = [
        element
        for element in output_root.iter()
        if (element.tag == f"{{{SVG_NS}}}path" and element.get("d"))
    ]

    if not manufacturing_paths:
        raise BorderLabelError(
            "Materialized Border Label does not contain manufacturing path geometry."
        )

    #
    # Restore the default SVG namespace for OpenSCAD compatibility.
    #
    # ElementTree namespace registrations are process-global. Other modules
    # may have changed the registry since this module was imported.
    # Register immediately before serializing the manufacturing product.
    #

    ET.register_namespace("", SVG_NS)
    ET.register_namespace("xlink", XLINK_NS)

    output_tree.write(
        output,
        encoding="utf-8",
        xml_declaration=True,
    )

    return output


def _width_per_font_size(
    metrics: LabelMetrics,
) -> float:
    """
    Return rendered width per SVG/CSS font-size unit.
    """

    _validate_metrics(metrics)

    return metrics.width_per_height / metrics.font_size_per_height


def _common_font_size_per_height(
    metrics: Mapping[str, LabelMetrics],
) -> float:
    """
    Return the common font-size conversion for participating labels.

    The smallest conversion ratio ensures no participating label exceeds
    the requested common physical glyph-height allocation.
    """

    if not metrics:
        raise BorderLabelError("At least one participating Border Label is required.")

    for label_metrics in metrics.values():
        _validate_metrics(label_metrics)

    return min(label_metrics.font_size_per_height for label_metrics in metrics.values())


def _common_font_size(
    metrics: Mapping[str, LabelMetrics],
    glyph_height: float,
) -> float:
    """
    Return the common SVG/CSS font-size at a candidate glyph height.
    """

    if glyph_height <= 0:
        raise BorderLabelError("Border Label glyph height must be greater than zero.")

    return _common_font_size_per_height(metrics) * glyph_height


def _rendered_height(
    metrics: LabelMetrics,
    *,
    font_size: float,
) -> float:
    """
    Return actual rendered glyph height at a common font size.
    """

    _validate_metrics(metrics)

    return font_size / metrics.font_size_per_height


def _rendered_width(
    metrics: LabelMetrics,
    *,
    font_size: float,
) -> float:
    """
    Return actual rendered text width at a common font size.
    """

    return _width_per_font_size(metrics) * font_size


# =========================================================
# Circular path geometry
# =========================================================


def point_on_circle(
    center_x: float,
    center_y: float,
    radius: float,
    angle_from_top: float,
) -> tuple[
    float,
    float,
]:
    """
    Return a point on a circle.

    ``angle_from_top`` is measured in degrees relative to
    top-dead-center. SVG Y coordinates increase downward.

    The operation is unit-independent as long as the center and radius
    use the same coordinate system.
    """

    if radius <= 0:
        raise BorderLabelError("Border Label path radius must be greater than zero.")

    radians = math.radians(angle_from_top)

    x = center_x + radius * math.sin(radians)

    y = center_y - radius * math.cos(radians)

    return (
        x,
        y,
    )


def circular_arc_path(
    *,
    center_x: float,
    center_y: float,
    radius: float,
    start_angle: float,
    end_angle: float,
    sweep: int,
) -> str:
    """
    Construct an SVG circular arc path.

    Angles are measured relative to top-dead-center.
    """

    if sweep not in (
        0,
        1,
    ):
        raise BorderLabelError("Border Label SVG arc sweep must be zero or one.")

    start_x, start_y = point_on_circle(
        center_x,
        center_y,
        radius,
        start_angle,
    )

    end_x, end_y = point_on_circle(
        center_x,
        center_y,
        radius,
        end_angle,
    )

    angle_span = abs(end_angle - start_angle)

    large_arc = 1 if angle_span > 180 else 0

    return (
        f"M {start_x:.9f},{start_y:.9f} "
        f"A {radius:.9f},{radius:.9f} "
        f"0 {large_arc} {sweep} "
        f"{end_x:.9f},{end_y:.9f}"
    )


def top_label_path(
    *,
    center_x: float,
    center_y: float,
    radius: float,
    arc_degrees: float,
) -> str:
    """
    Return the circular path for the Top Border Label.

    The path traverses upper-left to upper-right so left-to-right text
    reads normally.
    """

    if not 0 < arc_degrees < 180:
        raise BorderLabelError(
            "Border Label arc degrees must be greater than zero and less than 180."
        )

    half_arc = arc_degrees / 2

    return circular_arc_path(
        center_x=center_x,
        center_y=center_y,
        radius=radius,
        start_angle=-half_arc,
        end_angle=half_arc,
        sweep=1,
    )


def bottom_label_path(
    *,
    center_x: float,
    center_y: float,
    radius: float,
    arc_degrees: float,
) -> str:
    """
    Return the circular path for the Bottom Border Label.

    The path traverses in the opposite direction around the lower arc so
    the lettering remains upright and reads left-to-right.
    """

    if not 0 < arc_degrees < 180:
        raise BorderLabelError(
            "Border Label arc degrees must be greater than zero and less than 180."
        )

    half_arc = arc_degrees / 2

    return circular_arc_path(
        center_x=center_x,
        center_y=center_y,
        radius=radius,
        start_angle=(180 + half_arc),
        end_angle=(180 - half_arc),
        sweep=0,
    )


def available_arc_length(
    radius: float,
    arc_degrees: float,
    *,
    end_margin: float,
) -> float:
    """
    Return usable physical path length.

    ``end_margin`` is reserved at both ends of the maximum permitted arc:

        radius * radians(arc_degrees)
        - 2 * end_margin
    """

    if radius <= 0:
        raise BorderLabelError("Border Label arc radius must be greater than zero.")

    if not 0 < arc_degrees < 180:
        raise BorderLabelError(
            "Border Label arc degrees must be greater than zero and less than 180."
        )

    if end_margin < 0:
        raise BorderLabelError("Border Label end margin cannot be negative.")

    length = radius * math.radians(arc_degrees) - 2 * end_margin

    return max(
        0.0,
        length,
    )


# =========================================================
# Circular Border Label fitting
# =========================================================


def _circular_baseline_radii(
    *,
    reference_radius: float,
    border_width: float,
    glyph_height: float,
) -> tuple[
    float,
    float,
    float,
]:
    """
    Return the circular Border Label lettering-band geometry.

    Moving inward:

        reference boundary
            ↓ border_width
        shared construction radius / lettering-band outer edge
            ↓ glyph_height
        lettering-band inner edge
            ↓ border_width
        Border Label inner boundary

    ``glyph_height`` is the common physical allocation for the lettering
    band. The shared construction radius is used for SVG text-on-path
    materialization; it must not be confused with the individual
    typographic baseline of either rendered label.
    """

    baseline_radius = reference_radius - border_width

    inner_boundary_radius = baseline_radius - glyph_height - border_width

    return (
        baseline_radius,
        baseline_radius,
        inner_boundary_radius,
    )


def _circular_labels_fit(
    *,
    metrics: Mapping[str, LabelMetrics],
    glyph_height: float,
    reference_radius: float,
    border_width: float,
    arc_degrees: float,
    end_margin: float,
    arc_degrees_by_position: Mapping[str, float] | None = None,
    independent_font_sizes: bool = False,
) -> bool:
    """
    Determine whether every participating label fits within its own arc.

    Both labels share a physical glyph-height allocation. When independent
    typography is enabled, each font's metrics determine its SVG font size.
    """

    if glyph_height <= 0:
        return False

    bottom_radius, top_radius, inner_radius = _circular_baseline_radii(
        reference_radius=reference_radius,
        border_width=border_width,
        glyph_height=glyph_height,
    )

    if min(bottom_radius, top_radius, inner_radius) <= 0:
        return False

    if not math.isclose(
        bottom_radius,
        top_radius,
        rel_tol=0.0,
        abs_tol=1e-12,
    ):
        raise BorderLabelError("Circular Border Labels must share one baseline radius.")

    common_font_size = None if independent_font_sizes else _common_font_size(metrics, glyph_height)

    for position, label_metrics in metrics.items():
        if position not in {"top", "bottom"}:
            raise BorderLabelError(f"Unknown circular Border Label position: {position!r}")

        effective_arc = (
            arc_degrees_by_position.get(position, arc_degrees)
            if arc_degrees_by_position is not None
            else arc_degrees
        )

        available = available_arc_length(
            top_radius,
            effective_arc,
            end_margin=end_margin,
        )

        font_size = (
            font_size_for_height(
                label_metrics,
                glyph_height=glyph_height,
            )
            if common_font_size is None
            else common_font_size
        )

        required = _rendered_width(
            label_metrics,
            font_size=font_size,
        )

        if required > available:
            return False

    return True


def _fit_circular_glyph_height(
    *,
    metrics: Mapping[str, LabelMetrics],
    reference_radius: float,
    border_width: float,
    max_glyph_height: float,
    arc_degrees: float,
    end_margin: float,
    arc_degrees_by_position: Mapping[str, float] | None = None,
    independent_font_sizes: bool = False,
) -> float:
    """
    Find the largest common physical glyph-height allocation fitting all
    participating labels within their independently available arcs.
    """

    def fits(candidate: float) -> bool:
        return _circular_labels_fit(
            metrics=metrics,
            glyph_height=candidate,
            reference_radius=reference_radius,
            border_width=border_width,
            arc_degrees=arc_degrees,
            end_margin=end_margin,
            arc_degrees_by_position=arc_degrees_by_position,
            independent_font_sizes=independent_font_sizes,
        )

    if fits(max_glyph_height):
        return max_glyph_height

    low = 0.0
    high = max_glyph_height

    for _ in range(GLYPH_HEIGHT_MAX_ITERATIONS):
        if high - low <= GLYPH_HEIGHT_TOLERANCE_MM:
            break

        candidate = (low + high) / 2.0

        if fits(candidate):
            low = candidate
        else:
            high = candidate

    if low <= 0:
        raise BorderLabelError(
            "Border Labels cannot be fitted within the available Shape geometry."
        )

    return low


def _expand_symbolic_text(text: str) -> str:
    """
    Expand supported Border Label symbolic commands.

    Supported syntax:
    - \\bullet produces U+2022 BULLET.
    - \\\\ produces one literal backslash.

    All other backslash commands are rejected. Expansion preserves
    authored whitespace and is performed exactly once before measurement.
    """
    result: list[str] = []
    index = 0

    while index < len(text):
        if text[index] != "\\":
            result.append(text[index])
            index += 1
            continue

        if index + 1 < len(text) and text[index + 1] == "\\":
            result.append("\\")
            index += 2
            continue

        if text.startswith(r"\bullet", index):
            end = index + len(r"\bullet")

            if end == len(text) or not text[end].isalpha():
                result.append("\u2022")
                index = end
                continue

        end = index + 1

        while end < len(text) and text[end].isalpha():
            end += 1

        command = text[index:end]

        raise BorderLabelError(f"Unsupported Border Label symbolic command: {command!r}.")

    return "".join(result)


def fit_circular_border_labels(
    *,
    top_text: str | None,
    bottom_text: str | None,
    font_family: str,
    reference_radius: float,
    border_width: float,
    max_glyph_height: float,
    arc_degrees: float,
    end_margin: float,
    top_font_family: str | None = None,
    bottom_font_family: str | None = None,
    top_arc_degrees: float | None = None,
    bottom_arc_degrees: float | None = None,
) -> CircularBorderLabelFit:
    """
    Measure and fit participating circular Border Labels.

    Position-specific settings inherit shared settings when omitted.
    Both labels share one physical glyph-height allocation.

    Symbolic commands are expanded once before measurement and fitting.
    The expanded text is retained for manufacturing geometry.

    Legacy shared-only callers retain their common-font-size behavior.
    """

    _validate_circular_fit_inputs(
        reference_radius=reference_radius,
        border_width=border_width,
        max_glyph_height=max_glyph_height,
        arc_degrees=arc_degrees,
        end_margin=end_margin,
    )

    texts = {
        "top": top_text,
        "bottom": bottom_text,
    }

    fonts = {
        "top": top_font_family if top_font_family is not None else font_family,
        "bottom": (bottom_font_family if bottom_font_family is not None else font_family),
    }

    arcs = {
        "top": (top_arc_degrees if top_arc_degrees is not None else arc_degrees),
        "bottom": (bottom_arc_degrees if bottom_arc_degrees is not None else arc_degrees),
    }

    participating = {
        position: _expand_symbolic_text(text)
        for position, text in texts.items()
        if text is not None
    }

    if not participating:
        raise BorderLabelError("At least one participating Border Label is required.")

    metrics: dict[str, LabelMetrics] = {}

    for position, text in participating.items():
        _validate_text(text, fonts[position])

        _validate_circular_fit_inputs(
            reference_radius=reference_radius,
            border_width=border_width,
            max_glyph_height=max_glyph_height,
            arc_degrees=arcs[position],
            end_margin=end_margin,
        )

        metrics[position] = measure_label_metrics(
            text=text,
            font_family=fonts[position],
        )

    independent_font_sizes = len({fonts[position] for position in participating}) > 1

    glyph_height = _fit_circular_glyph_height(
        metrics=metrics,
        reference_radius=reference_radius,
        border_width=border_width,
        max_glyph_height=max_glyph_height,
        arc_degrees=arc_degrees,
        end_margin=end_margin,
        arc_degrees_by_position=arcs,
        independent_font_sizes=independent_font_sizes,
    )

    common_font_size = _common_font_size(
        metrics,
        glyph_height,
    )

    def make_fit(position: str) -> LabelFit | None:
        text = participating.get(position)

        if text is None:
            return None

        label_metrics = metrics[position]

        font_size = (
            font_size_for_height(
                label_metrics,
                glyph_height=glyph_height,
            )
            if independent_font_sizes
            else common_font_size
        )

        return LabelFit(
            text=text,
            metrics=label_metrics,
            width=_rendered_width(
                label_metrics,
                font_size=font_size,
            ),
            rendered_height=_rendered_height(
                label_metrics,
                font_size=font_size,
            ),
            font_size=font_size,
        )

    (
        bottom_baseline_radius,
        top_baseline_radius,
        inner_boundary_radius,
    ) = _circular_baseline_radii(
        reference_radius=reference_radius,
        border_width=border_width,
        glyph_height=glyph_height,
    )

    return CircularBorderLabelFit(
        glyph_height=glyph_height,
        font_size=common_font_size,
        bottom_baseline_radius=bottom_baseline_radius,
        top_baseline_radius=top_baseline_radius,
        inner_boundary_radius=inner_boundary_radius,
        top=make_fit("top"),
        bottom=make_fit("bottom"),
    )


__all__ = [
    "BorderLabelError",
    "CircularBorderLabelFit",
    "GLYPH_HEIGHT_MAX_ITERATIONS",
    "GLYPH_HEIGHT_TOLERANCE_MM",
    "LabelFit",
    "LabelMeasurement",
    "LabelMetrics",
    "REFERENCE_FONT_SIZE",
    "available_arc_length",
    "bottom_label_path",
    "circular_arc_path",
    "fit_circular_border_labels",
    "font_size_for_height",
    "measure_label_metrics",
    "measure_participating_labels",
    "measurement_from_metrics",
    "point_on_circle",
    "top_label_path",
    "write_registered_circular_label_svg",
]
