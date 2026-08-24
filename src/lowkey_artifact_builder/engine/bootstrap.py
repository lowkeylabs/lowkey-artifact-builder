"""
Artifact build engine bootstrap.

This module constructs the executable stage registry used by the build
engine.

The engine owns stage execution, but model-specific stage
implementations belong to the model subsystem. Bootstrap connects those
two subsystems through a deliberately small registration interface.

The engine does not know which models, features, or plugins exist.
Those concerns belong to the model subsystem.

Future model or feature plugin discovery may therefore evolve entirely
within the model subsystem while preserving this bootstrap interface.
"""
# File: src/lowkey_artifact_builder/engine/bootstrap.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from lowkey_artifact_builder.model import (
    register_stage_implementations,
)

from .registry import StageRegistry

# =========================================================
# Public interface
# =========================================================


def build_stage_registry() -> StageRegistry:
    """
    Construct the executable stage registry.

    The model subsystem contributes the implementations associated with
    its registered model stages.

    Registration is delegated to the model subsystem so the engine does
    not need to know about individual models, features, or plugins.
    """

    registry = StageRegistry()

    register_stage_implementations(registry)

    return registry


__all__ = [
    "build_stage_registry",
]
