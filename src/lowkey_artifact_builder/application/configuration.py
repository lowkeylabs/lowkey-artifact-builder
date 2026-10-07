"""
Reusable Realization configuration inspection.

Configuration inspection answers operator-oriented questions about the
construction configuration of an effective Artifact Realization:

    Which Model controls the Realization?
    Which construction parameters does that Model expose?
    What is the effective value of each parameter?
    Which configuration source supplied each effective value?

This module composes existing configuration resolution and Model capabilities.
It does not reconstruct configuration precedence, derivation, or Model
parameter semantics.

Inspection is read-only. It does not materialize Artifacts, write
configuration, manufacture Products, or otherwise mutate the Artifact.
"""

# File: src/lowkey_artifact_builder/application/configuration.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from lowkey_artifact_builder.config import (
    ConfigError,
    get_realization_names,
    get_resolver,
)
from lowkey_artifact_builder.model import (
    build_model_registry,
)

# =========================================================
# Structured application results
# =========================================================


@dataclass(
    frozen=True,
    slots=True,
)
class ConfigurationParameter:
    """
    Effective value and provenance for one construction parameter.

    name
        Model-defined construction parameter name.

    value
        Effective value resolved through the authoritative Resolver.

    source
        Configuration source reported by the authoritative Resolver.
    """

    name: str
    value: Any
    source: str


@dataclass(
    frozen=True,
    slots=True,
)
class RealizationConfiguration:
    """
    Effective construction configuration for one Artifact Realization.

    artifact_id
        Artifact identity.

    realization
        Effective Artifact Realization identity.

    model
        Model selected by the Realization's effective configuration.

    parameters
        Model-defined construction parameters in Model declaration order,
        with their effective values and provenance.
    """

    artifact_id: str
    realization: str
    model: str
    parameters: tuple[
        ConfigurationParameter,
        ...,
    ]


# =========================================================
# Public inspection operation
# =========================================================


def inspect_realization_configuration(
    artifact_id: str,
    realization: str,
    *,
    project_root: Path | None = None,
) -> RealizationConfiguration:
    """
    Inspect effective construction configuration for one Realization.

    Realization identity is established through the existing configuration
    discovery boundary.

    Effective values and provenance are delegated to the authoritative
    Resolver. The selected Model owns the construction-parameter inventory.

    This operation is read-only and does not persist configuration,
    materialize the Artifact, or execute manufacturing work.
    """

    root = project_root if project_root is not None else Path.cwd()

    realization_names = tuple(
        get_realization_names(
            artifact_id,
            project_root=root,
        )
    )

    if realization not in realization_names:
        raise ConfigError(
            f"Realization {realization!r} is not defined for Artifact {artifact_id!r}."
        )

    resolver = get_resolver(
        artifact_id,
        realization=realization,
        project_root=root,
    )

    model_name = resolver(
        "model",
    )

    if not isinstance(
        model_name,
        str,
    ):
        raise ConfigError(
            f"Model for Realization {realization!r} "
            f"of Artifact {artifact_id!r} must resolve to a string."
        )

    registry = build_model_registry()

    model = registry.get_model(
        model_name,
    )

    parameters = tuple(
        ConfigurationParameter(
            name=name,
            value=resolver(
                name,
            ),
            source=resolver.source(
                name,
            ),
        )
        for name in model.parameters
    )

    return RealizationConfiguration(
        artifact_id=artifact_id,
        realization=realization,
        model=model_name,
        parameters=parameters,
    )


# =========================================================
# Exports
# =========================================================


__all__ = [
    "ConfigurationParameter",
    "RealizationConfiguration",
    "inspect_realization_configuration",
]
