"""
Behavioral tests for SHAPE surface-region material partitioning.

Surface fills are independently printable physical components.
Inlaid foreground geometry must replace, rather than overlap,
the corresponding background material.

These tests preserve the existing Artwork placement policy.
"""

# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from lowkey_artifact_builder.engine import StageContext
from lowkey_artifact_builder.model.models.shape.stages import (
    compose,
    extrude,
)
from tests.support.model_parameters import model_test_resolver

SVG = "http://www.w3.org/2000/svg"


def _compose(
    directory: Path,
) -> tuple[Path, Path]:
    """
    Compose a circular SHAPE with independently registered
    Border Fill and Artwork Region Fill.

    No incorporated Artwork participates.
    """
    directory.mkdir(parents=True, exist_ok=True)

    structure = directory / "structure.svg"
    composition = directory / "composition.svg"
    manifest = directory / "products.json"
    artifact = directory / "artifact.svg"

    structure.write_text(
        f'<svg xmlns="{SVG}" viewBox="-0.5 -0.5 1 1">'
        '<circle id="shape-boundary" cx="0" cy="0" r="0.5"/>'
        "</svg>",
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
            "shape_outer_ridge_width": 5.0,
            "shape_outer_ridge_style": "integrated",
            "shape_inner_ridge_width": 2.0,
            "shape_inner_to_outer_ridge_dist": 10.0,
            "shape_top_border_label_text": "",
            "shape_bottom_border_label_text": "",
            "shape_qr_payload": "",
        },
        project_root=directory,
    )

    compose.execute(context)
    return composition, manifest


def _extrude(
    directory: Path,
    composition: Path,
    composition_manifest: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    raise_style: str,
) -> dict[str, str]:
    """
    Execute the real SHAPE Extrude stage while capturing OpenSCAD
    source instead of invoking the external renderer.
    """
    output = directory / "extrude" / "products.json"

    inputs = {
        "compose.composition": composition,
        "compose.manifest": composition_manifest,
    }

    context = Mock(spec=StageContext)
    context.input.side_effect = inputs.__getitem__
    context.has_input.side_effect = inputs.__contains__
    context.output.return_value = output

    context.resolver.side_effect = model_test_resolver(
        "shape",
        overrides={
            "shape_size": 100.0,
            "shape_raise_style": raise_style,
            "shape_outer_ridge_width": 5.0,
            "shape_outer_ridge_style": "integrated",
            "shape_inner_ridge_width": 2.0,
            "shape_inner_to_outer_ridge_dist": 10.0,
            "shape_top_border_label_text": "",
            "shape_bottom_border_label_text": "",
            "shape_qr_payload": "",
        },
        project_root=directory,
    )

    sources: dict[str, str] = {}

    def fake_render(
        source: str,
        target: Path,
    ) -> None:
        sources[target.name] = source
        target.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        target.write_bytes(b"test-stl")

    monkeypatch.setattr(
        extrude,
        "render_stl_source",
        fake_render,
    )

    extrude.execute(context)

    data = json.loads(output.read_text(encoding="utf-8"))
    names = {component["name"] for component in data["components"]}

    assert "base" in names
    assert "border-fill" in names
    assert "artwork-region-fill" in names

    return sources


def test_surface_regions_remain_independent_without_foreground(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Both surface regions exist as separate physical components
    even when Artwork and Border Labels are absent.
    """
    composition, manifest = _compose(tmp_path / "compose")

    sources = _extrude(
        tmp_path,
        composition,
        manifest,
        monkeypatch,
        raise_style="inlaid",
    )

    assert "border-fill.stl" in sources
    assert "artwork-region-fill.stl" in sources

    assert "linear_extrude(" in sources["border-fill.stl"]
    assert "linear_extrude(" in sources["artwork-region-fill.stl"]


@pytest.mark.parametrize(
    "raise_style",
    ["raised", "inlaid"],
)
def test_surface_region_components_preserve_base_partition(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    raise_style: str,
) -> None:
    """
    The Base must not occupy the same full-depth volumes
    assigned to independently printable surface regions.
    """
    composition, manifest = _compose(tmp_path / "compose")

    sources = _extrude(
        tmp_path,
        composition,
        manifest,
        monkeypatch,
        raise_style=raise_style,
    )

    base = sources["base.stl"]

    assert "difference()" in base
    assert "linear_extrude(" in sources["border-fill.stl"]
    assert "linear_extrude(" in sources["artwork-region-fill.stl"]


def test_inlaid_border_label_displaces_border_fill(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    An inlaid Border Label occupies material within Border Fill.

    Its physical footprint must be subtracted from the Border Fill
    component, preventing overlapping full-depth printable solids.
    """
    output_directory = tmp_path / "output"
    output_directory.mkdir()

    fill = extrude.RegisteredArtworkFill(
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

    # Represents the planar footprint of an independently colored
    # inlaid foreground component within the Border Fill region.
    foreground = "translate([0, 40]) {\n    square([12, 4], center = true);\n}\n"

    sources: dict[str, str] = {}

    def fake_render(
        source: str,
        target: Path,
    ) -> None:
        sources[target.name] = source
        target.write_bytes(b"test-stl")

    monkeypatch.setattr(
        extrude,
        "render_stl_source",
        fake_render,
    )

    extrude._render_border_fill_component(
        fill,
        output_directory,
        shape_size=100.0,
        shape_base_raise=2.0,
        hole=None,
        planar_subtraction=foreground,
    )

    source = sources["border-fill.stl"]

    assert "difference()" in source
    assert "translate([0, 40]) {" in source
    assert "square([12, 4], center = true);" in source
    assert "linear_extrude(" in source


def test_artwork_region_supports_inlaid_foreground_subtraction(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    The existing Artwork Region Fill contract subtracts
    inlaid foreground footprints from its physical material.
    """
    output_directory = tmp_path / "output"
    output_directory.mkdir()

    boundary: dict[str, object] = {
        "type": "circle",
        "cx": 0.0,
        "cy": 0.0,
        "r": 0.35,
    }

    foreground = "circle(r = 10, $fn = 64);\n"

    sources: dict[str, str] = {}

    def fake_render(
        source: str,
        target: Path,
    ) -> None:
        sources[target.name] = source
        target.write_bytes(b"test-stl")

    monkeypatch.setattr(
        extrude,
        "render_stl_source",
        fake_render,
    )

    extrude._render_artwork_region_fill_component(
        boundary,
        output_directory,
        shape_size=100.0,
        shape_base_raise=2.0,
        hole=None,
        planar_subtraction=foreground,
    )

    source = sources["artwork-region-fill.stl"]

    assert "difference()" in source
    assert "circle(r = 35, $fn = 256);" in source
    assert "circle(r = 10, $fn = 64);" in source
    assert "linear_extrude(" in source


@pytest.mark.parametrize(
    ("raise_style", "expects_subtraction"),
    [
        ("inlaid", True),
        ("raised", False),
    ],
)
def test_border_label_partitioning_reaches_border_fill(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    raise_style: str,
    expects_subtraction: bool,
) -> None:
    """
    Extrude forwards a composed Border Label's planar footprint
    into Border Fill subtraction when the label is inlaid.

    Raised Border Labels must not subtract full-depth material
    from Border Fill.
    """
    directory = tmp_path / "compose"
    directory.mkdir(parents=True)

    structure = directory / "structure.svg"
    composition = directory / "composition.svg"
    manifest = directory / "products.json"
    artifact = directory / "artifact.svg"

    structure.write_text(
        f'<svg xmlns="{SVG}" viewBox="-0.5 -0.5 1 1">'
        '<circle id="shape-boundary" cx="0" cy="0" r="0.5"/>'
        "</svg>",
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

    parameters = {
        "shape_size": 100.0,
        "shape_outer_ridge_width": 5.0,
        "shape_outer_ridge_style": "integrated",
        "shape_inner_ridge_width": 2.0,
        "shape_inner_to_outer_ridge_dist": 10.0,
        "shape_top_border_label_text": "TEST",
        "shape_bottom_border_label_text": "",
        "shape_border_label_font_family": "Liberation Sans",
        "shape_qr_payload": "",
    }

    context.resolver.side_effect = model_test_resolver(
        "shape",
        overrides=parameters,
        project_root=directory,
    )

    compose.execute(context)

    composed = json.loads(manifest.read_text(encoding="utf-8"))

    assert composed.get("border_fill") is not None

    assert composed["border_labels"]["top"] is not None
    assert composed["border_labels"]["bottom"] is None

    extrusion_manifest = tmp_path / "extrude" / "products.json"

    extrusion_inputs = {
        "compose.composition": composition,
        "compose.manifest": manifest,
    }

    extrusion_context = Mock(spec=StageContext)
    extrusion_context.input.side_effect = extrusion_inputs.__getitem__
    extrusion_context.has_input.side_effect = extrusion_inputs.__contains__
    extrusion_context.output.return_value = extrusion_manifest

    extrusion_context.resolver.side_effect = model_test_resolver(
        "shape",
        overrides={
            **parameters,
            "shape_raise_style": raise_style,
            "shape_top_border_label_raise": 1.0,
        },
        project_root=directory,
    )

    rendered_sources: dict[str, str] = {}

    def fake_render(
        source: str,
        target: Path,
    ) -> None:
        rendered_sources[target.name] = source
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"test-stl")

    monkeypatch.setattr(
        extrude,
        "render_stl_source",
        fake_render,
    )

    extrude.execute(extrusion_context)

    assert "border-fill.stl" in rendered_sources

    border_source = rendered_sources["border-fill.stl"]

    # The composed label's registered SVG must be used to
    # construct the inlaid foreground footprint.

    label_path = composed["border_labels"]["top"]["path"]

    assert isinstance(label_path, str)
    assert (manifest.parent / label_path).is_file()

    # The Border Fill always uses difference() to construct
    # its annular geometry. Only an inlaid Border Label should
    # introduce the registered label SVG as an additional
    # subtraction footprint.
    assert "difference()" in border_source

    assert ("import(" in border_source) is expects_subtraction

    assert "linear_extrude(" in border_source
