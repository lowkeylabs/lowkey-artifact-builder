"""QR registration, placement, and Artwork precedence in SHAPE Compose."""

from __future__ import annotations

import json
import math
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import Mock

import pytest

from lowkey_artifact_builder.engine import StageContext
from lowkey_artifact_builder.model.models.shape.stages import compose
from tests.support.model_parameters import (
    configure_mock_resolver,
    model_test_resolver,
)

SVG = "http://www.w3.org/2000/svg"


def _write_structure(path: Path, geometry: str = "circle") -> None:
    if geometry == "circle":
        boundary = '<circle cx="0" cy="0" r="0.5"/>'
    elif geometry == "square":
        boundary = '<rect x="-0.5" y="-0.5" width="1" height="1"/>'
    else:
        raise ValueError(f"Unsupported test geometry: {geometry}")
    path.write_text(
        f'<svg xmlns="{SVG}" viewBox="-0.5 -0.5 1 1">{boundary}</svg>',
        encoding="utf-8",
    )


def _run_compose(
    directory: Path,
    *,
    payload: str,
    qr_size: float = 30.0,
    alignment: str = "centered",
    position: float = 0.0,
    ridge_width: float = 0.0,
    geometry: str = "circle",
    artwork_manifest: Path | None = None,
) -> tuple[Path, dict]:
    directory.mkdir(parents=True, exist_ok=True)
    structure = directory / "structure.svg"
    manifest = directory / "products.json"
    _write_structure(structure, geometry)

    resolver = model_test_resolver(
        "shape",
        overrides={
            "shape_size": 100.0,
            "shape_outer_ridge_width": ridge_width,
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
            "shape_artwork_offset_x": 0.0,
            "shape_artwork_offset_y": 0.0,
            "shape_artwork_scale": 1.0,
            "shape_qr_payload": payload,
            "shape_qr_size": qr_size,
            "shape_qr_alignment": alignment,
            "shape_qr_position": position,
        },
        project_root=directory,
    )
    context = Mock(spec=StageContext)
    inputs = {"structure.structure": structure}
    if artwork_manifest is not None:
        inputs["artwork.vector.manifest"] = artwork_manifest
    context.input.side_effect = inputs.__getitem__
    context.has_input.side_effect = inputs.__contains__
    context.output.side_effect = {
        "composition": directory / "composition.svg",
        "manifest": manifest,
        "artifact": directory / "artifact.svg",
    }.__getitem__
    configure_mock_resolver(context, resolver)
    compose.execute(context)
    return manifest, json.loads(manifest.read_text(encoding="utf-8"))


def _execute_compose(
    tmp_path: Path,
    *,
    payload: str,
    qr_size: float = 30.0,
) -> tuple[Path, dict]:
    return _run_compose(tmp_path, payload=payload, qr_size=qr_size)


def _compose_qr(
    tmp_path: Path,
    *,
    alignment: str,
    position: float = 0.0,
    qr_size: float = 20.0,
    ridge_width: float = 0.0,
    geometry: str = "circle",
) -> dict:
    _, data = _run_compose(
        tmp_path,
        payload="https://lowkeylabs.com",
        qr_size=qr_size,
        alignment=alignment,
        position=position,
        ridge_width=ridge_width,
        geometry=geometry,
    )
    return data["qr"]["footprint"]


def _center(footprint: dict) -> tuple[float, float]:
    return (
        footprint["x"] + footprint["width"] / 2,
        footprint["y"] + footprint["height"] / 2,
    )


def test_empty_qr_payload_does_not_participate(tmp_path: Path) -> None:
    """QR is absent by default and does not require Artwork."""
    _, data = _execute_compose(tmp_path, payload="")
    assert data["artwork"] is None
    assert not data.get("qr")


def test_qr_composition_without_artwork(tmp_path: Path) -> None:
    """A participating QR has two registered semantic components."""
    manifest, data = _execute_compose(tmp_path, payload="https://lowkeylabs.com")
    assert data["artwork"] is None
    qr = data["qr"]
    assert set(qr["components"]) == {"qr-dark", "qr-light"}
    for component in qr["components"].values():
        path = manifest.parent / component["path"]
        assert path.is_file()
        assert path.suffix == ".svg"


def test_qr_size_includes_quiet_zone(tmp_path: Path) -> None:
    """The complete footprint is 30 mm in a 100 mm Shape."""
    _, data = _execute_compose(tmp_path, payload="https://lowkeylabs.com", qr_size=30.0)
    footprint = data["qr"]["footprint"]
    assert footprint["width"] == pytest.approx(0.3)
    assert footprint["height"] == pytest.approx(0.3)
    assert footprint["x"] == pytest.approx(-0.15)
    assert footprint["y"] == pytest.approx(-0.15)
    assert data["qr"]["quiet_zone_modules"] > 0


def test_centered_qr_ignores_position(tmp_path: Path) -> None:
    """Clock angle does not affect centered QR placement."""
    first = _compose_qr(tmp_path, alignment="centered", position=0)
    second = _compose_qr(tmp_path, alignment="centered", position=37)
    assert first == second
    assert _center(first) == pytest.approx((0.0, 0.0))


@pytest.mark.parametrize(
    ("angle", "direction"),
    [
        (0.0, (0.0, -1.0)),
        (90.0, (1.0, 0.0)),
        (180.0, (0.0, 1.0)),
        (-90.0, (-1.0, 0.0)),
        (45.0, (math.sqrt(0.5), -math.sqrt(0.5))),
    ],
)
def test_inner_aligned_qr_uses_clock_direction(
    tmp_path: Path, angle: float, direction: tuple[float, float]
) -> None:
    """The inward-facing edge crosses the interior center."""
    footprint = _compose_qr(tmp_path, alignment="inner-aligned", position=angle)
    cx, cy = _center(footprint)
    dx, dy = direction
    half_size = footprint["width"] / 2
    radial_half_extent = half_size * (abs(dx) + abs(dy))
    assert cx == pytest.approx(dx * radial_half_extent)
    assert cy == pytest.approx(dy * radial_half_extent)


def test_outer_aligned_qr_uses_complete_footprint(tmp_path: Path) -> None:
    """Outermost top placement is tangent to the circular interior."""
    footprint = _compose_qr(tmp_path, alignment="outer-aligned", position=0, qr_size=20.0)
    cx, cy = _center(footprint)
    half_size = footprint["width"] / 2
    assert cx == pytest.approx(0.0)
    assert math.hypot(half_size, cy - half_size) == pytest.approx(0.5)
    assert cy < 0


def test_outer_alignment_uses_ridge_reduced_interior(tmp_path: Path) -> None:
    """QR placement respects the actual interior, not the Shape envelope."""
    footprint = _compose_qr(tmp_path, alignment="outer-aligned", position=0, ridge_width=5.0)
    cx, cy = _center(footprint)
    half_size = footprint["width"] / 2
    assert cx == pytest.approx(0.0)
    assert math.hypot(half_size, cy - half_size) == pytest.approx(0.45)


def test_qr_rejects_footprint_that_cannot_fit_interior(tmp_path: Path) -> None:
    """An oversized square cannot fit merely because its width is legal."""
    with pytest.raises(ValueError, match="(?i)(qr|footprint|interior|fit)"):
        _compose_qr(tmp_path, alignment="centered", qr_size=80.0)


def test_outer_aligned_qr_remains_axis_aligned(tmp_path: Path) -> None:
    """Changing clock position translates rather than rotates the QR."""
    footprint = _compose_qr(tmp_path, alignment="outer-aligned", position=45.0)
    cx, cy = _center(footprint)
    assert cx > 0
    assert cy < 0
    assert cx == pytest.approx(-cy)
    assert footprint["width"] == pytest.approx(0.2)
    assert footprint["height"] == pytest.approx(0.2)


def test_square_interior_allows_corner_safe_outer_placement(tmp_path: Path) -> None:
    """Outer placement follows the square interior rather than a circle."""
    footprint = _compose_qr(tmp_path, alignment="outer-aligned", position=90.0, geometry="square")
    assert footprint["x"] + footprint["width"] == pytest.approx(0.5)
    assert _center(footprint)[1] == pytest.approx(0.0)


def test_qr_footprint_has_fixed_one_mm_corner_radius(tmp_path: Path) -> None:
    """QR footprint records a 1 mm radius in registered Shape space."""
    footprint = _compose_qr(tmp_path, alignment="centered", qr_size=30.0)
    assert footprint["type"] == "rounded_rect"
    assert footprint["width"] == pytest.approx(0.3)
    assert footprint["height"] == pytest.approx(0.3)
    assert footprint["corner_radius"] == pytest.approx(0.01)


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
    return _run_compose(
        directory,
        payload=payload,
        artwork_manifest=tmp_path / "source" / "vector.json",
    )


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
