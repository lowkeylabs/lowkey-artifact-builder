"""
Tests for Shape Inner Ridge registered composition.
"""
# File: tests/model/shape/test_inner_ridge_compose.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import Mock

import pytest

from lowkey_artifact_builder.model.models.shape.stages import compose

# =========================================================
# Helpers
# =========================================================


def _write_registered_circle_structure(
    path: Path,
) -> None:
    """
    Write representative registered circular Shape structure.
    """

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        (
            '<svg xmlns="http://www.w3.org/2000/svg" '
            'viewBox="-0.5 -0.5 1.0 1.0">'
            '<circle cx="0.0" cy="0.0" r="0.5" />'
            "</svg>"
        ),
        encoding="utf-8",
    )


def _compose_inner_ridge(
    tmp_path: Path,
    *,
    outer_ridge_width: float,
    inner_ridge_width: float = 2.0,
    inner_to_outer_ridge_dist: float = 10.0,
) -> Path:
    """
    Execute Shape Compose with representative Inner Ridge parameters.
    """

    structure = tmp_path / "structure.svg"
    composition = tmp_path / "composition.svg"
    manifest = tmp_path / "products.json"

    _write_registered_circle_structure(
        structure,
    )

    context = Mock()

    inputs = {
        "structure.structure": structure,
    }

    outputs = {
        "composition": composition,
        "manifest": manifest,
    }

    values = {
        "shape_size": 100.0,
        "shape_outer_ridge_width": outer_ridge_width,
        "shape_outer_ridge_style": "integrated",
        "shape_inner_ridge_width": inner_ridge_width,
        "shape_inner_to_outer_ridge_dist": inner_to_outer_ridge_dist,
    }

    context.input.side_effect = inputs.__getitem__
    context.has_input.side_effect = inputs.__contains__
    context.output.side_effect = outputs.__getitem__
    context.resolver.side_effect = values.__getitem__

    compose.execute(
        context,
    )

    return composition


# =========================================================
# Inner Ridge registered composition
# =========================================================


def test_inner_ridge_uses_outer_ridge_inner_boundary_as_positioning_reference(
    tmp_path: Path,
) -> None:
    """
    A participating Outer Ridge establishes the Inner Ridge reference edge.

    For a 100 mm circular Shape with a 5 mm Outer Ridge, the Outer Ridge
    inside radius is 0.45 in registered space. A 10 mm separation therefore
    places the Inner Ridge outside radius at 0.35. A 2 mm Inner Ridge then
    places its inside radius at 0.33.

    The Inner Ridge inside boundary becomes the registered Shape interior.
    """

    composition = _compose_inner_ridge(
        tmp_path,
        outer_ridge_width=5.0,
        inner_ridge_width=2.0,
        inner_to_outer_ridge_dist=10.0,
    )

    root = ET.parse(
        composition,
    ).getroot()

    outer_ridge_inner = root.find(
        ".//*[@id='ridge-inner-boundary']",
    )
    inner_ridge_outer = root.find(
        ".//*[@id='inner-ridge-outer-boundary']",
    )
    inner_ridge_inner = root.find(
        ".//*[@id='inner-ridge-inner-boundary']",
    )

    assert outer_ridge_inner is not None
    assert inner_ridge_outer is not None
    assert inner_ridge_inner is not None

    assert float(outer_ridge_inner.get("r", "nan")) == pytest.approx(
        0.45,
    )
    assert float(inner_ridge_outer.get("r", "nan")) == pytest.approx(
        0.35,
    )
    assert float(inner_ridge_inner.get("r", "nan")) == pytest.approx(
        0.33,
    )

    interior = compose.registered_interior_region(
        composition,
    )

    assert interior.get("id") == "inner-ridge-inner-boundary"
    assert float(interior.get("r", "nan")) == pytest.approx(
        0.33,
    )


def test_inner_ridge_uses_shape_boundary_when_outer_ridge_does_not_participate(
    tmp_path: Path,
) -> None:
    """
    Without an Outer Ridge, the Shape boundary establishes the reference edge.

    For a 100 mm circular Shape, the registered Shape radius is 0.5.
    A 10 mm separation places the Inner Ridge outside radius at 0.4.
    A 2 mm Inner Ridge then places its inside radius at 0.38.

    The Inner Ridge inside boundary becomes the registered Shape interior.
    """

    composition = _compose_inner_ridge(
        tmp_path,
        outer_ridge_width=0.0,
        inner_ridge_width=2.0,
        inner_to_outer_ridge_dist=10.0,
    )

    root = ET.parse(
        composition,
    ).getroot()

    outer_ridge_inner = root.find(
        ".//*[@id='ridge-inner-boundary']",
    )
    inner_ridge_outer = root.find(
        ".//*[@id='inner-ridge-outer-boundary']",
    )
    inner_ridge_inner = root.find(
        ".//*[@id='inner-ridge-inner-boundary']",
    )

    assert outer_ridge_inner is None
    assert inner_ridge_outer is not None
    assert inner_ridge_inner is not None

    assert float(inner_ridge_outer.get("r", "nan")) == pytest.approx(
        0.4,
    )
    assert float(inner_ridge_inner.get("r", "nan")) == pytest.approx(
        0.38,
    )

    interior = compose.registered_interior_region(
        composition,
    )

    assert interior.get("id") == "inner-ridge-inner-boundary"
    assert float(interior.get("r", "nan")) == pytest.approx(
        0.38,
    )
