"""
Registered Artwork vector product specifications.

These structures describe the reusable Registered Artwork vector
representation consumed by Artwork operations.

They contain no standalone physical dimensionalization or extrusion policy.
"""
# File: src/lowkey_artifact_builder/model/models/artwork/vector_manifest.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(
    frozen=True,
    slots=True,
)
class VectorLayer:
    """
    One registered vector color layer.

    Artifact color identity and RGB describe the color discovered from
    the Artwork. Printer color identity and RGB describe the physical
    assignment established during rasterization.
    """

    index: int

    path: Path

    artifact_color_index: int

    artifact_color: tuple[
        int,
        int,
        int,
    ]

    printer_color_name: str

    printer_color: tuple[
        int,
        int,
        int,
    ]

    distance: float


@dataclass(
    frozen=True,
    slots=True,
)
class VectorManifest:
    """
    Registered vector geometry consumed by Artwork operations.

    registered_extent describes the common square coordinate system
    shared by the envelope and every vector layer.

    envelope identifies the registered occupied Artwork envelope.
    """

    registered_extent: int

    envelope: Path

    layers: tuple[
        VectorLayer,
        ...,
    ]


__all__ = [
    "VectorLayer",
    "VectorManifest",
]
