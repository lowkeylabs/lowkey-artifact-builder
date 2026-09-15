"""
Tests for independent Artwork Hole and Loop composition.

Hole and Loop are independent optional Artwork Features. Sharing cardinal
placement mechanics must not couple their participation, position, planar
geometry, physical extrusion, or semantic color behavior.
"""
# File: tests/model/artwork/test_hole_loop_composition.py
# Copyright 2026 lowkeylabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from lowkey_artifact_builder.config import (
    Resolver,
    get_resolver,
)
from lowkey_artifact_builder.model.models.artwork.hole import (
    HoleGeometry,
    create_hole_geometry,
)
from lowkey_artifact_builder.model.models.artwork.loop import (
    Bounds,
    LoopGeometry,
    create_loop_geometry,
)
from lowkey_artifact_builder.model.models.artwork.stages import extrude

# =========================================================
# Test support
# =========================================================


class _StubContext:
    """
    Minimal StageContext substitute for execute-level composition tests.
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
        "hole-loop-composition",
        model="artwork",
        project_root=tmp_path,
    )

    return resolver.with_values(
        overrides,
        provenance="test",
    )


def _write_svg(
    path: Path,
    *,
    x: float = 0.0,
    y: float = 0.0,
    width: float = 100.0,
    height: float = 100.0,
) -> None:
    """
    Write one simple rectangular SVG.
    """

    path.write_text(
        f"""
<svg xmlns="http://www.w3.org/2000/svg"
     width="100"
     height="100"
     viewBox="0 0 100 100">
  <rect
      x="{x}"
      y="{y}"
      width="{width}"
      height="{height}"
      fill="#000000" />
</svg>
""".strip(),
        encoding="utf-8",
    )


def _write_vector_manifest(
    path: Path,
) -> None:
    """
    Write Registered Artwork with distinct cardinal attachment colors.

    Red occupies the top attachment axis and green occupies the right
    attachment axis. This lets the composition test distinguish Loop color
    selection from independently configured Hole position.
    """

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    envelope = path.parent / "envelope.svg"
    top = path.parent / "top.svg"
    right = path.parent / "right.svg"

    _write_svg(
        envelope,
    )

    _write_svg(
        top,
        x=45.0,
        y=0.0,
        width=10.0,
        height=20.0,
    )

    _write_svg(
        right,
        x=80.0,
        y=45.0,
        width=20.0,
        height=10.0,
    )

    path.write_text(
        json.dumps(
            {
                "registered_extent": 100,
                "envelope": envelope.name,
                "products": [
                    {
                        "index": 1,
                        "path": top.name,
                        "artifact_color": {
                            "index": 1,
                            "rgb": {
                                "red": 255,
                                "green": 0,
                                "blue": 0,
                            },
                        },
                        "printer_color": {
                            "name": "red",
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
                        "path": right.name,
                        "artifact_color": {
                            "index": 2,
                            "rgb": {
                                "red": 0,
                                "green": 255,
                                "blue": 0,
                            },
                        },
                        "printer_color": {
                            "name": "green",
                            "rgb": {
                                "red": 0,
                                "green": 255,
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
    """
    Stand in for OpenSCAD while preserving execute() output behavior.
    """

    del source

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output.write_text(
        "solid test\nendsolid test\n",
        encoding="utf-8",
    )


# =========================================================
# Planar independence
# =========================================================


def test_hole_and_loop_positions_are_independent() -> None:
    """
    Hole and Loop may select different cardinal positions.

    Resolving one Feature's position does not constrain the other Feature.
    """

    bounds = Bounds(
        min_x=-20.0,
        min_y=-15.0,
        max_x=20.0,
        max_y=15.0,
    )

    hole = create_hole_geometry(
        envelope_bounds=bounds,
        diameter=6.0,
        edge_distance=1.0,
        position=90,
    )

    loop = create_loop_geometry(
        envelope_bounds=bounds,
        inner_diameter=6.0,
        width=1.0,
        position=0,
    )

    assert hole.center_x == pytest.approx(16.0)
    assert hole.center_y == pytest.approx(0.0)

    assert loop.center_x == pytest.approx(0.0)
    assert loop.center_y == pytest.approx(-12.0)


def test_enabling_loop_does_not_change_hole_geometry() -> None:
    """
    Loop geometry outside the Artwork extent does not affect Hole placement.

    Hole remains measured from the size-controlled Artwork boundary rather
    than from Loop geometry extending beyond that boundary.
    """

    bounds = Bounds(
        min_x=-20.0,
        min_y=-15.0,
        max_x=20.0,
        max_y=15.0,
    )

    hole_without_loop = create_hole_geometry(
        envelope_bounds=bounds,
        diameter=6.0,
        edge_distance=1.0,
        position=0,
    )

    loop = create_loop_geometry(
        envelope_bounds=bounds,
        inner_diameter=8.0,
        width=2.0,
        position=0,
    )

    hole_with_loop = create_hole_geometry(
        envelope_bounds=bounds,
        diameter=6.0,
        edge_distance=1.0,
        position=0,
    )

    assert loop.inner_attachment_point == (
        0.0,
        -15.0,
    )

    loop_outermost_y = loop.center_y - loop.outer_radius

    assert loop_outermost_y < bounds.min_y

    assert hole_with_loop == hole_without_loop

    assert hole_with_loop.center_y == pytest.approx(
        -11.0,
    )

    assert hole_with_loop.nearest_edge_y == pytest.approx(
        -14.0,
    )


def test_enabling_hole_does_not_change_loop_geometry() -> None:
    """
    Hole participation does not alter Loop attachment geometry.
    """

    bounds = Bounds(
        min_x=-20.0,
        min_y=-15.0,
        max_x=20.0,
        max_y=15.0,
    )

    loop_without_hole = create_loop_geometry(
        envelope_bounds=bounds,
        inner_diameter=8.0,
        width=2.0,
        position=180,
    )

    hole = create_hole_geometry(
        envelope_bounds=bounds,
        diameter=6.0,
        edge_distance=1.0,
        position=-90,
    )

    loop_with_hole = create_loop_geometry(
        envelope_bounds=bounds,
        inner_diameter=8.0,
        width=2.0,
        position=180,
    )

    assert hole.center_x == pytest.approx(-16.0)
    assert hole.center_y == pytest.approx(0.0)

    assert loop_with_hole == loop_without_hole


# =========================================================
# Execution composition
# =========================================================


@pytest.mark.slow
def test_execute_resolves_hole_and_loop_independently(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    execute() composes participating Hole and Loop Features independently.

    Hole and Loop use their independently configured cardinal positions.
    Hole remains resolved against the size-controlled Artwork boundary,
    while Loop receives only its own resolved geometry.

    Hole does not become subtractive input to Loop geometry and does not
    participate in Loop attachment-color selection.
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
            artwork_size=100.0,
            artwork_raise=1.0,
            artwork_hole_diameter=10.0,
            artwork_hole_edge_distance=2.0,
            artwork_hole_position=90,
            loop_inner_diameter=10.0,
            loop_width=2.0,
            loop_position=0,
            loop_raise=1.0,
        ),
    )

    captured_hole: HoleGeometry | None = None
    captured_loop: LoopGeometry | None = None

    original_build_scad = extrude._build_scad
    original_build_loop_scad = extrude._build_loop_scad

    def capture_build_scad(
        svg: Path,
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
        nonlocal captured_hole

        captured_hole = hole_geometry

        return original_build_scad(
            svg,
            registered_extent=registered_extent,
            envelope_bounds=envelope_bounds,
            artwork_size=artwork_size,
            artwork_raise=artwork_raise,
            artwork_z=artwork_z,
            artwork_scale=artwork_scale,
            hole_geometry=hole_geometry,
        )

    def capture_build_loop_scad(
        geometry: LoopGeometry,
        *,
        loop_raise: float,
        loop_z: float = 0.0,
    ) -> str:
        nonlocal captured_loop

        captured_loop = geometry

        return original_build_loop_scad(
            geometry,
            loop_raise=loop_raise,
            loop_z=loop_z,
        )

    monkeypatch.setattr(
        extrude,
        "_build_scad",
        capture_build_scad,
    )

    monkeypatch.setattr(
        extrude,
        "_build_loop_scad",
        capture_build_loop_scad,
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
    assert captured_loop is not None

    # Hole position 90 is independently resolved against the right-hand
    # size-controlled Artwork boundary.
    assert captured_hole.radius == pytest.approx(5.0)

    assert captured_hole.center_x == pytest.approx(
        43.0,
    )
    assert captured_hole.center_y == pytest.approx(
        0.0,
    )

    assert captured_hole.nearest_edge_x == pytest.approx(
        48.0,
    )
    assert captured_hole.nearest_edge_y == pytest.approx(
        0.0,
    )

    # Loop position 0 remains independently attached at the top.
    assert captured_loop.position == 0

    assert captured_loop.center_x == pytest.approx(
        0.0,
    )
    assert captured_loop.center_y == pytest.approx(
        -45.0,
    )

    assert captured_loop.inner_attachment_point == (
        0.0,
        -50.0,
    )

    # Loop geometry extends outside the size-controlled Artwork boundary,
    # but that additional extent did not become Hole's placement boundary.
    assert captured_loop.center_y - captured_loop.outer_radius < captured_hole.envelope_bounds.min_y

    # The final manifest contains Loop as a printable component but no
    # independently printable Hole component.
    data: dict[str, Any] = json.loads(
        extrude_manifest.read_text(
            encoding="utf-8",
        )
    )

    products = {product["path"]: product for product in data["products"]}

    assert "loop.stl" in products
    assert "hole.stl" not in products

    # Loop position is top, so its derived semantic color remains the
    # registered top attachment color. Hole position 90/right must not
    # redirect Loop color derivation to green.
    loop_product = products["loop.stl"]

    assert loop_product["printer_color"]["name"] == "red"
    assert loop_product["printer_color"]["rgb"] == {
        "red": 255,
        "green": 0,
        "blue": 0,
    }
