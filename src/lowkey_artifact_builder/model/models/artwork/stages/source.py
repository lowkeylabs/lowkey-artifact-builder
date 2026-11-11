"""
Artwork source-preserving Stage.

Registers the original materialized Artwork source without tracing,
rasterization, color discovery, or dimensionalization.
"""

# File: src/lowkey_artifact_builder/model/models/artwork/stages/source.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import hashlib
import json
import shutil

from lowkey_artifact_builder.engine import StageContext


class SourceError(RuntimeError):
    """Raised when source-preserving registration cannot be completed."""


def execute(
    context: StageContext,
) -> None:
    """
    Register a byte-identical source Product and its provenance.

    The original materialized source is never modified.
    """

    representation = context.resolver("artwork_representation")
    processing = context.resolver("artwork_processing")

    if (representation, processing) != ("source", "none"):
        raise SourceError(
            "Artwork source Stage requires "
            "artwork_representation='source' and "
            "artwork_processing='none'."
        )

    source = context.input("source")
    artifact = context.output("artifact")
    metadata = context.output("metadata")

    if not source.is_file():
        raise SourceError(f"Artwork source does not exist: {source}")

    source_format = source.suffix.lower().removeprefix(".")

    if source_format not in {"png", "svg"}:
        raise SourceError(f"Unsupported source format {source_format!r}. Expected PNG or SVG.")

    if artifact.resolve() == source.resolve():
        raise SourceError("Source Product must not overwrite its materialized input.")

    if artifact.resolve() == metadata.resolve():
        raise SourceError("Source Product and metadata paths must differ.")

    artifact.parent.mkdir(parents=True, exist_ok=True)
    metadata.parent.mkdir(parents=True, exist_ok=True)

    shutil.copyfile(source, artifact)

    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()

    provenance = {
        "representation": "source",
        "processing": "none",
        "format": source_format,
        "source_name": source.name,
        "sha256": digest,
    }

    metadata.write_text(
        json.dumps(provenance, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
