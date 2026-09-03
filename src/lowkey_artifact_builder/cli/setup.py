"""
Interactive artifact configuration helpers.

This module owns interactive command-line walkthroughs used to gather
artifact configuration from the user.

Setup is driven by the selected model's declared stage parameters and
the resolved configuration stack.

Initial values supplied by the caller participate in normal resolution.
Only parameters that remain unresolved are prompted for.

The setup routines collect configuration choices. They do not persist
configuration or perform artifact builds.
"""
# File: src/lowkey_artifact_builder/cli/setup.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import click

from lowkey_artifact_builder.cli.display import (
    console,
)
from lowkey_artifact_builder.config import (
    ConfigError,
    get_resolver,
    load_artifact_config,
)
from lowkey_artifact_builder.model import (
    ModelRegistry,
    ModelSpec,
)

# =========================================================
# Results
# =========================================================


@dataclass(
    frozen=True,
    slots=True,
)
class ArtifactSetup:
    """
    Configuration collected for an artifact setup.

    values contains explicit artifact configuration supplied by the
    caller or collected interactively.

    Values supplied by system, model, variant, or workspace
    configuration are intentionally omitted.
    """

    artifact_id: str

    model: str

    values: dict[str, Any] = field(
        default_factory=dict,
    )


# =========================================================
# Public interface
# =========================================================


def setup_artifact(
    artifact_id: str,
    registry: ModelRegistry,
    *,
    values: dict[str, object] | None = None,
    project_root: Path | None = None,
) -> ArtifactSetup:
    """
    Complete configuration required to define an artifact.

    The artifact ID is supplied by the command line and is therefore
    not prompted for.

    Explicit values supplied by the caller are treated as initial
    artifact configuration. They participate in resolution before
    missing parameters are determined.

    If the model is supplied explicitly, that model is used. Otherwise
    an existing artifact model is used when present. If neither source
    identifies the model, the user selects one interactively.

    Once the model is known, its declared stage parameters are examined
    against the complete configuration stack plus the supplied initial
    values. Only parameters that remain unresolved are prompted for.

    Source files are discovered relative to the project root.

    This function collects configuration only. It does not persist the
    artifact.
    """

    root = project_root if project_root is not None else Path.cwd()

    supplied_values = dict(
        values or {},
    )

    console.print()
    console.print(f"[bold]Configure artifact:[/bold] {artifact_id}")
    console.print()

    existing = load_artifact_config(
        artifact_id,
        project_root=root,
    )

    model_name = supplied_values.get(
        "model",
    )

    if model_name is None:
        model_name = existing.get(
            "model",
        )

    if model_name is None:
        model_name = _prompt_model(
            registry,
        )

    elif not isinstance(
        model_name,
        str,
    ):
        raise click.ClickException("Artifact model must be a string.")

    try:
        model = registry.get_model(
            model_name,
        )

    except KeyError as exc:
        raise click.ClickException(f"Unknown artifact model {model_name!r}.") from exc

    resolver = get_resolver(
        artifact_id,
        model=model_name,
        project_root=root,
    )

    resolver = resolver.with_values(
        supplied_values,
        provenance="setup",
    )

    missing = _missing_parameters(
        model,
        resolver,
    )

    prompted_values = _prompt_missing_parameters(
        missing,
        project_root=root,
    )

    result_values = dict(
        supplied_values,
    )

    result_values.update(
        prompted_values,
    )

    result = ArtifactSetup(
        artifact_id=artifact_id,
        model=model_name,
        values=result_values,
    )

    _display_summary(
        result,
    )

    return result


# =========================================================
# Model selection
# =========================================================


def _prompt_model(
    registry: ModelRegistry,
) -> str:
    """
    Prompt for an artifact model.
    """

    models = list(registry.all_models())

    if not models:
        raise click.ClickException("No artifact models are registered.")

    console.print("[bold]Available models[/bold]")

    for index, model in enumerate(
        models,
        start=1,
    ):
        console.print(f"  {index}. [bold]{model.name}[/bold] — {model.description}")

    console.print()

    choice = click.prompt(
        "Model",
        type=click.IntRange(
            1,
            len(models),
        ),
    )

    return models[choice - 1].name


# =========================================================
# Missing parameters
# =========================================================


def _missing_parameters(
    model: ModelSpec,
    resolver,
) -> tuple[str, ...]:
    """
    Return model parameters that cannot currently be resolved.

    Parameters are considered in their model-defined order.

    A parameter may be satisfied by system defaults, model defaults,
    workspace overrides, artifact overrides, supplied setup values, or
    derivation.
    """

    missing: list[str] = []

    for parameter in model.parameters:
        try:
            resolver.resolve(
                parameter,
            )

        except ConfigError as exc:
            if not _is_unknown_parameter_error(
                exc,
                parameter,
            ):
                raise

            missing.append(
                parameter,
            )

    return tuple(
        missing,
    )


def _is_unknown_parameter_error(
    exc: ConfigError,
    parameter: str,
) -> bool:
    """
    Return whether a configuration error represents a missing value.

    Other resolution errors, such as derivation failures or cycles,
    must not be mistaken for missing configuration.
    """

    return str(exc) == (f"Unknown configuration value {parameter!r}.")


# =========================================================
# Parameter prompting
# =========================================================


def _prompt_missing_parameters(
    parameters: tuple[str, ...],
    *,
    project_root: Path,
) -> dict[str, Any]:
    """
    Prompt for unresolved model parameters.

    Parameter-specific prompts are defined here only when interaction
    requires domain-specific behavior such as selecting a source file
    or validating a physical dimension.

    Encountering an unresolved parameter without a prompt definition is
    treated as an implementation error rather than silently guessing
    its type or meaning.
    """

    values: dict[str, Any] = {}

    for parameter in parameters:
        values[parameter] = _prompt_parameter(
            parameter,
            project_root=project_root,
        )

    return values


def _prompt_parameter(
    parameter: str,
    *,
    project_root: Path,
) -> Any:
    """
    Prompt for one unresolved parameter.
    """

    if parameter == "source":
        return _prompt_source(
            project_root,
        )

    if parameter == "artwork_size":
        return _prompt_positive_float(
            "Artwork size (mm)",
        )

    raise click.ClickException(
        f"Model requires unresolved parameter "
        f"{parameter!r}, but no interactive prompt "
        "has been defined for it."
    )


# =========================================================
# Source
# =========================================================


def _prompt_source(
    project_root: Path,
) -> str:
    """
    Prompt for a PNG source file in the project root.
    """

    sources = sorted(
        path for path in project_root.iterdir() if path.is_file() and path.suffix.lower() == ".png"
    )

    if not sources:
        raise click.ClickException(f"No PNG source files were found in {project_root}.")

    console.print()
    console.print("[bold]Available PNG sources[/bold]")

    for index, source in enumerate(
        sources,
        start=1,
    ):
        console.print(f"  {index}. {source.name}")

    console.print()

    choice = click.prompt(
        "Source",
        type=click.IntRange(
            1,
            len(sources),
        ),
    )

    return sources[choice - 1].name


# =========================================================
# Numeric parameters
# =========================================================


def _prompt_positive_float(
    label: str,
) -> float:
    """
    Prompt for a positive floating-point value.
    """

    return click.prompt(
        label,
        type=click.FloatRange(
            min=0.0,
            min_open=True,
        ),
    )


# =========================================================
# Summary
# =========================================================


def _display_summary(
    setup: ArtifactSetup,
) -> None:
    """
    Display explicit configuration collected for this artifact.
    """

    console.print()
    console.print("[bold]Artifact configuration[/bold]")
    console.print()

    console.print(f"  [bold]Artifact ID:[/bold] {setup.artifact_id}")

    console.print(f"  [bold]Model:[/bold]       {setup.model}")

    display_values = {name: value for name, value in setup.values.items() if name != "model"}

    if not display_values:
        console.print()
        console.print("  [dim]All model parameters are already configured.[/dim]")

        return

    console.print()
    console.print("[bold]Artifact values[/bold]")

    for name, value in display_values.items():
        console.print(f"  [bold]{name}:[/bold] {value}")


# =========================================================
# Exports
# =========================================================


__all__ = [
    "ArtifactSetup",
    "setup_artifact",
]
