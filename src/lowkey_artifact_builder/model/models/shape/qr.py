"""
Registered QR Code geometry for the Shape model.

QR encoding and SVG generation are nonphysical. The complete footprint,
including the quiet zone, is partitioned into complementary dark and
light components.
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
    x: float
    y: float
    width: float
    height: float


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
    Write one semantic QR region as a collection of registered rectangles.

    Light rectangles include the entire quiet zone. Dark and light
    components partition the complete square without overlap.
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


def compose_qr(
    output_directory: Path,
    *,
    payload: str,
    qr_size: float,
    shape_size: float,
    alignment: str,
    position: float,
) -> RegisteredQR:
    """
    Generate registered QR components.

    This first composition slice supports centered placement.
    Other alignment modes require registered-interior containment
    geometry and are deliberately not approximated here.
    """
    if not payload:
        raise ValueError("QR composition requires a nonempty payload.")

    if not math.isfinite(shape_size) or shape_size <= 0:
        raise ValueError("shape_size must be positive.")

    if not math.isfinite(qr_size) or qr_size <= 0:
        raise ValueError("shape_qr_size must be positive.")

    if qr_size > shape_size:
        raise ValueError("QR footprint exceeds the Shape envelope.")

    if alignment != "centered":
        raise ValueError("QR inner-aligned and outer-aligned placement is not yet implemented.")

    if not math.isfinite(position):
        raise ValueError("shape_qr_position must be finite.")

    matrix = encode_qr(payload)
    registered_size = qr_size / shape_size

    footprint = QRFootprint(
        x=-registered_size / 2,
        y=-registered_size / 2,
        width=registered_size,
        height=registered_size,
    )

    output_directory.mkdir(parents=True, exist_ok=True)

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
