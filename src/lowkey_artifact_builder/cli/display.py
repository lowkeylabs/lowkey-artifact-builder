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

from lowkey_artifact_builder.model import ModelSpec

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
    products,
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


__all__ = [
    "console",
    "display_model",
    "display_models",
]
