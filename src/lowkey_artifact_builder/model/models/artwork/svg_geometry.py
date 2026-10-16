"""Validate filled native-SVG geometry across Artifact colors.

This module does not modify SVG paths or rasterize artwork. Curves are
flattened for intersection testing only; downstream Vector retains the
original authored geometry.
"""

# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import math
import re
import xml.etree.ElementTree as ET
from collections.abc import Sequence

from shapely.geometry import LineString, Point
from shapely.geometry.base import BaseGeometry
from shapely.ops import polygonize, unary_union
from svgpathtools import parse_path

from lowkey_artifact_builder.formats.svg import SVG_NS

type RGB = tuple[int, int, int]
type Matrix = tuple[float, float, float, float, float, float]

_IDENTITY: Matrix = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
_NUMBER = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"
_TRANSFORM = re.compile(r"([a-zA-Z]+)\s*\(([^)]*)\)")
_VALUES = re.compile(_NUMBER)


class SVGGeometryError(ValueError):
    """Raised when SVG filled geometry is invalid or cannot be interpreted."""


def _multiply(left: Matrix, right: Matrix) -> Matrix:
    """Compose affine transforms, applying right before left."""
    a, b, c, d, e, f = left
    g, h, i, j, k, offset_y = right

    return (
        a * g + c * h,
        b * g + d * h,
        a * i + c * j,
        b * i + d * j,
        a * k + c * offset_y + e,
        b * k + d * offset_y + f,
    )


def _transform_matrix(value: str) -> Matrix:
    """Parse standard SVG affine transform functions."""
    result = _IDENTITY
    remaining = value.strip()

    while remaining:
        match = _TRANSFORM.match(remaining)

        if match is None:
            raise SVGGeometryError(f"Unsupported SVG transform: {remaining!r}")

        name = match.group(1)
        arguments = match.group(2)
        values = [float(number) for number in _VALUES.findall(arguments)]

        residue = _VALUES.sub("", arguments)

        if residue.strip(" ,\t\r\n"):
            raise SVGGeometryError(f"Invalid SVG transform arguments: {arguments!r}")

        if name == "matrix" and len(values) == 6:
            local: Matrix = (
                values[0],
                values[1],
                values[2],
                values[3],
                values[4],
                values[5],
            )

        elif name == "translate" and len(values) in (1, 2):
            local = (
                1.0,
                0.0,
                0.0,
                1.0,
                values[0],
                values[1] if len(values) == 2 else 0.0,
            )

        elif name == "scale" and len(values) in (1, 2):
            local = (
                values[0],
                0.0,
                0.0,
                values[1] if len(values) == 2 else values[0],
                0.0,
                0.0,
            )

        elif name == "rotate" and len(values) in (1, 3):
            angle = math.radians(values[0])
            cosine, sine = math.cos(angle), math.sin(angle)

            rotation: Matrix = (
                cosine,
                sine,
                -sine,
                cosine,
                0.0,
                0.0,
            )

            if len(values) == 3:
                cx, cy = values[1:]

                local = _multiply(
                    _multiply(
                        (1, 0, 0, 1, cx, cy),
                        rotation,
                    ),
                    (1, 0, 0, 1, -cx, -cy),
                )
            else:
                local = rotation

        elif name == "skewX" and len(values) == 1:
            local = (
                1.0,
                0.0,
                math.tan(math.radians(values[0])),
                1.0,
                0.0,
                0.0,
            )

        elif name == "skewY" and len(values) == 1:
            local = (
                1.0,
                math.tan(math.radians(values[0])),
                0.0,
                1.0,
                0.0,
                0.0,
            )

        else:
            raise SVGGeometryError(f"Unsupported SVG transform: {name}({arguments})")

        result = _multiply(result, local)

        remaining = remaining[match.end() :].lstrip(" ,\t\r\n")

    return result


def _apply(
    matrix: Matrix,
    point: complex,
) -> tuple[float, float]:
    a, b, c, d, e, f = matrix

    return (
        a * point.real + c * point.imag + e,
        b * point.real + d * point.imag + f,
    )


def _style_value(
    element: ET.Element[str],
    name: str,
    inherited: str,
) -> str:
    result = element.get(name, inherited)

    for declaration in element.get("style", "").split(";"):
        key, separator, value = declaration.partition(":")

        if separator and key.strip().lower() == name:
            result = value.strip()

    return result.strip()


def _collect_paths(
    root: ET.Element[str],
) -> dict[str, tuple[ET.Element[str], Matrix, str]]:
    """Index paths with effective document transforms and fill rules."""
    found: dict[
        str,
        tuple[ET.Element[str], Matrix, str],
    ] = {}

    path_tag = f"{{{SVG_NS}}}path"
    group_tag = f"{{{SVG_NS}}}g"

    def visit(
        element: ET.Element[str],
        parent: Matrix,
        inherited_rule: str,
    ) -> None:
        local = _transform_matrix(element.get("transform", ""))

        matrix = _multiply(parent, local)

        rule = _style_value(
            element,
            "fill-rule",
            inherited_rule,
        ).lower()

        if rule not in ("evenodd", "nonzero"):
            raise SVGGeometryError(f"Unsupported SVG fill-rule: {rule!r}")

        if element.tag == path_tag:
            object_id = element.get("id")

            if not object_id:
                raise SVGGeometryError("Native SVG paths must have object IDs.")

            if object_id in found:
                raise SVGGeometryError(f"Duplicate native SVG object ID: {object_id}")

            found[object_id] = (
                element,
                matrix,
                rule,
            )

        elif element.tag == group_tag or element is root:
            for child in element:
                if child.tag in (path_tag, group_tag):
                    visit(child, matrix, rule)

    visit(root, _IDENTITY, "nonzero")

    return found


def _rings(
    element: ET.Element[str],
    matrix: Matrix,
) -> list[list[tuple[float, float]]]:
    """Approximate closed SVG subpaths as rings for validation only."""
    path_data = element.get("d", "")

    try:
        path = parse_path(path_data)
    except (ValueError, TypeError) as exc:
        raise SVGGeometryError(f"Invalid SVG path {element.get('id')!r}: {exc}") from exc

    rings: list[list[tuple[float, float]]] = []

    for subpath in path.continuous_subpaths():
        if not subpath:
            continue

        points: list[tuple[float, float]] = []

        for segment in subpath:
            # Straight edges remain exact. Curves are subdivided
            # for geometric intersection validation only.
            start = _apply(matrix, segment.start)
            end = _apply(matrix, segment.end)
            chord = math.dist(start, end)

            try:
                length = segment.length(error=1e-5)
            except (
                ValueError,
                ZeroDivisionError,
                OverflowError,
            ) as exc:
                raise SVGGeometryError("Could not measure SVG curve.") from exc

            steps = (
                1
                if segment.__class__.__name__ == "Line"
                else max(
                    16,
                    min(
                        4096,
                        math.ceil(max(length, chord) / 0.1),
                    ),
                )
            )

            if not points:
                points.append(start)

            points.extend(_apply(matrix, segment.point(i / steps)) for i in range(1, steps + 1))

        if len(points) < 3:
            continue

        if math.dist(points[0], points[-1]) > 1e-9:
            # SVG fill implicitly closes open subpaths.
            points.append(points[0])

        rings.append(points)

    return rings


def _winding_number(
    point: Point,
    ring: list[tuple[float, float]],
) -> int:
    """Compute the signed winding count of one ring around a test point."""
    x, y = point.x, point.y
    winding = 0

    for (x1, y1), (x2, y2) in zip(
        ring,
        ring[1:],
        strict=False,
    ):
        cross = (x2 - x1) * (y - y1) - (x - x1) * (y2 - y1)

        if y1 <= y < y2 and cross > 0:
            winding += 1

        elif y2 <= y < y1 and cross < 0:
            winding -= 1

    return winding


def _filled_region(
    element: ET.Element[str],
    matrix: Matrix,
    rule: str,
) -> BaseGeometry | None:
    """Construct filled geometry using the authored SVG fill rule."""
    rings = _rings(element, matrix)

    if not rings:
        return None

    boundaries = unary_union([LineString(ring) for ring in rings])

    faces = list(polygonize(boundaries))

    selected: list[BaseGeometry] = []

    for face in faces:
        interior = face.representative_point()

        windings = [_winding_number(interior, ring) for ring in rings]

        filled = (
            sum(abs(number) for number in windings) % 2 == 1
            if rule == "evenodd"
            else sum(windings) != 0
        )

        if filled:
            selected.append(face)

    return unary_union(selected) if selected else None


def validate_nonoverlapping_colors(
    tree: ET.ElementTree[ET.Element[str]],
    objects: Sequence[tuple[str, RGB]],
) -> None:
    """Reject positive-area overlap between different Artifact colors.

    Same-color overlap and boundary contact are allowed. Holes and
    inherited SVG transforms are respected. Geometry is not rewritten
    or rasterized.

    Raises:
        SVGGeometryError: Unsupported geometry or conflicting object IDs.
    """
    root = tree.getroot()

    if root.tag != f"{{{SVG_NS}}}svg":
        raise SVGGeometryError("Artwork source is not an SVG document.")

    indexed = _collect_paths(root)

    regions: list[tuple[str, RGB, BaseGeometry]] = []

    for object_id, color in objects:
        try:
            element, matrix, rule = indexed[object_id]
        except KeyError as exc:
            raise SVGGeometryError(f"Missing native SVG object: {object_id}") from exc

        region = _filled_region(
            element,
            matrix,
            rule,
        )

        if region is None or region.is_empty:
            continue

        for prior_id, prior_color, prior_region in regions:
            if prior_color == color:
                continue

            intersection = region.intersection(prior_region)

            if intersection.area > 1e-9:
                raise SVGGeometryError(
                    f"Native SVG color overlap between objects "
                    f"{prior_id!r} and {object_id!r}. "
                    "Separate their filled interiors "
                    "or assign the same Artifact color."
                )

        regions.append((object_id, color, region))


SVGMatrix = Matrix
SVG_IDENTITY = _IDENTITY

svg_transform_matrix = _transform_matrix
svg_multiply = _multiply
svg_apply = _apply


__all__ = [
    "SVGGeometryError",
    "SVGMatrix",
    "SVG_IDENTITY",
    "svg_transform_matrix",
    "svg_multiply",
    "svg_apply",
    "validate_nonoverlapping_colors",
]
