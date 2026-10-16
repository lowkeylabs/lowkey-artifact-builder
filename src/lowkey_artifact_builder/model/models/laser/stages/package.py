"""
Package registered Shape composition as a laser-ready SVG.
"""
# File: src/lowkey_artifact_builder/model/models/laser/stages/package.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import copy
import json
import math
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from lowkey_artifact_builder.engine import StageContext

SVG_NS = "http://www.w3.org/2000/svg"
SVG = f"{{{SVG_NS}}}"

ET.register_namespace("", SVG_NS)

SHAPE_BOUNDARY_ID = "shape-boundary"
RIDGE_INNER_BOUNDARY_ID = "ridge-inner-boundary"
INNER_RIDGE_OUTER_BOUNDARY_ID = "inner-ridge-outer-boundary"
INNER_RIDGE_INNER_BOUNDARY_ID = "inner-ridge-inner-boundary"


def _number(value: float) -> str:
    return format(value, ".12g")


def _load_svg(path: Path) -> ET.Element:
    """
    Load a registered SVG document.
    """
    root = ET.parse(path).getroot()

    if root.tag != f"{SVG}svg":
        raise ValueError(f"Expected SVG document: {path}")

    return root


def _registered_boundaries(
    composition_path: Path,
) -> dict[str, ET.Element]:
    """
    Load registered structural boundaries by semantic identity.

    Shape Compose owns geometry and placement. Laser interprets
    the same boundary identities used by Shape Extrude.
    """
    source = _load_svg(composition_path)

    recognized = {
        SHAPE_BOUNDARY_ID,
        RIDGE_INNER_BOUNDARY_ID,
        INNER_RIDGE_OUTER_BOUNDARY_ID,
        INNER_RIDGE_INNER_BOUNDARY_ID,
    }

    boundaries: dict[str, ET.Element] = {}

    for element in source:
        identifier = element.get("id")

        if identifier not in recognized:
            continue

        if identifier in boundaries:
            raise ValueError(f"Duplicate registered Shape boundary: {identifier}")

        boundaries[identifier] = element

    if SHAPE_BOUNDARY_ID not in boundaries:
        raise ValueError("Registered Shape composition requires shape-boundary.")

    return boundaries


def _boundary_path(
    element: ET.Element,
) -> str:
    """
    Express one registered structural boundary as SVG path data.

    Shape Compose currently registers circular, rectangular, and
    polygonal boundaries. Conversion preserves their coordinates
    without independently scaling or centering them.
    """
    if element.tag == f"{SVG}circle":
        cx = float(element.get("cx", "0"))
        cy = float(element.get("cy", "0"))
        radius = float(element.attrib["r"])

        if not all(math.isfinite(v) for v in (cx, cy, radius)):
            raise ValueError("Circle boundary must be finite.")

        if radius <= 0:
            raise ValueError("Circle boundary radius must be positive.")

        left = _number(cx - radius)
        right = _number(cx + radius)
        center_y = _number(cy)
        r = _number(radius)

        return (
            f"M {left} {center_y} "
            f"A {r} {r} 0 1 0 {right} {center_y} "
            f"A {r} {r} 0 1 0 {left} {center_y} Z"
        )

    if element.tag == f"{SVG}rect":
        x = float(element.get("x", "0"))
        y = float(element.get("y", "0"))
        width = float(element.attrib["width"])
        height = float(element.attrib["height"])

        if not all(math.isfinite(v) for v in (x, y, width, height)):
            raise ValueError("Rectangle boundary must be finite.")

        if width <= 0 or height <= 0:
            raise ValueError("Rectangle boundary dimensions must be positive.")

        x2 = x + width
        y2 = y + height

        return (
            f"M {_number(x)} {_number(y)} "
            f"L {_number(x2)} {_number(y)} "
            f"L {_number(x2)} {_number(y2)} "
            f"L {_number(x)} {_number(y2)} Z"
        )

    if element.tag == f"{SVG}polygon":
        raw_points = element.attrib["points"]
        coordinates = raw_points.replace(",", " ").split()

        if len(coordinates) < 6 or len(coordinates) % 2:
            raise ValueError("Polygon boundary requires at least three vertices.")

        values = [float(value) for value in coordinates]

        if not all(math.isfinite(value) for value in values):
            raise ValueError("Polygon boundary must be finite.")

        points = [(_number(values[i]), _number(values[i + 1])) for i in range(0, len(values), 2)]

        first_x, first_y = points[0]

        segments = [f"M {first_x} {first_y}"]

        for x, y in points[1:]:
            segments.append(f"L {x} {y}")

        segments.append("Z")

        return " ".join(segments)

    raise ValueError(f"Unsupported registered Shape boundary: {element.tag}")


def _add_outline(
    parent: ET.Element,
    identifier: str,
    boundary: ET.Element,
) -> None:
    """
    Export a structural perimeter as an unfilled outline.
    """
    ET.SubElement(
        parent,
        f"{SVG}path",
        {
            "id": identifier,
            "d": _boundary_path(boundary),
            "fill": "none",
            "stroke": "black",
        },
    )


def _add_region(
    parent: ET.Element,
    identifier: str,
    outer: ET.Element,
    inner: ET.Element,
) -> None:
    """
    Export the planar region between two registered boundaries.

    Even-odd filling preserves the interior opening independently
    of path winding direction.
    """
    outer_path = _boundary_path(outer)
    inner_path = _boundary_path(inner)

    ET.SubElement(
        parent,
        f"{SVG}path",
        {
            "id": identifier,
            "d": f"{outer_path} {inner_path}",
            "fill": "black",
            "fill-rule": "evenodd",
            "stroke": "none",
        },
    )


def _add_structure(
    output: ET.Element,
    composition_path: Path,
) -> None:
    """
    Export Shape structural geometry using Shape Extrude semantics.

    Registered boundaries describe physical regions. The perimeter
    is an outline; participating ridges are filled planar regions.

    Construction geometry, including border-label baselines,
    is not exported.
    """
    boundaries = _registered_boundaries(composition_path)

    structure = ET.SubElement(
        output,
        f"{SVG}g",
        {"id": "structure"},
    )

    shape_boundary = boundaries[SHAPE_BOUNDARY_ID]

    _add_outline(
        structure,
        SHAPE_BOUNDARY_ID,
        shape_boundary,
    )

    ridge_inner = boundaries.get(RIDGE_INNER_BOUNDARY_ID)

    if ridge_inner is not None:
        _add_region(
            structure,
            "ridge",
            shape_boundary,
            ridge_inner,
        )

    inner_ridge_outer = boundaries.get(INNER_RIDGE_OUTER_BOUNDARY_ID)
    inner_ridge_inner = boundaries.get(INNER_RIDGE_INNER_BOUNDARY_ID)

    if (inner_ridge_outer is None) != (inner_ridge_inner is None):
        raise ValueError("Registered inner ridge requires both boundaries.")

    if inner_ridge_outer is not None and inner_ridge_inner is not None:
        _add_region(
            structure,
            "inner-ridge",
            inner_ridge_outer,
            inner_ridge_inner,
        )


def _add_border_labels(
    output: ET.Element,
    directory: Path,
    border_labels: dict[str, Any],
) -> None:
    """
    Export participating registered border-label geometry.

    Shape Compose has already resolved typography, glyph outlines,
    font metrics, and placement. Laser must not reconstruct text
    or depend on installed fonts.
    """
    for position in ("top", "bottom"):
        entry = border_labels.get(position)

        if entry is None:
            continue

        source_path = directory / str(entry["path"])
        source = _load_svg(source_path)

        component = ET.SubElement(
            output,
            f"{SVG}g",
            {"id": f"{position}-border-label"},
        )

        for element in source:
            component.append(copy.deepcopy(element))


def _add_artwork(
    output: ET.Element,
    directory: Path,
    artwork: dict[str, Any],
) -> None:
    """
    Export registered Artwork using its persisted common transform.

    The transform maps source Artwork coordinates into registered
    Shape coordinates. Physical sizing is applied by the outer SVG.

    Each Artwork color region remains independently identifiable.
    """
    transform = artwork["transform"]

    scale = float(transform["scale"])
    tx = float(transform["translate_x"])
    ty = float(transform["translate_y"])

    if not all(math.isfinite(v) for v in (scale, tx, ty)):
        raise ValueError("Artwork transform must be finite.")

    if scale <= 0:
        raise ValueError("Artwork scale must be positive.")

    placement = ET.SubElement(
        output,
        f"{SVG}g",
        {
            "id": "artwork",
            "transform": (f"translate({_number(tx)} {_number(ty)}) scale({_number(scale)})"),
        },
    )

    for entry in artwork["components"]:
        index = int(entry["index"])
        source_path = directory / str(entry["path"])
        source = _load_svg(source_path)

        component = ET.SubElement(
            placement,
            f"{SVG}g",
            {"id": f"artwork-{index}"},
        )

        for element in source:
            component.append(copy.deepcopy(element))


def execute(context: StageContext) -> None:
    """
    Produce one physically dimensioned SVG from Shape Compose Products.

    The output contains participating registered geometry in a
    common coordinate system, without Shape extrusion or 3MF
    packaging.

    Shape Compose owns registration and placement. Laser owns
    the two-dimensional manufacturing representation.
    """
    manifest_path = context.input("shape.compose.manifest")
    output_path = context.output("artifact")

    shape_size = float(context.resolver("shape_size"))

    if not math.isfinite(shape_size) or shape_size <= 0:
        raise ValueError("shape_size must be finite and positive.")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    directory = manifest_path.parent
    composition_path = directory / manifest["composition"]

    output = ET.Element(
        f"{SVG}svg",
        {
            "width": f"{_number(shape_size)}mm",
            "height": f"{_number(shape_size)}mm",
            "viewBox": "-0.5 -0.5 1 1",
        },
    )

    _add_structure(
        output,
        composition_path,
    )

    border_labels = manifest.get("border_labels")

    if border_labels is not None:
        _add_border_labels(
            output,
            directory,
            border_labels,
        )

    artwork = manifest.get("artwork")

    if artwork is not None:
        _add_artwork(
            output,
            directory,
            artwork,
        )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    ET.ElementTree(output).write(
        output_path,
        encoding="utf-8",
        xml_declaration=True,
    )
