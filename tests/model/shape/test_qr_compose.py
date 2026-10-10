"""
Tests for QR registered composition within the Shape model.

The QR Feature is Shape-owned and does not require incorporated Artwork.
Its dark/light geometry is composed before physical dimensionalization.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from lowkey_artifact_builder.engine import StageContext
from lowkey_artifact_builder.model.models.shape.stages import compose


def _write_structure(path: Path) -> None:
    path.write_text(
        (
            '<svg xmlns="http://www.w3.org/2000/svg" '
            'viewBox="-0.5 -0.5 1 1">'
            '<circle cx="0" cy="0" r="0.5"/>'
            "</svg>"
        ),
        encoding="utf-8",
    )


def _execute_compose(
    tmp_path: Path,
    *,
    payload: str,
    qr_size: float = 30.0,
) -> tuple[Path, dict]:
    structure = tmp_path / "structure.svg"
    composition = tmp_path / "composition.svg"
    manifest = tmp_path / "products.json"

    _write_structure(structure)

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
        "shape_qr_size": qr_size,
        "shape_qr_alignment": "centered",
        "shape_qr_position": 0.0,
    }

    context = Mock(spec=StageContext)
    context.input.side_effect = {
        "structure.structure": structure,
    }.__getitem__
    context.has_input.return_value = False
    context.output.side_effect = {
        "composition": composition,
        "manifest": manifest,
    }.__getitem__
    context.resolver.side_effect = values.__getitem__

    compose.execute(context)

    return manifest, json.loads(manifest.read_text(encoding="utf-8"))


def test_empty_qr_payload_does_not_participate(
    tmp_path: Path,
) -> None:
    """QR is absent by default and does not require Artwork."""

    _, data = _execute_compose(
        tmp_path,
        payload="",
    )

    assert data["artwork"] is None
    assert not data.get("qr")


def test_qr_composition_without_artwork(
    tmp_path: Path,
) -> None:
    """A participating QR has two registered semantic components."""

    manifest, data = _execute_compose(
        tmp_path,
        payload="https://lowkeylabs.com",
    )

    assert data["artwork"] is None

    qr = data["qr"]
    assert set(qr["components"]) == {"qr-dark", "qr-light"}

    for component in qr["components"].values():
        path = manifest.parent / component["path"]

        assert path.is_file()
        assert path.suffix == ".svg"


def test_qr_size_includes_quiet_zone(
    tmp_path: Path,
) -> None:
    """The complete footprint is 30 mm in a 100 mm Shape."""

    _, data = _execute_compose(
        tmp_path,
        payload="https://lowkeylabs.com",
        qr_size=30.0,
    )

    qr = data["qr"]

    # Registered Shape extent is 1.0.
    # Physical 30 / 100 corresponds to registered 0.3.
    footprint = qr["footprint"]

    assert footprint["width"] == pytest.approx(0.3)
    assert footprint["height"] == pytest.approx(0.3)
    assert footprint["x"] == pytest.approx(-0.15)
    assert footprint["y"] == pytest.approx(-0.15)

    assert qr["quiet_zone_modules"] > 0
