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

from lowkey_artifact_builder.cli.display import (
    display_color_matches,
)
from lowkey_artifact_builder.model.models.artwork.color_analysis import (
    ArtworkColorMatch,
)

# =========================================================
# Analysis
# =========================================================


def analyze_artifact_colors(
    artifact_id: str,
) -> Sequence[ArtworkColorMatch]:
    """
    Analyze color matches for one configured artifact.

    Artifact resolution is implemented separately from CLI orchestration.
    """

    del artifact_id
    return ()


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

    matches = analyze_artifact_colors(
        artifact_id,
    )

    display_color_matches(
        matches,
    )
