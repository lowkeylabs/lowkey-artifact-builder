"""
Logo artifact model.

The logo model provides the foundation for artifacts whose physical
outline is derived from source artwork rather than a predefined
geometric shape.
"""

from __future__ import annotations

from lowkey_artifact_builder.model.registry import (
    ModelRegistry,
)
from lowkey_artifact_builder.model.specs import (
    ModelSpec,
)

MODEL = ModelSpec(
    name="logo",
    title="Logo",
    description=(
        "Artwork-defined artifact model whose physical outline may be derived from source artwork."
    ),
    defined_in=__name__,
)


def register_models(
    registry: ModelRegistry,
) -> None:
    """
    Register models defined by this package.
    """

    registry.register_model(
        MODEL,
    )
