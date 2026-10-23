"""Behavioral tests for SHAPE Compose's canonical combined SVG Product."""

# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import Mock

import pytest

from lowkey_artifact_builder.engine import StageContext
from lowkey_artifact_builder.model.models.shape import MODEL
from lowkey_artifact_builder.model.models.shape.stages import compose
from tests.support.model_parameters import model_test_resolver

SVG = "http://www.w3.org/2000/svg"


def _write_artwork(directory: Path) -> Path:
    """Create two registered Artwork components with distinct identities."""
    directory.mkdir(parents=True, exist_ok=True)

    for name, x in (("left", 2), ("right", 8)):
        (directory / f"{name}.svg").write_text(
            f'<svg xmlns="{SVG}" viewBox="0 0 16 16">'
            f'<rect x="{x}" y="3" width="6" height="10"/>'
            "</svg>",
            encoding="utf-8",
        )

    (directory / "envelope.svg").write_text(
        f'<svg xmlns="{SVG}" viewBox="0 0 16 16"><rect x="2" y="3" width="12" height="10"/></svg>',
        encoding="utf-8",
    )

    manifest = directory / "products.json"
    manifest.write_text(
        json.dumps(
            {
                "registered_extent": 16,
                "envelope": "envelope.svg",
                "products": [
                    {
                        "index": index,
                        "path": f"{name}.svg",
                        "artifact_color": {
                            "index": index,
                            "rgb": {
                                "red": shade,
                                "green": shade,
                                "blue": shade,
                            },
                        },
                    }
                    for index, name, shade in (
                        (1, "left", 240),
                        (2, "right", 20),
                    )
                ],
            }
        ),
        encoding="utf-8",
    )
    return manifest


def _run_compose(
    directory: Path,
    *,
    artwork_manifest: Path | None = None,
    shape_size: float = 80.0,
    offset_x: float = 0.0,
    offset_y: float = 0.0,
    scale: float = 1.0,
    outer_ridge_width: float = 0.0,
    top_label: str = "",
    bottom_label: str = "",
    qr_payload: str = "",
    qr_size: float = 20.0,
) -> tuple[Path, Path, Path]:
    """Execute SHAPE Compose with real registered inputs."""
    directory.mkdir(parents=True, exist_ok=True)

    structure = directory / "structure.svg"
    structure.write_text(
        f'<svg xmlns="{SVG}" viewBox="-0.5 -0.5 1 1">'
        '<circle id="shape-boundary" cx="0" cy="0" r="0.5"/>'
        "</svg>",
        encoding="utf-8",
    )

    composition = directory / "composition.svg"
    manifest = directory / "products.json"
    artifact = directory / "artifact.svg"

    context = Mock(spec=StageContext)

    inputs = {"structure.structure": structure}
    if artwork_manifest is not None:
        inputs["artwork.vector.manifest"] = artwork_manifest

    context.input.side_effect = inputs.__getitem__
    context.has_input.side_effect = inputs.__contains__

    context.output.side_effect = {
        "composition": composition,
        "manifest": manifest,
        "artifact": artifact,
    }.__getitem__

    resolver = model_test_resolver(
        "shape",
        overrides={
            "shape_size": shape_size,
            "shape_outer_ridge_width": outer_ridge_width,
            "shape_outer_ridge_style": "integrated",
            "shape_inner_ridge_width": 0.0,
            "shape_inner_to_outer_ridge_dist": 10.0,
            "shape_border_label_width": 1.0,
            "shape_border_label_max_glyph_height": 5.0,
            "shape_border_label_arc_degrees": 140.0,
            "shape_border_label_end_margin": 1.0,
            "shape_border_label_font_family": "DejaVu Sans",
            "shape_top_border_label_text": top_label,
            "shape_bottom_border_label_text": bottom_label,
            "shape_qr_payload": qr_payload,
            "shape_qr_size": qr_size,
            "shape_qr_alignment": "centered",
            "shape_qr_position": 0.0,
            "shape_artwork_offset_x": offset_x,
            "shape_artwork_offset_y": offset_y,
            "shape_artwork_scale": scale,
        },
        project_root=directory,
    )

    context.resolver.side_effect = resolver

    compose.execute(context)

    return artifact, composition, manifest


def _svg_root(path: Path) -> ET.Element:
    assert path.is_file(), f"Missing canonical Compose SVG: {path}"
    root = ET.parse(path).getroot()
    assert root.tag == f"{{{SVG}}}svg"
    return root


def test_compose_declares_canonical_svg_product() -> None:
    stage = next(stage for stage in MODEL.stages if stage.name == "compose")

    products = {product.name: product.path for product in stage.products}

    assert products == {
        "composition": "composition.svg",
        "manifest": "products.json",
        "artifact": "artifact.svg",
    }


def test_compose_writes_physically_dimensioned_svg_without_artwork(
    tmp_path: Path,
) -> None:
    artifact, composition, manifest = _run_compose(
        tmp_path / "output",
        shape_size=80.0,
    )

    root = _svg_root(artifact)

    assert composition.is_file()
    assert manifest.is_file()

    assert root.get("width") == "80mm"
    assert root.get("height") == "80mm"

    # The canonical output must contain actual visible manufacturing geometry,
    # not just a collection of construction boundaries.
    visible = [
        element
        for element in root.iter()
        if element.tag
        in {
            f"{{{SVG}}}path",
            f"{{{SVG}}}rect",
            f"{{{SVG}}}circle",
            f"{{{SVG}}}polygon",
        }
    ]
    assert visible


def test_compose_svg_includes_distinct_registered_artwork_components(
    tmp_path: Path,
) -> None:
    source = _write_artwork(tmp_path / "source")

    artifact, _, manifest_path = _run_compose(
        tmp_path / "output",
        artwork_manifest=source,
        offset_x=4.0,
        offset_y=3.0,
        scale=0.6,
    )

    root = _svg_root(artifact)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert root.get("width") == "80mm"
    assert root.get("height") == "80mm"

    # The SVG must preserve both Artwork color components as separate
    # identifiable regions, rather than flattening them into one shape.
    components = [
        element for element in root.iter() if element.get("id") in {"artwork-1", "artwork-2"}
    ]
    assert {element.get("id") for element in components} == {
        "artwork-1",
        "artwork-2",
    }

    # The authoritative registered transform is still persisted for
    # downstream consumers; SVG export must not replace that contract.
    transform = manifest["artwork"]["transform"]
    assert transform["scale"] > 0.0
    assert transform["translate_x"] != 0.0
    assert transform["translate_y"] != 0.0


def test_compose_svg_has_no_opaque_solid_base(
    tmp_path: Path,
) -> None:
    source = _write_artwork(tmp_path / "source")

    artifact, _, _ = _run_compose(
        tmp_path / "output",
        artwork_manifest=source,
    )

    root = _svg_root(artifact)

    # The full Shape body is not a filled background in the 2D export.
    # An explicit perimeter outline is permitted.
    for element in root.iter():
        if element.get("id") == "shape-boundary":
            assert element.get("fill", "none") == "none"

    assert not any(element.get("id") == "base" for element in root.iter())


def test_compose_svg_ridge_is_filled_region(
    tmp_path: Path,
) -> None:
    """
    An enabled outer ridge must produce a filled planar region
    with an unfilled interior, not construction outlines.
    """
    artifact, _, _ = _run_compose(
        tmp_path / "output",
        outer_ridge_width=2.0,
    )

    root = _svg_root(artifact)

    ridge_regions = [element for element in root.iter() if element.get("id") == "outer-ridge"]

    assert len(ridge_regions) == 1

    ridge = ridge_regions[0]

    assert ridge.tag == f"{{{SVG}}}path"
    assert ridge.get("fill") not in (
        None,
        "none",
        "transparent",
    )

    # The outer ridge is an annular region, not a solid disc.
    assert ridge.get("fill-rule") == "evenodd"

    # Construction boundaries must not appear as visible
    # manufacturing geometry.
    construction_ids = {
        "ridge-inner-boundary",
        "inner-ridge-outer-boundary",
        "inner-ridge-inner-boundary",
        "border-label-top-baseline",
        "border-label-bottom-baseline",
        "border-label-inner-boundary",
    }

    assert not any(element.get("id") in construction_ids for element in root.iter())


def test_compose_svg_preserves_registered_artwork_colors(
    tmp_path: Path,
) -> None:
    """
    Each registered Artwork component must retain its own
    RGB identity and authoritative placement in the SVG.
    """
    artwork_manifest = _write_artwork(tmp_path / "artwork")

    artifact, _, _ = _run_compose(
        tmp_path / "output",
        artwork_manifest=artwork_manifest,
    )

    root = _svg_root(artifact)

    components = {
        element.get("id"): element
        for element in root.iter(f"{{{SVG}}}g")
        if element.get("id") in {"artwork-1", "artwork-2"}
    }

    assert set(components) == {
        "artwork-1",
        "artwork-2",
    }

    def effective_fill(element: ET.Element) -> str | None:
        fill = element.get("fill")

        if fill is not None:
            return fill.lower()

        style = element.get("style", "")

        for declaration in style.split(";"):
            name, separator, value = declaration.partition(":")

            if separator and name.strip() == "fill":
                return value.strip().lower()

        return None

    assert effective_fill(components["artwork-1"]) == "#f0f0f0"
    assert effective_fill(components["artwork-2"]) == "#141414"

    # Both components must use the same registered placement.
    assert components["artwork-1"].get("transform") == components["artwork-2"].get("transform")


@pytest.mark.slow
def test_compose_svg_includes_registered_border_label_geometry(
    tmp_path: Path,
) -> None:
    """
    Participating Border Labels must appear as portable vector
    geometry in the canonical SVG.

    The SVG must reuse the registered glyph geometry persisted
    by Compose rather than exporting construction baselines.
    """
    artifact, _, manifest_path = _run_compose(
        tmp_path / "output",
        shape_size=100.0,
        outer_ridge_width=2.0,
        top_label="Holiday House Tour",
        bottom_label="Fan District RVA",
    )

    root = _svg_root(artifact)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    labels = manifest["border_labels"]

    for position in ("top", "bottom"):
        component = labels[position]
        assert component is not None

        source = manifest_path.parent / component["path"]
        assert source.is_file()

        source_root = ET.parse(source).getroot()
        source_paths = list(source_root.iter(f"{{{SVG}}}path"))

        assert source_paths, f"Missing registered {position} glyph paths"

        exported = next(
            (element for element in root.iter() if element.get("id") == f"{position}-border-label"),
            None,
        )

        assert exported is not None
        assert list(exported.iter(f"{{{SVG}}}path"))

    # Construction geometry is not manufacturing geometry.
    construction_ids = {
        "border-label-top-baseline",
        "border-label-bottom-baseline",
        "border-label-inner-boundary",
        "top-border-label-path",
        "bottom-border-label-path",
    }

    assert not any(element.get("id") in construction_ids for element in root.iter())

    # Text must already be converted into portable paths.
    assert not list(root.iter(f"{{{SVG}}}text"))
    assert not list(root.iter(f"{{{SVG}}}textPath"))


def test_compose_svg_includes_registered_qr_components_without_artwork(
    tmp_path: Path,
) -> None:
    """
    QR is Shape-owned and must appear in the canonical SVG
    even when no incorporated Artwork exists.

    Dark and light geometry retain independent identities.
    """
    artifact, _, manifest_path = _run_compose(
        tmp_path / "output",
        shape_size=100.0,
        qr_payload="https://lowkeylabs.com",
        qr_size=30.0,
    )

    root = _svg_root(artifact)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert manifest["artwork"] is None

    qr = manifest["qr"]

    assert set(qr["components"]) == {"qr-dark", "qr-light"}

    for name in ("qr-dark", "qr-light"):
        source = manifest_path.parent / qr["components"][name]["path"]

        assert source.is_file()

        exported = next(
            (element for element in root.iter() if element.get("id") == name),
            None,
        )

        assert exported is not None

        geometry = [
            element
            for element in exported.iter()
            if element.tag
            in {
                f"{{{SVG}}}path",
                f"{{{SVG}}}rect",
                f"{{{SVG}}}circle",
                f"{{{SVG}}}polygon",
            }
        ]

        assert geometry, f"Missing exported {name} geometry"

    footprint = qr["footprint"]

    assert footprint["width"] == pytest.approx(0.3)
    assert footprint["height"] == pytest.approx(0.3)

    assert root.get("width") == "100mm"
    assert root.get("height") == "100mm"

    assert not any(element.get("id") == "base" for element in root.iter())


def test_compose_svg_qr_precedence_preserves_artwork_registration(
    tmp_path: Path,
) -> None:
    """
    QR must reserve its complete footprint, including the
    quiet zone, against underlying Artwork in the SVG.

    Artwork component identities, colors, and placement
    remain authoritative.
    """
    artwork_manifest = _write_artwork(tmp_path / "source")

    artifact, _, manifest_path = _run_compose(
        tmp_path / "output",
        artwork_manifest=artwork_manifest,
        shape_size=100.0,
        qr_payload="https://lowkeylabs.com",
        qr_size=30.0,
    )

    root = _svg_root(artifact)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    artwork = manifest["artwork"]
    qr = manifest["qr"]

    assert artwork is not None
    assert len(artwork["exclusions"]) == 1

    exclusion = artwork["exclusions"][0]
    footprint = qr["footprint"]

    for key in ("x", "y", "width", "height", "corner_radius"):
        assert exclusion[key] == pytest.approx(footprint[key])

    groups = {
        element.get("id"): element
        for element in root.iter(f"{{{SVG}}}g")
        if element.get("id")
        in {
            "artwork-1",
            "artwork-2",
            "qr-dark",
            "qr-light",
        }
    }

    assert set(groups) == {
        "artwork-1",
        "artwork-2",
        "qr-dark",
        "qr-light",
    }

    assert groups["artwork-1"].get("fill") == "#f0f0f0"
    assert groups["artwork-2"].get("fill") == "#141414"

    assert groups["artwork-1"].get("transform") == groups["artwork-2"].get("transform")

    # The QR footprint must actually mask or clip the
    # underlying Artwork, not merely cover it visually
    # with an opaque rectangle.
    artwork_group = next(
        element for element in root.iter(f"{{{SVG}}}g") if element.get("id") == "artwork"
    )

    masking = [
        element
        for element in (artwork_group, *artwork_group.iter())
        if element.get("clip-path") or element.get("mask")
    ]

    assert masking, "QR precedence must exclude the complete QR footprint from exported Artwork."


def test_compose_svg_artwork_color_overrides_conflicting_source_fill(
    tmp_path: Path,
) -> None:
    """
    Canonical SHAPE SVG must use registered Artwork RGB even when
    incorporated SVG geometry declares a conflicting fill.

    Source geometry, transforms, and fill rules remain unchanged.
    """
    artwork_manifest = _write_artwork(tmp_path / "artwork")

    # Simulate registered SVG layers with Inkscape-authored black fills.
    for name in ("left", "right"):
        source = artwork_manifest.parent / f"{name}.svg"

        source.write_text(
            (
                f'<svg xmlns="{SVG}" viewBox="0 0 16 16">'
                '<g id="source-group">'
                '<path id="source-path" '
                'style="fill:#000000;fill-rule:evenodd" '
                'd="M 2 3 H 8 V 13 H 2 Z"/>'
                "</g>"
                "</svg>"
            ),
            encoding="utf-8",
        )

    artifact, _, _ = _run_compose(
        tmp_path / "output",
        artwork_manifest=artwork_manifest,
    )

    root = _svg_root(artifact)

    expected_colors = {
        "artwork-1": "#f0f0f0",
        "artwork-2": "#141414",
    }

    components = {
        element.get("id"): element
        for element in root.iter(f"{{{SVG}}}g")
        if element.get("id") in expected_colors
    }

    assert set(components) == set(expected_colors)

    for component_id, expected_color in expected_colors.items():
        group = components[component_id]

        assert group.get("fill") == expected_color

        paths = list(group.iter(f"{{{SVG}}}path"))
        assert len(paths) == 1

        path = paths[0]

        style = dict(
            declaration.strip().split(":", 1)
            for declaration in path.get("style", "").split(";")
            if ":" in declaration
        )

        # A source path's explicit fill must not override
        # the registered Artifact color.
        effective_fill = style.get(
            "fill",
            path.get("fill", group.get("fill")),
        )

        assert effective_fill == expected_color

        # Recoloring must not alter geometry or fill rules.
        assert path.get("d") == "M 2 3 H 8 V 13 H 2 Z"

        assert (
            style.get(
                "fill-rule",
                path.get("fill-rule"),
            )
            == "evenodd"
        )

    # Both components retain the same registered placement.
    assert components["artwork-1"].get("transform") == components["artwork-2"].get("transform")
