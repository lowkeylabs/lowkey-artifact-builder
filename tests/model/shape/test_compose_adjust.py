"""Behavioral tests for SHAPE Compose Artwork placement adjustments.

Phase 1: offsets and scale modify one authoritative registered transform.
These tests intentionally precede the production implementation (RED).
"""
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
import math
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import Mock

import pytest

from lowkey_artifact_builder.engine import StageContext
from lowkey_artifact_builder.model.models.shape.stages import compose

SVG_NS = "http://www.w3.org/2000/svg"


def _write_artwork(directory: Path) -> Path:
    """Two independently colored components sharing one off-center envelope."""
    directory.mkdir(parents=True, exist_ok=True)
    for name, x, width in (("envelope", 2, 12), ("left", 2, 6), ("right", 8, 6)):
        (directory / f"{name}.svg").write_text(
            f'<svg xmlns="{SVG_NS}" viewBox="0 0 16 16">'
            f'<rect x="{x}" y="3" width="{width}" height="10"/></svg>',
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
                            "rgb": {"red": red, "green": red, "blue": red},
                        },
                    }
                    for index, name, red in ((1, "left", 240), (2, "right", 20))
                ],
            }
        ),
        encoding="utf-8",
    )
    return manifest


def _run_compose(
    directory: Path,
    artwork_manifest: Path,
    *,
    shape_size: float = 100.0,
    offset_x: float = 0.0,
    offset_y: float = 0.0,
    scale: float = 1.0,
) -> tuple[dict, str]:
    directory.mkdir(parents=True, exist_ok=True)

    structure = directory / "structure.svg"
    structure.write_text(
        f'<svg xmlns="{SVG_NS}" viewBox="-0.5 -0.5 1 1">'
        '<circle id="shape-boundary" cx="0" cy="0" r="0.5"/></svg>',
        encoding="utf-8",
    )

    composition = directory / "composition.svg"
    manifest = directory / "products.json"
    artifact = directory / "artifact.svg"

    context = Mock(spec=StageContext)
    inputs = {
        "structure.structure": structure,
        "artwork.vector.manifest": artwork_manifest,
    }
    context.input.side_effect = inputs.__getitem__
    context.has_input.side_effect = inputs.__contains__
    context.output.side_effect = {
        "composition": composition,
        "manifest": manifest,
        "artifact": artifact,
    }.__getitem__

    values = {
        "shape_size": shape_size,
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
        "shape_qr_payload": "",
        "shape_artwork_offset_x": offset_x,
        "shape_artwork_offset_y": offset_y,
        "shape_artwork_scale": scale,
    }
    context.resolver.side_effect = values.__getitem__

    compose.execute(context)

    return (
        json.loads(manifest.read_text(encoding="utf-8")),
        composition.read_text(encoding="utf-8"),
    )


def _center(artwork: compose.RegisteredArtwork, transform: dict) -> tuple[float, float]:
    bounds = compose.registered_artwork_envelope_bounds(artwork)
    source_x = bounds.x + bounds.width / 2
    source_y = bounds.y + bounds.height / 2
    return (
        source_x * transform["scale"] + transform["translate_x"],
        source_y * transform["scale"] + transform["translate_y"],
    )


def test_neutral_adjustments_preserve_automatic_fit(tmp_path: Path) -> None:
    source = _write_artwork(tmp_path / "source")
    artwork = compose.load_registered_artwork(source)
    baseline = compose.fit_registered_artwork_to_shape(
        artwork, composition=_circle_composition(tmp_path)
    )
    result, _ = _run_compose(tmp_path / "neutral", source)
    transform = result["artwork"]["transform"]
    assert transform["scale"] == pytest.approx(baseline.scale)
    assert transform["translate_x"] == pytest.approx(baseline.translate_x)
    assert transform["translate_y"] == pytest.approx(baseline.translate_y)


def _circle_composition(directory: Path) -> Path:
    path = directory / "baseline.svg"
    path.write_text(
        f'<svg xmlns="{SVG_NS}" viewBox="-0.5 -0.5 1 1">'
        '<circle id="shape-boundary" cx="0" cy="0" r="0.5"/></svg>',
        encoding="utf-8",
    )
    return path


@pytest.mark.parametrize(
    ("offset_x", "offset_y", "expected_x", "expected_y"),
    [
        (10.0, 0.0, 0.1, 0.0),
        (0.0, 5.0, 0.0, -0.05),  # SVG registered Y increases downward.
        (-4.0, -6.0, -0.04, 0.06),
    ],
)
def test_physical_offsets_move_artwork_center(
    tmp_path: Path,
    offset_x: float,
    offset_y: float,
    expected_x: float,
    expected_y: float,
) -> None:
    source = _write_artwork(tmp_path / "source")
    artwork = compose.load_registered_artwork(source)
    baseline, _ = _run_compose(tmp_path / "baseline", source, scale=0.5)
    shifted, _ = _run_compose(
        tmp_path / "shifted",
        source,
        offset_x=offset_x,
        offset_y=offset_y,
        scale=0.5,
    )
    center_before = _center(artwork, baseline["artwork"]["transform"])
    center_after = _center(artwork, shifted["artwork"]["transform"])
    assert center_after[0] - center_before[0] == pytest.approx(expected_x)
    assert center_after[1] - center_before[1] == pytest.approx(expected_y)
    assert shifted["artwork"]["transform"]["scale"] == pytest.approx(
        baseline["artwork"]["transform"]["scale"]
    )


def test_scale_changes_fitted_size_without_moving_center(tmp_path: Path) -> None:
    source = _write_artwork(tmp_path / "source")
    artwork = compose.load_registered_artwork(source)
    baseline, _ = _run_compose(tmp_path / "baseline", source)
    scaled, _ = _run_compose(tmp_path / "scaled", source, scale=0.65)
    before = baseline["artwork"]["transform"]
    after = scaled["artwork"]["transform"]
    assert after["scale"] == pytest.approx(before["scale"] * 0.65)
    assert _center(artwork, after) == pytest.approx(_center(artwork, before))


def test_components_and_envelope_share_persisted_transform(tmp_path: Path) -> None:
    source = _write_artwork(tmp_path / "source")
    result, _ = _run_compose(tmp_path / "output", source, offset_x=4.0, offset_y=3.0, scale=0.6)
    registered = result["artwork"]
    assert {item["index"] for item in registered["components"]} == {1, 2}
    assert {item["path"] for item in registered["components"]} == {"left.svg", "right.svg"}
    assert registered["transform"]["scale"] > 0
    fill = result["artwork_fill"]
    assert fill is not None
    # The persisted fill envelope is derived from the same placement transform.
    artwork = compose.load_registered_artwork(source)
    transform = compose.RegisteredArtworkTransform(
        scale=registered["transform"]["scale"],
        width=0.0,
        height=0.0,
        translate_x=registered["transform"]["translate_x"],
        translate_y=registered["transform"]["translate_y"],
    )
    expected = compose.registered_artwork_fill_region(
        ET.fromstring(f'<circle xmlns="{SVG_NS}" cx="0" cy="0" r="0.5"/>'),
        artwork,
        transform=transform,
    )
    envelope = expected.inner_boundary
    actual = fill["inner_boundary"]
    assert actual["type"] == "rect"
    for field in ("x", "y", "width", "height"):
        assert actual[field] == pytest.approx(float(envelope.get(field, "nan")))


def test_adjustments_do_not_move_shape_geometry(tmp_path: Path) -> None:
    source = _write_artwork(tmp_path / "source")
    _, baseline = _run_compose(tmp_path / "baseline", source)
    _, adjusted = _run_compose(tmp_path / "adjusted", source, offset_x=3.0, offset_y=2.0, scale=0.6)
    assert ET.tostring(ET.fromstring(baseline)) == ET.tostring(ET.fromstring(adjusted))


@pytest.mark.parametrize(
    ("offset_x", "offset_y", "scale"),
    [
        (math.nan, 0.0, 0.5),
        (math.inf, 0.0, 0.5),
        (0.0, -math.inf, 0.5),
        (0.0, 0.0, 0.0),
        (0.0, 0.0, -1.0),
        (0.0, 0.0, math.nan),
        (0.0, 0.0, math.inf),
        (60.0, 0.0, 0.5),
        (0.0, 0.0, 1.1),
    ],
)
def test_invalid_adjustments_fail_clearly(
    tmp_path: Path, offset_x: float, offset_y: float, scale: float
) -> None:
    source = _write_artwork(tmp_path / "source")
    with pytest.raises(ValueError, match="(?i)artwork|placement|offset|scale|interior"):
        _run_compose(
            tmp_path / "invalid",
            source,
            offset_x=offset_x,
            offset_y=offset_y,
            scale=scale,
        )
