"""
Model registry.

The registry owns model definition-layer entities.

Execution state, artifact configuration, and generated filesystem
products are owned elsewhere.
"""
# File: src/lowkey_artifact_builder/model/registry.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from lowkey_artifact_builder.model.specs import ModelSpec


class ModelRegistryError(Exception):
    """
    Base exception for model registry errors.
    """


class ModelNotFoundError(ModelRegistryError):
    """
    Raised when a requested model is not registered.
    """


class DuplicateModelError(ModelRegistryError):
    """
    Raised when a model name is registered more than once.
    """


class ModelRegistry:
    """
    Registry of artifact model definitions.
    """

    def __init__(
        self,
    ) -> None:
        self._models: dict[str, ModelSpec] = {}

    # =====================================================
    # Registration
    # =====================================================

    def register_model(
        self,
        spec: ModelSpec,
    ) -> None:
        """
        Register a model definition.

        Model names must be unique.
        """

        if spec.name in self._models:
            raise DuplicateModelError(f"Model already registered: {spec.name}")

        self._models[spec.name] = spec

    # =====================================================
    # Lookup
    # =====================================================

    def get_model(
        self,
        name: str,
    ) -> ModelSpec:
        """
        Return a registered model.
        """

        try:
            return self._models[name]

        except KeyError as exc:
            raise ModelNotFoundError(f"Model not found: {name}") from exc

    def has_model(
        self,
        name: str,
    ) -> bool:
        """
        Return whether a model is registered.
        """

        return name in self._models

    def all_models(
        self,
    ) -> list[ModelSpec]:
        """
        Return all registered models sorted by name.
        """

        return sorted(
            self._models.values(),
            key=lambda model: model.name,
        )

    def __len__(
        self,
    ) -> int:
        """
        Return the number of registered models.
        """

        return len(self._models)
