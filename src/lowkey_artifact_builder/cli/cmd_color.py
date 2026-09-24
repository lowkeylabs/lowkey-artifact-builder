"""
Color analysis command.

Reports physical color analysis for Artifact Realizations.
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
    update_artifact_config,
)
from lowkey_artifact_builder.engine import (
    BuildPlan,
    create_build_plan,
    create_product_dependency_build_plan,
    execute_dependency_build,
)
from lowkey_artifact_builder.model import (
    ProductRef,
)
from lowkey_artifact_builder.model.models.artwork.color_analysis import (
    ArtworkColorAnalysis,
    analyze_registered_artwork_colors,
)
from lowkey_artifact_builder.model.models.shape.color_analysis import (
    ShapeColorAnalysis,
    analyze_shape_colors,
)

# =========================================================
# Analysis
# =========================================================


def analyze_artifact_colors(
    artifact_id: str,
    *,
    realization: str | None = None,
) -> ArtworkColorAnalysis | ShapeColorAnalysis:
    """
    Analyze physical colors for one configured Artifact.

    Without an explicitly selected Realization, analysis targets the canonical
    default Artwork Realization's registered manifest and realizes the required
    products through normal dependency-aware build orchestration before
    consuming the manifest.

    An explicitly requested Realization is resolved first, then dispatched
    according to the Model that owns that Realization.
    """

    project_root = Path.cwd()

    if realization is not None:
        plan = _resolve_color_realization(
            artifact_id,
            realization=realization,
            project_root=project_root,
        )

        if plan.model_name == "artwork":
            return _analyze_artwork_colors(
                artifact_id,
                realization=plan.realization_name,
                project_root=project_root,
            )

        if plan.model_name == "shape":
            return _analyze_shape_colors(
                plan,
            )

        raise RuntimeError(f"Unsupported color-analysis Model: {plan.model_name!r}.")

    return _analyze_artwork_colors(
        artifact_id,
        realization="artwork_default",
        project_root=project_root,
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


def _analyze_artwork_colors(
    artifact_id: str,
    *,
    realization: str,
    project_root: Path,
) -> ArtworkColorAnalysis:
    """
    Analyze one Artwork Realization.

    Color analysis requires only the registered Artwork manifest, so execution
    uses a product-targeted plan rather than a complete Artwork build plan.
    """

    target = ProductRef(
        artifact=artifact_id,
        model="artwork",
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


def _analyze_shape_colors(
    plan: BuildPlan,
) -> ShapeColorAnalysis:
    """
    Analyze colors for a Shape Realization.

    Shape semantic colors are resolved directly from configuration rather than
    interpreted as Artwork color assignments or obtained through Shape stage
    execution.

    Participating Artwork retains its distinct Artwork physical-color
    assignment analysis.
    """

    artwork = _analyze_shape_artwork_colors(
        plan,
    )

    return analyze_shape_colors(
        resolver=plan.resolver,
        artwork=artwork,
    )


def _analyze_shape_artwork_colors(
    plan: BuildPlan,
) -> ArtworkColorAnalysis | None:
    """
    Analyze registered Artwork participating in one Shape Realization.

    The Shape plan owns discovery of the bound Artwork producer. Color analysis
    follows that planned dependency rather than reconstructing or assuming an
    Artwork Artifact or Realization.

    Only the targeted registered Artwork dependency is realized. Shape stages
    and standalone Artwork manufacturing stages are not executed.
    """

    artwork_dependencies = tuple(
        dependency
        for dependency in plan.planned_product_dependencies
        if (
            dependency.product_ref.model == "artwork"
            and dependency.product_ref.stage == "vector"
            and dependency.product_ref.product == "manifest"
        )
    )

    if not artwork_dependencies:
        return None

    if len(artwork_dependencies) != 1:
        raise RuntimeError(
            "Shape color analysis requires exactly one registered Artwork manifest dependency."
        )

    artwork_plan = create_product_dependency_build_plan(
        artwork_dependencies[0],
        project_root=plan.project_root,
    )

    execute_dependency_build(
        artwork_plan,
    )

    manifest = _registered_artwork_manifest(
        artwork_plan,
    )

    return analyze_registered_artwork_colors(
        manifest=manifest,
        resolver=artwork_plan.resolver,
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
# Operation
# =========================================================


def _resolve_recolor_scope(
    artifact_id: str,
    *,
    realization: str | None,
    project_root: Path,
) -> BuildPlan:
    """
    Resolve the configuration scope used by a recolor operation.
    """

    if realization is not None:
        return create_build_plan(
            artifact_id,
            realization=realization,
            project_root=project_root,
        )

    return create_build_plan(
        artifact_id,
        realization="artwork_default",
        project_root=project_root,
    )


def _persist_printer_colors(
    artifact_id: str,
    *,
    realization: str | None,
    printer_colors: tuple[str, ...],
    project_root: Path,
) -> None:
    """
    Persist printer colors at the selected Artifact or Realization scope.

    Artifact-scoped persistence updates only the Artifact-level
    printer_colors value. Existing Realization-specific overrides remain
    unchanged.

    Realization-scoped persistence is introduced by a subsequent TDD slice.
    """

    if realization is not None:
        raise NotImplementedError(
            "Realization-scoped printer-color persistence is not implemented."
        )

    update_artifact_config(
        artifact_id,
        {
            "printer_colors": list(
                printer_colors,
            ),
        },
        project_root=project_root,
    )


def run_colors(
    artifact_id: str,
    *,
    realization: str | None = None,
    recolor: str | None = None,
) -> ArtworkColorAnalysis | ShapeColorAnalysis:
    """
    Run one color operation for an Artifact or Realization.

    Read-only operation delegates directly to normal color analysis.

    Printer recoloring pins the unresolved system/default printer palette at
    the selected Artifact or Realization scope, then performs normal color
    analysis against the newly persisted configuration.
    """

    if recolor is None:
        return analyze_artifact_colors(
            artifact_id,
            realization=realization,
        )

    if recolor == "printer":
        project_root = Path.cwd()

        plan = _resolve_recolor_scope(
            artifact_id,
            realization=realization,
            project_root=project_root,
        )

        printer_colors = tuple(
            plan.resolver.system_value(
                "printer_colors",
            )
        )

        _persist_printer_colors(
            artifact_id,
            realization=realization,
            printer_colors=printer_colors,
            project_root=project_root,
        )

        return analyze_artifact_colors(
            artifact_id,
            realization=realization,
        )

    raise NotImplementedError(f"Recolor operation {recolor!r} is not implemented.")


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
@click.option(
    "--recolor",
    type=click.Choice(
        (
            "printer",
            "library",
            "reset",
            "reset-all-realizations",
        ),
        case_sensitive=True,
    ),
    default=None,
    help="Select and persist an operator color assignment.",
)
def cli(
    artifact_id: str,
    realization: str | None,
    recolor: str | None,
) -> None:
    """
    Report color diagnostics for an Artifact or Realization.
    """

    if realization is not None and recolor == "reset-all-realizations":
        raise click.UsageError(
            "--recolor=reset-all-realizations cannot be combined with --realization."
        )

    analysis = run_colors(
        artifact_id,
        realization=realization,
        recolor=recolor,
    )

    display_color_analysis(
        analysis,
    )
