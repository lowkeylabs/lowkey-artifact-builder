"""
Artwork extrusion stage.

The extrusion stage converts registered vector color layers into
independently printable STL components.

Each vector layer shares a common registered coordinate system described
by the vector manifest. The extrusion stage dimensionalizes that common
coordinate system to the configured physical artwork size, centers it
about the origin, and linearly extrudes it from Z=0 through the
configured artwork raise.

The vector manifest identifies the dynamically generated vector layers
that participate in this stage and records their common registered
coordinate extent. Artifact color information and physical printer
assignments are preserved through extrusion into the declared extrusion
manifest.

Filesystem layout, dependency resolution, and configuration resolution
are responsibilities of the build engine. This implementation consumes
only the paths and values supplied through StageContext.
"""
# File: src/lowkey_artifact_builder/model/models/artwork/stages/extrude.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from lowkey_artifact_builder.engine import (
    StageContext,
)
from lowkey_artifact_builder.model.models.artwork.loop import (
    Bounds,
    LoopGeometry,
    create_loop_geometry,
)
from lowkey_artifact_builder.model.models.artwork.loop_color import (
    resolve_loop_color,
)
from lowkey_artifact_builder.model.models.artwork.vector_manifest import (
    VectorLayer,
    VectorManifest,
)
from lowkey_artifact_builder.tools.inkscape import (
    InkscapeError,
    query_all,
)
from lowkey_artifact_builder.tools.openscad import (
    OpenSCADError,
    render_stl_source,
)

# =========================================================
# Errors
# =========================================================


class ExtrudeError(RuntimeError):
    """
    Raised when artwork extrusion cannot be completed.
    """


# =========================================================
# Public interface
# =========================================================


def execute(
    context: StageContext,
) -> None:
    """
    Execute the artwork extrusion stage.

    The stage consumes:

        vector.manifest
            Manifest describing the registered vector color layers,
            their common registered coordinate extent, and the registered
            occupied Artwork envelope.

        artwork_size
            Maximum physical X/Y extent of the occupied Artwork envelope
            in millimeters.

        artwork_raise
            Physical extrusion height of the artwork geometry in
            millimeters.

        loop_inner_diameter
            Inner diameter of the optional Artwork Loop. A value greater
            than zero causes the Loop to participate.

        loop_width
            Radial width of a participating Loop.

        loop_position
            Cardinal attachment position of a participating Loop.

        loop_raise
            Physical extrusion height of a participating Loop.

        loop_color
            Physical semantic color of a participating Loop. When not
            explicitly configured, Artwork resolves the effective color
            from the registered Artwork at the attachment position.

    The stage produces:

        manifest
            Manifest describing the dynamically generated Artwork STL
            components while preserving their physical printer color
            identities.

        loop.stl
            Independently printable Loop component when Loop participates.
    """

    vector_manifest = context.input(
        "vector.manifest",
    )

    extrude_manifest = context.output(
        "manifest",
    )

    artwork_size = _positive_number(
        "artwork_size",
        context.resolver(
            "artwork_size",
        ),
    )

    artwork_raise = _positive_number(
        "artwork_raise",
        context.resolver(
            "artwork_raise",
        ),
    )

    loop_inner_diameter = float(
        context.resolver(
            "loop_inner_diameter",
        )
    )

    if not vector_manifest.is_file():
        raise ExtrudeError(f"Vector product manifest does not exist: {vector_manifest}")

    extrude_manifest.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    try:
        vector_products = _load_vector_manifest(
            vector_manifest,
        )

        envelope_bounds = _envelope_bounds(
            vector_products.envelope,
        )

        outputs: list[
            tuple[
                VectorLayer,
                Path,
            ]
        ] = []

        for layer in vector_products.layers:
            output = extrude_manifest.parent / f"color-{layer.index}.stl"

            source = _build_scad(
                layer.path,
                registered_extent=vector_products.registered_extent,
                envelope_bounds=envelope_bounds,
                artwork_size=artwork_size,
                artwork_raise=artwork_raise,
            )

            render_stl_source(
                source,
                output,
            )

            if not output.is_file():
                raise ExtrudeError(
                    f"OpenSCAD completed without creating the expected STL: {output}"
                )

            outputs.append(
                (
                    layer,
                    output,
                )
            )

        loop_product: tuple[Path, str] | None = None

        if loop_inner_diameter > 0.0:
            loop_width = _positive_number(
                "loop_width",
                context.resolver(
                    "loop_width",
                ),
            )

            loop_position = int(
                context.resolver(
                    "loop_position",
                )
            )

            loop_raise = _positive_number(
                "loop_raise",
                context.resolver(
                    "loop_raise",
                ),
            )

            physical_envelope_bounds = _physical_envelope_bounds(
                envelope_bounds,
                artwork_size=artwork_size,
            )

            loop_geometry = create_loop_geometry(
                envelope_bounds=physical_envelope_bounds,
                inner_diameter=loop_inner_diameter,
                width=loop_width,
                position=loop_position,
            )

            loop_output = extrude_manifest.parent / "loop.stl"

            loop_source = _build_loop_scad(
                loop_geometry,
                loop_raise=loop_raise,
            )

            render_stl_source(
                loop_source,
                loop_output,
            )

            if not loop_output.is_file():
                raise ExtrudeError(
                    f"OpenSCAD completed without creating the expected Loop STL: {loop_output}"
                )

            loop_color = resolve_loop_color(
                vector_products,
                resolver=context.resolver,
            )

            loop_product = (
                loop_output,
                loop_color,
            )

        _write_manifest(
            extrude_manifest,
            outputs,
            artwork_raise=artwork_raise,
            loop_product=loop_product,
        )

    except ExtrudeError:
        raise

    except OpenSCADError as exc:
        raise ExtrudeError(f"Could not extrude artwork from {vector_manifest}: {exc}") from exc

    except (
        OSError,
        ValueError,
        TypeError,
        KeyError,
        json.JSONDecodeError,
    ) as exc:
        raise ExtrudeError(
            f"Could not process vector artwork manifest {vector_manifest}: {exc}"
        ) from exc


# =========================================================
# Validation
# =========================================================


def _positive_number(
    name: str,
    value: Any,
) -> float:
    """
    Return a validated positive number.
    """

    if isinstance(
        value,
        bool,
    ):
        raise ExtrudeError(f"{name} must be greater than zero.")

    try:
        result = float(value)

    except (
        TypeError,
        ValueError,
    ) as exc:
        raise ExtrudeError(f"{name} must be numeric.") from exc

    if result <= 0:
        raise ExtrudeError(f"{name} must be greater than zero.")

    return result


def _positive_integer(
    name: str,
    value: Any,
) -> int:
    """
    Return a validated positive integer.
    """

    if (
        isinstance(
            value,
            bool,
        )
        or not isinstance(
            value,
            int,
        )
        or value < 1
    ):
        raise ExtrudeError(f"{name} must be a positive integer.")

    return value


def _color_component(
    color: dict[str, Any],
    name: str,
    index: int,
) -> int:
    """
    Return one validated RGB component.
    """

    value = color.get(name)

    if (
        isinstance(
            value,
            bool,
        )
        or not isinstance(
            value,
            int,
        )
        or value < 0
        or value > 255
    ):
        raise ExtrudeError(f"Vector product {index} has invalid {name} color component.")

    return value


# =========================================================
# Vector manifest
# =========================================================


def _load_vector_manifest(
    manifest: Path,
) -> VectorManifest:
    """
    Load registered vector products from the vector manifest.

    registered_extent describes the common square coordinate system
    shared by the registered envelope and every vector layer.

    envelope identifies the registered occupied Artwork envelope used
    by standalone extrusion for physical sizing and centering.

    Artifact color identity and RGB remain distinct from the physical
    printer identity and RGB assigned during rasterization.
    """

    try:
        data = json.loads(
            manifest.read_text(
                encoding="utf-8",
            )
        )

    except (
        OSError,
        json.JSONDecodeError,
    ) as exc:
        raise ExtrudeError(f"Could not read vector manifest: {manifest}") from exc

    registered_extent = _positive_integer(
        "Vector manifest registered extent",
        data.get(
            "registered_extent",
        ),
    )

    envelope_filename = data.get(
        "envelope",
    )

    if (
        not isinstance(
            envelope_filename,
            str,
        )
        or not envelope_filename
    ):
        raise ExtrudeError("Vector manifest does not contain a valid envelope path.")

    envelope = manifest.parent / envelope_filename

    if not envelope.is_file():
        raise ExtrudeError(f"Vector envelope does not exist: {envelope}")

    if envelope.suffix.lower() != ".svg":
        raise ExtrudeError(f"Vector envelope must be an SVG file: {envelope}")

    products = data.get(
        "products",
    )

    if not isinstance(
        products,
        list,
    ):
        raise ExtrudeError("Vector manifest does not contain a products list.")

    if not products:
        raise ExtrudeError("Vector manifest contains no vector products.")

    result: list[VectorLayer] = []

    for product in products:
        if not isinstance(
            product,
            dict,
        ):
            raise ExtrudeError("Vector manifest contains an invalid product.")

        index = product.get(
            "index",
        )

        filename = product.get(
            "path",
        )

        artifact_color_data = product.get(
            "artifact_color",
        )

        printer_color_data = product.get(
            "printer_color",
        )

        distance = product.get(
            "distance",
        )

        if (
            isinstance(
                index,
                bool,
            )
            or not isinstance(
                index,
                int,
            )
            or index < 1
        ):
            raise ExtrudeError("Vector product index must be a positive integer.")

        if (
            not isinstance(
                filename,
                str,
            )
            or not filename
        ):
            raise ExtrudeError(f"Vector product {index} has no valid path.")

        if not isinstance(
            artifact_color_data,
            dict,
        ):
            raise ExtrudeError(f"Vector product {index} has no valid Artifact color.")

        artifact_color_index = artifact_color_data.get(
            "index",
        )

        artifact_rgb_data = artifact_color_data.get(
            "rgb",
        )

        if (
            isinstance(
                artifact_color_index,
                bool,
            )
            or not isinstance(
                artifact_color_index,
                int,
            )
            or artifact_color_index < 1
        ):
            raise ExtrudeError(f"Vector product {index} has no valid Artifact color index.")

        if not isinstance(
            artifact_rgb_data,
            dict,
        ):
            raise ExtrudeError(f"Vector product {index} has no valid Artifact RGB.")

        artifact_color = (
            _color_component(
                artifact_rgb_data,
                "red",
                index,
            ),
            _color_component(
                artifact_rgb_data,
                "green",
                index,
            ),
            _color_component(
                artifact_rgb_data,
                "blue",
                index,
            ),
        )

        if not isinstance(
            printer_color_data,
            dict,
        ):
            raise ExtrudeError(f"Vector product {index} has no valid printer color.")

        printer_color_name = printer_color_data.get(
            "name",
        )

        printer_rgb_data = printer_color_data.get(
            "rgb",
        )

        if (
            not isinstance(
                printer_color_name,
                str,
            )
            or not printer_color_name.strip()
        ):
            raise ExtrudeError(f"Vector product {index} has no valid printer color name.")

        printer_color_name = printer_color_name.strip()

        if not isinstance(
            printer_rgb_data,
            dict,
        ):
            raise ExtrudeError(f"Vector product {index} has no valid printer RGB.")

        printer_color = (
            _color_component(
                printer_rgb_data,
                "red",
                index,
            ),
            _color_component(
                printer_rgb_data,
                "green",
                index,
            ),
            _color_component(
                printer_rgb_data,
                "blue",
                index,
            ),
        )

        if (
            isinstance(
                distance,
                bool,
            )
            or not isinstance(
                distance,
                int | float,
            )
            or distance < 0
        ):
            raise ExtrudeError(f"Vector product {index} has no valid assignment distance.")

        path = manifest.parent / filename

        if not path.is_file():
            raise ExtrudeError(f"Vector product does not exist: {path}")

        if path.suffix.lower() != ".svg":
            raise ExtrudeError(f"Vector product must be an SVG file: {path}")

        result.append(
            VectorLayer(
                index=index,
                path=path,
                artifact_color_index=artifact_color_index,
                artifact_color=artifact_color,
                printer_color_name=printer_color_name,
                printer_color=printer_color,
                distance=float(distance),
            )
        )

    indexes = [layer.index for layer in result]

    if len(indexes) != len(set(indexes)):
        raise ExtrudeError("Vector product indexes must be unique.")

    artifact_color_indexes = [layer.artifact_color_index for layer in result]

    if len(artifact_color_indexes) != len(set(artifact_color_indexes)):
        raise ExtrudeError("Artifact color indexes must be unique.")

    printer_color_names = [layer.printer_color_name for layer in result]

    if len(printer_color_names) != len(set(printer_color_names)):
        raise ExtrudeError("Vector product printer color names must be unique.")

    result.sort(
        key=lambda layer: layer.index,
    )

    return VectorManifest(
        registered_extent=registered_extent,
        envelope=envelope,
        layers=tuple(result),
    )


def _envelope_bounds(
    envelope: Path,
) -> tuple[
    float,
    float,
    float,
    float,
]:
    """
    Return the occupied bounds of a registered Artwork envelope.

    The result is:

        min_x, min_y, max_x, max_y

    Bounds are taken across all geometry in the registered envelope,
    rather than from the SVG page or registered coordinate extent.
    """

    try:
        objects = query_all(
            envelope,
            millimeters=False,
        )

    except InkscapeError as exc:
        raise ExtrudeError(
            f"Could not determine registered Artwork envelope bounds: {envelope}"
        ) from exc

    if not objects:
        raise ExtrudeError(f"Registered Artwork envelope contains no geometry: {envelope}")

    min_x = min(bounds["x"] for bounds in objects.values())

    min_y = min(bounds["y"] for bounds in objects.values())

    max_x = max(bounds["x"] + bounds["width"] for bounds in objects.values())

    max_y = max(bounds["y"] + bounds["height"] for bounds in objects.values())

    if max_x <= min_x or max_y <= min_y:
        raise ExtrudeError(f"Registered Artwork envelope has invalid bounds: {envelope}")

    return (
        min_x,
        min_y,
        max_x,
        max_y,
    )


def _physical_envelope_bounds(
    envelope_bounds: tuple[
        float,
        float,
        float,
        float,
    ],
    *,
    artwork_size: float,
) -> Bounds:
    """
    Return the dimensionalized Artwork envelope bounds in physical space.

    Standalone Artwork uniformly scales its occupied registered envelope so
    that the maximum X/Y extent equals artwork_size and centers that envelope
    about the physical origin.

    The resulting Bounds use the same physical coordinate system consumed by
    Artwork Loop geometry.
    """

    (
        min_x,
        min_y,
        max_x,
        max_y,
    ) = envelope_bounds

    envelope_width = max_x - min_x
    envelope_height = max_y - min_y

    envelope_extent = max(
        envelope_width,
        envelope_height,
    )

    if envelope_extent <= 0.0:
        raise ExtrudeError("Artwork envelope extent must be greater than zero.")

    scale = artwork_size / envelope_extent

    physical_width = envelope_width * scale
    physical_height = envelope_height * scale

    return Bounds(
        min_x=-physical_width / 2.0,
        min_y=-physical_height / 2.0,
        max_x=physical_width / 2.0,
        max_y=physical_height / 2.0,
    )


# =========================================================
# OpenSCAD source
# =========================================================


def _scad_number(
    value: float,
) -> str:
    """
    Format a number for generated OpenSCAD source.
    """

    if value.is_integer():
        return str(int(value))

    return format(
        value,
        ".12g",
    )


def _scad_string(
    value: str,
) -> str:
    """
    Quote a string for generated OpenSCAD source.
    """

    escaped = value.replace(
        "\\",
        "\\\\",
    ).replace(
        '"',
        '\\"',
    )

    return f'"{escaped}"'


def _build_loop_scad(
    geometry: LoopGeometry,
    *,
    loop_raise: float,
) -> str:
    """
    Return OpenSCAD source for one physical Artwork Loop.

    LoopGeometry owns the Artwork-specific planar geometry and placement.
    This function translates that resolved physical geometry into an
    extruded printable solid.
    """

    loop_center_x = _scad_number(
        geometry.center_x,
    )

    loop_center_y = _scad_number(
        geometry.center_y,
    )

    loop_inner_radius = _scad_number(
        geometry.inner_radius,
    )

    loop_outer_radius = _scad_number(
        geometry.outer_radius,
    )

    loop_raise_scad = _scad_number(
        loop_raise,
    )

    return f"""//
// Generated Artwork Loop.
//
// DO NOT EDIT THIS FILE.
//

loop_center_x = {loop_center_x};
loop_center_y = {loop_center_y};

loop_inner_radius = {loop_inner_radius};
loop_outer_radius = {loop_outer_radius};

loop_raise = {loop_raise_scad};


// ---------------------------------------------------------
// Loop solid
// ---------------------------------------------------------

translate(
    [
        loop_center_x,
        loop_center_y,
        0
    ]
)
    linear_extrude(
        height = loop_raise,
        convexity = 10
    )
        difference()
        {{
            circle(
                r = loop_outer_radius,
                $fn = 128
            );

            circle(
                r = loop_inner_radius,
                $fn = 128
            );
        }}
"""


def _build_scad(
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
) -> str:
    """
    Return OpenSCAD source for one artwork color layer.

    All SVG color layers share one common registered coordinate system.
    Their individual geometry bounds intentionally differ and must not
    be fitted or centered independently.

    The occupied Artwork envelope determines standalone physical size.
    One common uniform scale and translation are applied to every color
    layer so that the maximum physical X/Y extent of the envelope equals
    artwork_size while preserving registration between layers.

    Registered Artwork uses SVG coordinates, where positive Y points
    downward. OpenSCAD SVG import presents that geometry in an
    upward-positive coordinate system. The occupied envelope Y center is
    therefore converted into OpenSCAD coordinates before centering.

    SVG import uses a fixed DPI only to establish the SVG coordinate-unit
    convention. Physical Artwork size remains determined by artwork_size
    and the occupied registered envelope.
    """

    svg = svg.resolve()

    if not svg.is_file():
        raise ExtrudeError(f"Artwork SVG does not exist: {svg}")

    registered_extent = _positive_integer(
        "registered_extent",
        registered_extent,
    )

    (
        min_x,
        min_y,
        max_x,
        max_y,
    ) = envelope_bounds

    envelope_width = max_x - min_x
    envelope_height = max_y - min_y

    envelope_extent = max(
        envelope_width,
        envelope_height,
    )

    if envelope_extent <= 0:
        raise ExtrudeError("Artwork envelope extent must be greater than zero.")

    envelope_center_x = (min_x + max_x) / 2

    envelope_center_y = (min_y + max_y) / 2

    envelope_openscad_center_y = registered_extent - envelope_center_y

    registered_extent_scad = str(
        registered_extent,
    )

    envelope_width_scad = _scad_number(
        envelope_width,
    )

    envelope_height_scad = _scad_number(
        envelope_height,
    )

    envelope_extent_scad = _scad_number(
        envelope_extent,
    )

    envelope_center_x_scad = _scad_number(
        envelope_center_x,
    )

    envelope_openscad_center_y_scad = _scad_number(
        envelope_openscad_center_y,
    )

    artwork_size_scad = _scad_number(
        artwork_size,
    )

    artwork_raise_scad = _scad_number(
        artwork_raise,
    )

    artwork_svg = _scad_string(
        str(svg),
    )

    return f"""//
// Generated artwork color layer.
//
// DO NOT EDIT THIS FILE.
//

registered_extent = {registered_extent_scad};

envelope_width = {envelope_width_scad};
envelope_height = {envelope_height_scad};
envelope_extent = {envelope_extent_scad};
envelope_center_x = {envelope_center_x_scad};
envelope_openscad_center_y = {envelope_openscad_center_y_scad};

artwork_size = {artwork_size_scad};
artwork_raise = {artwork_raise_scad};

artwork_svg = {artwork_svg};


// ---------------------------------------------------------
// Artwork solid
// ---------------------------------------------------------

scale(
    [
        artwork_size / envelope_extent,
        artwork_size / envelope_extent,
        1
    ]
)
    translate(
        [
            -envelope_center_x,
            -envelope_openscad_center_y,
            0
        ]
    )
        linear_extrude(
            height = artwork_raise,
            convexity = 10
        )
            import(
                artwork_svg,
                center = false,
                dpi = 25.4
            );
"""


# =========================================================
# Extrusion manifest
# =========================================================


def _write_manifest(
    path: Path,
    layers: list[
        tuple[
            VectorLayer,
            Path,
        ]
    ],
    *,
    artwork_raise: float,
    loop_product: tuple[Path, str] | None = None,
) -> None:
    """
    Write the extrusion product manifest.

    Registered Artwork products preserve their Artifact color information
    and physical printer assignments unchanged.

    A participating Loop is recorded as an independently printable physical
    component with its resolved semantic printer color identity. The Loop is
    not Registered Artwork and therefore does not acquire synthetic Artifact
    color or color-assignment metadata.
    """

    products = [
        {
            "index": vector.index,
            "path": stl.name,
            "artifact_color": {
                "index": vector.artifact_color_index,
                "rgb": {
                    "red": vector.artifact_color[0],
                    "green": vector.artifact_color[1],
                    "blue": vector.artifact_color[2],
                },
            },
            "printer_color": {
                "name": vector.printer_color_name,
                "rgb": {
                    "red": vector.printer_color[0],
                    "green": vector.printer_color[1],
                    "blue": vector.printer_color[2],
                },
            },
            "distance": vector.distance,
        }
        for vector, stl in layers
    ]

    if loop_product is not None:
        loop_stl, loop_color = loop_product

        products.append(
            {
                "path": loop_stl.name,
                "printer_color": {
                    "name": loop_color,
                },
            }
        )

    data = {
        "artwork_raise": artwork_raise,
        "products": products,
    }

    path.write_text(
        json.dumps(
            data,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


__all__ = [
    "ExtrudeError",
    "execute",
]
