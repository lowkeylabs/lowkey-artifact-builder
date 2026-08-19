"""
Tests for model specifications.
"""

from dataclasses import FrozenInstanceError

import pytest

from lowkey_artifact_builder.model.specs import (
    FeatureSpec,
    ModelSpec,
    ProductSpec,
    StageSpec,
)

# =========================================================
# ProductSpec
# =========================================================


def test_product_spec() -> None:
    """
    Product specifications retain their definition.
    """

    product = ProductSpec(
        name="stl",
        path="holder/model.stl",
        description="Holder STL",
    )

    assert product.name == "stl"
    assert product.path == "holder/model.stl"
    assert product.description == "Holder STL"


def test_product_spec_defaults() -> None:
    """
    Product descriptions are optional.
    """

    product = ProductSpec(
        name="stl",
        path="holder/model.stl",
    )

    assert product.description == ""


# =========================================================
# FeatureSpec
# =========================================================


def test_feature_spec() -> None:
    """
    Feature specifications retain their definition.
    """

    feature = FeatureSpec(
        name="magnet",
        description="Embedded magnet cavity",
    )

    assert feature.name == "magnet"
    assert feature.description == "Embedded magnet cavity"


def test_feature_spec_defaults() -> None:
    """
    Feature descriptions are optional.
    """

    feature = FeatureSpec(
        name="hanger",
    )

    assert feature.description == ""


# =========================================================
# StageSpec
# =========================================================


def test_stage_spec() -> None:
    """
    Stage specifications retain their complete definition.
    """

    product = ProductSpec(
        name="stl",
        path="holder/model.stl",
    )

    stage = StageSpec(
        name="holder",
        description="Build the artifact holder",
        dependencies=("source",),
        requires_features=("artwork",),
        parameters=(
            "outside_diameter",
            "base_raise",
        ),
        products=(product,),
    )

    assert stage.name == "holder"
    assert stage.description == "Build the artifact holder"
    assert stage.dependencies == ("source",)
    assert stage.requires_features == ("artwork",)
    assert stage.parameters == (
        "outside_diameter",
        "base_raise",
    )
    assert stage.products == (product,)


def test_stage_spec_defaults() -> None:
    """
    Stages default to no dependencies, required features,
    parameters, or products.
    """

    stage = StageSpec(
        name="holder",
    )

    assert stage.description == ""
    assert stage.dependencies == ()
    assert stage.requires_features == ()
    assert stage.parameters == ()
    assert stage.products == ()


def test_stage_spec_required_features() -> None:
    """
    Stages may require optional model features.
    """

    stage = StageSpec(
        name="labels",
        description="Build artifact labels",
        requires_features=("labels",),
    )

    assert stage.requires_features == ("labels",)


def test_stage_spec_parameters() -> None:
    """
    Stages declare the resolved parameters that affect their products.
    """

    stage = StageSpec(
        name="holder",
        parameters=(
            "outside_diameter",
            "base_raise",
            "ridge_width",
            "hanger_od",
            "magnet_diameter",
        ),
    )

    assert stage.parameters == (
        "outside_diameter",
        "base_raise",
        "ridge_width",
        "hanger_od",
        "magnet_diameter",
    )


def test_stage_parameters_are_independent_of_source() -> None:
    """
    Stage parameters identify resolved values rather than configuration
    tiers or TOML locations.

    The specification therefore contains parameter names only.
    """

    stage = StageSpec(
        name="holder",
        parameters=(
            "outside_diameter",
            "base_raise",
        ),
    )

    assert "workspace.outside_diameter" not in stage.parameters
    assert "artifact.outside_diameter" not in stage.parameters

    assert "outside_diameter" in stage.parameters
    assert "base_raise" in stage.parameters


# =========================================================
# ModelSpec
# =========================================================


def test_model_spec() -> None:
    """
    Model specifications retain features and stages.
    """

    feature = FeatureSpec(
        name="magnet",
    )

    product = ProductSpec(
        name="stl",
        path="holder/model.stl",
    )

    stage = StageSpec(
        name="holder",
        parameters=(
            "outside_diameter",
            "base_raise",
        ),
        products=(product,),
    )

    model = ModelSpec(
        name="example",
        title="Example",
        description="Example artifact model",
        features=(feature,),
        stages=(stage,),
        defined_in="example.models.example",
    )

    assert model.name == "example"
    assert model.title == "Example"
    assert model.description == "Example artifact model"
    assert model.features == (feature,)
    assert model.stages == (stage,)
    assert model.defined_in == "example.models.example"


def test_model_spec_defaults() -> None:
    """
    Models default to no features or stages.
    """

    model = ModelSpec(
        name="example",
        title="Example",
    )

    assert model.description == ""
    assert model.features == ()
    assert model.stages == ()
    assert model.defined_in is None


# =========================================================
# Immutability
# =========================================================


def test_product_spec_is_immutable() -> None:
    """
    Product definitions cannot be modified after creation.
    """

    product = ProductSpec(
        name="model",
        path="holder/model.stl",
    )

    with pytest.raises(FrozenInstanceError):
        product.name = "changed"  # type: ignore[misc]


def test_feature_spec_is_immutable() -> None:
    """
    Feature definitions cannot be modified after creation.
    """

    feature = FeatureSpec(
        name="magnet",
    )

    with pytest.raises(FrozenInstanceError):
        feature.name = "changed"  # type: ignore[misc]


def test_stage_spec_is_immutable() -> None:
    """
    Stage definitions cannot be modified after creation.
    """

    stage = StageSpec(
        name="holder",
    )

    with pytest.raises(FrozenInstanceError):
        stage.name = "changed"  # type: ignore[misc]


def test_model_spec_is_immutable() -> None:
    """
    Model definitions cannot be modified after creation.
    """

    model = ModelSpec(
        name="example",
        title="Example",
    )

    with pytest.raises(FrozenInstanceError):
        model.name = "changed"  # type: ignore[misc]
