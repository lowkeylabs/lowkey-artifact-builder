"""
Artwork raster stage.

The raster stage converts the stacked multicolor SVG trace into
registered, mutually exclusive raster color layers.

Each traced SVG object is rendered independently through one common
square export region. The original embedded raster image supplies the
artwork footprint. Visible regions are then calculated in pixel space
so no SVG Boolean operations are required.

Each traced color is assigned one-to-one to the configured artwork
palette using perceptual color matching. The resulting semantic color
identity is recorded in the stage manifest for consumption by later
stages.

Small disconnected islands are removed using a raster pixel-area threshold.
"""
# File: src/lowkey_artifact_builder/model/models/artwork/stages/raster.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
import tempfile
import xml.etree.ElementTree as ET
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image

from lowkey_artifact_builder.colors import (
    ColorAssignment,
    ColorError,
    MeasuredColor,
    assign_colors,
    resolve_palette,
)
from lowkey_artifact_builder.engine import (
    StageContext,
)
from lowkey_artifact_builder.formats.svg import (
    SVG_NS,
    SVGError,
    get_fill_rgb,
    get_trace_objects,
    load,
    remove_object,
    require_ids,
    save,
)
from lowkey_artifact_builder.tools.inkscape import (
    InkscapeError,
    run,
)

# =========================================================
# Errors
# =========================================================


class RasterError(RuntimeError):
    """
    Raised when artwork rasterization cannot be completed.
    """


# =========================================================
# Specifications
# =========================================================


@dataclass(
    frozen=True,
    slots=True,
)
class ObjectBounds:
    """
    Bounding box for one SVG object.
    """

    x: float

    y: float

    width: float

    height: float

    @property
    def x2(
        self,
    ) -> float:
        """
        Return the right edge.
        """

        return self.x + self.width

    @property
    def y2(
        self,
    ) -> float:
        """
        Return the bottom edge.
        """

        return self.y + self.height


@dataclass(
    frozen=True,
    slots=True,
)
class RasterBounds:
    """
    Square SVG export bounds.
    """

    x: float

    y: float

    size: float

    @property
    def x2(
        self,
    ) -> float:
        """
        Return the right edge.
        """

        return self.x + self.size

    @property
    def y2(
        self,
    ) -> float:
        """
        Return the bottom edge.
        """

        return self.y + self.size


# =========================================================
# Public interface
# =========================================================


def execute(
    context: StageContext,
) -> None:
    """
    Execute the artwork raster stage.

    Inputs:

        prepare.trace
            Multicolor SVG trace produced by prepare.

    Parameters:

        artwork_colors
            Ordered semantic color names available to the artwork.

        artwork_pixels
            Width and height of every registered raster layer.

        artwork_min_island_area
            Minimum disconnected island area in square pixels.

        artwork_island_connectivity
            Pixel connectivity used for island detection.

    Outputs:

        manifest
            JSON manifest describing generated raster layers,
            semantic color assignments, measured trace colors, and
            perceptual assignment distances.
    """

    trace = context.input(
        "prepare.trace",
    )

    manifest = context.output(
        "manifest",
    )

    artwork_colors = _color_names(
        context.resolver(
            "artwork_colors",
        )
    )

    pixels = _positive_integer(
        "artwork_pixels",
        context.resolver(
            "artwork_pixels",
        ),
    )

    minimum_area = _positive_integer(
        "artwork_min_island_area",
        context.resolver(
            "artwork_min_island_area",
        ),
    )

    connectivity = _connectivity(
        context.resolver(
            "artwork_island_connectivity",
        )
    )

    if not trace.is_file():
        raise RasterError(f"Artwork trace does not exist: {trace}")

    manifest.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    try:
        palette = resolve_palette(
            artwork_colors,
            context.resolver.colors,
        )

        tree = load(trace)

        objects = get_trace_objects(tree)

        if len(objects) != len(palette):
            raise RasterError(
                "Unexpected number of traced color objects. "
                f"Requested {len(palette)}, found {len(objects)}."
            )

        trace_colors = tuple(
            get_fill_rgb(
                tree,
                object_id,
            )
            for object_id in objects
        )

        measured_colors = tuple(
            MeasuredColor(
                index=index,
                rgb=color,
            )
            for index, color in enumerate(
                trace_colors,
                start=1,
            )
        )

        assignments = assign_colors(
            measured_colors,
            palette,
        )

        bounds = _square_bounds(
            trace,
            objects,
        )

        layers = _render_layers(
            trace,
            objects,
            tuple(assignment.color.rgb for assignment in assignments),
            directory=manifest.parent,
            bounds=bounds,
            pixels=pixels,
        )

        _cleanup_layers(
            layers,
            minimum_area=minimum_area,
            connectivity=connectivity,
        )

        _write_manifest(
            manifest,
            layers,
            assignments,
            pixels=pixels,
        )

    except (
        ColorError,
        SVGError,
        InkscapeError,
        OSError,
    ) as exc:
        raise RasterError(f"Could not rasterize artwork trace {trace}: {exc}") from exc


# =========================================================
# Parameter validation
# =========================================================


def _color_names(
    value: Any,
) -> tuple[str, ...]:
    """
    Return a validated sequence of artwork color names.
    """

    if isinstance(
        value,
        str | bytes,
    ):
        raise RasterError("artwork_colors must be a sequence of color names.")

    try:
        colors = tuple(value)

    except TypeError as exc:
        raise RasterError("artwork_colors must be a sequence of color names.") from exc

    if not colors:
        raise RasterError("artwork_colors must contain at least one color.")

    if not all(
        isinstance(
            color,
            str,
        )
        and bool(color.strip())
        for color in colors
    ):
        raise RasterError("artwork_colors must contain only non-empty color names.")

    return tuple(color.strip() for color in colors)


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
        raise RasterError(f"{name} must be a positive integer.")

    return value


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
        raise RasterError(f"{name} must be greater than zero.")

    try:
        result = float(value)

    except (
        TypeError,
        ValueError,
    ) as exc:
        raise RasterError(f"{name} must be numeric.") from exc

    if result <= 0:
        raise RasterError(f"{name} must be greater than zero.")

    return result


def _connectivity(
    value: Any,
) -> int:
    """
    Validate island connectivity.
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
        or value
        not in (
            4,
            8,
        )
    ):
        raise RasterError("artwork_island_connectivity must be 4 or 8.")

    return value


# =========================================================
# Bounds
# =========================================================


def _query_bounds(
    source: Path,
) -> dict[str, ObjectBounds]:
    """
    Query SVG object bounds from Inkscape.
    """

    stdout = run(
        source,
        args=("--query-all",),
    )

    result: dict[
        str,
        ObjectBounds,
    ] = {}

    for line in stdout.splitlines():
        fields = line.split(",")

        if len(fields) != 5:
            continue

        object_id, x, y, width, height = fields

        try:
            result[object_id] = ObjectBounds(
                x=float(x),
                y=float(y),
                width=float(width),
                height=float(height),
            )

        except ValueError:
            continue

    return result


def _square_bounds(
    source: Path,
    objects: list[str],
) -> RasterBounds:
    """
    Return common square bounds enclosing all traced objects.
    """

    queried = _query_bounds(source)

    missing = [object_id for object_id in objects if object_id not in queried]

    if missing:
        raise RasterError("Could not determine bounds for SVG objects: " + ", ".join(missing))

    selected = [queried[object_id] for object_id in objects]

    min_x = min(item.x for item in selected)

    min_y = min(item.y for item in selected)

    max_x = max(item.x2 for item in selected)

    max_y = max(item.y2 for item in selected)

    width = max_x - min_x
    height = max_y - min_y

    if width <= 0 or height <= 0:
        raise RasterError("Artwork bounds must have positive dimensions.")

    size = max(
        width,
        height,
    )

    center_x = (min_x + max_x) / 2.0

    center_y = (min_y + max_y) / 2.0

    return RasterBounds(
        x=center_x - size / 2.0,
        y=center_y - size / 2.0,
        size=size,
    )


# =========================================================
# SVG isolation
# =========================================================


def _remove_raster_images(
    tree: ET.ElementTree[ET.Element[str]],
) -> None:
    """
    Remove embedded raster images from an SVG.
    """

    image_tag = f"{{{SVG_NS}}}image"

    root = tree.getroot()

    for parent in root.iter():
        for child in list(parent):
            if child.tag == image_tag:
                parent.remove(child)


def _build_object_svg(
    source: Path,
    output: Path,
    objects: list[str],
    target: str,
) -> None:
    """
    Create an SVG containing one traced object.
    """

    tree = load(source)

    require_ids(
        tree,
        objects,
    )

    _remove_raster_images(tree)

    for object_id in objects:
        if object_id != target:
            remove_object(
                tree,
                object_id,
            )

    save(
        tree,
        output,
    )


def _build_source_svg(
    source: Path,
    output: Path,
    objects: list[str],
) -> None:
    """
    Create an SVG containing only the original embedded raster.
    """

    tree = load(source)

    require_ids(
        tree,
        objects,
    )

    root = tree.getroot()

    image_tag = f"{{{SVG_NS}}}image"

    if not any(element.tag == image_tag for element in root.iter()):
        raise RasterError("Traced SVG does not contain the original raster image.")

    for object_id in objects:
        remove_object(
            tree,
            object_id,
        )

    save(
        tree,
        output,
    )


# =========================================================
# Rendering
# =========================================================


def _export_png(
    source: Path,
    output: Path,
    *,
    bounds: RasterBounds,
    pixels: int,
) -> None:
    """
    Render an SVG through common registered bounds.
    """

    output = output.resolve()

    export_area = f"{bounds.x}:{bounds.y}:{bounds.x2}:{bounds.y2}"

    run(
        source,
        actions=(
            "export-type:png",
            f"export-filename:{output}",
            f"export-area:{export_area}",
            f"export-width:{pixels}",
            f"export-height:{pixels}",
            "export-do",
        ),
    )

    if not output.is_file():
        raise RasterError(f"Inkscape did not create expected PNG: {output}")


def _threshold_alpha(
    value: int,
) -> int:
    """
    Convert an alpha value into binary occupancy.
    """

    return 255 if value >= 128 else 0


def _load_binary_mask(
    source: Path,
) -> Image.Image:
    """
    Load a rendered PNG alpha channel as binary occupancy.
    """

    with Image.open(source) as image:
        rgba = image.convert("RGBA")

    try:
        alpha = rgba.getchannel("A")

        try:
            return alpha.point(_threshold_alpha)

        finally:
            alpha.close()

    finally:
        rgba.close()


def _mask_and(
    a: int,
    b: int,
) -> int:
    """
    Return the intersection of two binary mask values.
    """

    return 255 if a and b else 0


def _mask_subtract(
    a: int,
    b: int,
) -> int:
    """
    Subtract the second binary mask value from the first.
    """

    return 255 if a and not b else 0


def _mask_or(
    a: int,
    b: int,
) -> int:
    """
    Return the union of two binary mask values.
    """

    return 255 if a or b else 0


def _binary_operation(
    first: Image.Image,
    second: Image.Image,
    operation: str,
) -> Image.Image:
    """
    Perform a logical operation on two binary masks.
    """

    if first.size != second.size:
        raise RasterError("Raster masks must have identical dimensions.")

    function: Callable[
        [int, int],
        int,
    ]

    if operation == "and":
        function = _mask_and

    elif operation == "subtract":
        function = _mask_subtract

    elif operation == "or":
        function = _mask_or

    else:
        raise RasterError(f"Unsupported mask operation: {operation}")

    return Image.frombytes(
        "L",
        first.size,
        bytes(
            function(
                a,
                b,
            )
            for a, b in zip(
                first.tobytes(),
                second.tobytes(),
                strict=True,
            )
        ),
    )


def _save_mask(
    mask: Image.Image,
    output: Path,
    color: tuple[int, int, int],
) -> None:
    """
    Save binary geometry using the supplied RGB color.
    """

    image = Image.new(
        "RGBA",
        mask.size,
        (
            color[0],
            color[1],
            color[2],
            0,
        ),
    )

    try:
        image.putalpha(mask)

        image.save(
            output,
            format="PNG",
        )

    finally:
        image.close()


def _render_layers(
    source: Path,
    objects: list[str],
    colors: tuple[
        tuple[int, int, int],
        ...,
    ],
    *,
    directory: Path,
    bounds: RasterBounds,
    pixels: int,
) -> list[Path]:
    """
    Render mutually exclusive registered color layers.

    The supplied colors are the assigned configured palette colors,
    not the measured trace colors.
    """

    outputs: list[Path] = []

    with tempfile.TemporaryDirectory() as temporary:
        temp = Path(temporary)

        source_svg = temp / "source.svg"

        source_png = temp / "source.png"

        _build_source_svg(
            source,
            source_svg,
            objects,
        )

        _export_png(
            source_svg,
            source_png,
            bounds=bounds,
            pixels=pixels,
        )

        artwork_mask = _load_binary_mask(source_png)

        covered = Image.new(
            "L",
            (
                pixels,
                pixels,
            ),
            0,
        )

        try:
            for index, (
                object_id,
                color,
            ) in enumerate(
                zip(
                    objects,
                    colors,
                    strict=True,
                ),
                start=1,
            ):
                isolated_svg = temp / f"object-{index}.svg"

                isolated_png = temp / f"object-{index}.png"

                _build_object_svg(
                    source,
                    isolated_svg,
                    objects,
                    object_id,
                )

                _export_png(
                    isolated_svg,
                    isolated_png,
                    bounds=bounds,
                    pixels=pixels,
                )

                mask = _load_binary_mask(isolated_png)

                try:
                    clipped = _binary_operation(
                        mask,
                        artwork_mask,
                        "and",
                    )

                    try:
                        visible = _binary_operation(
                            clipped,
                            covered,
                            "subtract",
                        )

                        try:
                            output = directory / f"color-{index}.png"

                            _save_mask(
                                visible,
                                output,
                                color,
                            )

                            outputs.append(output)

                        finally:
                            visible.close()

                        combined = _binary_operation(
                            covered,
                            clipped,
                            "or",
                        )

                        covered.close()

                        covered = combined

                    finally:
                        clipped.close()

                finally:
                    mask.close()

        finally:
            covered.close()
            artwork_mask.close()

    return outputs


# =========================================================
# Island cleanup
# =========================================================


def _remove_small_islands(
    alpha: Image.Image,
    *,
    minimum_pixels: int,
    connectivity: int,
) -> Image.Image:
    """
    Remove disconnected foreground islands below a pixel threshold.
    """

    width, height = alpha.size

    source = alpha.load()

    if source is None:
        raise RasterError("Could not access source mask pixels.")

    output = Image.new(
        "L",
        alpha.size,
        0,
    )

    destination = output.load()

    if destination is None:
        output.close()

        raise RasterError("Could not access destination mask pixels.")

    visited = bytearray(width * height)

    if connectivity == 4:
        neighbors = (
            (-1, 0),
            (1, 0),
            (0, -1),
            (0, 1),
        )

    else:
        neighbors = (
            (-1, -1),
            (0, -1),
            (1, -1),
            (-1, 0),
            (1, 0),
            (-1, 1),
            (0, 1),
            (1, 1),
        )

    for y in range(height):
        for x in range(width):
            offset = y * width + x

            if visited[offset]:
                continue

            visited[offset] = 1

            if source[x, y] == 0:
                continue

            component = [
                (
                    x,
                    y,
                )
            ]

            stack = [
                (
                    x,
                    y,
                )
            ]

            while stack:
                current_x, current_y = stack.pop()

                for dx, dy in neighbors:
                    next_x = current_x + dx
                    next_y = current_y + dy

                    if next_x < 0 or next_x >= width or next_y < 0 or next_y >= height:
                        continue

                    next_offset = next_y * width + next_x

                    if visited[next_offset]:
                        continue

                    visited[next_offset] = 1

                    if (
                        source[
                            next_x,
                            next_y,
                        ]
                        == 0
                    ):
                        continue

                    point = (
                        next_x,
                        next_y,
                    )

                    component.append(point)

                    stack.append(point)

            if len(component) < minimum_pixels:
                continue

            for point_x, point_y in component:
                destination[
                    point_x,
                    point_y,
                ] = 255

    return output


def _cleanup_layers(
    layers: list[Path],
    *,
    minimum_area: int,
    connectivity: int,
) -> None:
    """
    Remove raster islands below the configured pixel-area threshold.
    """

    if not layers:
        raise RasterError("No raster layers were generated.")

    with Image.open(layers[0]) as first:
        width, height = first.size

    if width != height:
        raise RasterError("Raster color layers must be square.")

    for path in layers:
        with Image.open(path) as image:
            rgba = image.convert("RGBA")

        try:
            if rgba.size != (
                width,
                height,
            ):
                raise RasterError("Raster color layers must have identical dimensions.")

            alpha = rgba.getchannel("A")

            try:
                cleaned = _remove_small_islands(
                    alpha,
                    minimum_pixels=minimum_area,
                    connectivity=connectivity,
                )

                try:
                    rgba.putalpha(cleaned)

                    rgba.save(
                        path,
                        format="PNG",
                    )

                finally:
                    cleaned.close()

            finally:
                alpha.close()

        finally:
            rgba.close()


# =========================================================
# Manifest
# =========================================================


def _write_manifest(
    path: Path,
    layers: list[Path],
    assignments: tuple[
        ColorAssignment,
        ...,
    ],
    *,
    pixels: int,
) -> None:
    """
    Write the raster product manifest.

    Each product records:

        name
            Semantic configured artwork color.

        color
            Configured RGB representation of that semantic color.

        trace_color
            RGB value measured from the corresponding Inkscape trace
            object.

        distance
            Perceptual distance between the measured trace color and
            the assigned configured color.
    """

    products = [
        {
            "index": index,
            "path": layer.name,
            "name": assignment.color.name,
            "color": {
                "red": assignment.color.rgb[0],
                "green": assignment.color.rgb[1],
                "blue": assignment.color.rgb[2],
            },
            "trace_color": {
                "red": assignment.measured.rgb[0],
                "green": assignment.measured.rgb[1],
                "blue": assignment.measured.rgb[2],
            },
            "distance": assignment.distance,
        }
        for index, (
            layer,
            assignment,
        ) in enumerate(
            zip(
                layers,
                assignments,
                strict=True,
            ),
            start=1,
        )
    ]

    data = {
        "pixels": pixels,
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
    "RasterError",
    "execute",
]
