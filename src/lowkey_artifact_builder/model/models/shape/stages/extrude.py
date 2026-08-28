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


@dataclass(frozen=True)
class RegisteredRectangle:
    """
    One rectangle expressed in registered Shape coordinates.
    """

    x: float
    y: float
    width: float
    height: float


@dataclass(frozen=True)
class RegisteredSquareRidge:
    """
    Registered square geometry defining an outer ridge partition.
    """

    outer: RegisteredRectangle
    inner: RegisteredRectangle


@dataclass(frozen=True)
class RegisteredPolygon:
    """
    One polygon expressed in registered Shape coordinates.
    """

    vertices: tuple[
        tuple[float, float],
        ...,
    ]


@dataclass(frozen=True)
class RegisteredPolygonRidge:
    """
    Registered polygon geometry defining an outer ridge partition.
    """

    outer: RegisteredPolygon
    inner: RegisteredPolygon


type RegisteredRidge = RegisteredCircleRidge | RegisteredSquareRidge | RegisteredPolygonRidge


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

    A composition with an integrated or separate ridge produces physical
    components according to the configured ridge style and raise.

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
        ridge = _load_ridge(
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

        elif isinstance(
            ridge,
            RegisteredCircleRidge,
        ):
            components = _render_circle_ridge_components(
                ridge,
                manifest.parent,
                shape_size=shape_size,
                shape_base_raise=shape_base_raise,
                shape_outer_ridge_raise=shape_outer_ridge_raise,
                shape_outer_ridge_style=shape_outer_ridge_style,
            )

        elif isinstance(
            ridge,
            RegisteredSquareRidge,
        ):
            components = _render_square_ridge_components(
                ridge,
                manifest.parent,
                shape_size=shape_size,
                shape_base_raise=shape_base_raise,
                shape_outer_ridge_raise=shape_outer_ridge_raise,
                shape_outer_ridge_style=shape_outer_ridge_style,
            )

        elif isinstance(
            ridge,
            RegisteredPolygonRidge,
        ):
            components = _render_polygon_ridge_components(
                ridge,
                manifest.parent,
                shape_size=shape_size,
                shape_base_raise=shape_base_raise,
                shape_outer_ridge_raise=shape_outer_ridge_raise,
                shape_outer_ridge_style=shape_outer_ridge_style,
            )

        else:
            raise ValueError(
                f"Unsupported registered Shape ridge geometry: {type(ridge).__name__}."
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
    """

    return _render_no_ridge_components(
        composition,
        output_directory,
        shape_size=shape_size,
        shape_base_raise=shape_base_raise,
    )


def _render_circle_ridge_components(
    ridge: RegisteredCircleRidge,
    output_directory: Path,
    *,
    shape_size: float,
    shape_base_raise: float,
    shape_outer_ridge_raise: float,
    shape_outer_ridge_style: str,
) -> tuple[
    tuple[str, str],
    ...,
]:
    """
    Dispatch physical circle ridge component production by ridge style.
    """

    if shape_outer_ridge_style == "integrated":
        return _render_integrated_circle_ridge_components(
            ridge,
            output_directory,
            shape_size=shape_size,
            shape_base_raise=shape_base_raise,
            shape_outer_ridge_raise=shape_outer_ridge_raise,
        )

    if shape_outer_ridge_style == "separate":
        return _render_separate_circle_ridge_components(
            ridge,
            output_directory,
            shape_size=shape_size,
            shape_base_raise=shape_base_raise,
            shape_outer_ridge_raise=shape_outer_ridge_raise,
        )

    raise ValueError(f"Unsupported Shape outer ridge style: {shape_outer_ridge_style!r}")


def _render_square_ridge_components(
    ridge: RegisteredSquareRidge,
    output_directory: Path,
    *,
    shape_size: float,
    shape_base_raise: float,
    shape_outer_ridge_raise: float,
    shape_outer_ridge_style: str,
) -> tuple[
    tuple[str, str],
    ...,
]:
    """
    Dispatch physical square ridge component production by ridge style.
    """

    if shape_outer_ridge_style == "integrated":
        return _render_integrated_square_ridge_components(
            ridge,
            output_directory,
            shape_size=shape_size,
            shape_base_raise=shape_base_raise,
            shape_outer_ridge_raise=shape_outer_ridge_raise,
        )

    if shape_outer_ridge_style == "separate":
        return _render_separate_square_ridge_components(
            ridge,
            output_directory,
            shape_size=shape_size,
            shape_base_raise=shape_base_raise,
            shape_outer_ridge_raise=shape_outer_ridge_raise,
        )

    raise ValueError(f"Unsupported Shape outer ridge style: {shape_outer_ridge_style!r}")


def _render_polygon_ridge_components(
    ridge: RegisteredPolygonRidge,
    output_directory: Path,
    *,
    shape_size: float,
    shape_base_raise: float,
    shape_outer_ridge_raise: float,
    shape_outer_ridge_style: str,
) -> tuple[
    tuple[str, str],
    ...,
]:
    """
    Dispatch physical polygon ridge component production by ridge style.
    """

    if shape_outer_ridge_style == "integrated":
        return _render_integrated_polygon_ridge_components(
            ridge,
            output_directory,
            shape_size=shape_size,
            shape_base_raise=shape_base_raise,
            shape_outer_ridge_raise=shape_outer_ridge_raise,
        )

    if shape_outer_ridge_style == "separate":
        return _render_separate_polygon_ridge_components(
            ridge,
            output_directory,
            shape_size=shape_size,
            shape_base_raise=shape_base_raise,
            shape_outer_ridge_raise=shape_outer_ridge_raise,
        )

    raise ValueError(f"Unsupported Shape outer ridge style: {shape_outer_ridge_style!r}")


def _render_integrated_polygon_ridge_components(
    ridge: RegisteredPolygonRidge,
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
    Render independently printable components for a positive integrated
    polygon ridge.
    """

    base = output_directory / BASE_COMPONENT_PATH

    base_source = _build_polygon_base_scad(
        ridge.outer,
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

    if shape_outer_ridge_raise <= 0.0:
        return (
            (
                BASE_COMPONENT_NAME,
                BASE_COMPONENT_PATH,
            ),
        )

    ridge_output = output_directory / RIDGE_COMPONENT_PATH

    ridge_source = _build_integrated_polygon_ridge_component_scad(
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


def _render_separate_polygon_ridge_components(
    ridge: RegisteredPolygonRidge,
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
    Render independently printable components for a separate polygon ridge.
    """

    base = output_directory / BASE_COMPONENT_PATH

    base_source = _build_polygon_base_scad(
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

    ridge_source = _build_separate_polygon_ridge_component_scad(
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


def _render_integrated_square_ridge_components(
    ridge: RegisteredSquareRidge,
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
    Render independently printable components for an integrated square ridge.

    For positive ridge raise, the base occupies the complete square footprint
    through the base top and the ridge component occupies only the perimeter
    volume above that top.
    """

    base = output_directory / BASE_COMPONENT_PATH

    base_source = _build_integrated_square_base_scad(
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

    ridge_source = _build_integrated_square_ridge_component_scad(
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


def _render_separate_square_ridge_components(
    ridge: RegisteredSquareRidge,
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
    Render independently printable components for a separate square ridge.

    The base occupies the registered inner square while the ridge occupies
    the surrounding registered perimeter from Z=0 through the assembled
    ridge height.
    """

    base = output_directory / BASE_COMPONENT_PATH

    base_source = _build_rectangle_base_scad(
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

    ridge_source = _build_separate_square_ridge_component_scad(
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

    Registered Shape composition occupies a canonical unit envelope centered
    about the origin.

    A composition without a ridge partition is extruded uniformly through
    shape_base_raise.

    Registered ridge boundaries are dimensionalized using shape_size.

    Integrated circle, square, and polygon ridges preserve their registered
    structural partition when constructing complete assembled geometry.
    """

    ridge = _load_ridge(
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

    if isinstance(
        ridge,
        RegisteredCircleRidge,
    ):
        if shape_outer_ridge_style == "integrated":
            return _build_integrated_circle_ridge_scad(
                ridge,
                shape_size=shape_size,
                shape_base_raise=shape_base_raise,
                shape_outer_ridge_raise=shape_outer_ridge_raise,
            )

    elif isinstance(
        ridge,
        RegisteredSquareRidge,
    ):
        if shape_outer_ridge_style == "integrated":
            return _build_integrated_square_ridge_scad(
                ridge,
                shape_size=shape_size,
                shape_base_raise=shape_base_raise,
                shape_outer_ridge_raise=shape_outer_ridge_raise,
            )

    elif isinstance(
        ridge,
        RegisteredPolygonRidge,
    ):
        if shape_outer_ridge_style == "integrated":
            return _build_integrated_polygon_ridge_scad(
                ridge,
                shape_size=shape_size,
                shape_base_raise=shape_base_raise,
                shape_outer_ridge_raise=shape_outer_ridge_raise,
            )

        if shape_outer_ridge_style == "separate":
            return _build_separate_polygon_ridge_scad(
                ridge,
                shape_size=shape_size,
                shape_base_raise=shape_base_raise,
                shape_outer_ridge_raise=shape_outer_ridge_raise,
            )

    else:
        raise ValueError(f"Unsupported registered Shape ridge geometry: {type(ridge).__name__}.")

    return _build_base_scad(
        _scad_path(
            composition,
        ),
        shape_size=shape_size,
        shape_base_raise=shape_base_raise,
    )


def _build_integrated_polygon_ridge_scad(
    ridge: RegisteredPolygonRidge,
    *,
    shape_size: float,
    shape_base_raise: float,
    shape_outer_ridge_raise: float,
) -> str:
    """
    Build OpenSCAD source for complete integrated polygon ridge geometry.
    """

    boundaries = _build_polygon_boundary_modules(
        ridge,
        shape_size=shape_size,
    )

    return (
        f"shape_size = {shape_size:g};\n"
        f"shape_base_raise = {shape_base_raise:g};\n"
        f"shape_outer_ridge_raise = {shape_outer_ridge_raise:g};\n"
        "\n"
        f"{boundaries}"
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


def _build_rectangle_base_scad(
    rectangle: RegisteredRectangle,
    *,
    shape_size: float,
    shape_base_raise: float,
) -> str:
    """
    Build OpenSCAD source for a physical registered rectangle base.
    """

    x = rectangle.x * shape_size
    y = rectangle.y * shape_size
    width = rectangle.width * shape_size
    height = rectangle.height * shape_size

    return (
        f"shape_size = {shape_size:g};\n"
        f"shape_base_raise = {shape_base_raise:g};\n"
        "\n"
        "linear_extrude(\n"
        "    height = shape_base_raise,\n"
        "    center = false\n"
        ")\n"
        f"    translate([{x:g}, {y:g}, 0])\n"
        f"        square([{width:g}, {height:g}], center = false);\n"
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


def _build_integrated_square_base_scad(
    ridge: RegisteredSquareRidge,
    *,
    shape_size: float,
    shape_base_raise: float,
    shape_outer_ridge_raise: float,
) -> str:
    """
    Build OpenSCAD source for the base material of an integrated square ridge.

    For zero or positive ridge raise, base material occupies the complete
    Shape footprint through shape_base_raise.

    For negative ridge raise, the interior occupies the complete base height
    while the perimeter occupies only the reduced assembled ridge height:

        interior  -> Z=0 through shape_base_raise
        perimeter -> Z=0 through
                     shape_base_raise + shape_outer_ridge_raise
    """

    if shape_outer_ridge_raise >= 0.0:
        return _build_rectangle_base_scad(
            ridge.outer,
            shape_size=shape_size,
            shape_base_raise=shape_base_raise,
        )

    boundaries = _build_square_boundary_modules(
        ridge,
        shape_size=shape_size,
    )

    return (
        f"shape_size = {shape_size:g};\n"
        f"shape_base_raise = {shape_base_raise:g};\n"
        f"shape_outer_ridge_raise = {shape_outer_ridge_raise:g};\n"
        "\n"
        f"{boundaries}"
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
    Build OpenSCAD source for an independently printable separate circle ridge.
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


def _build_separate_polygon_ridge_scad(
    ridge: RegisteredPolygonRidge,
    *,
    shape_size: float,
    shape_base_raise: float,
    shape_outer_ridge_raise: float,
) -> str:
    """
    Build OpenSCAD source for complete separate polygon ridge geometry.
    """

    boundaries = _build_polygon_boundary_modules(
        ridge,
        shape_size=shape_size,
    )

    return (
        f"shape_size = {shape_size:g};\n"
        f"shape_base_raise = {shape_base_raise:g};\n"
        f"shape_outer_ridge_raise = {shape_outer_ridge_raise:g};\n"
        "\n"
        f"{boundaries}"
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


def _build_integrated_circle_ridge_scad(
    ridge: RegisteredCircleRidge,
    *,
    shape_size: float,
    shape_base_raise: float,
    shape_outer_ridge_raise: float,
) -> str:
    """
    Build OpenSCAD source for complete integrated circle ridge geometry.
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


def _build_integrated_square_ridge_component_scad(
    ridge: RegisteredSquareRidge,
    *,
    shape_size: float,
    shape_base_raise: float,
    shape_outer_ridge_raise: float,
) -> str:
    """
    Build OpenSCAD source for a positive integrated square ridge component.
    """

    boundaries = _build_square_boundary_modules(
        ridge,
        shape_size=shape_size,
    )

    return (
        f"shape_size = {shape_size:g};\n"
        f"shape_base_raise = {shape_base_raise:g};\n"
        f"shape_outer_ridge_raise = {shape_outer_ridge_raise:g};\n"
        "\n"
        f"{boundaries}"
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


def _build_separate_square_ridge_component_scad(
    ridge: RegisteredSquareRidge,
    *,
    shape_size: float,
    shape_base_raise: float,
    shape_outer_ridge_raise: float,
) -> str:
    """
    Build OpenSCAD source for an independently printable separate square ridge.
    """

    boundaries = _build_square_boundary_modules(
        ridge,
        shape_size=shape_size,
    )

    return (
        f"shape_size = {shape_size:g};\n"
        f"shape_base_raise = {shape_base_raise:g};\n"
        f"shape_outer_ridge_raise = {shape_outer_ridge_raise:g};\n"
        "\n"
        f"{boundaries}"
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


def _build_integrated_square_ridge_scad(
    ridge: RegisteredSquareRidge,
    *,
    shape_size: float,
    shape_base_raise: float,
    shape_outer_ridge_raise: float,
) -> str:
    """
    Build OpenSCAD source for complete integrated square ridge geometry.
    """

    boundaries = _build_square_boundary_modules(
        ridge,
        shape_size=shape_size,
    )

    return (
        f"shape_size = {shape_size:g};\n"
        f"shape_base_raise = {shape_base_raise:g};\n"
        f"shape_outer_ridge_raise = {shape_outer_ridge_raise:g};\n"
        "\n"
        f"{boundaries}"
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


def _build_square_boundary_modules(
    ridge: RegisteredSquareRidge,
    *,
    shape_size: float,
) -> str:
    """
    Build OpenSCAD modules for registered square ridge boundaries.
    """

    outer_x = ridge.outer.x * shape_size
    outer_y = ridge.outer.y * shape_size
    outer_width = ridge.outer.width * shape_size
    outer_height = ridge.outer.height * shape_size

    inner_x = ridge.inner.x * shape_size
    inner_y = ridge.inner.y * shape_size
    inner_width = ridge.inner.width * shape_size
    inner_height = ridge.inner.height * shape_size

    return (
        f"// {SHAPE_BOUNDARY_ID}\n"
        "module registered_shape_boundary() {\n"
        f"    translate([{outer_x:g}, {outer_y:g}, 0])\n"
        f"        square([{outer_width:g}, {outer_height:g}], center = false);\n"
        "}\n"
        "\n"
        f"// {RIDGE_INNER_BOUNDARY_ID}\n"
        "module registered_ridge_inner_boundary() {\n"
        f"    translate([{inner_x:g}, {inner_y:g}, 0])\n"
        f"        square([{inner_width:g}, {inner_height:g}], center = false);\n"
        "}\n"
    )


def _build_polygon_base_scad(
    polygon: RegisteredPolygon,
    *,
    shape_size: float,
    shape_base_raise: float,
) -> str:
    """
    Build OpenSCAD source for a physical registered polygon base.
    """

    points = _scad_polygon_points(
        polygon,
        shape_size=shape_size,
    )

    return (
        f"shape_size = {shape_size:g};\n"
        f"shape_base_raise = {shape_base_raise:g};\n"
        "\n"
        "linear_extrude(\n"
        "    height = shape_base_raise,\n"
        "    center = false\n"
        ")\n"
        f"    polygon(points = {points});\n"
    )


def _build_integrated_polygon_ridge_component_scad(
    ridge: RegisteredPolygonRidge,
    *,
    shape_size: float,
    shape_base_raise: float,
    shape_outer_ridge_raise: float,
) -> str:
    """
    Build OpenSCAD source for a positive integrated polygon ridge component.
    """

    boundaries = _build_polygon_boundary_modules(
        ridge,
        shape_size=shape_size,
    )

    return (
        f"shape_size = {shape_size:g};\n"
        f"shape_base_raise = {shape_base_raise:g};\n"
        f"shape_outer_ridge_raise = {shape_outer_ridge_raise:g};\n"
        "\n"
        f"{boundaries}"
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


def _build_separate_polygon_ridge_component_scad(
    ridge: RegisteredPolygonRidge,
    *,
    shape_size: float,
    shape_base_raise: float,
    shape_outer_ridge_raise: float,
) -> str:
    """
    Build OpenSCAD source for an independently printable separate polygon ridge.
    """

    boundaries = _build_polygon_boundary_modules(
        ridge,
        shape_size=shape_size,
    )

    return (
        f"shape_size = {shape_size:g};\n"
        f"shape_base_raise = {shape_base_raise:g};\n"
        f"shape_outer_ridge_raise = {shape_outer_ridge_raise:g};\n"
        "\n"
        f"{boundaries}"
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


def _build_polygon_boundary_modules(
    ridge: RegisteredPolygonRidge,
    *,
    shape_size: float,
) -> str:
    """
    Build OpenSCAD modules for registered polygon ridge boundaries.
    """

    outer_points = _scad_polygon_points(
        ridge.outer,
        shape_size=shape_size,
    )

    inner_points = _scad_polygon_points(
        ridge.inner,
        shape_size=shape_size,
    )

    return (
        f"// {SHAPE_BOUNDARY_ID}\n"
        "module registered_shape_boundary() {\n"
        f"    polygon(points = {outer_points});\n"
        "}\n"
        "\n"
        f"// {RIDGE_INNER_BOUNDARY_ID}\n"
        "module registered_ridge_inner_boundary() {\n"
        f"    polygon(points = {inner_points});\n"
        "}\n"
    )


def _scad_polygon_points(
    polygon: RegisteredPolygon,
    *,
    shape_size: float,
) -> str:
    """
    Format registered polygon vertices as physical OpenSCAD points.
    """

    points = ", ".join((f"[{x * shape_size:g}, {y * shape_size:g}]") for x, y in polygon.vertices)

    return f"[{points}]"


# =========================================================
# Registered composition inspection
# =========================================================


def _load_ridge(
    composition: Path,
) -> RegisteredRidge | None:
    """
    Load a registered ridge partition from Shape composition.

    Ridge existence has already been established during registered
    composition. Extrusion consumes the resulting semantic boundaries rather
    than resolving shape_outer_ridge_width again.

    Circle, square, and polygon semantic ridge boundaries are supported.

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
        return None

    outer_kind = _local_name(
        outer_element.tag,
    )
    inner_kind = _local_name(
        inner_element.tag,
    )

    if outer_kind != inner_kind:
        raise ValueError(
            "Registered Shape outer and ridge inner boundaries must use matching geometry."
        )

    if outer_kind == "circle":
        return _load_circle_ridge_elements(
            outer_element,
            inner_element,
        )

    if outer_kind == "rect":
        return _load_square_ridge_elements(
            outer_element,
            inner_element,
        )

    if outer_kind == "polygon":
        return _load_polygon_ridge_elements(
            outer_element,
            inner_element,
        )

    raise ValueError(f"Unsupported registered ridge boundary geometry: {outer_kind!r}.")


def _load_circle_ridge(
    composition: Path,
) -> RegisteredCircleRidge | None:
    """
    Load a registered circle ridge partition from Shape composition.

    This circle-specific helper is retained for existing tests and callers.
    """

    ridge = _load_ridge(
        composition,
    )

    if ridge is None:
        return None

    if not isinstance(
        ridge,
        RegisteredCircleRidge,
    ):
        raise ValueError("Registered ridge composition does not contain circle boundaries.")

    return ridge


def _load_circle_ridge_elements(
    outer_element: ET.Element,
    inner_element: ET.Element,
) -> RegisteredCircleRidge:
    """
    Load semantic registered circle ridge boundaries.
    """

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


def _load_square_ridge_elements(
    outer_element: ET.Element,
    inner_element: ET.Element,
) -> RegisteredSquareRidge:
    """
    Load semantic registered square ridge boundaries.
    """

    outer = _load_registered_rectangle(
        outer_element,
        boundary_name=SHAPE_BOUNDARY_ID,
    )

    inner = _load_registered_rectangle(
        inner_element,
        boundary_name=RIDGE_INNER_BOUNDARY_ID,
    )

    if outer.width != outer.height:
        raise ValueError("Registered Shape square boundary must have equal width and height.")

    if inner.width != inner.height:
        raise ValueError("Registered ridge inner square boundary must have equal width and height.")

    if (
        inner.x < outer.x
        or inner.y < outer.y
        or inner.x + inner.width > outer.x + outer.width
        or inner.y + inner.height > outer.y + outer.height
    ):
        raise ValueError("Registered ridge inner boundary exceeds the Shape outer boundary.")

    return RegisteredSquareRidge(
        outer=outer,
        inner=inner,
    )


def _load_polygon_ridge_elements(
    outer_element: ET.Element,
    inner_element: ET.Element,
) -> RegisteredPolygonRidge:
    """
    Load semantic registered polygon ridge boundaries.
    """

    outer = _load_registered_polygon(
        outer_element,
        boundary_name=SHAPE_BOUNDARY_ID,
    )

    inner = _load_registered_polygon(
        inner_element,
        boundary_name=RIDGE_INNER_BOUNDARY_ID,
    )

    if len(inner.vertices) != len(outer.vertices):
        raise ValueError(
            "Registered Shape outer and ridge inner polygon boundaries "
            "must have the same number of vertices."
        )

    return RegisteredPolygonRidge(
        outer=outer,
        inner=inner,
    )


def _load_registered_polygon(
    element: ET.Element,
    *,
    boundary_name: str,
) -> RegisteredPolygon:
    """
    Load one semantic registered polygon boundary.
    """

    if (
        _local_name(
            element.tag,
        )
        != "polygon"
    ):
        raise ValueError(f"Registered boundary {boundary_name!r} must be an SVG polygon.")

    points = element.get(
        "points",
    )

    if points is None:
        raise ValueError(
            f"Registered boundary {boundary_name!r} is missing required attribute 'points'."
        )

    vertices: list[tuple[float, float]] = []

    for point in points.split():
        coordinates = point.split(
            ",",
        )

        if len(coordinates) != 2:
            raise ValueError(
                f"Registered boundary {boundary_name!r} contains an invalid polygon point."
            )

        vertices.append(
            (
                float(coordinates[0]),
                float(coordinates[1]),
            )
        )

    if len(vertices) < 3:
        raise ValueError(
            f"Registered boundary {boundary_name!r} must have at least three vertices."
        )

    return RegisteredPolygon(
        vertices=tuple(
            vertices,
        ),
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


def _load_registered_rectangle(
    element: ET.Element,
    *,
    boundary_name: str,
) -> RegisteredRectangle:
    """
    Load one semantic registered rectangle boundary.
    """

    if (
        _local_name(
            element.tag,
        )
        != "rect"
    ):
        raise ValueError(f"Registered boundary {boundary_name!r} must be an SVG rect.")

    x = _float_attribute(
        element,
        "x",
        boundary_name=boundary_name,
        default=0.0,
    )

    y = _float_attribute(
        element,
        "y",
        boundary_name=boundary_name,
        default=0.0,
    )

    width = _float_attribute(
        element,
        "width",
        boundary_name=boundary_name,
    )

    height = _float_attribute(
        element,
        "height",
        boundary_name=boundary_name,
    )

    if width <= 0.0 or height <= 0.0:
        raise ValueError(f"Registered boundary {boundary_name!r} must have positive dimensions.")

    return RegisteredRectangle(
        x=x,
        y=y,
        width=width,
        height=height,
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
    """

    return path.resolve().as_posix()


__all__ = [
    "ExtrudeError",
    "execute",
]
