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
from lowkey_artifact_builder.engine import (
    BuildPlan,
    create_build_plan,
    execute_dependency_build,
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
    *,
    realization: str | None = None,
) -> ArtworkColorAnalysis:
    """
    Analyze physical color assignments for one configured artifact.

    Analysis currently targets the canonical default Artwork Realization's
    registered manifest and realizes the required products through normal
    dependency-aware build orchestration before consuming the manifest.

    A requested Realization is resolved before its Model-specific color
    semantics are interpreted.
    """

    project_root = Path.cwd()

    if realization is not None:
        _resolve_color_realization(
            artifact_id,
            realization=realization,
            project_root=project_root,
        )

        raise NotImplementedError("Realization-scoped color analysis is not yet implemented.")

    artwork_realization = "artwork_default"

    target = ProductRef(
        artifact=artifact_id,
        model="artwork",
        realization=artwork_realization,
        stage="vector",
        product="manifest",
    )

    plan = create_build_plan(
        artifact_id,
        realization=artwork_realization,
        targets=(target,),
        project_root=project_root,
    )

    execute_dependency_build(
        plan,
    )

    manifest = _registered_artwork_manifest(
        plan,
    )

    return analyze_registered_artwork_colors(
        manifest=manifest,
        resolver=plan.resolver,
    )


def _resolve_color_realization(
    artifact_id: str,
    *,
    realization: str,
    project_root: Path,
) -> BuildPlan:
    """
    Resolve the Realization selected for color analysis.

    Resolution identifies the selected execution coordinate without assuming
    which Model owns the Realization or which Model products color analysis
    will ultimately consume.
    """

    return create_build_plan(
        artifact_id,
        realization=realization,
        project_root=project_root,
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
@click.option(
    "--realization",
    type=str,
    default=None,
    help="Analyze a specific Realization.",
)
def cli(
    artifact_id: str,
    realization: str | None,
) -> None:
    """
    Report color diagnostics for registered Artwork.
    """

    analysis = analyze_artifact_colors(
        artifact_id,
        realization=realization,
    )

    display_color_analysis(
        analysis,
    )
