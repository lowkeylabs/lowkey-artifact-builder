"""
Artifact inspection command.

Displays the resolved configuration of an existing artifact without
modifying persistent artifact state.
"""
# File: src/lowkey_artifact_builder/cli/cmd_show.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path

import click

from lowkey_artifact_builder.cli.display import (
    display_artifact_config,
)
from lowkey_artifact_builder.cli.variants import (
    parse_variant_reference,
)
from lowkey_artifact_builder.config import (
    ConfigError,
    get_resolver,
    load_artifact_config,
)
from lowkey_artifact_builder.model import (
    build_model_registry,
)

# =========================================================
# CLI
# =========================================================


@click.command("show")
@click.argument(
    "artifact_ids",
    nargs=-1,
)
@click.option(
    "--variant",
    type=str,
    default=None,
    help="Select one artifact Variant.",
)
def cli(
    artifact_ids: tuple[str, ...],
    variant: str | None,
) -> None:
    """
    Display an existing artifact's resolved configuration.

    An optional --variant selects the Variant whose effective
    configuration is inspected.
    """

    if not artifact_ids:
        raise click.UsageError("Artifact inspection requires an artifact ID.")

    if len(artifact_ids) != 1:
        raise click.UsageError("Artifact inspection requires exactly one artifact ID.")

    artifact_id = artifact_ids[0]
    project_root = Path.cwd()

    existing = load_artifact_config(
        artifact_id,
        project_root=project_root,
    )

    if not existing:
        raise click.ClickException(f"Artifact {artifact_id!r} is not defined.")

    if variant is None:
        _display_artifact(
            artifact_id,
            project_root=project_root,
        )
        return

    model_name, variant_name = parse_variant_reference(
        variant,
    )

    _display_artifact(
        artifact_id,
        model_name=model_name,
        variant_name=variant_name,
        project_root=project_root,
    )


# =========================================================
# Artifact display
# =========================================================


def _display_artifact(
    artifact_id: str,
    *,
    model_name: str | None = None,
    variant_name: str | None = None,
    project_root: Path,
) -> None:
    """
    Display an artifact's resolved configuration.

    The artifact must already be defined.

    A selected Variant is identified by its Model and local Variant name.
    The historical runtime realization coordinate carries that local name.
    """

    try:
        if model_name is None and variant_name is None:
            resolver = get_resolver(
                artifact_id,
                project_root=project_root,
            )
        else:
            resolver = get_resolver(
                artifact_id,
                model=model_name,
                realization=variant_name,
                project_root=project_root,
            )

        resolved_model_name = resolver("model")

        registry = build_model_registry()
        model = registry.get_model(
            resolved_model_name,
        )

    except (
        ConfigError,
        KeyError,
    ) as exc:
        raise click.ClickException(str(exc)) from exc

    display_artifact_config(
        artifact_id,
        model,
        resolver,
    )


if __name__ == "__main__":
    cli()
