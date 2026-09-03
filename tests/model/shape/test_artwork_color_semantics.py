"""
Tests for Artwork color semantics consumed by Shape.
"""
# File: tests/model/shape/test_artwork_color_semantics.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lowkey_artifact_builder.model.models.shape.stages import compose, extrude

# =========================================================
# Helpers
# =========================================================


def _rgb(
    red: int,
    green: int,
    blue: int,
) -> dict[str, int]:
    """
    Return manifest RGB metadata.
    """

    return {
        "red": red,
        "green": green,
        "blue": blue,
    }


def _write_registered_artwork_manifest(
    path: Path,
) -> None:
    """
    Write representative registered Artwork using the current vector contract.

    Artifact color identity and measured RGB remain distinct from the physical
    printer assignment selected during Artwork rasterization.
    """

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    envelope = path.parent / "envelope.svg"

    envelope.write_text(
        (
            '<svg xmlns="http://www.w3.org/2000/svg" '
            'viewBox="0 0 16 16">'
            '<rect x="2" y="3" width="12" height="10"/>'
            "</svg>"
        ),
        encoding="utf-8",
    )

    first = path.parent / "color-1.svg"

    first.write_text(
        (
            '<svg xmlns="http://www.w3.org/2000/svg" '
            'viewBox="0 0 16 16">'
            '<rect x="2" y="3" width="6" height="10"/>'
            "</svg>"
        ),
        encoding="utf-8",
    )

    second = path.parent / "color-2.svg"

    second.write_text(
        (
            '<svg xmlns="http://www.w3.org/2000/svg" '
            'viewBox="0 0 16 16">'
            '<rect x="8" y="3" width="6" height="10"/>'
            "</svg>"
        ),
        encoding="utf-8",
    )

    path.write_text(
        json.dumps(
            {
                "registered_extent": 16,
                "envelope": "envelope.svg",
                "products": [
                    {
                        "index": 1,
                        "path": "color-1.svg",
                        "artifact_color": {
                            "index": 7,
                            "rgb": _rgb(
                                17,
                                43,
                                91,
                            ),
                        },
                        "printer_color": {
                            "name": "physical-blue",
                            "rgb": _rgb(
                                20,
                                40,
                                90,
                            ),
                        },
                        "distance": 1.25,
                    },
                    {
                        "index": 2,
                        "path": "color-2.svg",
                        "artifact_color": {
                            "index": 11,
                            "rgb": _rgb(
                                203,
                                61,
                                47,
                            ),
                        },
                        "printer_color": {
                            "name": "physical-red",
                            "rgb": _rgb(
                                200,
                                60,
                                50,
                            ),
                        },
                        "distance": 2.5,
                    },
                ],
            }
        ),
        encoding="utf-8",
    )


# =========================================================
# Registered Artwork consumption
# =========================================================


def test_shape_consumes_artifact_and_printer_color_semantics(
    tmp_path: Path,
) -> None:
    """
    Shape consumes both semantic color layers published by Artwork.

    Artifact color identity and measured RGB describe the persistent Artwork
    region. Printer color identity and RGB describe its selected physical
    realization. Shape must not collapse those distinct semantics.
    """

    manifest = tmp_path / "vector" / "products.json"

    _write_registered_artwork_manifest(
        manifest,
    )

    artwork = compose.load_registered_artwork(
        manifest,
    )

    first = artwork.components[0]
    second = artwork.components[1]

    assert first.index == 1
    assert first.artifact_color_index == 7
    assert first.artifact_color == _rgb(
        17,
        43,
        91,
    )
    assert first.printer_color_name == "physical-blue"
    assert first.printer_color == _rgb(
        20,
        40,
        90,
    )
    assert first.distance == pytest.approx(
        1.25,
    )

    assert second.index == 2
    assert second.artifact_color_index == 11
    assert second.artifact_color == _rgb(
        203,
        61,
        47,
    )
    assert second.printer_color_name == "physical-red"
    assert second.printer_color == _rgb(
        200,
        60,
        50,
    )
    assert second.distance == pytest.approx(
        2.5,
    )


# =========================================================
# Shape composition persistence
# =========================================================


def test_shape_composition_preserves_artifact_and_printer_color_semantics(
    tmp_path: Path,
) -> None:
    """
    Shape composition preserves registered Artwork color semantics unchanged.

    Incorporation changes Artwork placement but does not reinterpret Artifact
    RGB or its already-selected printer assignment.
    """

    vector_manifest = tmp_path / "vector" / "products.json"

    _write_registered_artwork_manifest(
        vector_manifest,
    )

    artwork = compose.load_registered_artwork(
        vector_manifest,
    )

    composition = tmp_path / "compose" / "composition.svg"
    composition_manifest = tmp_path / "compose" / "products.json"

    composition.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    composition.write_text(
        (
            '<svg xmlns="http://www.w3.org/2000/svg" '
            'viewBox="-0.5 -0.5 1.0 1.0">'
            '<circle id="shape-boundary" '
            'cx="0" cy="0" r="0.5"/>'
            "</svg>"
        ),
        encoding="utf-8",
    )

    transform = compose.RegisteredArtworkTransform(
        scale=0.01,
        width=0.12,
        height=0.10,
        translate_x=-0.08,
        translate_y=-0.08,
    )

    compose._write_composition_manifest(
        composition_manifest,
        composition=composition,
        artwork=artwork,
        artwork_transform=transform,
    )

    data = json.loads(
        composition_manifest.read_text(
            encoding="utf-8",
        )
    )

    assert data["artwork"]["components"] == [
        {
            "index": 1,
            "path": "color-1.svg",
            "artifact_color": {
                "index": 7,
                "rgb": _rgb(
                    17,
                    43,
                    91,
                ),
            },
            "printer_color": {
                "name": "physical-blue",
                "rgb": _rgb(
                    20,
                    40,
                    90,
                ),
            },
            "distance": 1.25,
        },
        {
            "index": 2,
            "path": "color-2.svg",
            "artifact_color": {
                "index": 11,
                "rgb": _rgb(
                    203,
                    61,
                    47,
                ),
            },
            "printer_color": {
                "name": "physical-red",
                "rgb": _rgb(
                    200,
                    60,
                    50,
                ),
            },
            "distance": 2.5,
        },
    ]


# =========================================================
# Shape physical dimensionalization
# =========================================================


def test_shape_extrusion_uses_registered_artwork_printer_assignment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Shape physical extrusion uses Artwork's selected printer assignment.

    Artifact RGB describes the Artwork itself and may differ from the physical
    printer RGB. Dimensionalization must therefore carry printer identity and
    RGB into the physical component manifest rather than substituting Artifact
    RGB.
    """

    source = tmp_path / "compose" / "color-1.svg"

    source.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    source.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg"/>',
        encoding="utf-8",
    )

    artwork = {
        "registered_extent": {
            "width": 16.0,
            "height": 16.0,
        },
        "transform": {
            "scale": 0.01,
            "translate_x": -0.08,
            "translate_y": -0.08,
        },
        "components": [
            {
                "index": 1,
                "path": source.name,
                "artifact_color": {
                    "index": 7,
                    "rgb": _rgb(
                        17,
                        43,
                        91,
                    ),
                },
                "printer_color": {
                    "name": "physical-blue",
                    "rgb": _rgb(
                        20,
                        40,
                        90,
                    ),
                },
                "distance": 1.25,
            },
        ],
    }

    def fake_render_stl_source(
        scad_source: str,
        output: Path,
    ) -> None:
        del scad_source

        output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        output.write_text(
            "solid test\nendsolid test\n",
            encoding="utf-8",
        )

    monkeypatch.setattr(
        extrude,
        "render_stl_source",
        fake_render_stl_source,
    )

    rendered = extrude._render_artwork_components(
        artwork,
        source.parent,
        tmp_path / "extrude",
        shape_size=100.0,
        shape_base_raise=2.0,
        shape_artwork_raise=1.0,
    )

    assert rendered == (
        (
            "artwork-1",
            "artwork-1.stl",
            {
                "name": "physical-blue",
                "rgb": [
                    20,
                    40,
                    90,
                ],
            },
        ),
    )

    physical_color = rendered[0][2]

    assert physical_color["rgb"] != [
        17,
        43,
        91,
    ]
