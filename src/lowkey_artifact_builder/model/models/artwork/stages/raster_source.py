"""
Raster-preserving Artwork Stage.

Registers PNG artwork without color separation or vector tracing.
JPEG sources are decoded and normalized to PNG.
"""

# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import hashlib
import json
import shutil

from PIL import Image, UnidentifiedImageError

from lowkey_artifact_builder.engine import StageContext


class RasterSourceError(RuntimeError):
    """Raised when raster-preserving registration fails."""


def execute(context: StageContext) -> None:
    """Register raster Artwork as a reusable PNG Product."""

    representation = context.resolver("artwork_representation")
    processing = context.resolver("artwork_processing")

    if (representation, processing) != ("raster", "none"):
        raise RasterSourceError(
            "Artwork raster_source Stage requires "
            "artwork_representation='raster' and "
            "artwork_processing='none'."
        )

    source = context.input("source")
    artifact = context.output("artifact")
    metadata = context.output("metadata")

    if not source.is_file():
        raise RasterSourceError(f"Artwork source does not exist: {source}")

    if artifact.resolve() == source.resolve():
        raise RasterSourceError("Raster Product must not overwrite its source.")

    if artifact.resolve() == metadata.resolve():
        raise RasterSourceError("Raster Product and metadata paths must differ.")

    source_format = source.suffix.lower().removeprefix(".")
    if source_format not in {"png", "jpg", "jpeg"}:
        raise RasterSourceError(
            f"Unsupported raster source format {source_format!r}. Expected PNG or JPEG."
        )

    try:
        with Image.open(source) as image:
            if image.format not in {"PNG", "JPEG"}:
                raise RasterSourceError(f"Unsupported image encoding: {image.format!r}")

            image.load()
            width, height = image.size
            mode = image.mode

            artifact.parent.mkdir(parents=True, exist_ok=True)

            if image.format == "PNG":
                shutil.copyfile(source, artifact)
            else:
                image.save(artifact, format="PNG")

    except (OSError, UnidentifiedImageError) as exc:
        raise RasterSourceError(f"Cannot decode raster Artwork source: {source}") from exc

    digest = hashlib.sha256(source.read_bytes()).hexdigest()

    provenance = {
        "representation": "raster",
        "processing": "none",
        "format": "png",
        "source_format": source_format,
        "source_name": source.name,
        "width": width,
        "height": height,
        "mode": mode,
        "sha256": digest,
    }

    metadata.parent.mkdir(parents=True, exist_ok=True)
    metadata.write_text(
        json.dumps(provenance, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
