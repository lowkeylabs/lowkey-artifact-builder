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
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from lowkey_artifact_builder.engine import StageContext

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


def execute(
    context: StageContext,
) -> None:
    """
    Execute registered Shape composition.

    Composition consumes the registered structural Shape product through
    StageContext and materializes the declared registered composition product
    through StageContext.

    This initial executable composition boundary preserves the registered
    structural geometry unchanged. It does not introduce physical dimensions.

    Registered Artwork incorporation is introduced separately once optional
    Artwork dependency semantics are established.
    """

    structure_input = context.input(
        "structure.structure",
    )

    output = context.output(
        "composition",
    )

    shutil.copyfile(
        structure_input,
        output,
    )


# =========================================================
# Registered Artwork placement
# =========================================================


def fit_registered_artwork(
    artwork: RegisteredArtwork,
    *,
    available_width: float,
    available_height: float,
) -> RegisteredArtworkTransform:
    """
    Fit registered Artwork uniformly within an available region.

    One scale is derived from the common registered extent. The transformed
    extent is centered within the available region.

    Individual component payloads are not inspected or independently fitted.
    """

    registered_width = artwork.registered_extent.width
    registered_height = artwork.registered_extent.height

    scale = min(
        available_width / registered_width,
        available_height / registered_height,
    )

    width = registered_width * scale
    height = registered_height * scale

    translate_x = (available_width - width) / 2.0
    translate_y = (available_height - height) / 2.0

    return RegisteredArtworkTransform(
        scale=scale,
        width=width,
        height=height,
        translate_x=translate_x,
        translate_y=translate_y,
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
