"""Behavioral tests for QR placement within registered Shape interiors."""

from __future__ import annotations

import json
import math
from pathlib import Path
from unittest.mock import Mock

import pytest

from lowkey_artifact_builder.engine import StageContext
from lowkey_artifact_builder.model.models.shape.stages import compose


def _compose_qr(
    tmp_path: Path,
    *,
    alignment: str,
    position: float = 0.0,
    qr_size: float = 20.0,
    ridge_width: float = 0.0,
    geometry: str = "circle",
) -> dict:
    """Execute Shape Compose with a participating QR and no Artwork."""
    structure = tmp_path / "structure.svg"
    composition = tmp_path / "composition.svg"
    manifest = tmp_path / "products.json"
    artifact = tmp_path / "artifact.svg"

    if geometry == "circle":
        boundary = '<circle cx="0" cy="0" r="0.5"/>'
    elif geometry == "square":
        boundary = '<rect x="-0.5" y="-0.5" width="1" height="1"/>'
    else:
        raise ValueError(f"Unsupported test geometry: {geometry}")

    structure.write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="-0.5 -0.5 1 1">{boundary}</svg>',
        encoding="utf-8",
    )

    values = {
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
        "shape_qr_payload": "https://lowkeylabs.com",
        "shape_qr_size": qr_size,
        "shape_qr_alignment": alignment,
        "shape_qr_position": position,
    }

    context = Mock(spec=StageContext)
    context.input.side_effect = {"structure.structure": structure}.__getitem__
    context.has_input.return_value = False
    context.output.side_effect = {
        "composition": composition,
        "manifest": manifest,
        "artifact": artifact,
    }.__getitem__
    context.resolver.side_effect = values.__getitem__

    compose.execute(context)

    return json.loads(manifest.read_text(encoding="utf-8"))["qr"]["footprint"]


def _center(footprint: dict) -> tuple[float, float]:
    return (
        footprint["x"] + footprint["width"] / 2,
        footprint["y"] + footprint["height"] / 2,
    )


def test_centered_qr_ignores_position(tmp_path: Path) -> None:
    """Clock angle does not affect centered QR placement."""
    first = _compose_qr(
        tmp_path,
        alignment="centered",
        position=0,
    )
    second = _compose_qr(
        tmp_path,
        alignment="centered",
        position=37,
    )

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
    tmp_path: Path,
    angle: float,
    direction: tuple[float, float],
) -> None:
    """The inward-facing edge crosses the interior center."""
    footprint = _compose_qr(
        tmp_path,
        alignment="inner-aligned",
        position=angle,
    )

    cx, cy = _center(footprint)
    dx, dy = direction

    # A square's support distance in a radial direction.
    half_size = footprint["width"] / 2
    radial_half_extent = half_size * (abs(dx) + abs(dy))

    assert cx == pytest.approx(dx * radial_half_extent)
    assert cy == pytest.approx(dy * radial_half_extent)


def test_outer_aligned_qr_uses_complete_footprint(
    tmp_path: Path,
) -> None:
    """Outermost top placement is tangent to the circular interior."""
    footprint = _compose_qr(
        tmp_path,
        alignment="outer-aligned",
        position=0,
        qr_size=20.0,
    )

    cx, cy = _center(footprint)
    half_size = footprint["width"] / 2

    # The upper corners, not just the QR center, must fit.
    assert cx == pytest.approx(0.0)
    assert math.hypot(half_size, cy - half_size) == pytest.approx(0.5)
    assert cy < 0


def test_outer_alignment_uses_ridge_reduced_interior(
    tmp_path: Path,
) -> None:
    """QR placement respects the actual interior, not the Shape envelope."""
    footprint = _compose_qr(
        tmp_path,
        alignment="outer-aligned",
        position=0,
        ridge_width=5.0,
    )

    cx, cy = _center(footprint)
    half_size = footprint["width"] / 2

    assert cx == pytest.approx(0.0)
    assert math.hypot(half_size, cy - half_size) == pytest.approx(0.45)


def test_qr_rejects_footprint_that_cannot_fit_interior(
    tmp_path: Path,
) -> None:
    """An oversized square cannot fit merely because its width is legal."""
    with pytest.raises(ValueError, match="(?i)(qr|footprint|interior|fit)"):
        _compose_qr(
            tmp_path,
            alignment="centered",
            qr_size=80.0,
        )


def test_outer_aligned_qr_remains_axis_aligned(
    tmp_path: Path,
) -> None:
    """Changing clock position translates rather than rotates the QR."""
    footprint = _compose_qr(
        tmp_path,
        alignment="outer-aligned",
        position=45.0,
    )

    cx, cy = _center(footprint)

    assert cx > 0
    assert cy < 0
    assert cx == pytest.approx(-cy)
    assert footprint["width"] == pytest.approx(0.2)
    assert footprint["height"] == pytest.approx(0.2)


def test_square_interior_allows_corner_safe_outer_placement(
    tmp_path: Path,
) -> None:
    """Outer placement follows the square interior rather than a circle."""
    footprint = _compose_qr(
        tmp_path,
        alignment="outer-aligned",
        position=90.0,
        geometry="square",
    )

    assert footprint["x"] + footprint["width"] == pytest.approx(0.5)
    assert _center(footprint)[1] == pytest.approx(0.0)


def test_qr_footprint_has_fixed_one_mm_corner_radius(
    tmp_path: Path,
) -> None:
    """QR footprint records a 1 mm radius in registered Shape space."""
    footprint = _compose_qr(
        tmp_path,
        alignment="centered",
        qr_size=30.0,
    )

    assert footprint["type"] == "rounded_rect"
    assert footprint["width"] == pytest.approx(0.3)
    assert footprint["height"] == pytest.approx(0.3)
    assert footprint["corner_radius"] == pytest.approx(0.01)
