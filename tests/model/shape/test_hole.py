"""
Feature tests for Shape Hole.

Hole behavior is kept together here across the Shape manufacturing boundary.
General Extrude contracts remain in their stage-oriented tests.

The first implementation slice establishes the physical subtraction seam:

- Hole is positioned inward from the dimensionalized Shape envelope.
- Hole subtracts from every intersecting manufactured component regardless
  of semantic ownership.
- Hole is subtractive geometry and does not become a physical component.
"""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import Mock

import pytest

from lowkey_artifact_builder.engine import StageContext
from lowkey_artifact_builder.model.models.shape.stages import extrude

SVG_NS = "http://www.w3.org/2000/svg"


def _stl_vertices(
    path: Path,
) -> tuple[
    tuple[
        float,
        float,
        float,
    ],
    ...,
]:
    """
    Return vertices from an ASCII OpenSCAD STL.
    """

    vertices: list[
        tuple[
            float,
            float,
            float,
        ]
    ] = []

    for line in path.read_text(
        encoding="utf-8",
    ).splitlines():
        parts = line.strip().split()

        if len(parts) != 4 or parts[0] != "vertex":
            continue

        vertices.append(
            (
                float(parts[1]),
                float(parts[2]),
                float(parts[3]),
            )
        )

    assert vertices

    return tuple(
        vertices,
    )


def _write_circular_composition(
    path: Path,
) -> None:
    """
    Write the canonical registered circular Shape boundary.
    """

    ET.register_namespace(
        "",
        SVG_NS,
    )

    root = ET.Element(
        f"{{{SVG_NS}}}svg",
        {
            "viewBox": "-0.5 -0.5 1.0 1.0",
        },
    )

    ET.SubElement(
        root,
        f"{{{SVG_NS}}}circle",
        {
            "id": "shape-boundary",
            "cx": "0.0",
            "cy": "0.0",
            "r": "0.5",
        },
    )

    ET.ElementTree(
        root,
    ).write(
        path,
        encoding="utf-8",
        xml_declaration=True,
    )


def _write_artwork_component(
    path: Path,
) -> None:
    """
    Write registered Artwork geometry used by the Hole intersection test.

    The Artwork occupies a 0.30 x 0.20 registered rectangle. Its persistent
    composition transform places that geometry across the top-center Hole
    region during Shape dimensionalization.
    """

    path.write_text(
        """
<svg
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 1.0 1.0"
>
    <rect
        x="0.0"
        y="0.0"
        width="0.30"
        height="0.20"
    />
</svg>
""".strip(),
        encoding="utf-8",
    )


def _write_composition_manifest(
    path: Path,
    *,
    artwork_component: Path | None = None,
) -> None:
    """
    Write the minimum persistent Shape composition manifest.

    When Artwork participates, its registered 0.30 x 0.20 geometry is
    positioned across the top-center region of the Shape so the physical
    Hole intersects it.
    """

    artwork: dict[str, object] | None = None

    if artwork_component is not None:
        artwork = {
            "registered_extent": {
                "width": 1.0,
                "height": 1.0,
            },
            "transform": {
                "scale": 1.0,
                "translate_x": -0.15,
                "translate_y": -0.5,
            },
            "components": [
                {
                    "index": 1,
                    "path": artwork_component.name,
                    "artifact_color": {
                        "index": 7,
                        "rgb": {
                            "red": 17,
                            "green": 43,
                            "blue": 91,
                        },
                    },
                },
            ],
        }

    path.write_text(
        json.dumps(
            {
                "artwork": artwork,
                "artwork_fill": None,
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def _configure_extrude_context(
    context: Mock,
    *,
    composition: Path,
    composition_manifest: Path,
    output_manifest: Path,
    values: dict[str, object],
) -> None:
    """
    Configure the Shape Extrude boundary for Hole feature tests.

    The resolver remains strict so unexpected parameter resolution fails
    rather than silently manufacturing test defaults.
    """

    inputs = {
        "compose.composition": composition,
        "compose.manifest": composition_manifest,
    }

    outputs = {
        "manifest": output_manifest,
    }

    context.input.side_effect = inputs.__getitem__
    context.output.side_effect = outputs.__getitem__
    context.resolver.side_effect = values.__getitem__


@pytest.mark.slow
def test_shape_hole_is_positioned_from_envelope_and_subtracted_from_base(
    tmp_path: Path,
) -> None:
    """
    A participating Hole is positioned inward from the physical Shape envelope.

    For a 100 mm circular Shape with:

        Hole diameter      = 10 mm
        Hole edge distance = 2 mm
        Hole position      = top

    the Shape radius is 50 mm and the Hole radius is 5 mm.

    The Hole center therefore lies at:

        Y = 50 - 5 - 2
          = 43 mm

    so the Hole occupies Y = 38..48 mm and its nearest edge is exactly
    2 mm inside the Shape envelope.

    The Hole is subtractive and does not become a physical component.
    """

    composition = tmp_path / "composition.svg"
    composition_manifest = tmp_path / "composition-products.json"
    output_manifest = tmp_path / "products.json"

    _write_circular_composition(
        composition,
    )

    _write_composition_manifest(
        composition_manifest,
    )

    context = Mock(
        spec=StageContext,
    )

    _configure_extrude_context(
        context,
        composition=composition,
        composition_manifest=composition_manifest,
        output_manifest=output_manifest,
        values={
            "shape_size": 100.0,
            "shape_base_raise": 2.0,
            "shape_outer_ridge_raise": 1.0,
            "shape_outer_ridge_style": "integrated",
            "shape_inner_ridge_raise": 1.0,
            "shape_top_border_label_raise": 1.0,
            "shape_bottom_border_label_raise": 1.0,
            "shape_artwork_raise": 1.0,
            "shape_hole_diameter": 10.0,
            "shape_hole_position": 0,
            "shape_hole_edge_distance": 2.0,
        },
    )

    extrude.execute(
        context,
    )

    data = json.loads(
        output_manifest.read_text(
            encoding="utf-8",
        )
    )

    assert [component["name"] for component in data["components"]] == [
        "base",
    ]

    base = output_manifest.parent / data["components"][0]["path"]

    vertices = _stl_vertices(
        base,
    )

    #
    # A circular through-hole creates vertical wall vertices at the expected
    # physical Hole extent. These extrema establish both its diameter and
    # its placement from the Shape envelope without prescribing the internal
    # SCAD construction.
    #

    hole_vertices = [
        vertex for vertex in vertices if 37.9 <= vertex[1] <= 48.1 and -5.1 <= vertex[0] <= 5.1
    ]

    assert hole_vertices

    hole_x = [vertex[0] for vertex in hole_vertices]
    hole_y = [vertex[1] for vertex in hole_vertices]

    assert min(hole_x) == pytest.approx(
        -5.0,
        abs=0.1,
    )
    assert max(hole_x) == pytest.approx(
        5.0,
        abs=0.1,
    )
    assert min(hole_y) == pytest.approx(
        38.0,
        abs=0.1,
    )
    assert max(hole_y) == pytest.approx(
        48.0,
        abs=0.1,
    )


@pytest.mark.slow
def test_shape_hole_subtracts_from_base_and_incorporated_artwork(
    tmp_path: Path,
) -> None:
    """
    Hole subtraction crosses semantic component ownership.

    Incorporated Artwork occupies the top-center region intersected by the
    configured Hole. Shape Extrude must subtract the same physical Hole from
    both the Shape-owned Base and the incorporated Artwork component.

    The remaining Artwork preserves its persistent Artifact-color identity.
    Hole itself does not become a physical component.
    """

    composition = tmp_path / "composition.svg"
    composition_manifest = tmp_path / "composition-products.json"
    artwork_component = tmp_path / "artwork-1.svg"
    output_manifest = tmp_path / "products.json"

    _write_circular_composition(
        composition,
    )

    _write_artwork_component(
        artwork_component,
    )

    _write_composition_manifest(
        composition_manifest,
        artwork_component=artwork_component,
    )

    context = Mock(
        spec=StageContext,
    )

    _configure_extrude_context(
        context,
        composition=composition,
        composition_manifest=composition_manifest,
        output_manifest=output_manifest,
        values={
            "shape_size": 100.0,
            "shape_base_raise": 2.0,
            "shape_outer_ridge_raise": 1.0,
            "shape_outer_ridge_style": "integrated",
            "shape_inner_ridge_raise": 1.0,
            "shape_top_border_label_raise": 1.0,
            "shape_bottom_border_label_raise": 1.0,
            "shape_artwork_raise": 1.0,
            "shape_hole_diameter": 10.0,
            "shape_hole_position": 0,
            "shape_hole_edge_distance": 2.0,
        },
    )

    extrude.execute(
        context,
    )

    data = json.loads(
        output_manifest.read_text(
            encoding="utf-8",
        )
    )

    components = {component["name"]: component for component in data["components"]}

    assert set(components) == {
        "base",
        "artwork-1",
    }

    assert components["artwork-1"]["color"] == {
        "index": 7,
        "rgb": {
            "red": 17,
            "green": 43,
            "blue": 91,
        },
    }

    component_vertices = {
        "base": _stl_vertices(
            output_manifest.parent / components["base"]["path"],
        ),
        "artwork-1": _stl_vertices(
            output_manifest.parent / components["artwork-1"]["path"],
        ),
    }

    #
    # Both independently manufactured components must contain vertices on
    # the same circular Hole wall. Checking the horizontal cardinal extrema
    # establishes that physical subtraction crossed the component-ownership
    # boundary.
    #

    for component_name, vertices in component_vertices.items():
        xs = [x for x, _, _ in vertices]
        ys = [y for _, y, _ in vertices]

        bounds = (
            f"{component_name} bounds: "
            f"x={min(xs):.3f}..{max(xs):.3f}, "
            f"y={min(ys):.3f}..{max(ys):.3f}"
        )

        assert any(
            x
            == pytest.approx(
                -5.0,
                abs=0.1,
            )
            and y
            == pytest.approx(
                43.0,
                abs=0.1,
            )
            for x, y, _ in vertices
        ), bounds

        assert any(
            x
            == pytest.approx(
                5.0,
                abs=0.1,
            )
            and y
            == pytest.approx(
                43.0,
                abs=0.1,
            )
            for x, y, _ in vertices
        ), bounds
