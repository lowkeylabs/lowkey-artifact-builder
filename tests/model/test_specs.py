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
    Stage specifications retain dependencies and products.
    """

    product = ProductSpec(
        name="stl",
        path="holder/model.stl",
    )

    stage = StageSpec(
        name="holder",
        description="Build the artifact holder",
        dependencies=("source",),
        products=(product,),
    )

    assert stage.name == "holder"
    assert stage.description == "Build the artifact holder"
    assert stage.dependencies == ("source",)
    assert stage.products == (product,)


def test_stage_spec_defaults() -> None:
    """
    Stages default to no dependencies and no products.
    """

    stage = StageSpec(
        name="holder",
    )

    assert stage.description == ""
    assert stage.dependencies == ()
    assert stage.products == ()


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


def test_specs_are_immutable() -> None:
    """
    Model definitions cannot be modified after creation.
    """

    model = ModelSpec(
        name="example",
        title="Example",
    )

    with pytest.raises(FrozenInstanceError):
        model.name = "changed"  # type: ignore[misc]
