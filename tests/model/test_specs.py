"""
Tests for model specifications.
"""
# File: tests/model/test_specs.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from dataclasses import FrozenInstanceError

import pytest

from lowkey_artifact_builder.model.specs import (
    FeatureSpec,
    InputSpec,
    ModelSpec,
    ProductDependencyBinding,
    ProductDependencySpec,
    ProductRef,
    ProductSpec,
    StageSpec,
)

# =========================================================
# InputSpec
# =========================================================


def test_input_spec() -> None:
    """
    Input specifications retain their definition.
    """

    input_spec = InputSpec(
        name="source",
        parameter="source",
        path="artifact.png",
        description="Source artwork",
    )

    assert input_spec.name == "source"
    assert input_spec.parameter == "source"
    assert input_spec.path == "artifact.png"
    assert input_spec.description == "Source artwork"


def test_input_spec_defaults() -> None:
    """
    Input descriptions are optional.
    """

    input_spec = InputSpec(
        name="source",
        parameter="source",
        path="artifact.png",
    )

    assert input_spec.description == ""


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
# ProductDependencySpec
# =========================================================


def test_product_dependency_spec_preserves_logical_identity() -> None:
    """
    A product dependency identifies its producer without filesystem location.
    """

    dependency = ProductDependencySpec(
        model="producer",
        stage="prepare",
        product="geometry",
    )

    assert dependency.model == "producer"
    assert dependency.stage == "prepare"
    assert dependency.product == "geometry"


def test_product_dependency_spec_is_structurally_equal() -> None:
    """
    Equivalent product dependencies have value-object equality.
    """

    first = ProductDependencySpec(
        model="producer",
        stage="prepare",
        product="geometry",
    )

    second = ProductDependencySpec(
        model="producer",
        stage="prepare",
        product="geometry",
    )

    assert first == second


def test_product_dependency_spec_contains_no_artifact_identity() -> None:
    """
    Declarative product dependencies do not bind a model to one artifact.
    """

    dependency = ProductDependencySpec(
        model="producer",
        stage="prepare",
        product="geometry",
    )

    assert not hasattr(dependency, "artifact")
    assert not hasattr(dependency, "realization")
    assert not hasattr(dependency, "path")


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

    input_spec = InputSpec(
        name="source",
        parameter="source",
        path="artifact.png",
    )

    product = ProductSpec(
        name="stl",
        path="holder/model.stl",
    )

    stage = StageSpec(
        id=10,
        name="holder",
        description="Build the artifact holder",
        dependencies=("source",),
        requires_features=("artwork",),
        inputs=(input_spec,),
        parameters=(
            "outside_diameter",
            "base_raise",
        ),
        products=(product,),
    )

    assert stage.id == 10
    assert stage.name == "holder"
    assert stage.description == "Build the artifact holder"
    assert stage.dependencies == ("source",)
    assert stage.requires_features == ("artwork",)
    assert stage.inputs == (input_spec,)
    assert stage.parameters == (
        "outside_diameter",
        "base_raise",
    )
    assert stage.products == (product,)


def test_stage_spec_defaults() -> None:
    """
    Stages require an ID and name and default to no dependencies,
    required features, inputs, parameters, or products.
    """

    stage = StageSpec(
        id=10,
        name="holder",
    )

    assert stage.id == 10
    assert stage.description == ""
    assert stage.dependencies == ()
    assert stage.product_dependencies == ()
    assert stage.requires_features == ()
    assert stage.inputs == ()
    assert stage.parameters == ()
    assert stage.products == ()


def test_stage_spec_required_features() -> None:
    """
    Stages may require optional model features.
    """

    stage = StageSpec(
        id=10,
        name="labels",
        description="Build artifact labels",
        requires_features=("labels",),
    )

    assert stage.requires_features == ("labels",)


def test_stage_spec_inputs() -> None:
    """
    Stages declare external filesystem inputs separately from ordinary
    resolved parameters.
    """

    input_spec = InputSpec(
        name="source",
        parameter="source",
        path="artifact.png",
    )

    stage = StageSpec(
        id=10,
        name="prepare",
        inputs=(input_spec,),
        parameters=("artwork_colors",),
    )

    assert stage.inputs == (input_spec,)
    assert stage.parameters == ("artwork_colors",)


def test_stage_spec_parameters() -> None:
    """
    Stages declare the resolved parameters that affect their products.
    """

    stage = StageSpec(
        id=10,
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
        id=10,
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


def test_stage_spec_supports_cross_model_product_dependency() -> None:
    """
    A stage may declaratively depend on a product produced by another model.
    """

    dependency = ProductDependencySpec(
        model="producer",
        stage="prepare",
        product="geometry",
    )

    stage = StageSpec(
        id=10,
        name="consume",
        product_dependencies=(dependency,),
    )

    assert stage.product_dependencies == (dependency,)


def test_stage_dependency_identity_is_independent_of_numeric_id() -> None:
    """
    Stage dependencies identify stages by semantic name rather than numeric ID.
    """

    first_prepare = StageSpec(
        id=10,
        name="prepare",
    )

    first_vector = StageSpec(
        id=20,
        name="vector",
        dependencies=("prepare",),
    )

    second_prepare = StageSpec(
        id=40,
        name="prepare",
    )

    second_vector = StageSpec(
        id=10,
        name="vector",
        dependencies=("prepare",),
    )

    first_model = ModelSpec(
        name="first",
        title="First",
        stages=(
            first_prepare,
            first_vector,
        ),
    )

    second_model = ModelSpec(
        name="second",
        title="Second",
        stages=(
            second_prepare,
            second_vector,
        ),
    )

    first_dependencies = {stage.name: stage.dependencies for stage in first_model.stages}

    second_dependencies = {stage.name: stage.dependencies for stage in second_model.stages}

    assert (
        first_dependencies
        == second_dependencies
        == {
            "prepare": (),
            "vector": ("prepare",),
        }
    )


def test_stage_numeric_id_does_not_imply_dependency() -> None:
    """
    Numeric stage ordering does not create an undeclared dependency.
    """

    later_id = StageSpec(
        id=20,
        name="independent",
    )

    earlier_id = StageSpec(
        id=10,
        name="prepare",
    )

    model = ModelSpec(
        name="example",
        title="Example",
        stages=(
            later_id,
            earlier_id,
        ),
    )

    stages = {stage.name: stage for stage in model.stages}

    assert stages["independent"].dependencies == ()
    assert stages["prepare"].dependencies == ()


def test_stage_dependency_may_point_to_higher_numeric_id() -> None:
    """
    Dependency direction is independent of numeric stage ordering.
    """

    producer = StageSpec(
        id=20,
        name="prepare",
    )

    consumer = StageSpec(
        id=10,
        name="vector",
        dependencies=("prepare",),
    )

    model = ModelSpec(
        name="example",
        title="Example",
        stages=(
            producer,
            consumer,
        ),
    )

    stages = {stage.name: stage for stage in model.stages}

    assert stages["vector"].dependencies == ("prepare",)
    assert stages["prepare"].dependencies == ()


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
        id=10,
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


def test_model_spec_rejects_duplicate_stage_ids() -> None:
    """
    Stage IDs must be unique within a model.
    """

    first = StageSpec(
        id=10,
        name="prepare",
    )

    second = StageSpec(
        id=10,
        name="raster",
    )

    with pytest.raises(
        ValueError,
        match="stage ID",
    ):
        ModelSpec(
            name="example",
            title="Example",
            stages=(
                first,
                second,
            ),
        )


def test_model_spec_rejects_duplicate_stage_names() -> None:
    """
    Stage names must be unique within a model.
    """

    first = StageSpec(
        id=10,
        name="prepare",
    )

    second = StageSpec(
        id=20,
        name="prepare",
    )

    with pytest.raises(
        ValueError,
        match="stage name",
    ):
        ModelSpec(
            name="example",
            title="Example",
            stages=(
                first,
                second,
            ),
        )


def test_model_parameters_include_input_parameters() -> None:
    """
    Model parameters include configuration values used to locate
    external filesystem inputs.
    """

    input_spec = InputSpec(
        name="source",
        parameter="source",
        path="artifact.png",
    )

    stage = StageSpec(
        id=10,
        name="prepare",
        inputs=(input_spec,),
        parameters=("artwork_colors",),
    )

    model = ModelSpec(
        name="example",
        title="Example",
        stages=(stage,),
    )

    assert model.parameters == (
        "source",
        "artwork_colors",
    )


def test_model_parameters_preserve_first_occurrence() -> None:
    """
    Model parameters are unique and preserve their first occurrence
    across stage inputs and ordinary parameters.
    """

    first = StageSpec(
        id=10,
        name="prepare",
        inputs=(
            InputSpec(
                name="source",
                parameter="source",
                path="artifact.png",
            ),
        ),
        parameters=(
            "artwork_colors",
            "shared",
        ),
    )

    second = StageSpec(
        id=20,
        name="build",
        inputs=(
            InputSpec(
                name="reference",
                parameter="reference",
                path="reference.png",
            ),
        ),
        parameters=(
            "shared",
            "artwork_size",
            "source",
        ),
    )

    model = ModelSpec(
        name="example",
        title="Example",
        stages=(
            first,
            second,
        ),
    )

    assert model.parameters == (
        "source",
        "artwork_colors",
        "shared",
        "reference",
        "artwork_size",
    )


# =========================================================
# Immutability
# =========================================================


def test_input_spec_is_immutable() -> None:
    """
    Input definitions cannot be modified after creation.
    """

    input_spec = InputSpec(
        name="source",
        parameter="source",
        path="artifact.png",
    )

    with pytest.raises(FrozenInstanceError):
        input_spec.name = "changed"  # type: ignore[misc]


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


def test_product_dependency_spec_is_immutable() -> None:
    """
    Product dependency definitions cannot be modified after creation.
    """

    dependency = ProductDependencySpec(
        model="producer",
        stage="prepare",
        product="geometry",
    )

    with pytest.raises(FrozenInstanceError):
        dependency.model = "changed"  # type: ignore[misc]


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
    Stage definitions, including their stable IDs, cannot be modified
    after creation.
    """

    stage = StageSpec(
        id=10,
        name="holder",
    )

    with pytest.raises(FrozenInstanceError):
        stage.id = 20  # type: ignore[misc]

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


def test_product_dependency_binding_preserves_producer_identity() -> None:
    """
    A product dependency binding identifies the concrete producer
    artifact and realization for one declarative dependency.
    """

    dependency = ProductDependencySpec(
        model="artwork",
        stage="vector",
        product="geometry",
    )

    binding = ProductDependencyBinding(
        dependency=dependency,
        artifact="nydeli",
        realization="default",
    )

    assert binding.dependency == dependency
    assert binding.artifact == "nydeli"
    assert binding.realization == "default"


def test_product_dependency_binding_resolves_product_ref() -> None:
    """
    A dependency binding resolves its declarative dependency to a
    concrete logical product reference.
    """

    binding = ProductDependencyBinding(
        dependency=ProductDependencySpec(
            model="artwork",
            stage="vector",
            product="geometry",
        ),
        artifact="nydeli",
        realization="default",
    )

    assert binding.product_ref == ProductRef(
        artifact="nydeli",
        model="artwork",
        realization="default",
        stage="vector",
        product="geometry",
    )


def test_product_dependency_binding_is_structurally_equal() -> None:
    """
    Equivalent dependency bindings have value-object equality.
    """

    dependency = ProductDependencySpec(
        model="artwork",
        stage="vector",
        product="geometry",
    )

    first = ProductDependencyBinding(
        dependency=dependency,
        artifact="nydeli",
        realization="default",
    )

    second = ProductDependencyBinding(
        dependency=dependency,
        artifact="nydeli",
        realization="default",
    )

    assert first == second


def test_product_dependency_binding_is_immutable() -> None:
    """
    Product dependency bindings are immutable value objects.
    """

    binding = ProductDependencyBinding(
        dependency=ProductDependencySpec(
            model="artwork",
            stage="vector",
            product="geometry",
        ),
        artifact="nydeli",
        realization="default",
    )

    with pytest.raises(
        FrozenInstanceError,
    ):
        binding.artifact = "other"  # type: ignore[misc]
