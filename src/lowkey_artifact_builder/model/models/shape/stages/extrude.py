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
from lowkey_artifact_builder.model.geometry import Bounds
from lowkey_artifact_builder.model.models.shape.hole import (
    HoleGeometry,
    create_hole_geometry,
)
from lowkey_artifact_builder.model.models.shape.loop import (
    LoopGeometry,
    create_loop_geometry,
)
from lowkey_artifact_builder.tools.openscad import (
    render_stl_source,
)

# =========================================================
# Constants
# =========================================================

SHAPE_BOUNDARY_ID = "shape-boundary"
RIDGE_INNER_BOUNDARY_ID = "ridge-inner-boundary"
INNER_RIDGE_OUTER_BOUNDARY_ID = "inner-ridge-outer-boundary"
INNER_RIDGE_INNER_BOUNDARY_ID = "inner-ridge-inner-boundary"

BASE_COMPONENT_NAME = "base"
BASE_COMPONENT_PATH = "base.stl"

LOOP_COMPONENT_NAME = "loop"
LOOP_COMPONENT_PATH = "loop.stl"

RIDGE_COMPONENT_NAME = "ridge"
RIDGE_COMPONENT_PATH = "ridge.stl"

INNER_RIDGE_COMPONENT_NAME = "inner-ridge"
INNER_RIDGE_COMPONENT_PATH = "inner-ridge.stl"

ARTWORK_FILL_COMPONENT_NAME = "artwork-fill"
ARTWORK_FILL_COMPONENT_PATH = "artwork-fill.stl"

TOP_BORDER_LABEL_COMPONENT_NAME = "top-border-label"
TOP_BORDER_LABEL_COMPONENT_PATH = "top-border-label.stl"

BOTTOM_BORDER_LABEL_COMPONENT_NAME = "bottom-border-label"
BOTTOM_BORDER_LABEL_COMPONENT_PATH = "bottom-border-label.stl"

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


@dataclass(frozen=True)
class RegisteredArtworkFill:
    """
    Registered Shape-owned Artwork-fill geometry.

    The fill occupies the registered Shape interior outside the transformed
    authoritative Artwork envelope.
    """

    outer_boundary: dict[str, object]
    inner_boundary: dict[str, object]


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

    Registered Shape structure, Shape-owned semantic components, and
    incorporated registered Artwork are dimensionalized into independently
    printable physical components.

    Shape owns all physical X/Y and Z semantics of the resulting assembly.
    Physical printer-color assignment belongs to downstream packaging.

    A participating Shape Hole is resolved once from the complete physical
    Shape envelope and subtracted from every independently printable physical
    component before STL materialization.
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

    shape_raise_style = context.resolver(
        "shape_raise_style",
    )

    shape_outer_ridge_raise = context.resolver(
        "shape_outer_ridge_raise",
    )

    shape_outer_ridge_style = context.resolver(
        "shape_outer_ridge_style",
    )

    shape_hole_diameter = context.resolver(
        "shape_hole_diameter",
    )

    hole: HoleGeometry | None = None

    if shape_hole_diameter > 0.0:
        half_size = shape_size / 2.0

        hole = create_hole_geometry(
            envelope_bounds=Bounds(
                min_x=-half_size,
                min_y=-half_size,
                max_x=half_size,
                max_y=half_size,
            ),
            diameter=shape_hole_diameter,
            edge_distance=context.resolver(
                "shape_hole_edge_distance",
            ),
            position=context.resolver(
                "shape_hole_position",
            ),
        )

    shape_loop_inner_diameter = context.resolver(
        "shape_loop_inner_diameter",
    )

    loop: LoopGeometry | None = None

    if shape_loop_inner_diameter > 0.0:
        half_size = shape_size / 2.0

        loop = create_loop_geometry(
            envelope_bounds=Bounds(
                min_x=-half_size,
                min_y=-half_size,
                max_x=half_size,
                max_y=half_size,
            ),
            inner_diameter=shape_loop_inner_diameter,
            width=context.resolver(
                "shape_loop_width",
            ),
            position=context.resolver(
                "shape_loop_position",
            ),
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

        artwork_fill = _load_artwork_fill(
            composition_manifest,
        )

        border_labels = _load_border_labels(
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

        shape_artwork_fill_raise = 0.0

        if artwork_fill is not None:
            shape_artwork_fill_raise = context.resolver(
                "shape_artwork_fill_raise",
            )

        ridge = _load_ridge(
            composition,
        )

        if ridge is not None:
            _validate_ridge_height(
                shape_base_raise=shape_base_raise,
                shape_outer_ridge_raise=shape_outer_ridge_raise,
            )

        inner_ridge = _load_inner_ridge(
            composition,
        )

        shape_inner_ridge_raise = 0.0

        if inner_ridge is not None:
            shape_inner_ridge_raise = context.resolver(
                "shape_inner_ridge_raise",
            )

            _validate_inner_ridge_height(
                shape_base_raise=shape_base_raise,
                shape_inner_ridge_raise=shape_inner_ridge_raise,
            )

        top_border_label = border_labels.get(
            "top",
        )

        shape_top_border_label_raise = 0.0

        if top_border_label is not None:
            shape_top_border_label_raise = context.resolver(
                "shape_top_border_label_raise",
            )

        bottom_border_label = border_labels.get(
            "bottom",
        )

        shape_bottom_border_label_raise = 0.0

        if bottom_border_label is not None:
            shape_bottom_border_label_raise = context.resolver(
                "shape_bottom_border_label_raise",
            )

        manifest.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        inlaid_planar_geometries: list[str] = []

        if shape_raise_style == "inlaid":
            if artwork is not None:
                inlaid_planar_geometries.append(
                    _build_artwork_planar_union_scad(
                        artwork,
                        composition_manifest.parent,
                        shape_size=shape_size,
                    )
                )

            if artwork_fill is not None and shape_artwork_fill_raise > 0.0:
                inlaid_planar_geometries.append(
                    _build_artwork_fill_planar_geometry_scad(
                        artwork_fill,
                        shape_size=shape_size,
                    )
                )

            if inner_ridge is not None and shape_inner_ridge_raise > 0.0:
                inlaid_planar_geometries.append(
                    _build_inner_ridge_planar_geometry_scad(
                        inner_ridge,
                        shape_size=shape_size,
                    )
                )

            if top_border_label is not None and shape_top_border_label_raise > 0.0:
                raw_path = top_border_label.get(
                    "path",
                )

                if not isinstance(
                    raw_path,
                    str,
                ):
                    raise ExtrudeError("Registered top-border-label is missing its component path.")

                inlaid_planar_geometries.append(
                    _build_border_label_planar_geometry_scad(
                        composition_manifest.parent / raw_path,
                        shape_size=shape_size,
                    )
                )

            if bottom_border_label is not None and shape_bottom_border_label_raise > 0.0:
                raw_path = bottom_border_label.get(
                    "path",
                )

                if not isinstance(
                    raw_path,
                    str,
                ):
                    raise ExtrudeError(
                        "Registered bottom-border-label is missing its component path."
                    )

                inlaid_planar_geometries.append(
                    _build_border_label_planar_geometry_scad(
                        composition_manifest.parent / raw_path,
                        shape_size=shape_size,
                    )
                )

        inlaid_planar_subtraction = _build_planar_union_scad(
            inlaid_planar_geometries,
        )

        if ridge is None:
            components = _render_no_ridge_components(
                composition,
                manifest.parent,
                shape_size=shape_size,
                shape_base_raise=shape_base_raise,
                hole=hole,
                planar_subtraction=inlaid_planar_subtraction,
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
                shape_raise_style=shape_raise_style,
                shape_outer_ridge_raise=shape_outer_ridge_raise,
                shape_outer_ridge_style=shape_outer_ridge_style,
                hole=hole,
                planar_subtraction=inlaid_planar_subtraction,
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
                shape_raise_style=shape_raise_style,
                shape_outer_ridge_raise=shape_outer_ridge_raise,
                shape_outer_ridge_style=shape_outer_ridge_style,
                hole=hole,
                planar_subtraction=inlaid_planar_subtraction,
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
                shape_raise_style=shape_raise_style,
                shape_outer_ridge_raise=shape_outer_ridge_raise,
                shape_outer_ridge_style=shape_outer_ridge_style,
                hole=hole,
                planar_subtraction=inlaid_planar_subtraction,
            )

        else:
            raise ValueError(
                f"Unsupported registered Shape ridge geometry: {type(ridge).__name__}."
            )

        if loop is not None:
            components += _render_loop_component(
                loop,
                manifest.parent,
                shape_base_raise=shape_base_raise,
                shape_raise_style=shape_raise_style,
                shape_loop_raise=context.resolver(
                    "shape_loop_raise",
                ),
                hole=hole,
            )

        if inner_ridge is not None:
            components += _render_inner_ridge_component(
                inner_ridge,
                manifest.parent,
                shape_size=shape_size,
                shape_base_raise=shape_base_raise,
                shape_raise_style=shape_raise_style,
                shape_inner_ridge_raise=shape_inner_ridge_raise,
                hole=hole,
            )

        if top_border_label is not None:
            components += _render_border_label_component(
                top_border_label,
                composition_manifest.parent,
                manifest.parent,
                component_name=TOP_BORDER_LABEL_COMPONENT_NAME,
                component_path=TOP_BORDER_LABEL_COMPONENT_PATH,
                shape_size=shape_size,
                shape_base_raise=shape_base_raise,
                shape_raise_style=shape_raise_style,
                shape_border_label_raise=shape_top_border_label_raise,
                hole=hole,
            )

        if bottom_border_label is not None:
            components += _render_border_label_component(
                bottom_border_label,
                composition_manifest.parent,
                manifest.parent,
                component_name=BOTTOM_BORDER_LABEL_COMPONENT_NAME,
                component_path=BOTTOM_BORDER_LABEL_COMPONENT_PATH,
                shape_size=shape_size,
                shape_base_raise=shape_base_raise,
                shape_raise_style=shape_raise_style,
                shape_border_label_raise=shape_bottom_border_label_raise,
                hole=hole,
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
                shape_raise_style=shape_raise_style,
                shape_artwork_raise=shape_artwork_raise,
                hole=hole,
            )

        artwork_fill_components: tuple[
            tuple[str, str],
            ...,
        ] = ()

        if artwork_fill is not None and shape_artwork_fill_raise > 0.0:
            artwork_fill_components = _render_artwork_fill_component(
                artwork_fill,
                manifest.parent,
                shape_size=shape_size,
                shape_base_raise=shape_base_raise,
                shape_raise_style=shape_raise_style,
                shape_artwork_fill_raise=shape_artwork_fill_raise,
                hole=hole,
            )

        _write_component_manifest(
            manifest,
            components,
            artwork_components=artwork_components,
            artwork_fill_components=artwork_fill_components,
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


def _render_loop_component(
    loop: LoopGeometry,
    output_directory: Path,
    *,
    shape_base_raise: float,
    shape_loop_raise: float,
    hole: HoleGeometry | None = None,
    shape_raise_style: str = "raised",
) -> tuple[
    tuple[str, str],
    ...,
]:
    """
    Render the independently printable Shape Loop component.

    Loop is additive physical geometry beginning at Z=0.

    Raised dimensionalization uses shape_loop_raise as the complete Loop
    height.

    Inlaid dimensionalization spans the complete Shape base thickness.
    Unlike inlaid principal-surface components, Loop does not partition or
    subtract material from the Shape Base.

    A participating Shape Hole is subtracted from intersecting Loop material.
    """

    if shape_raise_style == "raised":
        component_height = shape_loop_raise

    elif shape_raise_style == "inlaid":
        component_height = shape_base_raise

    else:
        raise ValueError(
            f"Unsupported Shape raise style: {shape_raise_style!r}",
        )

    if component_height <= 0.0:
        return ()

    output_path = output_directory / LOOP_COMPONENT_PATH

    source = _build_loop_component_scad(
        loop,
        component_height=component_height,
        hole=hole,
    )

    render_stl_source(
        source,
        output_path,
    )

    _require_component(
        output_path,
        component_name=LOOP_COMPONENT_NAME,
    )

    return (
        (
            LOOP_COMPONENT_NAME,
            LOOP_COMPONENT_PATH,
        ),
    )


def _render_border_label_component(
    label: dict[str, object],
    source_directory: Path,
    output_directory: Path,
    *,
    component_name: str,
    component_path: str,
    shape_size: float,
    shape_base_raise: float,
    shape_border_label_raise: float,
    hole: HoleGeometry | None = None,
    shape_raise_style: str = "raised",
) -> tuple[
    tuple[str, str],
    ...,
]:
    """
    Dimensionalize one persistent registered Border Label component.

    Compose has already established participation and registered X/Y glyph
    geometry.

    Raised dimensionalization begins at the top of the Shape base and uses
    shape_border_label_raise as the component height.

    Inlaid dimensionalization preserves the same registered X/Y geometry while
    spanning the component through the complete Shape base thickness.
    """

    if shape_border_label_raise <= 0.0:
        return ()

    raw_path = label.get(
        "path",
    )

    if not isinstance(
        raw_path,
        str,
    ):
        raise ExtrudeError(f"Registered {component_name} is missing its component path.")

    source_path = source_directory / raw_path
    output_path = output_directory / component_path

    if not source_path.is_file():
        raise ExtrudeError(f"Registered {component_name} component does not exist: {source_path}")

    source = _build_border_label_component_scad(
        source_path,
        shape_size=shape_size,
        shape_base_raise=shape_base_raise,
        shape_raise_style=shape_raise_style,
        shape_border_label_raise=shape_border_label_raise,
        hole=hole,
    )

    render_stl_source(
        source,
        output_path,
    )

    _require_component(
        output_path,
        component_name=component_name,
    )

    return (
        (
            component_name,
            component_path,
        ),
    )


def _render_inner_ridge_component(
    ridge: RegisteredRidge,
    output_directory: Path,
    *,
    shape_size: float,
    shape_base_raise: float,
    shape_inner_ridge_raise: float,
    hole: HoleGeometry | None = None,
    shape_raise_style: str = "raised",
) -> tuple[
    tuple[str, str],
    ...,
]:
    """
    Render the independently printable Inner Ridge component.

    Inner Ridge geometry is established by Compose and consumed here directly.

    Raised dimensionalization begins at the top of the Shape base and uses
    shape_inner_ridge_raise as the component height.

    Inlaid dimensionalization preserves the same registered X/Y partition while
    spanning the component through the complete Shape base thickness.
    """

    if shape_inner_ridge_raise <= 0.0:
        return ()

    output_path = output_directory / INNER_RIDGE_COMPONENT_PATH

    source = _build_inner_ridge_component_scad(
        ridge,
        shape_size=shape_size,
        shape_base_raise=shape_base_raise,
        shape_raise_style=shape_raise_style,
        shape_inner_ridge_raise=shape_inner_ridge_raise,
        hole=hole,
    )

    render_stl_source(
        source,
        output_path,
    )

    _require_component(
        output_path,
        component_name=INNER_RIDGE_COMPONENT_NAME,
    )

    return (
        (
            INNER_RIDGE_COMPONENT_NAME,
            INNER_RIDGE_COMPONENT_PATH,
        ),
    )


def _render_artwork_fill_component(
    fill: RegisteredArtworkFill,
    output_directory: Path,
    *,
    shape_size: float,
    shape_base_raise: float,
    shape_artwork_fill_raise: float,
    hole: HoleGeometry | None = None,
    shape_raise_style: str = "raised",
) -> tuple[
    tuple[str, str],
    ...,
]:
    """
    Render the independently printable Shape-owned Artwork Fill component.

    Registered Artwork Fill geometry is established by Compose and consumed
    here directly.

    Raised dimensionalization begins at the top of the Shape base and uses
    shape_artwork_fill_raise as the component height.

    Inlaid dimensionalization preserves the same registered X/Y partition while
    spanning the component through the complete Shape base thickness.
    """

    if shape_artwork_fill_raise <= 0.0:
        return ()

    output_path = output_directory / ARTWORK_FILL_COMPONENT_PATH

    source = _build_artwork_fill_scad(
        fill,
        shape_size=shape_size,
        shape_base_raise=shape_base_raise,
        shape_raise_style=shape_raise_style,
        shape_artwork_fill_raise=shape_artwork_fill_raise,
        hole=hole,
    )

    render_stl_source(
        source,
        output_path,
    )

    _require_component(
        output_path,
        component_name=ARTWORK_FILL_COMPONENT_NAME,
    )

    return (
        (
            ARTWORK_FILL_COMPONENT_NAME,
            ARTWORK_FILL_COMPONENT_PATH,
        ),
    )


def _render_artwork_components(
    artwork: dict[str, object],
    source_directory: Path,
    output_directory: Path,
    *,
    shape_size: float,
    shape_base_raise: float,
    shape_artwork_raise: float,
    hole: HoleGeometry | None = None,
    shape_raise_style: str = "raised",
) -> tuple[
    tuple[str, str, dict[str, object]],
    ...,
]:
    """
    Dimensionalize incorporated registered Artwork components.

    Every Artwork component receives the same persisted registered-space
    transform, the same Shape physical X/Y scaling, and the same physical
    Z interval.

    Artifact-color identity remains persistent Artwork information through
    extrusion. Physical printer-color assignment belongs to downstream
    packaging and is not required or resolved here.

    The persistent registered coordinate extent is required so downstream
    physical dimensionalization retains the Artwork coordinate-system
    contract.

    A participating Shape Hole is subtracted from each Artwork component's
    native constructive geometry before STL materialization.
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

    rendered: list[
        tuple[
            str,
            str,
            dict[str, object],
        ]
    ] = []

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

        artifact_color = component.get(
            "artifact_color",
        )

        if not isinstance(
            artifact_color,
            dict,
        ):
            raise ValueError(
                f"Registered Artwork component {index} requires Artifact color metadata."
            )

        artifact_color_index = artifact_color.get(
            "index",
        )

        if (
            not isinstance(
                artifact_color_index,
                int,
            )
            or isinstance(
                artifact_color_index,
                bool,
            )
            or artifact_color_index <= 0
        ):
            raise ValueError(
                f"Registered Artwork component {index} requires a positive Artifact color index."
            )

        artifact_rgb = artifact_color.get(
            "rgb",
        )

        if not isinstance(
            artifact_rgb,
            dict,
        ):
            raise ValueError(
                f"Registered Artwork component {index} requires Artifact RGB metadata."
            )

        red = artifact_rgb.get(
            "red",
        )
        green = artifact_rgb.get(
            "green",
        )
        blue = artifact_rgb.get(
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
                f"Registered Artwork component {index} requires valid Artifact RGB metadata."
            )

        logical_color: dict[str, object] = {
            "index": artifact_color_index,
            "rgb": {
                "red": red,
                "green": green,
                "blue": blue,
            },
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
            shape_raise_style=shape_raise_style,
            artwork_registered_width=registered_width,
            artwork_registered_height=registered_height,
            artwork_scale=scale,
            artwork_translate_x=translate_x,
            artwork_translate_y=translate_y,
            hole=hole,
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
                logical_color,
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
    hole: HoleGeometry | None,
    planar_subtraction: str | None = None,
) -> tuple[
    tuple[str, str],
    ...,
]:
    """
    Render physical components for a Shape without an outer ridge.

    Optional planar subtraction removes participating inlaid surface-component
    regions from the Base before materialization.
    """

    base = output_directory / BASE_COMPONENT_PATH

    source = _build_base_scad(
        _scad_path(
            composition,
        ),
        shape_size=shape_size,
        shape_base_raise=shape_base_raise,
        hole=hole,
        planar_subtraction=planar_subtraction,
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
    hole: HoleGeometry | None,
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
        hole=hole,
    )


def _surface_component_interval(
    *,
    shape_base_raise: float,
    component_raise: float,
    shape_raise_style: str = "raised",
) -> tuple[float, float]:
    """
    Resolve the physical Z offset and height of a Shape surface component.

    Raised components begin at the top of the structural base and extend by
    their component-specific raise.

    Inlaid components span the complete Shape thickness. The resolved
    component raise retains its raised-style configuration meaning but does
    not determine the inlaid physical Z interval.
    """

    if shape_raise_style == "raised":
        return (
            shape_base_raise,
            component_raise,
        )

    if shape_raise_style == "inlaid":
        return (
            0.0,
            shape_base_raise,
        )

    raise ValueError(
        f"Unsupported Shape raise style: {shape_raise_style!r}",
    )


def _surface_component_height(
    *,
    shape_base_raise: float,
    component_raise: float,
    shape_raise_style: str = "raised",
) -> float:
    """
    Resolve the physical height of a Shape principal-surface component.

    Raised dimensionalization preserves the component-specific raise above
    the structural base.

    Inlaid dimensionalization spans the component through the complete Shape
    thickness. The resolved component raise remains configuration with its
    raised-style meaning, but does not determine the inlaid Z extent.
    """

    if shape_raise_style == "raised":
        return shape_base_raise + component_raise

    if shape_raise_style == "inlaid":
        return shape_base_raise

    raise ValueError(
        f"Unsupported Shape raise style: {shape_raise_style!r}",
    )


def _build_separate_circle_ridge_component_scad_at_height(
    ridge: RegisteredCircleRidge,
    *,
    shape_size: float,
    component_height: float,
    hole: HoleGeometry | None = None,
) -> str:
    """
    Build a separate circle-ridge component at one resolved physical height.

    The registered ridge partition owns X/Y geometry. The caller owns the
    physical Z policy and supplies the complete component height.
    """

    outer_x = ridge.outer.cx * shape_size
    outer_y = ridge.outer.cy * shape_size
    outer_radius = ridge.outer.radius * shape_size

    inner_x = ridge.inner.cx * shape_size
    inner_y = ridge.inner.cy * shape_size
    inner_radius = ridge.inner.radius * shape_size

    geometry = (
        "linear_extrude(\n"
        "    height = component_height,\n"
        "    center = false\n"
        ")\n"
        "    difference() {\n"
        "        registered_shape_boundary();\n"
        "        registered_ridge_inner_boundary();\n"
        "    }\n"
    )

    return (
        f"shape_size = {shape_size:g};\n"
        f"component_height = {component_height:g};\n"
        f"{_build_hole_parameters_scad(hole)}"
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
        f"{_build_hole_subtracted_geometry_scad(geometry, hole=hole)}"
    )


def _build_separate_square_ridge_component_scad_at_height(
    ridge: RegisteredSquareRidge,
    *,
    shape_size: float,
    component_height: float,
    hole: HoleGeometry | None = None,
) -> str:
    """
    Build a separate square-ridge component at one resolved physical height.

    The registered ridge partition owns X/Y geometry. The caller owns the
    physical Z policy and supplies the complete component height.
    """

    boundaries = _build_square_boundary_modules(
        ridge,
        shape_size=shape_size,
    )

    geometry = (
        "linear_extrude(\n"
        "    height = component_height,\n"
        "    center = false\n"
        ")\n"
        "    difference() {\n"
        "        registered_shape_boundary();\n"
        "        registered_ridge_inner_boundary();\n"
        "    }\n"
    )

    return (
        f"shape_size = {shape_size:g};\n"
        f"component_height = {component_height:g};\n"
        f"{_build_hole_parameters_scad(hole)}"
        "\n"
        f"{boundaries}"
        "\n"
        f"{_build_hole_subtracted_geometry_scad(geometry, hole=hole)}"
    )


def _build_separate_polygon_ridge_component_scad_at_height(
    ridge: RegisteredPolygonRidge,
    *,
    shape_size: float,
    component_height: float,
    hole: HoleGeometry | None = None,
) -> str:
    """
    Build a separate polygon ridge component at an explicit physical height.

    The registered outer and inner polygon boundaries determine the X/Y
    partition. component_height determines only the physical Z extent.
    """

    boundaries = _build_polygon_boundary_modules(
        ridge,
        shape_size=shape_size,
    )

    geometry = (
        "linear_extrude(\n"
        "    height = component_height,\n"
        "    center = false\n"
        ")\n"
        "    difference() {\n"
        "        registered_shape_boundary();\n"
        "        registered_ridge_inner_boundary();\n"
        "    }\n"
    )

    return (
        f"shape_size = {shape_size:g};\n"
        f"component_height = {component_height:g};\n"
        f"{_build_hole_parameters_scad(hole)}"
        "\n"
        f"{boundaries}"
        "\n"
        f"{_build_hole_subtracted_geometry_scad(geometry, hole=hole)}"
    )


def _render_circle_ridge_components(
    ridge: RegisteredCircleRidge,
    output_directory: Path,
    *,
    shape_size: float,
    shape_base_raise: float,
    shape_outer_ridge_raise: float,
    shape_outer_ridge_style: str,
    hole: HoleGeometry | None = None,
    shape_raise_style: str = "raised",
    planar_subtraction: str | None = None,
) -> tuple[
    tuple[str, str],
    ...,
]:
    """
    Dispatch physical circle ridge component production.

    Outer-Ridge structural style distinguishes raised construction.

    Under inlaid dimensionalization, every participating Outer Ridge is a
    full-depth partition of the Shape base regardless of whether its resolved
    structural style is integrated or separate.
    """

    if shape_outer_ridge_style not in {
        "integrated",
        "separate",
    }:
        raise ValueError(f"Unsupported Shape outer ridge style: {shape_outer_ridge_style!r}")

    if shape_raise_style == "inlaid":
        return _render_separate_circle_ridge_components(
            ridge,
            output_directory,
            shape_size=shape_size,
            shape_base_raise=shape_base_raise,
            shape_raise_style=shape_raise_style,
            shape_outer_ridge_raise=shape_outer_ridge_raise,
            hole=hole,
            planar_subtraction=planar_subtraction,
        )

    if shape_raise_style != "raised":
        raise ValueError(
            f"Unsupported Shape raise style: {shape_raise_style!r}",
        )

    if shape_outer_ridge_style == "integrated":
        return _render_integrated_circle_ridge_components(
            ridge,
            output_directory,
            shape_size=shape_size,
            shape_base_raise=shape_base_raise,
            shape_outer_ridge_raise=shape_outer_ridge_raise,
            hole=hole,
        )

    return _render_separate_circle_ridge_components(
        ridge,
        output_directory,
        shape_size=shape_size,
        shape_base_raise=shape_base_raise,
        shape_raise_style=shape_raise_style,
        shape_outer_ridge_raise=shape_outer_ridge_raise,
        hole=hole,
        planar_subtraction=planar_subtraction,
    )


def _render_square_ridge_components(
    ridge: RegisteredSquareRidge,
    output_directory: Path,
    *,
    shape_size: float,
    shape_base_raise: float,
    shape_outer_ridge_raise: float,
    shape_outer_ridge_style: str,
    hole: HoleGeometry | None = None,
    shape_raise_style: str = "raised",
    planar_subtraction: str | None = None,
) -> tuple[
    tuple[str, str],
    ...,
]:
    """
    Dispatch physical square ridge component production.

    Outer-Ridge structural style distinguishes raised construction.

    Under inlaid dimensionalization, every participating Outer Ridge is a
    full-depth partition of the Shape base regardless of whether its resolved
    structural style is integrated or separate.
    """

    if shape_outer_ridge_style not in {
        "integrated",
        "separate",
    }:
        raise ValueError(f"Unsupported Shape outer ridge style: {shape_outer_ridge_style!r}")

    if shape_raise_style == "inlaid":
        return _render_separate_square_ridge_components(
            ridge,
            output_directory,
            shape_size=shape_size,
            shape_base_raise=shape_base_raise,
            shape_raise_style=shape_raise_style,
            shape_outer_ridge_raise=shape_outer_ridge_raise,
            hole=hole,
            planar_subtraction=planar_subtraction,
        )

    if shape_raise_style != "raised":
        raise ValueError(
            f"Unsupported Shape raise style: {shape_raise_style!r}",
        )

    if shape_outer_ridge_style == "integrated":
        return _render_integrated_square_ridge_components(
            ridge,
            output_directory,
            shape_size=shape_size,
            shape_base_raise=shape_base_raise,
            shape_outer_ridge_raise=shape_outer_ridge_raise,
            hole=hole,
        )

    return _render_separate_square_ridge_components(
        ridge,
        output_directory,
        shape_size=shape_size,
        shape_base_raise=shape_base_raise,
        shape_raise_style=shape_raise_style,
        shape_outer_ridge_raise=shape_outer_ridge_raise,
        hole=hole,
        planar_subtraction=planar_subtraction,
    )


def _render_polygon_ridge_components(
    ridge: RegisteredPolygonRidge,
    output_directory: Path,
    *,
    shape_size: float,
    shape_base_raise: float,
    shape_outer_ridge_raise: float,
    shape_outer_ridge_style: str,
    hole: HoleGeometry | None = None,
    shape_raise_style: str = "raised",
    planar_subtraction: str | None = None,
) -> tuple[
    tuple[str, str],
    ...,
]:
    """
    Dispatch physical polygon ridge component production.

    Outer-Ridge structural style distinguishes raised construction.

    Under inlaid dimensionalization, every participating Outer Ridge is a
    full-depth partition of the Shape base regardless of whether its resolved
    structural style is integrated or separate.
    """

    if shape_outer_ridge_style not in {
        "integrated",
        "separate",
    }:
        raise ValueError(f"Unsupported Shape outer ridge style: {shape_outer_ridge_style!r}")

    if shape_raise_style == "inlaid":
        return _render_separate_polygon_ridge_components(
            ridge,
            output_directory,
            shape_size=shape_size,
            shape_base_raise=shape_base_raise,
            shape_raise_style=shape_raise_style,
            shape_outer_ridge_raise=shape_outer_ridge_raise,
            hole=hole,
            planar_subtraction=planar_subtraction,
        )

    if shape_raise_style != "raised":
        raise ValueError(
            f"Unsupported Shape raise style: {shape_raise_style!r}",
        )

    if shape_outer_ridge_style == "integrated":
        return _render_integrated_polygon_ridge_components(
            ridge,
            output_directory,
            shape_size=shape_size,
            shape_base_raise=shape_base_raise,
            shape_outer_ridge_raise=shape_outer_ridge_raise,
            hole=hole,
        )

    return _render_separate_polygon_ridge_components(
        ridge,
        output_directory,
        shape_size=shape_size,
        shape_base_raise=shape_base_raise,
        shape_raise_style=shape_raise_style,
        shape_outer_ridge_raise=shape_outer_ridge_raise,
        hole=hole,
        planar_subtraction=planar_subtraction,
    )


def _render_integrated_polygon_ridge_components(
    ridge: RegisteredPolygonRidge,
    output_directory: Path,
    *,
    shape_size: float,
    shape_base_raise: float,
    shape_outer_ridge_raise: float,
    hole: HoleGeometry | None = None,
) -> tuple[
    tuple[str, str],
    ...,
]:
    """
    Render independently printable components for a positive integrated
    polygon ridge.

    A participating Shape Hole is incorporated into each component's native
    constructive OpenSCAD geometry before STL materialization.
    """

    base = output_directory / BASE_COMPONENT_PATH

    base_source = _build_polygon_base_scad(
        ridge.outer,
        shape_size=shape_size,
        shape_base_raise=shape_base_raise,
        hole=hole,
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
        hole=hole,
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
    hole: HoleGeometry | None = None,
    shape_raise_style: str = "raised",
    planar_subtraction: str | None = None,
) -> tuple[
    tuple[str, str],
    ...,
]:
    """
    Render independently printable components for a separate polygon ridge.

    The registered ridge partition already establishes nonoverlapping Base and
    Ridge X/Y regions.

    Raised dimensionalization extends the Ridge through the assembled ridge
    height.

    Inlaid dimensionalization preserves the same registered partition while
    making both Base and Ridge span the complete Shape base thickness.

    Optional planar subtraction removes participating inlaid surface-component
    regions from the Base before physical extrusion.
    """

    base = output_directory / BASE_COMPONENT_PATH

    base_source = _build_polygon_base_scad(
        ridge.inner,
        shape_size=shape_size,
        shape_base_raise=shape_base_raise,
        hole=hole,
        planar_subtraction=planar_subtraction,
    )

    render_stl_source(
        base_source,
        base,
    )

    _require_component(
        base,
        component_name=BASE_COMPONENT_NAME,
    )

    ridge_height = _surface_component_height(
        shape_raise_style=shape_raise_style,
        shape_base_raise=shape_base_raise,
        component_raise=shape_outer_ridge_raise,
    )

    if ridge_height <= 0.0:
        return (
            (
                BASE_COMPONENT_NAME,
                BASE_COMPONENT_PATH,
            ),
        )

    ridge_output = output_directory / RIDGE_COMPONENT_PATH

    if shape_raise_style == "raised":
        ridge_source = _build_separate_polygon_ridge_component_scad(
            ridge,
            shape_size=shape_size,
            shape_base_raise=shape_base_raise,
            shape_outer_ridge_raise=shape_outer_ridge_raise,
            hole=hole,
        )

    elif shape_raise_style == "inlaid":
        ridge_source = _build_separate_polygon_ridge_component_scad_at_height(
            ridge,
            shape_size=shape_size,
            component_height=shape_base_raise,
            hole=hole,
        )

    else:
        raise ValueError(
            f"Unsupported Shape raise style: {shape_raise_style!r}",
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
    hole: HoleGeometry | None = None,
) -> tuple[
    tuple[str, str],
    ...,
]:
    """
    Render independently printable components for an integrated circle ridge.

    A participating Shape Hole is incorporated into each component's native
    constructive OpenSCAD geometry before STL materialization.
    """

    base = output_directory / BASE_COMPONENT_PATH

    base_source = _build_integrated_circle_base_scad(
        ridge,
        shape_size=shape_size,
        shape_base_raise=shape_base_raise,
        shape_outer_ridge_raise=shape_outer_ridge_raise,
        hole=hole,
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
        hole=hole,
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
    hole: HoleGeometry | None = None,
    shape_raise_style: str = "raised",
    planar_subtraction: str | None = None,
) -> tuple[
    tuple[str, str],
    ...,
]:
    """
    Render independently printable components for a separate circle ridge.

    The registered ridge partition already establishes nonoverlapping Base and
    Ridge X/Y regions.

    Raised dimensionalization extends the Ridge through the assembled ridge
    height.

    Inlaid dimensionalization preserves the same registered partition while
    making both Base and Ridge span the complete Shape base thickness.

    Optional planar subtraction removes participating inlaid surface-component
    regions from the Base before physical extrusion.
    """

    base = output_directory / BASE_COMPONENT_PATH

    base_source = _build_circle_base_scad(
        ridge.inner,
        shape_size=shape_size,
        shape_base_raise=shape_base_raise,
        hole=hole,
        planar_subtraction=planar_subtraction,
    )

    render_stl_source(
        base_source,
        base,
    )

    _require_component(
        base,
        component_name=BASE_COMPONENT_NAME,
    )

    ridge_height = _surface_component_height(
        shape_raise_style=shape_raise_style,
        shape_base_raise=shape_base_raise,
        component_raise=shape_outer_ridge_raise,
    )

    if ridge_height <= 0.0:
        return (
            (
                BASE_COMPONENT_NAME,
                BASE_COMPONENT_PATH,
            ),
        )

    ridge_output = output_directory / RIDGE_COMPONENT_PATH

    if shape_raise_style == "raised":
        ridge_source = _build_separate_circle_ridge_component_scad(
            ridge,
            shape_size=shape_size,
            shape_base_raise=shape_base_raise,
            shape_outer_ridge_raise=shape_outer_ridge_raise,
            hole=hole,
        )

    elif shape_raise_style == "inlaid":
        ridge_source = _build_separate_circle_ridge_component_scad_at_height(
            ridge,
            shape_size=shape_size,
            component_height=shape_base_raise,
            hole=hole,
        )

    else:
        raise ValueError(
            f"Unsupported Shape raise style: {shape_raise_style!r}",
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
    hole: HoleGeometry | None = None,
) -> tuple[
    tuple[str, str],
    ...,
]:
    """
    Render independently printable components for an integrated square ridge.

    For positive ridge raise, the base occupies the complete square footprint
    through the base top and the ridge component occupies only the perimeter
    volume above that top.

    A participating Shape Hole is incorporated into each component's native
    constructive OpenSCAD geometry before STL materialization.
    """

    base = output_directory / BASE_COMPONENT_PATH

    base_source = _build_integrated_square_base_scad(
        ridge,
        shape_size=shape_size,
        shape_base_raise=shape_base_raise,
        shape_outer_ridge_raise=shape_outer_ridge_raise,
        hole=hole,
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
        hole=hole,
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
    hole: HoleGeometry | None = None,
    shape_raise_style: str = "raised",
    planar_subtraction: str | None = None,
) -> tuple[
    tuple[str, str],
    ...,
]:
    """
    Render independently printable components for a separate square ridge.

    The registered ridge partition already establishes nonoverlapping Base and
    Ridge X/Y regions.

    Raised dimensionalization extends the Ridge through the assembled ridge
    height.

    Inlaid dimensionalization preserves the same registered partition while
    making both Base and Ridge span the complete Shape base thickness.

    Optional planar subtraction removes participating inlaid surface-component
    regions from the Base before physical extrusion.
    """

    base = output_directory / BASE_COMPONENT_PATH

    base_source = _build_rectangle_base_scad(
        ridge.inner,
        shape_size=shape_size,
        shape_base_raise=shape_base_raise,
        hole=hole,
        planar_subtraction=planar_subtraction,
    )

    render_stl_source(
        base_source,
        base,
    )

    _require_component(
        base,
        component_name=BASE_COMPONENT_NAME,
    )

    ridge_height = _surface_component_height(
        shape_raise_style=shape_raise_style,
        shape_base_raise=shape_base_raise,
        component_raise=shape_outer_ridge_raise,
    )

    if ridge_height <= 0.0:
        return (
            (
                BASE_COMPONENT_NAME,
                BASE_COMPONENT_PATH,
            ),
        )

    ridge_output = output_directory / RIDGE_COMPONENT_PATH

    if shape_raise_style == "raised":
        ridge_source = _build_separate_square_ridge_component_scad(
            ridge,
            shape_size=shape_size,
            shape_base_raise=shape_base_raise,
            shape_outer_ridge_raise=shape_outer_ridge_raise,
            hole=hole,
        )

    elif shape_raise_style == "inlaid":
        ridge_source = _build_separate_square_ridge_component_scad_at_height(
            ridge,
            shape_size=shape_size,
            component_height=shape_base_raise,
            hole=hole,
        )

    else:
        raise ValueError(
            f"Unsupported Shape raise style: {shape_raise_style!r}",
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
        tuple[
            str,
            str,
        ],
        ...,
    ],
    *,
    artwork_components: tuple[
        tuple[
            str,
            str,
            dict[str, object],
        ],
        ...,
    ] = (),
    artwork_fill_components: tuple[
        tuple[
            str,
            str,
        ],
        ...,
    ] = (),
) -> None:
    """
    Write the physical-component manifest for Shape extrusion.

    Shape-owned components are identified by component name and path only.
    Their physical printer-color assignment belongs to downstream packaging.

    Incorporated Artwork components retain persistent Artifact-color identity
    so downstream packaging can resolve their physical printer assignments.
    """

    manifest_components: list[dict[str, object]] = [
        {
            "name": name,
            "path": component_path,
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

    for (
        name,
        component_path,
    ) in artwork_fill_components:
        manifest_components.append(
            {
                "name": name,
                "path": component_path,
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


def _validate_inner_ridge_height(
    *,
    shape_base_raise: float,
    shape_inner_ridge_raise: float,
) -> None:
    """
    Validate that an Inner Ridge has a nonnegative physical height.
    """

    if shape_base_raise + shape_inner_ridge_raise < 0.0:
        raise ExtrudeError(
            "Shape inner ridge physical height must be greater than or equal to zero."
        )


def _load_border_labels(
    composition_manifest: Path,
) -> dict[str, dict[str, object] | None]:
    """
    Load persistent registered Border Label components.

    Compose owns Border Label participation, typography, fitting, and
    registered X/Y glyph geometry.

    Extrude consumes that persistent contract directly and introduces only
    physical Shape scaling and Z geometry.
    """

    data = json.loads(
        composition_manifest.read_text(
            encoding="utf-8",
        )
    )

    border_labels = data.get(
        "border_labels",
    )

    if border_labels is None:
        return {
            "top": None,
            "bottom": None,
        }

    if not isinstance(
        border_labels,
        dict,
    ):
        raise ValueError("Registered Shape composition Border Labels must be an object.")

    loaded: dict[
        str,
        dict[str, object] | None,
    ] = {}

    for position in (
        "top",
        "bottom",
    ):
        label = border_labels.get(
            position,
        )

        if label is None:
            loaded[position] = None
            continue

        if not isinstance(
            label,
            dict,
        ):
            raise ValueError(
                f"Registered Shape composition {position} Border Label must be an object."
            )

        path = label.get(
            "path",
        )

        if (
            not isinstance(
                path,
                str,
            )
            or not path
        ):
            raise ValueError(
                f"Registered Shape composition {position} Border Label requires a path."
            )

        loaded[position] = label

    return loaded


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
            hole=None,
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
        hole=None,
    )


def _build_loop_component_scad(
    loop: LoopGeometry,
    *,
    component_height: float,
    hole: HoleGeometry | None = None,
) -> str:
    """
    Build the independently printable Shape Loop component.

    Shape Loop is an annulus whose X/Y position has already been resolved
    relative to the complete physical Shape envelope.

    A participating Shape Hole is subtracted from intersecting Loop material.
    """

    geometry = (
        "linear_extrude(\n"
        "    height = component_height,\n"
        "    center = false\n"
        ")\n"
        "    translate([center_x, center_y])\n"
        "        difference() {\n"
        "            circle(r = outer_radius, $fn = 256);\n"
        "            circle(r = inner_radius, $fn = 256);\n"
        "        }\n"
    )

    return (
        f"component_height = {component_height:g};\n"
        f"center_x = {loop.center_x:g};\n"
        f"center_y = {loop.center_y:g};\n"
        f"outer_radius = {loop.outer_radius:g};\n"
        f"inner_radius = {loop.inner_radius:g};\n"
        f"{_build_hole_parameters_scad(hole)}"
        "\n"
        f"{_build_hole_subtracted_geometry_scad(geometry, hole=hole)}"
    )


def _build_border_label_planar_geometry_scad(
    source: str | Path,
    *,
    shape_size: float,
) -> str:
    """
    Build the physical planar footprint of one registered Border Label.

    Compose owns the persistent registered glyph geometry. This helper applies
    the same registered-SVG-to-physical-Shape transform used for component
    extrusion so that inlaid Base partitioning consumes exactly the same X/Y
    geometry.
    """

    source_path = Path(
        source,
    )

    return (
        f"scale([{shape_size:g}, {shape_size:g}, 1])\n"
        "    translate([-0.5, -1.5, 0])\n"
        f'        import("{source_path.as_posix()}", dpi = 25.4);\n'
    )


def _build_border_label_component_scad(
    source: str | Path,
    *,
    shape_size: float,
    shape_base_raise: float,
    shape_border_label_raise: float,
    hole: HoleGeometry | None,
    shape_raise_style: str = "raised",
) -> str:
    """
    Build OpenSCAD for one registered Border Label component.

    Compose owns the persistent registered glyph geometry.

    Registered Shape geometry uses SVG coordinates: X increases rightward
    and Y increases downward. OpenSCAD imports SVG geometry into its
    upward-positive Cartesian coordinate system.

    The imported registered viewport is offset from the Shape origin.
    Extrude removes that viewport offset and applies the physical Shape size,
    while preserving OpenSCAD's SVG-to-Cartesian Y-axis conversion.

    The resulting physical component therefore preserves the visual Shape
    placement authored by Compose:

        registered SVG Top     -> positive physical Y
        registered SVG Bottom  -> negative physical Y

    Raised labels begin at the top of the structural base and extend by
    shape_border_label_raise.

    Inlaid labels preserve the same registered X/Y geometry while spanning
    the complete Shape thickness.

    A participating Shape Hole is subtracted from the physical Border Label
    geometry.
    """

    label_z_offset, label_height = _surface_component_interval(
        shape_raise_style=shape_raise_style,
        shape_base_raise=shape_base_raise,
        component_raise=shape_border_label_raise,
    )

    planar_geometry = _build_border_label_planar_geometry_scad(
        source,
        shape_size=shape_size,
    )

    if hole is not None:
        hole_parameters = _build_hole_parameters_scad(
            hole,
        )

        planar_geometry = (
            "difference() {\n"
            f"{_indent_scad(planar_geometry, 4)}"
            "    translate([hole_x, hole_y])\n"
            "        circle(r = hole_radius, $fn = 256);\n"
            "}\n"
        )
    else:
        hole_parameters = ""

    return (
        f"shape_size = {shape_size:g};\n"
        f"shape_base_raise = {shape_base_raise:g};\n"
        f"shape_border_label_raise = {shape_border_label_raise:g};\n"
        f"{hole_parameters}"
        "\n"
        f"translate([0, 0, {label_z_offset:g}])\n"
        "    linear_extrude(\n"
        f"        height = {label_height:g},\n"
        "        center = false\n"
        "    )\n"
        f"{_indent_scad(planar_geometry, 8)}"
    )


def _build_inner_ridge_component_scad(
    ridge: RegisteredRidge,
    *,
    shape_size: float,
    shape_base_raise: float,
    shape_inner_ridge_raise: float,
    hole: HoleGeometry | None = None,
    shape_raise_style: str = "raised",
) -> str:
    """
    Build OpenSCAD source for the independently printable Inner Ridge.

    Compose owns the Inner Ridge X/Y geometry. Extrude consumes its registered
    outer and inner boundaries and applies only physical dimensionalization.

    Raised dimensionalization places the Inner Ridge above the structural base
    using shape_inner_ridge_raise.

    Inlaid dimensionalization preserves the registered X/Y partition while
    spanning the component through the complete Shape thickness. The resolved
    shape_inner_ridge_raise retains its raised-style meaning but does not
    determine the inlaid Z interval.

    A participating Shape Hole is subtracted from the physical ridge geometry
    while registered boundary modules remain top-level declarations.
    """

    if isinstance(
        ridge,
        RegisteredCircleRidge,
    ):
        outer = (
            f"translate(["
            f"{ridge.outer.cx * shape_size:g}, "
            f"{ridge.outer.cy * shape_size:g}, 0])\n"
            f"    circle(r = {ridge.outer.radius * shape_size:g}, $fn = 256);\n"
        )

        inner = (
            f"translate(["
            f"{ridge.inner.cx * shape_size:g}, "
            f"{ridge.inner.cy * shape_size:g}, 0])\n"
            f"    circle(r = {ridge.inner.radius * shape_size:g}, $fn = 256);\n"
        )

    elif isinstance(
        ridge,
        RegisteredSquareRidge,
    ):
        outer = (
            f"translate(["
            f"{ridge.outer.x * shape_size:g}, "
            f"{ridge.outer.y * shape_size:g}, 0])\n"
            f"    square(["
            f"{ridge.outer.width * shape_size:g}, "
            f"{ridge.outer.height * shape_size:g}], center = false);\n"
        )

        inner = (
            f"translate(["
            f"{ridge.inner.x * shape_size:g}, "
            f"{ridge.inner.y * shape_size:g}, 0])\n"
            f"    square(["
            f"{ridge.inner.width * shape_size:g}, "
            f"{ridge.inner.height * shape_size:g}], center = false);\n"
        )

    elif isinstance(
        ridge,
        RegisteredPolygonRidge,
    ):
        outer = f"polygon(points = {_scad_polygon_points(ridge.outer, shape_size=shape_size)});\n"

        inner = f"polygon(points = {_scad_polygon_points(ridge.inner, shape_size=shape_size)});\n"

    else:
        raise ValueError(f"Unsupported registered Inner Ridge geometry: {type(ridge).__name__}.")

    if shape_raise_style == "raised":
        inner_ridge_z_offset = shape_base_raise
        inner_ridge_height = shape_inner_ridge_raise

    elif shape_raise_style == "inlaid":
        inner_ridge_z_offset = 0.0
        inner_ridge_height = shape_base_raise

    else:
        raise ValueError(
            f"Unsupported Shape raise style: {shape_raise_style!r}",
        )

    geometry = (
        "translate([0, 0, inner_ridge_z_offset])\n"
        "    linear_extrude(\n"
        "        height = inner_ridge_height,\n"
        "        center = false\n"
        "    )\n"
        "        difference() {\n"
        "            registered_inner_ridge_outer_boundary();\n"
        "            registered_inner_ridge_inner_boundary();\n"
        "        }\n"
    )

    return (
        f"shape_size = {shape_size:g};\n"
        f"shape_base_raise = {shape_base_raise:g};\n"
        f"shape_inner_ridge_raise = {shape_inner_ridge_raise:g};\n"
        f"inner_ridge_z_offset = {inner_ridge_z_offset:g};\n"
        f"inner_ridge_height = {inner_ridge_height:g};\n"
        f"{_build_hole_parameters_scad(hole)}"
        "\n"
        f"// {INNER_RIDGE_OUTER_BOUNDARY_ID}\n"
        "module registered_inner_ridge_outer_boundary() {\n"
        f"{_indent_scad(outer, 4)}"
        "}\n"
        "\n"
        f"// {INNER_RIDGE_INNER_BOUNDARY_ID}\n"
        "module registered_inner_ridge_inner_boundary() {\n"
        f"{_indent_scad(inner, 4)}"
        "}\n"
        "\n"
        f"{_build_hole_subtracted_geometry_scad(geometry, hole=hole)}"
    )


def _build_artwork_fill_planar_geometry_scad(
    fill: RegisteredArtworkFill,
    *,
    shape_size: float,
) -> str:
    """
    Build the physical planar footprint of registered Shape Artwork Fill.

    Compose owns the registered Artwork Fill partition. This helper applies
    only Shape's physical X/Y dimensionalization so the resulting planar
    geometry can be shared by component extrusion and inlaid Base
    partitioning.
    """

    outer_boundary = _build_registered_fill_boundary_scad(
        fill.outer_boundary,
        shape_size=shape_size,
    )

    inner_boundary = _build_registered_fill_boundary_scad(
        fill.inner_boundary,
        shape_size=shape_size,
    )

    return (
        f"difference() {{\n{_indent_scad(outer_boundary, 4)}{_indent_scad(inner_boundary, 4)}}}\n"
    )


def _build_artwork_fill_scad(
    fill: RegisteredArtworkFill,
    *,
    shape_size: float,
    shape_base_raise: float,
    shape_artwork_fill_raise: float,
    hole: HoleGeometry | None,
    shape_raise_style: str = "raised",
) -> str:
    """
    Build OpenSCAD for the physical Shape-owned Artwork Fill component.

    Registered X/Y fill geometry is preserved from Compose.

    Raised dimensionalization begins at the top of the structural base and
    extends by shape_artwork_fill_raise.

    Inlaid dimensionalization spans the complete Shape thickness. The resolved
    fill raise remains configuration with its raised-style meaning but does not
    determine the inlaid physical Z interval.
    """

    fill_z_offset, fill_height = _surface_component_interval(
        shape_raise_style=shape_raise_style,
        shape_base_raise=shape_base_raise,
        component_raise=shape_artwork_fill_raise,
    )

    planar_geometry = _build_artwork_fill_planar_geometry_scad(
        fill,
        shape_size=shape_size,
    )

    geometry = (
        f"translate([0, 0, {fill_z_offset:g}])\n"
        "    linear_extrude(\n"
        f"        height = {fill_height:g},\n"
        "        center = false\n"
        "    )\n"
        f"{_indent_scad(planar_geometry, 8)}"
    )

    if hole is not None:
        geometry = _build_hole_subtracted_geometry_scad(
            geometry,
            hole=hole,
        )

    return (
        f"shape_size = {shape_size:g};\n"
        f"shape_base_raise = {shape_base_raise:g};\n"
        f"shape_artwork_fill_raise = {shape_artwork_fill_raise:g};\n"
        "\n"
        f"{geometry}"
    )


def _build_registered_fill_boundary_scad(
    boundary: dict[str, object],
    *,
    shape_size: float,
) -> str:
    """
    Build physical OpenSCAD geometry from one persisted registered boundary.
    """

    boundary_type = boundary.get(
        "type",
    )

    if boundary_type == "circle":
        cx = (
            _registered_fill_number(
                boundary,
                "cx",
                boundary_type="circle",
            )
            * shape_size
        )

        cy = (
            _registered_fill_number(
                boundary,
                "cy",
                boundary_type="circle",
            )
            * shape_size
        )

        radius = (
            _registered_fill_number(
                boundary,
                "r",
                boundary_type="circle",
            )
            * shape_size
        )

        return f"translate([{cx:g}, {cy:g}, 0])\n    circle(r = {radius:g}, $fn = 256);\n"

    if boundary_type == "rect":
        x = (
            _registered_fill_number(
                boundary,
                "x",
                boundary_type="rect",
            )
            * shape_size
        )

        y = (
            _registered_fill_number(
                boundary,
                "y",
                boundary_type="rect",
            )
            * shape_size
        )

        width = (
            _registered_fill_number(
                boundary,
                "width",
                boundary_type="rect",
            )
            * shape_size
        )

        height = (
            _registered_fill_number(
                boundary,
                "height",
                boundary_type="rect",
            )
            * shape_size
        )

        return (
            f"translate([{x:g}, {y:g}, 0])\n    square([{width:g}, {height:g}], center = false);\n"
        )

    if boundary_type in {
        "polygon",
        "path",
    }:
        points = boundary.get(
            "points",
        )

        if not isinstance(
            points,
            list,
        ):
            raise ValueError(f"Registered Artwork-fill {boundary_type} boundary requires points.")

        physical_points: list[str] = []

        for point in points:
            if not isinstance(
                point,
                dict,
            ):
                raise ValueError(
                    f"Registered Artwork-fill {boundary_type} point must be an object."
                )

            x = (
                _registered_fill_number(
                    point,
                    "x",
                    boundary_type=boundary_type,
                )
                * shape_size
            )

            y = (
                _registered_fill_number(
                    point,
                    "y",
                    boundary_type=boundary_type,
                )
                * shape_size
            )

            physical_points.append(
                f"[{x:g}, {y:g}]",
            )

        return (
            "polygon(points = ["
            + ", ".join(
                physical_points,
            )
            + "]);\n"
        )

    if boundary_type == "group":
        children = boundary.get(
            "children",
        )

        if not isinstance(
            children,
            list,
        ):
            raise ValueError("Registered Artwork-fill group boundary requires children.")

        child_sources: list[str] = []

        for child in children:
            if not isinstance(
                child,
                dict,
            ):
                raise ValueError("Registered Artwork-fill group child must be an object.")

            child_sources.append(
                _build_registered_fill_boundary_scad(
                    child,
                    shape_size=shape_size,
                )
            )

        return (
            "union() {\n"
            + "".join(
                _indent_scad(
                    child,
                    4,
                )
                for child in child_sources
            )
            + "}\n"
        )

    raise ValueError(f"Unsupported registered Artwork-fill boundary type: {boundary_type!r}.")


def _registered_fill_number(
    data: dict[str, object],
    name: str,
    *,
    boundary_type: object,
) -> float:
    """
    Return one numeric value from persistent registered fill geometry.
    """

    value = data.get(
        name,
    )

    if not isinstance(
        value,
        int | float,
    ) or isinstance(
        value,
        bool,
    ):
        raise ValueError(
            f"Registered Artwork-fill {boundary_type!r} boundary requires numeric {name!r}."
        )

    return float(
        value,
    )


def _indent_scad(
    source: str,
    spaces: int,
) -> str:
    """
    Indent generated OpenSCAD source.
    """

    prefix = " " * spaces

    return "".join(
        prefix + line
        for line in source.splitlines(
            keepends=True,
        )
    )


def _build_hole_parameters_scad(
    hole: HoleGeometry | None,
) -> str:
    """
    Build OpenSCAD parameter declarations for a participating Shape Hole.
    """

    if hole is None:
        return ""

    return (
        f"hole_center_x = {hole.center_x:g};\n"
        f"hole_center_y = {hole.center_y:g};\n"
        f"hole_radius = {hole.radius:g};\n"
    )


def _build_hole_subtracted_geometry_scad(
    geometry: str,
    *,
    hole: HoleGeometry | None,
) -> str:
    """
    Apply Shape Hole subtraction to one executable physical geometry expression.

    The caller owns the complete SCAD program, including parameter and module
    declarations. This helper operates only on executable constructive geometry
    and therefore never moves declarations inside a geometry block.
    """

    if hole is None:
        return geometry

    return (
        "difference() {\n"
        f"{_indent_scad(geometry, 4)}"
        "\n"
        "    translate([hole_center_x, hole_center_y, -1000])\n"
        "        cylinder(\n"
        "            h = 2000,\n"
        "            r = hole_radius,\n"
        "            center = false,\n"
        "            $fn = 256\n"
        "        );\n"
        "}\n"
    )


def _build_inner_ridge_planar_geometry_scad(
    ridge: RegisteredRidge,
    *,
    shape_size: float,
) -> str:
    """
    Build the physical planar footprint of one registered Inner Ridge.

    Compose owns the registered Inner Ridge partition. This helper applies only
    Shape's physical X/Y dimensionalization so the resulting planar geometry can
    participate in inlaid Base subtraction.
    """

    if isinstance(
        ridge,
        RegisteredCircleRidge,
    ):
        outer = (
            f"translate(["
            f"{ridge.outer.cx * shape_size:g}, "
            f"{ridge.outer.cy * shape_size:g}, 0])\n"
            f"    circle(r = {ridge.outer.radius * shape_size:g}, $fn = 256);\n"
        )

        inner = (
            f"translate(["
            f"{ridge.inner.cx * shape_size:g}, "
            f"{ridge.inner.cy * shape_size:g}, 0])\n"
            f"    circle(r = {ridge.inner.radius * shape_size:g}, $fn = 256);\n"
        )

    elif isinstance(
        ridge,
        RegisteredSquareRidge,
    ):
        outer = (
            f"translate(["
            f"{ridge.outer.x * shape_size:g}, "
            f"{ridge.outer.y * shape_size:g}, 0])\n"
            f"    square(["
            f"{ridge.outer.width * shape_size:g}, "
            f"{ridge.outer.height * shape_size:g}], center = false);\n"
        )

        inner = (
            f"translate(["
            f"{ridge.inner.x * shape_size:g}, "
            f"{ridge.inner.y * shape_size:g}, 0])\n"
            f"    square(["
            f"{ridge.inner.width * shape_size:g}, "
            f"{ridge.inner.height * shape_size:g}], center = false);\n"
        )

    elif isinstance(
        ridge,
        RegisteredPolygonRidge,
    ):
        outer = f"polygon(points = {_scad_polygon_points(ridge.outer, shape_size=shape_size)});\n"

        inner = f"polygon(points = {_scad_polygon_points(ridge.inner, shape_size=shape_size)});\n"

    else:
        raise ValueError(f"Unsupported registered Inner Ridge geometry: {type(ridge).__name__}.")

    return f"difference() {{\n{_indent_scad(outer, 4)}{_indent_scad(inner, 4)}}}\n"


def _build_artwork_planar_geometry_scad(
    source: str,
    *,
    shape_size: float,
    artwork_registered_height: float,
    artwork_scale: float,
    artwork_translate_x: float,
    artwork_translate_y: float,
) -> str:
    """
    Build physical planar geometry for one registered Artwork component.

    Registered Artwork uses a zero-origin SVG coordinate system with positive Y
    downward. OpenSCAD SVG import maps that geometry into its upward-positive
    coordinate system while preserving the Artwork's top-view orientation.

    The persistent Artwork-to-Shape composition transform is expressed in SVG
    registered coordinates. Its Y translation is therefore converted into the
    OpenSCAD coordinate system before being applied.
    """

    artwork_openscad_translate_y = (
        -(artwork_registered_height * artwork_scale) - artwork_translate_y
    )

    return (
        f"scale([{shape_size:g}, {shape_size:g}, 1])\n"
        "    translate([\n"
        f"        {artwork_translate_x:g},\n"
        f"        {artwork_openscad_translate_y:g},\n"
        "        0\n"
        "    ])\n"
        f"        scale([{artwork_scale:g}, {artwork_scale:g}, 1])\n"
        f'            import("{source}", dpi = 25.4);\n'
    )


def _build_artwork_planar_union_scad(
    artwork: dict[str, object],
    source_directory: Path,
    *,
    shape_size: float,
) -> str:
    """
    Build the union of incorporated registered Artwork in physical X/Y space.

    The resulting planar geometry represents the complete physical footprint
    occupied by incorporated Artwork and is suitable for subtraction from an
    inlaid Shape Base.
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

    geometries: list[str] = []

    for component in components:
        if not isinstance(
            component,
            dict,
        ):
            raise ValueError("Registered Artwork component must be an object.")

        source_path = source_directory / str(
            component["path"],
        )

        if not source_path.is_file():
            raise ValueError(f"Registered Artwork component does not exist: {source_path}")

        geometries.append(
            _build_artwork_planar_geometry_scad(
                _scad_path(
                    source_path,
                ),
                shape_size=shape_size,
                artwork_registered_height=registered_height,
                artwork_scale=scale,
                artwork_translate_x=translate_x,
                artwork_translate_y=translate_y,
            )
        )

    return (
        "union() {\n"
        + "".join(
            _indent_scad(
                geometry,
                4,
            )
            for geometry in geometries
        )
        + "}\n"
    )


def _build_planar_union_scad(
    geometries: list[str],
) -> str | None:
    """
    Build one planar union from participating physical X/Y geometries.

    An empty collection represents no planar subtraction.
    """

    if not geometries:
        return None

    return (
        "union() {\n"
        + "".join(
            _indent_scad(
                geometry,
                4,
            )
            for geometry in geometries
        )
        + "}\n"
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
    hole: HoleGeometry | None = None,
    shape_raise_style: str = "raised",
) -> str:
    """
    Build OpenSCAD source for one incorporated Artwork component.

    Registered Artwork uses its persistent registered-space transform for
    physical X/Y placement.

    Raised dimensionalization places Artwork above the structural base using
    shape_artwork_raise.

    Inlaid dimensionalization spans Artwork through the complete Shape
    thickness. The resolved shape_artwork_raise retains its raised-style
    meaning but does not determine the inlaid Z interval.

    A participating Shape Hole is subtracted from the planar Artwork geometry
    before extrusion so SVG-derived geometry is materialized as STL only once.
    """

    if shape_raise_style == "raised":
        artwork_z_offset = shape_base_raise
        artwork_height = shape_artwork_raise

    elif shape_raise_style == "inlaid":
        artwork_z_offset = 0.0
        artwork_height = shape_base_raise

    else:
        raise ValueError(
            f"Unsupported Shape raise style: {shape_raise_style!r}",
        )

    planar_geometry = _build_artwork_planar_geometry_scad(
        source,
        shape_size=shape_size,
        artwork_registered_height=artwork_registered_height,
        artwork_scale=artwork_scale,
        artwork_translate_x=artwork_translate_x,
        artwork_translate_y=artwork_translate_y,
    )

    if hole is not None:
        planar_geometry = (
            "difference() {\n"
            f"{_indent_scad(planar_geometry, 4)}"
            "\n"
            "    translate([hole_center_x, hole_center_y, 0])\n"
            "        circle(\n"
            "            r = hole_radius,\n"
            "            $fn = 256\n"
            "        );\n"
            "}\n"
        )

    return (
        f"shape_size = {shape_size:g};\n"
        f"shape_base_raise = {shape_base_raise:g};\n"
        f"shape_artwork_raise = {shape_artwork_raise:g};\n"
        f"artwork_z_offset = {artwork_z_offset:g};\n"
        f"artwork_height = {artwork_height:g};\n"
        f"artwork_registered_width = {artwork_registered_width:g};\n"
        f"{_build_hole_parameters_scad(hole)}"
        "\n"
        "translate([0, 0, artwork_z_offset])\n"
        "    linear_extrude(\n"
        "        height = artwork_height,\n"
        "        center = false\n"
        "    )\n"
        f"{_indent_scad(planar_geometry, 8)}"
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
    composition: str,
    *,
    shape_size: float,
    shape_base_raise: float,
    hole: HoleGeometry | None,
    planar_subtraction: str | None = None,
) -> str:
    """
    Build OpenSCAD source for the physical Shape base.

    Optional planar subtraction removes participating inlaid surface-component
    regions from the Base before physical extrusion.

    A participating Shape Hole is independently subtracted from the constructive
    planar geometry before the Base is materialized as STL.
    """

    shape_source = f"""\
scale([shape_size, shape_size, 1])
    translate([-0.5, -1.5, 0])
        import("{composition}", dpi = 25.4);
"""

    subtractive_geometry: list[str] = []

    if planar_subtraction is not None:
        subtractive_geometry.append(
            planar_subtraction,
        )

    hole_parameters = ""

    if hole is not None:
        hole_parameters = (
            f"hole_center_x = {hole.center_x:g};\n"
            f"hole_center_y = {hole.center_y:g};\n"
            f"hole_radius = {hole.radius:g};\n"
        )

        subtractive_geometry.append(
            "translate([hole_center_x, hole_center_y, 0])\n"
            "    circle(\n"
            "        r = hole_radius,\n"
            "        $fn = 256\n"
            "    );\n"
        )

    if subtractive_geometry:
        planar_source = (
            "difference() {\n"
            f"{_indent_scad(shape_source, 4)}"
            + "".join(
                _indent_scad(
                    geometry,
                    4,
                )
                for geometry in subtractive_geometry
            )
            + "}\n"
        )
    else:
        planar_source = shape_source

    return f"""\
shape_size = {shape_size:g};
shape_base_raise = {shape_base_raise:g};
{hole_parameters}
linear_extrude(
    height = shape_base_raise,
    center = false
)
{planar_source}"""


def _build_circle_base_scad(
    circle: RegisteredCircle,
    *,
    shape_size: float,
    shape_base_raise: float,
    hole: HoleGeometry | None = None,
    planar_subtraction: str | None = None,
) -> str:
    """
    Build OpenSCAD source for a physical circle base.

    Optional planar subtraction removes participating inlaid surface-component
    regions from the Base before physical extrusion.

    A participating Shape Hole is independently subtracted from the constructive
    planar geometry before the Base is materialized as STL.
    """

    x = circle.cx * shape_size
    y = circle.cy * shape_size
    radius = circle.radius * shape_size

    base_geometry = f"translate([{x:g}, {y:g}, 0])\n    circle(r = {radius:g}, $fn = 256);\n"

    subtractive_geometry: list[str] = []

    if planar_subtraction is not None:
        subtractive_geometry.append(
            planar_subtraction,
        )

    if hole is not None:
        subtractive_geometry.append(
            "translate([hole_center_x, hole_center_y, 0])\n"
            "    circle(r = hole_radius, $fn = 256);\n"
        )

    if subtractive_geometry:
        planar_geometry = (
            "difference() {\n"
            + _indent_scad(
                base_geometry,
                4,
            )
            + "".join(
                _indent_scad(
                    geometry,
                    4,
                )
                for geometry in subtractive_geometry
            )
            + "}\n"
        )
    else:
        planar_geometry = base_geometry

    return (
        f"shape_size = {shape_size:g};\n"
        f"shape_base_raise = {shape_base_raise:g};\n"
        f"{_build_hole_parameters_scad(hole)}"
        "\n"
        "linear_extrude(\n"
        "    height = shape_base_raise,\n"
        "    center = false\n"
        ")\n"
        f"{_indent_scad(planar_geometry, 4)}"
    )


def _build_rectangle_base_scad(
    rectangle: RegisteredRectangle,
    *,
    shape_size: float,
    shape_base_raise: float,
    hole: HoleGeometry | None = None,
    planar_subtraction: str | None = None,
) -> str:
    """
    Build OpenSCAD source for a physical registered rectangle base.

    Optional planar subtraction removes participating inlaid surface-component
    regions from the Base before physical extrusion.

    A participating Shape Hole is independently subtracted from the constructive
    planar geometry before the Base is materialized as STL.
    """

    x = rectangle.x * shape_size
    y = rectangle.y * shape_size
    width = rectangle.width * shape_size
    height = rectangle.height * shape_size

    base_geometry = (
        f"translate([{x:g}, {y:g}, 0])\n    square([{width:g}, {height:g}], center = false);\n"
    )

    subtractive_geometry: list[str] = []

    if planar_subtraction is not None:
        subtractive_geometry.append(
            planar_subtraction,
        )

    if hole is not None:
        subtractive_geometry.append(
            "translate([hole_center_x, hole_center_y, 0])\n"
            "    circle(r = hole_radius, $fn = 256);\n"
        )

    if subtractive_geometry:
        planar_geometry = (
            "difference() {\n"
            + _indent_scad(
                base_geometry,
                4,
            )
            + "".join(
                _indent_scad(
                    geometry,
                    4,
                )
                for geometry in subtractive_geometry
            )
            + "}\n"
        )
    else:
        planar_geometry = base_geometry

    return (
        f"shape_size = {shape_size:g};\n"
        f"shape_base_raise = {shape_base_raise:g};\n"
        f"{_build_hole_parameters_scad(hole)}"
        "\n"
        "linear_extrude(\n"
        "    height = shape_base_raise,\n"
        "    center = false\n"
        ")\n"
        f"{_indent_scad(planar_geometry, 4)}"
    )


def _build_integrated_circle_base_scad(
    ridge: RegisteredCircleRidge,
    *,
    shape_size: float,
    shape_base_raise: float,
    shape_outer_ridge_raise: float,
    hole: HoleGeometry | None = None,
) -> str:
    """
    Build OpenSCAD source for the base material of an integrated circle ridge.

    A participating Shape Hole is subtracted from the native constructive
    base geometry before STL materialization.
    """

    if shape_outer_ridge_raise >= 0.0:
        return _build_circle_base_scad(
            ridge.outer,
            shape_size=shape_size,
            shape_base_raise=shape_base_raise,
            hole=hole,
        )

    outer_x = ridge.outer.cx * shape_size
    outer_y = ridge.outer.cy * shape_size
    outer_radius = ridge.outer.radius * shape_size

    inner_x = ridge.inner.cx * shape_size
    inner_y = ridge.inner.cy * shape_size
    inner_radius = ridge.inner.radius * shape_size

    geometry = (
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

    return (
        f"shape_size = {shape_size:g};\n"
        f"shape_base_raise = {shape_base_raise:g};\n"
        f"shape_outer_ridge_raise = {shape_outer_ridge_raise:g};\n"
        f"{_build_hole_parameters_scad(hole)}"
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
        f"{_build_hole_subtracted_geometry_scad(geometry, hole=hole)}"
    )


def _build_integrated_square_base_scad(
    ridge: RegisteredSquareRidge,
    *,
    shape_size: float,
    shape_base_raise: float,
    shape_outer_ridge_raise: float,
    hole: HoleGeometry | None = None,
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

    A participating Shape Hole is subtracted from the native constructive
    base geometry before STL materialization.
    """

    if shape_outer_ridge_raise >= 0.0:
        return _build_rectangle_base_scad(
            ridge.outer,
            shape_size=shape_size,
            shape_base_raise=shape_base_raise,
            hole=hole,
        )

    boundaries = _build_square_boundary_modules(
        ridge,
        shape_size=shape_size,
    )

    geometry = (
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

    return (
        f"shape_size = {shape_size:g};\n"
        f"shape_base_raise = {shape_base_raise:g};\n"
        f"shape_outer_ridge_raise = {shape_outer_ridge_raise:g};\n"
        f"{_build_hole_parameters_scad(hole)}"
        "\n"
        f"{boundaries}"
        "\n"
        f"{_build_hole_subtracted_geometry_scad(geometry, hole=hole)}"
    )


def _build_integrated_circle_ridge_component_scad(
    ridge: RegisteredCircleRidge,
    *,
    shape_size: float,
    shape_base_raise: float,
    shape_outer_ridge_raise: float,
    hole: HoleGeometry | None = None,
) -> str:
    """
    Build OpenSCAD source for the independently printable integrated ridge.

    A participating Shape Hole is subtracted from the native constructive
    ridge geometry before STL materialization.
    """

    outer_x = ridge.outer.cx * shape_size
    outer_y = ridge.outer.cy * shape_size
    outer_radius = ridge.outer.radius * shape_size

    inner_x = ridge.inner.cx * shape_size
    inner_y = ridge.inner.cy * shape_size
    inner_radius = ridge.inner.radius * shape_size

    geometry = (
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

    return (
        f"shape_size = {shape_size:g};\n"
        f"shape_base_raise = {shape_base_raise:g};\n"
        f"shape_outer_ridge_raise = {shape_outer_ridge_raise:g};\n"
        f"{_build_hole_parameters_scad(hole)}"
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
        f"{_build_hole_subtracted_geometry_scad(geometry, hole=hole)}"
    )


def _build_separate_circle_ridge_component_scad(
    ridge: RegisteredCircleRidge,
    *,
    shape_size: float,
    shape_base_raise: float,
    shape_outer_ridge_raise: float,
    hole: HoleGeometry | None = None,
) -> str:
    """
    Build OpenSCAD source for a separate circle ridge component.

    This function preserves the raised-style construction contract used by
    existing callers and tests.
    """

    assembled_ridge_height = shape_base_raise + shape_outer_ridge_raise

    return _build_separate_circle_ridge_component_scad_at_height(
        ridge,
        shape_size=shape_size,
        component_height=assembled_ridge_height,
        hole=hole,
    )


def _build_separate_polygon_ridge_component_scad(
    ridge: RegisteredPolygonRidge,
    *,
    shape_size: float,
    shape_base_raise: float,
    shape_outer_ridge_raise: float,
    hole: HoleGeometry | None = None,
) -> str:
    """
    Build OpenSCAD source for an independently printable separate polygon ridge.

    The registered polygon ridge owns the X/Y partition. The separate ridge
    occupies the registered perimeter from Z=0 through the complete assembled
    ridge height.

    A participating Shape Hole is subtracted from the native constructive
    ridge geometry before STL materialization.
    """

    assembled_ridge_height = shape_base_raise + shape_outer_ridge_raise

    return _build_separate_polygon_ridge_component_scad_at_height(
        ridge,
        shape_size=shape_size,
        component_height=assembled_ridge_height,
        hole=hole,
    )


def _build_separate_polygon_ridge_scad(
    ridge: RegisteredPolygonRidge,
    *,
    shape_size: float,
    shape_base_raise: float,
    shape_outer_ridge_raise: float,
) -> str:
    """
    Build complete assembled geometry for a separate polygon ridge.

    This helper exists for complete-geometry construction used by the
    compatibility/test boundary. Ridge style changes component partitioning,
    not the intended assembled Shape geometry.
    """

    assembled_ridge_height = shape_base_raise + shape_outer_ridge_raise

    boundaries = _build_polygon_boundary_modules(
        ridge,
        shape_size=shape_size,
    )

    if assembled_ridge_height <= 0.0:
        return (
            f"shape_size = {shape_size:g};\n"
            f"shape_base_raise = {shape_base_raise:g};\n"
            f"assembled_ridge_height = {assembled_ridge_height:g};\n"
            "\n"
            f"{boundaries}"
            "\n"
            "linear_extrude(\n"
            "    height = shape_base_raise,\n"
            "    center = false\n"
            ")\n"
            "    registered_ridge_inner_boundary();\n"
        )

    return (
        f"shape_size = {shape_size:g};\n"
        f"shape_base_raise = {shape_base_raise:g};\n"
        f"assembled_ridge_height = {assembled_ridge_height:g};\n"
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
        "        height = assembled_ridge_height,\n"
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
    hole: HoleGeometry | None = None,
) -> str:
    """
    Build OpenSCAD source for a positive integrated square ridge component.

    A participating Shape Hole is subtracted from the native constructive
    ridge geometry before STL materialization.
    """

    boundaries = _build_square_boundary_modules(
        ridge,
        shape_size=shape_size,
    )

    geometry = (
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

    return (
        f"shape_size = {shape_size:g};\n"
        f"shape_base_raise = {shape_base_raise:g};\n"
        f"shape_outer_ridge_raise = {shape_outer_ridge_raise:g};\n"
        f"{_build_hole_parameters_scad(hole)}"
        "\n"
        f"{boundaries}"
        "\n"
        f"{_build_hole_subtracted_geometry_scad(geometry, hole=hole)}"
    )


def _build_separate_square_ridge_component_scad(
    ridge: RegisteredSquareRidge,
    *,
    shape_size: float,
    shape_base_raise: float,
    shape_outer_ridge_raise: float,
    hole: HoleGeometry | None = None,
) -> str:
    """
    Build OpenSCAD source for a separate square ridge component.

    This function preserves the raised-style construction contract used by
    existing callers and tests.
    """

    assembled_ridge_height = shape_base_raise + shape_outer_ridge_raise

    return _build_separate_square_ridge_component_scad_at_height(
        ridge,
        shape_size=shape_size,
        component_height=assembled_ridge_height,
        hole=hole,
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
    hole: HoleGeometry | None = None,
    planar_subtraction: str | None = None,
) -> str:
    """
    Build OpenSCAD source for a physical registered polygon base.

    Optional planar subtraction removes participating inlaid surface-component
    regions from the Base before physical extrusion.

    A participating Shape Hole is independently subtracted from the constructive
    planar geometry before the Base is materialized as STL.
    """

    points = _scad_polygon_points(
        polygon,
        shape_size=shape_size,
    )

    base_geometry = f"polygon(points = {points});\n"

    subtractive_geometry: list[str] = []

    if planar_subtraction is not None:
        subtractive_geometry.append(
            planar_subtraction,
        )

    if hole is not None:
        subtractive_geometry.append(
            "translate([hole_center_x, hole_center_y, 0])\n"
            "    circle(r = hole_radius, $fn = 256);\n"
        )

    if subtractive_geometry:
        planar_geometry = (
            "difference() {\n"
            + _indent_scad(
                base_geometry,
                4,
            )
            + "".join(
                _indent_scad(
                    geometry,
                    4,
                )
                for geometry in subtractive_geometry
            )
            + "}\n"
        )
    else:
        planar_geometry = base_geometry

    return (
        f"shape_size = {shape_size:g};\n"
        f"shape_base_raise = {shape_base_raise:g};\n"
        f"{_build_hole_parameters_scad(hole)}"
        "\n"
        "linear_extrude(\n"
        "    height = shape_base_raise,\n"
        "    center = false\n"
        ")\n"
        f"{_indent_scad(planar_geometry, 4)}"
    )


def _build_integrated_polygon_ridge_component_scad(
    ridge: RegisteredPolygonRidge,
    *,
    shape_size: float,
    shape_base_raise: float,
    shape_outer_ridge_raise: float,
    hole: HoleGeometry | None = None,
) -> str:
    """
    Build OpenSCAD source for a positive integrated polygon ridge component.

    A participating Shape Hole is subtracted from the native constructive
    ridge geometry before STL materialization.
    """

    boundaries = _build_polygon_boundary_modules(
        ridge,
        shape_size=shape_size,
    )

    geometry = (
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

    return (
        f"shape_size = {shape_size:g};\n"
        f"shape_base_raise = {shape_base_raise:g};\n"
        f"shape_outer_ridge_raise = {shape_outer_ridge_raise:g};\n"
        f"{_build_hole_parameters_scad(hole)}"
        "\n"
        f"{boundaries}"
        "\n"
        f"{_build_hole_subtracted_geometry_scad(geometry, hole=hole)}"
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


def _load_artwork_fill(
    composition_manifest: Path,
) -> RegisteredArtworkFill | None:
    """
    Load persistent registered Artwork-fill geometry.

    Extrusion consumes the compose-stage fill contract directly rather than
    rediscovering the Artwork envelope or reconstructing fill policy.
    """

    data = json.loads(
        composition_manifest.read_text(
            encoding="utf-8",
        )
    )

    artwork_fill = data.get(
        "artwork_fill",
    )

    if artwork_fill is None:
        return None

    if not isinstance(
        artwork_fill,
        dict,
    ):
        raise ValueError("Registered Shape composition Artwork fill must be an object.")

    outer_boundary = artwork_fill.get(
        "outer_boundary",
    )

    inner_boundary = artwork_fill.get(
        "inner_boundary",
    )

    if not isinstance(
        outer_boundary,
        dict,
    ):
        raise ValueError("Registered Shape composition Artwork fill requires an outer boundary.")

    if not isinstance(
        inner_boundary,
        dict,
    ):
        raise ValueError("Registered Shape composition Artwork fill requires an inner boundary.")

    return RegisteredArtworkFill(
        outer_boundary=outer_boundary,
        inner_boundary=inner_boundary,
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


def _load_inner_ridge(
    composition: Path,
) -> RegisteredRidge | None:
    """
    Load the registered Inner Ridge partition from Shape composition.

    Inner Ridge participation and X/Y geometry have already been established
    during registered composition. Extrusion consumes the persisted semantic
    outer and inner boundaries directly.
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

        if element_id == INNER_RIDGE_OUTER_BOUNDARY_ID:
            outer_element = element

        elif element_id == INNER_RIDGE_INNER_BOUNDARY_ID:
            inner_element = element

    if outer_element is None and inner_element is None:
        return None

    if outer_element is None:
        raise ValueError(
            "Registered Inner Ridge composition contains an inner boundary "
            "without an outer boundary."
        )

    if inner_element is None:
        raise ValueError(
            "Registered Inner Ridge composition contains an outer boundary "
            "without an inner boundary."
        )

    outer_kind = _local_name(
        outer_element.tag,
    )

    inner_kind = _local_name(
        inner_element.tag,
    )

    if outer_kind != inner_kind:
        raise ValueError(
            "Registered Inner Ridge outer and inner boundaries must use matching geometry."
        )

    if outer_kind == "circle":
        outer = _load_registered_circle(
            outer_element,
            boundary_name=INNER_RIDGE_OUTER_BOUNDARY_ID,
        )

        inner = _load_registered_circle(
            inner_element,
            boundary_name=INNER_RIDGE_INNER_BOUNDARY_ID,
        )

        if inner.radius > outer.radius:
            raise ValueError("Registered Inner Ridge inner boundary exceeds its outer boundary.")

        return RegisteredCircleRidge(
            outer=outer,
            inner=inner,
        )

    if outer_kind == "rect":
        outer = _load_registered_rectangle(
            outer_element,
            boundary_name=INNER_RIDGE_OUTER_BOUNDARY_ID,
        )

        inner = _load_registered_rectangle(
            inner_element,
            boundary_name=INNER_RIDGE_INNER_BOUNDARY_ID,
        )

        if outer.width != outer.height:
            raise ValueError(
                "Registered Inner Ridge outer square boundary must have equal width and height."
            )

        if inner.width != inner.height:
            raise ValueError(
                "Registered Inner Ridge inner square boundary must have equal width and height."
            )

        if (
            inner.x < outer.x
            or inner.y < outer.y
            or inner.x + inner.width > outer.x + outer.width
            or inner.y + inner.height > outer.y + outer.height
        ):
            raise ValueError("Registered Inner Ridge inner boundary exceeds its outer boundary.")

        return RegisteredSquareRidge(
            outer=outer,
            inner=inner,
        )

    if outer_kind == "polygon":
        outer = _load_registered_polygon(
            outer_element,
            boundary_name=INNER_RIDGE_OUTER_BOUNDARY_ID,
        )

        inner = _load_registered_polygon(
            inner_element,
            boundary_name=INNER_RIDGE_INNER_BOUNDARY_ID,
        )

        if len(inner.vertices) != len(outer.vertices):
            raise ValueError(
                "Registered Inner Ridge outer and inner polygon boundaries "
                "must have the same number of vertices."
            )

        return RegisteredPolygonRidge(
            outer=outer,
            inner=inner,
        )

    raise ValueError(f"Unsupported registered Inner Ridge boundary geometry: {outer_kind!r}.")


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
