"""
Artifact configuration display.

This module contains CLI presentation for resolved artifact
configuration.
"""

from __future__ import annotations

from typing import Any

from lowkey_artifact_builder.cli.display.common import (
    console,
    create_table,
    format_value,
)
from lowkey_artifact_builder.colors import (
    ColorError,
    resolve_palette,
)
from lowkey_artifact_builder.config import (
    Resolver,
)
from lowkey_artifact_builder.model import (
    ModelSpec,
)

# =========================================================
# Artifact configuration
# =========================================================


def display_artifact_config(
    artifact_id: str,
    model: ModelSpec,
    resolver: Resolver,
) -> None:
    """
    Display complete resolved configuration information for an
    artifact.
    """

    console.print(f"[bold]{artifact_id} Configuration[/bold]")

    console.print()

    summary = create_table(
        show_header=False,
    )

    summary.add_column(
        "Field",
        style="bold",
    )

    summary.add_column(
        "Value",
    )

    summary.add_row(
        "Artifact ID",
        artifact_id,
    )

    summary.add_row(
        "Model",
        model.name,
    )

    console.print(summary)

    console.print()

    _display_artifact_parameters(
        model,
        resolver,
    )

    _display_artwork_colors(
        model,
        resolver,
    )


# =========================================================
# Resolved parameters
# =========================================================


def _display_artifact_parameters(
    model: ModelSpec,
    resolver: Resolver,
) -> None:
    """
    Display resolved parameters required by an artifact model.
    """

    console.print("[bold]Resolved parameters[/bold]")

    console.print()

    table = create_table()

    table.add_column(
        "Parameter",
    )

    table.add_column(
        "Value",
    )

    table.add_column(
        "Source",
    )

    for name in model.parameters:
        value = resolver(name)

        source = resolver.source(name)

        table.add_row(
            name,
            format_value(value),
            source,
        )

    console.print(table)


# =========================================================
# Artwork colors
# =========================================================


def _display_artwork_colors(
    model: ModelSpec,
    resolver: Resolver,
) -> None:
    """
    Display the effective artwork color palette.

    Catalog RGB definitions take precedence over CSS color values.
    Colors without a catalog RGB definition fall back to their CSS
    color value.

    Models that do not consume artwork_colors do not display this
    section.
    """

    if "artwork_colors" not in model.parameters:
        return

    names = resolver("artwork_colors")

    try:
        palette = resolve_palette(
            names,
            resolver.colors,
        )

    except ColorError:
        return

    console.print()
    console.print("[bold]Artwork colors[/bold]")
    console.print()

    table = create_table()

    table.add_column(
        "Color",
    )

    table.add_column(
        "RGB",
    )

    table.add_column(
        "Manufacturer",
    )

    table.add_column(
        "Filament",
    )

    table.add_column(
        "Source",
    )

    for color in palette:
        catalog_entry = _catalog_entry(
            resolver,
            color.name,
        )

        rgb = ", ".join(str(channel) for channel in color.rgb)

        if catalog_entry is not None and "rgb" in catalog_entry:
            source = "catalog"
        else:
            source = "CSS"

        table.add_row(
            color.name,
            rgb,
            _catalog_text(
                catalog_entry,
                "manufacturer",
            ),
            _catalog_text(
                catalog_entry,
                "filament",
            ),
            source,
        )

    console.print(table)


# =========================================================
# Color catalog
# =========================================================


def _catalog_entry(
    resolver: Resolver,
    name: str,
) -> dict[str, Any] | None:
    """
    Return a color catalog entry when one exists.
    """

    if not resolver.has_color(name):
        return None

    return dict(resolver.color(name))


def _catalog_text(
    entry: dict[str, Any] | None,
    key: str,
) -> str:
    """
    Return printable color catalog metadata.
    """

    if entry is None:
        return "-"

    value = entry.get(key)

    if value is None:
        return "-"

    return str(value)


__all__ = [
    "display_artifact_config",
]
