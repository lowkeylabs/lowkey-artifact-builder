"""Behavioral tests for QR precedence over incorporated registered Artwork.

QR reserves its entire footprint, including its light quiet zone. Shape Compose
must preserve uncovered Artwork and its logical Artifact-color identity.
"""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import Mock

import pytest

from lowkey_artifact_builder.engine import StageContext
from lowkey_artifact_builder.model.models.shape.stages import compose, extrude

SVG = "http://www.w3.org/2000/svg"


def _svg(path: Path, rectangles: list[tuple[float, float, float, float]]) -> None:
    root = ET.Element(f"{{{SVG}}}svg", {"viewBox": "-0.5 -0.5 1 1"})
    for x, y, width, height in rectangles:
        ET.SubElement(
            root,
            f"{{{SVG}}}rect",
            {"x": str(x), "y": str(y), "width": str(width), "height": str(height)},
        )
    ET.ElementTree(root).write(path, encoding="unicode", xml_declaration=True)


def _artwork(tmp_path: Path) -> Path:
    source = tmp_path / "source"
    source.mkdir()
    # The envelope fits the complete square within the Shape's placement circle.
    # A centered QR crosses two colors; the right-hand component is untouched.
    _svg(source / "envelope.svg", [(-0.5, -0.5, 1.0, 1.0)])
    _svg(source / "color-1.svg", [(-0.45, -0.12, 0.65, 0.24)])
    _svg(source / "color-2.svg", [(-0.1, -0.4, 0.2, 0.8)])
    _svg(source / "color-3.svg", [(0.3, 0.2, 0.12, 0.12)])
    products = []
    for index, rgb in enumerate(((220, 20, 20), (20, 180, 20), (20, 20, 220)), 1):
        products.append(
            {
                "index": index,
                "path": f"color-{index}.svg",
                "artifact_color": {
                    "index": index,
                    "rgb": {"red": rgb[0], "green": rgb[1], "blue": rgb[2]},
                },
            }
        )
    manifest = source / "vector.json"
    manifest.write_text(
        json.dumps({"registered_extent": 1.0, "envelope": "envelope.svg", "products": products}),
        encoding="utf-8",
    )
    return manifest


def _compose(tmp_path: Path, *, payload: str) -> tuple[Path, dict]:
    directory = tmp_path / ("with_qr" if payload else "without_qr")
    directory.mkdir()
    structure = directory / "structure.svg"
    _svg(structure, [])
    # Shape structure must have a circle as its structural boundary.
    root = ET.parse(structure).getroot()
    ET.SubElement(root, f"{{{SVG}}}circle", {"cx": "0", "cy": "0", "r": "0.5"})
    ET.ElementTree(root).write(structure, encoding="unicode", xml_declaration=True)

    manifest = directory / "products.json"
    values = {
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
        "shape_top_border_label_text": "",
        "shape_bottom_border_label_text": "",
        "shape_qr_payload": payload,
        "shape_qr_size": 30.0,
        "shape_qr_alignment": "centered",
        "shape_qr_position": 0.0,
    }
    context = Mock(spec=StageContext)
    vector = tmp_path / "source" / "vector.json"
    context.input.side_effect = {
        "structure.structure": structure,
        "artwork.vector.manifest": vector,
    }.__getitem__
    context.has_input.side_effect = lambda name: name == "artwork.vector.manifest"
    context.output.side_effect = {
        "composition": directory / "composition.svg",
        "manifest": manifest,
    }.__getitem__
    context.resolver.side_effect = values.__getitem__
    compose.execute(context)
    return manifest, json.loads(manifest.read_text(encoding="utf-8"))


def _components(manifest: Path, data: dict) -> dict[int, tuple[Path, dict]]:
    return {
        component["index"]: (
            manifest.parent / component["path"],
            component["artifact_color"],
        )
        for component in data["artwork"]["components"]
    }


def test_qr_reserves_full_footprint_and_preserves_uncovered_artwork(
    tmp_path: Path,
) -> None:
    """
    Compose registers QR precedence without modifying Artwork geometry.

    The complete rounded QR footprint, including its quiet zone, is
    registered as an Artwork exclusion for downstream extrusion.

    All Artwork components retain their original registered geometry,
    logical color identity, and fitting transform.
    """
    _artwork(tmp_path)

    original_manifest, original = _compose(
        tmp_path,
        payload="",
    )
    qr_manifest, with_qr = _compose(
        tmp_path,
        payload="https://lowkeylabs.com",
    )

    footprint = with_qr["qr"]["footprint"]

    assert footprint["type"] == "rounded_rect"
    assert footprint["width"] == pytest.approx(0.3)
    assert footprint["height"] == pytest.approx(0.3)
    assert footprint["corner_radius"] == pytest.approx(0.01)

    assert with_qr["qr"]["quiet_zone_modules"] == 2
    assert set(with_qr["qr"]["components"]) == {
        "qr-dark",
        "qr-light",
    }

    before = _components(original_manifest, original)
    after = _components(qr_manifest, with_qr)

    assert set(before) == set(after) == {1, 2, 3}

    # QR participation must not change Artwork registration or fitting.
    assert with_qr["artwork"]["transform"] == original["artwork"]["transform"]
    assert with_qr["composition"] == original["composition"]

    # Compose must register the complete QR exclusion for Extrude.
    exclusions = with_qr["artwork"]["exclusions"]

    assert len(exclusions) == 1

    exclusion = exclusions[0]

    assert exclusion["type"] == "rounded_rect"

    for key in ("x", "y", "width", "height", "corner_radius"):
        assert exclusion[key] == pytest.approx(footprint[key])

    # No QR means no Artwork exclusions.
    assert not original["artwork"].get("exclusions", [])

    # Compose must preserve all registered Artwork components.
    # Exclusion is a downstream dimensionalization responsibility.
    for index in (1, 2, 3):
        before_path, before_color = before[index]
        after_path, after_color = after[index]

        assert before_color == after_color
        assert before_path.is_file()
        assert after_path.is_file()

        assert before_path.read_bytes() == after_path.read_bytes()


def test_qr_does_not_rewrite_unaffected_artwork(
    tmp_path: Path,
) -> None:
    """Artwork wholly outside the footprint keeps its registered geometry."""
    _artwork(tmp_path)
    original_manifest, original = _compose(tmp_path, payload="")
    clipped_manifest, clipped = _compose(tmp_path, payload="https://lowkeylabs.com")

    before = _components(original_manifest, original)
    after = _components(clipped_manifest, clipped)
    assert after[3][1] == before[3][1]
    assert after[3][0].read_bytes() == before[3][0].read_bytes()
    assert clipped["artwork"]["transform"] == original["artwork"]["transform"]
    assert clipped["composition"] == original["composition"]


@pytest.mark.parametrize("raise_style", ["raised", "inlaid"])
def test_extrude_excludes_qr_footprint_from_artwork_components(
    tmp_path: Path,
    raise_style: str,
) -> None:
    """
    Extrude must subtract the complete registered QR footprint
    from each Artwork component before dimensionalization.

    The exclusion must apply to raised and inlaid Artwork alike.
    """
    _artwork(tmp_path)

    composition_manifest, composition = _compose(
        tmp_path,
        payload="https://lowkeylabs.com",
    )

    artwork = composition["artwork"]
    exclusions = artwork["exclusions"]

    assert len(exclusions) == 1
    assert exclusions[0]["type"] == "rounded_rect"

    components = _components(composition_manifest, composition)
    transform = artwork["transform"]
    extent = artwork["registered_extent"]

    for index in (1, 2, 3):
        component_path, _ = components[index]

        scad = extrude._build_artwork_component_scad(
            str(component_path),
            shape_size=100.0,
            shape_base_raise=2.0,
            shape_artwork_raise=0.6,
            shape_raise_style=raise_style,
            artwork_registered_width=float(extent["width"]),
            artwork_registered_height=float(extent["height"]),
            artwork_scale=float(transform["scale"]),
            artwork_translate_x=float(transform["translate_x"]),
            artwork_translate_y=float(transform["translate_y"]),
            exclusions=exclusions,
        )

        # The QR exclusion must be part of the planar Artwork
        # construction, rather than a separate overlapping solid.
        assert "difference()" in scad

        # Physical QR footprint: 30 mm square, 1 mm corner radius.
        # The footprint must be converted from registered Shape space.
        assert "30" in scad
        assert "1" in scad

        assert "linear_extrude" in scad

        if raise_style == "raised":
            assert "artwork_z_offset = 2" in scad
            assert "artwork_height = 0.6" in scad
        else:
            assert "artwork_z_offset = 0" in scad
            assert "artwork_height = 2" in scad


def test_inlaid_artwork_union_respects_qr_exclusion(
    tmp_path: Path,
) -> None:
    """
    The inlaid Base must subtract only the Artwork geometry
    remaining after QR exclusion.

    Otherwise, the Base and Artwork partitions would disagree
    about which material occupies the QR footprint.
    """
    _artwork(tmp_path)

    composition_manifest, composition = _compose(
        tmp_path,
        payload="https://lowkeylabs.com",
    )

    artwork = composition["artwork"]
    exclusions = artwork["exclusions"]

    assert len(exclusions) == 1

    scad = extrude._build_artwork_planar_union_scad(
        artwork,
        composition_manifest.parent,
        shape_size=100.0,
    )

    # The registered Artwork union must be clipped by the same
    # QR exclusion used for individual Artwork components.
    assert "difference()" in scad

    # The registered 30 mm rounded-square footprint must
    # participate in the subtraction.
    assert "30" in scad

    # The union must still contain the registered Artwork
    # components rather than discarding Artwork entirely.
    assert "union()" in scad

    for index in (1, 2, 3):
        component_path, _ = _components(
            composition_manifest,
            composition,
        )[index]

        assert component_path.name in scad
