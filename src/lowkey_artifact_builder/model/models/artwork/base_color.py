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

from lowkey_artifact_builder.config.config import Resolver
from lowkey_artifact_builder.model.models.artwork.attachment import (
    select_attachment_color,
)
from lowkey_artifact_builder.model.models.artwork.loop_color import (
    resolve_loop_color,
)
from lowkey_artifact_builder.model.models.artwork.vector_manifest import (
    VectorManifest,
)


def resolve_base_color(
    artwork: VectorManifest,
    *,
    resolver: Resolver,
) -> str:
    """
    Resolve the physical semantic color of the standalone Artwork Base.

    Resolution precedence is:

    1. explicitly configured artwork_base_color;
    2. resolved Loop color when Loop participates;
    3. registered Artwork attachment color at position 0.

    The final rule is equivalent to resolving the attachment color of a
    hypothetical Loop at position 0 without requiring Loop participation.
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

        return value

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
        return resolve_loop_color(
            artwork,
            resolver=resolver,
        )

    return select_attachment_color(
        artwork,
        position=0,
    )


__all__ = [
    "resolve_base_color",
]
