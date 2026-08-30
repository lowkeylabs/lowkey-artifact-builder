"""
Artwork vector stage.

The vector stage converts registered raster color layers into
registered vector geometry without assigning physical manufacturing
dimensions.

The raster manifest identifies the dynamically generated raster layers
that participate in this stage. One common square crop is calculated
from the union of all raster layers and applied to every layer so that
registration is preserved.

Each cropped raster layer is traced by Inkscape. All resulting SVG
documents retain the common coordinate system established by the
registered raster crop.

The prepared Artwork envelope is registered into that same coordinate
system and published as part of Registered Artwork.

The vector manifest records the common registered coordinate extent and
the registered envelope so that downstream consumers can dimensionalize
and place the registered geometry without inspecting individual SVG
documents.

Physical dimensionalization is the responsibility of a downstream
consumer.

Filesystem layout, dependency resolution, and configuration resolution
are responsibilities of the build engine. This implementation consumes
only the paths and values supplied through StageContext.
"""
# File: src/lowkey_artifact_builder/model/models/artwork/stages/vector.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import (
    Image,
    ImageChops,
)

from lowkey_artifact_builder.engine import (
    StageContext,
)
from lowkey_artifact_builder.formats.svg import (
    SVG_NS,
    SVGError,
    load,
    save,
)
from lowkey_artifact_builder.logging_config import get_logger
from lowkey_artifact_builder.tools.inkscape import (
    InkscapeError,
    run,
)

logger = get_logger(__name__)

# =========================================================
# Constants
# =========================================================


DEFAULT_SPECKLES = 2

DEFAULT_SMOOTH_CORNERS = 1.0

DEFAULT_OPTIMIZE = 0.2


# =========================================================
# Errors
# =========================================================


class VectorError(RuntimeError):
    """
    Raised when artwork vector generation cannot be completed.
    """


# =========================================================
# Specifications
# =========================================================


@dataclass(
    frozen=True,
    slots=True,
)
class RasterLayer:
    """
    One raster layer described by the raster manifest.
    """

    index: int

    path: Path

    name: str

    color: tuple[
        int,
        int,
        int,
    ]


@dataclass(
    frozen=True,
    slots=True,
)
class RasterCrop:
    """
    Common square crop in source-raster coordinates.
    """

    x: int

    y: int

    size: int

    @property
    def box(
        self,
    ) -> tuple[
        int,
        int,
        int,
        int,
    ]:
        """
        Return the crop as a Pillow box.
        """

        return (
            self.x,
            self.y,
            self.x + self.size,
            self.y + self.size,
        )


# =========================================================
# Public interface
# =========================================================


def execute(
    context: StageContext,
) -> None:
    """
    Execute the artwork vector stage.

    The stage consumes:

        raster.manifest
            Manifest describing registered raster color layers.

        prepare.envelope
            Prepared Artwork envelope in source coordinates.

    The stage produces:

        manifest
            Manifest describing the reusable Registered Artwork,
            including its registered envelope and dynamically generated
            vector color layers.
    """

    raster_manifest = context.input(
        "raster.manifest",
    )

    prepared_envelope = context.input(
        "prepare.envelope",
    )

    vector_manifest = context.output(
        "manifest",
    )

    if not raster_manifest.is_file():
        raise VectorError(f"Raster product manifest does not exist: {raster_manifest}")

    if not prepared_envelope.is_file():
        raise VectorError(f"Prepared Artwork envelope does not exist: {prepared_envelope}")

    vector_manifest.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    try:
        layers = _load_raster_manifest(
            raster_manifest,
        )

        crop = _common_crop(
            layers,
        )

        registered_envelope = vector_manifest.parent / "envelope.svg"

        _register_envelope(
            prepared_envelope,
            registered_envelope,
            crop=crop,
        )

        vector_layers: list[
            tuple[
                RasterLayer,
                Path,
            ]
        ] = []

        for layer in layers:
            output = vector_manifest.parent / f"color-{layer.index}.svg"

            _trace_mask(
                layer.path,
                output,
                crop=crop,
            )

            vector_layers.append(
                (
                    layer,
                    output,
                )
            )

        _write_manifest(
            vector_manifest,
            vector_layers,
            registered_extent=crop.size,
            envelope=registered_envelope,
        )

    except (
        SVGError,
        InkscapeError,
        OSError,
        ValueError,
        TypeError,
        KeyError,
        json.JSONDecodeError,
    ) as exc:
        raise VectorError(
            f"Could not generate vector artwork from {raster_manifest}: {exc}"
        ) from exc


# =========================================================
# Raster manifest
# =========================================================


def _load_raster_manifest(
    manifest: Path,
) -> list[RasterLayer]:
    """
    Load raster products from the raster manifest.
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
        raise VectorError(f"Could not read raster manifest: {manifest}") from exc

    products = data.get(
        "products",
    )

    if not isinstance(
        products,
        list,
    ):
        raise VectorError("Raster manifest does not contain a products list.")

    if not products:
        raise VectorError("Raster manifest contains no raster products.")

    result: list[RasterLayer] = []

    for product in products:
        if not isinstance(
            product,
            dict,
        ):
            raise VectorError("Raster manifest contains an invalid product.")

        index = product.get(
            "index",
        )

        filename = product.get(
            "path",
        )

        name = product.get(
            "name",
        )

        color_data = product.get(
            "color",
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
            raise VectorError("Raster product index must be a positive integer.")

        if (
            not isinstance(
                filename,
                str,
            )
            or not filename
        ):
            raise VectorError(f"Raster product {index} has no valid path.")

        if (
            not isinstance(
                name,
                str,
            )
            or not name.strip()
        ):
            raise VectorError(f"Raster product {index} has no valid color name.")

        name = name.strip()

        if not isinstance(
            color_data,
            dict,
        ):
            raise VectorError(f"Raster product {index} has no valid color.")

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
            raise VectorError(f"Raster product does not exist: {path}")

        result.append(
            RasterLayer(
                index=index,
                path=path,
                name=name,
                color=color,
            )
        )

    indexes = [layer.index for layer in result]

    if len(indexes) != len(set(indexes)):
        raise VectorError("Raster product indexes must be unique.")

    names = [layer.name for layer in result]

    if len(names) != len(set(names)):
        raise VectorError("Raster product color names must be unique.")

    result.sort(
        key=lambda layer: layer.index,
    )

    return result


def _color_component(
    color: dict[str, Any],
    name: str,
    index: int,
) -> int:
    """
    Return one validated RGB component.
    """

    value = color.get(
        name,
    )

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
        raise VectorError(f"Raster product {index} has invalid {name} color component.")

    return value


# =========================================================
# Common artwork crop
# =========================================================


def _common_crop(
    layers: list[RasterLayer],
) -> RasterCrop:
    """
    Calculate one square crop containing the union of all layers.

    Every layer must have identical raster dimensions.
    """

    if not layers:
        raise VectorError("Cannot calculate artwork crop without raster layers.")

    union_alpha: Image.Image | None = None

    size: (
        tuple[
            int,
            int,
        ]
        | None
    ) = None

    try:
        for layer in layers:
            with Image.open(
                layer.path,
            ) as image:
                rgba = image.convert(
                    "RGBA",
                )

            try:
                if size is None:
                    size = rgba.size

                elif rgba.size != size:
                    raise VectorError("Raster color layers do not have identical dimensions.")

                alpha = rgba.getchannel(
                    "A",
                )

                try:
                    if union_alpha is None:
                        union_alpha = alpha.copy()

                    else:
                        combined = ImageChops.lighter(
                            union_alpha,
                            alpha,
                        )

                        union_alpha.close()

                        union_alpha = combined

                finally:
                    alpha.close()

            finally:
                rgba.close()

        if size is None or union_alpha is None:
            raise VectorError("Could not determine raster artwork bounds.")

        width, height = size

        bounds = union_alpha.getbbox()

        if bounds is None:
            raise VectorError("Raster artwork contains no visible geometry.")

        left, top, right, bottom = bounds

        artwork_width = right - left

        artwork_height = bottom - top

        if artwork_width <= 0 or artwork_height <= 0:
            raise VectorError("Raster artwork bounds must have positive dimensions.")

        crop_size = max(
            artwork_width,
            artwork_height,
        )

        if crop_size > width or crop_size > height:
            raise VectorError("Artwork cannot be enclosed by a square crop.")

        center_x = (left + right) / 2.0

        center_y = (top + bottom) / 2.0

        x = round(center_x - crop_size / 2.0)

        y = round(center_y - crop_size / 2.0)

        x = max(
            0,
            min(
                x,
                width - crop_size,
            ),
        )

        y = max(
            0,
            min(
                y,
                height - crop_size,
            ),
        )

        return RasterCrop(
            x=x,
            y=y,
            size=crop_size,
        )

    finally:
        if union_alpha is not None:
            union_alpha.close()


def _crop_raster(
    source: Path,
    output: Path,
    crop: RasterCrop,
) -> None:
    """
    Apply the common crop to one raster layer and convert the result
    into a hard opaque black-and-white tracing image.

    Raster-layer membership is defined exclusively by alpha:

        opaque pixel       -> black
        transparent pixel  -> white

    The resulting PNG is fully opaque. This prevents Inkscape from
    interpreting source RGB values, transparency, or antialiased
    boundary colors while tracing.

    All layers use the same crop, preserving registration.
    """

    with Image.open(
        source,
    ) as image:
        rgba = image.convert(
            "RGBA",
        )

    try:
        if (
            crop.x < 0
            or crop.y < 0
            or crop.x + crop.size > rgba.width
            or crop.y + crop.size > rgba.height
        ):
            raise VectorError("Raster crop lies outside the source image.")

        cropped = rgba.crop(
            crop.box,
        )

        try:
            alpha = cropped.getchannel(
                "A",
            )

            try:
                mask = alpha.point(
                    [255] + [0] * 255,
                    mode="1",
                )

                try:
                    tracing_image = mask.convert(
                        "L",
                    )

                    try:
                        tracing_image.save(
                            output,
                            format="PNG",
                        )

                    finally:
                        tracing_image.close()

                finally:
                    mask.close()

            finally:
                alpha.close()

        finally:
            cropped.close()

    finally:
        rgba.close()


# =========================================================
# Registered envelope
# =========================================================


def _register_envelope(
    source: Path,
    output: Path,
    *,
    crop: RasterCrop,
) -> None:
    """
    Register the prepared Artwork envelope with the vector coordinate system.

    The prepared envelope is expressed in source-image coordinates. Vector
    layers are generated from a common square crop of those same coordinates.

    Assigning the crop as the SVG viewBox makes the envelope use that same
    registered coordinate system without altering its geometry.
    """

    tree = load(
        source,
    )

    root = tree.getroot()

    root.set(
        "viewBox",
        " ".join(
            (
                str(crop.x),
                str(crop.y),
                str(crop.size),
                str(crop.size),
            )
        ),
    )

    root.set(
        "width",
        str(crop.size),
    )

    root.set(
        "height",
        str(crop.size),
    )

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    save(
        tree,
        output,
    )


# =========================================================
# Inkscape tracing
# =========================================================


def _trace_actions(
    *,
    speckles: int = 0,
    smooth_corners: float = 0.0,
    optimize: float = 0.0,
) -> tuple[str, ...]:
    """
    Return Inkscape actions for tracing a hard monochrome mask.

    The raster supplied to Inkscape is already categorical:

        black = geometry
        white = background

    Smoothing and optimization are disabled here because the raster
    stage has already established the authoritative color boundaries.

    Vectorization should reproduce those boundaries rather than
    independently reinterpret or simplify them.
    """

    parameters = ",".join(
        (
            "2",
            "false",
            "true",
            "true",
            str(speckles),
            str(smooth_corners),
            str(optimize),
        )
    )

    return (
        "select-all",
        f"object-trace:{parameters}",
    )


def _trace_mask(
    source: Path,
    output: Path,
    *,
    crop: RasterCrop,
) -> None:
    """
    Trace one categorical raster mask into registered vector geometry.

    The source mask is first cropped using the common artwork crop and
    converted into a fully opaque black-and-white tracing image.

    Raster alpha defines geometry:

        opaque source pixel       -> black
        transparent source pixel  -> white

    Inkscape therefore receives no source colors, transparency, or
    antialiased intermediate values.

    Inkscape traces the cropped raster in crop-local coordinates. The
    resulting vector geometry is then restored to the common Registered
    Artwork coordinate system established by the source-raster crop.
    """

    output = output.resolve()

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with tempfile.TemporaryDirectory() as directory:
        temporary = Path(
            directory,
        )

        tracing_image = temporary / "mask.png"

        _crop_raster(
            source,
            tracing_image,
            crop,
        )

        actions = list(_trace_actions())

        actions.extend(
            (
                "export-type:svg",
                f"export-filename:{output}",
                "export-area-page",
                "export-do",
            )
        )

        run(
            tracing_image,
            actions=tuple(actions),
        )

    if not output.is_file():
        raise VectorError(f"Inkscape did not create expected vector layer: {output}")

    tree = load(
        output,
    )

    _remove_raster_images(
        tree,
    )

    _register_vector_layer(
        tree,
        crop=crop,
    )

    save(
        tree,
        output,
    )


def _remove_raster_images(
    tree: ET.ElementTree[ET.Element[str]],
) -> None:
    """
    Remove embedded raster images from the traced SVG.
    """

    image_tag = f"{{{SVG_NS}}}image"

    root = tree.getroot()

    for parent in root.iter():
        for child in list(
            parent,
        ):
            if child.tag == image_tag:
                parent.remove(
                    child,
                )


def _register_vector_layer(
    tree: ET.ElementTree[ET.Element[str]],
    *,
    crop: RasterCrop,
) -> None:
    """
    Register one traced vector layer in the common Artwork coordinate system.

    Inkscape traces the already-cropped raster in crop-local coordinates.
    Registered Artwork instead uses the corresponding source-raster
    coordinates.

    The SVG coordinate system is therefore restored to the common crop and
    supported crop-local geometry is translated by the crop origin.
    """

    root = tree.getroot()

    root.set(
        "viewBox",
        " ".join(
            (
                str(crop.x),
                str(crop.y),
                str(crop.size),
                str(crop.size),
            )
        ),
    )

    root.set(
        "width",
        str(crop.size),
    )

    root.set(
        "height",
        str(crop.size),
    )

    for element in root:
        x = element.get(
            "x",
        )
        y = element.get(
            "y",
        )

        if x is not None:
            element.set(
                "x",
                str(float(x) + crop.x),
            )

        if y is not None:
            element.set(
                "y",
                str(float(y) + crop.y),
            )


# =========================================================
# Vector manifest
# =========================================================


def _write_manifest(
    path: Path,
    layers: list[
        tuple[
            RasterLayer,
            Path,
        ]
    ],
    *,
    registered_extent: int,
    envelope: Path,
) -> None:
    """
    Write the Registered Artwork product manifest.

    registered_extent records the common square coordinate extent shared
    by the registered envelope and every generated vector color layer.

    Envelope and dynamic-product paths are relative to the manifest's
    stage-local product location.
    """

    products = [
        {
            "index": raster.index,
            "path": vector.name,
            "name": raster.name,
            "color": {
                "red": raster.color[0],
                "green": raster.color[1],
                "blue": raster.color[2],
            },
        }
        for raster, vector in layers
    ]

    data = {
        "registered_extent": registered_extent,
        "envelope": envelope.name,
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
    "VectorError",
    "execute",
]
