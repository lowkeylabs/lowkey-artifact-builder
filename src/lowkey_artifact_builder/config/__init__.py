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
    clean_artifact,
    configure_artifact,
    list_artifacts,
)
from lowkey_artifact_builder.config.config import (
    ConfigError,
    Derivation,
    Derivations,
    Resolver,
    artifact_config_path,
    get_product_dependency_binding,
    get_realization_names,
    get_resolver,
    has_product_dependency_binding,
    load_artifact_config,
    update_artifact_config,
    write_artifact_config,
)

__all__ = [
    "ConfigError",
    "Derivation",
    "Derivations",
    "Resolver",
    "artifact_config_path",
    "clean_artifact",
    "configure_artifact",
    "get_product_dependency_binding",
    "get_realization_names",
    "get_resolver",
    "has_product_dependency_binding",
    "list_artifacts",
    "load_artifact_config",
    "update_artifact_config",
    "write_artifact_config",
]
