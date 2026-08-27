"""
Tests for Shape registered structural geometry.
"""
# File: tests/model/shape/test_structure.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from lowkey_artifact_builder.formats import svg
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
