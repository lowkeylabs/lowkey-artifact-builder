"""
Tests for Shape registered-Artwork composition.
"""
# File: tests/model/shape/test_compose.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
from pathlib import Path

from lowkey_artifact_builder.model.models.shape.stages import compose


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
