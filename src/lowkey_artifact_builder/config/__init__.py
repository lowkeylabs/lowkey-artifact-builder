"""
Artifact configuration subsystem.

This package provides configuration loading, persistence, resolution,
provenance tracking, reference color data, and model-derived values.

Application code should normally import configuration services from
this package rather than directly from config.py.
"""
# File: src/lowkey_artifact_builder/config/__init__.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from lowkey_artifact_builder.config.artifact import (
    configure_artifact,
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
    "get_realization_names",
    "get_resolver",
    "load_artifact_config",
    "update_artifact_config",
    "get_product_dependency_binding",
    "has_product_dependency_binding",
    "write_artifact_config",
    "configure_artifact",
]
