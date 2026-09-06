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
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from lowkey_artifact_builder.engine import (
    StageContext,
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
# Specifications
# =========================================================


@dataclass(
    frozen=True,
    slots=True,
)
class VectorLayer:
    """
    One registered vector color layer.

    Artifact color identity and RGB describe the color discovered from
    the Artwork. Printer color identity and RGB describe the physical
    assignment established during rasterization.
    """

    index: int

    path: Path

    artifact_color_index: int

    artifact_color: tuple[
        int,
        int,
        int,
    ]

    printer_color_name: str

    printer_color: tuple[
        int,
        int,
        int,
    ]

    distance: float


@dataclass(
    frozen=True,
    slots=True,
)
class VectorManifest:
    """
    Registered vector geometry consumed by the extrusion stage.

    registered_extent describes the common square coordinate system
    shared by the envelope and every vector layer.

    envelope identifies the registered occupied Artwork envelope used
    to dimensionalize standalone Artwork.
    """

    registered_extent: int

    envelope: Path

    layers: tuple[
        VectorLayer,
        ...,
    ]


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

    The stage produces:

        manifest
            Manifest describing the dynamically generated STL
            components while preserving Artifact color information and
            physical printer assignments from Registered Artwork.
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

        _write_manifest(
            extrude_manifest,
            outputs,
            artwork_raise=artwork_raise,
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

    envelope_center_y_scad = _scad_number(
        envelope_center_y,
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
envelope_center_y = {envelope_center_y_scad};

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
            -envelope_center_y,
            0
        ]
    )
        linear_extrude(
            height = artwork_raise,
            convexity = 10
        )
            import(
                artwork_svg,
                center = false
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
) -> None:
    """
    Write the extrusion product manifest.

    Artifact color information and physical printer assignments are
    propagated unchanged from Registered Artwork.
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
