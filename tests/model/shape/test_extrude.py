"""
Tests for Shape physical extrusion.
"""
# File: tests/model/shape/test_extrude.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import Mock, call

import pytest

from lowkey_artifact_builder.engine import StageContext
from lowkey_artifact_builder.engine.bootstrap import build_stage_registry
from lowkey_artifact_builder.model.models.shape import stages
from lowkey_artifact_builder.model.models.shape.stages import extrude
from lowkey_artifact_builder.model.models.shape.stages.extrude import _load_ridge

# =========================================================
# Test support
# =========================================================


def _write_composition(
    path: Path,
) -> None:
    """
    Write representative registered Shape composition geometry without a ridge.
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
        cx="0.0"
        cy="0.0"
        r="0.5"
    />
</svg>
""".strip(),
        encoding="utf-8",
    )


def _write_integrated_ridge_composition(
    path: Path,
) -> None:
    """
    Write registered circle composition containing an outer ridge boundary.

    The complete Shape boundary has radius 0.5. A 5 mm ridge on a
    100 mm Shape has a registered inset of 0.05, giving the ridge an
    inner radius of 0.45.
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
</svg>
""".strip(),
        encoding="utf-8",
    )


def _write_square_ridge_composition(
    path: Path,
) -> None:
    """
    Write registered square composition containing an outer ridge boundary.

    The complete Shape boundary is 1x1. A 5 mm ridge on a 100 mm Shape
    has a registered inset of 0.05 on every side, giving the ridge an
    inner boundary of 0.9x0.9.
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
    <rect
        id="shape-boundary"
        x="-0.5"
        y="-0.5"
        width="1.0"
        height="1.0"
    />
    <rect
        id="ridge-inner-boundary"
        x="-0.45"
        y="-0.45"
        width="0.9"
        height="0.9"
    />
</svg>
""".strip(),
        encoding="utf-8",
    )


def _write_polygon_ridge_composition(
    path: Path,
) -> None:
    """
    Write registered polygon composition containing an outer ridge boundary.

    The representative polygon is a side-top regular octagon. Its inner
    boundary is a perpendicular 0.05 registered-unit inset from every edge.
    """

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    from lowkey_artifact_builder.model.models.shape.stages import (
        compose,
        structure,
    )

    geometry = structure.create_polygon_geometry(
        number_of_sides=8,
        rotation=22.5,
    )

    document = structure.create_polygon_svg(
        geometry,
    )

    structure_path = path.parent / "polygon-structure.svg"

    document.write(
        structure_path,
        encoding="unicode",
    )

    compose._compose_ridge(
        structure_path,
        path,
        shape_size=100.0,
        ridge_width=5.0,
    )


def _stl_bounds(
    path: Path,
) -> tuple[
    float,
    float,
    float,
    float,
    float,
    float,
]:
    """
    Return X/Y/Z bounds from an ASCII STL produced by OpenSCAD.

    The tuple contains:

        min_x, max_x, min_y, max_y, min_z, max_z
    """

    vertices: list[
        tuple[
            float,
            float,
            float,
        ]
    ] = []

    for line in path.read_text(
        encoding="utf-8",
    ).splitlines():
        fields = line.strip().split()

        if len(fields) != 4 or fields[0] != "vertex":
            continue

        vertices.append(
            (
                float(fields[1]),
                float(fields[2]),
                float(fields[3]),
            )
        )

    if not vertices:
        raise AssertionError(
            f"STL contains no readable vertices: {path}",
        )

    xs = tuple(vertex[0] for vertex in vertices)
    ys = tuple(vertex[1] for vertex in vertices)
    zs = tuple(vertex[2] for vertex in vertices)

    return (
        min(xs),
        max(xs),
        min(ys),
        max(ys),
        min(zs),
        max(zs),
    )


def _stl_radii_at_z(
    path: Path,
    z: float,
    *,
    tolerance: float = 0.001,
) -> tuple[float, ...]:
    """
    Return the physical X/Y radii of STL vertices at a specified Z height.

    This permits tests to inspect where distinct horizontal surfaces terminate
    without assuming that an arbitrary radius is represented by mesh vertices.
    """

    radii: list[float] = []

    for line in path.read_text(
        encoding="utf-8",
    ).splitlines():
        fields = line.strip().split()

        if len(fields) != 4 or fields[0] != "vertex":
            continue

        x = float(fields[1])
        y = float(fields[2])
        vertex_z = float(fields[3])

        if abs(vertex_z - z) > tolerance:
            continue

        radii.append(
            (x**2 + y**2) ** 0.5,
        )

    if not radii:
        raise AssertionError(
            f"STL contains no readable vertices at Z={z}: {path}",
        )

    return tuple(
        radii,
    )


def _read_manifest(
    path: Path,
) -> dict:
    """
    Read a Shape physical-component manifest.
    """

    return json.loads(
        path.read_text(
            encoding="utf-8",
        )
    )


def _write_composition_manifest(
    path: Path,
    *,
    artwork: dict[str, object] | None = None,
) -> None:
    """
    Write the persistent registered-composition manifest used by extrusion.
    """

    path.write_text(
        json.dumps(
            {
                "composition": "composition.svg",
                "artwork": artwork,
            }
        ),
        encoding="utf-8",
    )


def _configure_extrude_context_inputs(
    context: Mock,
    *,
    composition: Path,
    composition_manifest: Path,
) -> None:
    """
    Configure the declared compose-stage inputs consumed by Shape extrusion.
    """

    context.input.side_effect = {
        "compose.composition": composition,
        "compose.manifest": composition_manifest,
    }.__getitem__


def _make_extrude_resolver(
    *,
    shape_size: float = 100.0,
    shape_base_raise: float = 2.0,
    shape_base_color: str = "white",
    shape_outer_ridge_raise: float = 1.0,
    shape_outer_ridge_style: str = "integrated",
    shape_outer_ridge_color: str = "white",
    shape_artwork_raise: float = 1.0,
    colors: dict[str, object] | None = None,
) -> Mock:
    """
    Create a resolver satisfying the Shape extrude-stage parameter contract.
    """

    resolver = Mock(
        side_effect={
            "shape_size": shape_size,
            "shape_base_raise": shape_base_raise,
            "shape_base_color": shape_base_color,
            "shape_outer_ridge_raise": shape_outer_ridge_raise,
            "shape_outer_ridge_style": shape_outer_ridge_style,
            "shape_outer_ridge_color": shape_outer_ridge_color,
            "shape_artwork_raise": shape_artwork_raise,
        }.__getitem__,
    )

    resolver.colors = {} if colors is None else colors

    return resolver


# =========================================================
# Physical dimensionalization
# =========================================================


def test_build_scad_scales_registered_composition_to_shape_size(
    tmp_path: Path,
) -> None:
    """
    Shape extrusion introduces the configured physical X/Y extent.

    Registered composition remains dimensionless until extrusion.
    shape_size scales the canonical unit Shape envelope to its physical
    manufacturing size.
    """

    composition = tmp_path / "composition.svg"

    _write_composition(
        composition,
    )

    source = extrude._build_scad(
        composition,
        shape_size=100.0,
        shape_base_raise=2.0,
        shape_outer_ridge_raise=1.0,
        shape_outer_ridge_style="integrated",
    )

    assert "shape_size = 100;" in source
    assert "scale(" in source
    assert "shape_size" in source


def test_build_scad_uses_shape_base_raise_as_physical_z(
    tmp_path: Path,
) -> None:
    """
    Shape extrusion introduces physical base thickness in Z.

    Registered composition has no physical thickness. shape_base_raise
    supplies the extrusion height at the physical boundary.
    """

    composition = tmp_path / "composition.svg"

    _write_composition(
        composition,
    )

    source = extrude._build_scad(
        composition,
        shape_size=100.0,
        shape_base_raise=2.5,
        shape_outer_ridge_raise=1.0,
        shape_outer_ridge_style="integrated",
    )

    assert "shape_base_raise = 2.5;" in source
    assert "linear_extrude(" in source
    assert "height = shape_base_raise" in source


def test_build_scad_preserves_centered_registered_origin(
    tmp_path: Path,
) -> None:
    """
    Physical dimensionalization preserves the registered Shape origin.

    The canonical Shape composition is already centered about the origin,
    so extrusion must not independently recenter its geometry from calculated
    component bounds.
    """

    composition = tmp_path / "composition.svg"

    _write_composition(
        composition,
    )

    source = extrude._build_scad(
        composition,
        shape_size=100.0,
        shape_base_raise=2.0,
        shape_outer_ridge_raise=1.0,
        shape_outer_ridge_style="integrated",
    )

    assert str(composition.resolve()) in source
    assert "center = false" in source


def test_build_scad_integrated_ridge_preserves_distinct_physical_heights(
    tmp_path: Path,
) -> None:
    """
    Integrated ridge dimensionalization preserves distinct interior and
    perimeter heights.

    The registered ridge inner boundary partitions the complete Shape into:

        interior  -> shape_base_raise
        perimeter -> shape_base_raise + shape_outer_ridge_raise

    The physical representation must therefore retain both height semantics
    rather than uniformly extruding the complete composition to one height.
    """

    composition = tmp_path / "composition.svg"

    _write_integrated_ridge_composition(
        composition,
    )

    source = extrude._build_scad(
        composition,
        shape_size=100.0,
        shape_base_raise=2.0,
        shape_outer_ridge_raise=1.0,
        shape_outer_ridge_style="integrated",
    )

    assert "shape_base_raise = 2;" in source
    assert "shape_outer_ridge_raise = 1;" in source
    assert "shape_base_raise + shape_outer_ridge_raise" in source
    assert "shape-boundary" in source
    assert "ridge-inner-boundary" in source


# =========================================================
# Physical STL geometry
# =========================================================


@pytest.mark.parametrize(
    ("shape_size", "expected_min", "expected_max"),
    [
        (50.0, -25.0, 25.0),
        (100.0, -50.0, 50.0),
        (150.0, -75.0, 75.0),
    ],
)
def test_extruded_base_has_configured_physical_xy_extent(
    tmp_path: Path,
    shape_size: float,
    expected_min: float,
    expected_max: float,
) -> None:
    """
    Extruded Shape geometry has the configured physical X/Y extent.

    Registered composition spans the canonical -0.5 through +0.5
    envelope. Physical dimensionalization scales that unit envelope
    directly to shape_size while preserving its centered origin.
    """

    composition = tmp_path / "composition.svg"
    output = tmp_path / "base.stl"

    _write_composition(
        composition,
    )

    source = extrude._build_scad(
        composition,
        shape_size=shape_size,
        shape_base_raise=2.0,
        shape_outer_ridge_raise=1.0,
        shape_outer_ridge_style="integrated",
    )

    extrude.render_stl_source(
        source,
        output,
    )

    bounds = _stl_bounds(
        output,
    )

    assert bounds[0] == pytest.approx(expected_min)
    assert bounds[1] == pytest.approx(expected_max)
    assert bounds[2] == pytest.approx(expected_min)
    assert bounds[3] == pytest.approx(expected_max)


@pytest.mark.parametrize(
    "shape_base_raise",
    [
        1.0,
        2.0,
        3.5,
    ],
)
def test_extruded_base_has_configured_physical_z_extent(
    tmp_path: Path,
    shape_base_raise: float,
) -> None:
    """
    A no-ridge Shape occupies Z=0 through shape_base_raise.

    Ridge parameters do not create ridge geometry when the registered
    composition contains no ridge partition.
    """

    composition = tmp_path / "composition.svg"
    output = tmp_path / "base.stl"

    _write_composition(
        composition,
    )

    source = extrude._build_scad(
        composition,
        shape_size=100.0,
        shape_base_raise=shape_base_raise,
        shape_outer_ridge_raise=1.0,
        shape_outer_ridge_style="integrated",
    )

    extrude.render_stl_source(
        source,
        output,
    )

    bounds = _stl_bounds(
        output,
    )

    assert bounds[4] == pytest.approx(0.0)
    assert bounds[5] == pytest.approx(shape_base_raise)


@pytest.mark.slow
def test_extruded_integrated_ridge_has_complete_physical_envelope(
    tmp_path: Path,
) -> None:
    """
    A positive integrated circle ridge reaches the configured assembled height.

    A 100 mm Shape with a 2 mm base and +1 mm integrated ridge retains the
    complete 100 mm X/Y envelope and reaches 3 mm at the perimeter.
    """

    composition = tmp_path / "composition.svg"
    output = tmp_path / "base.stl"

    _write_integrated_ridge_composition(
        composition,
    )

    source = extrude._build_scad(
        composition,
        shape_size=100.0,
        shape_base_raise=2.0,
        shape_outer_ridge_raise=1.0,
        shape_outer_ridge_style="integrated",
    )

    extrude.render_stl_source(
        source,
        output,
    )

    bounds = _stl_bounds(
        output,
    )

    assert bounds[0] == pytest.approx(-50.0)
    assert bounds[1] == pytest.approx(50.0)
    assert bounds[2] == pytest.approx(-50.0)
    assert bounds[3] == pytest.approx(50.0)
    assert bounds[4] == pytest.approx(0.0)
    assert bounds[5] == pytest.approx(3.0)


def test_separate_ridge_base_uses_registered_inner_boundary(
    tmp_path: Path,
) -> None:
    """
    A separate circle ridge reduces the physical X/Y extent of the base.

    For a 100 mm circle with a 5 mm ridge, registered composition establishes
    an outer radius of 0.5 and a ridge inner radius of 0.45. With separate
    construction, the base occupies the region inside that inner boundary:

        base -> 90 mm circle from Z=0 through Z=2

    The complete assembled Shape envelope remains 100 mm.
    """

    composition = tmp_path / "composition.svg"
    composition_manifest = tmp_path / "composition-products.json"
    manifest = tmp_path / "products.json"

    _write_integrated_ridge_composition(
        composition,
    )

    _write_composition_manifest(
        composition_manifest,
    )

    resolver = _make_extrude_resolver(
        shape_outer_ridge_style="separate",
    )

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

    extrude.execute(
        context,
    )

    base = manifest.parent / "base.stl"

    assert base.is_file()

    bounds = _stl_bounds(
        base,
    )

    assert bounds[0] == pytest.approx(-45.0)
    assert bounds[1] == pytest.approx(45.0)
    assert bounds[2] == pytest.approx(-45.0)
    assert bounds[3] == pytest.approx(45.0)
    assert bounds[4] == pytest.approx(0.0)
    assert bounds[5] == pytest.approx(2.0)


def test_separate_ridge_occupies_registered_perimeter_at_assembled_height(
    tmp_path: Path,
) -> None:
    """
    A positive separate circle ridge occupies the registered perimeter region.

    For a 100 mm circle with a 5 mm ridge, 2 mm base, and +1 mm ridge raise:

        ridge outer diameter -> 100 mm
        ridge inner diameter -> 90 mm
        ridge Z              -> 0 through 3 mm

    The ridge is therefore adjacent to the reduced base in X/Y and reaches the
    same complete assembled ridge height as the corresponding integrated ridge.
    """

    composition = tmp_path / "composition.svg"
    composition_manifest = tmp_path / "composition-products.json"
    manifest = tmp_path / "products.json"

    _write_integrated_ridge_composition(
        composition,
    )

    _write_composition_manifest(
        composition_manifest,
    )

    resolver = _make_extrude_resolver(
        shape_outer_ridge_style="separate",
    )

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

    extrude.execute(
        context,
    )

    ridge = manifest.parent / "ridge.stl"

    assert ridge.is_file()

    bounds = _stl_bounds(
        ridge,
    )

    assert bounds[0] == pytest.approx(-50.0)
    assert bounds[1] == pytest.approx(50.0)
    assert bounds[2] == pytest.approx(-50.0)
    assert bounds[3] == pytest.approx(50.0)
    assert bounds[4] == pytest.approx(0.0)
    assert bounds[5] == pytest.approx(3.0)


@pytest.mark.slow
def test_zero_raise_integrated_ridge_is_flush_with_base(
    tmp_path: Path,
) -> None:
    """
    A zero-raise integrated circle ridge is flush with the base top.

    Ridge existence is determined by ridge width rather than ridge raise.
    For a 100 mm Shape with a 2 mm base and a zero ridge raise, the
    registered perimeter region therefore continues to exist while its
    complete assembled height equals the base height:

        interior top  -> Z=2
        perimeter top -> Z=2

    The complete assembled Shape retains its 100 mm X/Y envelope.
    """

    composition = tmp_path / "composition.svg"
    output = tmp_path / "assembled.stl"

    _write_integrated_ridge_composition(
        composition,
    )

    source = extrude._build_scad(
        composition,
        shape_size=100.0,
        shape_base_raise=2.0,
        shape_outer_ridge_raise=0.0,
        shape_outer_ridge_style="integrated",
    )

    extrude.render_stl_source(
        source,
        output,
    )

    bounds = _stl_bounds(
        output,
    )

    assert bounds[0] == pytest.approx(-50.0)
    assert bounds[1] == pytest.approx(50.0)
    assert bounds[2] == pytest.approx(-50.0)
    assert bounds[3] == pytest.approx(50.0)
    assert bounds[4] == pytest.approx(0.0)
    assert bounds[5] == pytest.approx(2.0)


@pytest.mark.slow
def test_zero_raise_separate_ridge_is_flush_with_base(
    tmp_path: Path,
) -> None:
    """
    A zero-raise separate circle ridge has the same height as the base.

    Ridge existence is determined by ridge width rather than ridge raise.
    For a 100 mm Shape with a 5 mm separate ridge and a 2 mm base:

        base  -> 90 mm circle from Z=0 through Z=2
        ridge -> 100/90 mm perimeter from Z=0 through Z=2

    Base and ridge remain adjacent, independently printable components while
    their top surfaces are flush.
    """

    composition = tmp_path / "composition.svg"
    composition_manifest = tmp_path / "composition-products.json"
    manifest = tmp_path / "products.json"

    _write_integrated_ridge_composition(
        composition,
    )

    _write_composition_manifest(
        composition_manifest,
    )

    resolver = _make_extrude_resolver(
        shape_outer_ridge_raise=0.0,
        shape_outer_ridge_style="separate",
    )

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

    extrude.execute(
        context,
    )

    base = manifest.parent / "base.stl"
    ridge = manifest.parent / "ridge.stl"

    assert base.is_file()
    assert ridge.is_file()

    base_bounds = _stl_bounds(
        base,
    )
    ridge_bounds = _stl_bounds(
        ridge,
    )

    assert base_bounds[0] == pytest.approx(-45.0)
    assert base_bounds[1] == pytest.approx(45.0)
    assert base_bounds[2] == pytest.approx(-45.0)
    assert base_bounds[3] == pytest.approx(45.0)
    assert base_bounds[4] == pytest.approx(0.0)
    assert base_bounds[5] == pytest.approx(2.0)

    assert ridge_bounds[0] == pytest.approx(-50.0)
    assert ridge_bounds[1] == pytest.approx(50.0)
    assert ridge_bounds[2] == pytest.approx(-50.0)
    assert ridge_bounds[3] == pytest.approx(50.0)
    assert ridge_bounds[4] == pytest.approx(0.0)
    assert ridge_bounds[5] == pytest.approx(2.0)


@pytest.mark.slow
def test_negative_raise_integrated_ridge_recesses_base_perimeter(
    tmp_path: Path,
) -> None:
    """
    A negative integrated circle ridge recesses the base perimeter.

    For a 100 mm Shape with a 2 mm base and a -0.5 mm integrated ridge raise:

        interior top  -> Z=2.0
        perimeter top -> Z=1.5

    The registered ridge region continues to exist because ridge existence is
    determined by ridge width rather than ridge raise. The recessed perimeter
    remains base material and the complete Shape retains its 100 mm envelope.
    """

    composition = tmp_path / "composition.svg"
    output = tmp_path / "assembled.stl"

    _write_integrated_ridge_composition(
        composition,
    )

    source = extrude._build_scad(
        composition,
        shape_size=100.0,
        shape_base_raise=2.0,
        shape_outer_ridge_raise=-0.5,
        shape_outer_ridge_style="integrated",
    )

    extrude.render_stl_source(
        source,
        output,
    )

    bounds = _stl_bounds(
        output,
    )

    assert bounds[0] == pytest.approx(-50.0)
    assert bounds[1] == pytest.approx(50.0)
    assert bounds[2] == pytest.approx(-50.0)
    assert bounds[3] == pytest.approx(50.0)
    assert bounds[4] == pytest.approx(0.0)
    assert bounds[5] == pytest.approx(2.0)

    interior_top_radii = _stl_radii_at_z(
        output,
        2.0,
    )

    assert max(interior_top_radii) == pytest.approx(
        45.0,
        abs=0.1,
    )

    perimeter_top_radii = _stl_radii_at_z(
        output,
        1.5,
    )

    assert max(perimeter_top_radii) == pytest.approx(
        50.0,
        abs=0.1,
    )


def test_negative_raise_integrated_ridge_produces_only_base_component(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    A negative integrated ridge produces no independent ridge-color component.

    Integrated ridge color applies only to ridge geometry above the base top.
    With a negative ridge raise, the complete perimeter lies below that top
    and remains base material. Extrusion therefore materializes only base.stl.
    """

    composition = tmp_path / "composition.svg"
    composition_manifest = tmp_path / "composition-products.json"
    manifest = tmp_path / "products.json"

    _write_integrated_ridge_composition(
        composition,
    )

    _write_composition_manifest(
        composition_manifest,
    )

    resolver = _make_extrude_resolver(
        shape_outer_ridge_raise=-0.5,
    )

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

    rendered_outputs: list[Path] = []

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

        rendered_outputs.append(
            target,
        )

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

    assert data["components"] == [
        {
            "name": "base",
            "path": "base.stl",
            "color": {
                "name": "white",
                "rgb": [
                    255,
                    255,
                    255,
                ],
            },
        },
    ]

    assert rendered_outputs == [
        manifest.parent / "base.stl",
    ]

    assert (manifest.parent / "base.stl").is_file()
    assert not (manifest.parent / "ridge.stl").exists()


def test_negative_raise_separate_ridge_is_shorter_than_base(
    tmp_path: Path,
) -> None:
    """
    A negative separate circle ridge is shorter than its adjacent base.

    For a 100 mm Shape with a 5 mm separate ridge, 2 mm base, and
    -0.5 mm ridge raise:

        base  -> 90 mm circle from Z=0 through Z=2.0
        ridge -> 100/90 mm perimeter from Z=0 through Z=1.5

    The ridge remains an independently printable component because its
    existence is determined by its nonzero registered width.
    """

    composition = tmp_path / "composition.svg"
    composition_manifest = tmp_path / "composition-products.json"
    manifest = tmp_path / "products.json"

    _write_integrated_ridge_composition(
        composition,
    )

    _write_composition_manifest(
        composition_manifest,
    )

    resolver = _make_extrude_resolver(
        shape_outer_ridge_raise=-0.5,
        shape_outer_ridge_style="separate",
    )

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

    extrude.execute(
        context,
    )

    base = manifest.parent / "base.stl"
    ridge = manifest.parent / "ridge.stl"

    assert base.is_file()
    assert ridge.is_file()

    base_bounds = _stl_bounds(
        base,
    )
    ridge_bounds = _stl_bounds(
        ridge,
    )

    assert base_bounds[0] == pytest.approx(-45.0)
    assert base_bounds[1] == pytest.approx(45.0)
    assert base_bounds[2] == pytest.approx(-45.0)
    assert base_bounds[3] == pytest.approx(45.0)
    assert base_bounds[4] == pytest.approx(0.0)
    assert base_bounds[5] == pytest.approx(2.0)

    assert ridge_bounds[0] == pytest.approx(-50.0)
    assert ridge_bounds[1] == pytest.approx(50.0)
    assert ridge_bounds[2] == pytest.approx(-50.0)
    assert ridge_bounds[3] == pytest.approx(50.0)
    assert ridge_bounds[4] == pytest.approx(0.0)
    assert ridge_bounds[5] == pytest.approx(1.5)


@pytest.mark.slow
def test_positive_integrated_square_ridge_has_complete_physical_geometry(
    tmp_path: Path,
) -> None:
    """
    A positive integrated square ridge preserves the complete Shape envelope.

    For a 100 mm square with a 5 mm ridge, 2 mm base, and +1 mm ridge
    raise, the base occupies the complete 100x100 mm envelope through Z=2
    and the perimeter reaches the assembled ridge height of Z=3.
    """

    composition = tmp_path / "composition.svg"
    composition_manifest = tmp_path / "composition-products.json"
    manifest = tmp_path / "products.json"

    _write_square_ridge_composition(
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

    extrude.execute(
        context,
    )

    base = manifest.parent / "base.stl"
    ridge = manifest.parent / "ridge.stl"

    assert base.is_file()
    assert ridge.is_file()

    base_bounds = _stl_bounds(
        base,
    )
    ridge_bounds = _stl_bounds(
        ridge,
    )

    assert base_bounds == pytest.approx(
        (
            -50.0,
            50.0,
            -50.0,
            50.0,
            0.0,
            2.0,
        )
    )

    assert ridge_bounds == pytest.approx(
        (
            -50.0,
            50.0,
            -50.0,
            50.0,
            2.0,
            3.0,
        )
    )


@pytest.mark.slow
def test_positive_separate_square_ridge_partitions_base_and_ridge(
    tmp_path: Path,
) -> None:
    """
    A positive separate square ridge partitions the assembled Shape in X/Y.

    For a 100 mm square with a 5 mm ridge, 2 mm base, and +1 mm ridge
    raise:

        base  -> 90x90 mm from Z=0 through Z=2
        ridge -> 100x100 mm outer envelope from Z=0 through Z=3

    The components occupy adjacent, nonoverlapping registered X/Y regions.
    """

    composition = tmp_path / "composition.svg"
    composition_manifest = tmp_path / "composition-products.json"
    manifest = tmp_path / "products.json"

    _write_square_ridge_composition(
        composition,
    )

    _write_composition_manifest(
        composition_manifest,
    )

    resolver = _make_extrude_resolver(
        shape_outer_ridge_style="separate",
    )

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

    extrude.execute(
        context,
    )

    base = manifest.parent / "base.stl"
    ridge = manifest.parent / "ridge.stl"

    assert base.is_file()
    assert ridge.is_file()

    base_bounds = _stl_bounds(
        base,
    )
    ridge_bounds = _stl_bounds(
        ridge,
    )

    assert base_bounds == pytest.approx(
        (
            -45.0,
            45.0,
            -45.0,
            45.0,
            0.0,
            2.0,
        )
    )

    assert ridge_bounds == pytest.approx(
        (
            -50.0,
            50.0,
            -50.0,
            50.0,
            0.0,
            3.0,
        )
    )


def test_positive_integrated_polygon_ridge_has_complete_physical_geometry(
    tmp_path: Path,
) -> None:
    """
    A positive integrated polygon ridge preserves the complete Shape envelope.

    The base occupies the complete registered polygon through the base top,
    while the ridge component occupies its perimeter above the base.
    """

    composition = tmp_path / "composition.svg"
    composition_manifest = tmp_path / "composition-products.json"
    manifest = tmp_path / "products.json"

    _write_polygon_ridge_composition(
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

    extrude.execute(
        context,
    )

    base = manifest.parent / "base.stl"
    ridge = manifest.parent / "ridge.stl"

    assert base.is_file()
    assert ridge.is_file()

    base_bounds = _stl_bounds(
        base,
    )
    ridge_bounds = _stl_bounds(
        ridge,
    )

    assert base_bounds == pytest.approx(
        (
            -50.0,
            50.0,
            -50.0,
            50.0,
            0.0,
            2.0,
        )
    )

    assert ridge_bounds == pytest.approx(
        (
            -50.0,
            50.0,
            -50.0,
            50.0,
            2.0,
            3.0,
        )
    )


def test_positive_separate_polygon_ridge_partitions_physical_geometry(
    tmp_path: Path,
) -> None:
    """
    A positive separate polygon ridge partitions the assembled Shape.

    The base occupies the polygon inside the registered ridge boundary while
    the independent ridge occupies the surrounding perimeter through the
    complete assembled ridge height.
    """

    composition = tmp_path / "composition.svg"
    composition_manifest = tmp_path / "composition-products.json"
    manifest = tmp_path / "products.json"

    _write_polygon_ridge_composition(
        composition,
    )

    _write_composition_manifest(
        composition_manifest,
    )

    resolver = _make_extrude_resolver(
        shape_outer_ridge_style="separate",
    )

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

    extrude.execute(
        context,
    )

    base = manifest.parent / "base.stl"
    ridge = manifest.parent / "ridge.stl"

    assert base.is_file()
    assert ridge.is_file()

    base_bounds = _stl_bounds(
        base,
    )
    ridge_bounds = _stl_bounds(
        ridge,
    )

    assert base_bounds[0] > -50.0
    assert base_bounds[1] < 50.0
    assert base_bounds[2] > -50.0
    assert base_bounds[3] < 50.0
    assert base_bounds[4] == pytest.approx(
        0.0,
    )
    assert base_bounds[5] == pytest.approx(
        2.0,
    )

    assert ridge_bounds == pytest.approx(
        (
            -50.0,
            50.0,
            -50.0,
            50.0,
            0.0,
            3.0,
        )
    )


# =========================================================
# Extrude stage execution
# =========================================================


def test_extrude_stage_materializes_declared_component_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Shape extrusion materializes its declared physical-component manifest.

    Physical STL components are members of the manifest rather than
    independently declared stage products. This permits component membership
    to vary according to Shape structure while retaining one stable,
    independently verifiable stage product.
    """

    composition = tmp_path / "arbitrary-input" / "composition.svg"
    composition_manifest = tmp_path / "composition-products.json"
    manifest = tmp_path / "arbitrary-output" / "products.json"

    _write_composition(
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

    rendered_sources: list[str] = []
    rendered_outputs: list[Path] = []

    def fake_render_stl_source(
        source: str,
        target: Path,
    ) -> None:
        rendered_sources.append(
            source,
        )
        rendered_outputs.append(
            target,
        )

        target.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        target.write_text(
            "stl",
            encoding="utf-8",
        )

    monkeypatch.setattr(
        extrude,
        "render_stl_source",
        fake_render_stl_source,
    )

    extrude.execute(
        context,
    )

    assert context.input.call_args_list == [
        call("compose.composition"),
        call("compose.manifest"),
    ]
    context.output.assert_called_once_with(
        "manifest",
    )

    assert resolver.call_args_list == [
        call("shape_size"),
        call("shape_base_raise"),
        call("shape_base_color"),
        call("shape_outer_ridge_color"),
        call("shape_outer_ridge_raise"),
        call("shape_outer_ridge_style"),
    ]

    assert manifest.is_file()

    data = _read_manifest(
        manifest,
    )

    assert data["components"] == [
        {
            "name": "base",
            "path": "base.stl",
            "color": {
                "name": "white",
                "rgb": [
                    255,
                    255,
                    255,
                ],
            },
        },
    ]

    assert rendered_outputs == [
        manifest.parent / "base.stl",
    ]

    assert len(rendered_sources) == 1
    assert str(composition.resolve()) in rendered_sources[0]


def test_no_ridge_component_manifest_contains_only_base(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    A Shape without a ridge has exactly one physical structural component.

    Ridge existence is represented by the registered composition produced
    upstream. When no ridge partition exists, extrusion records only the
    physical base component.
    """

    composition = tmp_path / "composition.svg"
    composition_manifest = tmp_path / "composition-products.json"
    manifest = tmp_path / "products.json"

    _write_composition(
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

    assert tuple(component["name"] for component in data["components"]) == ("base",)

    assert (manifest.parent / "base.stl").is_file()
    assert not (manifest.parent / "ridge.stl").exists()


def test_integrated_ridge_component_manifest_contains_base_and_ridge(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    An integrated ridge remains a distinct physical component.

    Structural integration determines the assembled geometry but does not
    erase ridge component identity. Base and ridge remain independently
    identifiable so downstream packaging can preserve independent printing
    properties such as color.
    """

    composition = tmp_path / "composition.svg"
    composition_manifest = tmp_path / "composition-products.json"
    manifest = tmp_path / "products.json"

    _write_integrated_ridge_composition(
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

    rendered_outputs: list[Path] = []

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

        rendered_outputs.append(
            target,
        )

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

    assert data["components"] == [
        {
            "name": "base",
            "path": "base.stl",
            "color": {
                "name": "white",
                "rgb": [
                    255,
                    255,
                    255,
                ],
            },
        },
        {
            "name": "ridge",
            "path": "ridge.stl",
            "color": {
                "name": "white",
                "rgb": [
                    255,
                    255,
                    255,
                ],
            },
        },
    ]

    assert rendered_outputs == [
        manifest.parent / "base.stl",
        manifest.parent / "ridge.stl",
    ]

    assert (manifest.parent / "base.stl").is_file()
    assert (manifest.parent / "ridge.stl").is_file()


def test_integrated_ridge_components_preserve_physical_partition(
    tmp_path: Path,
) -> None:
    """
    Integrated ridge component geometry preserves the intended partition.

    For a 100 mm circle with a 2 mm base and a +1 mm ridge:

        base  -> complete 100 mm circle from Z=0 through Z=2
        ridge -> 100/90 mm perimeter from Z=2 through Z=3

    Independent component identity therefore preserves the intended assembled
    geometry rather than changing the structural meaning of an integrated
    ridge.
    """

    composition = tmp_path / "composition.svg"
    composition_manifest = tmp_path / "composition-products.json"
    manifest = tmp_path / "products.json"

    _write_integrated_ridge_composition(
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

    extrude.execute(
        context,
    )

    base = manifest.parent / "base.stl"
    ridge = manifest.parent / "ridge.stl"

    assert base.is_file()
    assert ridge.is_file()

    base_bounds = _stl_bounds(
        base,
    )
    ridge_bounds = _stl_bounds(
        ridge,
    )

    assert base_bounds[0] == pytest.approx(-50.0)
    assert base_bounds[1] == pytest.approx(50.0)
    assert base_bounds[2] == pytest.approx(-50.0)
    assert base_bounds[3] == pytest.approx(50.0)
    assert base_bounds[4] == pytest.approx(0.0)
    assert base_bounds[5] == pytest.approx(2.0)

    assert ridge_bounds[0] == pytest.approx(-50.0)
    assert ridge_bounds[1] == pytest.approx(50.0)
    assert ridge_bounds[2] == pytest.approx(-50.0)
    assert ridge_bounds[3] == pytest.approx(50.0)
    assert ridge_bounds[4] == pytest.approx(2.0)
    assert ridge_bounds[5] == pytest.approx(3.0)


def test_integrated_ridge_accepts_minimum_raise(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    An integrated ridge accepts the minimum raise producing zero perimeter height.

    At shape_outer_ridge_raise = -shape_base_raise, the registered ridge
    continues to exist while its perimeter has zero physical height.
    The interior base remains at shape_base_raise.
    """

    composition = tmp_path / "composition.svg"
    composition_manifest = tmp_path / "composition-products.json"
    manifest = tmp_path / "products.json"

    _write_integrated_ridge_composition(
        composition,
    )

    _write_composition_manifest(
        composition_manifest,
    )

    resolver = _make_extrude_resolver(
        shape_outer_ridge_raise=-2.0,
    )

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

    rendered_sources: list[str] = []
    rendered_outputs: list[Path] = []

    def fake_render_stl_source(
        source: str,
        target: Path,
    ) -> None:
        rendered_sources.append(source)
        rendered_outputs.append(target)

        target.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        target.write_text(
            "stl",
            encoding="utf-8",
        )

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

    assert data["components"] == [
        {
            "name": "base",
            "path": "base.stl",
            "color": {
                "name": "white",
                "rgb": [
                    255,
                    255,
                    255,
                ],
            },
        },
    ]

    assert rendered_outputs == [
        manifest.parent / "base.stl",
    ]

    assert len(rendered_sources) == 1
    assert "shape_base_raise + shape_outer_ridge_raise" in rendered_sources[0]


def test_separate_ridge_accepts_minimum_raise_without_physical_ridge_volume(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    A separate ridge accepts the minimum raise producing zero physical height.

    At shape_outer_ridge_raise = -shape_base_raise, the ridge remains
    semantically defined by its registered nonzero width, but it has no
    dimensionalized physical volume to materialize as an STL component.
    """

    composition = tmp_path / "composition.svg"
    composition_manifest = tmp_path / "composition-products.json"
    manifest = tmp_path / "products.json"

    _write_integrated_ridge_composition(
        composition,
    )

    _write_composition_manifest(
        composition_manifest,
    )

    resolver = _make_extrude_resolver(
        shape_outer_ridge_raise=-2.0,
        shape_outer_ridge_style="separate",
    )

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

    rendered_outputs: list[Path] = []

    def fake_render_stl_source(
        source: str,
        target: Path,
    ) -> None:
        rendered_outputs.append(target)

        target.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        target.write_text(
            "stl",
            encoding="utf-8",
        )

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

    assert data["components"] == [
        {
            "name": "base",
            "path": "base.stl",
            "color": {
                "name": "white",
                "rgb": [
                    255,
                    255,
                    255,
                ],
            },
        },
    ]

    assert rendered_outputs == [
        manifest.parent / "base.stl",
    ]

    assert (manifest.parent / "base.stl").is_file()
    assert not (manifest.parent / "ridge.stl").exists()


@pytest.mark.parametrize(
    "ridge_style",
    [
        "integrated",
        "separate",
    ],
)
def test_extrude_rejects_ridge_raise_below_negative_base_raise(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    ridge_style: str,
) -> None:
    """
    Ridge extrusion rejects a negative assembled physical height.

    The minimum valid ridge raise is -shape_base_raise for both integrated
    and separate ridge styles.
    """

    composition = tmp_path / "composition.svg"
    composition_manifest = tmp_path / "composition-products.json"
    manifest = tmp_path / "products.json"

    _write_integrated_ridge_composition(
        composition,
    )

    _write_composition_manifest(
        composition_manifest,
    )

    resolver = _make_extrude_resolver(
        shape_outer_ridge_raise=-2.5,
        shape_outer_ridge_style=ridge_style,
    )

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

    render_stl_source = Mock()

    monkeypatch.setattr(
        extrude,
        "render_stl_source",
        render_stl_source,
    )

    with pytest.raises(
        extrude.ExtrudeError,
        match="ridge",
    ):
        extrude.execute(
            context,
        )

    render_stl_source.assert_not_called()


# =========================================================
# Stage registration
# =========================================================


def test_shape_registers_extrude_stage_implementation() -> None:
    """
    Shape contributes its extrusion implementation through its stage package.
    """

    registry = Mock()

    stages.register_stage_implementations(
        registry,
    )

    assert (
        call(
            "shape",
            "extrude",
            extrude.execute,
        )
        in registry.register.call_args_list
    )


def test_engine_bootstrap_discovers_shape_extrude_implementation() -> None:
    """
    Normal engine bootstrap discovers the executable Shape extrude stage.
    """

    registry = build_stage_registry()

    implementation = registry.get(
        "shape",
        "extrude",
    )

    assert implementation is extrude.execute


@pytest.mark.slow
def test_positive_integrated_and_separate_ridges_have_equivalent_assembled_geometry(
    tmp_path: Path,
) -> None:
    """
    Positive integrated and separate ridges describe the same assembled geometry.

    Ridge style changes component partitioning, not the intended physical
    Shape. For a 100 mm circle with a 5 mm ridge, 2 mm base, and +1 mm raise,
    both styles have a 90 mm interior at 2 mm and a 100 mm perimeter at 3 mm.
    """

    composition = tmp_path / "composition.svg"

    _write_integrated_ridge_composition(
        composition,
    )

    integrated = tmp_path / "integrated.stl"

    ridge = extrude._load_circle_ridge(
        composition,
    )

    assert ridge is not None

    integrated_source = extrude._build_integrated_circle_ridge_scad(
        ridge,
        shape_size=100.0,
        shape_base_raise=2.0,
        shape_outer_ridge_raise=1.0,
    )

    extrude.render_stl_source(
        integrated_source,
        integrated,
    )

    separate_base = tmp_path / "separate-base.stl"
    separate_ridge = tmp_path / "separate-ridge.stl"

    separate_base_source = extrude._build_circle_base_scad(
        ridge.inner,
        shape_size=100.0,
        shape_base_raise=2.0,
    )

    separate_ridge_source = extrude._build_separate_circle_ridge_component_scad(
        ridge,
        shape_size=100.0,
        shape_base_raise=2.0,
        shape_outer_ridge_raise=1.0,
    )

    extrude.render_stl_source(
        separate_base_source,
        separate_base,
    )

    extrude.render_stl_source(
        separate_ridge_source,
        separate_ridge,
    )

    integrated_bounds = _stl_bounds(
        integrated,
    )
    separate_base_bounds = _stl_bounds(
        separate_base,
    )
    separate_ridge_bounds = _stl_bounds(
        separate_ridge,
    )

    assert integrated_bounds == pytest.approx(
        (
            -50.0,
            50.0,
            -50.0,
            50.0,
            0.0,
            3.0,
        )
    )

    assert separate_base_bounds == pytest.approx(
        (
            -45.0,
            45.0,
            -45.0,
            45.0,
            0.0,
            2.0,
        )
    )

    assert separate_ridge_bounds == pytest.approx(
        (
            -50.0,
            50.0,
            -50.0,
            50.0,
            50.0 * 0.0,
            3.0,
        )
    )

    integrated_base_radii = _stl_radii_at_z(
        integrated,
        2.0,
    )
    integrated_ridge_radii = _stl_radii_at_z(
        integrated,
        3.0,
    )

    assert min(integrated_base_radii) == pytest.approx(
        45.0,
        abs=0.01,
    )
    assert max(integrated_ridge_radii) == pytest.approx(
        50.0,
        abs=0.01,
    )


@pytest.mark.slow
def test_negative_integrated_and_separate_ridges_have_equivalent_assembled_geometry(
    tmp_path: Path,
) -> None:
    """
    Negative integrated and separate ridges describe the same assembled geometry.

    With a 2 mm base and -0.5 mm ridge raise, both constructions have a
    90 mm interior reaching Z=2 and a 5 mm perimeter reaching Z=1.5.
    """

    composition = tmp_path / "composition.svg"

    _write_integrated_ridge_composition(
        composition,
    )

    ridge = extrude._load_circle_ridge(
        composition,
    )

    assert ridge is not None

    integrated = tmp_path / "integrated.stl"

    integrated_source = extrude._build_integrated_circle_ridge_scad(
        ridge,
        shape_size=100.0,
        shape_base_raise=2.0,
        shape_outer_ridge_raise=-0.5,
    )

    extrude.render_stl_source(
        integrated_source,
        integrated,
    )

    separate_base = tmp_path / "separate-base.stl"
    separate_ridge = tmp_path / "separate-ridge.stl"

    extrude.render_stl_source(
        extrude._build_circle_base_scad(
            ridge.inner,
            shape_size=100.0,
            shape_base_raise=2.0,
        ),
        separate_base,
    )

    extrude.render_stl_source(
        extrude._build_separate_circle_ridge_component_scad(
            ridge,
            shape_size=100.0,
            shape_base_raise=2.0,
            shape_outer_ridge_raise=-0.5,
        ),
        separate_ridge,
    )

    integrated_interior_radii = _stl_radii_at_z(
        integrated,
        2.0,
    )
    integrated_perimeter_radii = _stl_radii_at_z(
        integrated,
        1.5,
    )

    separate_base_top_radii = _stl_radii_at_z(
        separate_base,
        2.0,
    )
    separate_ridge_top_radii = _stl_radii_at_z(
        separate_ridge,
        1.5,
    )

    assert max(integrated_interior_radii) == pytest.approx(
        max(separate_base_top_radii),
        abs=0.01,
    )

    assert min(integrated_perimeter_radii) == pytest.approx(
        min(separate_ridge_top_radii),
        abs=0.01,
    )

    assert max(integrated_perimeter_radii) == pytest.approx(
        max(separate_ridge_top_radii),
        abs=0.01,
    )

    assert max(integrated_interior_radii) == pytest.approx(
        45.0,
        abs=0.01,
    )

    assert max(integrated_perimeter_radii) == pytest.approx(
        50.0,
        abs=0.01,
    )


def test_zero_raise_separate_square_ridge_is_flush_with_base(
    tmp_path: Path,
) -> None:
    """
    A zero-raise separate square ridge remains a physical component.

    Ridge existence is determined by registered ridge width rather than raise.
    For a 100 mm square with a 5 mm ridge and 2 mm base:

        base  -> 90x90 mm from Z=0 through Z=2
        ridge -> surrounding perimeter from Z=0 through Z=2

    The complete assembled surface is therefore flush at Z=2.
    """

    composition = tmp_path / "composition.svg"
    composition_manifest = tmp_path / "composition-products.json"
    manifest = tmp_path / "products.json"

    _write_square_ridge_composition(
        composition,
    )

    _write_composition_manifest(
        composition_manifest,
    )

    resolver = _make_extrude_resolver(
        shape_outer_ridge_raise=0.0,
        shape_outer_ridge_style="separate",
    )

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

    extrude.execute(
        context,
    )

    base = manifest.parent / "base.stl"
    ridge = manifest.parent / "ridge.stl"

    assert base.is_file()
    assert ridge.is_file()

    assert _stl_bounds(base) == pytest.approx(
        (
            -45.0,
            45.0,
            -45.0,
            45.0,
            0.0,
            2.0,
        )
    )

    assert _stl_bounds(ridge) == pytest.approx(
        (
            -50.0,
            50.0,
            -50.0,
            50.0,
            0.0,
            2.0,
        )
    )


def test_negative_raise_integrated_square_ridge_recesses_base_perimeter(
    tmp_path: Path,
) -> None:
    """
    A negative integrated square ridge recesses the base perimeter.

    For a 100 mm square with a 5 mm ridge, 2 mm base, and -0.5 mm
    ridge raise:

        interior 90x90 mm -> Z=0 through Z=2
        perimeter         -> Z=0 through Z=1.5

    No independently printable ridge-color component exists above the base.
    """

    composition = tmp_path / "composition.svg"
    composition_manifest = tmp_path / "composition-products.json"
    manifest = tmp_path / "products.json"

    _write_square_ridge_composition(
        composition,
    )

    _write_composition_manifest(
        composition_manifest,
    )

    resolver = _make_extrude_resolver(
        shape_outer_ridge_raise=-0.5,
    )

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

    extrude.execute(
        context,
    )

    base = manifest.parent / "base.stl"
    ridge = manifest.parent / "ridge.stl"

    assert base.is_file()
    assert not ridge.exists()

    bounds = _stl_bounds(
        base,
    )

    assert bounds == pytest.approx(
        (
            -50.0,
            50.0,
            -50.0,
            50.0,
            0.0,
            2.0,
        )
    )

    vertices_at_base_top: list[tuple[float, float]] = []

    for line in base.read_text(
        encoding="utf-8",
    ).splitlines():
        fields = line.strip().split()

        if len(fields) != 4 or fields[0] != "vertex":
            continue

        x = float(fields[1])
        y = float(fields[2])
        z = float(fields[3])

        if z == pytest.approx(2.0):
            vertices_at_base_top.append(
                (
                    x,
                    y,
                )
            )

    assert vertices_at_base_top

    assert max(
        abs(coordinate) for vertex in vertices_at_base_top for coordinate in vertex
    ) == pytest.approx(45.0)


def test_negative_integrated_and_separate_square_ridges_have_equivalent_assembled_geometry(
    tmp_path: Path,
) -> None:
    """
    Integrated and separate negative square ridges describe the same assembly.

    With a 2 mm base and -0.5 mm ridge raise, both styles describe:

        interior 90x90 mm -> Z=0 through Z=2
        perimeter         -> Z=0 through Z=1.5

    Ridge style changes component partitioning, not assembled geometry.
    """

    composition = tmp_path / "composition.svg"

    _write_square_ridge_composition(
        composition,
    )

    ridge = extrude._load_ridge(
        composition,
    )

    assert isinstance(
        ridge,
        extrude.RegisteredSquareRidge,
    )

    integrated_source = extrude._build_integrated_square_ridge_scad(
        ridge,
        shape_size=100.0,
        shape_base_raise=2.0,
        shape_outer_ridge_raise=-0.5,
    )

    integrated = tmp_path / "integrated.stl"

    extrude.render_stl_source(
        integrated_source,
        integrated,
    )

    separate_base_source = extrude._build_rectangle_base_scad(
        ridge.inner,
        shape_size=100.0,
        shape_base_raise=2.0,
    )

    separate_ridge_source = extrude._build_separate_square_ridge_component_scad(
        ridge,
        shape_size=100.0,
        shape_base_raise=2.0,
        shape_outer_ridge_raise=-0.5,
    )

    separate_base = tmp_path / "separate-base.stl"
    separate_ridge = tmp_path / "separate-ridge.stl"

    extrude.render_stl_source(
        separate_base_source,
        separate_base,
    )
    extrude.render_stl_source(
        separate_ridge_source,
        separate_ridge,
    )

    assert _stl_bounds(integrated) == pytest.approx(
        (
            -50.0,
            50.0,
            -50.0,
            50.0,
            0.0,
            2.0,
        )
    )

    assert _stl_bounds(separate_base) == pytest.approx(
        (
            -45.0,
            45.0,
            -45.0,
            45.0,
            0.0,
            2.0,
        )
    )

    assert _stl_bounds(separate_ridge) == pytest.approx(
        (
            -50.0,
            50.0,
            -50.0,
            50.0,
            0.0,
            1.5,
        )
    )


def test_zero_raise_separate_polygon_ridge_is_flush_with_base(
    tmp_path: Path,
) -> None:
    """
    A zero-raise separate polygon ridge remains a physical ridge component.

    Ridge existence is determined by ridge width rather than ridge raise.
    The base and ridge therefore remain adjacent independently printable
    components whose top surfaces are both at the base height.
    """

    composition = tmp_path / "composition.svg"
    composition_manifest = tmp_path / "composition-products.json"
    manifest = tmp_path / "products.json"

    _write_polygon_ridge_composition(
        composition,
    )

    _write_composition_manifest(
        composition_manifest,
    )

    resolver = _make_extrude_resolver(
        shape_outer_ridge_raise=0.0,
        shape_outer_ridge_style="separate",
    )

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

    extrude.execute(
        context,
    )

    base = manifest.parent / "base.stl"
    ridge = manifest.parent / "ridge.stl"

    assert base.is_file()
    assert ridge.is_file()

    base_bounds = _stl_bounds(
        base,
    )
    ridge_bounds = _stl_bounds(
        ridge,
    )

    assert base_bounds[4] == pytest.approx(0.0)
    assert base_bounds[5] == pytest.approx(2.0)

    assert ridge_bounds[4] == pytest.approx(0.0)
    assert ridge_bounds[5] == pytest.approx(2.0)


def test_negative_raise_separate_polygon_ridge_is_shorter_than_base(
    tmp_path: Path,
) -> None:
    """
    A negative separate polygon ridge remains independently printable.

    The base retains the configured base height while the surrounding
    polygon ridge terminates at the reduced assembled ridge height.
    """

    composition = tmp_path / "composition.svg"
    composition_manifest = tmp_path / "composition-products.json"
    manifest = tmp_path / "products.json"

    _write_polygon_ridge_composition(
        composition,
    )

    _write_composition_manifest(
        composition_manifest,
    )

    resolver = _make_extrude_resolver(
        shape_outer_ridge_raise=-0.5,
        shape_outer_ridge_style="separate",
    )

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

    extrude.execute(
        context,
    )

    base = manifest.parent / "base.stl"
    ridge = manifest.parent / "ridge.stl"

    assert base.is_file()
    assert ridge.is_file()

    base_bounds = _stl_bounds(
        base,
    )
    ridge_bounds = _stl_bounds(
        ridge,
    )

    assert base_bounds[4] == pytest.approx(0.0)
    assert base_bounds[5] == pytest.approx(2.0)

    assert ridge_bounds[4] == pytest.approx(0.0)
    assert ridge_bounds[5] == pytest.approx(1.5)


def test_negative_raise_integrated_polygon_ridge_recesses_base_perimeter(
    tmp_path: Path,
) -> None:
    """
    A negative integrated polygon ridge recesses the base perimeter.

    The polygon interior remains at the complete base height while the
    registered perimeter terminates at the reduced assembled ridge height.
    No independently colored ridge volume exists above the base.
    """

    composition = tmp_path / "composition.svg"
    composition_manifest = tmp_path / "composition-products.json"
    manifest = tmp_path / "products.json"

    _write_polygon_ridge_composition(
        composition,
    )

    _write_composition_manifest(
        composition_manifest,
    )

    resolver = _make_extrude_resolver(
        shape_outer_ridge_raise=-0.5,
    )

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

    extrude.execute(
        context,
    )

    base = manifest.parent / "base.stl"

    assert base.is_file()
    assert not (manifest.parent / "ridge.stl").exists()

    bounds = _stl_bounds(
        base,
    )

    assert bounds[0] == pytest.approx(-50.0)
    assert bounds[1] == pytest.approx(50.0)
    assert bounds[2] == pytest.approx(-50.0)
    assert bounds[3] == pytest.approx(50.0)
    assert bounds[4] == pytest.approx(0.0)
    assert bounds[5] == pytest.approx(2.0)


def test_positive_polygon_ridge_styles_have_equivalent_assembled_geometry(
    tmp_path: Path,
) -> None:
    """
    Integrated and separate positive polygon ridges have the same assembled geometry.

    Ridge style changes how the Shape is partitioned into independently
    printable components, not the intended complete physical structure.
    """

    composition = tmp_path / "composition.svg"
    integrated = tmp_path / "integrated.stl"
    separate = tmp_path / "separate.stl"

    _write_polygon_ridge_composition(
        composition,
    )

    integrated_source = extrude._build_scad(
        composition,
        shape_size=100.0,
        shape_base_raise=2.0,
        shape_outer_ridge_raise=1.0,
        shape_outer_ridge_style="integrated",
    )

    separate_source = extrude._build_scad(
        composition,
        shape_size=100.0,
        shape_base_raise=2.0,
        shape_outer_ridge_raise=1.0,
        shape_outer_ridge_style="separate",
    )

    extrude.render_stl_source(
        integrated_source,
        integrated,
    )
    extrude.render_stl_source(
        separate_source,
        separate,
    )

    assert _stl_bounds(integrated) == pytest.approx(
        _stl_bounds(separate),
    )


def test_negative_polygon_ridge_styles_have_equivalent_assembled_geometry(
    tmp_path: Path,
) -> None:
    """
    Integrated and separate negative polygon ridges have the same assembled geometry.

    A negative ridge raise recesses the polygon perimeter in either style.
    Style changes component partitioning while preserving the complete
    intended physical Shape.
    """

    composition = tmp_path / "composition.svg"
    integrated = tmp_path / "integrated.stl"
    separate = tmp_path / "separate.stl"

    _write_polygon_ridge_composition(
        composition,
    )

    integrated_source = extrude._build_scad(
        composition,
        shape_size=100.0,
        shape_base_raise=2.0,
        shape_outer_ridge_raise=-0.5,
        shape_outer_ridge_style="integrated",
    )

    separate_source = extrude._build_scad(
        composition,
        shape_size=100.0,
        shape_base_raise=2.0,
        shape_outer_ridge_raise=-0.5,
        shape_outer_ridge_style="separate",
    )

    extrude.render_stl_source(
        integrated_source,
        integrated,
    )
    extrude.render_stl_source(
        separate_source,
        separate,
    )

    assert _stl_bounds(integrated) == pytest.approx(
        _stl_bounds(separate),
    )


def test_load_ridge_treats_shape_boundary_without_inner_boundary_as_no_ridge(
    tmp_path: Path,
) -> None:
    """
    A registered Shape boundary without a ridge inner boundary
    represents a Shape without an outer ridge.
    """

    composition = tmp_path / "composition.svg"

    composition.write_text(
        """
<svg xmlns="http://www.w3.org/2000/svg"
     viewBox="-0.5 -0.5 1 1">
  <circle
      id="shape-boundary"
      cx="0"
      cy="0"
      r="0.5" />
</svg>
""".strip(),
        encoding="utf-8",
    )

    ridge = _load_ridge(
        composition,
    )

    assert ridge is None


def test_load_ridge_rejects_inner_boundary_without_shape_boundary(
    tmp_path: Path,
) -> None:
    """
    A ridge inner boundary without its Shape outer boundary
    is an invalid registered composition.
    """

    composition = tmp_path / "composition.svg"

    composition.write_text(
        """
<svg xmlns="http://www.w3.org/2000/svg"
     viewBox="-0.5 -0.5 1 1">
  <circle
      id="ridge-inner-boundary"
      cx="0"
      cy="0"
      r="0.45" />
</svg>
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="ridge inner boundary without a Shape outer boundary",
    ):
        _load_ridge(
            composition,
        )


def test_base_component_manifest_preserves_semantic_color(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Shape extrusion preserves semantic color identity for the base component.

    Physical components identify both their structural role and their
    resolved semantic printing color.
    """

    composition = tmp_path / "composition.svg"
    composition_manifest = tmp_path / "composition-products.json"
    manifest = tmp_path / "products.json"

    _write_composition(
        composition,
    )

    _write_composition_manifest(
        composition_manifest,
    )

    resolver = _make_extrude_resolver(
        shape_base_color="red",
        colors={
            "red": {
                "rgb": [
                    220,
                    38,
                    38,
                ],
            },
        },
    )

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

    assert data["components"] == [
        {
            "name": "base",
            "path": "base.stl",
            "color": {
                "name": "red",
                "rgb": [
                    220,
                    38,
                    38,
                ],
            },
        },
    ]


def test_positive_integrated_ridge_manifest_preserves_semantic_color(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    A positive integrated ridge preserves its independent semantic color.

    Only the physical ridge volume above the base top is represented by the
    ridge component, so that component carries shape_outer_ridge_color.
    """

    composition = tmp_path / "composition.svg"
    composition_manifest = tmp_path / "composition-products.json"
    manifest = tmp_path / "products.json"

    _write_integrated_ridge_composition(
        composition,
    )

    _write_composition_manifest(
        composition_manifest,
    )

    resolver = _make_extrude_resolver(
        shape_base_color="white",
        shape_outer_ridge_color="red",
        colors={
            "red": {
                "rgb": [
                    220,
                    38,
                    38,
                ],
            },
        },
    )

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

    assert data["components"] == [
        {
            "name": "base",
            "path": "base.stl",
            "color": {
                "name": "white",
                "rgb": [
                    255,
                    255,
                    255,
                ],
            },
        },
        {
            "name": "ridge",
            "path": "ridge.stl",
            "color": {
                "name": "red",
                "rgb": [
                    220,
                    38,
                    38,
                ],
            },
        },
    ]


def test_separate_ridge_manifest_preserves_semantic_color(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    A physical separate ridge preserves its independent semantic color.

    Base and ridge are independently printable components and therefore
    retain their independently resolved semantic printing colors.
    """

    composition = tmp_path / "composition.svg"
    composition_manifest = tmp_path / "composition-products.json"
    manifest = tmp_path / "products.json"

    _write_integrated_ridge_composition(
        composition,
    )

    _write_composition_manifest(
        composition_manifest,
    )

    resolver = _make_extrude_resolver(
        shape_base_color="white",
        shape_outer_ridge_color="red",
        shape_outer_ridge_style="separate",
        colors={
            "red": {
                "rgb": [
                    220,
                    38,
                    38,
                ],
            },
        },
    )

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

    assert data["components"] == [
        {
            "name": "base",
            "path": "base.stl",
            "color": {
                "name": "white",
                "rgb": [
                    255,
                    255,
                    255,
                ],
            },
        },
        {
            "name": "ridge",
            "path": "ridge.stl",
            "color": {
                "name": "red",
                "rgb": [
                    220,
                    38,
                    38,
                ],
            },
        },
    ]


def test_ridge_color_does_not_create_component_without_ridge(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Ridge color configuration does not create physical ridge geometry.

    A registered composition without a ridge produces only the base component
    even when an independent ridge color is configured.
    """

    composition = tmp_path / "composition.svg"
    composition_manifest = tmp_path / "composition-products.json"
    manifest = tmp_path / "products.json"

    _write_composition(
        composition,
    )

    _write_composition_manifest(
        composition_manifest,
    )

    resolver = _make_extrude_resolver(
        shape_base_color="white",
        shape_outer_ridge_color="red",
    )

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

    assert data["components"] == [
        {
            "name": "base",
            "path": "base.stl",
            "color": {
                "name": "white",
                "rgb": [
                    255,
                    255,
                    255,
                ],
            },
        },
    ]


@pytest.mark.parametrize(
    "shape_outer_ridge_raise",
    [
        0.0,
        -0.5,
    ],
)
def test_integrated_nonpositive_ridge_has_no_independent_color_component(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    shape_outer_ridge_raise: float,
) -> None:
    """
    A nonpositive integrated ridge has no independently colored ridge volume.

    The registered ridge remains structurally meaningful, but its configured
    color cannot manufacture a physical component above the base top.
    """

    composition = tmp_path / "composition.svg"
    composition_manifest = tmp_path / "composition-products.json"
    manifest = tmp_path / "products.json"

    _write_integrated_ridge_composition(
        composition,
    )

    _write_composition_manifest(
        composition_manifest,
    )

    resolver = _make_extrude_resolver(
        shape_base_color="white",
        shape_outer_ridge_color="red",
        shape_outer_ridge_raise=shape_outer_ridge_raise,
        shape_outer_ridge_style="integrated",
    )

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

    assert data["components"] == [
        {
            "name": "base",
            "path": "base.stl",
            "color": {
                "name": "white",
                "rgb": [
                    255,
                    255,
                    255,
                ],
            },
        },
    ]


def test_zero_height_separate_ridge_has_no_independent_color_component(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    A zero-height separate ridge has no physical color component.

    The ridge remains semantically defined, but color metadata does not cause
    zero-volume physical geometry to be emitted.
    """

    composition = tmp_path / "composition.svg"
    composition_manifest = tmp_path / "composition-products.json"
    manifest = tmp_path / "products.json"

    _write_integrated_ridge_composition(
        composition,
    )

    _write_composition_manifest(
        composition_manifest,
    )

    resolver = _make_extrude_resolver(
        shape_base_raise=2.0,
        shape_base_color="white",
        shape_outer_ridge_color="red",
        shape_outer_ridge_raise=-2.0,
        shape_outer_ridge_style="separate",
    )

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

    assert data["components"] == [
        {
            "name": "base",
            "path": "base.stl",
            "color": {
                "name": "white",
                "rgb": [
                    255,
                    255,
                    255,
                ],
            },
        },
    ]


def test_execute_rejects_nonpositive_artwork_raise_when_artwork_is_incorporated(
    tmp_path: Path,
) -> None:
    """
    Incorporated Artwork must have positive physical height.

    Shape owns the physical Z semantics of incorporated Artwork, so an
    incorporated Artwork component requires shape_artwork_raise > 0.
    """

    composition = tmp_path / "composition.svg"
    composition_manifest = tmp_path / "composition-products.json"
    output_manifest = tmp_path / "products.json"

    _write_composition(
        composition,
    )

    _write_composition_manifest(
        composition_manifest,
        artwork={
            "manifest": "artwork/products.json",
        },
    )

    resolver = _make_extrude_resolver(
        shape_artwork_raise=0.0,
    )

    context = Mock(
        spec=StageContext,
    )
    context.resolver = resolver
    _configure_extrude_context_inputs(
        context,
        composition=composition,
        composition_manifest=composition_manifest,
    )
    context.output.return_value = output_manifest

    with pytest.raises(
        extrude.ExtrudeError,
        match="shape_artwork_raise",
    ):
        extrude.execute(
            context,
        )


def test_execute_ignores_artwork_raise_when_no_artwork_is_incorporated(
    tmp_path: Path,
) -> None:
    """
    Artwork raise is irrelevant when the composition contains no Artwork.

    The positivity requirement is conditional on incorporated Artwork and
    must not impose an unnecessary constraint on structural-only Shapes.
    """

    composition = tmp_path / "composition.svg"
    composition_manifest = tmp_path / "composition-products.json"
    output_manifest = tmp_path / "products.json"

    _write_composition(
        composition,
    )

    _write_composition_manifest(
        composition_manifest,
    )

    resolver = _make_extrude_resolver(
        shape_artwork_raise=0.0,
    )

    context = Mock(
        spec=StageContext,
    )
    context.resolver = resolver
    _configure_extrude_context_inputs(
        context,
        composition=composition,
        composition_manifest=composition_manifest,
    )
    context.output.return_value = output_manifest

    extrude.execute(
        context,
    )

    assert output_manifest.is_file()


@pytest.mark.slow
def test_incorporated_artwork_is_dimensionalized_above_shape_base(
    tmp_path: Path,
) -> None:
    """
    Incorporated Artwork begins at the top of the Shape base.

    Shape owns Artwork physical dimensionalization. Every incorporated
    Artwork component therefore begins at shape_base_raise and extends
    upward by shape_artwork_raise.
    """

    composition = tmp_path / "composition.svg"
    composition_manifest = tmp_path / "composition-products.json"
    artwork_component = tmp_path / "color-1.svg"
    output_manifest = tmp_path / "products.json"

    _write_composition(
        composition,
    )

    artwork_component.write_text(
        """
<svg
    xmlns="http://www.w3.org/2000/svg"
    viewBox="-0.5 -0.5 1.0 1.0"
>
    <circle
        cx="0.0"
        cy="0.0"
        r="0.25"
    />
</svg>
""".strip(),
        encoding="utf-8",
    )

    _write_composition_manifest(
        composition_manifest,
        artwork={
            "transform": {
                "scale": 1.0,
                "translate_x": 0.0,
                "translate_y": 0.0,
            },
            "components": [
                {
                    "index": 1,
                    "path": "color-1.svg",
                    "name": "red",
                    "color": {
                        "red": 220,
                        "green": 38,
                        "blue": 38,
                    },
                },
            ],
        },
    )

    resolver = _make_extrude_resolver(
        shape_base_raise=2.0,
        shape_artwork_raise=1.0,
    )

    context = Mock(
        spec=StageContext,
    )
    context.resolver = resolver
    _configure_extrude_context_inputs(
        context,
        composition=composition,
        composition_manifest=composition_manifest,
    )
    context.output.return_value = output_manifest

    extrude.execute(
        context,
    )

    data = _read_manifest(
        output_manifest,
    )

    artwork_components = [
        component for component in data["components"] if component["name"] == "artwork-1"
    ]

    assert len(artwork_components) == 1

    physical_artwork = output_manifest.parent / artwork_components[0]["path"]

    assert physical_artwork.is_file()

    bounds = _stl_bounds(
        physical_artwork,
    )

    assert bounds[4] == pytest.approx(2.0)
    assert bounds[5] == pytest.approx(3.0)
