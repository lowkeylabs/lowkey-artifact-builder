"""
Tests for Shape registered structural geometry.
"""
# File: tests/model/shape/test_structure.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import Mock, call

import pytest

from lowkey_artifact_builder.engine import StageContext
from lowkey_artifact_builder.engine.bootstrap import build_stage_registry
from lowkey_artifact_builder.formats import svg
from lowkey_artifact_builder.model.models.shape import stages
from lowkey_artifact_builder.model.models.shape.stages import structure

# =========================================================
# Circle registered geometry
# =========================================================


def test_circle_geometry_uses_canonical_registered_extent() -> None:
    """
    Circle structural geometry uses the canonical Shape registered extent.

    Registered Shape geometry is nonphysical. The complete circle has
    diameter 1.0 regardless of the Shape's later physical size.
    """

    geometry = structure.create_circle_geometry()

    assert geometry.diameter == 1.0
    assert geometry.width == 1.0
    assert geometry.height == 1.0


def test_circle_geometry_is_centered_about_registered_origin() -> None:
    """
    Registered circle geometry is centered about the Shape origin.

    The canonical Shape envelope spans -0.5 through +0.5 on both axes.
    """

    geometry = structure.create_circle_geometry()

    assert geometry.min_x == -0.5
    assert geometry.max_x == 0.5
    assert geometry.min_y == -0.5
    assert geometry.max_y == 0.5


def test_circle_geometry_requires_no_physical_size() -> None:
    """
    Registered structural construction is independent of physical Shape size.

    Physical X/Y dimensionalization belongs to the downstream Shape
    dimensionalization boundary.
    """

    first = structure.create_circle_geometry()
    second = structure.create_circle_geometry()

    assert first == second
    assert first.diameter == 1.0


# =========================================================
# Circle registered SVG
# =========================================================


def test_circle_geometry_produces_registered_svg_document() -> None:
    """
    Circle structural geometry can be represented as a registered SVG document.

    The SVG uses the canonical Shape registered envelope centered at the
    origin rather than introducing physical dimensions.
    """

    geometry = structure.create_circle_geometry()

    document = structure.create_circle_svg(
        geometry,
    )

    root = document.getroot()

    assert root is not None
    assert root.tag == "{http://www.w3.org/2000/svg}svg"
    assert root.get("viewBox") == "-0.5 -0.5 1.0 1.0"


def test_circle_svg_contains_canonical_registered_circle() -> None:
    """
    The structural SVG contains the canonical registered circle geometry.
    """

    geometry = structure.create_circle_geometry()

    document = structure.create_circle_svg(
        geometry,
    )

    root = document.getroot()

    circle = root.find(
        "{http://www.w3.org/2000/svg}circle",
    )

    assert circle is not None
    assert circle.get("cx") == "0.0"
    assert circle.get("cy") == "0.0"
    assert circle.get("r") == "0.5"


def test_circle_svg_can_be_persisted_as_declared_structure_product(
    tmp_path: Path,
) -> None:
    """
    Registered circle geometry can be persisted as an SVG product.

    Generic SVG persistence writes the model-specific registered geometry
    without assigning physical millimeter dimensions.
    """

    geometry = structure.create_circle_geometry()

    document = structure.create_circle_svg(
        geometry,
    )

    output = tmp_path / "structure.svg"

    svg.save(
        document,
        output,
    )

    assert output.is_file()

    persisted = ET.parse(
        output,
    )

    root = persisted.getroot()

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


# =========================================================
# Square registered geometry
# =========================================================


def test_square_geometry_uses_canonical_registered_extent() -> None:
    """
    Square structural geometry uses the canonical Shape registered extent.
    """

    geometry = structure.create_square_geometry()

    assert geometry.width == 1.0
    assert geometry.height == 1.0
    assert geometry.min_x == -0.5
    assert geometry.max_x == 0.5
    assert geometry.min_y == -0.5
    assert geometry.max_y == 0.5


def test_square_svg_contains_canonical_registered_square() -> None:
    """
    Registered square SVG fills the canonical Shape envelope.
    """

    geometry = structure.create_square_geometry()

    document = structure.create_square_svg(
        geometry,
    )

    root = document.getroot()

    assert root.get("viewBox") == "-0.5 -0.5 1.0 1.0"

    rect = root.find(
        "{http://www.w3.org/2000/svg}rect",
    )

    assert rect is not None
    assert rect.get("x") == "-0.5"
    assert rect.get("y") == "-0.5"
    assert rect.get("width") == "1.0"
    assert rect.get("height") == "1.0"


# =========================================================
# Octagon registered geometry
# =========================================================


def test_octagon_geometry_uses_canonical_registered_extent() -> None:
    """
    Octagon geometry uses a canonical 1.0 by 1.0 bounding envelope.
    """

    geometry = structure.create_octagon_geometry()

    assert geometry.width == 1.0
    assert geometry.height == 1.0
    assert geometry.min_x == -0.5
    assert geometry.max_x == 0.5
    assert geometry.min_y == -0.5
    assert geometry.max_y == 0.5


def test_octagon_svg_contains_centered_regular_octagon() -> None:
    """
    Registered octagon SVG contains a centered regular octagon.

    Its opposing horizontal and vertical vertices establish the canonical
    1.0 by 1.0 Shape bounding envelope.
    """

    geometry = structure.create_octagon_geometry()

    document = structure.create_octagon_svg(
        geometry,
    )

    root = document.getroot()

    assert root.get("viewBox") == "-0.5 -0.5 1.0 1.0"

    polygon = root.find(
        "{http://www.w3.org/2000/svg}polygon",
    )

    assert polygon is not None

    points = polygon.get("points")

    assert points is not None

    coordinates = [tuple(float(value) for value in point.split(",")) for point in points.split()]

    assert len(coordinates) == 8

    xs = [point[0] for point in coordinates]
    ys = [point[1] for point in coordinates]

    assert min(xs) == pytest.approx(-0.5)
    assert max(xs) == pytest.approx(0.5)
    assert min(ys) == pytest.approx(-0.5)
    assert max(ys) == pytest.approx(0.5)


# =========================================================
# Structural stage execution
# =========================================================


def test_structure_stage_materializes_declared_registered_product(
    tmp_path: Path,
) -> None:
    """
    Shape structural production materializes its declared registered SVG.

    The stage obtains Shape policy and its output location through StageContext
    rather than constructing artifact filesystem paths itself.
    """

    output = tmp_path / "structure.svg"

    resolver = Mock(
        side_effect={
            "shape_geometry": "circle",
        }.__getitem__,
    )

    context = Mock(
        spec=StageContext,
    )
    context.resolver = resolver
    context.output.return_value = output

    structure.execute(
        context,
    )

    assert resolver.call_args_list == [
        call("shape_geometry"),
    ]

    context.output.assert_called_once_with(
        "structure",
    )

    assert output.is_file()

    persisted = ET.parse(
        output,
    )

    root = persisted.getroot()

    assert root.get("viewBox") == "-0.5 -0.5 1.0 1.0"

    circle = root.find(
        "{http://www.w3.org/2000/svg}circle",
    )

    assert circle is not None
    assert circle.get("cx") == "0.0"
    assert circle.get("cy") == "0.0"
    assert circle.get("r") == "0.5"


@pytest.mark.parametrize(
    ("shape_geometry", "element_name"),
    (
        ("circle", "circle"),
        ("square", "rect"),
        ("octagon", "polygon"),
    ),
)
def test_structure_stage_materializes_selected_registered_geometry(
    tmp_path: Path,
    shape_geometry: str,
    element_name: str,
) -> None:
    """
    Structural production dispatches every declared Shape geometry.

    Every supported geometry is persisted in the same canonical registered
    Shape envelope.
    """

    output = tmp_path / "structure.svg"

    resolver = Mock(
        side_effect={
            "shape_geometry": shape_geometry,
        }.__getitem__,
    )

    context = Mock(
        spec=StageContext,
    )
    context.resolver = resolver
    context.output.return_value = output

    structure.execute(
        context,
    )

    assert output.is_file()

    root = ET.parse(
        output,
    ).getroot()

    assert root.get("viewBox") == "-0.5 -0.5 1.0 1.0"

    element = root.find(
        f"{{http://www.w3.org/2000/svg}}{element_name}",
    )

    assert element is not None


def test_structure_stage_rejects_unknown_geometry(
    tmp_path: Path,
) -> None:
    """
    Structural production rejects geometry outside the Shape definition.
    """

    output = tmp_path / "structure.svg"

    resolver = Mock(
        side_effect={
            "shape_geometry": "triangle",
        }.__getitem__,
    )

    context = Mock(
        spec=StageContext,
    )
    context.resolver = resolver
    context.output.return_value = output

    with pytest.raises(
        ValueError,
        match="triangle",
    ):
        structure.execute(
            context,
        )

    assert not output.exists()


# =========================================================
# Stage registration
# =========================================================


def test_shape_registers_structure_stage_implementation() -> None:
    """
    Shape contributes its structural implementation through its stage package.

    Registration uses logical model and stage identities rather than numeric
    stage IDs or engine-specific orchestration.
    """

    registry = Mock()

    stages.register_stage_implementations(
        registry,
    )

    assert registry.register.call_args_list == [
        call(
            "shape",
            "structure",
            structure.execute,
        ),
    ]


def test_engine_bootstrap_discovers_shape_structure_implementation() -> None:
    """
    Normal engine bootstrap discovers the executable Shape structure stage.

    Shape participates in generic model stage discovery without requiring the
    engine to know about the Shape model explicitly.
    """

    registry = build_stage_registry()

    implementation = registry.get(
        "shape",
        "structure",
    )

    assert implementation is structure.execute
