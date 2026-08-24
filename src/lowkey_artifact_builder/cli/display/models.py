"""
Model display helpers.

This module owns human-readable terminal presentation for registered
artifact models and their declared workplans.
"""
# File: src/lowkey_artifact_builder/cli/display/models.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from collections.abc import Iterable

from rich.text import Text

from lowkey_artifact_builder.cli.display.common import (
    console,
    create_table,
)
from lowkey_artifact_builder.model import (
    InputSpec,
    ModelSpec,
    ProductSpec,
    StageSpec,
)

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

    table = create_table(
        title="Available Models",
        show_header=True,
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

    table = create_table(
        show_header=False,
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

    table = create_table(
        show_header=True,
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

        if stage.inputs:
            _display_stage_inputs(
                stage.inputs,
            )

        if stage.parameters:
            _display_stage_parameters(
                stage.parameters,
            )

        if stage.products:
            _display_stage_products(
                stage.products,
            )


def _display_stage_inputs(
    inputs: tuple[InputSpec, ...],
) -> None:
    """
    Display external filesystem inputs consumed by a stage.
    """

    console.print("    [bold]Inputs[/bold]")

    table = create_table(
        show_header=True,
    )

    table.add_column(
        "Name",
        style="bold",
        no_wrap=True,
    )

    table.add_column(
        "Parameter",
        no_wrap=True,
    )

    table.add_column(
        "Materialized Path",
        no_wrap=True,
    )

    table.add_column(
        "Description",
    )

    for input_spec in inputs:
        table.add_row(
            input_spec.name,
            input_spec.parameter,
            input_spec.path,
            input_spec.description,
        )

    console.print(
        table,
        justify="left",
    )


def _display_stage_parameters(
    parameters: tuple[str, ...],
) -> None:
    """
    Display resolved non-filesystem parameters consumed by a stage.
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

    table = create_table(
        show_header=True,
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
# Workplans
# =========================================================


def display_model_workplan(
    model: ModelSpec,
) -> None:
    """
    Display the complete declared workplan for a model.

    The workplan is a compact workflow-oriented representation of the
    model stages. It describes the potential work declared by the
    model; it does not represent the execution state of a particular
    artifact.
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

    table = create_table(
        show_header=True,
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
        "Inputs",
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
            _format_inputs(stage.inputs),
            _format_values(stage.parameters),
            _format_products(stage.products),
        )

    console.print(
        table,
    )


# =========================================================
# Formatting
# =========================================================


def _format_values(
    values: tuple[str, ...],
) -> str:
    """
    Format a tuple of names for compact table presentation.
    """

    if not values:
        return "-"

    return "\n".join(values)


def _format_inputs(
    inputs: tuple[InputSpec, ...],
) -> str:
    """
    Format stage external inputs for compact workplan presentation.
    """

    if not inputs:
        return "-"

    return "\n".join(
        (f"{input_spec.name}: {input_spec.parameter} -> {input_spec.path}") for input_spec in inputs
    )


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
    "display_model",
    "display_model_workplan",
    "display_model_workplans",
    "display_models",
]
