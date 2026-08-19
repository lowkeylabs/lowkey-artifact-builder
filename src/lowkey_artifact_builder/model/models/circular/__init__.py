"""
Circular artifact model.

The circular model begins with a circular base and supports optional
features that modify the base geometry or add independently printable
geometry.

A circular artifact may contain zero or more placements of reusable
artwork. Artwork placements reference existing artwork artifacts; the
circular model does not rebuild source artwork.

Artwork placement is planar. A placement may specify X/Y translation,
uniform XY scale, planar rotation, and a placement raise. The placement
raise defines the height from the artifact datum at which the bottom of
the artwork begins.

A circular artifact with no artwork and no optional features is a
simple circular disk.
"""

from __future__ import annotations

from lowkey_artifact_builder.model.registry import (
    ModelRegistry,
)
from lowkey_artifact_builder.model.specs import (
    FeatureSpec,
    ModelSpec,
    ProductSpec,
    StageSpec,
)

# =========================================================
# Features
# =========================================================


FEATURES = (
    FeatureSpec(
        name="labels",
        description=("Add independently printable text labels to the artifact."),
    ),
    FeatureSpec(
        name="ridge",
        description=("Add raised ridge geometry to the artifact base."),
    ),
    FeatureSpec(
        name="hanger",
        description=("Add hanger geometry to the artifact base."),
    ),
    FeatureSpec(
        name="magnet",
        description=("Add a magnet cavity to the artifact base."),
    ),
)


# =========================================================
# Stages
# =========================================================


STAGES = (
    StageSpec(
        name="base",
        description=("Build the circular artifact base."),
        parameters=(
            "outside_diameter",
            "base_height",
        ),
        products=(
            ProductSpec(
                name="model",
                path="base/model.stl",
                description=("Printable circular base geometry."),
            ),
        ),
    ),
    StageSpec(
        name="labels",
        description=("Build independently printable label geometry."),
        requires_features=("labels",),
        products=(
            ProductSpec(
                name="model",
                path="labels/model.stl",
                description=("Printable label geometry."),
            ),
        ),
    ),
    StageSpec(
        name="package",
        description=(
            "Assemble the circular base, optional geometry, and "
            "placed reusable artwork components into the final 3MF."
        ),
        dependencies=(
            "base",
            "labels",
        ),
        products=(
            ProductSpec(
                name="artifact",
                path="artifact.3mf",
                description=("Final printable multicomponent 3MF artifact."),
            ),
        ),
    ),
)


# =========================================================
# Model
# =========================================================


MODEL = ModelSpec(
    name="circular",
    title="Circular",
    description=(
        "Circular artifact model supporting reusable artwork "
        "placements and optional labels, ridge, hanger, and magnet "
        "capabilities."
    ),
    features=FEATURES,
    stages=STAGES,
    defined_in=__name__,
)


# =========================================================
# Registration
# =========================================================


def register_models(
    registry: ModelRegistry,
) -> None:
    """
    Register models defined by this package.
    """

    registry.register_model(
        MODEL,
    )
