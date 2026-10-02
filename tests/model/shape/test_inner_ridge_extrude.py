"""
Tests for Shape Inner Ridge physical extrusion.
"""

# File: tests/model/shape/test_inner_ridge_extrude.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from lowkey_artifact_builder.engine import StageContext
from lowkey_artifact_builder.model.models.shape.stages import extrude

# =========================================================
# Test support
# =========================================================


def _write_inner_ridge_composition(
    path: Path,
) -> None:
    """
    Write representative registered circle geometry containing both ridges.

    For a 100 mm Shape:

        Shape boundary            -> radius 0.50
        Outer Ridge inner         -> radius 0.45
        Inner Ridge outer         -> radius 0.35
        Inner Ridge inner         -> radius 0.33

    Extrude consumes these registered boundaries directly. It does not
    reconstruct Inner Ridge placement from width or spacing parameters.
    """

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        """
<svg
    xmlns="http://www.w3.org/2000/svg"
    viewBox="-0.5 -0.5 1.0 1.0"
>
    <circle
        id="shape-boundary"
        cx="0.0"
        cy="0.0"
        r="0.5"
    />
    <circle
        id="ridge-inner-boundary"
        cx="0.0"
        cy="0.0"
        r="0.45"
    />
    <circle
        id="inner-ridge-outer-boundary"
        cx="0.0"
        cy="0.0"
        r="0.35"
    />
    <circle
        id="inner-ridge-inner-boundary"
        cx="0.0"
        cy="0.0"
        r="0.33"
    />
</svg>
""".strip(),
        encoding="utf-8",
    )


def _write_composition_manifest(
    path: Path,
) -> None:
    """
    Write the minimal registered Shape composition manifest.
    """

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        json.dumps(
            {
                "products": [],
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def _make_extrude_resolver(
    *,
    shape_size: float = 100.0,
    shape_base_raise: float = 2.0,
    shape_outer_ridge_raise: float = 1.0,
    shape_outer_ridge_style: str = "integrated",
    shape_inner_ridge_raise: float = 1.5,
) -> Mock:
    """
    Build a strict resolver containing parameters material to Inner Ridge
    extrusion.

    Unrelated optional Shape Extrude features use their ordinary
    nonparticipating defaults. Unknown parameter requests continue to fail so
    the test detects accidental stage coupling without requiring Inner Ridge
    tests to enumerate every optional Extrude Feature.
    """

    values = {
        "shape_size": shape_size,
        "shape_base_raise": shape_base_raise,
        "shape_outer_ridge_raise": shape_outer_ridge_raise,
        "shape_outer_ridge_style": shape_outer_ridge_style,
        "shape_inner_ridge_raise": shape_inner_ridge_raise,
    }

    defaults = {
        "shape_hole_diameter": 0.0,
    }

    def resolver(
        name: str,
    ) -> object:
        if name in values:
            return values[name]

        if name in defaults:
            return defaults[name]

        raise KeyError(
            name,
        )

    return Mock(
        side_effect=resolver,
    )


def _configure_extrude_context_inputs(
    context: Mock,
    *,
    composition: Path,
    composition_manifest: Path,
) -> None:
    """
    Configure the registered Shape composition inputs consumed by Extrude.
    """

    inputs = {
        "compose.composition": composition,
        "compose.manifest": composition_manifest,
    }

    context.input.side_effect = inputs.__getitem__


def _read_manifest(
    path: Path,
) -> dict[str, object]:
    """
    Read an Extrude physical-component manifest.
    """

    data = json.loads(
        path.read_text(
            encoding="utf-8",
        )
    )

    assert isinstance(
        data,
        dict,
    )

    components = data.get(
        "components",
    )

    assert isinstance(
        components,
        list,
    )

    return {
        **data,
        "components": components,
    }


# =========================================================
# Inner Ridge extrusion
# =========================================================


def test_positive_inner_ridge_uses_registered_geometry_and_preserves_component_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    A positive Inner Ridge is an independently identifiable physical component.

    Compose has already established the Inner Ridge position and width through
    its registered outer and inner boundaries. Extrude consumes those
    boundaries directly and applies only the physical Z dimensionalization.

    For a 100 mm Shape with a 2 mm base and +1.5 mm Inner Ridge raise:

        Inner Ridge outer diameter -> 70 mm
        Inner Ridge inner diameter -> 66 mm
        Inner Ridge Z              -> 2.0 through 3.5 mm
    """

    composition = tmp_path / "composition.svg"
    composition_manifest = tmp_path / "composition-products.json"
    manifest = tmp_path / "products.json"

    _write_inner_ridge_composition(
        composition,
    )

    _write_composition_manifest(
        composition_manifest,
    )

    resolver = _make_extrude_resolver()

    context = Mock(
        spec=StageContext,
    )
    context.resolver = resolver

    _configure_extrude_context_inputs(
        context,
        composition=composition,
        composition_manifest=composition_manifest,
    )

    context.output.return_value = manifest

    rendered_sources: dict[str, str] = {}

    def fake_render_stl_source(
        source: str,
        target: Path,
    ) -> None:
        target.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        target.write_text(
            "stl",
            encoding="utf-8",
        )

        rendered_sources[target.name] = source

    monkeypatch.setattr(
        extrude,
        "render_stl_source",
        fake_render_stl_source,
    )

    extrude.execute(
        context,
    )

    data = _read_manifest(
        manifest,
    )

    components = data["components"]

    assert isinstance(
        components,
        list,
    )

    assert {
        "name": "inner-ridge",
        "path": "inner-ridge.stl",
    } in components

    assert (manifest.parent / "inner-ridge.stl").is_file()

    inner_ridge_source = rendered_sources["inner-ridge.stl"]

    assert "35" in inner_ridge_source
    assert "33" in inner_ridge_source
    assert "2" in inner_ridge_source
    assert "1.5" in inner_ridge_source


def test_polygon_inner_ridge_uses_registered_geometry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Polygon Inner Ridge extrusion consumes its registered boundaries directly.

    Compose owns the polygon offset geometry. Extrude dimensionalizes the
    persisted outer and inner boundaries without reconstructing ridge width,
    spacing, or placement.
    """

    composition = tmp_path / "composition.svg"
    composition_manifest = tmp_path / "composition-products.json"
    manifest = tmp_path / "products.json"

    composition.write_text(
        """
<svg
    xmlns="http://www.w3.org/2000/svg"
    viewBox="-0.5 -0.5 1.0 1.0"
>
    <polygon
        id="shape-boundary"
        points="-0.5,-0.5 0.5,-0.5 0.5,0.5 -0.5,0.5"
    />
    <polygon
        id="ridge-inner-boundary"
        points="-0.45,-0.45 0.45,-0.45 0.45,0.45 -0.45,0.45"
    />
    <polygon
        id="inner-ridge-outer-boundary"
        points="-0.35,-0.35 0.35,-0.35 0.35,0.35 -0.35,0.35"
    />
    <polygon
        id="inner-ridge-inner-boundary"
        points="-0.33,-0.33 0.33,-0.33 0.33,0.33 -0.33,0.33"
    />
</svg>
""".strip(),
        encoding="utf-8",
    )

    _write_composition_manifest(
        composition_manifest,
    )

    resolver = _make_extrude_resolver()

    context = Mock(
        spec=StageContext,
    )
    context.resolver = resolver

    _configure_extrude_context_inputs(
        context,
        composition=composition,
        composition_manifest=composition_manifest,
    )

    context.output.return_value = manifest

    rendered_sources: dict[str, str] = {}

    def fake_render_stl_source(
        source: str,
        target: Path,
    ) -> None:
        target.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        target.write_text(
            "stl",
            encoding="utf-8",
        )

        rendered_sources[target.name] = source

    monkeypatch.setattr(
        extrude,
        "render_stl_source",
        fake_render_stl_source,
    )

    extrude.execute(
        context,
    )

    data = _read_manifest(
        manifest,
    )

    components = data["components"]

    assert isinstance(
        components,
        list,
    )

    assert {
        "name": "inner-ridge",
        "path": "inner-ridge.stl",
    } in components

    inner_ridge_source = rendered_sources["inner-ridge.stl"]

    assert "[-35, -35]" in inner_ridge_source
    assert "[35, 35]" in inner_ridge_source
    assert "[-33, -33]" in inner_ridge_source
    assert "[33, 33]" in inner_ridge_source

    assert "shape_base_raise = 2" in inner_ridge_source
    assert "shape_inner_ridge_raise = 1.5" in inner_ridge_source
