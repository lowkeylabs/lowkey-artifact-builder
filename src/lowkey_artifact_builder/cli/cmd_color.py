"""
Color analysis command.

Reports color-match analysis for prepared Artwork.
"""
# File: src/lowkey_artifact_builder/cli/cmd_color.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import click

from lowkey_artifact_builder.cli.display import (
    display_color_matches,
)
from lowkey_artifact_builder.engine import (
    BuildPlan,
    create_build_plan,
)
from lowkey_artifact_builder.model.models.artwork.color_analysis import (
    ArtworkColorMatch,
    analyze_registered_artwork_colors,
)

# =========================================================
# Analysis
# =========================================================


def analyze_artifact_colors(
    artifact_id: str,
) -> Sequence[ArtworkColorMatch]:
    """
    Analyze color matches for one configured artifact.

    Analysis consumes the existing registered Artwork manifest identified
    by build planning without executing the build.
    """

    plan = create_build_plan(
        artifact_id,
        project_root=Path.cwd(),
    )

    manifest = _registered_artwork_manifest(
        plan,
    )

    return analyze_registered_artwork_colors(
        manifest=manifest,
        resolver=plan.resolver,
    )


def _registered_artwork_manifest(
    plan: BuildPlan,
) -> Path:
    """
    Return the planned registered Artwork manifest.
    """

    for stage in plan.stages:
        if stage.name != "vector":
            continue

        for product in stage.products:
            if product.name == "manifest":
                return product.path

    raise RuntimeError("Artwork color analysis requires the registered Artwork manifest.")


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
