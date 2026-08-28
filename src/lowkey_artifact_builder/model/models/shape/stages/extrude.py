"""
Physical extrusion for the Shape model.

The extrude stage is the Shape physical-dimensionalization boundary.

It consumes registered composed Shape geometry, applies the configured
physical X/Y size and Z dimensions, and renders the resulting manufacturing
geometry as independently printable STL components.

The stage records those physical components in a persistent products.json
manifest consumed by downstream packaging.

Final 3MF assembly belongs to the downstream package stage.
"""
# File: src/lowkey_artifact_builder/model/models/shape/stages/extrude.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
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

BASE_COMPONENT_NAME = "base"
BASE_COMPONENT_PATH = "base.stl"

RIDGE_COMPONENT_NAME = "ridge"
RIDGE_COMPONENT_PATH = "ridge.stl"


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

        manifest
            Persistent products.json manifest describing independently
            printable physical Shape components.

    A composition without a ridge produces one physical component:

        base.stl

    A composition with an integrated or separate ridge produces:

        base.stl
        ridge.stl

    Ridge style determines how the complete assembled structural geometry is
    partitioned between those components.

    Packaging the physical components into artifact.3mf belongs to the
    downstream package stage.
    """

    composition = context.input(
        "compose.composition",
    )

    manifest = context.output(
        "manifest",
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
        ridge = _load_circle_ridge(
            composition,
        )
        if ridge is not None:
            _validate_ridge_height(
                shape_base_raise=shape_base_raise,
                shape_outer_ridge_raise=shape_outer_ridge_raise,
            )

        manifest.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        if ridge is None:
            components = _render_no_ridge_components(
                composition,
                manifest.parent,
                shape_size=shape_size,
                shape_base_raise=shape_base_raise,
            )

        elif shape_outer_ridge_style == "integrated":
            components = _render_integrated_circle_ridge_components(
                ridge,
                manifest.parent,
                shape_size=shape_size,
                shape_base_raise=shape_base_raise,
                shape_outer_ridge_raise=shape_outer_ridge_raise,
            )

        elif shape_outer_ridge_style == "separate":
            components = _render_separate_circle_ridge_components(
                ridge,
                manifest.parent,
                shape_size=shape_size,
                shape_base_raise=shape_base_raise,
                shape_outer_ridge_raise=shape_outer_ridge_raise,
            )

        else:
            components = _render_baseline_components(
                composition,
                manifest.parent,
                shape_size=shape_size,
                shape_base_raise=shape_base_raise,
            )

        _write_component_manifest(
            manifest,
            components,
        )

        if not manifest.is_file():
            raise ExtrudeError(
                "Shape extrusion completed without creating the expected "
                f"component manifest: {manifest}"
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
# Physical component production
# =========================================================


def _render_no_ridge_components(
    composition: Path,
    output_directory: Path,
    *,
    shape_size: float,
    shape_base_raise: float,
) -> tuple[
    tuple[str, str],
    ...,
]:
    """
    Render physical components for a Shape without an outer ridge.
    """

    base = output_directory / BASE_COMPONENT_PATH

    source = _build_base_scad(
        _scad_path(
            composition,
        ),
        shape_size=shape_size,
        shape_base_raise=shape_base_raise,
    )

    render_stl_source(
        source,
        base,
    )

    _require_component(
        base,
        component_name=BASE_COMPONENT_NAME,
    )

    return (
        (
            BASE_COMPONENT_NAME,
            BASE_COMPONENT_PATH,
        ),
    )


def _render_baseline_components(
    composition: Path,
    output_directory: Path,
    *,
    shape_size: float,
    shape_base_raise: float,
) -> tuple[
    tuple[str, str],
    ...,
]:
    """
    Render the baseline physical base component.

    This preserves the existing fallback behavior for ridge styles whose
    physical partitioning has not been established.
    """

    return _render_no_ridge_components(
        composition,
        output_directory,
        shape_size=shape_size,
        shape_base_raise=shape_base_raise,
    )


def _render_integrated_circle_ridge_components(
    ridge: RegisteredCircleRidge,
    output_directory: Path,
    *,
    shape_size: float,
    shape_base_raise: float,
    shape_outer_ridge_raise: float,
) -> tuple[
    tuple[str, str],
    ...,
]:
    """
    Render independently printable components for an integrated circle ridge.

    The integrated ridge remains base material through the base top.

    When ridge raise is positive, the base retains the complete Shape
    footprint through shape_base_raise and the ridge component occupies only
    the perimeter volume above the base.

    When ridge raise is zero or negative, no independently colored ridge
    volume exists above the base and only the base component is produced.
    """

    base = output_directory / BASE_COMPONENT_PATH

    base_source = _build_integrated_circle_base_scad(
        ridge,
        shape_size=shape_size,
        shape_base_raise=shape_base_raise,
        shape_outer_ridge_raise=shape_outer_ridge_raise,
    )

    render_stl_source(
        base_source,
        base,
    )

    _require_component(
        base,
        component_name=BASE_COMPONENT_NAME,
    )

    if shape_outer_ridge_raise <= 0.0:
        return (
            (
                BASE_COMPONENT_NAME,
                BASE_COMPONENT_PATH,
            ),
        )

    ridge_output = output_directory / RIDGE_COMPONENT_PATH

    ridge_source = _build_integrated_circle_ridge_component_scad(
        ridge,
        shape_size=shape_size,
        shape_base_raise=shape_base_raise,
        shape_outer_ridge_raise=shape_outer_ridge_raise,
    )

    render_stl_source(
        ridge_source,
        ridge_output,
    )

    _require_component(
        ridge_output,
        component_name=RIDGE_COMPONENT_NAME,
    )

    return (
        (
            BASE_COMPONENT_NAME,
            BASE_COMPONENT_PATH,
        ),
        (
            RIDGE_COMPONENT_NAME,
            RIDGE_COMPONENT_PATH,
        ),
    )


def _render_separate_circle_ridge_components(
    ridge: RegisteredCircleRidge,
    output_directory: Path,
    *,
    shape_size: float,
    shape_base_raise: float,
    shape_outer_ridge_raise: float,
) -> tuple[
    tuple[str, str],
    ...,
]:
    """
    Render independently printable components for a separate circle ridge.

    The base occupies the region inside the registered ridge inner boundary
    and extends from Z=0 through shape_base_raise.

    The ridge occupies the surrounding registered perimeter annulus and
    extends from Z=0 through the complete assembled ridge height:

        shape_base_raise + shape_outer_ridge_raise

    Base and ridge therefore occupy adjacent, nonoverlapping X/Y regions.

    At the minimum valid ridge raise, the ridge remains semantically defined
    by its registered nonzero width but has zero physical volume. In that
    case no ridge STL component is materialized.
    """

    base = output_directory / BASE_COMPONENT_PATH

    base_source = _build_circle_base_scad(
        ridge.inner,
        shape_size=shape_size,
        shape_base_raise=shape_base_raise,
    )

    render_stl_source(
        base_source,
        base,
    )

    _require_component(
        base,
        component_name=BASE_COMPONENT_NAME,
    )

    assembled_ridge_height = shape_base_raise + shape_outer_ridge_raise

    if assembled_ridge_height == 0.0:
        return (
            (
                BASE_COMPONENT_NAME,
                BASE_COMPONENT_PATH,
            ),
        )

    ridge_output = output_directory / RIDGE_COMPONENT_PATH

    ridge_source = _build_separate_circle_ridge_component_scad(
        ridge,
        shape_size=shape_size,
        shape_base_raise=shape_base_raise,
        shape_outer_ridge_raise=shape_outer_ridge_raise,
    )

    render_stl_source(
        ridge_source,
        ridge_output,
    )

    _require_component(
        ridge_output,
        component_name=RIDGE_COMPONENT_NAME,
    )

    return (
        (
            BASE_COMPONENT_NAME,
            BASE_COMPONENT_PATH,
        ),
        (
            RIDGE_COMPONENT_NAME,
            RIDGE_COMPONENT_PATH,
        ),
    )


def _require_component(
    path: Path,
    *,
    component_name: str,
) -> None:
    """
    Require one rendered physical Shape component to exist.
    """

    if not path.is_file():
        raise ExtrudeError(
            f"Shape extrusion completed without creating the expected {component_name} STL: {path}"
        )


def _write_component_manifest(
    path: Path,
    components: tuple[
        tuple[str, str],
        ...,
    ],
) -> None:
    """
    Write the physical-component manifest for Shape extrusion.
    """

    path.write_text(
        json.dumps(
            {
                "components": [
                    {
                        "name": name,
                        "path": component_path,
                    }
                    for name, component_path in components
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _validate_ridge_height(
    *,
    shape_base_raise: float,
    shape_outer_ridge_raise: float,
) -> None:
    """
    Validate that an outer ridge has a nonnegative physical height.

    Ridge raise is measured relative to the base top, so the complete
    assembled ridge height must be greater than or equal to zero.
    """

    if shape_base_raise + shape_outer_ridge_raise < 0.0:
        raise ExtrudeError(
            "Shape outer ridge physical height must be greater than or equal to zero."
        )


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
    Build OpenSCAD source for complete physical Shape extrusion.

    Registered Shape composition occupies a canonical 1x1 envelope centered
    about the origin.

    A composition without a ridge partition is extruded uniformly through
    shape_base_raise.

    An integrated circle ridge composition contains semantic outer and inner
    ridge boundaries. Those registered boundaries are dimensionalized using
    shape_size.

    This helper retains the complete assembled representation used by the
    dimensionalization tests. Stage execution separately renders independently
    printable physical components.

    Positive integrated and separate circle ridge component partitioning is
    established. Zero and negative ridge raise semantics are established by
    later slices.
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


def _build_circle_base_scad(
    circle: RegisteredCircle,
    *,
    shape_size: float,
    shape_base_raise: float,
) -> str:
    """
    Build OpenSCAD source for a physical circle base.

    The supplied registered circle boundary is dimensionalized using
    shape_size and extruded from Z=0 through shape_base_raise.
    """

    x = circle.cx * shape_size
    y = circle.cy * shape_size
    radius = circle.radius * shape_size

    return (
        f"shape_size = {shape_size:g};\n"
        f"shape_base_raise = {shape_base_raise:g};\n"
        "\n"
        "linear_extrude(\n"
        "    height = shape_base_raise,\n"
        "    center = false\n"
        ")\n"
        f"    translate([{x:g}, {y:g}, 0])\n"
        f"        circle(r = {radius:g}, $fn = 256);\n"
    )


def _build_integrated_circle_base_scad(
    ridge: RegisteredCircleRidge,
    *,
    shape_size: float,
    shape_base_raise: float,
    shape_outer_ridge_raise: float,
) -> str:
    """
    Build OpenSCAD source for the base material of an integrated circle ridge.

    For zero or positive ridge raise, base material occupies the complete
    Shape footprint through shape_base_raise.

    For negative ridge raise, the interior occupies the complete base height
    while the perimeter occupies only the reduced assembled ridge height:

        interior  -> Z=0 through shape_base_raise
        perimeter -> Z=0 through
                     shape_base_raise + shape_outer_ridge_raise
    """

    if shape_outer_ridge_raise >= 0.0:
        return _build_circle_base_scad(
            ridge.outer,
            shape_size=shape_size,
            shape_base_raise=shape_base_raise,
        )

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
        "        registered_ridge_inner_boundary();\n"
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


def _build_integrated_circle_ridge_component_scad(
    ridge: RegisteredCircleRidge,
    *,
    shape_size: float,
    shape_base_raise: float,
    shape_outer_ridge_raise: float,
) -> str:
    """
    Build OpenSCAD source for the independently printable integrated ridge.

    A positive integrated ridge component occupies the registered perimeter
    annulus above the base top through the complete assembled ridge height.
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
        "translate([0, 0, shape_base_raise])\n"
        "    linear_extrude(\n"
        "        height = shape_outer_ridge_raise,\n"
        "        center = false\n"
        "    )\n"
        "        difference() {\n"
        "            registered_shape_boundary();\n"
        "            registered_ridge_inner_boundary();\n"
        "        }\n"
    )


def _build_separate_circle_ridge_component_scad(
    ridge: RegisteredCircleRidge,
    *,
    shape_size: float,
    shape_base_raise: float,
    shape_outer_ridge_raise: float,
) -> str:
    """
    Build OpenSCAD source for an independently printable separate ridge.

    The ridge occupies the registered perimeter annulus from Z=0 through the
    complete assembled ridge height.
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
        "linear_extrude(\n"
        "    height = shape_base_raise + shape_outer_ridge_raise,\n"
        "    center = false\n"
        ")\n"
        "    difference() {\n"
        "        registered_shape_boundary();\n"
        "        registered_ridge_inner_boundary();\n"
        "    }\n"
    )


def _build_integrated_circle_ridge_scad(
    ridge: RegisteredCircleRidge,
    *,
    shape_size: float,
    shape_base_raise: float,
    shape_outer_ridge_raise: float,
) -> str:
    """
    Build OpenSCAD source for complete integrated circle ridge geometry.

    The interior occupies Z=0 through shape_base_raise.

    The perimeter occupies Z=0 through:

        shape_base_raise + shape_outer_ridge_raise

    Positive ridge raise therefore raises the perimeter above the interior,
    zero raise leaves both surfaces flush, and negative raise recesses the
    perimeter below the interior.
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
        "        registered_ridge_inner_boundary();\n"
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
