"""
Tests for Coin packaging.

Coin Package consumes the persistent physical Coin Product and packages its
already-composed components without changing physical geometry, semantic
identity, resolved physical color, or independent component membership.
"""
# File: tests/model/coin/test_package.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import Mock

from lowkey_artifact_builder.colors import PaletteColor
from lowkey_artifact_builder.engine import StageContext
from lowkey_artifact_builder.formats.threemf import (
    Mesh,
    read,
)
from lowkey_artifact_builder.model.models.coin.stages import package


def _write_component_stl(
    path: Path,
    *,
    x_offset: float,
) -> Mesh:
    """
    Write one representative physical Coin component.

    Distinct X offsets make preservation of each component's physical
    geometry observable after packaging.
    """

    mesh = Mesh(
        vertices=(
            (x_offset + 0.0, 0.0, 0.0),
            (x_offset + 1.0, 0.0, 0.0),
            (x_offset + 0.0, 1.0, 1.0),
        ),
        triangles=((0, 1, 2),),
    )

    path.write_text(
        "\n".join(
            (
                "solid component",
                "  facet normal 0 0 0",
                "    outer loop",
                (f"      vertex {mesh.vertices[0][0]} {mesh.vertices[0][1]} {mesh.vertices[0][2]}"),
                (f"      vertex {mesh.vertices[1][0]} {mesh.vertices[1][1]} {mesh.vertices[1][2]}"),
                (f"      vertex {mesh.vertices[2][0]} {mesh.vertices[2][1]} {mesh.vertices[2][2]}"),
                "    endloop",
                "  endfacet",
                "endsolid component",
                "",
            )
        ),
        encoding="ascii",
    )

    return mesh


def test_coin_package_preserves_physical_components_identity_and_colors(
    tmp_path: Path,
) -> None:
    """
    Coin Package faithfully packages the persistent physical Coin Product.

    Face identity, source semantic identity, resolved physical color, physical
    geometry, and independent component membership survive packaging.
    Components sharing a physical color remain independently represented.
    """

    physical = tmp_path / "products.json"
    artifact = tmp_path / "artifact.3mf"

    face_a_base = tmp_path / "face-a-base.stl"
    face_a_artwork = tmp_path / "face-a-artwork.stl"
    face_b_base = tmp_path / "face-b-base.stl"
    face_b_artwork = tmp_path / "face-b-artwork.stl"

    expected_meshes = {
        "faceA-base": _write_component_stl(
            face_a_base,
            x_offset=0.0,
        ),
        "faceA-artwork-1": _write_component_stl(
            face_a_artwork,
            x_offset=10.0,
        ),
        "faceB-base": _write_component_stl(
            face_b_base,
            x_offset=20.0,
        ),
        "faceB-artwork-1": _write_component_stl(
            face_b_artwork,
            x_offset=30.0,
        ),
    }

    physical.write_text(
        json.dumps(
            {
                "components": [
                    {
                        "name": "faceA-base",
                        "path": face_a_base.name,
                        "color": {
                            "name": "white",
                            "rgb": [255, 255, 255],
                        },
                    },
                    {
                        "name": "faceA-artwork-1",
                        "path": face_a_artwork.name,
                        "color": {
                            "name": "red",
                            "rgb": [255, 0, 0],
                        },
                    },
                    {
                        "name": "faceB-base",
                        "path": face_b_base.name,
                        "color": {
                            "name": "white",
                            "rgb": [255, 255, 255],
                        },
                    },
                    {
                        "name": "faceB-artwork-1",
                        "path": face_b_artwork.name,
                        "color": {
                            "name": "blue",
                            "rgb": [0, 0, 255],
                        },
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    context = Mock(
        spec=StageContext,
    )

    context.input.side_effect = {
        "compose.physical": physical,
    }.__getitem__

    context.output.side_effect = {
        "artifact": artifact,
    }.__getitem__

    package.execute(
        context,
    )

    assert artifact.is_file()

    components = read(
        artifact,
    )

    assert len(components) == 4

    packaged = {component.name: component for component in components}

    assert set(packaged) == {
        "faceA-base - white",
        "faceA-artwork-1 - red",
        "faceB-base - white",
        "faceB-artwork-1 - blue",
    }

    expected_colors = {
        "faceA-base - white": PaletteColor(
            name="white",
            rgb=(255, 255, 255),
        ),
        "faceA-artwork-1 - red": PaletteColor(
            name="red",
            rgb=(255, 0, 0),
        ),
        "faceB-base - white": PaletteColor(
            name="white",
            rgb=(255, 255, 255),
        ),
        "faceB-artwork-1 - blue": PaletteColor(
            name="blue",
            rgb=(0, 0, 255),
        ),
    }

    assert {name: component.color for name, component in packaged.items()} == expected_colors

    expected_packaged_meshes = {
        "faceA-base - white": expected_meshes["faceA-base"],
        "faceA-artwork-1 - red": expected_meshes["faceA-artwork-1"],
        "faceB-base - white": expected_meshes["faceB-base"],
        "faceB-artwork-1 - blue": expected_meshes["faceB-artwork-1"],
    }

    assert {
        name: component.mesh for name, component in packaged.items()
    } == expected_packaged_meshes
