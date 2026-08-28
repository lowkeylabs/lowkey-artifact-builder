"""
Physical extrusion for the Shape model.

The extrude stage is the Shape physical-dimensionalization boundary.

It consumes registered composed Shape geometry, applies the configured
physical X/Y size and Z dimensions, and renders the resulting manufacturing
geometry as an independently printable STL component.

Final 3MF assembly belongs to the downstream package stage.
"""
# File: src/lowkey_artifact_builder/model/models/shape/stages/extrude.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from lowkey_artifact_builder.engine import StageContext
from lowkey_artifact_builder.model.models.artwork.stages.extrude import (
    render_stl_source,
)

# =========================================================
# Constants
# =========================================================

SHAPE_BOUNDARY_ID = "shape-boundary"
RIDGE_INNER_BOUNDARY_ID = "ridge-inner-boundary"


# =========================================================
# Registered geometry
# =========================================================


@dataclass(frozen=True)
class RegisteredCircle:
    """
    One circle expressed in registered Shape coordinates.
    """

    cx: float
    cy: float
    radius: float


@dataclass(frozen=True)
class RegisteredCircleRidge:
    """
    Registered circle geometry defining an outer ridge partition.
    """

    outer: RegisteredCircle
    inner: RegisteredCircle


# =========================================================
# Errors
# =========================================================


class ExtrudeError(RuntimeError):
    """
    Raised when Shape extrusion cannot be completed.
    """


# =========================================================
# Public interface
# =========================================================


def execute(
    context: StageContext,
) -> None:
    """
    Execute physical Shape extrusion.

    The stage consumes:

        compose.composition
            Registered composed Shape geometry.

    The stage resolves:

        shape_size
            Physical X/Y extent of the Shape in millimeters.

        shape_base_raise
            Physical Z thickness of the structural base in millimeters.

        shape_outer_ridge_raise
            Physical change in ridge height relative to the base top.

        shape_outer_ridge_style
            Structural partitioning style of the outer ridge.

    The stage produces:

        base
            Independently printable physical Shape structural STL.

    An integrated ridge remains part of the base structural component.

    Packaging the physical component into artifact.3mf belongs to the
    downstream package stage.
    """

    composition = context.input(
        "compose.composition",
    )

    base = context.output(
        "base",
    )

    shape_size = context.resolver(
        "shape_size",
    )

    shape_base_raise = context.resolver(
        "shape_base_raise",
    )

    shape_outer_ridge_raise = context.resolver(
        "shape_outer_ridge_raise",
    )

    shape_outer_ridge_style = context.resolver(
        "shape_outer_ridge_style",
    )

    if not composition.is_file():
        raise ExtrudeError(f"Registered Shape composition does not exist: {composition}")

    try:
        source = _build_scad(
            composition,
            shape_size=shape_size,
            shape_base_raise=shape_base_raise,
            shape_outer_ridge_raise=shape_outer_ridge_raise,
            shape_outer_ridge_style=shape_outer_ridge_style,
        )

        render_stl_source(
            source,
            base,
        )

        if not base.is_file():
            raise ExtrudeError(
                f"Shape extrusion completed without creating the expected base STL: {base}"
            )

    except ExtrudeError:
        raise

    except (
        ET.ParseError,
        OSError,
        TypeError,
        ValueError,
    ) as exc:
        raise ExtrudeError(
            f"Could not extrude registered Shape composition {composition}: {exc}"
        ) from exc


# =========================================================
# OpenSCAD construction
# =========================================================


def _build_scad(
    composition: Path,
    *,
    shape_size: float,
    shape_base_raise: float,
    shape_outer_ridge_raise: float,
    shape_outer_ridge_style: str,
) -> str:
    """
    Build OpenSCAD source for physical Shape extrusion.

    Registered Shape composition occupies a canonical 1x1 envelope centered
    about the origin.

    A composition without a ridge partition is extruded uniformly through
    shape_base_raise.

    An integrated circle ridge composition contains semantic outer and inner
    ridge boundaries. Those registered boundaries are dimensionalized using
    shape_size.

    This slice establishes positive integrated circle ridge raise. Zero and
    negative integrated raise and separate ridge partitioning are established
    by later slices.
    """

    ridge = _load_circle_ridge(
        composition,
    )

    if ridge is None:
        return _build_base_scad(
            _scad_path(
                composition,
            ),
            shape_size=shape_size,
            shape_base_raise=shape_base_raise,
        )

    if shape_outer_ridge_style == "integrated":
        return _build_integrated_circle_ridge_scad(
            ridge,
            shape_size=shape_size,
            shape_base_raise=shape_base_raise,
            shape_outer_ridge_raise=shape_outer_ridge_raise,
        )

    return _build_base_scad(
        _scad_path(
            composition,
        ),
        shape_size=shape_size,
        shape_base_raise=shape_base_raise,
    )


def _build_base_scad(
    source: str,
    *,
    shape_size: float,
    shape_base_raise: float,
) -> str:
    """
    Build OpenSCAD source for the baseline no-ridge Shape base.
    """

    return (
        f"shape_size = {shape_size:g};\n"
        f"shape_base_raise = {shape_base_raise:g};\n"
        "\n"
        "linear_extrude(\n"
        "    height = shape_base_raise,\n"
        "    center = false\n"
        ")\n"
        "    scale([shape_size, shape_size, 1])\n"
        "        translate([-0.5, -1.5, 0])\n"
        f'            import("{source}", dpi = 25.4);\n'
    )


def _build_integrated_circle_ridge_scad(
    ridge: RegisteredCircleRidge,
    *,
    shape_size: float,
    shape_base_raise: float,
    shape_outer_ridge_raise: float,
) -> str:
    """
    Build OpenSCAD source for a positive integrated circle ridge.

    The complete outer circle occupies Z=0 through shape_base_raise.

    The perimeter between the outer and inner registered circles occupies
    Z=0 through:

        shape_base_raise + shape_outer_ridge_raise

    Registered circle coordinates are converted directly to physical
    millimeters using shape_size.
    """

    outer_x = ridge.outer.cx * shape_size
    outer_y = ridge.outer.cy * shape_size
    outer_radius = ridge.outer.radius * shape_size

    inner_x = ridge.inner.cx * shape_size
    inner_y = ridge.inner.cy * shape_size
    inner_radius = ridge.inner.radius * shape_size

    return (
        f"shape_size = {shape_size:g};\n"
        f"shape_base_raise = {shape_base_raise:g};\n"
        f"shape_outer_ridge_raise = {shape_outer_ridge_raise:g};\n"
        "\n"
        f"// {SHAPE_BOUNDARY_ID}\n"
        "module registered_shape_boundary() {\n"
        f"    translate([{outer_x:g}, {outer_y:g}, 0])\n"
        f"        circle(r = {outer_radius:g}, $fn = 256);\n"
        "}\n"
        "\n"
        f"// {RIDGE_INNER_BOUNDARY_ID}\n"
        "module registered_ridge_inner_boundary() {\n"
        f"    translate([{inner_x:g}, {inner_y:g}, 0])\n"
        f"        circle(r = {inner_radius:g}, $fn = 256);\n"
        "}\n"
        "\n"
        "union() {\n"
        "    linear_extrude(\n"
        "        height = shape_base_raise,\n"
        "        center = false\n"
        "    )\n"
        "        registered_shape_boundary();\n"
        "\n"
        "    linear_extrude(\n"
        "        height = shape_base_raise + shape_outer_ridge_raise,\n"
        "        center = false\n"
        "    )\n"
        "        difference() {\n"
        "            registered_shape_boundary();\n"
        "            registered_ridge_inner_boundary();\n"
        "        }\n"
        "}\n"
    )


# =========================================================
# Registered composition inspection
# =========================================================


def _load_circle_ridge(
    composition: Path,
) -> RegisteredCircleRidge | None:
    """
    Load a registered circle ridge partition from Shape composition.

    Ridge existence has already been established during registered
    composition. Extrusion consumes the resulting semantic boundaries rather
    than resolving shape_outer_ridge_width again.

    A composition without ridge semantic boundaries returns None.
    """

    tree = ET.parse(
        composition,
    )

    root = tree.getroot()

    outer_element: ET.Element | None = None
    inner_element: ET.Element | None = None

    for element in root.iter():
        element_id = element.get(
            "id",
        )

        if element_id == SHAPE_BOUNDARY_ID:
            outer_element = element

        elif element_id == RIDGE_INNER_BOUNDARY_ID:
            inner_element = element

    if outer_element is None and inner_element is None:
        return None

    if outer_element is None:
        raise ValueError(
            "Registered ridge composition contains a ridge inner boundary "
            "without a Shape outer boundary."
        )

    if inner_element is None:
        raise ValueError(
            "Registered ridge composition contains a Shape outer boundary "
            "without a ridge inner boundary."
        )

    outer = _load_registered_circle(
        outer_element,
        boundary_name=SHAPE_BOUNDARY_ID,
    )

    inner = _load_registered_circle(
        inner_element,
        boundary_name=RIDGE_INNER_BOUNDARY_ID,
    )

    if inner.radius > outer.radius:
        raise ValueError("Registered ridge inner boundary exceeds the Shape outer boundary.")

    return RegisteredCircleRidge(
        outer=outer,
        inner=inner,
    )


def _load_registered_circle(
    element: ET.Element,
    *,
    boundary_name: str,
) -> RegisteredCircle:
    """
    Load one semantic registered circle boundary.
    """

    if (
        _local_name(
            element.tag,
        )
        != "circle"
    ):
        raise ValueError(f"Registered boundary {boundary_name!r} must be an SVG circle.")

    cx = _float_attribute(
        element,
        "cx",
        boundary_name=boundary_name,
        default=0.0,
    )

    cy = _float_attribute(
        element,
        "cy",
        boundary_name=boundary_name,
        default=0.0,
    )

    radius = _float_attribute(
        element,
        "r",
        boundary_name=boundary_name,
    )

    if radius <= 0.0:
        raise ValueError(f"Registered boundary {boundary_name!r} must have a positive radius.")

    return RegisteredCircle(
        cx=cx,
        cy=cy,
        radius=radius,
    )


def _float_attribute(
    element: ET.Element,
    name: str,
    *,
    boundary_name: str,
    default: float | None = None,
) -> float:
    """
    Return one numeric SVG attribute.
    """

    value = element.get(
        name,
    )

    if value is None:
        if default is not None:
            return default

        raise ValueError(
            f"Registered boundary {boundary_name!r} is missing required attribute {name!r}."
        )

    return float(
        value,
    )


def _local_name(
    tag: str,
) -> str:
    """
    Return an XML element's namespace-independent local name.
    """

    return tag.rsplit(
        "}",
        maxsplit=1,
    )[-1]


def _scad_path(
    path: Path,
) -> str:
    """
    Return a filesystem path suitable for an OpenSCAD string literal.

    OpenSCAD accepts forward slashes on supported platforms. Converting here
    also avoids introducing platform-specific backslash escaping into the
    generated source.
    """

    return path.resolve().as_posix()


__all__ = [
    "ExtrudeError",
    "execute",
]
