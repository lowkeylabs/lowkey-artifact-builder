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
    Laser packages registered Shape geometry as planar manufacturing
    objects, preserving Artwork identity and registration.

    The perimeter is an outline, the outer ridge is a filled
    annular region, and the complete Shape Base is not filled.
    """
    composition_manifest = _write_shape_composition(
        tmp_path / "shape" / "compose",
    )

    artifact = tmp_path / "laser" / "package" / "artifact.svg"

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
    assert _millimeters(root.attrib["width"]) == pytest.approx(100.0)
    assert _millimeters(root.attrib["height"]) == pytest.approx(100.0)

    assert tuple(float(value) for value in root.attrib["viewBox"].split()) == pytest.approx(
        (-0.5, -0.5, 1.0, 1.0)
    )

    boundary = _svg_id(root, "shape-boundary")
    assert boundary is not None
    assert boundary.tag == f"{SVG}path"
    assert boundary.get("fill") == "none"
    assert boundary.get("stroke") == "black"

    ridge = _svg_id(root, "ridge")
    assert ridge is not None
    assert ridge.tag == f"{SVG}path"
    assert ridge.get("fill") == "black"
    assert ridge.get("fill-rule") == "evenodd"
    assert ridge.get("stroke") == "none"

    # The compound ridge path contains both registered circles.
    assert ridge.attrib["d"].count("M ") == 2
    assert "0.5 0.5" in ridge.attrib["d"]
    assert "0.45 0.45" in ridge.attrib["d"]

    # Structural construction boundaries are not separate
    # manufacturing objects.
    assert _svg_id(root, "ridge-inner-boundary") is None

    # No opaque Shape Base or document background is exported.
    assert _svg_id(root, "base") is None
    assert not any(
        element.tag == f"{SVG}rect" and element.get("id") in {"background", "base"}
        for element in root.iter()
    )

    artwork_1 = _svg_id(root, "artwork-1")
    artwork_2 = _svg_id(root, "artwork-2")

    assert artwork_1 is not None
    assert artwork_2 is not None
    assert artwork_1 is not artwork_2

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
    Laser exports registered manufacturing components independently.

    Ridge geometry is a filled planar region. Border-label glyphs
    remain registered filled vectors, not construction baselines
    or font-dependent text.
    """
    directory = tmp_path / "shape" / "compose"
    manifest_path = _write_shape_composition(directory)

    (directory / "top-border-label.svg").write_text(
        f"""
        <svg xmlns="{SVG_NS}" viewBox="-0.5 -0.5 1 1">
          <path
              id="glyph-A"
              d="M -0.10 -0.30
                 L 0.00 -0.40
                 L 0.10 -0.30 Z"
              fill="black"/>
        </svg>
        """,
        encoding="utf-8",
    )

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["border_labels"] = {
        "top": {"path": "top-border-label.svg"},
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

    boundary = _svg_id(root, "shape-boundary")
    assert boundary is not None
    assert boundary.get("fill") == "none"

    ridge = _svg_id(root, "ridge")
    assert ridge is not None
    assert ridge.get("fill") == "black"
    assert ridge.get("fill-rule") == "evenodd"

    label = _svg_id(root, "top-border-label")
    assert label is not None

    glyphs = [element for element in label.iter(f"{SVG}path") if element.get("id") == "glyph-A"]

    assert len(glyphs) == 1
    assert glyphs[0].get("fill") == "black"

    assert not list(root.iter(f"{SVG}text"))

    for identifier in (
        "top-border-label-path",
        "bottom-border-label-path",
        "border-label-top-baseline",
        "border-label-bottom-baseline",
    ):
        assert _svg_id(root, identifier) is None

    assert _svg_id(root, "artwork-1") is not None
    assert _svg_id(root, "artwork-2") is not None


def test_laser_package_preserves_centered_shape_layout(
    tmp_path: Path,
) -> None:
    """
    All registered Shape components share one centered coordinate system.

    Outer and inner ridges retain their registered geometry.
    Border labels retain their positions, and Artwork retains its
    intentional offset rather than being independently centered.
    """
    directory = tmp_path / "shape" / "compose"
    manifest_path = _write_shape_composition(directory)

    composition_path = directory / "composition.svg"
    composition = ET.parse(composition_path)

    for identifier, radius in (
        ("inner-ridge-outer-boundary", 0.35),
        ("inner-ridge-inner-boundary", 0.33),
    ):
        ET.SubElement(
            composition.getroot(),
            f"{SVG}circle",
            {
                "id": identifier,
                "cx": "0",
                "cy": "0",
                "r": str(radius),
                "fill": "none",
            },
        )

    composition.write(
        composition_path,
        encoding="utf-8",
        xml_declaration=True,
    )

    labels = {
        "top": (-0.10, -0.40, 0.10, -0.30),
        "bottom": (-0.10, 0.30, 0.10, 0.40),
    }

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    for position, (x1, y1, x2, y2) in labels.items():
        filename = f"{position}-border-label.svg"

        label = ET.Element(
            f"{SVG}svg",
            {"viewBox": "-0.5 -0.5 1 1"},
        )

        ET.SubElement(
            label,
            f"{SVG}rect",
            {
                "id": f"{position}-glyph",
                "x": str(x1),
                "y": str(y1),
                "width": str(x2 - x1),
                "height": str(y2 - y1),
                "fill": "black",
            },
        )

        ET.ElementTree(label).write(
            directory / filename,
            encoding="utf-8",
            xml_declaration=True,
        )

        manifest["border_labels"][position] = {
            "path": filename,
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

    assert tuple(float(value) for value in root.attrib["viewBox"].split()) == pytest.approx(
        (-0.5, -0.5, 1.0, 1.0)
    )

    assert _millimeters(root.attrib["width"]) == pytest.approx(100.0)
    assert _millimeters(root.attrib["height"]) == pytest.approx(100.0)

    boundary = _svg_id(root, "shape-boundary")
    assert boundary is not None
    assert boundary.tag == f"{SVG}path"
    assert "0.5 0.5" in boundary.attrib["d"]

    outer_ridge = _svg_id(root, "ridge")
    assert outer_ridge is not None
    assert outer_ridge.get("fill-rule") == "evenodd"
    assert outer_ridge.attrib["d"].count("M ") == 2
    assert "0.5 0.5" in outer_ridge.attrib["d"]
    assert "0.45 0.45" in outer_ridge.attrib["d"]

    inner_ridge = _svg_id(root, "inner-ridge")
    assert inner_ridge is not None
    assert inner_ridge.get("fill-rule") == "evenodd"
    assert inner_ridge.attrib["d"].count("M ") == 2
    assert "0.35 0.35" in inner_ridge.attrib["d"]
    assert "0.33 0.33" in inner_ridge.attrib["d"]

    for identifier in (
        "ridge-inner-boundary",
        "inner-ridge-outer-boundary",
        "inner-ridge-inner-boundary",
    ):
        assert _svg_id(root, identifier) is None

    for position, (x1, y1, x2, y2) in labels.items():
        group = _svg_id(root, f"{position}-border-label")
        assert group is not None

        glyph = _svg_id(group, f"{position}-glyph")
        assert glyph is not None

        assert float(glyph.attrib["x"]) == pytest.approx(x1)
        assert float(glyph.attrib["y"]) == pytest.approx(y1)
        assert float(glyph.attrib["width"]) == pytest.approx(x2 - x1)
        assert float(glyph.attrib["height"]) == pytest.approx(y2 - y1)

    artwork = _svg_id(root, "artwork")
    assert artwork is not None

    assert artwork.attrib["transform"] == ("translate(-0.4 -0.4) scale(0.05)")

    assert _svg_id(artwork, "artwork-1") is not None
    assert _svg_id(artwork, "artwork-2") is not None
