"""
Artwork source-preserving Stage.

Registers PNG and SVG sources unchanged and normalizes JPEG to PNG,
without tracing, color discovery, or dimensionalization.
"""
# File: src/lowkey_artifact_builder/model/models/artwork/stages/source.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import hashlib
import json
import shutil

from PIL import Image, UnidentifiedImageError

from lowkey_artifact_builder.engine import StageContext


class SourceError(RuntimeError):
    """Raised when source-preserving registration cannot be completed."""


def execute(
    context: StageContext,
) -> None:
    """
    Register source-preserving Artwork and its provenance.

    PNG and SVG are copied without transformation.
    JPEG is decoded and normalized to PNG.

    The original materialized source is never modified.
    """

    representation = context.resolver("artwork_representation")
    processing = context.resolver("artwork_processing")

    if (representation, processing) not in {
        ("source", "none"),
        ("raster", "none"),
        ("vector", "auto"),
    }:
        raise SourceError(
            "Unsupported Artwork representation and processing combination: "
            f"{representation!r}, {processing!r}."
        )

    source = context.input("source")
    artifact = context.output("artifact")
    metadata = context.output("metadata")

    if not source.is_file():
        raise SourceError(f"Artwork source does not exist: {source}")

    if artifact.resolve() == source.resolve():
        raise SourceError("Source Product must not overwrite its materialized input.")

    if artifact.resolve() == metadata.resolve():
        raise SourceError("Source Product and metadata paths must differ.")

    source_format = source.suffix.lower().removeprefix(".")

    if source_format not in {"png", "svg", "jpg", "jpeg"}:
        raise SourceError(
            f"Unsupported source format {source_format!r}. Expected PNG, JPEG, or SVG."
        )

    artifact.parent.mkdir(parents=True, exist_ok=True)
    metadata.parent.mkdir(parents=True, exist_ok=True)

    if source_format == "svg":
        shutil.copyfile(source, artifact)

        output_format = "svg"
        width = None
        height = None
        mode = None

    else:
        try:
            with Image.open(source) as image:
                if image.format not in {"PNG", "JPEG"}:
                    raise SourceError(f"Unsupported image encoding: {image.format!r}")

                image.load()

                width, height = image.size
                mode = image.mode

                if image.format == "JPEG":
                    image.save(artifact, format="PNG")
                    output_format = "png"
                else:
                    shutil.copyfile(source, artifact)
                    output_format = "png"

        except (OSError, UnidentifiedImageError) as exc:
            raise SourceError(f"Cannot decode Artwork source: {source}") from exc

    digest = hashlib.sha256(source.read_bytes()).hexdigest()

    provenance: dict[str, str | int | None] = {
        "representation": "source",
        "processing": "none",
        "format": output_format,
        "source_format": source_format,
        "source_name": source.name,
        "sha256": digest,
    }

    if width is not None and height is not None:
        provenance["width"] = width
        provenance["height"] = height
        provenance["mode"] = mode

    metadata.write_text(
        json.dumps(provenance, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
