"""
Artwork Loop color resolution.

This module owns the Artwork-specific policy for resolving the semantic
physical color of a participating Loop Feature.

An explicitly configured Loop color is authoritative. Otherwise the Loop
uses the semantic physical color selected from Registered Artwork at the
effective Loop attachment position.
"""
# File: src/lowkey_artifact_builder/model/models/artwork/loop_color.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from lowkey_artifact_builder.config import Resolver
from lowkey_artifact_builder.model.models.artwork.attachment import (
    select_attachment_color,
)
from lowkey_artifact_builder.model.models.artwork.vector_manifest import (
    VectorManifest,
)


def resolve_loop_color(
    artwork: VectorManifest,
    *,
    resolver: Resolver,
) -> str:
    """
    Return the semantic physical color for a participating Artwork Loop.

    An explicitly configured loop_color is authoritative.

    Otherwise color is selected from Registered Artwork at the effective
    loop_position.
    """

    if "loop_color" in resolver.configured_names():
        return str(
            resolver(
                "loop_color",
            )
        )

    position = resolver(
        "loop_position",
    )

    return select_attachment_color(
        artwork,
        position=position,
    )


__all__ = [
    "resolve_loop_color",
]
