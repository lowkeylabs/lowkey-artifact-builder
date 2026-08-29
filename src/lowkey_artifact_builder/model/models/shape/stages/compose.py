"""
Registered composition for the Shape model.

This module establishes the registered-geometry composition boundary for
Shape.

Registered structural Shape geometry and registered Artwork remain
nonphysical through this stage. Physical Shape dimensionalization and
extrusion belong to downstream Shape stages.
"""
# File: src/lowkey_artifact_builder/model/models/shape/stages/compose.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
import math
import shutil
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from lowkey_artifact_builder.engine import StageContext

SVG_NAMESPACE = "http://www.w3.org/2000/svg"
SVG_CIRCLE = f"{{{SVG_NAMESPACE}}}circle"
SVG_RECT = f"{{{SVG_NAMESPACE}}}rect"
SVG_POLYGON = f"{{{SVG_NAMESPACE}}}polygon"

ET.register_namespace(
    "",
    SVG_NAMESPACE,
)

# =========================================================
# Registered Artwork
# =========================================================


@dataclass(frozen=True)
class RegisteredExtent:
    """
    Common registered coordinate extent of an Artwork component collection.
    """

    width: float
    height: float


@dataclass(frozen=True)
class RegisteredBounds:
    """
    Bounds of occupied geometry in a registered coordinate system.
    """

    x: float
    y: float
    width: float
    height: float


@dataclass(frozen=True)
class RegisteredArtworkComponent:
    """
    One component declared by a registered Artwork manifest.

    The component payload remains opaque to this manifest-loading boundary.
    """

    index: int
    path: Path
    name: str
    color: dict[str, Any]


@dataclass(frozen=True)
class RegisteredArtwork:
    """
    Registered Artwork supplied to Shape through an Artwork vector manifest.

    The envelope and every component share the common registered coordinate
    system declared by registered_extent.
    """

    registered_extent: RegisteredExtent
    envelope: Path
    components: tuple[RegisteredArtworkComponent, ...]


@dataclass(frozen=True)
class RegisteredArtworkTransform:
    """
    One common transformation applied to registered Artwork.

    The transformation uniformly scales the registered coordinate system
    to fit within the available region and centers the transformed extent.
    """

    scale: float
    width: float
    height: float
    translate_x: float
    translate_y: float


@dataclass(frozen=True)
class PlacedRegisteredArtworkComponent:
    """
    One registered Artwork component associated with its common transform.

    The component payload remains unchanged and opaque at this boundary.
    """

    component: RegisteredArtworkComponent
    transform: RegisteredArtworkTransform


@dataclass(frozen=True)
class PlacedRegisteredArtwork:
    """
    Registered Artwork positioned within an available region.

    Every component shares the same transformation so their registered
    relationship is preserved.
    """

    transform: RegisteredArtworkTransform
    components: tuple[PlacedRegisteredArtworkComponent, ...]


# =========================================================
# Public interface
# =========================================================


def registered_interior_region(
    composition: Path,
) -> ET.Element:
    """
    Return the boundary defining the registered Shape interior region.

    The innermost existing ridge boundary defines the interior region.
    When no ridge boundary exists, the registered Shape boundary defines
    the interior region.
    """

    root = ET.parse(
        composition,
    ).getroot()

    ridge_boundaries = tuple(
        element for element in root if element.get("id") == "ridge-inner-boundary"
    )

    if ridge_boundaries:
        return ridge_boundaries[-1]

    shape_boundary = next(
        (element for element in root if element.get("id") == "shape-boundary"),
        None,
    )

    if shape_boundary is not None:
        return shape_boundary

    shape_boundary = next(
        (
            element
            for element in root
            if element.tag
            in {
                SVG_CIRCLE,
                SVG_RECT,
                SVG_POLYGON,
            }
        ),
        None,
    )

    if shape_boundary is None:
        raise ValueError("Registered Shape composition requires a Shape boundary.")

    return shape_boundary


def execute(
    context: StageContext,
) -> None:
    """
    Execute registered Shape composition.

    Composition consumes registered Shape structure and establishes structural
    partition geometry in the same registered coordinate system.

    Physical ridge width is interpreted relative to physical Shape size so the
    resulting partition boundary can be represented in registered space.

    Physical Z dimensions remain downstream.
    """

    structure_input = context.input(
        "structure.structure",
    )

    output = context.output(
        "composition",
    )

    shape_size = float(
        context.resolver("shape_size"),
    )
    ridge_width = float(
        context.resolver("shape_outer_ridge_width"),
    )
    ridge_style = str(
        context.resolver("shape_outer_ridge_style"),
    )

    if ridge_style in {
        "integrated",
        "separate",
    }:
        _compose_ridge(
            structure_input,
            output,
            shape_size=shape_size,
            ridge_width=ridge_width,
        )
        return

    shutil.copyfile(
        structure_input,
        output,
    )


# =========================================================
# Structural composition
# =========================================================


def _compose_ridge(
    structure_input: Path,
    output: Path,
    *,
    shape_size: float,
    ridge_width: float,
) -> None:
    """
    Compose ridge boundaries in registered Shape space.

    The complete Shape boundary remains unchanged. Physical ridge width is
    converted into a registered-space inset that establishes the ridge's
    inner boundary.

    Ridge existence is determined solely by ridge width. Zero width preserves
    the registered Shape boundary without creating a ridge partition, while
    negative width is invalid.

    Integrated and separate ridge styles share these registered boundaries.
    Their different physical component partitioning belongs downstream.

    Circle, square, and regular-polygon registered structures are supported.
    """

    if ridge_width < 0.0:
        raise ValueError("shape_outer_ridge_width must be nonnegative.")

    tree = ET.parse(
        structure_input,
    )
    root = tree.getroot()

    circle = root.find(
        SVG_CIRCLE,
    )
    square = root.find(
        SVG_RECT,
    )
    polygon = root.find(
        SVG_POLYGON,
    )

    outer_boundary = circle if circle is not None else square if square is not None else polygon

    if outer_boundary is None:
        raise ValueError("Ridge composition requires supported registered Shape structure.")

    outer_boundary.set(
        "id",
        "shape-boundary",
    )

    if ridge_width == 0.0:
        tree.write(
            output,
            encoding="unicode",
        )
        return

    registered_inset = ridge_width / shape_size

    if circle is not None:
        _compose_circle_ridge(
            root,
            circle,
            registered_inset=registered_inset,
        )

    elif square is not None:
        _compose_square_ridge(
            root,
            square,
            registered_inset=registered_inset,
        )

    else:
        assert polygon is not None

        _compose_polygon_ridge(
            root,
            polygon,
            registered_inset=registered_inset,
        )

    tree.write(
        output,
        encoding="unicode",
    )


def _compose_circle_ridge(
    root: ET.Element,
    outer_boundary: ET.Element,
    *,
    registered_inset: float,
) -> None:
    """
    Establish registered outer and inner boundaries for a circle ridge.
    """

    outer_boundary.set(
        "id",
        "shape-boundary",
    )

    outer_radius = float(
        outer_boundary.get(
            "r",
            "0.0",
        )
    )

    inner_radius = outer_radius - registered_inset

    ET.SubElement(
        root,
        SVG_CIRCLE,
        {
            "id": "ridge-inner-boundary",
            "cx": outer_boundary.get("cx", "0.0"),
            "cy": outer_boundary.get("cy", "0.0"),
            "r": str(inner_radius),
        },
    )


def _compose_square_ridge(
    root: ET.Element,
    outer_boundary: ET.Element,
    *,
    registered_inset: float,
) -> None:
    """
    Establish registered outer and inner boundaries for a square ridge.

    Ridge width is measured inward from every side, so the inner square loses
    twice the registered inset from both its width and height.
    """

    outer_boundary.set(
        "id",
        "shape-boundary",
    )

    outer_x = float(
        outer_boundary.get(
            "x",
            "0.0",
        )
    )
    outer_y = float(
        outer_boundary.get(
            "y",
            "0.0",
        )
    )
    outer_width = float(
        outer_boundary.get(
            "width",
            "0.0",
        )
    )
    outer_height = float(
        outer_boundary.get(
            "height",
            "0.0",
        )
    )

    ET.SubElement(
        root,
        SVG_RECT,
        {
            "id": "ridge-inner-boundary",
            "x": str(outer_x + registered_inset),
            "y": str(outer_y + registered_inset),
            "width": str(outer_width - (2.0 * registered_inset)),
            "height": str(outer_height - (2.0 * registered_inset)),
        },
    )


def _compose_polygon_ridge(
    root: ET.Element,
    outer_boundary: ET.Element,
    *,
    registered_inset: float,
) -> None:
    """
    Establish registered outer and inner boundaries for a polygon ridge.

    Each outer edge is translated inward by registered_inset along its
    perpendicular normal. Adjacent translated edge lines are intersected to
    establish the vertices of the inner polygon.

    This preserves parallel corresponding edges and gives ridge width its
    perpendicular edge-distance semantics rather than treating the ridge as
    a radial scale of the outer polygon.
    """

    outer_points = _read_polygon_points(
        outer_boundary,
    )

    inner_points = _inset_polygon(
        outer_points,
        inset=registered_inset,
    )

    outer_boundary.set(
        "id",
        "shape-boundary",
    )

    ET.SubElement(
        root,
        SVG_POLYGON,
        {
            "id": "ridge-inner-boundary",
            "points": _format_polygon_points(
                inner_points,
            ),
        },
    )


# =========================================================
# Polygon composition helpers
# =========================================================


def _read_polygon_points(
    polygon: ET.Element,
) -> tuple[tuple[float, float], ...]:
    """
    Read registered vertices from an SVG polygon element.
    """

    points = polygon.get(
        "points",
    )

    if points is None:
        raise ValueError("Registered polygon structure requires polygon points.")

    vertices = tuple(
        _parse_polygon_point(
            point,
        )
        for point in points.split()
    )

    if len(vertices) < 3:
        raise ValueError("Registered polygon structure requires at least 3 vertices.")

    return vertices


def _parse_polygon_point(
    point: str,
) -> tuple[float, float]:
    """
    Parse one SVG polygon point.
    """

    coordinates = point.split(
        ",",
    )

    if len(coordinates) != 2:
        raise ValueError("Registered polygon structure contains an invalid polygon point.")

    return (
        float(coordinates[0]),
        float(coordinates[1]),
    )


def _format_polygon_points(
    points: tuple[tuple[float, float], ...],
) -> str:
    """
    Format registered polygon vertices for SVG persistence.
    """

    return " ".join(f"{x},{y}" for x, y in points)


def _inset_polygon(
    points: tuple[tuple[float, float], ...],
    *,
    inset: float,
) -> tuple[tuple[float, float], ...]:
    """
    Construct an inward edge-offset polygon.

    Each edge is represented by an inward-translated parallel line. The
    intersection of each edge with its following edge produces one vertex of
    the inset polygon.
    """

    orientation = _polygon_orientation(
        points,
    )

    offset_lines = tuple(
        _offset_edge_line(
            points[index],
            points[(index + 1) % len(points)],
            inset=inset,
            orientation=orientation,
        )
        for index in range(len(points))
    )

    return tuple(
        _intersect_lines(
            offset_lines[(index - 1) % len(offset_lines)],
            offset_lines[index],
        )
        for index in range(len(offset_lines))
    )


def _polygon_orientation(
    points: tuple[tuple[float, float], ...],
) -> float:
    """
    Return the signed orientation of a polygon.

    Positive values indicate counterclockwise vertex order and negative
    values indicate clockwise vertex order.
    """

    signed_area_twice = sum(
        (start[0] * end[1] - end[0] * start[1])
        for start, end in (
            (
                points[index],
                points[(index + 1) % len(points)],
            )
            for index in range(len(points))
        )
    )

    if math.isclose(
        signed_area_twice,
        0.0,
        abs_tol=1.0e-12,
    ):
        raise ValueError("Registered polygon structure has zero area.")

    return signed_area_twice


def _offset_edge_line(
    start: tuple[float, float],
    end: tuple[float, float],
    *,
    inset: float,
    orientation: float,
) -> tuple[
    tuple[float, float],
    tuple[float, float],
]:
    """
    Translate one polygon edge inward by a perpendicular registered distance.

    The polygon orientation determines which perpendicular normal points
    toward the polygon interior.
    """

    dx = end[0] - start[0]
    dy = end[1] - start[1]

    length = math.hypot(
        dx,
        dy,
    )

    if math.isclose(
        length,
        0.0,
        abs_tol=1.0e-12,
    ):
        raise ValueError("Registered polygon structure contains a zero-length edge.")

    if orientation > 0.0:
        normal_x = -dy / length
        normal_y = dx / length
    else:
        normal_x = dy / length
        normal_y = -dx / length

    offset_x = normal_x * inset
    offset_y = normal_y * inset

    return (
        (
            start[0] + offset_x,
            start[1] + offset_y,
        ),
        (
            end[0] + offset_x,
            end[1] + offset_y,
        ),
    )


def _intersect_lines(
    first: tuple[
        tuple[float, float],
        tuple[float, float],
    ],
    second: tuple[
        tuple[float, float],
        tuple[float, float],
    ],
) -> tuple[float, float]:
    """
    Return the intersection of two infinite lines.

    Adjacent edges of a valid regular polygon are nonparallel, so their inward
    offset lines must have one unique intersection.
    """

    first_start, first_end = first
    second_start, second_end = second

    first_dx = first_end[0] - first_start[0]
    first_dy = first_end[1] - first_start[1]

    second_dx = second_end[0] - second_start[0]
    second_dy = second_end[1] - second_start[1]

    denominator = first_dx * second_dy - first_dy * second_dx

    if math.isclose(
        denominator,
        0.0,
        abs_tol=1.0e-12,
    ):
        raise ValueError("Registered polygon structure contains parallel adjacent edges.")

    delta_x = second_start[0] - first_start[0]
    delta_y = second_start[1] - first_start[1]

    first_parameter = (delta_x * second_dy - delta_y * second_dx) / denominator

    return (
        first_start[0] + first_parameter * first_dx,
        first_start[1] + first_parameter * first_dy,
    )


# =========================================================
# Registered Artwork placement
# =========================================================


def registered_artwork_envelope_bounds(
    artwork: RegisteredArtwork,
) -> RegisteredBounds:
    """
    Return the occupied bounds declared by the registered Artwork envelope.

    The Artwork envelope is interpreted in the common registered coordinate
    system. Component geometry is not inspected independently.
    """

    root = ET.parse(
        artwork.envelope,
    ).getroot()

    envelope = next(
        iter(root),
        None,
    )

    if envelope is None:
        raise ValueError("Registered Artwork envelope requires geometry.")

    return _registered_element_bounds(
        envelope,
    )


def _registered_element_bounds(
    element: ET.Element,
) -> RegisteredBounds:
    """
    Return registered bounds for supported envelope geometry.
    """

    if element.tag == SVG_RECT:
        return RegisteredBounds(
            x=float(element.get("x", "0.0")),
            y=float(element.get("y", "0.0")),
            width=float(element.get("width", "0.0")),
            height=float(element.get("height", "0.0")),
        )

    if element.tag == SVG_CIRCLE:
        center_x = float(
            element.get(
                "cx",
                "0.0",
            )
        )
        center_y = float(
            element.get(
                "cy",
                "0.0",
            )
        )
        radius = float(
            element.get(
                "r",
                "0.0",
            )
        )

        return RegisteredBounds(
            x=center_x - radius,
            y=center_y - radius,
            width=2.0 * radius,
            height=2.0 * radius,
        )

    if element.tag == SVG_POLYGON:
        points = _read_polygon_points(
            element,
        )

        x_coordinates = tuple(point[0] for point in points)
        y_coordinates = tuple(point[1] for point in points)

        minimum_x = min(
            x_coordinates,
        )
        maximum_x = max(
            x_coordinates,
        )
        minimum_y = min(
            y_coordinates,
        )
        maximum_y = max(
            y_coordinates,
        )

        return RegisteredBounds(
            x=minimum_x,
            y=minimum_y,
            width=maximum_x - minimum_x,
            height=maximum_y - minimum_y,
        )

    raise ValueError("Registered Artwork envelope contains unsupported geometry.")


def fit_registered_artwork(
    artwork: RegisteredArtwork,
    *,
    available_width: float,
    available_height: float,
) -> RegisteredArtworkTransform:
    """
    Fit registered Artwork uniformly within an available region.

    The Artwork envelope defines occupied geometry while registered_extent
    defines the common coordinate system. One uniform transformation fits
    and centers the occupied envelope within the available region.

    Individual component payloads are not inspected or independently fitted.
    """

    bounds = registered_artwork_envelope_bounds(
        artwork,
    )

    scale = min(
        available_width / bounds.width,
        available_height / bounds.height,
    )

    width = bounds.width * scale
    height = bounds.height * scale

    target_x = (available_width - width) / 2.0
    target_y = (available_height - height) / 2.0

    translate_x = target_x - (bounds.x * scale)
    translate_y = target_y - (bounds.y * scale)

    return RegisteredArtworkTransform(
        scale=scale,
        width=width,
        height=height,
        translate_x=translate_x,
        translate_y=translate_y,
    )


def fit_registered_artwork_to_shape(
    artwork: RegisteredArtwork,
    *,
    composition: Path,
) -> RegisteredArtworkTransform:
    """
    Fit registered Artwork within a rectangular Shape interior.

    The Shape composition determines the available registered region.
    Artwork occupancy is determined by its registered envelope.

    This operation currently supports rectangular Shape interiors only.
    """

    interior = registered_interior_region(
        composition,
    )

    if interior.tag != SVG_RECT:
        raise ValueError(
            "Registered Artwork fitting currently requires a rectangular Shape interior."
        )

    interior_x = float(
        interior.get(
            "x",
            "0.0",
        )
    )
    interior_y = float(
        interior.get(
            "y",
            "0.0",
        )
    )
    interior_width = float(
        interior.get(
            "width",
            "0.0",
        )
    )
    interior_height = float(
        interior.get(
            "height",
            "0.0",
        )
    )

    transform = fit_registered_artwork(
        artwork,
        available_width=interior_width,
        available_height=interior_height,
    )

    return RegisteredArtworkTransform(
        scale=transform.scale,
        width=transform.width,
        height=transform.height,
        translate_x=transform.translate_x + interior_x,
        translate_y=transform.translate_y + interior_y,
    )


def place_registered_artwork(
    artwork: RegisteredArtwork,
    *,
    available_width: float,
    available_height: float,
) -> PlacedRegisteredArtwork:
    """
    Place every registered Artwork component using one common transform.

    The common transform is calculated once from the registered collection
    extent and associated unchanged with every component. This preserves the
    registration established by the Artwork producer.
    """

    transform = fit_registered_artwork(
        artwork,
        available_width=available_width,
        available_height=available_height,
    )

    components = tuple(
        PlacedRegisteredArtworkComponent(
            component=component,
            transform=transform,
        )
        for component in artwork.components
    )

    return PlacedRegisteredArtwork(
        transform=transform,
        components=components,
    )


# =========================================================
# Manifest loading
# =========================================================


def load_registered_artwork(
    manifest_path: Path,
) -> RegisteredArtwork:
    """
    Load registered Artwork from its declared vector manifest.

    The envelope and component membership are determined exclusively by the
    manifest. Their paths are resolved relative to the manifest location.

    This boundary does not inspect registered geometry or independently
    calculate component bounds.
    """

    manifest = _load_manifest(
        manifest_path,
    )

    registered_extent = _load_registered_extent(
        manifest,
    )

    envelope = _load_envelope(
        manifest,
        manifest_path=manifest_path,
    )

    components = _load_components(
        manifest,
        manifest_path=manifest_path,
    )

    return RegisteredArtwork(
        registered_extent=registered_extent,
        envelope=envelope,
        components=components,
    )


def _load_manifest(
    manifest_path: Path,
) -> dict[str, Any]:
    """
    Load the vector manifest document.
    """

    with manifest_path.open(
        "r",
        encoding="utf-8",
    ) as stream:
        manifest = json.load(
            stream,
        )

    if not isinstance(
        manifest,
        dict,
    ):
        raise ValueError("Registered Artwork manifest must contain an object.")

    return manifest


def _load_registered_extent(
    manifest: dict[str, Any],
) -> RegisteredExtent:
    """
    Read the common registered extent declared by the manifest.
    """

    extent = manifest["registered_extent"]

    if not isinstance(
        extent,
        dict,
    ):
        raise ValueError("Registered Artwork extent must contain an object.")

    width = extent["width"]
    height = extent["height"]

    if not isinstance(
        width,
        int | float,
    ):
        raise ValueError("Registered Artwork extent width must be numeric.")

    if not isinstance(
        height,
        int | float,
    ):
        raise ValueError("Registered Artwork extent height must be numeric.")

    return RegisteredExtent(
        width=float(width),
        height=float(height),
    )


def _load_envelope(
    manifest: dict[str, Any],
    *,
    manifest_path: Path,
) -> Path:
    """
    Read the registered Artwork envelope declared by the manifest.

    The envelope path is resolved relative to the manifest location.
    """

    relative_path = manifest.get(
        "envelope",
    )

    if not isinstance(
        relative_path,
        str,
    ):
        raise ValueError("Registered Artwork manifest requires an envelope.")

    return manifest_path.parent / relative_path


def _load_components(
    manifest: dict[str, Any],
    *,
    manifest_path: Path,
) -> tuple[RegisteredArtworkComponent, ...]:
    """
    Read registered components declared by the manifest.
    """

    products = manifest["products"]

    if not isinstance(
        products,
        list,
    ):
        raise ValueError("Registered Artwork products must contain a list.")

    return tuple(
        _load_component(
            product,
            manifest_path=manifest_path,
        )
        for product in products
    )


def _load_component(
    product: Any,
    *,
    manifest_path: Path,
) -> RegisteredArtworkComponent:
    """
    Read one registered component declaration.
    """

    if not isinstance(
        product,
        dict,
    ):
        raise ValueError("Registered Artwork product must contain an object.")

    index = product["index"]
    relative_path = product["path"]
    name = product["name"]
    color = product["color"]

    if not isinstance(
        index,
        int,
    ):
        raise ValueError("Registered Artwork product index must be an integer.")

    if not isinstance(
        relative_path,
        str,
    ):
        raise ValueError("Registered Artwork product path must be a string.")

    if not isinstance(
        name,
        str,
    ):
        raise ValueError("Registered Artwork product name must be a string.")

    if not isinstance(
        color,
        dict,
    ):
        raise ValueError("Registered Artwork product color must contain an object.")

    return RegisteredArtworkComponent(
        index=index,
        path=manifest_path.parent / relative_path,
        name=name,
        color=color,
    )
