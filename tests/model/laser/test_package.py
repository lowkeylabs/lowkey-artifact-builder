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

import pytest

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


def test_laser_package_preserves_effective_artwork_registration(
    tmp_path: Path,
) -> None:
    """
    The exported Artwork must occupy the physical positions implied
    by Shape Compose's persisted registration transform.

    This test checks effective placement, not SVG serialization.
    """

    manifest_path = _write_shape_composition(
        tmp_path / "shape" / "compose",
    )

    output_path = tmp_path / "laser" / "package" / "artifact.svg"

    context = Mock(spec=StageContext)
    context.input.side_effect = {
        "shape.compose.manifest": manifest_path,
    }.__getitem__
    context.output.side_effect = {
        "artifact": output_path,
    }.__getitem__
    context.resolver.side_effect = {
        "shape_size": 100.0,
    }.__getitem__

    package.execute(context)

    root = ET.parse(output_path).getroot()

    # The registered source Artwork transform is:
    #
    #   registered_x = -0.4 + 0.05 * source_x
    #   registered_y = -0.4 + 0.05 * source_y
    #
    # The physical document maps registered [-0.5, 0.5]
    # into a 100 mm square.
    #
    # Component 1: x=2..8, y=3..13
    #   physical x=20..50 mm
    #   physical y=25..75 mm
    #
    # Component 2: x=8..14, y=3..13
    #   physical x=50..80 mm
    #   physical y=25..75 mm

    expected = {
        "artwork-1": (20.0, 25.0, 30.0, 50.0),
        "artwork-2": (50.0, 25.0, 30.0, 50.0),
    }

    def affine(transform: str) -> tuple[float, float, float, float]:
        """
        Return the scale and translation of the supported SVG
        translate/scale transform sequence.

        The resulting mapping is:
            x' = sx * x + tx
            y' = sy * y + ty
        """
        import re

        sx = sy = 1.0
        tx = ty = 0.0

        operations = re.findall(
            r"(translate|scale)\s*\(([^)]*)\)",
            transform,
        )

        for operation, arguments in operations:
            values = [float(value) for value in re.split(r"[\s,]+", arguments.strip()) if value]

            if operation == "translate":
                dx = values[0]
                dy = values[1] if len(values) > 1 else 0.0
                tx += sx * dx
                ty += sy * dy
            else:
                factor_x = values[0]
                factor_y = values[1] if len(values) > 1 else factor_x
                sx *= factor_x
                sy *= factor_y

        return sx, sy, tx, ty

    def visit(
        element: ET.Element,
        *,
        sx: float = 1.0,
        sy: float = 1.0,
        tx: float = 0.0,
        ty: float = 0.0,
    ) -> list[tuple[str, tuple[float, float, float, float]]]:
        local_sx, local_sy, local_tx, local_ty = affine(
            element.get("transform", ""),
        )

        next_sx = sx * local_sx
        next_sy = sy * local_sy
        next_tx = tx + sx * local_tx
        next_ty = ty + sy * local_ty

        found = []

        if element.tag == f"{SVG}rect":
            x = float(element.attrib["x"])
            y = float(element.attrib["y"])
            width = float(element.attrib["width"])
            height = float(element.attrib["height"])

            found.append(
                (
                    element.get("id", ""),
                    (
                        next_sx * x + next_tx,
                        next_sy * y + next_ty,
                        next_sx * width,
                        next_sy * height,
                    ),
                )
            )

        for child in element:
            found.extend(
                visit(
                    child,
                    sx=next_sx,
                    sy=next_sy,
                    tx=next_tx,
                    ty=next_ty,
                )
            )

        return found

    # Associate each rectangle with its semantic Artwork component.
    registered = {}

    for name in expected:
        component = _svg_id(root, name)
        assert component is not None

        rectangles = visit(component)
        assert len(rectangles) == 1

        # Include the transforms of the component's ancestors.
        parent_map = {child: parent for parent in root.iter() for child in parent}

        ancestors = []
        current = parent_map.get(component)

        while current is not None:
            ancestors.append(current)
            current = parent_map.get(current)

        ancestors.reverse()

        sx = sy = 1.0
        tx = ty = 0.0

        for ancestor in ancestors:
            lsx, lsy, ltx, lty = affine(
                ancestor.get("transform", ""),
            )
            tx += sx * ltx
            ty += sy * lty
            sx *= lsx
            sy *= lsy

        _, (x, y, width, height) = rectangles[0]

        registered[name] = (
            sx * x + tx,
            sy * y + ty,
            sx * width,
            sy * height,
        )

    view_box = [float(value) for value in root.attrib["viewBox"].split()]

    physical_width = _millimeters(root.attrib["width"])
    physical_height = _millimeters(root.attrib["height"])

    vx, vy, vw, vh = view_box

    for name, expected_bounds in expected.items():
        x, y, width, height = registered[name]

        actual = (
            (x - vx) / vw * physical_width,
            (y - vy) / vh * physical_height,
            width / vw * physical_width,
            height / vh * physical_height,
        )

        assert actual == pytest.approx(expected_bounds)


def test_laser_package_exports_participating_shape_components(
    tmp_path: Path,
) -> None:
    """
    Participating Shape components must appear as independent
    manufacturing objects.

    Structural boundaries are outlines; registered border-label
    glyphs remain filled vector geometry rather than construction
    paths or text requiring font resolution.
    """

    directory = tmp_path / "shape" / "compose"

    manifest_path = _write_shape_composition(directory)

    # A registered label Product generated by Shape Compose.
    # It deliberately contains a filled path rather than <text>.
    (directory / "top-border-label.svg").write_text(
        f"""
        <svg xmlns="{SVG_NS}" viewBox="-0.5 -0.5 1 1">
          <path
              id="glyph-A"
              d="M -0.10 -0.30
                 L 0.00 -0.40
                 L 0.10 -0.30
                 Z"
              fill="black"/>
        </svg>
        """,
        encoding="utf-8",
    )

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    manifest["border_labels"] = {
        "top": {
            "path": "top-border-label.svg",
        },
        "bottom": None,
    }

    manifest_path.write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )

    output_path = tmp_path / "laser" / "package" / "artifact.svg"

    context = Mock(spec=StageContext)
    context.input.side_effect = {
        "shape.compose.manifest": manifest_path,
    }.__getitem__
    context.output.side_effect = {
        "artifact": output_path,
    }.__getitem__
    context.resolver.side_effect = {
        "shape_size": 100.0,
    }.__getitem__

    package.execute(context)

    root = ET.parse(output_path).getroot()

    # The Shape perimeter is an outline, not a filled engraving.
    boundary = _svg_id(root, "shape-boundary")
    assert boundary is not None
    assert boundary.get("fill") == "none"

    # The label is an independent semantic component.
    label = _svg_id(root, "top-border-label")
    assert label is not None

    # Registered glyph geometry must be included without text
    # reconstruction or dependence on an installed font.
    glyphs = [element for element in label.iter(f"{SVG}path") if element.get("id") == "glyph-A"]

    assert len(glyphs) == 1
    assert glyphs[0].get("fill") == "black"

    assert not list(root.iter(f"{SVG}text"))

    # The semantic label object must not be replaced by the
    # construction baseline used during Shape composition.
    construction_baseline = _svg_id(
        root,
        "top-border-label-path",
    )

    assert construction_baseline is None

    # Existing registered Artwork remains independently present.
    assert _svg_id(root, "artwork-1") is not None
    assert _svg_id(root, "artwork-2") is not None
