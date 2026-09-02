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
    materialize_transform,
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
class RasterRegistration:
    """
    Mapping from source SVG coordinates into raster pixel coordinates.
    """

    x: float

    y: float

    size: float

    pixels: int


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
            Manifest describing registered raster color layers and the
            source-to-raster registration used to produce them.

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
        registration, layers = _load_raster_manifest(
            raster_manifest,
        )

        crop = _common_crop(
            layers,
        )

        registered_envelope = vector_manifest.parent / "envelope.svg"

        _register_envelope(
            prepared_envelope,
            registered_envelope,
            registration=registration,
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
) -> tuple[
    RasterRegistration,
    list[RasterLayer],
]:
    """
    Load raster registration and products from the raster manifest.
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

    registration_data = data.get(
        "registration",
    )

    if not isinstance(
        registration_data,
        dict,
    ):
        raise VectorError("Raster manifest does not contain registration.")

    registration_x = registration_data.get(
        "x",
    )

    registration_y = registration_data.get(
        "y",
    )

    registration_size = registration_data.get(
        "size",
    )

    registration_pixels = registration_data.get(
        "pixels",
    )

    if (
        isinstance(
            registration_x,
            bool,
        )
        or not isinstance(
            registration_x,
            int | float,
        )
        or isinstance(
            registration_y,
            bool,
        )
        or not isinstance(
            registration_y,
            int | float,
        )
        or isinstance(
            registration_size,
            bool,
        )
        or not isinstance(
            registration_size,
            int | float,
        )
        or registration_size <= 0
        or isinstance(
            registration_pixels,
            bool,
        )
        or not isinstance(
            registration_pixels,
            int,
        )
        or registration_pixels < 1
    ):
        raise VectorError("Raster manifest contains invalid registration.")

    registration = RasterRegistration(
        x=float(registration_x),
        y=float(registration_y),
        size=float(registration_size),
        pixels=registration_pixels,
    )

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
            raise VectorError("Raster product index must be a positive integer.")

        if (
            not isinstance(
                filename,
                str,
            )
            or not filename
        ):
            raise VectorError(f"Raster product {index} has no valid path.")

        if not isinstance(
            artifact_color_data,
            dict,
        ):
            raise VectorError(f"Raster product {index} has no valid Artifact color.")

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
            raise VectorError(f"Raster product {index} has no valid Artifact color index.")

        if not isinstance(
            artifact_rgb_data,
            dict,
        ):
            raise VectorError(f"Raster product {index} has no valid Artifact RGB.")

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
            raise VectorError(f"Raster product {index} has no valid printer color.")

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
            raise VectorError(f"Raster product {index} has no valid printer color name.")

        printer_color_name = printer_color_name.strip()

        if not isinstance(
            printer_rgb_data,
            dict,
        ):
            raise VectorError(f"Raster product {index} has no valid printer RGB.")

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
            raise VectorError(f"Raster product {index} has no valid assignment distance.")

        path = manifest.parent / filename

        if not path.is_file():
            raise VectorError(f"Raster product does not exist: {path}")

        result.append(
            RasterLayer(
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
        raise VectorError("Raster product indexes must be unique.")

    artifact_color_indexes = [layer.artifact_color_index for layer in result]

    if len(artifact_color_indexes) != len(set(artifact_color_indexes)):
        raise VectorError("Artifact color indexes must be unique.")

    printer_color_names = [layer.printer_color_name for layer in result]

    if len(printer_color_names) != len(set(printer_color_names)):
        raise VectorError("Raster product printer color names must be unique.")

    result.sort(
        key=lambda layer: layer.index,
    )

    return (
        registration,
        result,
    )


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
    registration: RasterRegistration,
    crop: RasterCrop,
) -> None:
    """
    Register the prepared Artwork envelope with the vector coordinate system.

    The prepared envelope is expressed in source coordinates.

    Raster registration maps the source-coordinate square into raster pixels.
    The common vector crop then maps those raster coordinates into canonical
    Registered Artwork coordinates.

    The complete mapping is:

        raster =
            (source - registration origin)
            * registration.pixels
            / registration.size

        registered =
            raster - crop origin

    The registration transform is materialized into the persistent envelope
    geometry so downstream consumers observe geometry directly in Registered
    Artwork coordinates.
    """

    scale = registration.pixels / registration.size

    translate_x = -registration.x * scale - crop.x

    translate_y = -registration.y * scale - crop.y

    tree = load(
        source,
    )

    root = tree.getroot()

    root.set(
        "viewBox",
        " ".join(
            (
                "0",
                "0",
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

    geometry_tags = {
        "{http://www.w3.org/2000/svg}path",
        "{http://www.w3.org/2000/svg}rect",
    }

    for element in root.iter():
        if element.tag not in geometry_tags:
            continue

        materialize_transform(
            element,
            scale=scale,
            translate_x=translate_x,
            translate_y=translate_y,
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
    Those crop-local coordinates are the canonical Registered Artwork
    coordinates.

    The common registered coordinate system therefore begins at zero and
    extends through the common crop size in both X and Y.

    Existing geometry transforms produced by Inkscape are preserved.
    Document metadata and definitions are not transformed.
    """

    root = tree.getroot()

    root.set(
        "viewBox",
        " ".join(
            (
                "0",
                "0",
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

    Artifact color identity and RGB are preserved independently from the
    physical printer-color assignment used to reproduce each region.
    """

    products = [
        {
            "index": raster.index,
            "path": vector.name,
            "artifact_color": {
                "index": raster.artifact_color_index,
                "rgb": {
                    "red": raster.artifact_color[0],
                    "green": raster.artifact_color[1],
                    "blue": raster.artifact_color[2],
                },
            },
            "printer_color": {
                "name": raster.printer_color_name,
                "rgb": {
                    "red": raster.printer_color[0],
                    "green": raster.printer_color[1],
                    "blue": raster.printer_color[2],
                },
            },
            "distance": raster.distance,
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
