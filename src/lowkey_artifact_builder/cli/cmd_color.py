"""
Color analysis command.

Reports color-match analysis for prepared Artwork.
"""
# File: src/lowkey_artifact_builder/cli/cmd_color.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from collections.abc import Sequence

import click

from lowkey_artifact_builder.colors import ColorMatch
from lowkey_artifact_builder.model.models.artwork.color_analysis import (
    ArtworkColorMatch,
)

# =========================================================
# Display
# =========================================================


def display_color_matches(
    matches: Sequence[ArtworkColorMatch],
) -> None:
    """
    Display structured Artwork color-match analysis.
    """

    click.echo("Artwork Color Matches")
    click.echo()
    click.echo(f"{'Artwork':<20}{'Printer':<28}{'Library':<28}{'Catalog':<28}")
    click.echo("-" * 104)

    for match in matches:
        click.echo(
            f"{match.artwork.name:<20}"
            f"{_format_match(match.printer):<28}"
            f"{_format_match(match.library):<28}"
            f"{_format_match(match.catalog):<28}"
        )


def _format_match(
    match: ColorMatch,
) -> str:
    """
    Format one structured color match for CLI presentation.
    """

    return f"{match.color.name} {match.distance:.2f}"


# =========================================================
# CLI
# =========================================================


@click.command("colors")
@click.argument(
    "artifact_id",
    required=True,
)
def cli(
    artifact_id: str,
) -> None:
    """
    Report color matches for prepared Artwork.
    """

    del artifact_id
