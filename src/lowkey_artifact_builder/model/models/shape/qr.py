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

QUIET_ZONE_MODULES = 4


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


def _write_component(
    path: Path,
    matrix: list[list[bool]],
    *,
    dark: bool,
    footprint: QRFootprint,
) -> None:
    """
    Write one semantic QR region as registered rectangles.

    Light rectangles include the complete quiet zone. Dark and light
    components partition the footprint without overlap or gaps.
    """
    count = len(matrix)
    pitch = footprint.width / count

    root = ET.Element(
        f"{{{SVG_NS}}}svg",
        {
            "viewBox": "-0.5 -0.5 1 1",
        },
    )

    for row_index, row in enumerate(matrix):
        for column_index, module in enumerate(row):
            if module is not dark:
                continue

            ET.SubElement(
                root,
                f"{{{SVG_NS}}}rect",
                {
                    "x": str(footprint.x + column_index * pitch),
                    "y": str(footprint.y + row_index * pitch),
                    "width": str(pitch),
                    "height": str(pitch),
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

    The complete footprint includes the quiet zone. Placement uses
    the available registered Shape interior and preserves the
    axis-aligned QR module grid.

    Shape Compose supplies its authoritative interior explicitly.
    The default square interior preserves compatibility with existing
    direct callers of this function.

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
    )

    return RegisteredQR(
        footprint=footprint,
        quiet_zone_modules=QUIET_ZONE_MODULES,
        components=components,
    )
