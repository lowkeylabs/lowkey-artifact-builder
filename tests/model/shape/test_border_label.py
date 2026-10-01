"""
Feature tests for Shape Border Labels.

Border Label behavior is kept together here across Shape Compose, Extrude,
and Package. General stage contracts remain in their stage-oriented tests.

The first implementation slice establishes the registered-composition seam:
a participating Border Label consumes a physical perimeter band and its inner
boundary becomes the available registered Shape interior when no Inner Ridge
participates.
"""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from lowkey_artifact_builder.engine import StageContext
from lowkey_artifact_builder.model.models.shape.stages import (
    compose,
    extrude,
    package,
)

SVG_NS = "http://www.w3.org/2000/svg"


def _write_registered_border_label_composition(
    path: Path,
    *,
    top: bool,
    bottom: bool,
) -> None:
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

    if top:
        ET.SubElement(
            root,
            f"{{{SVG_NS}}}path",
            {
                "id": "top-border-label",
                "d": ("M -0.10,-0.40 L 0.10,-0.40 L 0.10,-0.35 L -0.10,-0.35 Z"),
            },
        )

    if bottom:
        ET.SubElement(
            root,
            f"{{{SVG_NS}}}path",
            {
                "id": "bottom-border-label",
                "d": ("M -0.10,0.35 L 0.10,0.35 L 0.10,0.40 L -0.10,0.40 Z"),
            },
        )

    ET.ElementTree(
        root,
    ).write(
        path,
        encoding="utf-8",
        xml_declaration=True,
    )


def _write_border_label_component(
    path: Path,
    *,
    element_id: str,
    d: str,
) -> None:
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
        f"{{{SVG_NS}}}path",
        {
            "id": element_id,
            "d": d,
        },
    )

    ET.ElementTree(
        root,
    ).write(
        path,
        encoding="utf-8",
        xml_declaration=True,
    )


def _write_registered_circle_structure(
    path: Path,
) -> None:
    """
    Write the canonical registered 1x1 circular Shape structure.
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


def _configure_extrude_context(
    context: Mock,
    *,
    composition: Path,
    composition_manifest: Path,
    manifest: Path,
    values: dict[str, object],
) -> None:
    inputs = {
        "compose.composition": composition,
        "compose.manifest": composition_manifest,
    }

    outputs = {
        "manifest": manifest,
    }

    context.input.side_effect = inputs.__getitem__
    context.output.side_effect = outputs.__getitem__
    context.resolver.side_effect = values.__getitem__


def _configure_compose_context(
    context: Mock,
    *,
    structure: Path,
    composition: Path,
    manifest: Path,
    values: dict[str, object],
) -> None:
    """
    Configure the minimum Shape Compose stage boundary for this feature test.

    The resolver remains strict: if Compose begins resolving an undeclared
    parameter, the test fails rather than silently manufacturing a value.
    """

    inputs = {
        "structure.structure": structure,
    }
    outputs = {
        "composition": composition,
        "manifest": manifest,
    }

    context.input.side_effect = inputs.__getitem__
    context.output.side_effect = outputs.__getitem__
    context.has_input.return_value = False
    context.resolver.side_effect = values.__getitem__


@pytest.mark.slow
def test_participating_border_label_defines_circular_registered_interior(
    tmp_path: Path,
) -> None:
    """
    A participating Border Label consumes its registered perimeter band.

    For a 100 mm circular Shape with no ridges, the Base outside boundary is
    the Border Label reference boundary at registered radius 0.50.

    A 1 mm outer border, 5 mm common glyph-height allocation, and 1 mm inner
    border consume 7 mm radially. The Border Label inner boundary therefore
    lies at registered radius 0.43 and becomes the available Shape interior.

    This test establishes the Compose seam without prescribing how font
    measurement or fitting is internally implemented.
    """

    structure = tmp_path / "structure.svg"
    composition = tmp_path / "composition.svg"
    manifest = tmp_path / "products.json"

    _write_registered_circle_structure(
        structure,
    )

    context = Mock(
        spec=StageContext,
    )

    _configure_compose_context(
        context,
        structure=structure,
        composition=composition,
        manifest=manifest,
        values={
            "shape_size": 100.0,
            "shape_outer_ridge_width": 0.0,
            "shape_outer_ridge_style": "integrated",
            "shape_inner_ridge_width": 0.0,
            "shape_inner_to_outer_ridge_dist": 10.0,
            "shape_border_label_width": 1.0,
            "shape_border_label_max_glyph_height": 5.0,
            "shape_border_label_arc_degrees": 140.0,
            "shape_border_label_end_margin": 1.0,
            "shape_border_label_font_family": "DejaVu Sans",
            "shape_top_border_label_text": "RICHMOND",
            "shape_bottom_border_label_text": "",
        },
    )

    compose.execute(
        context,
    )

    interior = compose.registered_interior_region(
        composition,
    )

    assert interior.tag == f"{{{SVG_NS}}}circle"
    assert float(interior.get("cx", "nan")) == pytest.approx(
        0.0,
    )
    assert float(interior.get("cy", "nan")) == pytest.approx(
        0.0,
    )
    assert float(interior.get("r", "nan")) == pytest.approx(
        0.43,
    )


@pytest.mark.slow
def test_top_and_bottom_border_labels_share_circular_glyph_height(
    tmp_path: Path,
) -> None:
    """
    Participating Top and Bottom Border Labels share one glyph-height allocation.

    When both labels fit at the configured 5 mm maximum, the circular Border
    Label geometry uses that full common allocation.

    For a 100 mm circular Shape with no ridges:

        reference radius = 50 mm
        Bottom baseline = 50 - 1 = 49 mm
        Top baseline = 49 - 5 = 44 mm
        inner boundary = 44 - 1 = 43 mm

    The registered radii are therefore 0.49, 0.44, and 0.43.
    """

    structure = tmp_path / "structure.svg"
    composition = tmp_path / "composition.svg"
    manifest = tmp_path / "products.json"

    _write_registered_circle_structure(
        structure,
    )

    context = Mock(
        spec=StageContext,
    )

    _configure_compose_context(
        context,
        structure=structure,
        composition=composition,
        manifest=manifest,
        values={
            "shape_size": 100.0,
            "shape_outer_ridge_width": 0.0,
            "shape_outer_ridge_style": "integrated",
            "shape_inner_ridge_width": 0.0,
            "shape_inner_to_outer_ridge_dist": 10.0,
            "shape_border_label_width": 1.0,
            "shape_border_label_max_glyph_height": 5.0,
            "shape_border_label_arc_degrees": 140.0,
            "shape_border_label_end_margin": 1.0,
            "shape_border_label_font_family": "DejaVu Sans",
            "shape_top_border_label_text": "RICHMOND",
            "shape_bottom_border_label_text": "VIRGINIA",
        },
    )

    compose.execute(
        context,
    )

    root = ET.parse(
        composition,
    ).getroot()

    bottom_baseline = next(
        element for element in root if element.get("id") == "border-label-bottom-baseline"
    )

    top_baseline = next(
        element for element in root if element.get("id") == "border-label-top-baseline"
    )

    inner_boundary = next(
        element for element in root if element.get("id") == "border-label-inner-boundary"
    )

    assert bottom_baseline.tag == f"{{{SVG_NS}}}circle"
    assert float(
        bottom_baseline.get(
            "r",
            "nan",
        )
    ) == pytest.approx(
        0.49,
    )

    assert top_baseline.tag == f"{{{SVG_NS}}}circle"
    assert float(
        top_baseline.get(
            "r",
            "nan",
        )
    ) == pytest.approx(
        0.44,
    )

    assert inner_boundary.tag == f"{{{SVG_NS}}}circle"
    assert float(
        inner_boundary.get(
            "r",
            "nan",
        )
    ) == pytest.approx(
        0.43,
    )


@pytest.mark.slow
def test_constrained_border_label_reduces_shared_circular_glyph_height(
    tmp_path: Path,
) -> None:
    """
    Either participating label may constrain the common glyph-height allocation.

    A deliberately long Bottom label cannot fit the configured circular path at
    the 5 mm maximum glyph height. Compose therefore reduces the common fitted
    glyph height used by both labels.

    The Bottom baseline depends only on the outer border width and remains at
    registered radius 0.49. The reduced common glyph height moves the Top
    baseline outward from 0.44 and the Border Label inner boundary outward from
    0.43.

    This establishes shared fitting without prescribing the fitting algorithm
    or an exact fitted font size.
    """

    structure = tmp_path / "structure.svg"
    composition = tmp_path / "composition.svg"
    manifest = tmp_path / "products.json"

    _write_registered_circle_structure(
        structure,
    )

    context = Mock(
        spec=StageContext,
    )

    _configure_compose_context(
        context,
        structure=structure,
        composition=composition,
        manifest=manifest,
        values={
            "shape_size": 100.0,
            "shape_outer_ridge_width": 0.0,
            "shape_outer_ridge_style": "integrated",
            "shape_inner_ridge_width": 0.0,
            "shape_inner_to_outer_ridge_dist": 10.0,
            "shape_border_label_width": 1.0,
            "shape_border_label_max_glyph_height": 5.0,
            "shape_border_label_arc_degrees": 140.0,
            "shape_border_label_end_margin": 1.0,
            "shape_border_label_font_family": "DejaVu Sans",
            "shape_top_border_label_text": "RICHMOND",
            "shape_bottom_border_label_text": ("COMMONWEALTH OF VIRGINIA COMMONWEALTH OF VIRGINIA"),
        },
    )

    compose.execute(
        context,
    )

    root = ET.parse(
        composition,
    ).getroot()

    bottom_baseline = next(
        element for element in root if element.get("id") == "border-label-bottom-baseline"
    )

    top_baseline = next(
        element for element in root if element.get("id") == "border-label-top-baseline"
    )

    inner_boundary = next(
        element for element in root if element.get("id") == "border-label-inner-boundary"
    )

    bottom_radius = float(
        bottom_baseline.get(
            "r",
            "nan",
        )
    )

    top_radius = float(
        top_baseline.get(
            "r",
            "nan",
        )
    )

    inner_radius = float(
        inner_boundary.get(
            "r",
            "nan",
        )
    )

    assert bottom_radius == pytest.approx(
        0.49,
    )

    assert top_radius > 0.44
    assert top_radius < bottom_radius

    assert inner_radius > 0.43
    assert inner_radius < top_radius

    resolved_glyph_height = (bottom_radius - top_radius) * 100.0

    assert resolved_glyph_height > 0.0
    assert resolved_glyph_height < 5.0

    assert (top_radius - inner_radius) * 100.0 == pytest.approx(
        1.0,
    )


@pytest.mark.slow
def test_participating_border_labels_create_distinct_circular_registered_paths(
    tmp_path: Path,
) -> None:
    """
    Participating Top and Bottom Border Labels create distinct registered paths.

    Both labels occupy the same fitted lettering band but follow different
    semantic baseline paths:

    - Top traverses the upper arc from left to right.
    - Bottom traverses the lower arc in the opposite direction so ordinary
      left-to-right text remains upright.

    The paths are registered composition geometry. Physical Z
    dimensionalization remains downstream.
    """

    structure = tmp_path / "structure.svg"
    composition = tmp_path / "composition.svg"
    manifest = tmp_path / "products.json"

    _write_registered_circle_structure(
        structure,
    )

    context = Mock(
        spec=StageContext,
    )

    _configure_compose_context(
        context,
        structure=structure,
        composition=composition,
        manifest=manifest,
        values={
            "shape_size": 100.0,
            "shape_outer_ridge_width": 0.0,
            "shape_outer_ridge_style": "integrated",
            "shape_inner_ridge_width": 0.0,
            "shape_inner_to_outer_ridge_dist": 10.0,
            "shape_border_label_width": 1.0,
            "shape_border_label_max_glyph_height": 5.0,
            "shape_border_label_arc_degrees": 140.0,
            "shape_border_label_end_margin": 1.0,
            "shape_border_label_font_family": "DejaVu Sans",
            "shape_top_border_label_text": "RICHMOND",
            "shape_bottom_border_label_text": "VIRGINIA",
        },
    )

    compose.execute(
        context,
    )

    root = ET.parse(
        composition,
    ).getroot()

    top_path = next(
        (element for element in root if element.get("id") == "top-border-label-path"),
        None,
    )

    bottom_path = next(
        (element for element in root if element.get("id") == "bottom-border-label-path"),
        None,
    )

    assert top_path is not None
    assert bottom_path is not None

    assert top_path.tag == f"{{{SVG_NS}}}path"
    assert bottom_path.tag == f"{{{SVG_NS}}}path"

    top_path_data = top_path.get(
        "d",
    )
    bottom_path_data = bottom_path.get(
        "d",
    )

    assert top_path_data
    assert bottom_path_data
    assert top_path_data != bottom_path_data

    #
    # Both semantic paths belong to the same circular lettering band, but
    # their opposite traversal directions require distinct arc commands.
    #

    assert " A " in top_path_data
    assert " A " in bottom_path_data


@pytest.mark.slow
def test_border_label_registered_paths_follow_independent_participation(
    tmp_path: Path,
) -> None:
    """
    Top and Bottom Border Label path participation is independent.

    Empty or whitespace-only text does not create semantic registered label
    geometry. A participating label does not implicitly create its counterpart.
    """

    structure = tmp_path / "structure.svg"
    composition = tmp_path / "composition.svg"
    manifest = tmp_path / "products.json"

    _write_registered_circle_structure(
        structure,
    )

    context = Mock(
        spec=StageContext,
    )

    _configure_compose_context(
        context,
        structure=structure,
        composition=composition,
        manifest=manifest,
        values={
            "shape_size": 100.0,
            "shape_outer_ridge_width": 0.0,
            "shape_outer_ridge_style": "integrated",
            "shape_inner_ridge_width": 0.0,
            "shape_inner_to_outer_ridge_dist": 10.0,
            "shape_border_label_width": 1.0,
            "shape_border_label_max_glyph_height": 5.0,
            "shape_border_label_arc_degrees": 140.0,
            "shape_border_label_end_margin": 1.0,
            "shape_border_label_font_family": "DejaVu Sans",
            "shape_top_border_label_text": "RICHMOND",
            "shape_bottom_border_label_text": "   ",
        },
    )

    compose.execute(
        context,
    )

    root = ET.parse(
        composition,
    ).getroot()

    top_path = next(
        (element for element in root if element.get("id") == "top-border-label-path"),
        None,
    )

    bottom_path = next(
        (element for element in root if element.get("id") == "bottom-border-label-path"),
        None,
    )

    assert top_path is not None
    assert top_path.tag == f"{{{SVG_NS}}}path"

    assert bottom_path is None


@pytest.mark.slow
def test_inner_ridge_follows_participating_border_label_region(
    tmp_path: Path,
) -> None:
    """
    A participating Inner Ridge begins at the Border Label inner boundary.

    Border Labels and Inner Ridge are independent features. When both
    participate, however, the already-composed Border Label inner boundary
    becomes the positioning reference for Inner Ridge.

    The legacy Inner-to-Outer Ridge distance is not applied again between
    the Border Label region and Inner Ridge.
    """

    structure = tmp_path / "structure.svg"
    composition = tmp_path / "composition.svg"
    manifest = tmp_path / "products.json"

    _write_registered_circle_structure(
        structure,
    )

    context = Mock(
        spec=StageContext,
    )

    _configure_compose_context(
        context,
        structure=structure,
        composition=composition,
        manifest=manifest,
        values={
            "shape_size": 100.0,
            "shape_outer_ridge_width": 5.0,
            "shape_outer_ridge_style": "integrated",
            "shape_inner_ridge_width": 2.0,
            "shape_inner_to_outer_ridge_dist": 10.0,
            "shape_border_label_width": 1.0,
            "shape_border_label_max_glyph_height": 5.0,
            "shape_border_label_arc_degrees": 140.0,
            "shape_border_label_end_margin": 1.0,
            "shape_border_label_font_family": "DejaVu Sans",
            "shape_top_border_label_text": "RICHMOND",
            "shape_bottom_border_label_text": "",
        },
    )

    compose.execute(
        context,
    )

    root = ET.parse(
        composition,
    ).getroot()

    elements = {element.get("id"): element for element in root if element.get("id") is not None}

    outer_ridge_inner = elements["ridge-inner-boundary"]
    border_label_inner = elements["border-label-inner-boundary"]
    inner_ridge_outer = elements["inner-ridge-outer-boundary"]
    inner_ridge_inner = elements["inner-ridge-inner-boundary"]

    #
    # 100 mm Shape:
    #
    #   Shape radius                     50 mm -> .50
    #   Outer Ridge width                 5 mm -> .45
    #   Border outer clearance            1 mm
    #   Border glyph allocation           5 mm
    #   Border inner clearance            1 mm -> .38
    #   Inner Ridge width                 2 mm -> .36
    #
    # The configured 10 mm Inner-to-Outer Ridge distance must not be
    # reapplied after the participating Border Label region.
    #

    assert float(
        outer_ridge_inner.get(
            "r",
            "0.0",
        )
    ) == pytest.approx(
        0.45,
    )

    assert float(
        border_label_inner.get(
            "r",
            "0.0",
        )
    ) == pytest.approx(
        0.38,
    )

    assert float(
        inner_ridge_outer.get(
            "r",
            "0.0",
        )
    ) == pytest.approx(
        0.38,
    )

    assert float(
        inner_ridge_inner.get(
            "r",
            "0.0",
        )
    ) == pytest.approx(
        0.36,
    )

    interior = compose.registered_interior_region(
        composition,
    )

    assert (
        interior.get(
            "id",
        )
        == "inner-ridge-inner-boundary"
    )

    assert float(
        interior.get(
            "r",
            "0.0",
        )
    ) == pytest.approx(
        0.36,
    )


@pytest.mark.slow
def test_border_label_region_reduces_artwork_placement_without_inner_ridge(
    tmp_path: Path,
) -> None:
    """
    Border Labels constrain Artwork placement when no Inner Ridge participates.

    The Border Label inner boundary becomes the registered Shape interior,
    and the public Artwork-placement operation must consume that boundary
    rather than the complete Shape or Outer Ridge boundary.
    """

    structure = tmp_path / "structure.svg"
    composition = tmp_path / "composition.svg"
    manifest = tmp_path / "products.json"

    _write_registered_circle_structure(
        structure,
    )

    context = Mock(
        spec=StageContext,
    )

    _configure_compose_context(
        context,
        structure=structure,
        composition=composition,
        manifest=manifest,
        values={
            "shape_size": 100.0,
            "shape_outer_ridge_width": 5.0,
            "shape_outer_ridge_style": "integrated",
            "shape_inner_ridge_width": 0.0,
            "shape_inner_to_outer_ridge_dist": 10.0,
            "shape_border_label_width": 1.0,
            "shape_border_label_max_glyph_height": 5.0,
            "shape_border_label_arc_degrees": 140.0,
            "shape_border_label_end_margin": 1.0,
            "shape_border_label_font_family": "DejaVu Sans",
            "shape_top_border_label_text": "RICHMOND",
            "shape_bottom_border_label_text": "",
        },
    )

    compose.execute(
        context,
    )

    interior = compose.registered_interior_region(
        composition,
    )

    assert (
        interior.get(
            "id",
        )
        == "border-label-inner-boundary"
    )

    assert float(
        interior.get(
            "r",
            "0.0",
        )
    ) == pytest.approx(
        0.38,
    )

    placement = compose.artwork_placement_circle(
        interior,
    )

    assert placement.center_x == pytest.approx(
        0.0,
    )

    assert placement.center_y == pytest.approx(
        0.0,
    )

    assert placement.radius == pytest.approx(
        0.38,
    )


def test_extrude_produces_independent_border_label_components(
    tmp_path: Path,
) -> None:
    """
    Participating Top and Bottom Border Labels become distinct physical
    components and consume their independently configured raises.

    Compose has already established participation and persisted registered
    glyph geometry. Extrude consumes that persistent contract without
    rediscovering Border Label typography or fitting.
    """

    composition = tmp_path / "composition.svg"
    composition_manifest = tmp_path / "composition-products.json"
    manifest = tmp_path / "extrude" / "products.json"

    _write_registered_border_label_composition(
        composition,
        top=False,
        bottom=False,
    )

    top_border_label = tmp_path / "top-border-label.svg"

    bottom_border_label = tmp_path / "bottom-border-label.svg"

    _write_border_label_component(
        top_border_label,
        element_id="top-border-label",
        d=("M -0.10,-0.40 L 0.10,-0.40 L 0.10,-0.35 L -0.10,-0.35 Z"),
    )

    _write_border_label_component(
        bottom_border_label,
        element_id="bottom-border-label",
        d=("M -0.10,0.35 L 0.10,0.35 L 0.10,0.40 L -0.10,0.40 Z"),
    )

    composition_manifest.write_text(
        json.dumps(
            {
                "border_labels": {
                    "top": {
                        "path": top_border_label.name,
                    },
                    "bottom": {
                        "path": bottom_border_label.name,
                    },
                },
                "artwork": None,
                "artwork_fill": None,
            }
        ),
        encoding="utf-8",
    )

    context = Mock(
        spec=StageContext,
    )

    _configure_extrude_context(
        context,
        composition=composition,
        composition_manifest=composition_manifest,
        manifest=manifest,
        values={
            "shape_size": 100.0,
            "shape_base_raise": 2.0,
            "shape_outer_ridge_raise": 1.0,
            "shape_outer_ridge_style": "integrated",
            "shape_top_border_label_raise": 1.0,
            "shape_bottom_border_label_raise": 2.0,
        },
    )

    def render_stl(
        source: str,
        output_path: Path,
    ) -> None:
        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        output_path.write_text(
            source,
            encoding="utf-8",
        )

    with patch.object(
        extrude,
        "render_stl_source",
        side_effect=render_stl,
    ):
        extrude.execute(
            context,
        )

    data = json.loads(
        manifest.read_text(
            encoding="utf-8",
        )
    )

    components = {component["name"]: component for component in data["components"]}

    assert "base" in components

    assert components["top-border-label"]["path"] == "top-border-label.stl"

    assert components["bottom-border-label"]["path"] == "bottom-border-label.stl"

    top_source = (manifest.parent / "top-border-label.stl").read_text(
        encoding="utf-8",
    )

    bottom_source = (manifest.parent / "bottom-border-label.stl").read_text(
        encoding="utf-8",
    )

    assert "shape_border_label_raise = 1" in top_source

    assert "shape_border_label_raise = 2" in bottom_source


def test_zero_raise_suppresses_only_that_border_label_component(
    tmp_path: Path,
) -> None:
    """
    Border Label participation is established by Compose and persisted in the
    composition manifest, while Extrude raise determines whether that semantic
    label has physical volume.

    A zero Top raise must not suppress a positive Bottom label.
    """

    composition = tmp_path / "composition.svg"
    composition_manifest = tmp_path / "composition-products.json"
    manifest = tmp_path / "extrude" / "products.json"

    _write_registered_border_label_composition(
        composition,
        top=False,
        bottom=False,
    )

    top_border_label = tmp_path / "top-border-label.svg"

    bottom_border_label = tmp_path / "bottom-border-label.svg"

    _write_border_label_component(
        top_border_label,
        element_id="top-border-label",
        d=("M -0.10,-0.40 L 0.10,-0.40 L 0.10,-0.35 L -0.10,-0.35 Z"),
    )

    _write_border_label_component(
        bottom_border_label,
        element_id="bottom-border-label",
        d=("M -0.10,0.35 L 0.10,0.35 L 0.10,0.40 L -0.10,0.40 Z"),
    )

    composition_manifest.write_text(
        json.dumps(
            {
                "border_labels": {
                    "top": {
                        "path": top_border_label.name,
                    },
                    "bottom": {
                        "path": bottom_border_label.name,
                    },
                },
                "artwork": None,
                "artwork_fill": None,
            }
        ),
        encoding="utf-8",
    )

    context = Mock(
        spec=StageContext,
    )

    _configure_extrude_context(
        context,
        composition=composition,
        composition_manifest=composition_manifest,
        manifest=manifest,
        values={
            "shape_size": 100.0,
            "shape_base_raise": 2.0,
            "shape_outer_ridge_raise": 1.0,
            "shape_outer_ridge_style": "integrated",
            "shape_top_border_label_raise": 0.0,
            "shape_bottom_border_label_raise": 1.0,
        },
    )

    def render_stl(
        source: str,
        output_path: Path,
    ) -> None:
        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        output_path.write_text(
            source,
            encoding="utf-8",
        )

    with patch.object(
        extrude,
        "render_stl_source",
        side_effect=render_stl,
    ):
        extrude.execute(
            context,
        )

    data = json.loads(
        manifest.read_text(
            encoding="utf-8",
        )
    )

    component_names = {component["name"] for component in data["components"]}

    assert "base" in component_names
    assert "top-border-label" not in component_names
    assert "bottom-border-label" in component_names

    bottom_source = (manifest.parent / "bottom-border-label.stl").read_text(
        encoding="utf-8",
    )

    assert "shape_border_label_raise = 1" in bottom_source

    assert not (manifest.parent / "top-border-label.stl").exists()


def test_package_resolves_independent_border_label_colors(
    tmp_path: Path,
) -> None:
    """
    Package assigns Top and Bottom Border Labels their independently resolved
    physical printer colors.

    Border Label component membership is already established by Extrude.
    Package owns only the physical color policy.
    """

    components = (
        package.PhysicalComponent(
            name="base",
            path=tmp_path / "base.stl",
            artifact_color_index=None,
            artifact_color=None,
        ),
        package.PhysicalComponent(
            name="top-border-label",
            path=tmp_path / "top-border-label.stl",
            artifact_color_index=None,
            artifact_color=None,
        ),
        package.PhysicalComponent(
            name="bottom-border-label",
            path=tmp_path / "bottom-border-label.stl",
            artifact_color_index=None,
            artifact_color=None,
        ),
    )

    context = Mock(
        spec=StageContext,
    )

    context.resolver.side_effect = {
        "shape_base_color": "black",
        "shape_top_border_label_color": "white",
        "shape_bottom_border_label_color": "red",
    }.__getitem__

    context.resolver.has.side_effect = lambda name: name in {
        "shape_top_border_label_color",
        "shape_bottom_border_label_color",
    }

    black = Mock()
    black.name = "black"

    white = Mock()
    white.name = "white"

    red = Mock()
    red.name = "red"

    palette = {
        "black": black,
        "white": white,
        "red": red,
    }

    with patch.object(
        package,
        "resolve_palette",
        side_effect=lambda names, _colors: tuple(palette[name] for name in names),
    ):
        colors = package._resolve_shape_component_colors(
            components,
            context=context,
        )

    assert colors["base"] is black
    assert colors["top-border-label"] is white
    assert colors["bottom-border-label"] is red


def test_package_border_label_colors_inherit_base_color(
    tmp_path: Path,
) -> None:
    """
    Top and Bottom Border Labels inherit the resolved Base color when their
    optional Package-time color overrides are not explicitly configured.

    Color inheritance does not affect Border Label participation or geometry.
    """

    components = (
        package.PhysicalComponent(
            name="base",
            path=tmp_path / "base.stl",
            artifact_color_index=None,
            artifact_color=None,
        ),
        package.PhysicalComponent(
            name="top-border-label",
            path=tmp_path / "top-border-label.stl",
            artifact_color_index=None,
            artifact_color=None,
        ),
        package.PhysicalComponent(
            name="bottom-border-label",
            path=tmp_path / "bottom-border-label.stl",
            artifact_color_index=None,
            artifact_color=None,
        ),
    )

    context = Mock(
        spec=StageContext,
    )

    context.resolver.side_effect = {
        "shape_base_color": "black",
    }.__getitem__

    context.resolver.has.return_value = False

    black = Mock()
    black.name = "black"

    with patch.object(
        package,
        "resolve_palette",
        return_value=(black,),
    ):
        colors = package._resolve_shape_component_colors(
            components,
            context=context,
        )

    assert colors["base"] is black
    assert colors["top-border-label"] is black
    assert colors["bottom-border-label"] is black
