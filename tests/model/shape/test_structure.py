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
# Polygon registered geometry
# =========================================================


@pytest.mark.parametrize(
    "shape_sides",
    (
        3,
        5,
        6,
        8,
        12,
    ),
)
def test_polygon_geometry_uses_requested_number_of_sides(
    shape_sides: int,
) -> None:
    """
    Regular polygon construction produces the requested number of vertices.

    Polygon mechanics are generic rather than specific to named geometries
    such as triangle, hexagon, or octagon.
    """

    geometry = structure.create_polygon_geometry(
        number_of_sides=shape_sides,
        rotation=0.0,
    )

    assert len(geometry.vertices) == shape_sides


def test_polygon_geometry_zero_rotation_places_vertex_at_top() -> None:
    """
    Zero polygon rotation places one vertex on the positive Y axis.

    This establishes the canonical regular-polygon orientation independently
    of the number of polygon sides.
    """

    geometry = structure.create_polygon_geometry(
        number_of_sides=8,
        rotation=0.0,
    )

    top = max(
        geometry.vertices,
        key=lambda vertex: vertex[1],
    )

    assert top[0] == pytest.approx(0.0)
    assert top[1] == pytest.approx(0.5)


def test_polygon_positive_rotation_is_counterclockwise() -> None:
    """
    Positive polygon rotation is counterclockwise when viewed from above.

    Rotating the canonical top vertex positively therefore moves that vertex
    from the positive Y axis toward the negative X axis.
    """

    geometry = structure.create_polygon_geometry(
        number_of_sides=8,
        rotation=10.0,
    )

    rotated_top_vertex = geometry.vertices[0]

    assert rotated_top_vertex[0] < 0.0
    assert rotated_top_vertex[1] > 0.0


def test_polygon_geometry_half_step_rotation_places_side_at_top() -> None:
    """
    Rotation by half the polygon angular step places a side at the top.

    For an eight-sided polygon, 180 / 8 = 22.5 degrees changes the canonical
    vertex-top orientation into a side-top orientation.
    """

    geometry = structure.create_polygon_geometry(
        number_of_sides=8,
        rotation=22.5,
    )

    top_vertices = sorted(
        geometry.vertices,
        key=lambda vertex: vertex[1],
        reverse=True,
    )[:2]

    assert top_vertices[0][1] == pytest.approx(
        top_vertices[1][1],
    )

    assert top_vertices[0][0] == pytest.approx(
        -top_vertices[1][0],
    )

    assert top_vertices[0][0] != pytest.approx(0.0)


@pytest.mark.parametrize(
    "rotation",
    (
        0.0,
        11.25,
        22.5,
        45.0,
        73.0,
    ),
)
def test_polygon_rotation_preserves_canonical_maximum_extent(
    rotation: float,
) -> None:
    """
    Polygon rotation changes orientation without changing registered size.

    The rotated polygon is uniformly normalized so its greatest X/Y extent
    remains the canonical registered extent of 1.0.
    """

    geometry = structure.create_polygon_geometry(
        number_of_sides=8,
        rotation=rotation,
    )

    assert max(
        geometry.width,
        geometry.height,
    ) == pytest.approx(1.0)

    assert geometry.min_x == pytest.approx(
        -geometry.max_x,
    )
    assert geometry.min_y == pytest.approx(
        -geometry.max_y,
    )


def test_polygon_rotation_preserves_regular_polygon_proportions() -> None:
    """
    Registered normalization does not stretch rotated polygon geometry.

    Every edge of the regular polygon remains the same length after rotation
    and normalization.
    """

    geometry = structure.create_polygon_geometry(
        number_of_sides=8,
        rotation=17.0,
    )

    vertices = geometry.vertices

    edge_lengths = []

    for index, vertex in enumerate(vertices):
        next_vertex = vertices[(index + 1) % len(vertices)]

        dx = next_vertex[0] - vertex[0]
        dy = next_vertex[1] - vertex[1]

        edge_lengths.append((dx * dx + dy * dy) ** 0.5)

    assert edge_lengths == pytest.approx([edge_lengths[0]] * len(edge_lengths))


def test_polygon_svg_contains_registered_polygon() -> None:
    """
    Generic polygon geometry can be represented as registered SVG.

    SVG persistence retains the generated polygon vertices in registered
    Shape coordinate space.
    """

    geometry = structure.create_polygon_geometry(
        number_of_sides=8,
        rotation=22.5,
    )

    document = structure.create_polygon_svg(
        geometry,
    )

    root = document.getroot()

    assert root.get("viewBox") == "-0.5 -0.5 1.0 1.0"

    polygon = root.find(
        "{http://www.w3.org/2000/svg}polygon",
    )

    assert polygon is not None

    points = polygon.get(
        "points",
    )

    assert points is not None

    coordinates = [tuple(float(value) for value in point.split(",")) for point in points.split()]

    assert len(coordinates) == 8

    for actual, expected in zip(
        coordinates,
        geometry.vertices,
        strict=True,
    ):
        assert actual == pytest.approx(expected)


@pytest.mark.parametrize(
    "shape_sides",
    (
        0,
        1,
        2,
    ),
)
def test_polygon_geometry_rejects_fewer_than_three_sides(
    shape_sides: int,
) -> None:
    """
    Regular polygon geometry requires at least three sides.
    """

    with pytest.raises(
        ValueError,
        match="sides",
    ):
        structure.create_polygon_geometry(
            number_of_sides=shape_sides,
            rotation=0.0,
        )


# =========================================================
# Physical base dimensionalization
# =========================================================


@pytest.mark.parametrize(
    ("shape_geometry", "geometry_factory"),
    (
        ("circle", structure.create_circle_geometry),
        ("square", structure.create_square_geometry),
    ),
)
def test_structural_base_uses_shape_size_as_physical_envelope(
    shape_geometry: str,
    geometry_factory,
) -> None:
    """
    Physical base dimensionalization applies Shape size to registered geometry.

    Circle and square registered Shapes occupy the complete canonical 1.0 by
    1.0 envelope, so shape_size establishes their complete physical X/Y
    envelope.
    """

    registered = geometry_factory()

    base = structure.create_structural_base(
        registered,
        shape_size=100.0,
        shape_base_raise=2.0,
    )

    assert base.geometry_name == shape_geometry
    assert base.width == 100.0
    assert base.height == 100.0


@pytest.mark.parametrize(
    "shape_size",
    (
        75.0,
        100.0,
        125.0,
    ),
)
def test_structural_base_scales_registered_geometry_to_shape_size(
    shape_size: float,
) -> None:
    """
    Changing shape_size changes physical size rather than registered geometry.
    """

    registered = structure.create_circle_geometry()

    base = structure.create_structural_base(
        registered,
        shape_size=shape_size,
        shape_base_raise=2.0,
    )

    assert registered.width == 1.0
    assert registered.height == 1.0

    assert base.width == shape_size
    assert base.height == shape_size


@pytest.mark.parametrize(
    "shape_base_raise",
    (
        1.0,
        2.0,
        4.5,
    ),
)
def test_structural_base_uses_shape_base_raise_as_physical_thickness(
    shape_base_raise: float,
) -> None:
    """
    Structural base thickness is introduced at dimensionalization.

    The physical base begins at Z=0 and extends through shape_base_raise.
    """

    registered = structure.create_circle_geometry()

    base = structure.create_structural_base(
        registered,
        shape_size=100.0,
        shape_base_raise=shape_base_raise,
    )

    assert base.min_z == 0.0
    assert base.max_z == shape_base_raise
    assert base.thickness == shape_base_raise


def test_structural_base_preserves_registered_source_geometry() -> None:
    """
    Physical dimensionalization does not alter registered Shape geometry.

    Registered geometry remains reusable independently of any physical Shape
    realization derived from it.
    """

    registered = structure.create_circle_geometry()

    small = structure.create_structural_base(
        registered,
        shape_size=75.0,
        shape_base_raise=2.0,
    )
    large = structure.create_structural_base(
        registered,
        shape_size=125.0,
        shape_base_raise=4.0,
    )

    assert registered.width == 1.0
    assert registered.height == 1.0

    assert small.width == 75.0
    assert small.height == 75.0
    assert small.thickness == 2.0

    assert large.width == 125.0
    assert large.height == 125.0
    assert large.thickness == 4.0


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
    ),
)
def test_structure_stage_materializes_selected_registered_geometry(
    tmp_path: Path,
    shape_geometry: str,
    element_name: str,
) -> None:
    """
    Structural production dispatches the established nonpolygon Shape geometry.

    Every selected geometry is persisted in canonical registered Shape space.
    Polygon stage dispatch is established separately once the generic polygon
    construction primitive exists.
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

    assert (
        call(
            "shape",
            "structure",
            structure.execute,
        )
        in registry.register.call_args_list
    )


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


def test_structure_stage_materializes_configured_polygon(
    tmp_path: Path,
) -> None:
    """
    Polygon structural production resolves side count and rotation.

    Polygon-specific policy participates in structural geometry only when
    polygon geometry is selected.
    """

    output = tmp_path / "structure.svg"

    resolver = Mock(
        side_effect={
            "shape_geometry": "polygon",
            "shape_sides": 6,
            "shape_rotation": 30.0,
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
        call("shape_sides"),
        call("shape_rotation"),
    ]

    assert output.is_file()

    root = ET.parse(
        output,
    ).getroot()

    polygon = root.find(
        "{http://www.w3.org/2000/svg}polygon",
    )

    assert polygon is not None

    points = polygon.get("points")

    assert points is not None
    assert len(points.split()) == 6


@pytest.mark.parametrize(
    "shape_geometry",
    (
        "circle",
        "square",
    ),
)
def test_structure_stage_does_not_resolve_polygon_policy_for_other_geometry(
    tmp_path: Path,
    shape_geometry: str,
) -> None:
    """
    Polygon-specific policy is not resolved for circle or square geometry.
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

    assert resolver.call_args_list == [
        call("shape_geometry"),
    ]


def test_polygon_structural_base_uses_shape_size_as_maximum_extent() -> None:
    """
    Polygon physical dimensionalization applies shape_size uniformly.

    The polygon's greatest physical X/Y extent equals shape_size while the
    other extent retains the registered polygon's proportions.
    """

    registered = structure.create_polygon_geometry(
        number_of_sides=3,
        rotation=0.0,
    )

    base = structure.create_structural_base(
        registered,
        shape_size=100.0,
        shape_base_raise=2.0,
    )

    assert base.geometry_name == "polygon"

    assert max(
        base.width,
        base.height,
    ) == pytest.approx(100.0)

    assert base.width == pytest.approx(registered.width * 100.0)
    assert base.height == pytest.approx(registered.height * 100.0)


def test_polygon_structural_base_preserves_rotated_registered_proportions() -> None:
    """
    Polygon dimensionalization preserves the rotated registered geometry.

    Rotation may change the relative X/Y extents but does not change the
    configured maximum physical Shape extent.
    """

    first_registered = structure.create_polygon_geometry(
        number_of_sides=3,
        rotation=0.0,
    )
    rotated_registered = structure.create_polygon_geometry(
        number_of_sides=3,
        rotation=30.0,
    )

    first = structure.create_structural_base(
        first_registered,
        shape_size=100.0,
        shape_base_raise=2.0,
    )
    rotated = structure.create_structural_base(
        rotated_registered,
        shape_size=100.0,
        shape_base_raise=2.0,
    )

    assert max(
        first.width,
        first.height,
    ) == pytest.approx(100.0)

    assert max(
        rotated.width,
        rotated.height,
    ) == pytest.approx(100.0)

    assert (
        first.width,
        first.height,
    ) != pytest.approx(
        (
            rotated.width,
            rotated.height,
        )
    )
