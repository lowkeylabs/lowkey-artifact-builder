"""
Color analysis command.

Reports physical color analysis for Artifact Realizations.
"""
# File: src/lowkey_artifact_builder/cli/cmd_color.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import click

from lowkey_artifact_builder.cli.display import (
    display_color_analysis,
)
from lowkey_artifact_builder.colors import (
    PaletteColor,
)
from lowkey_artifact_builder.config import (
    ConfigError,
    get_realization_configurations_with_value,
    get_realization_names,
    remove_all_realization_config_values,
    remove_artifact_config_value,
    remove_realization_config_value,
    update_artifact_config,
    update_realization_config,
)
from lowkey_artifact_builder.config.artifact import (
    list_artifacts,
)
from lowkey_artifact_builder.engine import (
    BuildPlan,
    create_build_plan,
    create_product_dependency_build_plan,
    execute_dependency_build,
)
from lowkey_artifact_builder.formats.threemf import (
    update_component_colors,
)
from lowkey_artifact_builder.model import (
    ProductRef,
)
from lowkey_artifact_builder.model.color import (
    artwork_component_colors,
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


def _resolve_artifact_recolor_realizations(
    artifact_id: str,
    *,
    project_root: Path,
) -> tuple[str, ...]:
    """
    Return every effective Realization applicable to Artifact recoloring.

    Configuration owns Realization discovery so canonical Realizations and
    Artifact-defined Realizations follow the same semantics used by normal
    planning.
    """

    return get_realization_names(
        artifact_id,
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


def _prepare_existing_final_recolor(
    plan: BuildPlan,
    *,
    printer_colors: tuple[str, ...],
) -> dict[str, PaletteColor]:
    """
    Compute the prospective component-color mutation for one existing final 3MF.

    This operation is read-only. The supplied printer_colors are overlaid onto
    the plan's resolved configuration so color assignment reflects the
    configuration that will be effective after persistence.

    The returned mapping can later be applied to the existing final 3MF without
    recomputing color assignments after configuration mutation.
    """

    projected_resolver = plan.resolver.with_values(
        {
            "printer_colors": printer_colors,
        },
        provenance="prospective recolor",
    )

    projected_plan = replace(
        plan,
        resolver=projected_resolver,
    )

    if projected_plan.model_name == "artwork":
        analysis = _analyze_existing_artwork_colors(
            projected_plan,
        )

        return artwork_component_colors(
            analysis,
        )

    if projected_plan.model_name == "shape":
        analysis = _analyze_existing_shape_artwork_colors(
            projected_plan,
        )

        if analysis is None:
            return {}

        return artwork_component_colors(
            analysis,
        )

    raise NotImplementedError(
        f"Prospective existing-final recoloring is not yet implemented "
        f"for model {projected_plan.model_name!r}."
    )


def _prepare_artifact_recolor(
    artifact_id: str,
    *,
    project_root: Path,
) -> tuple[BuildPlan, ...]:
    """
    Resolve and validate the complete Artifact recolor scope.

    Preparation is read-only. Every applicable Realization is resolved and
    validated before any configuration or final-3MF mutation may occur.
    """
    realizations = _resolve_artifact_recolor_realizations(
        artifact_id,
        project_root=project_root,
    )

    plans = tuple(
        _resolve_existing_final_realization(
            artifact_id,
            realization,
            project_root,
        )
        for realization in realizations
    )

    missing_finals: list[Path] = []

    for plan in plans:
        package_stage = next(stage for stage in plan.stages if stage.name == "package")

        final_product = next(
            product for product in package_stage.products if product.name == "artifact"
        )

        if not final_product.path.is_file():
            missing_finals.append(
                final_product.path,
            )

    if missing_finals:
        missing = ", ".join(str(path) for path in missing_finals)

        raise RuntimeError(
            f"Recoloring requires an existing final 3MF for every "
            f"applicable Realization; missing: {missing}"
        )

    source_errors: list[RuntimeError] = []

    for plan in plans:
        try:
            _validate_existing_recolor_source(
                plan,
            )
        except RuntimeError as exc:
            source_errors.append(
                exc,
            )

    if source_errors:
        if len(source_errors) == 1:
            raise source_errors[0]

        details = "; ".join(str(error) for error in source_errors)

        raise RuntimeError(
            f"Recoloring requires usable existing recolor sources for every "
            f"applicable Realization: {details}"
        )

    return plans


def _validate_existing_recolor_source(
    plan: BuildPlan,
) -> None:
    """
    Validate that an existing Realization has the source data needed to recolor
    its final 3MF without executing build stages.

    Artwork Realizations require an existing registered Artwork manifest.
    Shape Realizations require the same only when they consume Artwork.
    Shape Realizations without Artwork have no physical Artwork assignments to
    validate or apply.
    """

    if plan.model_name == "artwork":
        _analyze_existing_artwork_colors(
            plan,
        )
        return

    if plan.model_name == "shape":
        _analyze_existing_shape_artwork_colors(
            plan,
        )
        return

    raise NotImplementedError(
        f"Existing-final recoloring is not yet implemented for model {plan.model_name!r}."
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


def _report_retained_printer_color_overrides(
    artifact_id: str,
    *,
    project_root: Path,
) -> None:
    """
    Report explicit Realization printer_colors overrides retained after an
    Artifact-scoped recolor.
    """

    realizations = get_realization_configurations_with_value(
        artifact_id,
        "printer_colors",
        project_root=project_root,
    )

    if realizations:
        _report_retained_realization_printer_colors(
            realizations,
        )


def _report_retained_realization_printer_colors(
    realizations: tuple[str, ...],
) -> None:
    """
    Report Realizations whose explicit printer_colors remain authoritative.
    """

    names = ", ".join(
        realizations,
    )

    click.echo(f"Retained Realization-specific printer_colors override(s): {names}")


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


def _recolor_existing_final(
    artifact_id: str,
    *,
    realization: str,
    project_root: Path,
) -> None:
    plan = _resolve_existing_final_realization(
        artifact_id,
        realization,
        project_root,
    )

    package_stage = next(stage for stage in plan.stages if stage.name == "package")

    final_product = next(
        product for product in package_stage.products if product.name == "artifact"
    )

    if not final_product.path.is_file():
        raise RuntimeError(f"Recoloring requires an existing final 3MF: {final_product.path}")

    if plan.model_name == "artwork":
        artwork = _analyze_existing_artwork_colors(
            plan,
        )

    elif plan.model_name == "shape":
        artwork = _analyze_existing_shape_artwork_colors(
            plan,
        )

    else:
        raise NotImplementedError(
            f"Existing-final recoloring is not yet implemented for model {plan.model_name!r}."
        )

    if artwork is None:
        return

    colors = artwork_component_colors(
        artwork,
    )

    update_component_colors(
        final_product.path,
        artifact_id=artifact_id,
        colors=colors,
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

    Realization-scoped persistence updates only the selected explicit
    Realization.
    """

    values = {
        "printer_colors": list(
            printer_colors,
        ),
    }

    if realization is not None:
        update_realization_config(
            artifact_id,
            realization,
            values,
            project_root=project_root,
        )

        return

    update_artifact_config(
        artifact_id,
        values,
        project_root=project_root,
    )


def _reset_all_realization_printer_colors(
    artifact_id: str,
    *,
    project_root: Path,
) -> None:
    """
    Remove printer_colors from every explicit Realization customization.

    Artifact-level printer_colors are preserved.
    """

    remove_all_realization_config_values(
        artifact_id,
        "printer_colors",
        project_root=project_root,
    )


def _reset_printer_colors(
    artifact_id: str,
    *,
    realization: str | None,
    project_root: Path,
) -> None:
    """
    Remove printer_colors at the selected Artifact or Realization scope.

    Removing the override restores normal configuration inheritance.
    """

    if realization is not None:
        remove_realization_config_value(
            artifact_id,
            realization,
            "printer_colors",
            project_root=project_root,
        )
        return

    remove_artifact_config_value(
        artifact_id,
        "printer_colors",
        project_root=project_root,
    )


def _resolve_existing_final_realization(
    artifact_id: str,
    realization: str,
    project_root: Path,
) -> BuildPlan:
    """
    Resolve the Realization whose existing final product may be recolored.

    Resolution uses normal build planning to identify the Model, effective
    configuration, and canonical product paths. It does not execute the plan
    or create missing products.
    """

    return create_build_plan(
        artifact_id,
        realization=realization,
        project_root=project_root,
    )


def _analyze_existing_artwork_colors(
    resolved_plan: BuildPlan,
) -> ArtworkColorAnalysis:
    """
    Analyze colors from an already-existing registered Artwork manifest.

    Existing-final recoloring consumes the planned manifest directly. It does
    not execute build stages to create or refresh missing prerequisites.
    """

    manifest = _registered_artwork_manifest(
        resolved_plan,
    )

    if not manifest.is_file():
        raise RuntimeError(
            f"Recoloring requires an existing registered Artwork manifest: {manifest}"
        )

    return analyze_registered_artwork_colors(
        manifest=manifest,
        resolver=resolved_plan.resolver,
    )


def _analyze_existing_shape_artwork_colors(
    resolved_plan: BuildPlan,
) -> ArtworkColorAnalysis | None:
    """
    Analyze already-existing Artwork participating in one Shape Realization.

    The Shape plan owns discovery of the bound Artwork producer. Existing-final
    recoloring follows that planned dependency but does not execute build
    stages to create or refresh the registered Artwork manifest.
    """

    artwork_dependencies = tuple(
        dependency
        for dependency in resolved_plan.planned_product_dependencies
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
        project_root=resolved_plan.project_root,
    )

    return _analyze_existing_artwork_colors(
        artwork_plan,
    )


def _resolve_color_artifact_ids(
    *,
    project_root: Path,
) -> tuple[str, ...]:
    """
    Resolve the Artifact scope for a bulk color operation.

    Artifact discovery is delegated to the authoritative Artifact lifecycle
    service rather than inferred from workspace layout.
    """

    return list_artifacts(
        project_root=project_root,
    )


def _prepare_bulk_recolor(
    artifact_ids: tuple[str, ...],
    *,
    realization: str | None,
    project_root: Path,
) -> tuple[
    tuple[
        str,
        BuildPlan | None,
        tuple[BuildPlan, ...],
    ],
    ...,
]:
    """
    Validate the complete bulk recolor scope before mutation.

    Artifact-scoped preparation delegates to _prepare_artifact_recolor(), which
    validates every applicable final Realization for each Artifact.

    Realization-scoped preparation is deliberately staged across the complete
    selected scope:

    1. resolve every Artifact + Realization coordinate;
    2. verify every required existing final 3MF;
    3. verify every existing recolor source.

    No persistent configuration or final 3MF metadata is changed during
    preparation.
    """

    if realization is None:
        return tuple(
            (
                artifact_id,
                None,
                _prepare_artifact_recolor(
                    artifact_id,
                    project_root=project_root,
                ),
            )
            for artifact_id in artifact_ids
        )

    scope_plans: list[tuple[str, BuildPlan]] = []

    # Pass 1: resolve the complete Artifact + Realization scope.
    for artifact_id in artifact_ids:
        scope_plan = _resolve_recolor_scope(
            artifact_id,
            realization=realization,
            project_root=project_root,
        )

        scope_plans.append(
            (
                artifact_id,
                scope_plan,
            )
        )

    # Pass 2: every selected Realization must already have a final 3MF.
    for _, scope_plan in scope_plans:
        final_path = _existing_final_path(
            scope_plan,
        )

        if not final_path.is_file():
            raise RuntimeError(f"Recoloring requires an existing final 3MF: {final_path}")

    # Pass 3: every selected Realization must have a usable existing
    # recolor source.
    for _, scope_plan in scope_plans:
        _validate_existing_recolor_source(
            scope_plan,
        )

    return tuple(
        (
            artifact_id,
            scope_plan,
            (),
        )
        for artifact_id, scope_plan in scope_plans
    )


def _existing_final_path(
    plan: BuildPlan,
) -> Path:
    """
    Return the existing final 3MF path for one resolved Realization.

    The caller is responsible for validating existence before mutation.
    """

    package_stage = next(stage for stage in plan.stages if stage.name == "package")

    final_product = next(
        product for product in package_stage.products if product.name == "artifact"
    )

    return final_product.path


def run_colors(
    artifact_id: str | None,
    *,
    realization: str | None = None,
    recolor: str | None = None,
) -> (
    ArtworkColorAnalysis
    | ShapeColorAnalysis
    | tuple[
        ArtworkColorAnalysis | ShapeColorAnalysis,
        ...,
    ]
):
    """
    Run one color operation for an Artifact or Realization.

    Read-only operation delegates directly to normal color analysis.

    Printer recoloring pins the unresolved system/default printer palette at
    the selected Artifact or Realization scope.

    Library recoloring pins the effective Library palette as printer_colors at
    the selected Artifact or Realization scope.

    Bulk printer and Library recoloring validate the complete selected scope
    and compute every prospective final-3MF color mutation before any
    persistent configuration or final-3MF mutation occurs.

    Bulk Artifact-scoped reset validates the complete selected scope before
    removing any Artifact-level printer_colors override. Existing finals are
    then recolored through normal post-reset configuration resolution.

    After persistence, normal color analysis runs against the newly persisted
    configuration.
    """

    if recolor is None:
        if artifact_id is not None:
            return analyze_artifact_colors(
                artifact_id,
                realization=realization,
            )

        project_root = Path.cwd()

        artifact_ids = _resolve_color_artifact_ids(
            project_root=project_root,
        )

        return tuple(
            analyze_artifact_colors(
                selected_artifact_id,
                realization=realization,
            )
            for selected_artifact_id in artifact_ids
        )

    if artifact_id is None:
        project_root = Path.cwd()

        artifact_ids = _resolve_color_artifact_ids(
            project_root=project_root,
        )

        if recolor == "reset":
            prepared_artifacts = _prepare_bulk_recolor(
                artifact_ids,
                realization=realization,
                project_root=project_root,
            )

            for (
                selected_artifact_id,
                scope_plan,
                prepared_plans,
            ) in prepared_artifacts:
                _reset_printer_colors(
                    selected_artifact_id,
                    realization=realization,
                    project_root=project_root,
                )

                if realization is None:
                    assert scope_plan is None

                    _report_retained_printer_color_overrides(
                        selected_artifact_id,
                        project_root=project_root,
                    )

                    for prepared_plan in prepared_plans:
                        _recolor_existing_final(
                            selected_artifact_id,
                            realization=prepared_plan.realization_name,
                            project_root=project_root,
                        )

                    continue

                assert scope_plan is not None

                _recolor_existing_final(
                    selected_artifact_id,
                    realization=scope_plan.realization_name,
                    project_root=project_root,
                )

            return tuple(
                analyze_artifact_colors(
                    selected_artifact_id,
                    realization=realization,
                )
                for selected_artifact_id in artifact_ids
            )

        if recolor == "reset-all-realizations":
            if realization is not None:
                raise ValueError(
                    "--recolor=reset-all-realizations cannot be combined with --realization."
                )

            prepared_artifacts = _prepare_bulk_recolor(
                artifact_ids,
                realization=None,
                project_root=project_root,
            )

            for (
                selected_artifact_id,
                scope_plan,
                prepared_plans,
            ) in prepared_artifacts:
                assert scope_plan is None

                _reset_all_realization_printer_colors(
                    selected_artifact_id,
                    project_root=project_root,
                )

                for prepared_plan in prepared_plans:
                    _recolor_existing_final(
                        selected_artifact_id,
                        realization=prepared_plan.realization_name,
                        project_root=project_root,
                    )

            return tuple(
                analyze_artifact_colors(
                    selected_artifact_id,
                    realization=None,
                )
                for selected_artifact_id in artifact_ids
            )

        if recolor not in {
            "printer",
            "library",
        }:
            raise ValueError("Bulk recoloring mutation is not implemented yet.")

        prepared_artifacts = _prepare_bulk_recolor(
            artifact_ids,
            realization=realization,
            project_root=project_root,
        )

        prospective_artifacts: list[
            tuple[
                str,
                tuple[str, ...],
                tuple[
                    tuple[
                        BuildPlan,
                        dict[str, PaletteColor],
                    ],
                    ...,
                ],
            ]
        ] = []

        for (
            selected_artifact_id,
            scope_plan,
            prepared_plans,
        ) in prepared_artifacts:
            if realization is not None:
                assert scope_plan is not None

                if recolor == "printer":
                    printer_colors = tuple(
                        scope_plan.resolver.system_value(
                            "printer_colors",
                        )
                    )
                else:
                    printer_colors = tuple(
                        scope_plan.resolver(
                            "library_colors",
                        )
                    )

                component_colors = _prepare_existing_final_recolor(
                    scope_plan,
                    printer_colors=printer_colors,
                )

                prospective_artifacts.append(
                    (
                        selected_artifact_id,
                        printer_colors,
                        (
                            (
                                scope_plan,
                                component_colors,
                            ),
                        ),
                    )
                )
                continue

            if not prepared_plans:
                continue

            if recolor == "printer":
                printer_colors = tuple(
                    prepared_plans[0].resolver.system_value(
                        "printer_colors",
                    )
                )
            else:
                printer_colors = tuple(
                    prepared_plans[0].resolver(
                        "library_colors",
                    )
                )

            prospective_recolors: list[
                tuple[
                    BuildPlan,
                    dict[str, PaletteColor],
                ]
            ] = []

            for prepared_plan in prepared_plans:
                effective_printer_colors = printer_colors

                if prepared_plan.resolver.source(
                    "printer_colors",
                ).startswith("realization "):
                    effective_printer_colors = tuple(
                        prepared_plan.resolver(
                            "printer_colors",
                        )
                    )

                component_colors = _prepare_existing_final_recolor(
                    prepared_plan,
                    printer_colors=effective_printer_colors,
                )

                prospective_recolors.append(
                    (
                        prepared_plan,
                        component_colors,
                    )
                )

            prospective_artifacts.append(
                (
                    selected_artifact_id,
                    printer_colors,
                    tuple(prospective_recolors),
                )
            )

        for (
            selected_artifact_id,
            printer_colors,
            prepared_recolors,
        ) in prospective_artifacts:
            _persist_printer_colors(
                selected_artifact_id,
                realization=realization,
                printer_colors=printer_colors,
                project_root=project_root,
            )

            if realization is None:
                _report_retained_printer_color_overrides(
                    selected_artifact_id,
                    project_root=project_root,
                )

            for prepared_plan, component_colors in prepared_recolors:
                if not component_colors:
                    continue

                final_path = _existing_final_path(
                    prepared_plan,
                )

                update_component_colors(
                    final_path,
                    artifact_id=selected_artifact_id,
                    colors=component_colors,
                )

        return tuple(
            analyze_artifact_colors(
                selected_artifact_id,
                realization=realization,
            )
            for selected_artifact_id in artifact_ids
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

        prepared_recolors: tuple[
            tuple[
                BuildPlan,
                dict[str, PaletteColor],
            ],
            ...,
        ] = ()

        if realization is None:
            prepared_plans = _prepare_artifact_recolor(
                artifact_id,
                project_root=project_root,
            )

            prospective_recolors: list[
                tuple[
                    BuildPlan,
                    dict[str, PaletteColor],
                ]
            ] = []

            for prepared_plan in prepared_plans:
                effective_printer_colors = printer_colors

                if prepared_plan.resolver.source(
                    "printer_colors",
                ).startswith("realization "):
                    effective_printer_colors = tuple(
                        prepared_plan.resolver(
                            "printer_colors",
                        )
                    )

                component_colors = _prepare_existing_final_recolor(
                    prepared_plan,
                    printer_colors=effective_printer_colors,
                )

                prospective_recolors.append(
                    (
                        prepared_plan,
                        component_colors,
                    )
                )

            prepared_recolors = tuple(
                prospective_recolors,
            )

        _persist_printer_colors(
            artifact_id,
            realization=realization,
            printer_colors=printer_colors,
            project_root=project_root,
        )

        if realization is None:
            _report_retained_printer_color_overrides(
                artifact_id,
                project_root=project_root,
            )

            for prepared_plan, component_colors in prepared_recolors:
                if not component_colors:
                    continue

                final_path = _existing_final_path(
                    prepared_plan,
                )

                update_component_colors(
                    final_path,
                    artifact_id=artifact_id,
                    colors=component_colors,
                )

        else:
            _recolor_existing_final(
                artifact_id,
                realization=realization,
                project_root=project_root,
            )

        return analyze_artifact_colors(
            artifact_id,
            realization=realization,
        )

    if recolor == "library":
        project_root = Path.cwd()

        plan = _resolve_recolor_scope(
            artifact_id,
            realization=realization,
            project_root=project_root,
        )

        printer_colors = tuple(
            plan.resolver(
                "library_colors",
            )
        )

        prepared_plans: tuple[BuildPlan, ...] = ()

        if realization is None:
            prepared_plans = _prepare_artifact_recolor(
                artifact_id,
                project_root=project_root,
            )

        _persist_printer_colors(
            artifact_id,
            realization=realization,
            printer_colors=printer_colors,
            project_root=project_root,
        )

        if realization is None:
            _report_retained_printer_color_overrides(
                artifact_id,
                project_root=project_root,
            )

            for prepared_plan in prepared_plans:
                _recolor_existing_final(
                    artifact_id,
                    realization=prepared_plan.realization_name,
                    project_root=project_root,
                )

        else:
            _recolor_existing_final(
                artifact_id,
                realization=realization,
                project_root=project_root,
            )

        return analyze_artifact_colors(
            artifact_id,
            realization=realization,
        )

    if recolor == "reset":
        project_root = Path.cwd()

        prepared_plans: tuple[BuildPlan, ...] = ()

        if realization is None:
            prepared_plans = _prepare_artifact_recolor(
                artifact_id,
                project_root=project_root,
            )

        _reset_printer_colors(
            artifact_id,
            realization=realization,
            project_root=project_root,
        )

        if realization is None:
            _report_retained_printer_color_overrides(
                artifact_id,
                project_root=project_root,
            )

            for prepared_plan in prepared_plans:
                _recolor_existing_final(
                    artifact_id,
                    realization=prepared_plan.realization_name,
                    project_root=project_root,
                )

        else:
            _recolor_existing_final(
                artifact_id,
                realization=realization,
                project_root=project_root,
            )

        return analyze_artifact_colors(
            artifact_id,
            realization=realization,
        )

    if recolor == "reset-all-realizations":
        if realization is not None:
            raise ValueError(
                "--recolor=reset-all-realizations cannot be combined with --realization."
            )

        project_root = Path.cwd()

        prepared_plans = _prepare_artifact_recolor(
            artifact_id,
            project_root=project_root,
        )

        _reset_all_realization_printer_colors(
            artifact_id,
            project_root=project_root,
        )

        for prepared_plan in prepared_plans:
            _recolor_existing_final(
                artifact_id,
                realization=prepared_plan.realization_name,
                project_root=project_root,
            )

        return analyze_artifact_colors(
            artifact_id,
            realization=realization,
        )

    raise ValueError(f"Unsupported recolor selection {recolor!r}.")


# =========================================================
# CLI
# =========================================================


@click.command("colors")
@click.argument(
    "artifact_id",
    required=False,
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
    artifact_id: str | None,
    realization: str | None,
    recolor: str | None,
) -> None:
    """
    Report color diagnostics for an Artifact or Realization.

    Expected configuration failures are translated into concise operator
    errors at the CLI boundary.
    """

    if realization is not None and recolor == "reset-all-realizations":
        raise click.UsageError(
            "--recolor=reset-all-realizations cannot be combined with --realization."
        )

    if artifact_id is not None:
        artifact_ids = list_artifacts(
            project_root=Path.cwd(),
        )

        if artifact_id not in artifact_ids:
            raise click.ClickException(f"Artifact {artifact_id!r} is not defined.")

    try:
        analysis = run_colors(
            artifact_id,
            realization=realization,
            recolor=recolor,
        )
    except ConfigError as exc:
        raise click.ClickException(str(exc)) from exc

    if isinstance(
        analysis,
        tuple,
    ):
        if not analysis:
            click.echo("No artifacts found.")
            return

        for artifact_analysis in analysis:
            display_color_analysis(
                artifact_analysis,
            )

        return

    display_color_analysis(
        analysis,
    )
