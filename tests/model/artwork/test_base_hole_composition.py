"""
Tests for composition of Artwork Base and Hole Features.

Base and Hole are independent optional standalone Artwork Features.

When both participate, the same resolved physical Hole used by Artwork
proper passes completely through the participating Base. Hole remains
subtractive geometry and does not become an independently printable
component.
"""
# File: tests/model/artwork/test_base_hole_composition.py
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
from lowkey_artifact_builder.model.models.artwork.loop import Bounds
from lowkey_artifact_builder.model.models.artwork.stages import extrude

# =========================================================
# Test support
# =========================================================


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
        "base-hole-composition",
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
    color = path.parent / "color-1.svg"

    _write_svg(envelope)
    _write_svg(color)

    path.write_text(
        json.dumps(
            {
                "registered_extent": 100,
                "envelope": envelope.name,
                "products": [
                    {
                        "index": 1,
                        "path": color.name,
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


def _hole_geometry() -> HoleGeometry:
    """
    Return one resolved physical Hole for Base composition tests.
    """

    return HoleGeometry(
        envelope_bounds=Bounds(
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


# =========================================================
# Disabled Hole
# =========================================================


def test_base_without_hole_preserves_existing_base_geometry(
    tmp_path: Path,
) -> None:
    """
    Base geometry remains unchanged when Hole does not participate.

    The neutral Hole state must therefore preserve the existing Base SCAD
    rather than introducing subtractive geometry.
    """

    envelope = tmp_path / "envelope.svg"

    _write_svg(
        envelope,
    )

    source = extrude._build_base_scad(
        envelope,
        registered_extent=100,
        envelope_bounds=(
            20.0,
            10.0,
            60.0,
            40.0,
        ),
        artwork_size=40.0,
        base_raise=1.5,
        hole_geometry=None,
    )

    assert "base_raise = 1.5;" in source
    assert "height = base_raise" in source

    assert "difference()" not in source
    assert "cylinder(" not in source


# =========================================================
# Participating Hole
# =========================================================


def test_base_subtracts_participating_hole(
    tmp_path: Path,
) -> None:
    """
    A participating Hole is subtracted from a participating Base.

    The Base remains one printable component whose physical solid contains
    the same circular opening used by Artwork proper.
    """

    envelope = tmp_path / "envelope.svg"

    _write_svg(
        envelope,
    )

    source = extrude._build_base_scad(
        envelope,
        registered_extent=100,
        envelope_bounds=(
            20.0,
            10.0,
            60.0,
            40.0,
        ),
        artwork_size=40.0,
        base_raise=1.5,
        hole_geometry=_hole_geometry(),
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
        h = 1.5,
        r = 3,
        $fn = 128
    );"""
        in source
    )


def test_base_hole_subtraction_spans_complete_base_z_extent(
    tmp_path: Path,
) -> None:
    """
    Hole passes completely through the Base.

    Base occupies Z=0 through artwork_base_raise, so its subtractive Hole
    cylinder must cover that complete physical Z interval.
    """

    envelope = tmp_path / "envelope.svg"

    _write_svg(
        envelope,
    )

    source = extrude._build_base_scad(
        envelope,
        registered_extent=100,
        envelope_bounds=(
            20.0,
            10.0,
            60.0,
            40.0,
        ),
        artwork_size=40.0,
        base_raise=2.25,
        hole_geometry=_hole_geometry(),
    )

    assert "base_raise = 2.25;" in source

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
        h = 2.25,
        r = 3,
        $fn = 128
    );"""
        in source
    )


# =========================================================
# Registration
# =========================================================


def test_base_and_artwork_use_same_resolved_hole_geometry(
    tmp_path: Path,
) -> None:
    """
    Base and Artwork proper consume the same resolved physical Hole.

    Hole placement is resolved once in the common dimensionalized Artwork
    coordinate system rather than being independently repositioned for Base.
    """

    envelope = tmp_path / "envelope.svg"
    artwork = tmp_path / "color-1.svg"

    _write_svg(
        envelope,
    )

    _write_svg(
        artwork,
    )

    hole = _hole_geometry()

    base_source = extrude._build_base_scad(
        envelope,
        registered_extent=100,
        envelope_bounds=(
            20.0,
            10.0,
            60.0,
            40.0,
        ),
        artwork_size=40.0,
        base_raise=1.5,
        hole_geometry=hole,
    )

    artwork_source = extrude._build_scad(
        artwork,
        registered_extent=100,
        envelope_bounds=(
            20.0,
            10.0,
            60.0,
            40.0,
        ),
        artwork_size=40.0,
        artwork_raise=1.0,
        artwork_z=1.5,
        hole_geometry=hole,
    )

    hole_xy = """translate(
    [
        0,
        11,"""

    assert hole_xy in base_source
    assert hole_xy in artwork_source

    assert "r = 3," in base_source
    assert "r = 3," in artwork_source


@pytest.mark.slow
def test_execute_passes_resolved_hole_geometry_to_participating_base(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    execute composes participating Base and Hole Features.

    Hole placement is resolved once in the standalone physical Artwork
    coordinate system and that resolved geometry is supplied to Base rather
    than being independently recomputed by Base generation.
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
            artwork_base_raise=1.5,
            artwork_hole_diameter=6.0,
            artwork_hole_edge_distance=1.0,
            artwork_hole_position=0,
        ),
    )

    captured_hole: HoleGeometry | None = None

    original_build_base_scad = extrude._build_base_scad

    def capture_build_base_scad(
        envelope: Path,
        *,
        registered_extent: int,
        envelope_bounds: tuple[
            float,
            float,
            float,
            float,
        ],
        artwork_size: float,
        base_raise: float,
        hole_geometry: HoleGeometry | None = None,
    ) -> str:
        nonlocal captured_hole

        captured_hole = hole_geometry

        return original_build_base_scad(
            envelope,
            registered_extent=registered_extent,
            envelope_bounds=envelope_bounds,
            artwork_size=artwork_size,
            base_raise=base_raise,
            hole_geometry=hole_geometry,
        )

    monkeypatch.setattr(
        extrude,
        "_build_base_scad",
        capture_build_base_scad,
    )

    monkeypatch.setattr(
        extrude,
        "render_stl_source",
        _fake_render_stl_source,
    )

    extrude.execute(
        context,  # type: ignore[arg-type]
    )

    assert captured_hole is not None

    assert captured_hole.radius == pytest.approx(3.0)

    assert captured_hole.envelope_bounds == Bounds(
        min_x=-20.0,
        min_y=-15.0,
        max_x=20.0,
        max_y=15.0,
    )

    assert captured_hole.center_x == pytest.approx(0.0)
    assert captured_hole.center_y == pytest.approx(11.0)
