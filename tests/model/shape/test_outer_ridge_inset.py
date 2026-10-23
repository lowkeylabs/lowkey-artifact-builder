"""Behavioral tests for SHAPE Outer Ridge inset composition."""

from __future__ import annotations

import math
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from lowkey_artifact_builder.model.models.shape.stages import compose


def _compose(
    tmp_path: Path,
    *,
    geometry: str = "circle",
    inset: float = 0.0,
    width: float = 5.0,
    inner_width: float = 0.0,
) -> Path:
    source = tmp_path / "structure.svg"
    target = tmp_path / "composition.svg"

    if geometry == "circle":
        shape = '<circle cx="0" cy="0" r="0.5"/>'
    elif geometry == "square":
        shape = '<rect x="-0.5" y="-0.5" width="1" height="1"/>'
    elif geometry == "polygon":
        # Canonical regular diamond, with four equal edges.
        shape = '<polygon points="0,-0.5 0.5,0 0,0.5 -0.5,0"/>'
    else:
        raise ValueError(f"Unsupported test geometry: {geometry}")

    source.write_text(
        (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="-0.5 -0.5 1 1">{shape}</svg>'),
        encoding="utf-8",
    )

    compose._compose_ridge(
        source,
        target,
        shape_size=100.0,
        ridge_width=width,
        ridge_inset=inset,
        inner_ridge_width=inner_width,
        inner_to_outer_ridge_dist=10.0,
    )

    return target


def _element(path: Path, name: str) -> ET.Element | None:
    return ET.parse(path).getroot().find(f".//*[@id='{name}']")


def test_circle_inset_preserves_shape_and_moves_both_ridge_edges(
    tmp_path: Path,
) -> None:
    path = _compose(
        tmp_path,
        inset=2.0,
        width=5.0,
        inner_width=2.0,
    )

    shape = _element(path, "shape-boundary")
    ridge_inner = _element(path, "ridge-inner-boundary")
    inner_outer = _element(path, "inner-ridge-outer-boundary")
    inner_inner = _element(path, "inner-ridge-inner-boundary")

    assert shape is not None
    assert ridge_inner is not None
    assert inner_outer is not None
    assert inner_inner is not None

    # The complete Shape remains 100 mm in diameter.
    assert float(shape.get("r", "nan")) == pytest.approx(0.5)

    # Outer Ridge:
    #   outside radius = 50 - 2 = 48 mm
    #   inside radius  = 48 - 5 = 43 mm
    assert float(ridge_inner.get("r", "nan")) == pytest.approx(0.43)

    # Inner Ridge follows the inset Outer Ridge:
    #   outside radius = 43 - 10 = 33 mm
    #   inside radius  = 33 - 2 = 31 mm
    assert float(inner_outer.get("r", "nan")) == pytest.approx(0.33)
    assert float(inner_inner.get("r", "nan")) == pytest.approx(0.31)


@pytest.mark.parametrize(
    ("geometry", "expected"),
    [
        ("circle", {"r": 0.45}),
        (
            "square",
            {
                "x": -0.45,
                "y": -0.45,
                "width": 0.90,
                "height": 0.90,
            },
        ),
    ],
)
def test_zero_inset_preserves_existing_ridge_inner_boundary(
    tmp_path: Path,
    geometry: str,
    expected: dict[str, float],
) -> None:
    path = _compose(
        tmp_path,
        geometry=geometry,
        inset=0.0,
        width=5.0,
    )

    ridge_inner = _element(path, "ridge-inner-boundary")

    assert ridge_inner is not None

    for attribute, value in expected.items():
        assert float(ridge_inner.get(attribute, "nan")) == pytest.approx(value)


def test_disabled_ridge_ignores_positive_inset(
    tmp_path: Path,
) -> None:
    path = _compose(
        tmp_path,
        inset=3.0,
        width=0.0,
        inner_width=2.0,
    )

    assert _element(path, "ridge-inner-boundary") is None

    inner = _element(path, "inner-ridge-outer-boundary")

    assert inner is not None
    assert float(inner.get("r", "nan")) == pytest.approx(0.4)


@pytest.mark.parametrize(
    ("inset", "width"),
    [
        (-1.0, 5.0),
        (math.nan, 5.0),
        (math.inf, 5.0),
        (-math.inf, 5.0),
        (48.0, 5.0),
        (50.0, 5.0),
    ],
)
def test_invalid_inset_is_rejected(
    tmp_path: Path,
    inset: float,
    width: float,
) -> None:
    with pytest.raises(ValueError):
        _compose(
            tmp_path,
            inset=inset,
            width=width,
        )
