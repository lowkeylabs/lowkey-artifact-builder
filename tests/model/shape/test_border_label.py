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


def _stl_bounds(
    path: Path,
) -> tuple[
    float,
    float,
    float,
    float,
    float,
    float,
]:
    """
    Return min/max X, Y, and Z bounds from an ASCII OpenSCAD STL.
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

    xs = [vertex[0] for vertex in vertices]
    ys = [vertex[1] for vertex in vertices]
    zs = [vertex[2] for vertex in vertices]

    return (
        min(xs),
        max(xs),
        min(ys),
        max(ys),
        min(zs),
        max(zs),
    )


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
    """
    Configure the Shape Extrude boundary for Border Label feature tests.

    Parameters material to the behavior under test are supplied explicitly.
    Unrelated optional Shape Extrude features use their ordinary
    nonparticipating defaults so adding such a feature does not require
    Border Label tests to enumerate its parameter contract.
    """

    inputs = {
        "compose.composition": composition,
        "compose.manifest": composition_manifest,
    }

    outputs = {
        "manifest": manifest,
    }

    defaults = {
        "shape_hole_diameter": 0.0,
    }

    def resolver(
        name: str,
    ) -> object:
        if name in values:
            return values[name]

        if name in defaults:
            return defaults[name]

        raise KeyError(
            name,
        )

    context.input.side_effect = inputs.__getitem__
    context.output.side_effect = outputs.__getitem__
    context.resolver.side_effect = resolver


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

    Top and Bottom occupy the same physical lettering band. Their semantic
    baseline paths traverse different arcs so that both strings remain upright,
    but both baselines lie at the same radial position within that shared band.

    For a 100 mm circular Shape with no ridges:

    reference radius = 50 mm
    outer clearance = 1 mm
    Top baseline = 49 mm
    Bottom baseline = 49 mm
    common glyph-height allocation = 5 mm
    inner clearance = 1 mm
    inner boundary = 43 mm

    The registered baseline radius is therefore 0.49 and the registered
    inner-boundary radius is 0.44.
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
        0.49,
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

    Top and Bottom continue to share the baseline established solely by the
    outer Border Label clearance, at registered radius 0.49.

    Reducing the common glyph-height allocation therefore moves only the Border
    Label inner boundary outward. The 1 mm inner clearance remains between the
    fitted lettering band and that inner boundary.

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

    assert top_radius == pytest.approx(
        0.49,
    )

    #
    # At the configured 5 mm maximum:
    #
    #   .49 baseline
    #   -.05 glyph allocation
    #   -.01 inner clearance
    #   = .43 inner boundary
    #
    # Because the long Bottom label constrains the fit, the glyph allocation
    # is smaller than 5 mm and the inner boundary moves outward. It must remain
    # inside .48 because a positive glyph allocation still exists between the
    # shared baseline and the 1 mm inner clearance.
    #

    assert inner_radius > 0.43
    assert inner_radius < 0.48

    resolved_glyph_height = (top_radius - inner_radius) * 100.0 - 1.0

    assert resolved_glyph_height > 0.0
    assert resolved_glyph_height < 5.0


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


@pytest.mark.slow
def test_compose_materializes_border_label_glyph_geometry(
    tmp_path: Path,
) -> None:
    """
    Compose persists manufacturing geometry for each participating Border Label.

    The semantic Border Label path describes where the lettering is placed, but
    it is not itself manufacturing geometry consumed by Extrude. Compose must
    materialize the fitted and positioned glyph outlines as a distinct
    registered SVG product and publish that product through its manifest.

    Supporting baseline geometry may be used while constructing or converting
    the text, but it must not remain as renderable geometry in the persistent
    manufacturing product.
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

    composition_root = ET.parse(
        composition,
    ).getroot()

    semantic_path = next(
        element for element in composition_root if element.get("id") == "top-border-label-path"
    )

    semantic_path_data = semantic_path.get(
        "d",
    )

    assert semantic_path_data

    data = json.loads(
        manifest.read_text(
            encoding="utf-8",
        )
    )

    top_product = data["border_labels"]["top"]

    bottom_product = data["border_labels"]["bottom"]

    assert top_product is not None
    assert bottom_product is None

    top_path = manifest.parent / top_product["path"]

    assert top_path.exists()

    glyph_root = ET.parse(
        top_path,
    ).getroot()

    #
    # The persistent Border Label product is registered Shape geometry.
    #

    assert glyph_root.get("viewBox") == "-0.5 -0.5 1 1"

    #
    # Supporting baseline geometry belongs only to text layout/conversion.
    # It must not survive as renderable geometry in the manufacturing SVG
    # handed to Extrude.
    #

    baseline = next(
        (element for element in glyph_root.iter() if element.get("id") == "border-label-baseline"),
        None,
    )

    assert baseline is None

    #
    # Text must already have been converted to ordinary path geometry.
    #

    text_elements = [
        element
        for element in glyph_root.iter()
        if element.tag
        in {
            f"{{{SVG_NS}}}text",
            f"{{{SVG_NS}}}textPath",
        }
    ]

    assert not text_elements

    glyph_paths = [element for element in glyph_root.iter() if element.tag == f"{{{SVG_NS}}}path"]

    assert glyph_paths

    glyph_path_data = [
        path_data for element in glyph_paths if (path_data := element.get("d")) is not None
    ]

    assert glyph_path_data

    #
    # The manufacturing product must contain geometry distinct from the
    # semantic baseline path persisted in the composition.
    #

    assert all(path_data != semantic_path_data for path_data in glyph_path_data)

    #
    # Extrusion requires bounded glyph outlines rather than only an open
    # placement path.
    #

    assert any("Z" in path_data.upper() for path_data in glyph_path_data)


@pytest.mark.slow
def test_extrude_preserves_registered_border_label_xy_placement(
    tmp_path: Path,
) -> None:
    """
    Extrude preserves registered Border Label placement while converting from
    SVG registered coordinates into physical Cartesian coordinates.

    Compose owns registered SVG X/Y geometry:

        X increases rightward.
        Y increases downward.

    Extrude dimensionalizes that geometry into physical OpenSCAD coordinates:

        X increases rightward.
        Y increases upward.

    Therefore registered X retains its sign while registered Y changes sign.
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

    _write_border_label_component(
        top_border_label,
        element_id="top-border-label",
        d=("M 0.10,-0.40 L 0.20,-0.40 L 0.20,-0.30 L 0.10,-0.30 Z"),
    )

    composition_manifest.write_text(
        json.dumps(
            {
                "border_labels": {
                    "top": {
                        "path": top_border_label.name,
                    },
                    "bottom": None,
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
            "shape_outer_ridge_raise": 0.0,
            "shape_outer_ridge_style": "integrated",
            "shape_top_border_label_raise": 1.0,
            "shape_bottom_border_label_raise": 0.0,
        },
    )

    extrude.execute(
        context,
    )

    data = json.loads(
        manifest.read_text(
            encoding="utf-8",
        )
    )

    components = {component["name"]: component for component in data["components"]}

    top_component = components["top-border-label"]

    top_stl = manifest.parent / top_component["path"]

    assert top_stl.is_file()

    bounds = _stl_bounds(
        top_stl,
    )

    #
    # Registered SVG:
    #
    #     X +0.10 .. +0.20
    #     Y -0.40 .. -0.30
    #
    # 100 mm physical Cartesian Shape:
    #
    #     X +10 .. +20 mm
    #     Y +30 .. +40 mm
    #
    # SVG's downward-positive Y axis becomes OpenSCAD's upward-positive
    # Cartesian Y axis.
    #

    assert bounds == pytest.approx(
        (
            10.0,
            20.0,
            30.0,
            40.0,
            2.0,
            3.0,
        ),
        abs=0.01,
    )


@pytest.mark.slow
def test_real_border_label_glyphs_extrude_within_shape_envelope(
    tmp_path: Path,
) -> None:
    """
    Real Border Label glyph geometry survives the Compose -> Extrude pipeline.

    Compose fits and materializes real font outlines in registered SVG Shape
    coordinates. Extrude must manufacture those persisted glyph outlines at
    the intended physical size and location in Cartesian Shape coordinates.

    This acceptance test covers the real typography -> Compose -> Inkscape ->
    Extrude -> OpenSCAD manufacturing seam without prescribing exact font
    outline vertices.
    """

    structure = tmp_path / "structure.svg"
    composition = tmp_path / "compose" / "composition.svg"
    composition_manifest = tmp_path / "compose" / "products.json"
    extrude_manifest = tmp_path / "extrude" / "products.json"

    composition.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    _write_registered_circle_structure(
        structure,
    )

    compose_context = Mock(
        spec=StageContext,
    )

    _configure_compose_context(
        compose_context,
        structure=structure,
        composition=composition,
        manifest=composition_manifest,
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
        compose_context,
    )

    compose_data = json.loads(
        composition_manifest.read_text(
            encoding="utf-8",
        )
    )

    top_product = compose_data["border_labels"]["top"]

    assert top_product is not None

    top_svg = composition_manifest.parent / top_product["path"]

    assert top_svg.is_file()

    extrude_context = Mock(
        spec=StageContext,
    )

    _configure_extrude_context(
        extrude_context,
        composition=composition,
        composition_manifest=composition_manifest,
        manifest=extrude_manifest,
        values={
            "shape_size": 100.0,
            "shape_base_raise": 2.0,
            "shape_outer_ridge_raise": 0.0,
            "shape_outer_ridge_style": "integrated",
            "shape_top_border_label_raise": 1.0,
            "shape_bottom_border_label_raise": 0.0,
        },
    )

    extrude.execute(
        extrude_context,
    )

    extrude_data = json.loads(
        extrude_manifest.read_text(
            encoding="utf-8",
        )
    )

    components = {component["name"]: component for component in extrude_data["components"]}

    assert "top-border-label" in components
    assert "bottom-border-label" not in components

    top_component = components["top-border-label"]

    top_stl = extrude_manifest.parent / top_component["path"]

    assert top_stl.is_file()

    (
        min_x,
        max_x,
        min_y,
        max_y,
        min_z,
        max_z,
    ) = _stl_bounds(
        top_stl,
    )

    #
    # Real glyph geometry must have positive physical extent.
    #

    assert min_x < max_x
    assert min_y < max_y

    #
    # A Border Label fitted to a 100 mm circular Shape must remain inside
    # that Shape's physical X/Y envelope.
    #

    assert -50.0 <= min_x <= 50.0
    assert -50.0 <= max_x <= 50.0
    assert -50.0 <= min_y <= 50.0
    assert -50.0 <= max_y <= 50.0

    assert min_y > 0.0
    assert max_y > 0.0

    #
    # Extrude owns physical Z. The label begins on top of the 2 mm Base and
    # has a 1 mm physical raise.
    #

    assert min_z == pytest.approx(
        2.0,
        abs=0.01,
    )

    assert max_z == pytest.approx(
        3.0,
        abs=0.01,
    )
