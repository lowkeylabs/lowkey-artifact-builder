"""
Circular artifact model.

The circular model provides the foundation for circular artifacts such
as ornaments and drink coasters.
"""

from __future__ import annotations

from lowkey_artifact_builder.model.registry import (
    ModelRegistry,
)
from lowkey_artifact_builder.model.specs import (
    ModelSpec,
)

MODEL = ModelSpec(
    name="circular",
    title="Circular",
    description=("Circular artifact model for products such as ornaments and drink coasters."),
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
