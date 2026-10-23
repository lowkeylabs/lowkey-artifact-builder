"""Behavioral RED tests for SHAPE Artwork Region Fill."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from lowkey_artifact_builder.engine import StageContext
from lowkey_artifact_builder.model.models.shape.stages import compose, extrude, package
from tests.support.model_parameters import (
    configure_mock_resolver,
    model_test_resolver,
)

SVG_NS = "http://www.w3.org/2000/svg"


def _compose(
    tmp_path: Path,
    *,
    outer_width: float = 0.0,
    inner_width: float = 0.0,
) -> tuple[Path, Path, Path]:
    structure = tmp_path / "structure.svg"
    composition = tmp_path / "composition.svg"
    manifest = tmp_path / "products.json"
    artifact = tmp_path / "artifact.svg"

    structure.write_text(
        f'<svg xmlns="{SVG_NS}" viewBox="-0.5 -0.5 1 1">'
        '<circle id="shape-boundary" cx="0" cy="0" r="0.5"/></svg>',
        encoding="utf-8",
    )

    inputs = {"structure.structure": structure}
    outputs = {
        "composition": composition,
        "manifest": manifest,
        "artifact": artifact,
    }

    context = Mock(spec=StageContext)
    context.input.side_effect = inputs.__getitem__
    context.has_input.side_effect = inputs.__contains__
    context.output.side_effect = outputs.__getitem__

    resolver = model_test_resolver(
        "shape",
        overrides={
            "shape_size": 100.0,
            "shape_outer_ridge_width": outer_width,
            "shape_outer_ridge_style": "integrated",
            "shape_inner_ridge_width": inner_width,
            "shape_inner_to_outer_ridge_dist": 10.0,
            "shape_top_border_label_text": "",
            "shape_bottom_border_label_text": "",
            "shape_qr_payload": "",
            "shape_artwork_fill_raise": 0.0,
        },
        project_root=tmp_path,
    )

    configure_mock_resolver(context, resolver)

    compose.execute(context)

    return composition, manifest, artifact


@pytest.mark.parametrize(
    ("outer_width", "inner_width", "expected_radius"),
    [
        (0.0, 0.0, 0.5),
        (5.0, 0.0, 0.45),
        (5.0, 2.0, 0.33),
    ],
    ids=["no-ridges", "outer-only", "inner-ridge"],
)
def test_region_uses_registered_interior_without_artwork(
    tmp_path: Path,
    outer_width: float,
    inner_width: float,
    expected_radius: float,
) -> None:
    """
    Artwork Region Fill exists without Artwork and follows the
    authoritative registered Shape interior boundary.
    """
    composition, manifest, artifact = _compose(
        tmp_path,
        outer_width=outer_width,
        inner_width=inner_width,
    )

    expected = compose.registered_interior_region(composition)

    assert float(expected.get("r", "nan")) == pytest.approx(
        expected_radius,
    )

    data = json.loads(manifest.read_text(encoding="utf-8"))
    region = data["artwork_region_fill"]
    boundary = region["boundary"]

    assert boundary["type"] == "circle"
    assert boundary["cx"] == pytest.approx(0.0)
    assert boundary["cy"] == pytest.approx(0.0)
    assert boundary["r"] == pytest.approx(expected_radius)

    root = ET.parse(artifact).getroot()

    paths = [element for element in root.iter() if element.get("id") == "artwork-region-fill"]

    assert len(paths) == 1
    assert paths[0].get("d")
    assert paths[0].get("stroke") == "none"


def test_region_is_independent_of_existing_artwork_fill(tmp_path: Path) -> None:
    """New background does not activate the optional envelope-based Artwork Fill."""
    _, manifest, _ = _compose(tmp_path)
    data = json.loads(manifest.read_text(encoding="utf-8"))
    assert data["artwork_region_fill"] is not None
    assert data.get("artwork_fill") is None


@pytest.mark.parametrize("raise_style", ["raised", "inlaid"])
def test_extrude_partitions_full_depth_region_from_base(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    raise_style: str,
) -> None:
    """The central region is independently printable and is removed from Base."""
    composition, composition_manifest, _ = _compose(tmp_path)
    output = tmp_path / "extrude" / "products.json"

    inputs = {
        "compose.composition": composition,
        "compose.manifest": composition_manifest,
    }

    context = Mock(spec=StageContext)
    context.input.side_effect = inputs.__getitem__
    context.has_input.side_effect = inputs.__contains__
    context.output.return_value = output

    resolver = model_test_resolver(
        "shape",
        overrides={"shape_raise_style": raise_style},
        project_root=tmp_path,
    )

    configure_mock_resolver(context, resolver)

    sources: dict[str, str] = {}

    def fake_render(source: str, target: Path) -> None:
        sources[target.name] = source
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"test-stl")

    monkeypatch.setattr(extrude, "render_stl_source", fake_render)

    extrude.execute(context)

    data = json.loads(output.read_text(encoding="utf-8"))
    components = {item["name"]: item["path"] for item in data["components"]}

    assert components["artwork-region-fill"] == "artwork-region-fill.stl"
    assert "base" in components
    assert "artwork-region-fill.stl" in sources
    assert "base.stl" in sources
    assert "difference()" in sources["base.stl"]
    assert "linear_extrude(" in sources["artwork-region-fill.stl"]
    assert "shape_base_raise" in sources["artwork-region-fill.stl"]


@pytest.mark.parametrize("override", [None, "red"], ids=["inherits-base", "independent-color"])
def test_package_resolves_region_color(
    tmp_path: Path,
    override: str | None,
) -> None:
    """Region defaults to resolved Base, or accepts its own physical color."""
    components = tuple(
        package.PhysicalComponent(
            name=name,
            path=tmp_path / f"{name}.stl",
            artifact_color_index=None,
            artifact_color=None,
        )
        for name in ("base", "artwork-region-fill")
    )

    overrides = {"shape_base_color": "black"}

    if override is not None:
        overrides["shape_artwork_region_fill_color"] = override

    context = Mock(spec=StageContext)

    resolver = model_test_resolver(
        "shape",
        overrides=overrides,
        project_root=tmp_path,
    )

    configure_mock_resolver(context, resolver)

    black = Mock(name="black")
    red = Mock(name="red")
    palette = {"black": black, "red": red}

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
    assert colors["artwork-region-fill"] is (red if override else black)


@pytest.mark.parametrize(
    ("outer_width", "inner_width"),
    [
        (0.0, 0.0),
        (5.0, 0.0),
        (5.0, 2.0),
    ],
    ids=["no-ridges", "outer-only", "inner-ridge"],
)
def test_artwork_region_fill_svg_uses_registered_interior(
    tmp_path: Path,
    outer_width: float,
    inner_width: float,
) -> None:
    """
    The canonical SVG contains the Artwork Region Fill as a
    printable planar region bounded by the authoritative Shape interior.
    """
    composition, _, artifact = _compose(
        tmp_path,
        outer_width=outer_width,
        inner_width=inner_width,
    )

    expected = compose.registered_interior_region(composition)

    root = ET.parse(artifact).getroot()

    regions = [element for element in root.iter() if element.get("id") == "artwork-region-fill"]

    assert len(regions) == 1

    region = regions[0]

    assert region.tag == f"{{{compose.SVG_NAMESPACE}}}path"
    assert region.get("fill") != "none"
    assert region.get("stroke") == "none"

    expected_path = compose._svg_boundary_path(expected)

    assert region.get("d") == expected_path


def test_artwork_region_fill_does_not_create_artwork_fill(
    tmp_path: Path,
) -> None:
    """
    The full-depth background region exists independently of the
    optional envelope-based Artwork Fill.
    """
    _, manifest, artifact = _compose(tmp_path)

    data = json.loads(manifest.read_text(encoding="utf-8"))

    assert data["artwork_region_fill"] is not None
    assert data["artwork_fill"] is None

    root = ET.parse(artifact).getroot()

    identifiers = {element.get("id") for element in root.iter() if element.get("id") is not None}

    assert "artwork-region-fill" in identifiers
    assert "artwork-fill" not in identifiers
