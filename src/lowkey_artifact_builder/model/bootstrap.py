"""
Model subsystem bootstrap.

Constructs and populates the artifact model registry.

The returned registry contains every model discovered in the model
implementation package.
"""

from __future__ import annotations

from lowkey_artifact_builder.model.models import (
    register_all_models,
)
from lowkey_artifact_builder.model.registry import (
    ModelRegistry,
)

# =========================================================
# Bootstrap
# =========================================================


def build_model_registry() -> ModelRegistry:
    """
    Construct and populate the model registry.
    """

    registry = ModelRegistry()

    register_all_models(
        registry,
    )

    return registry
