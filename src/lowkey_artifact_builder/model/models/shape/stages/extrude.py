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

from lowkey_artifact_builder.colors import PaletteColor, resolve_palette_color
from lowkey_artifact_builder.engine import StageContext
from lowkey_artifact_builder.tools.openscad import (
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

    Registered Shape structure and incorporated registered Artwork are
    dimensionalized into independently printable physical components.

    Shape owns all physical X/Y and Z semantics of the resulting assembly.
    """

    composition = context.input(
        "compose.composition",
    )

    composition_manifest = context.input(
        "compose.manifest",
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

    shape_base_color = resolve_palette_color(
        context.resolver(
            "shape_base_color",
        ),
        context.resolver.colors,
    )

    shape_outer_ridge_color = resolve_palette_color(
        context.resolver(
            "shape_outer_ridge_color",
        ),
        context.resolver.colors,
    )

    shape_outer_ridge_raise = context.resolver(
        "shape_outer_ridge_raise",
    )

    shape_outer_ridge_style = context.resolver(
        "shape_outer_ridge_style",
    )

    if not composition.is_file():
        raise ExtrudeError(f"Registered Shape composition does not exist: {composition}")

    if not composition_manifest.is_file():
        raise ExtrudeError(
            f"Registered Shape composition manifest does not exist: {composition_manifest}"
        )

    try:
        artwork = _load_composed_artwork(
            composition_manifest,
        )

        shape_artwork_raise = 0.0

        if artwork is not None:
            shape_artwork_raise = context.resolver(
                "shape_artwork_raise",
            )

            if shape_artwork_raise <= 0.0:
                raise ValueError(
                    "shape_artwork_raise must be greater than zero when Artwork is incorporated."
                )

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

        artwork_components: tuple[
            tuple[str, str, dict[str, object]],
            ...,
        ] = ()

        if artwork is not None:
            artwork_components = _render_artwork_components(
                artwork,
                composition_manifest.parent,
                manifest.parent,
                shape_size=shape_size,
                shape_base_raise=shape_base_raise,
                shape_artwork_raise=shape_artwork_raise,
            )

        _write_component_manifest(
            manifest,
            components,
            base_color=shape_base_color,
            ridge_color=shape_outer_ridge_color,
            artwork_components=artwork_components,
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


def _render_artwork_components(
    artwork: dict[str, object],
    source_directory: Path,
    output_directory: Path,
    *,
    shape_size: float,
    shape_base_raise: float,
    shape_artwork_raise: float,
) -> tuple[
    tuple[str, str, dict[str, object]],
    ...,
]:
    """
    Dimensionalize incorporated registered Artwork components.

    Every Artwork component receives the same persisted registered-space
    transform, the same Shape physical X/Y scaling, and the same physical
    Z interval.

    Artwork semantic color identity is preserved while being normalized into
    the physical-component color representation consumed by packaging.

    The persistent registered coordinate extent is required so downstream
    physical dimensionalization retains the Artwork coordinate-system
    contract.
    """

    registered_extent = artwork.get(
        "registered_extent",
    )
    transform = artwork.get(
        "transform",
    )
    components = artwork.get(
        "components",
    )

    if not isinstance(
        registered_extent,
        dict,
    ):
        raise ValueError("Registered Shape composition Artwork requires a registered extent.")

    if not isinstance(
        transform,
        dict,
    ):
        raise ValueError("Registered Shape composition Artwork requires a transform.")

    if not isinstance(
        components,
        list,
    ):
        raise ValueError("Registered Shape composition Artwork requires components.")

    registered_width = float(
        registered_extent["width"],
    )
    registered_height = float(
        registered_extent["height"],
    )

    scale = float(
        transform["scale"],
    )
    translate_x = float(
        transform["translate_x"],
    )
    translate_y = float(
        transform["translate_y"],
    )

    rendered: list[tuple[str, str, dict[str, object]]] = []

    for component in components:
        if not isinstance(
            component,
            dict,
        ):
            raise ValueError("Registered Artwork component must be an object.")

        index = int(
            component["index"],
        )

        source_path = source_directory / str(
            component["path"],
        )

        if not source_path.is_file():
            raise ValueError(f"Registered Artwork component does not exist: {source_path}")

        color_name = component.get(
            "name",
        )

        if (
            not isinstance(
                color_name,
                str,
            )
            or not color_name
        ):
            raise ValueError(
                f"Registered Artwork component {index} requires a semantic color name."
            )

        color = component.get(
            "color",
        )

        if not isinstance(
            color,
            dict,
        ):
            raise ValueError(f"Registered Artwork component {index} requires color metadata.")

        red = color.get(
            "red",
        )
        green = color.get(
            "green",
        )
        blue = color.get(
            "blue",
        )

        if any(
            not isinstance(channel, int)
            or isinstance(channel, bool)
            or channel < 0
            or channel > 255
            for channel in (
                red,
                green,
                blue,
            )
        ):
            raise ValueError(
                f"Registered Artwork component {index} requires valid RGB color metadata."
            )

        physical_color: dict[str, object] = {
            "name": color_name,
            "rgb": [
                red,
                green,
                blue,
            ],
        }

        component_name = f"artwork-{index}"
        component_path = f"{component_name}.stl"
        output_path = output_directory / component_path

        source = _build_artwork_component_scad(
            _scad_path(
                source_path,
            ),
            shape_size=shape_size,
            shape_base_raise=shape_base_raise,
            shape_artwork_raise=shape_artwork_raise,
            artwork_registered_width=registered_width,
            artwork_registered_height=registered_height,
            artwork_scale=scale,
            artwork_translate_x=translate_x,
            artwork_translate_y=translate_y,
        )

        render_stl_source(
            source,
            output_path,
        )

        _require_component(
            output_path,
            component_name=component_name,
        )

        rendered.append(
            (
                component_name,
                component_path,
                physical_color,
            )
        )

    return tuple(
        rendered,
    )


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
    *,
    base_color: PaletteColor,
    ridge_color: PaletteColor,
    artwork_components: tuple[
        tuple[str, str, dict[str, object]],
        ...,
    ] = (),
) -> None:
    """
    Write the physical-component manifest for Shape extrusion.

    Structural and incorporated Artwork components preserve their semantic
    printing-color identity for downstream packaging.
    """

    colors = {
        BASE_COMPONENT_NAME: base_color,
        RIDGE_COMPONENT_NAME: ridge_color,
    }

    manifest_components: list[dict[str, object]] = [
        {
            "name": name,
            "path": component_path,
            "color": {
                "name": colors[name].name,
                "rgb": list(
                    colors[name].rgb,
                ),
            },
        }
        for name, component_path in components
    ]

    for (
        name,
        component_path,
        color,
    ) in artwork_components:
        manifest_components.append(
            {
                "name": name,
                "path": component_path,
                "color": color,
            }
        )

    path.write_text(
        json.dumps(
            {
                "components": manifest_components,
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


def _build_artwork_component_scad(
    source: str,
    *,
    shape_size: float,
    shape_base_raise: float,
    shape_artwork_raise: float,
    artwork_registered_width: float,
    artwork_registered_height: float,
    artwork_scale: float,
    artwork_translate_x: float,
    artwork_translate_y: float,
) -> str:
    """
    Build OpenSCAD source for one incorporated Artwork component.

    Registered Artwork uses a zero-origin SVG coordinate system with positive Y
    downward. OpenSCAD SVG import preserves X but reverses Y within the
    registered extent.

    The imported geometry is therefore reflected through the registered
    Artwork height before the persistent Artwork-to-Shape composition
    transform is applied.

    Shape then maps its registered coordinates into physical X/Y space.

    The resulting component begins at the physical top of the Shape base.
    """

    return (
        f"shape_size = {shape_size:g};\n"
        f"shape_base_raise = {shape_base_raise:g};\n"
        f"shape_artwork_raise = {shape_artwork_raise:g};\n"
        f"artwork_registered_width = {artwork_registered_width:g};\n"
        f"artwork_registered_height = {artwork_registered_height:g};\n"
        f"artwork_scale = {artwork_scale:g};\n"
        f"artwork_translate_x = {artwork_translate_x:g};\n"
        f"artwork_translate_y = {artwork_translate_y:g};\n"
        "\n"
        "translate([0, 0, shape_base_raise])\n"
        "    linear_extrude(\n"
        "        height = shape_artwork_raise,\n"
        "        center = false\n"
        "    )\n"
        "        scale([shape_size, shape_size, 1])\n"
        "            translate([\n"
        "                artwork_translate_x,\n"
        "                artwork_translate_y,\n"
        "                0\n"
        "            ])\n"
        "                scale([artwork_scale, artwork_scale, 1])\n"
        "                    translate([0, artwork_registered_height, 0])\n"
        "                        mirror([0, 1, 0])\n"
        f'                            import("{source}", dpi = 25.4);\n'
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


def _composition_has_artwork(
    manifest: Path,
) -> bool:
    """
    Return whether the persistent registered composition incorporates Artwork.

    Artwork participation is recorded explicitly by the compose-stage
    manifest. A null Artwork member represents a structural-only Shape.
    """

    data = json.loads(
        manifest.read_text(
            encoding="utf-8",
        )
    )

    return (
        data.get(
            "artwork",
        )
        is not None
    )


def _load_composed_artwork(
    composition_manifest: Path,
) -> dict[str, object] | None:
    """
    Load incorporated registered Artwork from a Shape composition manifest.

    The compose stage persists component membership and one common registered
    placement transform. Extrusion consumes that persistent contract directly.
    """

    data = json.loads(
        composition_manifest.read_text(
            encoding="utf-8",
        )
    )

    artwork = data.get(
        "artwork",
    )

    if artwork is None:
        return None

    if not isinstance(
        artwork,
        dict,
    ):
        raise ValueError("Registered Shape composition Artwork must be an object.")

    return artwork


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
