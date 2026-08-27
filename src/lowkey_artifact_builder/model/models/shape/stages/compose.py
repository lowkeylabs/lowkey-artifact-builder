"""
Registered Artwork consumption for the Shape compose stage.

This module initially establishes only the registered-geometry consumer
contract. Physical Shape geometry, fitting, dimensionalization, and packaging
are introduced by later implementation slices.
"""
# File: src/lowkey_artifact_builder/model/models/shape/stages/compose.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

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
    """

    registered_extent: RegisteredExtent
    components: tuple[RegisteredArtworkComponent, ...]


# =========================================================
# Manifest loading
# =========================================================


def load_registered_artwork(
    manifest_path: Path,
) -> RegisteredArtwork:
    """
    Load registered Artwork from its declared vector manifest.

    Component membership is determined exclusively by the manifest.
    Component paths are resolved relative to the manifest location.

    This boundary does not inspect component payloads or independently
    calculate their geometry.
    """

    manifest = _load_manifest(
        manifest_path,
    )

    registered_extent = _load_registered_extent(
        manifest,
    )

    components = _load_components(
        manifest,
        manifest_path=manifest_path,
    )

    return RegisteredArtwork(
        registered_extent=registered_extent,
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
        manifest = json.load(stream)

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
