"""
Artifact model subsystem.

The model subsystem defines artifact models and their declarative
workflows.

Models describe what may be built. The model subsystem also provides
the small bootstrap interface used to register model definitions and
their stage implementations with the build engine.
"""

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
    ProductSpec,
    StageSpec,
)

__all__ = [
    "DuplicateModelError",
    "FeatureSpec",
    "InputSpec",
    "ModelNotFoundError",
    "ModelRegistry",
    "ModelRegistryError",
    "ModelSpec",
    "ProductSpec",
    "StageSpec",
    "build_model_registry",
    "register_stage_implementations",
]
