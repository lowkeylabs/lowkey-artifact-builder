"""
Artwork extrusion stage.

The extrusion stage converts registered vector color layers into
independently printable STL components.

Each vector layer is imported into OpenSCAD, centered about the origin,
and linearly extruded from Z=0 through the configured artwork raise.

The vector manifest identifies the dynamically generated vector layers
that participate in this stage. The generated STL components are
dynamic products whose filenames, geometry associations, semantic color
names, and color assignments are recorded in the declared extrusion
manifest.

Filesystem layout, dependency resolution, and configuration resolution
are responsibilities of the build engine. This implementation consumes
only the paths and values supplied through StageContext.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from lowkey_artifact_builder.engine import (
    StageContext,
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
    One vector layer described by the vector manifest.

    name preserves the semantic artwork color assigned by the raster
    stage and propagated by the vector stage.
    """

    index: int

    path: Path

    name: str

    color: tuple[
        int,
        int,
        int,
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
            Manifest describing the registered vector color layers
            produced by the vector stage.

        artwork_colors
            Resolved artwork palette.

        artwork_raise
            Physical extrusion height of the artwork geometry in
            millimeters.

    The stage produces:

        manifest
            Manifest describing the dynamically generated STL
            components and their semantic artwork color assignments.
    """

    vector_manifest = context.input(
        "vector.manifest",
    )

    extrude_manifest = context.output(
        "manifest",
    )

    artwork_colors = context.resolver(
        "artwork_colors",
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

    if not artwork_colors:
        raise ExtrudeError("Artwork palette is empty.")

    extrude_manifest.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    try:
        layers = _load_vector_manifest(vector_manifest)

        outputs: list[
            tuple[
                VectorLayer,
                Path,
            ]
        ] = []

        for layer in layers:
            output = extrude_manifest.parent / f"color-{layer.index}.stl"

            source = _build_scad(
                layer.path,
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
) -> list[VectorLayer]:
    """
    Load vector products from the vector manifest.

    Semantic color names assigned by the raster stage are required and
    preserved together with their configured RGB representations.
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

    products = data.get("products")

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

        index = product.get("index")

        filename = product.get("path")

        name = product.get("name")

        color_data = product.get("color")

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

        if (
            not isinstance(
                name,
                str,
            )
            or not name.strip()
        ):
            raise ExtrudeError(f"Vector product {index} has no valid color name.")

        name = name.strip()

        if not isinstance(
            color_data,
            dict,
        ):
            raise ExtrudeError(f"Vector product {index} has no valid color.")

        color = (
            _color_component(
                color_data,
                "red",
                index,
            ),
            _color_component(
                color_data,
                "green",
                index,
            ),
            _color_component(
                color_data,
                "blue",
                index,
            ),
        )

        path = manifest.parent / filename

        if not path.is_file():
            raise ExtrudeError(f"Vector product does not exist: {path}")

        if path.suffix.lower() != ".svg":
            raise ExtrudeError(f"Vector product must be an SVG file: {path}")

        result.append(
            VectorLayer(
                index=index,
                path=path,
                name=name,
                color=color,
            )
        )

    indexes = [layer.index for layer in result]

    if len(indexes) != len(set(indexes)):
        raise ExtrudeError("Vector product indexes must be unique.")

    names = [layer.name for layer in result]

    if len(names) != len(set(names)):
        raise ExtrudeError("Vector product color names must be unique.")

    result.sort(key=lambda layer: layer.index)

    return result


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
    artwork_size: float,
    artwork_raise: float,
) -> str:
    """
    Return OpenSCAD source for one artwork color layer.

    All SVG color layers share one common document coordinate system.
    Their individual geometry bounds intentionally differ and must not
    be centered independently.

    The SVG is therefore imported without OpenSCAD centering. The
    complete artwork coordinate system is translated by half the
    configured physical artwork size so that the common SVG canvas is
    centered at the model origin.

    This identical translation is applied to every color layer,
    preserving registration between layers.
    """

    svg = svg.resolve()

    if not svg.is_file():
        raise ExtrudeError(f"Artwork SVG does not exist: {svg}")

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

artwork_size = {artwork_size_scad};
artwork_raise = {artwork_raise_scad};

artwork_svg = {artwork_svg};


// ---------------------------------------------------------
// Artwork solid
// ---------------------------------------------------------

translate(
    [
        -artwork_size / 2,
        -artwork_size / 2,
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

    Semantic artwork color names and their configured RGB
    representations are propagated unchanged from the vector stage.
    """

    products = [
        {
            "index": vector.index,
            "path": stl.name,
            "name": vector.name,
            "color": {
                "red": vector.color[0],
                "green": vector.color[1],
                "blue": vector.color[2],
            },
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
