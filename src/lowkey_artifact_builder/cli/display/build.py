"""
Build plan display.

This module contains CLI presentation for concrete artifact build
plans.
"""

from __future__ import annotations

from pathlib import Path

from lowkey_artifact_builder.cli.display.common import (
    console,
    create_table,
    format_value,
)
from lowkey_artifact_builder.engine import (
    BuildPlan,
    PlannedInput,
    PlannedProduct,
    PlannedStage,
)

# =========================================================
# Build plan
# =========================================================


def display_build_plan(
    plan: BuildPlan,
) -> None:
    """
    Display a concrete artifact build plan.
    """

    console.print(f"[bold]{plan.artifact_id} Build Plan[/bold]")

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
        plan.artifact_id,
    )

    summary.add_row(
        "Model",
        plan.model.name,
    )

    summary.add_row(
        "Artifact directory",
        str(plan.artifact_dir),
    )

    console.print(summary)

    console.print()

    _display_execution_plan(plan)


# =========================================================
# Execution plan
# =========================================================


def _display_execution_plan(
    plan: BuildPlan,
) -> None:
    """
    Display the concrete stage execution plan.
    """

    table = create_table(
        title="Execution Plan",
    )

    table.add_column(
        "#",
        justify="right",
    )

    table.add_column(
        "Stage",
    )

    table.add_column(
        "Depends On",
    )

    table.add_column(
        "Inputs",
    )

    table.add_column(
        "Parameters",
    )

    table.add_column(
        "Products",
    )

    for index, stage in enumerate(
        plan.stages,
        start=1,
    ):
        table.add_row(
            str(index),
            stage.name,
            _format_dependencies(stage),
            _format_inputs(
                plan,
                stage,
            ),
            _format_parameters(
                plan,
                stage,
            ),
            _format_products(
                plan,
                stage,
            ),
        )

    console.print(table)


# =========================================================
# Stage formatting
# =========================================================


def _format_dependencies(
    stage: PlannedStage,
) -> str:
    """
    Format stage dependencies.
    """

    if not stage.dependencies:
        return "-"

    return ", ".join(stage.dependencies)


def _format_inputs(
    plan: BuildPlan,
    stage: PlannedStage,
) -> str:
    """
    Format planned stage inputs.

    External inputs display both their original source and their
    artifact-owned materialized destination.

    Paths are displayed relative to the project root where possible.
    """

    if not stage.inputs:
        return "-"

    return "\n".join(
        _format_input(
            plan,
            planned_input,
        )
        for planned_input in stage.inputs
    )


def _format_input(
    plan: BuildPlan,
    planned_input: PlannedInput,
) -> str:
    """
    Format one planned stage input.
    """

    destination = _display_path(
        planned_input.path,
        root=plan.project_root,
    )

    source = _display_path(
        planned_input.source_path,
        root=plan.project_root,
    )

    return f"{planned_input.name}={source}\n  ->\n{destination}"


def _format_parameters(
    plan: BuildPlan,
    stage: PlannedStage,
) -> str:
    """
    Format parameters declared by a planned stage.

    StageSpec declares which parameters the stage normally consumes.
    Values are obtained directly from the artifact-specific Resolver
    retained by BuildPlan rather than from copied stage-local values.
    """

    parameters = stage.spec.parameters

    if not parameters:
        return "-"

    return "\n".join((f"{name}={format_value(plan.resolver(name))}") for name in parameters)


def _format_products(
    plan: BuildPlan,
    stage: PlannedStage,
) -> str:
    """
    Format planned stage products.

    Paths are displayed relative to the project root where possible.
    """

    if not stage.products:
        return "-"

    return "\n".join(
        _format_product(
            plan,
            planned_product,
        )
        for planned_product in stage.products
    )


def _format_product(
    plan: BuildPlan,
    planned_product: PlannedProduct,
) -> str:
    """
    Format one planned stage product.
    """

    return _display_path(
        planned_product.path,
        root=plan.project_root,
    )


# =========================================================
# Paths
# =========================================================


def _display_path(
    path: Path,
    *,
    root: Path,
) -> str:
    """
    Return a path suitable for CLI presentation.

    Paths beneath the project root are displayed relative to that
    root. Paths outside the project root remain absolute.
    """

    path = Path(path)

    root = Path(root)

    try:
        return str(path.relative_to(root))

    except ValueError:
        return str(path)


__all__ = [
    "display_build_plan",
]
