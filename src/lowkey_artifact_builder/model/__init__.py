"""
Artifact model subsystem.

The model subsystem defines artifact models and their declarative
workflows.

Models describe what may be built. The model subsystem also provides
the small bootstrap interface used to register model definitions and
their stage implementations with the build engine.
"""
# File: src/lowkey_artifact_builder/model/__init__.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from lowkey_artifact_builder.model.bootstrap import (
    build_model_registry,
    register_stage_implementations,
)
from lowkey_artifact_builder.model.registry import (
    DuplicateModelError,
    ModelNotFoundError,
    ModelRegistry,
    ModelRegistryError,
)
from lowkey_artifact_builder.model.specs import (
    FeatureSpec,
    InputSpec,
    ModelSpec,
    ProductRef,
    ProductSpec,
    StageSpec,
    VariantSpec,
)

__all__ = [
    "DuplicateModelError",
    "FeatureSpec",
    "InputSpec",
    "ModelNotFoundError",
    "ModelRegistry",
    "ModelRegistryError",
    "ModelSpec",
    "ProductRef",
    "ProductSpec",
    "StageSpec",
    "VariantSpec",
    "build_model_registry",
    "register_stage_implementations",
]
