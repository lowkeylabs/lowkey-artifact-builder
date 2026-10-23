"""
Behavioral tests for the SHAPE Border Fill surface region.
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
from tests.support.model_parameters import model_test_resolver

SVG_NS = "http://www.w3.org/2000/svg"


def _compose_border_fill(
    tmp_path: Path,
    *,
    outer_width: float,
    outer_inset: float = 0.0,
    inner_width: float = 2.0,
) -> tuple[Path, Path]:
    """
    Execute registered SHAPE composition with controlled ridge geometry.

    No Artwork or Border Labels participate.
    """

    structure = tmp_path / "structure.svg"
    composition = tmp_path / "composition.svg"
    manifest = tmp_path / "products.json"
    artifact = tmp_path / "artifact.svg"

    structure.write_text(
        (
            f'<svg xmlns="{SVG_NS}" '
            'viewBox="-0.5 -0.5 1 1">'
            '<circle id="shape-boundary" '
            'cx="0" cy="0" r="0.5"/>'
            "</svg>"
        ),
        encoding="utf-8",
    )

    inputs = {
        "structure.structure": structure,
    }

    outputs = {
        "composition": composition,
        "manifest": manifest,
        "artifact": artifact,
    }

    context = Mock(spec=StageContext)

    context.input.side_effect = inputs.__getitem__
    context.has_input.side_effect = inputs.__contains__
    context.output.side_effect = outputs.__getitem__

    context.resolver.side_effect = model_test_resolver(
        "shape",
        overrides={
            "shape_size": 100.0,
            "shape_outer_ridge_width": outer_width,
            "shape_outer_ridge_inset": outer_inset,
            "shape_outer_ridge_style": "integrated",
            "shape_inner_ridge_width": inner_width,
            "shape_inner_to_outer_ridge_dist": 10.0,
            "shape_top_border_label_text": "",
            "shape_bottom_border_label_text": "",
            "shape_qr_payload": "",
        },
        project_root=tmp_path,
    )

    compose.execute(context)

    return composition, manifest


def test_border_fill_uses_existing_ridge_boundaries(
    tmp_path: Path,
) -> None:
    """
    Border Fill occupies the complete registered region between
    the participating Outer and Inner Ridges.

    The region exists independently of Border Label participation.
    Its geometry derives from existing registered boundaries rather
    than introducing independent offsets.
    """
    composition, manifest = _compose_border_fill(
        tmp_path,
        outer_width=5.0,
        outer_inset=2.0,
        inner_width=2.0,
    )

    root = ET.parse(composition).getroot()

    elements = {
        element.get("id"): element for element in root.iter() if element.get("id") is not None
    }

    outer_reference = elements["ridge-inner-boundary"]
    inner_reference = elements["inner-ridge-outer-boundary"]
    shape = elements["shape-boundary"]

    assert float(shape.get("r", "nan")) == pytest.approx(0.5)
    assert float(outer_reference.get("r", "nan")) == pytest.approx(0.43)
    assert float(inner_reference.get("r", "nan")) == pytest.approx(0.33)

    data = json.loads(manifest.read_text(encoding="utf-8"))

    assert "border_fill" in data

    border_fill = data["border_fill"]

    assert isinstance(border_fill, dict)

    outer_boundary = border_fill["outer_boundary"]
    inner_boundary = border_fill["inner_boundary"]

    assert outer_boundary == {
        "type": "circle",
        "cx": 0.0,
        "cy": 0.0,
        "r": pytest.approx(0.43),
    }

    assert inner_boundary == {
        "type": "circle",
        "cx": 0.0,
        "cy": 0.0,
        "r": pytest.approx(0.33),
    }


def test_border_fill_does_not_participate_without_inner_boundary(
    tmp_path: Path,
) -> None:
    """
    Without an Inner Ridge or Border Label, there is no
    positive-area Border Fill region.
    """

    _, manifest = _compose_border_fill(
        tmp_path,
        outer_width=5.0,
        inner_width=0.0,
    )

    data = json.loads(manifest.read_text(encoding="utf-8"))

    assert data.get("border_fill") is None


def test_package_resolves_border_fill_color_independently(
    tmp_path: Path,
) -> None:
    """
    Package assigns an independently configured physical color
    to the Border Fill component.

    Changing the Border Fill color does not change Base color
    or physical component identity.
    """

    components = (
        package.PhysicalComponent(
            name="base",
            path=tmp_path / "base.stl",
            artifact_color_index=None,
            artifact_color=None,
        ),
        package.PhysicalComponent(
            name="border-fill",
            path=tmp_path / "border-fill.stl",
            artifact_color_index=None,
            artifact_color=None,
        ),
    )

    context = Mock(spec=StageContext)

    context.resolver.side_effect = model_test_resolver(
        "shape",
        overrides={
            "shape_base_color": "black",
            "shape_border_fill_color": "red",
        },
        project_root=tmp_path,
    )

    black = Mock()
    black.name = "black"

    red = Mock()
    red.name = "red"

    palette = {
        "black": black,
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
    assert colors["border-fill"] is red


def test_package_border_fill_inherits_base_color(
    tmp_path: Path,
) -> None:
    """
    An unspecified Border Fill color inherits the resolved
    Base color.

    Inheritance follows the effective Base color, including
    an explicitly configured Base override.
    """

    components = (
        package.PhysicalComponent(
            name="base",
            path=tmp_path / "base.stl",
            artifact_color_index=None,
            artifact_color=None,
        ),
        package.PhysicalComponent(
            name="border-fill",
            path=tmp_path / "border-fill.stl",
            artifact_color_index=None,
            artifact_color=None,
        ),
    )

    context = Mock(spec=StageContext)

    context.resolver.side_effect = model_test_resolver(
        "shape",
        overrides={
            "shape_base_color": "black",
        },
        project_root=tmp_path,
    )

    black = Mock()
    black.name = "black"

    with patch.object(
        package,
        "resolve_palette",
        side_effect=lambda names, _colors: tuple(black for _ in names),
    ):
        colors = package._resolve_shape_component_colors(
            components,
            context=context,
        )

    assert colors["base"] is black
    assert colors["border-fill"] is black


def test_extrude_materializes_registered_border_fill(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Extrude consumes the registered Border Fill region produced
    by Compose and materializes it as an independent component.

    Border Fill has its own STL and physical component identity.
    """
    composition, composition_manifest = _compose_border_fill(
        tmp_path,
        outer_width=5.0,
        outer_inset=2.0,
        inner_width=2.0,
    )

    extrusion_manifest = tmp_path / "extrude" / "products.json"

    inputs = {
        "compose.composition": composition,
        "compose.manifest": composition_manifest,
    }

    context = Mock(spec=StageContext)
    context.input.side_effect = inputs.__getitem__
    context.has_input.side_effect = inputs.__contains__
    context.output.return_value = extrusion_manifest

    original_resolver = model_test_resolver(
        "shape",
        overrides={
            "shape_size": 100.0,
            "shape_outer_ridge_width": 5.0,
            "shape_outer_ridge_inset": 2.0,
            "shape_outer_ridge_style": "integrated",
            "shape_inner_ridge_width": 2.0,
            "shape_inner_to_outer_ridge_dist": 10.0,
            "shape_top_border_label_text": "",
            "shape_bottom_border_label_text": "",
            "shape_qr_payload": "",
        },
        project_root=tmp_path,
    )

    context.resolver.side_effect = original_resolver

    rendered_sources: dict[str, str] = {}

    def fake_render_stl_source(
        source: str,
        target: Path,
    ) -> None:
        rendered_sources[target.name] = source
        target.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        target.write_text(
            "stl",
            encoding="utf-8",
        )

    monkeypatch.setattr(
        extrude,
        "render_stl_source",
        fake_render_stl_source,
    )

    extrude.execute(context)

    data = json.loads(extrusion_manifest.read_text(encoding="utf-8"))

    components = {component["name"]: component for component in data["components"]}

    assert "base" in components
    assert "border-fill" in components

    border_fill_path = components["border-fill"]["path"]

    assert border_fill_path == "border-fill.stl"
    assert border_fill_path in rendered_sources
    assert (extrusion_manifest.parent / border_fill_path).is_file()


@pytest.mark.parametrize(
    "ridge_raise",
    [1.0, -0.5],
    ids=["positive-integrated-ridge", "recessed-integrated-ridge"],
)
def test_integrated_circle_base_subtracts_border_fill_through_full_height(
    ridge_raise: float,
) -> None:
    """
    Integrated circle Base geometry subtracts the registered
    Border Fill footprint through the full Base thickness.

    This must hold for both positive and recessed ridge heights.
    """
    ridge = extrude.RegisteredCircleRidge(
        outer=extrude.RegisteredCircle(
            cx=0.0,
            cy=0.0,
            radius=0.5,
        ),
        inner=extrude.RegisteredCircle(
            cx=0.0,
            cy=0.0,
            radius=0.45,
        ),
    )

    border_fill = extrude.RegisteredArtworkFill(
        outer_boundary={
            "type": "circle",
            "cx": 0.0,
            "cy": 0.0,
            "r": 0.45,
        },
        inner_boundary={
            "type": "circle",
            "cx": 0.0,
            "cy": 0.0,
            "r": 0.35,
        },
    )

    planar_subtraction = extrude._build_artwork_fill_planar_geometry_scad(
        border_fill,
        shape_size=100.0,
    )

    source = extrude._build_integrated_circle_base_scad(
        ridge,
        shape_size=100.0,
        shape_base_raise=2.0,
        shape_outer_ridge_raise=ridge_raise,
        planar_subtraction=planar_subtraction,
    )

    assert "difference()" in source
    assert "linear_extrude(" in source
    assert "circle(r = 45, $fn = 256);" in source
    assert "circle(r = 35, $fn = 256);" in source


def test_integrated_circle_renderer_forwards_border_fill_subtraction(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Integrated circle rendering must forward the planar
    subtraction to Base generation, not merely create a
    separate Border Fill component.
    """
    ridge = extrude.RegisteredCircleRidge(
        outer=extrude.RegisteredCircle(
            cx=0.0,
            cy=0.0,
            radius=0.5,
        ),
        inner=extrude.RegisteredCircle(
            cx=0.0,
            cy=0.0,
            radius=0.45,
        ),
    )

    rendered: dict[str, str] = {}

    def fake_render(source: str, path: Path) -> None:
        rendered[path.name] = source
        path.write_bytes(b"test-stl")

    monkeypatch.setattr(
        extrude,
        "render_stl_source",
        fake_render,
    )

    subtraction = "circle(r = 12.345);"

    extrude._render_integrated_circle_ridge_components(
        ridge,
        tmp_path,
        shape_size=100.0,
        shape_base_raise=2.0,
        shape_outer_ridge_raise=1.0,
        planar_subtraction=subtraction,
    )

    assert "base.stl" in rendered
    assert subtraction in rendered["base.stl"]


def test_border_fill_subtracts_participating_shape_hole(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Border Fill materialization applies the participating
    Shape Hole to its own physical geometry.
    """
    border_fill = extrude.RegisteredArtworkFill(
        outer_boundary={
            "type": "circle",
            "cx": 0.0,
            "cy": 0.0,
            "r": 0.45,
        },
        inner_boundary={
            "type": "circle",
            "cx": 0.0,
            "cy": 0.0,
            "r": 0.35,
        },
    )

    hole = extrude.create_hole_geometry(
        envelope_bounds=extrude.Bounds(
            min_x=-50.0,
            min_y=-50.0,
            max_x=50.0,
            max_y=50.0,
        ),
        diameter=4.0,
        edge_distance=2.0,
        position=0,
    )

    rendered: dict[str, str] = {}

    def fake_render(source: str, path: Path) -> None:
        rendered[path.name] = source
        path.write_bytes(b"test-stl")

    monkeypatch.setattr(
        extrude,
        "render_stl_source",
        fake_render,
    )

    components = extrude._render_border_fill_component(
        border_fill,
        tmp_path,
        shape_size=100.0,
        shape_base_raise=2.0,
        hole=hole,
    )

    assert components == (("border-fill", "border-fill.stl"),)

    source = rendered["border-fill.stl"]

    assert "difference()" in source
    assert "hole_radius = 2;" in source
    assert "r = hole_radius," in source
    assert "shape_base_raise = 2;" in source
