"""
Tests for Shape registered-Artwork composition.
"""
# File: tests/model/shape/test_compose.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import Mock, call

from lowkey_artifact_builder.engine import StageContext
from lowkey_artifact_builder.engine.bootstrap import build_stage_registry
from lowkey_artifact_builder.model.models.shape import stages
from lowkey_artifact_builder.model.models.shape.stages import compose

# =========================================================
# Helpers
# =========================================================


def _write_vector_manifest(
    path: Path,
) -> None:
    """
    Write a representative registered Artwork vector manifest.
    """

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        json.dumps(
            {
                "registered_extent": {
                    "width": 16.0,
                    "height": 12.0,
                },
                "products": [
                    {
                        "index": 1,
                        "path": "white.svg",
                        "name": "white",
                        "color": {
                            "r": 255,
                            "g": 255,
                            "b": 255,
                            "a": 255,
                        },
                    },
                    {
                        "index": 2,
                        "path": "black.svg",
                        "name": "black",
                        "color": {
                            "r": 0,
                            "g": 0,
                            "b": 0,
                            "a": 255,
                        },
                    },
                ],
            }
        ),
        encoding="utf-8",
    )


def _write_registered_structure(
    path: Path,
) -> None:
    """
    Write representative registered Shape structure.
    """

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        (
            '<svg xmlns="http://www.w3.org/2000/svg" '
            'viewBox="-0.5 -0.5 1.0 1.0">'
            '<circle cx="0.0" cy="0.0" r="0.5" />'
            "</svg>"
        ),
        encoding="utf-8",
    )


# =========================================================
# Registered Artwork manifest
# =========================================================


def test_load_registered_artwork_uses_declared_manifest_membership(
    tmp_path: Path,
) -> None:
    """
    Registered Artwork membership comes from the manifest.

    Files that happen to exist beside the manifest are not implicitly
    incorporated into the registered component set.
    """

    manifest = tmp_path / "vector" / "products.json"

    _write_vector_manifest(
        manifest,
    )

    unexpected = manifest.parent / "unexpected.svg"

    unexpected.write_text(
        "<svg/>",
        encoding="utf-8",
    )

    artwork = compose.load_registered_artwork(
        manifest,
    )

    assert tuple(component.path.name for component in artwork.components) == (
        "white.svg",
        "black.svg",
    )


def test_load_registered_artwork_resolves_components_beside_manifest(
    tmp_path: Path,
) -> None:
    """
    Manifest component paths are resolved relative to the manifest itself.

    Shape consumes the manifest contract rather than constructing Artwork
    stage-directory paths.
    """

    manifest = tmp_path / "arbitrary-location" / "products.json"

    _write_vector_manifest(
        manifest,
    )

    artwork = compose.load_registered_artwork(
        manifest,
    )

    assert tuple(component.path for component in artwork.components) == (
        manifest.parent / "white.svg",
        manifest.parent / "black.svg",
    )


def test_load_registered_artwork_preserves_component_metadata(
    tmp_path: Path,
) -> None:
    """
    Shape retains semantic component identity supplied by Artwork.

    The registered component payload remains opaque; Shape needs membership
    and semantic metadata without independently interpreting SVG geometry.
    """

    manifest = tmp_path / "vector" / "products.json"

    _write_vector_manifest(
        manifest,
    )

    artwork = compose.load_registered_artwork(
        manifest,
    )

    first = artwork.components[0]
    second = artwork.components[1]

    assert first.index == 1
    assert first.name == "white"
    assert first.color == {
        "r": 255,
        "g": 255,
        "b": 255,
        "a": 255,
    }

    assert second.index == 2
    assert second.name == "black"
    assert second.color == {
        "r": 0,
        "g": 0,
        "b": 0,
        "a": 255,
    }


def test_load_registered_artwork_reads_common_registered_extent(
    tmp_path: Path,
) -> None:
    """
    Shape obtains one common registered extent from the Artwork manifest.

    The consumer does not calculate independent bounds for individual
    registered components.
    """

    manifest = tmp_path / "vector" / "products.json"

    _write_vector_manifest(
        manifest,
    )

    artwork = compose.load_registered_artwork(
        manifest,
    )

    assert artwork.registered_extent.width == 16.0
    assert artwork.registered_extent.height == 12.0


# =========================================================
# Registered Artwork placement
# =========================================================


def test_registered_artwork_transform_is_derived_from_common_extent() -> None:
    """
    Artwork fitting derives one transform from the common registered extent.

    The transform is based on the registered collection as a whole rather
    than on bounds calculated independently for individual components.
    """

    artwork = compose.RegisteredArtwork(
        registered_extent=compose.RegisteredExtent(
            width=16.0,
            height=12.0,
        ),
        components=(),
    )

    transform = compose.fit_registered_artwork(
        artwork,
        available_width=80.0,
        available_height=80.0,
    )

    assert transform.scale == 5.0
    assert transform.width == 80.0
    assert transform.height == 60.0


def test_registered_artwork_fit_preserves_aspect_ratio() -> None:
    """
    Registered Artwork uses uniform contain-style scaling.

    The limiting interior dimension determines one X/Y scale so Artwork is
    completely contained without stretching.
    """

    artwork = compose.RegisteredArtwork(
        registered_extent=compose.RegisteredExtent(
            width=16.0,
            height=12.0,
        ),
        components=(),
    )

    transform = compose.fit_registered_artwork(
        artwork,
        available_width=64.0,
        available_height=36.0,
    )

    assert transform.scale == 3.0
    assert transform.width == 48.0
    assert transform.height == 36.0


def test_registered_artwork_fit_centers_common_extent() -> None:
    """
    Registered Artwork is centered within the available region.

    Translation is calculated from the transformed common registered extent,
    not independently for individual components.
    """

    artwork = compose.RegisteredArtwork(
        registered_extent=compose.RegisteredExtent(
            width=16.0,
            height=12.0,
        ),
        components=(),
    )

    transform = compose.fit_registered_artwork(
        artwork,
        available_width=80.0,
        available_height=80.0,
    )

    assert transform.translate_x == 0.0
    assert transform.translate_y == 10.0


def test_registered_artwork_components_share_one_transform(
    tmp_path: Path,
) -> None:
    """
    Every registered component receives the same Artwork transformation.

    Shape does not independently fit component payloads because doing so could
    destroy registration between the component layers.
    """

    artwork = compose.RegisteredArtwork(
        registered_extent=compose.RegisteredExtent(
            width=16.0,
            height=12.0,
        ),
        components=(
            compose.RegisteredArtworkComponent(
                index=1,
                path=tmp_path / "white.svg",
                name="white",
                color={
                    "r": 255,
                    "g": 255,
                    "b": 255,
                    "a": 255,
                },
            ),
            compose.RegisteredArtworkComponent(
                index=2,
                path=tmp_path / "black.svg",
                name="black",
                color={
                    "r": 0,
                    "g": 0,
                    "b": 0,
                    "a": 255,
                },
            ),
        ),
    )

    placement = compose.place_registered_artwork(
        artwork,
        available_width=80.0,
        available_height=80.0,
    )

    assert tuple(component.transform for component in placement.components) == (
        placement.transform,
        placement.transform,
    )

    assert tuple(component.component for component in placement.components) == artwork.components


# =========================================================
# Compose stage execution
# =========================================================


def test_compose_stage_materializes_registered_composition(
    tmp_path: Path,
) -> None:
    """
    Shape composition materializes its declared registered product.

    The stage obtains registered Shape structure and its output location
    through StageContext rather than constructing artifact filesystem paths.
    """

    structure_input = tmp_path / "structure.svg"
    output = tmp_path / "composition.svg"

    _write_registered_structure(
        structure_input,
    )

    context = Mock(
        spec=StageContext,
    )
    context.input.return_value = structure_input
    context.output.return_value = output

    compose.execute(
        context,
    )

    context.input.assert_called_once_with(
        "structure.structure",
    )
    context.output.assert_called_once_with(
        "composition",
    )

    assert output.is_file()


def test_compose_stage_preserves_registered_shape_geometry(
    tmp_path: Path,
) -> None:
    """
    Shape composition preserves structural geometry in registered Shape space.

    Composition does not introduce physical X/Y dimensions before the
    downstream dimensionalization boundary.
    """

    structure_input = tmp_path / "structure.svg"
    output = tmp_path / "composition.svg"

    _write_registered_structure(
        structure_input,
    )

    context = Mock(
        spec=StageContext,
    )
    context.input.return_value = structure_input
    context.output.return_value = output

    compose.execute(
        context,
    )

    root = ET.parse(
        output,
    ).getroot()

    assert root.get("viewBox") == "-0.5 -0.5 1.0 1.0"
    assert root.get("width") is None
    assert root.get("height") is None

    circle = root.find(
        "{http://www.w3.org/2000/svg}circle",
    )

    assert circle is not None
    assert circle.get("cx") == "0.0"
    assert circle.get("cy") == "0.0"
    assert circle.get("r") == "0.5"


def test_compose_stage_does_not_resolve_physical_parameters(
    tmp_path: Path,
) -> None:
    """
    Registered composition does not perform physical dimensionalization.

    Physical Shape dimensions belong to the downstream extrusion boundary.
    """

    structure_input = tmp_path / "structure.svg"
    output = tmp_path / "composition.svg"

    _write_registered_structure(
        structure_input,
    )

    resolver = Mock()

    context = Mock(
        spec=StageContext,
    )
    context.resolver = resolver
    context.input.return_value = structure_input
    context.output.return_value = output

    compose.execute(
        context,
    )

    assert resolver.call_args_list == []


# =========================================================
# Compose stage registration
# =========================================================


def test_shape_registers_compose_stage_implementation() -> None:
    """
    Shape contributes its compose implementation through its stage package.

    Registration uses logical model and stage identities rather than numeric
    stage IDs or engine-specific orchestration.
    """

    registry = Mock()

    stages.register_stage_implementations(
        registry,
    )

    assert (
        call(
            "shape",
            "compose",
            compose.execute,
        )
        in registry.register.call_args_list
    )


def test_engine_bootstrap_discovers_shape_compose_implementation() -> None:
    """
    Normal engine bootstrap discovers the executable Shape compose stage.

    Shape participates in generic model stage discovery without requiring the
    engine to know about the Shape model explicitly.
    """

    registry = build_stage_registry()

    implementation = registry.get(
        "shape",
        "compose",
    )

    assert implementation is compose.execute
