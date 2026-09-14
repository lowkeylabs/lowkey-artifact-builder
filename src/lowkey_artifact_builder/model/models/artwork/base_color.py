"""
Artwork Base semantic color resolution.

The optional standalone Artwork Base may have an explicitly configured
physical semantic color. Otherwise its color is derived from the existing
Artwork attachment-color semantics.

When Loop participates, Base inherits the resolved Loop color. This keeps
the two standalone attachment features semantically aligned.

When Loop does not participate, Base derives its color as though a Loop
were attached at position 0.
"""

from __future__ import annotations

from dataclasses import dataclass

from lowkey_artifact_builder.colors import resolve_palette_color
from lowkey_artifact_builder.config.config import Resolver
from lowkey_artifact_builder.model.models.artwork.attachment import (
    select_attachment_layer,
)
from lowkey_artifact_builder.model.models.artwork.loop_color import (
    resolve_loop_color,
)
from lowkey_artifact_builder.model.models.artwork.vector_manifest import (
    VectorManifest,
)


@dataclass(
    frozen=True,
    slots=True,
)
class BaseColor:
    """
    Resolved physical color identity of a standalone Artwork Base.

    name identifies the semantic physical color.

    rgb is the concrete physical RGB associated with that semantic color.
    Explicitly configured colors resolve through the configured color palette
    rather than inheriting an unrelated registered Artwork RGB assignment.
    Derived attachment colors preserve the physical RGB already assigned to
    the registered Artwork attachment.
    """

    name: str
    rgb: tuple[int, int, int]


def resolve_base_color_identity(
    artwork: VectorManifest,
    *,
    resolver: Resolver,
) -> BaseColor:
    """
    Resolve the complete physical color identity of the Artwork Base.

    Resolution precedence is:

    1. explicitly configured artwork_base_color;
    2. resolved Loop color and attachment identity when Loop participates;
    3. registered Artwork attachment identity at position 0.

    Explicit Base color configuration is authoritative. Its physical RGB is
    resolved from that semantic color through the configured color palette
    rather than inherited from registered Artwork.

    When Loop participates and its color is explicitly configured, Base
    inherits that semantic Loop color and resolves the physical RGB belonging
    to that color.

    Otherwise Base preserves the physical RGB from the registered Artwork
    attachment that determines the derived semantic color.
    """

    configured_names = resolver.configured_names()

    if "artwork_base_color" in configured_names:
        value = resolver(
            "artwork_base_color",
        )

        if not isinstance(
            value,
            str,
        ):
            raise TypeError("artwork_base_color must resolve to a string.")

        color = resolve_palette_color(
            value,
            resolver.colors,
        )

        return BaseColor(
            name=color.name,
            rgb=color.rgb,
        )

    loop_inner_diameter = resolver(
        "loop_inner_diameter",
    )

    if isinstance(
        loop_inner_diameter,
        bool,
    ) or not isinstance(
        loop_inner_diameter,
        int | float,
    ):
        raise TypeError("loop_inner_diameter must resolve to a number.")

    if float(loop_inner_diameter) > 0.0:
        loop_color = resolve_loop_color(
            artwork,
            resolver=resolver,
        )

        if "loop_color" in configured_names:
            color = resolve_palette_color(
                loop_color,
                resolver.colors,
            )

            return BaseColor(
                name=color.name,
                rgb=color.rgb,
            )

        loop_position = resolver(
            "loop_position",
        )

        if isinstance(
            loop_position,
            bool,
        ) or not isinstance(
            loop_position,
            int,
        ):
            raise TypeError("loop_position must resolve to an integer.")

        attachment_layer = select_attachment_layer(
            artwork,
            position=loop_position,
        )

        return BaseColor(
            name=loop_color,
            rgb=attachment_layer.printer_color,
        )

    attachment_layer = select_attachment_layer(
        artwork,
        position=0,
    )

    return BaseColor(
        name=attachment_layer.printer_color_name,
        rgb=attachment_layer.printer_color,
    )


def resolve_base_color(
    artwork: VectorManifest,
    *,
    resolver: Resolver,
) -> str:
    """
    Resolve the physical semantic color name of the standalone Artwork Base.

    This compatibility API exposes only the semantic color name. Consumers
    that also require the complete physical color identity should use
    resolve_base_color_identity().
    """

    return resolve_base_color_identity(
        artwork,
        resolver=resolver,
    ).name


__all__ = [
    "BaseColor",
    "resolve_base_color",
    "resolve_base_color_identity",
]
