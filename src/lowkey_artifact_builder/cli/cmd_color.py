"""
Color analysis command.

Reports physical color assignments for registered Artwork.
"""
# File: src/lowkey_artifact_builder/cli/cmd_color.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path

import click

from lowkey_artifact_builder.cli.display import (
    display_color_analysis,
)
from lowkey_artifact_builder.config import (
    get_resolver,
)
from lowkey_artifact_builder.engine import (
    BuildPlan,
    create_build_plan,
)
from lowkey_artifact_builder.model import (
    ProductRef,
)
from lowkey_artifact_builder.model.models.artwork.color_analysis import (
    ArtworkColorAnalysis,
    analyze_registered_artwork_colors,
)

# =========================================================
# Analysis
# =========================================================


def analyze_artifact_colors(
    artifact_id: str,
) -> ArtworkColorAnalysis:
    """
    Analyze physical color assignments for one configured artifact.

    Analysis consumes the existing registered Artwork manifest identified
    by targeted build planning without executing the build.
    """

    project_root = Path.cwd()

    resolver = get_resolver(
        artifact_id,
        project_root=project_root,
    )

    model = resolver("model")
    realization = resolver("realization")

    if not isinstance(model, str):
        raise RuntimeError("Artifact model must resolve to a string.")

    if not isinstance(realization, str):
        raise RuntimeError("Artifact realization must resolve to a string.")

    target = ProductRef(
        artifact=artifact_id,
        model=model,
        realization=realization,
        stage="vector",
        product="manifest",
    )

    plan = create_build_plan(
        artifact_id,
        realization=realization,
        targets=(target,),
        project_root=project_root,
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
    Report color diagnostics for registered Artwork.
    """

    analysis = analyze_artifact_colors(
        artifact_id,
    )

    display_color_analysis(
        analysis,
    )
