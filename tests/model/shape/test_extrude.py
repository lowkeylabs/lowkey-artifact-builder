"""
Tests for Shape physical extrusion.
"""
# File: tests/model/shape/test_extrude.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, call

import pytest

from lowkey_artifact_builder.engine import StageContext
from lowkey_artifact_builder.engine.bootstrap import build_stage_registry
from lowkey_artifact_builder.model.models.shape import stages
from lowkey_artifact_builder.model.models.shape.stages import extrude

# =========================================================
# Test support
# =========================================================


def _write_composition(
    path: Path,
) -> None:
    """
    Write representative registered Shape composition geometry.
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
    )

    assert str(composition.resolve()) in source
    assert "center = false" in source


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
    )

    extrude.render_stl_source(
        source,
        output,
    )

    bounds = _stl_bounds(
        output,
    )

    # print(bounds)

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
    Extruded Shape geometry occupies Z=0 through shape_base_raise.
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


# =========================================================
# Extrude stage execution
# =========================================================


def test_extrude_stage_materializes_declared_base_stl(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Shape extrusion materializes its declared physical base product.

    Input and output locations come exclusively from StageContext.
    """

    composition = tmp_path / "arbitrary-input" / "composition.svg"
    output = tmp_path / "arbitrary-output" / "base.stl"

    _write_composition(
        composition,
    )

    resolver = Mock(
        side_effect={
            "shape_size": 100.0,
            "shape_base_raise": 2.0,
        }.__getitem__,
    )

    context = Mock(
        spec=StageContext,
    )
    context.resolver = resolver
    context.input.return_value = composition
    context.output.return_value = output

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

    context.input.assert_called_once_with(
        "compose.composition",
    )
    context.output.assert_called_once_with(
        "base",
    )

    assert resolver.call_args_list == [
        call("shape_size"),
        call("shape_base_raise"),
    ]

    assert rendered_outputs == [
        output,
    ]

    assert len(rendered_sources) == 1
    assert str(composition.resolve()) in rendered_sources[0]

    assert output.is_file()


def test_extrude_stage_rejects_missing_registered_composition(
    tmp_path: Path,
) -> None:
    """
    Shape extrusion requires its declared registered composition input.
    """

    composition = tmp_path / "missing.svg"
    output = tmp_path / "base.stl"

    resolver = Mock(
        side_effect={
            "shape_size": 100.0,
            "shape_base_raise": 2.0,
        }.__getitem__,
    )

    context = Mock(
        spec=StageContext,
    )
    context.resolver = resolver
    context.input.return_value = composition
    context.output.return_value = output

    with pytest.raises(
        extrude.ExtrudeError,
        match="composition",
    ):
        extrude.execute(
            context,
        )

    assert not output.exists()


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
