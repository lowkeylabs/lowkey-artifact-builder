"""
Tests for composition of Artwork Outer Ridge and Hole Features.

Outer Ridge and Hole are independent optional standalone Artwork Features.

When both participate, Hole placement remains registered to the full
size-controlled Artwork boundary and subtracts any Outer Ridge material
intersecting its physical X/Y region.
"""
# File: tests/model/artwork/test_outer_ridge_hole_composition.py
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
    Return a Hole resolved against the full 40 x 30 mm outer boundary.

    A 6 mm Hole with a 1 mm edge distance at the top has its center
    4 mm inward from the outer boundary.
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


class _StubContext:
    """
    Minimal StageContext substitute for execute-level extrusion tests.
    """

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
    """
    Return an Artwork resolver with test-owned parameter overrides.
    """

    resolver = get_resolver(
        "outer-ridge-hole-composition",
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
    """
    Write the minimal vector-stage products required by extrude.execute().
    """

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
    """
    Stand in for OpenSCAD while preserving execute() output behavior.
    """

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output.write_text(
        "stl",
        encoding="utf-8",
    )


# =========================================================
# Disabled Hole
# =========================================================


def test_outer_ridge_without_hole_preserves_existing_geometry(
    tmp_path: Path,
) -> None:
    """
    Outer Ridge geometry remains unchanged when Hole does not participate.
    """

    envelope = tmp_path / "envelope.svg"
    _write_svg(envelope)

    source = extrude._build_outer_ridge_scad(
        envelope,
        registered_extent=100,
        envelope_bounds=(
            20.0,
            10.0,
            60.0,
            40.0,
        ),
        artwork_size=40.0,
        outer_ridge_width=2.0,
        outer_ridge_raise=1.5,
        hole_geometry=None,
    )

    assert "outer_ridge_raise = 1.5;" in source
    assert "outer_ridge_scale = 0.9;" in source

    # Existing ridge construction remains present.
    assert "artwork_size / envelope_extent" in source
    assert "artwork_size * outer_ridge_scale / envelope_extent" in source

    # Only the existing planar ring difference is present.
    assert source.count("difference()") == 1
    assert "cylinder(" not in source


# =========================================================
# Participating Hole
# =========================================================


def test_outer_ridge_subtracts_participating_hole(
    tmp_path: Path,
) -> None:
    """
    A participating Hole subtracts intersecting Outer Ridge material.
    """

    envelope = tmp_path / "envelope.svg"
    _write_svg(envelope)

    source = extrude._build_outer_ridge_scad(
        envelope,
        registered_extent=100,
        envelope_bounds=(
            20.0,
            10.0,
            60.0,
            40.0,
        ),
        artwork_size=40.0,
        outer_ridge_width=2.0,
        outer_ridge_raise=1.5,
        hole_geometry=_hole_geometry(),
    )

    # One difference constructs the ridge and another performs the
    # physical Hole subtraction.
    assert source.count("difference()") == 2

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


def test_outer_ridge_hole_subtraction_spans_complete_ridge_z_extent(
    tmp_path: Path,
) -> None:
    """
    Hole passes completely through the Outer Ridge physical Z extent.
    """

    envelope = tmp_path / "envelope.svg"
    _write_svg(envelope)

    source = extrude._build_outer_ridge_scad(
        envelope,
        registered_extent=100,
        envelope_bounds=(
            20.0,
            10.0,
            60.0,
            40.0,
        ),
        artwork_size=40.0,
        outer_ridge_width=2.0,
        outer_ridge_raise=2.25,
        outer_ridge_z=1.5,
        hole_geometry=_hole_geometry(),
    )

    assert "outer_ridge_raise = 2.25;" in source
    assert "outer_ridge_z = 1.5;" in source

    assert (
        """translate(
    [
        0,
        11,
        1.5
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


def test_outer_ridge_and_artwork_use_same_resolved_hole_geometry(
    tmp_path: Path,
) -> None:
    """
    Outer Ridge and Artwork proper consume the same resolved physical Hole.

    Outer Ridge must not independently reposition Hole relative to its
    inset Artwork-proper boundary.
    """

    envelope = tmp_path / "envelope.svg"
    artwork = tmp_path / "color-1.svg"

    _write_svg(envelope)
    _write_svg(artwork)

    hole = _hole_geometry()

    ridge_source = extrude._build_outer_ridge_scad(
        envelope,
        registered_extent=100,
        envelope_bounds=(
            20.0,
            10.0,
            60.0,
            40.0,
        ),
        artwork_size=40.0,
        outer_ridge_width=2.0,
        outer_ridge_raise=1.0,
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
        artwork_scale=0.9,
        hole_geometry=hole,
    )

    hole_xy = """translate(
    [
        0,
        11,"""

    assert hole_xy in ridge_source
    assert hole_xy in artwork_source

    assert "r = 3," in ridge_source
    assert "r = 3," in artwork_source


@pytest.mark.slow
def test_execute_passes_resolved_hole_geometry_to_participating_outer_ridge(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    execute composes participating Outer Ridge and Hole Features.

    Hole placement is resolved once against the full size-controlled
    standalone Artwork boundary and that resolved geometry is supplied to
    Outer Ridge rather than being independently recomputed by Ridge
    generation.
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
            artwork_outer_ridge_width=2.0,
            artwork_outer_ridge_raise=1.5,
            artwork_hole_diameter=6.0,
            artwork_hole_edge_distance=1.0,
            artwork_hole_position=0,
        ),
    )

    captured_hole: HoleGeometry | None = None

    original_build_outer_ridge_scad = extrude._build_outer_ridge_scad

    def capture_build_outer_ridge_scad(
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
        outer_ridge_width: float,
        outer_ridge_raise: float,
        outer_ridge_z: float = 0.0,
        hole_geometry: HoleGeometry | None = None,
    ) -> str:
        nonlocal captured_hole

        captured_hole = hole_geometry

        return original_build_outer_ridge_scad(
            envelope,
            registered_extent=registered_extent,
            envelope_bounds=envelope_bounds,
            artwork_size=artwork_size,
            outer_ridge_width=outer_ridge_width,
            outer_ridge_raise=outer_ridge_raise,
            outer_ridge_z=outer_ridge_z,
            hole_geometry=hole_geometry,
        )

    monkeypatch.setattr(
        extrude,
        "_build_outer_ridge_scad",
        capture_build_outer_ridge_scad,
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

    assert captured_hole.center_x == pytest.approx(0.0)
    assert captured_hole.center_y == pytest.approx(11.0)

    assert captured_hole.nearest_edge_x == pytest.approx(0.0)
    assert captured_hole.nearest_edge_y == pytest.approx(14.0)

    assert captured_hole.envelope_bounds == Bounds(
        min_x=-20.0,
        min_y=-15.0,
        max_x=20.0,
        max_y=15.0,
    )
