"""
Tests for Artwork Hole extrusion integration.

A participating Hole is subtractive standalone Artwork geometry.

Hole planar placement remains owned by Artwork Hole geometry. The extrusion
stage applies that resolved physical geometry to every Artwork color layer
without creating an independently printable Hole product.
"""
# File: tests/model/artwork/test_hole_extrusion.py
# Copyright 2026 lowkeylabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from lowkey_artifact_builder.config import Resolver, get_resolver
from lowkey_artifact_builder.model.models.artwork.hole import (
    HoleGeometry,
)
from lowkey_artifact_builder.model.models.artwork.stages import extrude

# =========================================================
# Test support
# =========================================================


def _write_svg(
    path: Path,
) -> None:
    path.write_text(
        """
<svg xmlns="http://www.w3.org/2000/svg"
     width="100"
     height="100"
     viewBox="0 0 100 100">
  <rect x="20" y="10" width="40" height="30"/>
</svg>
""".strip(),
        encoding="utf-8",
    )


class _StubContext:
    def __init__(
        self,
        *,
        vector_manifest: Path,
        extrude_manifest: Path,
        resolver: Resolver,
    ) -> None:
        self._vector_manifest = vector_manifest
        self._extrude_manifest = extrude_manifest
        self.resolver = resolver

    def input(
        self,
        name: str,
    ) -> Path:
        assert name == "vector.manifest"
        return self._vector_manifest

    def output(
        self,
        name: str,
    ) -> Path:
        assert name == "manifest"
        return self._extrude_manifest


def _resolver(
    tmp_path: Path,
    **overrides: Any,
) -> Resolver:
    resolver = get_resolver(
        "hole-extrusion",
        model="artwork",
        project_root=tmp_path,
    )

    return resolver.with_values(
        overrides,
        provenance="test",
    )


def _write_vector_manifest(
    path: Path,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    envelope = path.parent / "envelope.svg"
    first = path.parent / "color-1.svg"
    second = path.parent / "color-2.svg"

    _write_svg(envelope)
    _write_svg(first)
    _write_svg(second)

    path.write_text(
        json.dumps(
            {
                "registered_extent": 100,
                "envelope": envelope.name,
                "products": [
                    {
                        "index": 1,
                        "path": first.name,
                        "artifact_color": {
                            "index": 1,
                            "rgb": {
                                "red": 255,
                                "green": 0,
                                "blue": 0,
                            },
                        },
                        "printer_color": {
                            "name": "test-red",
                            "rgb": {
                                "red": 255,
                                "green": 0,
                                "blue": 0,
                            },
                        },
                        "distance": 0.0,
                    },
                    {
                        "index": 2,
                        "path": second.name,
                        "artifact_color": {
                            "index": 2,
                            "rgb": {
                                "red": 0,
                                "green": 0,
                                "blue": 255,
                            },
                        },
                        "printer_color": {
                            "name": "test-blue",
                            "rgb": {
                                "red": 0,
                                "green": 0,
                                "blue": 255,
                            },
                        },
                        "distance": 0.0,
                    },
                ],
            }
        ),
        encoding="utf-8",
    )


def _fake_render_stl_source(
    source: str,
    output: Path,
) -> None:
    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output.write_text(
        "stl",
        encoding="utf-8",
    )


# =========================================================
# Extrusion-stage integration
# =========================================================


@pytest.mark.slow
def test_execute_applies_same_hole_geometry_to_every_artwork_layer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    A participating Hole is subtracted from every Artwork color component.

    Every registered Artwork color layer therefore receives the same resolved
    physical Hole geometry so registration between layers is preserved.
    """

    vector_manifest = tmp_path / "vector" / "products.json"
    extrude_manifest = tmp_path / "extrude" / "products.json"

    _write_vector_manifest(
        vector_manifest,
    )

    context = _StubContext(
        vector_manifest=vector_manifest,
        extrude_manifest=extrude_manifest,
        resolver=_resolver(
            tmp_path,
            artwork_size=40.0,
            artwork_raise=1.0,
            artwork_hole_diameter=6.0,
            artwork_hole_edge_distance=1.0,
            artwork_hole_position=0,
        ),
    )

    holes: list[HoleGeometry | None] = []

    original_build_scad = extrude._build_scad

    def capture_build_scad(
        svg_path: Path,
        *,
        registered_extent: int,
        envelope_bounds: tuple[
            float,
            float,
            float,
            float,
        ],
        artwork_size: float,
        artwork_raise: float,
        artwork_z: float = 0.0,
        artwork_scale: float = 1.0,
        hole_geometry: HoleGeometry | None = None,
    ) -> str:
        holes.append(
            hole_geometry,
        )

        return original_build_scad(
            svg_path,
            registered_extent=registered_extent,
            envelope_bounds=envelope_bounds,
            artwork_size=artwork_size,
            artwork_raise=artwork_raise,
            artwork_z=artwork_z,
            artwork_scale=artwork_scale,
            hole_geometry=hole_geometry,
        )

    monkeypatch.setattr(
        extrude,
        "_build_scad",
        capture_build_scad,
    )

    monkeypatch.setattr(
        extrude,
        "render_stl_source",
        _fake_render_stl_source,
    )

    extrude.execute(
        context,  # type: ignore[arg-type]
    )

    assert len(holes) == 2

    first = holes[0]
    second = holes[1]

    assert first is not None
    assert second is not None

    assert first == second

    assert first.radius == pytest.approx(3.0)

    # The registered envelope is 40 x 30 and artwork_size is 40 mm,
    # producing physical bounds:
    #
    #     X: -20 .. 20
    #     Y: -15 .. 15
    #
    # Artwork cardinal orientation defines position 0 as top/min_y.
    # A top Hole with radius 3 mm and edge distance 1 mm therefore
    # has center Y = -15 + 3 + 1 = -11 mm.
    assert first.center_x == pytest.approx(0.0)
    assert first.center_y == pytest.approx(-11.0)


@pytest.mark.slow
def test_execute_uses_no_hole_geometry_when_hole_is_disabled(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Disabled Hole preserves ordinary Artwork extrusion.

    artwork_hole_diameter == 0 therefore supplies no Hole geometry to any
    registered Artwork color layer.
    """

    vector_manifest = tmp_path / "vector" / "products.json"
    extrude_manifest = tmp_path / "extrude" / "products.json"

    _write_vector_manifest(
        vector_manifest,
    )

    context = _StubContext(
        vector_manifest=vector_manifest,
        extrude_manifest=extrude_manifest,
        resolver=_resolver(
            tmp_path,
            artwork_size=40.0,
            artwork_raise=1.0,
            artwork_hole_diameter=0.0,
        ),
    )

    holes: list[HoleGeometry | None] = []

    original_build_scad = extrude._build_scad

    def capture_build_scad(
        svg_path: Path,
        *,
        registered_extent: int,
        envelope_bounds: tuple[
            float,
            float,
            float,
            float,
        ],
        artwork_size: float,
        artwork_raise: float,
        artwork_z: float = 0.0,
        artwork_scale: float = 1.0,
        hole_geometry: HoleGeometry | None = None,
    ) -> str:
        holes.append(
            hole_geometry,
        )

        return original_build_scad(
            svg_path,
            registered_extent=registered_extent,
            envelope_bounds=envelope_bounds,
            artwork_size=artwork_size,
            artwork_raise=artwork_raise,
            artwork_z=artwork_z,
            artwork_scale=artwork_scale,
            hole_geometry=hole_geometry,
        )

    monkeypatch.setattr(
        extrude,
        "_build_scad",
        capture_build_scad,
    )

    monkeypatch.setattr(
        extrude,
        "render_stl_source",
        _fake_render_stl_source,
    )

    extrude.execute(
        context,  # type: ignore[arg-type]
    )

    assert holes == [
        None,
        None,
    ]


# =========================================================
# Artwork color-layer subtraction
# =========================================================


def test_build_scad_subtracts_participating_hole_from_artwork_proper(
    tmp_path: Path,
) -> None:
    """
    A participating Hole is subtractive geometry.

    The Artwork color-layer solid is therefore formed by subtracting the
    resolved circular Hole from the ordinary dimensionalized Artwork solid.
    """

    svg = tmp_path / "layer.svg"

    _write_svg(
        svg,
    )

    hole = HoleGeometry(
        envelope_bounds=extrude.Bounds(
            min_x=-20.0,
            min_y=-15.0,
            max_x=20.0,
            max_y=15.0,
        ),
        center_x=0.0,
        center_y=11.0,
        radius=3.0,
        nearest_edge_x=0.0,
        nearest_edge_y=14.0,
    )

    source = extrude._build_scad(
        svg,
        registered_extent=100,
        envelope_bounds=(
            20.0,
            10.0,
            60.0,
            40.0,
        ),
        artwork_size=40.0,
        artwork_raise=1.0,
        hole_geometry=hole,
    )

    assert "difference()" in source

    assert (
        """translate(
    [
        0,
        11,
        0
    ]
)"""
        in source
    )

    assert (
        """cylinder(
        h = 1,
        r = 3,
        $fn = 128
    );"""
        in source
    )


def test_build_scad_hole_subtraction_spans_complete_artwork_z_extent(
    tmp_path: Path,
) -> None:
    """
    Hole subtraction passes through the complete Z extent of Artwork proper.

    The subtractive cylinder must therefore cover the Artwork extrusion from
    its physical bottom through its physical top rather than creating a
    blind recess.
    """

    svg = tmp_path / "layer.svg"

    _write_svg(
        svg,
    )

    hole = HoleGeometry(
        envelope_bounds=extrude.Bounds(
            min_x=-20.0,
            min_y=-15.0,
            max_x=20.0,
            max_y=15.0,
        ),
        center_x=0.0,
        center_y=11.0,
        radius=3.0,
        nearest_edge_x=0.0,
        nearest_edge_y=14.0,
    )

    source = extrude._build_scad(
        svg,
        registered_extent=100,
        envelope_bounds=(
            20.0,
            10.0,
            60.0,
            40.0,
        ),
        artwork_size=40.0,
        artwork_raise=1.25,
        artwork_z=2.0,
        hole_geometry=hole,
    )

    assert "artwork_raise = 1.25;" in source
    assert "artwork_z = 2;" in source

    # Hole subtraction is expressed relative to the complete Artwork-proper
    # Z extent rather than as an independently configured physical height.
    assert "hole_raise" not in source
    assert "hole_z" not in source

    assert "difference()" in source

    assert (
        """translate(
    [
        0,
        11,
        2
    ]
)"""
        in source
    )

    assert (
        """cylinder(
        h = 1.25,
        r = 3,
        $fn = 128
    );"""
        in source
    )


# =========================================================
# Product identity
# =========================================================


@pytest.mark.slow
def test_participating_hole_does_not_create_independent_extrusion_product(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Hole has no independently printable component or semantic color.

    Participating Hole changes the existing Artwork color solids but does not
    add a Hole STL or Hole entry to the extrusion manifest.
    """

    vector_manifest = tmp_path / "vector" / "products.json"
    extrude_manifest = tmp_path / "extrude" / "products.json"

    _write_vector_manifest(
        vector_manifest,
    )

    context = _StubContext(
        vector_manifest=vector_manifest,
        extrude_manifest=extrude_manifest,
        resolver=_resolver(
            tmp_path,
            artwork_size=40.0,
            artwork_raise=1.0,
            artwork_hole_diameter=6.0,
            artwork_hole_edge_distance=1.0,
            artwork_hole_position=0,
        ),
    )

    monkeypatch.setattr(
        extrude,
        "render_stl_source",
        _fake_render_stl_source,
    )

    extrude.execute(
        context,  # type: ignore[arg-type]
    )

    data = json.loads(
        extrude_manifest.read_text(
            encoding="utf-8",
        )
    )

    paths = [product["path"] for product in data["products"]]

    assert paths == [
        "color-1.stl",
        "color-2.stl",
    ]

    assert not (extrude_manifest.parent / "hole.stl").exists()

    assert all("hole" not in product for product in data["products"])
