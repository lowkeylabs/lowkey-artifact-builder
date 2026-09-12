"""
Artwork attachment-color selection.

This module owns the Artwork-specific policy for determining the semantic
physical printer color at a cardinal attachment point.

Attachment-color selection operates on Registered Artwork. The registered
Artwork envelope and all registered color layers share one common coordinate
system.

When the exact envelope attachment point is not occupied by a color layer,
selection proceeds inward along the same cardinal axis until the nearest
occupied Artwork color is found.
"""
# File: src/lowkey_artifact_builder/model/models/artwork/attachment.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from lowkey_artifact_builder.model.models.artwork.vector_manifest import (
    VectorLayer,
    VectorManifest,
)
from lowkey_artifact_builder.tools.inkscape import (
    InkscapeError,
    query_all,
)

# =========================================================
# Errors
# =========================================================


class AttachmentError(RuntimeError):
    """
    Raised when Artwork attachment-color selection cannot be completed.
    """


# =========================================================
# Geometry
# =========================================================


@dataclass(
    frozen=True,
    slots=True,
)
class Bounds:
    """
    Axis-aligned occupied bounds in Registered Artwork coordinates.
    """

    min_x: float
    min_y: float
    max_x: float
    max_y: float

    @property
    def center_x(
        self,
    ) -> float:
        """
        Return the horizontal center.
        """

        return (self.min_x + self.max_x) / 2.0

    @property
    def center_y(
        self,
    ) -> float:
        """
        Return the vertical center.
        """

        return (self.min_y + self.max_y) / 2.0


# =========================================================
# Public interface
# =========================================================


def select_attachment_color(
    artwork: VectorManifest,
    *,
    position: int,
) -> str:
    """
    Return the semantic printer color at one cardinal Artwork attachment.

    Supported positions are:

        0       top
        90      right
        180     bottom
        -90     left

    The attachment point is the intersection between the selected cardinal
    axis and the occupied Artwork envelope.

    If no color layer occupies the exact boundary point, the nearest
    occupied color encountered inward along the same cardinal axis is
    selected.
    """

    if position not in {
        0,
        90,
        180,
        -90,
    }:
        raise AttachmentError(f"Unsupported Artwork attachment position: {position}")

    try:
        envelope = _bounds(
            artwork.envelope,
        )

        layers = tuple(
            (
                layer,
                _bounds(
                    layer.path,
                ),
            )
            for layer in artwork.layers
        )

    except InkscapeError as exc:
        raise AttachmentError("Could not inspect Registered Artwork geometry.") from exc

    if not layers:
        raise AttachmentError("Registered Artwork contains no color layers.")

    candidates: list[
        tuple[
            float,
            int,
            VectorLayer,
        ]
    ] = []

    for layer, bounds in layers:
        distance = _inward_distance(
            envelope,
            bounds,
            position=position,
        )

        if distance is None:
            continue

        candidates.append(
            (
                distance,
                layer.index,
                layer,
            )
        )

    if not candidates:
        raise AttachmentError("No Artwork color occupies the selected attachment axis.")

    _, _, selected = min(
        candidates,
        key=lambda candidate: (
            candidate[0],
            candidate[1],
        ),
    )

    return selected.printer_color_name


# =========================================================
# Bounds
# =========================================================


def _bounds(
    path: Path,
) -> Bounds:
    """
    Return occupied bounds for one registered SVG product.

    Inkscape supplies geometry for the actual SVG objects rather than the
    document page or registered extent.
    """

    objects = query_all(
        path,
        millimeters=False,
    )

    if not objects:
        raise AttachmentError(f"Registered Artwork geometry contains no objects: {path}")

    min_x = min(item["x"] for item in objects.values())

    min_y = min(item["y"] for item in objects.values())

    max_x = max(item["x"] + item["width"] for item in objects.values())

    max_y = max(item["y"] + item["height"] for item in objects.values())

    return Bounds(
        min_x=min_x,
        min_y=min_y,
        max_x=max_x,
        max_y=max_y,
    )


# =========================================================
# Attachment selection
# =========================================================


def _inward_distance(
    envelope: Bounds,
    layer: Bounds,
    *,
    position: int,
) -> float | None:
    """
    Return inward distance from the selected envelope attachment boundary.

    None means the layer does not intersect the selected cardinal axis.

    Distance zero means the layer occupies the envelope boundary itself.
    Positive distance means the layer begins that far inward from the
    boundary.
    """

    if position == 0:
        if not _contains(
            layer.min_x,
            layer.max_x,
            envelope.center_x,
        ):
            return None

        if layer.max_y < envelope.min_y:
            return None

        return max(
            0.0,
            layer.min_y - envelope.min_y,
        )

    if position == 90:
        if not _contains(
            layer.min_y,
            layer.max_y,
            envelope.center_y,
        ):
            return None

        if layer.min_x > envelope.max_x:
            return None

        return max(
            0.0,
            envelope.max_x - layer.max_x,
        )

    if position == 180:
        if not _contains(
            layer.min_x,
            layer.max_x,
            envelope.center_x,
        ):
            return None

        if layer.min_y > envelope.max_y:
            return None

        return max(
            0.0,
            envelope.max_y - layer.max_y,
        )

    if position == -90:
        if not _contains(
            layer.min_y,
            layer.max_y,
            envelope.center_y,
        ):
            return None

        if layer.max_x < envelope.min_x:
            return None

        return max(
            0.0,
            layer.min_x - envelope.min_x,
        )

    raise AttachmentError(f"Unsupported Artwork attachment position: {position}")


def _contains(
    minimum: float,
    maximum: float,
    value: float,
) -> bool:
    """
    Return whether a coordinate lies within an inclusive interval.
    """

    return minimum <= value <= maximum
