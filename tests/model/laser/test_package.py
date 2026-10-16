"""
Tests for Laser SVG packaging.

Laser consumes persistent registered Shape Compose Products and produces
a single physically dimensioned SVG without Shape extrusion or packaging.
"""
# File: tests/model/laser/test_package.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
import math
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import Mock

from lowkey_artifact_builder.engine import StageContext
from lowkey_artifact_builder.model.models.laser.stages import package

SVG_NS = "http://www.w3.org/2000/svg"
SVG = f"{{{SVG_NS}}}"


def _write_shape_composition(directory: Path) -> Path:
    """
    Create representative persistent Shape Compose Products.

    The structure and Artwork have different coordinate systems.
    Shape's persisted Artwork transform is authoritative.
    """

    directory.mkdir(parents=True, exist_ok=True)

    (directory / "composition.svg").write_text(
        f"""
        <svg xmlns="{SVG_NS}" viewBox="-0.5 -0.5 1 1">
          <circle
              id="shape-boundary"
              cx="0" cy="0" r="0.5"
              fill="none"/>
          <circle
              id="ridge-inner-boundary"
              cx="0" cy="0" r="0.45"
              fill="none"/>
        </svg>
        """,
        encoding="utf-8",
    )

    (directory / "light.svg").write_text(
        f"""
        <svg xmlns="{SVG_NS}" viewBox="0 0 16 16">
          <rect x="2" y="3" width="6" height="10"/>
        </svg>
        """,
        encoding="utf-8",
    )

    (directory / "dark.svg").write_text(
        f"""
        <svg xmlns="{SVG_NS}" viewBox="0 0 16 16">
          <rect x="8" y="3" width="6" height="10"/>
        </svg>
        """,
        encoding="utf-8",
    )

    manifest = directory / "products.json"
    manifest.write_text(
        json.dumps(
            {
                "composition": "composition.svg",
                "border_labels": {
                    "top": None,
                    "bottom": None,
                },
                "artwork": {
                    "registered_extent": {
                        "width": 16.0,
                        "height": 16.0,
                    },
                    "transform": {
                        "scale": 0.05,
                        "translate_x": -0.4,
                        "translate_y": -0.4,
                    },
                    "components": [
                        {
                            "index": 1,
                            "path": "light.svg",
                            "artifact_color": {
                                "index": 1,
                                "rgb": {
                                    "red": 240,
                                    "green": 240,
                                    "blue": 240,
                                },
                            },
                        },
                        {
                            "index": 2,
                            "path": "dark.svg",
                            "artifact_color": {
                                "index": 2,
                                "rgb": {
                                    "red": 20,
                                    "green": 20,
                                    "blue": 20,
                                },
                            },
                        },
                    ],
                },
                "artwork_fill": None,
            }
        ),
        encoding="utf-8",
    )

    return manifest


def _svg_elements(root: ET.Element, name: str) -> list[ET.Element]:
    return list(root.iter(f"{SVG}{name}"))


def _svg_id(root: ET.Element, identifier: str) -> ET.Element | None:
    return next(
        (element for element in root.iter() if element.get("id") == identifier),
        None,
    )


def _millimeters(value: str) -> float:
    assert value.endswith("mm")
    return float(value.removesuffix("mm"))


def test_laser_package_combines_registered_shape_and_artwork(
    tmp_path: Path,
) -> None:
    """
    Laser packages Shape's existing registered composition.

    The output preserves physical size, structural outlines, distinct
    Artwork identities, and the common Artwork placement transform.
    The structural Base must not become an implicit filled region.
    """

    composition_manifest = _write_shape_composition(
        tmp_path / "shape" / "compose",
    )

    artifact = tmp_path / "laser" / "package" / "artifact.svg"
    artifact.parent.mkdir(parents=True, exist_ok=True)

    context = Mock(spec=StageContext)

    context.input.side_effect = {
        "shape.compose.manifest": composition_manifest,
    }.__getitem__

    context.output.side_effect = {
        "artifact": artifact,
    }.__getitem__

    context.resolver.side_effect = {
        "shape_size": 100.0,
    }.__getitem__

    package.execute(context)

    assert artifact.is_file()

    root = ET.parse(artifact).getroot()

    assert root.tag == f"{SVG}svg"

    assert math.isclose(
        _millimeters(root.attrib["width"]),
        100.0,
    )
    assert math.isclose(
        _millimeters(root.attrib["height"]),
        100.0,
    )

    view_box = tuple(float(value) for value in root.attrib["viewBox"].replace(",", " ").split())
    assert len(view_box) == 4
    assert view_box[2] > 0
    assert view_box[3] > 0

    # Structural geometry remains available as outlines.
    boundary = _svg_id(root, "shape-boundary")
    assert boundary is not None
    assert boundary.tag == f"{SVG}circle"
    assert boundary.get("fill") == "none"

    ridge = _svg_id(root, "ridge-inner-boundary")
    assert ridge is not None
    assert ridge.tag == f"{SVG}circle"

    # Each Artwork color region remains independently identifiable.
    artwork_1 = _svg_id(root, "artwork-1")
    artwork_2 = _svg_id(root, "artwork-2")

    assert artwork_1 is not None
    assert artwork_2 is not None
    assert artwork_1 is not artwork_2

    # Both regions retain their original geometry and share the
    # authoritative Shape Compose placement, rather than being
    # independently fitted into the laser document.
    rectangles = _svg_elements(root, "rect")
    assert len(rectangles) == 2

    assert {
        (
            float(rect.attrib["x"]),
            float(rect.attrib["y"]),
            float(rect.attrib["width"]),
            float(rect.attrib["height"]),
        )
        for rect in rectangles
    } == {
        (2.0, 3.0, 6.0, 10.0),
        (8.0, 3.0, 6.0, 10.0),
    }

    # The result is a self-contained SVG with no linked image assets.
    assert not _svg_elements(root, "image")

    for element in root.iter():
        for attribute, value in element.attrib.items():
            assert not attribute.endswith("}href") or not value.startswith(
                ("file:", "http:", "https:")
            )
