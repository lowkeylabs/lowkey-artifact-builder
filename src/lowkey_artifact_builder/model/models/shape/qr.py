"""
Registered QR Code geometry for the Shape model.

QR encoding, placement, and SVG generation are nonphysical. The complete
footprint, including the quiet zone, is partitioned into complementary
dark and light components.
"""
# File: src/lowkey_artifact_builder/model/models/shape/qr.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import math
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

import qrcode
from qrcode.constants import ERROR_CORRECT_M
from qrcode.exceptions import DataOverflowError

SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NS)

QUIET_ZONE_MODULES = 2
QR_CORNER_RADIUS_MM = 1.0
QR_CORNER_ARC_SEGMENTS = 12

_Point = tuple[int, int]
_Edge = tuple[_Point, _Point]


@dataclass(frozen=True)
class QRFootprint:
    """Square QR footprint in registered Shape coordinates."""

    x: float
    y: float
    width: float
    height: float


@dataclass(frozen=True)
class QRInterior:
    """
    Available registered Shape interior.

    A circular interior is represented by its center and radius.
    Rectangular and convex polygonal interiors use ordered vertices.

    Coordinates remain registered and nonphysical.
    """

    circle: tuple[float, float, float] | None = None
    vertices: tuple[tuple[float, float], ...] = ()


@dataclass(frozen=True)
class RegisteredQR:
    footprint: QRFootprint
    quiet_zone_modules: int
    components: dict[str, Path]


def encode_qr(payload: str) -> list[list[bool]]:
    """
    Encode a payload with error correction M and a four-module quiet zone.

    The returned matrix includes the quiet zone.
    """
    encoder = qrcode.QRCode(
        version=None,
        error_correction=ERROR_CORRECT_M,
        box_size=1,
        border=QUIET_ZONE_MODULES,
    )

    try:
        encoder.add_data(payload)
        encoder.make(fit=True)
    except DataOverflowError as exc:
        raise ValueError("QR payload exceeds QR encoding capacity.") from exc

    return [[bool(module) for module in row] for row in encoder.get_matrix()]


def _rounded_qr_corner_points(
    *,
    x: float,
    y: float,
    size: float,
    radius: float,
    corner: str,
) -> tuple[tuple[float, float], ...]:
    """
    Return a filled polygon for one rounded corner of a square QR footprint.

    Coordinates remain in registered Shape space. The polygon occupies
    the corner's radius-by-radius square, excluding the area outside
    the rounded outer boundary.

    The resulting geometry uses ordinary SVG polygons and is suitable
    for downstream OpenSCAD import.
    """
    if radius <= 0.0 or radius > size:
        raise ValueError("Invalid QR corner radius.")

    centers = {
        "top-left": (x + radius, y + radius),
        "top-right": (x + size - radius, y + radius),
        "bottom-right": (x + size - radius, y + size - radius),
        "bottom-left": (x + radius, y + size - radius),
    }

    angles = {
        "top-left": (180.0, 270.0),
        "top-right": (270.0, 360.0),
        "bottom-right": (0.0, 90.0),
        "bottom-left": (90.0, 180.0),
    }

    if corner not in centers:
        raise ValueError(f"Unsupported QR corner: {corner}")

    center_x, center_y = centers[corner]
    start_degrees, end_degrees = angles[corner]

    points: list[tuple[float, float]] = [
        (center_x, center_y),
    ]

    for index in range(QR_CORNER_ARC_SEGMENTS + 1):
        fraction = index / QR_CORNER_ARC_SEGMENTS

        angle = math.radians(start_degrees + (end_degrees - start_degrees) * fraction)

        points.append(
            (
                center_x + radius * math.cos(angle),
                center_y + radius * math.sin(angle),
            )
        )

    return tuple(points)


def _write_component(
    path: Path,
    matrix: list[list[bool]],
    *,
    dark: bool,
    footprint: QRFootprint,
    corner_radius: float = 0.0,
) -> None:
    """
    Write one QR color partition as boundary-traced SVG paths.

    Internal edges between adjacent same-color modules are removed.
    Separate regions and holes are represented by closed contours.

    Diagonal module contacts remain geometrically exact. The light
    partition includes the quiet zone and rounded outer corners.

    All coordinates remain registered and nonphysical.
    """
    count = len(matrix)

    if count == 0 or any(len(row) != count for row in matrix):
        raise ValueError("QR matrix must be nonempty and square.")

    if not math.isclose(
        footprint.width,
        footprint.height,
        rel_tol=1.0e-12,
        abs_tol=1.0e-12,
    ):
        raise ValueError("QR footprint must be square.")

    if not math.isfinite(footprint.width) or footprint.width <= 0.0:
        raise ValueError("QR footprint must have positive dimensions.")

    if not math.isfinite(corner_radius) or corner_radius < 0.0:
        raise ValueError("QR corner radius must be finite and nonnegative.")

    pitch = footprint.width / count
    radius = 0.0 if dark else corner_radius

    if radius > QUIET_ZONE_MODULES * pitch:
        raise ValueError("QR corner radius exceeds the four-module quiet zone.")

    root = ET.Element(
        f"{{{SVG_NS}}}svg",
        {"viewBox": "-0.5 -0.5 1 1"},
    )

    def occupied(row: int, column: int) -> bool:
        return 0 <= row < count and 0 <= column < count and matrix[row][column] is dark

    # Orient boundary edges with occupied material on the right.
    # SVG coordinates increase downward.
    edges: set[_Edge] = set()

    for row in range(count):
        for column in range(count):
            if not occupied(row, column):
                continue

            x = column
            y = row

            if not occupied(row - 1, column):
                edges.add(((x, y), (x + 1, y)))

            if not occupied(row, column + 1):
                edges.add(((x + 1, y), (x + 1, y + 1)))

            if not occupied(row + 1, column):
                edges.add(((x + 1, y + 1), (x, y + 1)))

            if not occupied(row, column - 1):
                edges.add(((x, y + 1), (x, y)))

    outgoing: dict[_Point, set[_Point]] = {}

    for start, end in edges:
        outgoing.setdefault(start, set()).add(end)

    # Direction indices follow clockwise screen-coordinate order:
    # right, down, left, up.
    directions: tuple[_Point, ...] = (
        (1, 0),
        (0, 1),
        (-1, 0),
        (0, -1),
    )

    def direction_index(start: _Point, end: _Point) -> int:
        delta = (end[0] - start[0], end[1] - start[1])
        return directions.index(delta)

    # At a diagonal contact, prefer the rightmost continuation.
    # This keeps corner-touching regions as distinct contours.
    def next_edge(previous: _Point, current: _Point) -> _Point:
        candidates = outgoing.get(current, set())

        if not candidates:
            raise ValueError("QR boundary contains an open contour.")

        incoming = direction_index(previous, current)

        def priority(candidate: _Point) -> int:
            outgoing_direction = direction_index(current, candidate)
            turn = (outgoing_direction - incoming) % 4

            return {
                1: 0,  # Right turn
                0: 1,  # Straight
                3: 2,  # Left turn
                2: 3,  # Reverse
            }[turn]

        return min(candidates, key=priority)

    remaining = set(edges)
    contours: list[list[_Point]] = []

    while remaining:
        start, first = min(remaining)
        remaining.remove((start, first))

        contour = [start]
        previous = start
        current = first

        while current != start:
            contour.append(current)

            following = next_edge(previous, current)
            edge = (current, following)

            if edge not in remaining:
                raise ValueError("QR boundary contains a repeated or missing edge.")

            remaining.remove(edge)
            previous, current = current, following

        if len(contour) < 4:
            raise ValueError("QR boundary contains a degenerate contour.")

        contours.append(contour)

    def physical_point(point: _Point) -> tuple[float, float]:
        return (
            footprint.x + point[0] * pitch,
            footprint.y + point[1] * pitch,
        )

    def corner_points(
        point: _Point,
    ) -> list[tuple[float, float]] | None:
        if radius == 0.0:
            return None

        corners: dict[_Point, str] = {
            (0, 0): "top-left",
            (count, 0): "top-right",
            (count, count): "bottom-right",
            (0, count): "bottom-left",
        }

        corner = corners.get(point)

        if corner is None:
            return None

        # The helper returns a center point followed by the arc.
        # Only the arc belongs to the exterior boundary.
        return list(
            _rounded_qr_corner_points(
                x=footprint.x,
                y=footprint.y,
                size=footprint.width,
                radius=radius,
                corner=corner,
            )[1:]
        )

    def contour_points(
        contour: list[_Point],
    ) -> list[tuple[float, float]]:
        result: list[tuple[float, float]] = []

        for point in contour:
            arc = corner_points(point)

            if arc is None:
                result.append(physical_point(point))
            else:
                result.extend(arc)

        return result

    # A single compound path represents disconnected regions and
    # interior holes. The boundary orientations are preserved.
    commands: list[str] = []

    for contour in contours:
        points = contour_points(contour)

        if len(points) < 3:
            raise ValueError("QR contour has insufficient vertices.")

        first_x, first_y = points[0]
        commands.append(f"M {first_x:.12g},{first_y:.12g}")

        for x, y in points[1:]:
            commands.append(f"L {x:.12g},{y:.12g}")

        commands.append("Z")

    if commands:
        ET.SubElement(
            root,
            f"{{{SVG_NS}}}path",
            {
                "d": " ".join(commands),
                "fill": "black",
                "fill-rule": "evenodd",
            },
        )

    ET.ElementTree(root).write(
        path,
        encoding="unicode",
        xml_declaration=True,
    )


def _qr_direction(
    position: float,
) -> tuple[float, float]:
    """
    Convert a Shape clock angle to a registered radial direction.

    Zero points upward; positive angles proceed clockwise.
    """
    angle = math.radians(position)

    return (
        math.sin(angle),
        -math.cos(angle),
    )


def _qr_corners(
    center_x: float,
    center_y: float,
    half_size: float,
) -> tuple[tuple[float, float], ...]:
    """Return the four corners of an axis-aligned QR footprint."""
    return (
        (center_x - half_size, center_y - half_size),
        (center_x + half_size, center_y - half_size),
        (center_x + half_size, center_y + half_size),
        (center_x - half_size, center_y + half_size),
    )


def _qr_contains(
    interior: QRInterior,
    *,
    center_x: float,
    center_y: float,
    half_size: float,
) -> bool:
    """
    Determine whether the complete QR square fits the Shape interior.

    Supported interiors are circles, rectangles, and convex polygons.
    For convex interiors, containment of all four square corners
    establishes containment of the complete footprint.
    """
    tolerance = 1e-10

    corners = _qr_corners(
        center_x,
        center_y,
        half_size,
    )

    if interior.circle is not None:
        cx, cy, radius = interior.circle

        if not math.isfinite(radius) or radius <= 0:
            raise ValueError("QR placement requires a valid circular Shape interior.")

        return all(math.hypot(x - cx, y - cy) <= radius + tolerance for x, y in corners)

    vertices = interior.vertices

    if len(vertices) < 3:
        raise ValueError("QR placement requires a valid Shape interior.")

    signed_area = sum(
        x1 * y2 - x2 * y1
        for (x1, y1), (x2, y2) in zip(
            vertices,
            vertices[1:] + vertices[:1],
            strict=True,
        )
    )

    if abs(signed_area) <= tolerance:
        raise ValueError("QR placement requires a nondegenerate Shape interior.")

    orientation = 1.0 if signed_area > 0 else -1.0

    for (ax, ay), (bx, by) in zip(
        vertices,
        vertices[1:] + vertices[:1],
        strict=True,
    ):
        for x, y in corners:
            cross = (bx - ax) * (y - ay) - (by - ay) * (x - ax)

            if orientation * cross < -tolerance:
                return False

    return True


def _qr_outer_distance(
    interior: QRInterior,
    *,
    direction_x: float,
    direction_y: float,
    half_size: float,
) -> float:
    """
    Find the outermost feasible QR center along a radial direction.

    The supported Shape interiors are convex. Starting from a contained
    centered square, feasible translations along a ray form an interval.

    Binary search finds its outer boundary while checking the complete
    QR footprint at every candidate position.
    """
    if not _qr_contains(
        interior,
        center_x=0.0,
        center_y=0.0,
        half_size=half_size,
    ):
        raise ValueError("QR footprint cannot fit within the Shape interior.")

    if interior.circle is not None:
        cx, cy, radius = interior.circle

        upper = math.hypot(cx, cy) + radius
    else:
        upper = max(math.hypot(x, y) for x, y in interior.vertices)

    lower = 0.0

    for _ in range(64):
        middle = (lower + upper) / 2.0

        if _qr_contains(
            interior,
            center_x=middle * direction_x,
            center_y=middle * direction_y,
            half_size=half_size,
        ):
            lower = middle
        else:
            upper = middle

    return lower


def _qr_footprint(
    *,
    registered_size: float,
    alignment: str,
    position: float,
    interior: QRInterior,
) -> QRFootprint:
    """
    Place the complete axis-aligned QR footprint in registered space.

    Centered placement ignores clock position.

    Inner alignment places the inward-facing radial support boundary
    through the Shape center.

    Outer alignment places the square as far outward as possible along
    the selected ray while maintaining complete containment.
    """
    if alignment not in {
        "centered",
        "inner-aligned",
        "outer-aligned",
    }:
        raise ValueError(f"Unsupported QR alignment: {alignment}")

    half_size = registered_size / 2.0

    if not _qr_contains(
        interior,
        center_x=0.0,
        center_y=0.0,
        half_size=half_size,
    ):
        raise ValueError("QR footprint cannot fit within the Shape interior.")

    center_x = 0.0
    center_y = 0.0

    if alignment != "centered":
        direction_x, direction_y = _qr_direction(position)

        if alignment == "inner-aligned":
            distance = half_size * (abs(direction_x) + abs(direction_y))
        else:
            distance = _qr_outer_distance(
                interior,
                direction_x=direction_x,
                direction_y=direction_y,
                half_size=half_size,
            )

        center_x = distance * direction_x
        center_y = distance * direction_y

    if not _qr_contains(
        interior,
        center_x=center_x,
        center_y=center_y,
        half_size=half_size,
    ):
        raise ValueError("QR footprint exceeds the Shape interior.")

    return QRFootprint(
        x=center_x - half_size,
        y=center_y - half_size,
        width=registered_size,
        height=registered_size,
    )


def compose_qr(
    output_directory: Path,
    *,
    payload: str,
    qr_size: float,
    shape_size: float,
    alignment: str,
    position: float,
    interior: QRInterior | None = None,
) -> RegisteredQR:
    """
    Generate registered QR dark/light geometry.

    The complete footprint includes the four-module quiet zone.
    The light background has a fixed 1 mm outer corner radius.

    The corner radius must fit entirely within the quiet zone,
    preserving the QR encoding and square module geometry.

    Physical dimensionalization and color assignment remain downstream.
    """
    if not payload:
        raise ValueError("QR composition requires a nonempty payload.")

    if not math.isfinite(shape_size) or shape_size <= 0:
        raise ValueError("shape_size must be positive.")

    if not math.isfinite(qr_size) or qr_size <= 0:
        raise ValueError("shape_qr_size must be positive.")

    if qr_size > shape_size:
        raise ValueError("QR footprint exceeds the Shape envelope.")

    if not math.isfinite(position):
        raise ValueError("shape_qr_position must be finite.")

    if interior is None:
        interior = QRInterior(
            vertices=(
                (-0.5, -0.5),
                (0.5, -0.5),
                (0.5, 0.5),
                (-0.5, 0.5),
            ),
        )

    registered_size = qr_size / shape_size

    footprint = _qr_footprint(
        registered_size=registered_size,
        alignment=alignment,
        position=position,
        interior=interior,
    )

    matrix = encode_qr(payload)

    registered_corner_radius = QR_CORNER_RADIUS_MM / shape_size

    module_pitch = footprint.width / len(matrix)

    if registered_corner_radius > QUIET_ZONE_MODULES * module_pitch:
        raise ValueError(
            "QR size is too small to preserve the quiet zone with a 1 mm corner radius."
        )

    output_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    components = {
        "qr-dark": output_directory / "qr-dark.svg",
        "qr-light": output_directory / "qr-light.svg",
    }

    _write_component(
        components["qr-dark"],
        matrix,
        dark=True,
        footprint=footprint,
    )

    _write_component(
        components["qr-light"],
        matrix,
        dark=False,
        footprint=footprint,
        corner_radius=registered_corner_radius,
    )

    return RegisteredQR(
        footprint=footprint,
        quiet_zone_modules=QUIET_ZONE_MODULES,
        components=components,
    )
