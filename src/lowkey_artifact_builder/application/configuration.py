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

import tomlkit

from lowkey_artifact_builder.config import (
    ConfigError,
    artifact_config_path,
    get_realization_names,
    get_resolver,
)
from lowkey_artifact_builder.config.config import (
    _load_artifact_document,
    _load_model_parameters,
    _write_artifact_document_atomic,
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
# Artifact configuration annotation
# =========================================================


def annotate_artifact_configuration(
    artifact_id: str,
    *,
    project_root: Path | None = None,
) -> Path:
    """
    Append or refresh a commented Model parameter reference.

    The reference includes each registered Model once, regardless
    of how many Realizations select that Model.

    Parameter names come from the Model registry. Values come from
    explicit Model defaults, not effective Realization configuration.

    Missing Model defaults are represented as None in comments.

    Existing active configuration and user-authored comments are
    preserved. Repeated annotation replaces the generated reference.
    """

    root = project_root if project_root is not None else Path.cwd()

    path = artifact_config_path(
        artifact_id,
        project_root=root,
    )

    if not path.is_file():
        raise ConfigError(f"Artifact {artifact_id!r} is not defined.")

    begin_marker = "# BEGIN MODEL PARAMETER REFERENCE"
    end_marker = "# END MODEL PARAMETER REFERENCE"

    document = _load_artifact_document(path)
    original_text = tomlkit.dumps(document)

    begin = original_text.find(begin_marker)
    end = original_text.find(end_marker)

    if (begin == -1) != (end == -1):
        raise ConfigError(
            "Artifact configuration contains an incomplete generated Model parameter reference."
        )

    if begin != -1:
        if end < begin:
            raise ConfigError(
                "Artifact configuration contains an invalid generated Model parameter reference."
            )

        # The generated section owns the blank lines immediately
        # preceding its begin marker.
        section_start = begin

        while section_start > 0 and original_text[section_start - 1] in "\r\n":
            section_start -= 1

        section_end = end + len(end_marker)

        if original_text.startswith("\r\n", section_end):
            section_end += 2
        elif original_text.startswith("\n", section_end):
            section_end += 1

        original_text = original_text[:section_start] + original_text[section_end:]

    # Preserve the retained document and its authored comments.
    document = tomlkit.parse(original_text)

    # Ensure a blank line before the generated section.
    if original_text and not original_text.endswith("\n"):
        document.add(tomlkit.nl())

    document.add(tomlkit.nl())
    document.add(tomlkit.comment("BEGIN MODEL PARAMETER REFERENCE"))
    document.add(tomlkit.comment("Reference only. Uncomment and customize valid TOML values."))

    registry = build_model_registry()

    for model in registry.all_models():
        defaults = _load_model_parameters(model.name)

        document.add(tomlkit.nl())
        document.add(tomlkit.comment(f"Model: {model.name}"))

        for name in model.parameters:
            value = defaults.get(name)

            if value is None:
                rendered = "None"
            else:
                rendered = tomlkit.dumps({"value": value}).partition("=")[2].strip()

            document.add(tomlkit.comment(f"{name} = {rendered}"))

    document.add(tomlkit.nl())
    document.add(tomlkit.comment("END MODEL PARAMETER REFERENCE"))

    _write_artifact_document_atomic(
        path,
        document,
    )

    return path


# =========================================================
# Exports
# =========================================================

__all__ = [
    "ConfigurationParameter",
    "RealizationConfiguration",
    "annotate_artifact_configuration",
    "inspect_realization_configuration",
]
