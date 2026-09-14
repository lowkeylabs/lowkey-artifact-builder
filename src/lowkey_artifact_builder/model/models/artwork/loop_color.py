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

from dataclasses import dataclass

from lowkey_artifact_builder.colors import resolve_palette_color
from lowkey_artifact_builder.config import Resolver
from lowkey_artifact_builder.model.models.artwork.attachment import (
    select_attachment_layer,
)
from lowkey_artifact_builder.model.models.artwork.vector_manifest import (
    VectorManifest,
)


@dataclass(
    frozen=True,
    slots=True,
)
class LoopColor:
    """
    Resolved physical color identity of a standalone Artwork Loop.

    name identifies the semantic physical color.

    rgb is the concrete physical RGB associated with that semantic color.
    Explicitly configured colors resolve through the configured color palette.
    Derived attachment colors preserve the physical RGB already assigned to
    the registered Artwork attachment.
    """

    name: str
    rgb: tuple[int, int, int]


def resolve_loop_color_identity(
    artwork: VectorManifest,
    *,
    resolver: Resolver,
) -> LoopColor:
    """
    Resolve the complete physical color identity of a participating Loop.

    An explicitly configured loop_color is authoritative. Its physical RGB
    is resolved from that semantic color through the configured color palette.

    Otherwise the Loop preserves the semantic physical color and physical RGB
    of Registered Artwork selected at the effective loop_position.
    """

    if "loop_color" in resolver.configured_names():
        value = resolver(
            "loop_color",
        )

        if not isinstance(
            value,
            str,
        ):
            raise TypeError("loop_color must resolve to a string.")

        color = resolve_palette_color(
            value,
            resolver.colors,
        )

        return LoopColor(
            name=color.name,
            rgb=color.rgb,
        )

    position = resolver(
        "loop_position",
    )

    if isinstance(
        position,
        bool,
    ) or not isinstance(
        position,
        int,
    ):
        raise TypeError("loop_position must resolve to an integer.")

    attachment_layer = select_attachment_layer(
        artwork,
        position=position,
    )

    return LoopColor(
        name=attachment_layer.printer_color_name,
        rgb=attachment_layer.printer_color,
    )


def resolve_loop_color(
    artwork: VectorManifest,
    *,
    resolver: Resolver,
) -> str:
    """
    Return the semantic physical color for a participating Artwork Loop.

    This compatibility API exposes only the semantic color name. Consumers
    that also require the complete physical color identity should use
    resolve_loop_color_identity().
    """

    return resolve_loop_color_identity(
        artwork,
        resolver=resolver,
    ).name


__all__ = [
    "LoopColor",
    "resolve_loop_color",
    "resolve_loop_color_identity",
]
