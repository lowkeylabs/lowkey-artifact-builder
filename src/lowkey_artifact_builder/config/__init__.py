"""
Artifact configuration subsystem.

This package provides configuration loading, persistence, resolution,
provenance tracking, reference color data, model-derived values, and
high-level artifact lifecycle services.

Application code should normally import configuration services from
this package rather than directly from config.py.
"""
# File: src/lowkey_artifact_builder/config/__init__.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from lowkey_artifact_builder.config.artifact import (
    ArtifactState,
    clean_artifact,
    clean_realization_across_artifacts,
    configure_artifact,
    configure_realization,
    configure_realization_across_artifacts,
    create_realization,
    create_realization_across_artifacts,
    discover_artifacts,
    list_artifacts,
    materialize_artifact,
    realization_3mf_filename,
)
from lowkey_artifact_builder.config.config import (
    ConfigError,
    Derivation,
    Derivations,
    Resolver,
    artifact_config_path,
    get_product_dependency_binding,
    get_realization_configurations_with_value,
    get_realization_names,
    get_resolver,
    has_product_dependency_binding,
    load_artifact_config,
    remove_all_realization_config_values,
    remove_artifact_config_value,
    remove_realization_config_value,
    update_artifact_config,
    update_realization_config,
    write_artifact_config,
)

__all__ = [
    "ArtifactState",
    "ConfigError",
    "Derivation",
    "Derivations",
    "Resolver",
    "artifact_config_path",
    "clean_artifact",
    "clean_realization_across_artifacts",
    "configure_artifact",
    "configure_realization",
    "configure_realization_across_artifacts",
    "create_realization",
    "create_realization_across_artifacts",
    "discover_artifacts",
    "get_product_dependency_binding",
    "get_realization_configurations_with_value",
    "get_realization_names",
    "get_resolver",
    "has_product_dependency_binding",
    "list_artifacts",
    "load_artifact_config",
    "remove_all_realization_config_values",
    "remove_artifact_config_value",
    "remove_realization_config_value",
    "update_artifact_config",
    "update_realization_config",
    "write_artifact_config",
    "materialize_artifact",
    "realization_3mf_filename",
]
