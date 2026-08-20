"""
CLI presentation helpers.

This module owns human-readable terminal presentation for the command
line interface.

Core application subsystems should not depend on Rich. Commands obtain
application objects and pass them to the display functions defined
here.
"""

from __future__ import annotations

from collections.abc import Iterable

from rich.console import Console
from rich.table import Table
from rich.text import Text

from lowkey_artifact_builder.engine.plan import (
    BuildPlan,
    PlannedStage,
)
from lowkey_artifact_builder.model import ModelSpec
from lowkey_artifact_builder.model.specs import (
    ProductSpec,
    StageSpec,
)

# =========================================================
# Console
# =========================================================


console = Console()


# =========================================================
# Models
# =========================================================


def display_models(
    models: Iterable[ModelSpec],
    *,
    dump: bool = False,
) -> None:
    """
    Display registered artifact models.

    When dump is false, display a concise summary table.

    When dump is true, display the complete declarative definition of
    each model.
    """

    model_list = list(models)

    if not model_list:
        console.print("[dim]No models are registered.[/dim]")
        return

    if dump:
        for index, model in enumerate(model_list):
            if index:
                console.print()

            display_model(
                model,
            )

        return

    _display_model_summary(
        model_list,
    )


def _display_model_summary(
    models: list[ModelSpec],
) -> None:
    """
    Display a concise table of registered models.
    """

    table = Table(
        title="Available Models",
        show_header=True,
        header_style="bold",
    )

    table.add_column(
        "Model",
        style="bold",
        no_wrap=True,
    )

    table.add_column(
        "Title",
        no_wrap=True,
    )

    table.add_column(
        "Description",
    )

    for model in models:
        table.add_row(
            model.name,
            model.title,
            model.description,
        )

    console.print(
        table,
    )


def display_model(
    model: ModelSpec,
) -> None:
    """
    Display the complete declarative definition of one model.
    """

    console.print(
        Text(
            model.name,
            style="bold",
        )
    )

    _display_model_metadata(
        model,
    )

    console.print()

    _display_features(
        model,
    )

    console.print()

    _display_stages(
        model,
    )


def _display_model_metadata(
    model: ModelSpec,
) -> None:
    """
    Display model identity and provenance.
    """

    table = Table(
        show_header=False,
        box=None,
        pad_edge=False,
    )

    table.add_column(
        "Field",
        style="bold",
        no_wrap=True,
    )

    table.add_column(
        "Value",
    )

    table.add_row(
        "Title",
        model.title,
    )

    if model.description:
        table.add_row(
            "Description",
            model.description,
        )

    if model.defined_in:
        table.add_row(
            "Defined in",
            model.defined_in,
        )

    console.print(
        table,
    )


# =========================================================
# Features
# =========================================================


def _display_features(
    model: ModelSpec,
) -> None:
    """
    Display features supported by a model.
    """

    console.print("[bold]Features[/bold]")

    if not model.features:
        console.print("  [dim](none)[/dim]")
        return

    table = Table(
        show_header=True,
        header_style="bold",
        box=None,
        pad_edge=False,
    )

    table.add_column(
        "Feature",
        style="bold",
        no_wrap=True,
    )

    table.add_column(
        "Description",
    )

    for feature in model.features:
        table.add_row(
            feature.name,
            feature.description,
        )

    console.print(
        table,
    )


# =========================================================
# Stages
# =========================================================


def _display_stages(
    model: ModelSpec,
) -> None:
    """
    Display stages declared by a model.
    """

    console.print("[bold]Stages[/bold]")

    if not model.stages:
        console.print("  [dim](none)[/dim]")
        return

    for index, stage in enumerate(model.stages):
        if index:
            console.print()

        console.print(f"  [bold]{stage.name}[/bold]")

        if stage.description:
            console.print(f"    {stage.description}")

        if stage.requires_features:
            console.print(
                "    [bold]Requires features:[/bold] " + ", ".join(stage.requires_features)
            )

        if stage.dependencies:
            console.print("    [bold]Dependencies:[/bold] " + ", ".join(stage.dependencies))

        if stage.parameters:
            _display_stage_parameters(
                stage.parameters,
            )

        if stage.products:
            _display_stage_products(
                stage.products,
            )


def _display_stage_parameters(
    parameters: tuple[str, ...],
) -> None:
    """
    Display resolved parameters consumed by a stage.
    """

    console.print("    [bold]Parameters[/bold]")

    for parameter in parameters:
        console.print(f"      {parameter}")


def _display_stage_products(
    products: tuple[ProductSpec, ...],
) -> None:
    """
    Display filesystem products produced by a stage.
    """

    console.print("    [bold]Products[/bold]")

    table = Table(
        show_header=True,
        header_style="bold",
        box=None,
        pad_edge=False,
    )

    table.add_column(
        "Name",
        style="bold",
        no_wrap=True,
    )

    table.add_column(
        "Path",
        no_wrap=True,
    )

    table.add_column(
        "Description",
    )

    for product in products:
        table.add_row(
            product.name,
            product.path,
            product.description,
        )

    console.print(
        table,
        justify="left",
    )


# =========================================================
# Artifact configuration
# =========================================================


def display_artifact_config(
    artifact_id: str,
    model: ModelSpec,
    resolver,
) -> None:
    """
    Display the resolved configuration for an artifact.

    The model determines which resolved parameters participate in its
    potential workflow.

    Each parameter is displayed with its effective value and
    configuration provenance.
    """

    console.print(
        Text(
            f"{artifact_id} Configuration",
            style="bold",
        )
    )

    console.print()

    metadata = Table(
        show_header=False,
        box=None,
        pad_edge=False,
    )

    metadata.add_column(
        "Field",
        style="bold",
        no_wrap=True,
    )

    metadata.add_column(
        "Value",
    )

    metadata.add_row(
        "Artifact ID",
        artifact_id,
    )

    metadata.add_row(
        "Model",
        model.name,
    )

    console.print(
        metadata,
    )

    console.print()

    _display_artifact_parameters(
        model,
        resolver,
    )


def _display_artifact_parameters(
    model: ModelSpec,
    resolver,
) -> None:
    """
    Display resolved parameters consumed by an artifact model.

    Parameters that cannot currently be resolved are shown as missing.
    """

    console.print("[bold]Resolved parameters[/bold]")

    if not model.parameters:
        console.print("  [dim](none)[/dim]")
        return

    table = Table(
        show_header=True,
        header_style="bold",
    )

    table.add_column(
        "Parameter",
        style="bold",
        no_wrap=True,
    )

    table.add_column(
        "Value",
    )

    table.add_column(
        "Source",
        no_wrap=True,
    )

    for parameter in model.parameters:
        if not resolver.has(parameter):
            table.add_row(
                parameter,
                "[red](missing)[/red]",
                "-",
            )

            continue

        value = resolver(parameter)

        source = resolver.source(parameter)

        table.add_row(
            parameter,
            _format_parameter_value(value),
            source,
        )

    console.print(
        table,
    )


def _format_parameter_value(
    value: object,
) -> str:
    """
    Format a resolved configuration value for terminal display.
    """

    if isinstance(
        value,
        list | tuple,
    ):
        return ", ".join(str(item) for item in value)

    if value is None:
        return "-"

    return str(value)


# =========================================================
# Build plans
# =========================================================


def display_build_plan(
    plan: BuildPlan,
) -> None:
    """
    Display the concrete build plan for an artifact.

    Unlike a model workplan, a build plan represents the resolved
    workflow for one particular artifact.
    """

    console.print(
        Text(
            f"{plan.artifact_id} Build Plan",
            style="bold",
        )
    )

    console.print()

    metadata = Table(
        show_header=False,
        box=None,
        pad_edge=False,
    )

    metadata.add_column(
        "Field",
        style="bold",
        no_wrap=True,
    )

    metadata.add_column(
        "Value",
    )

    metadata.add_row(
        "Artifact ID",
        plan.artifact_id,
    )

    metadata.add_row(
        "Model",
        plan.model_name,
    )

    console.print(
        metadata,
    )

    console.print()

    if not plan.stages:
        console.print("[dim]No build stages are required.[/dim]")
        return

    _display_build_plan_table(
        plan.stages,
    )


def _display_build_plan_table(
    stages: tuple[PlannedStage, ...],
) -> None:
    """
    Display the resolved stages in an artifact build plan.
    """

    table = Table(
        title="Execution Plan",
        show_header=True,
        header_style="bold",
    )

    table.add_column(
        "#",
        justify="right",
        style="dim",
        no_wrap=True,
    )

    table.add_column(
        "Stage",
        style="bold",
        no_wrap=True,
    )

    table.add_column(
        "Depends On",
        no_wrap=True,
    )

    table.add_column(
        "Parameters",
    )

    table.add_column(
        "Products",
    )

    for index, stage in enumerate(
        stages,
        start=1,
    ):
        table.add_row(
            str(index),
            stage.name,
            _format_values(stage.dependencies),
            _format_planned_parameters(stage),
            _format_planned_products(stage),
        )

    console.print(
        table,
    )


def _format_planned_parameters(
    stage: PlannedStage,
) -> str:
    """
    Format resolved stage parameters for build-plan display.
    """

    if not stage.parameters:
        return "-"

    return "\n".join(
        f"{parameter.name}={_format_parameter_value(parameter.value)}"
        for parameter in stage.parameters
    )


def _format_planned_products(
    stage: PlannedStage,
) -> str:
    """
    Format stage products for build-plan display.
    """

    if not stage.products:
        return "-"

    return "\n".join(product.spec.path for product in stage.products)


# =========================================================
# Workplans
# =========================================================


def display_model_workplan(
    model: ModelSpec,
) -> None:
    """
    Display the complete declared workplan for a model.

    The workplan is a compact workflow-oriented representation of the
    model stages. It describes the potential work declared by the model;
    it does not represent the execution state of a particular artifact.
    """

    console.print(
        Text(
            f"{model.title} Workplan",
            style="bold",
        )
    )

    if model.description:
        console.print(
            model.description,
        )

    console.print()

    if not model.stages:
        console.print("[dim]No stages are declared.[/dim]")
        return

    _display_workplan_table(
        model.stages,
    )


def display_model_workplans(
    models: Iterable[ModelSpec],
) -> None:
    """
    Display declared workplans for multiple models.
    """

    model_list = list(models)

    if not model_list:
        console.print("[dim]No models are registered.[/dim]")
        return

    for index, model in enumerate(model_list):
        if index:
            console.print()

        display_model_workplan(
            model,
        )


def _display_workplan_table(
    stages: tuple[StageSpec, ...],
) -> None:
    """
    Display model stages as a compact workplan table.
    """

    table = Table(
        show_header=True,
        header_style="bold",
    )

    table.add_column(
        "#",
        justify="right",
        style="dim",
        no_wrap=True,
    )

    table.add_column(
        "Stage",
        style="bold",
        no_wrap=True,
    )

    table.add_column(
        "Depends On",
        no_wrap=True,
    )

    table.add_column(
        "Features",
        no_wrap=True,
    )

    table.add_column(
        "Parameters",
    )

    table.add_column(
        "Products",
    )

    for index, stage in enumerate(
        stages,
        start=1,
    ):
        table.add_row(
            str(index),
            stage.name,
            _format_values(stage.dependencies),
            _format_values(stage.requires_features),
            _format_values(stage.parameters),
            _format_products(stage.products),
        )

    console.print(
        table,
    )


def _format_values(
    values: tuple[str, ...],
) -> str:
    """
    Format a tuple of names for compact table presentation.
    """

    if not values:
        return "-"

    return "\n".join(values)


def _format_products(
    products: tuple[ProductSpec, ...],
) -> str:
    """
    Format stage product paths for compact table presentation.
    """

    if not products:
        return "-"

    return "\n".join(product.path for product in products)


__all__ = [
    "console",
    "display_artifact_config",
    "display_build_plan",
    "display_model",
    "display_model_workplan",
    "display_model_workplans",
    "display_models",
]
