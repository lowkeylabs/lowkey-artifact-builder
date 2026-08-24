"""
Model subsystem bootstrap.

Constructs and populates the artifact model registry and contributes
model-specific stage implementations to the build engine.

The model subsystem owns discovery of models, features, and their
implementations. Other subsystems interact with that discovery through
the small public bootstrap interfaces defined here.

Future plugin discovery may extend the model implementation package
without requiring the build engine to know which models, features, or
plugins exist.
"""
# File: src/lowkey_artifact_builder/model/bootstrap.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol

from .models import (
    register_all_models,
    register_all_stage_implementations,
)
from .registry import (
    ModelRegistry,
)

# =========================================================
# Stage implementation registration protocol
# =========================================================


class StageImplementationRegistry(
    Protocol,
):
    """
    Minimal interface required to register stage implementations.

    This protocol intentionally describes only the registration
    operation required by the model subsystem.

    The concrete registry belongs to the build engine. Keeping that
    concrete type out of the model subsystem prevents the model
    subsystem from depending on engine implementation details.
    """

    def register(
        self,
        model_name: str,
        stage_name: str,
        implementation: Callable[[Any], None],
    ) -> None:
        """
        Register an executable implementation for a model stage.
        """

        ...


# =========================================================
# Model bootstrap
# =========================================================


def build_model_registry() -> ModelRegistry:
    """
    Construct and populate the model registry.

    The returned registry contains every model discovered by the model
    implementation package.
    """

    registry = ModelRegistry()

    register_all_models(
        registry,
    )

    return registry


# =========================================================
# Stage implementation bootstrap
# =========================================================


def register_stage_implementations(
    registry: StageImplementationRegistry,
) -> None:
    """
    Register all discovered model stage implementations.

    Discovery belongs to the model implementation package. This
    bootstrap function provides the stable public boundary used by the
    build engine.

    Individual model packages decide which executable stage
    implementations they contribute. Future feature or plugin
    discovery can extend that process without requiring changes to the
    build engine.
    """

    register_all_stage_implementations(
        registry,
    )


__all__ = [
    "StageImplementationRegistry",
    "build_model_registry",
    "register_stage_implementations",
]
