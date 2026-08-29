"""Tests for the shape model."""
# File: tests/model/shape/test_shape.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from lowkey_artifact_builder.model import (
    build_model_registry,
)
from lowkey_artifact_builder.model.models.shape import MODEL

# =========================================================
# Helpers
# =========================================================


def _compose_stage():
    """Return the Shape stage that composes registered geometry."""

    return next(stage for stage in MODEL.stages if stage.name == "compose")


def _structure_stage():
    """Return the Shape stage that produces structural geometry."""

    return next(stage for stage in MODEL.stages if stage.name == "structure")


def _extrude_stage():
    """Return the Shape stage that dimensionalizes registered geometry."""

    return next(stage for stage in MODEL.stages if stage.name == "extrude")


def _package_stage():
    """Return the Shape stage that packages physical components."""

    return next(stage for stage in MODEL.stages if stage.name == "package")


# =========================================================
# Model identity
# =========================================================


def test_shape_model_identity() -> None:
    """The shape model has the expected identity."""

    assert MODEL.name == "shape"
    assert MODEL.title == "Shape"


def test_shape_model_is_discovered() -> None:
    """The shape model participates in normal model discovery."""

    registry = build_model_registry()

    names = [model.name for model in registry.all_models()]

    assert "shape" in names


# =========================================================
# Registered composition
# =========================================================


def test_shape_declares_registered_composition_stage() -> None:
    """
    Shape declares a stage for composing registered Shape geometry.
    """

    compose_stage = _compose_stage()

    assert compose_stage.name == "compose"


def test_shape_compose_declares_registered_artwork_dependency() -> None:
    """
    Shape composition declares registered Artwork as its external product dependency.

    The dependency identifies the reusable Artwork vector manifest by logical
    model, stage, and product identity without embedding artifact identity,
    realization identity, or generated filesystem paths.
    """

    compose_stage = _compose_stage()

    assert len(compose_stage.product_dependencies) == 1

    dependency = compose_stage.product_dependencies[0]

    assert dependency.model == "artwork"
    assert dependency.stage == "vector"
    assert dependency.product == "manifest"


def test_shape_artwork_dependency_belongs_only_to_compose() -> None:
    """
    Registered Artwork enters Shape through registered composition.

    Structural Shape generation remains independent of Artwork, while
    extrusion and packaging consume the resulting Shape-local dependency
    closure rather than declaring their own Artwork dependencies.
    """

    dependencies_by_stage = {stage.name: stage.product_dependencies for stage in MODEL.stages}

    assert dependencies_by_stage["structure"] == ()
    assert len(dependencies_by_stage["compose"]) == 1
    assert dependencies_by_stage["extrude"] == ()
    assert dependencies_by_stage["package"] == ()


# =========================================================
# Structural Shape declaration
# =========================================================


def test_shape_declares_structural_stage() -> None:
    """
    Shape declares an independently executable structural stage.

    Structural Shape production has no prerequisite stage or registered
    Artwork dependency.
    """

    structure_stage = _structure_stage()

    assert structure_stage.dependencies == ()
    assert structure_stage.product_dependencies == ()


def test_shape_structure_consumes_registered_geometry_parameters() -> None:
    """
    Structural production consumes only policy required to construct the
    registered Shape geometry.

    Physical X/Y size and Z dimensions belong to downstream physical
    dimensionalization rather than registered structural production.
    """

    structure_stage = _structure_stage()

    assert structure_stage.parameters == ("shape_geometry",)


def test_shape_structure_produces_persistent_structure() -> None:
    """
    Structural production declares one independently verifiable product.

    The product participates in the normal resumable-build and canonical
    product-resolution contracts.
    """

    structure_stage = _structure_stage()

    assert tuple(product.name for product in structure_stage.products) == ("structure",)


def test_shape_structure_has_canonical_relative_product_path() -> None:
    """
    Registered Shape structural geometry has a model-declared relative
    vector-product path.

    The structure stage persists registered two-dimensional geometry rather
    than dimensionalized manufacturing geometry or a packaged 3MF.

    Generated filesystem placement remains the responsibility of planning
    and product resolution rather than artifact configuration.
    """

    structure_stage = _structure_stage()

    product = next(product for product in structure_stage.products if product.name == "structure")

    assert product.path == "structure.svg"


# =========================================================
# Registered composition boundary
# =========================================================


def test_shape_compose_depends_on_structure_stage() -> None:
    """
    Shape composition follows registered structural production.

    Products from the Shape-local structure stage participate in the normal
    model-local stage dependency closure rather than the external product
    dependency mechanism.
    """

    compose_stage = _compose_stage()

    assert compose_stage.dependencies == ("structure",)


def test_shape_compose_produces_persistent_registered_composition() -> None:
    """
    Shape composition declares persistent registered-composition products.

    Registered Shape geometry remains available as composition.svg while a
    manifest provides the persistent contract through which downstream stages
    discover composition membership without scanning the stage directory.
    """

    compose_stage = _compose_stage()

    assert tuple(product.name for product in compose_stage.products) == (
        "composition",
        "manifest",
    )


def test_shape_compose_products_have_canonical_relative_paths() -> None:
    """
    Shape composition products use canonical stage-local relative paths.

    Generated filesystem placement remains the responsibility of planning
    and product resolution rather than the Shape model definition.
    """

    compose_stage = _compose_stage()

    paths = {product.name: product.path for product in compose_stage.products}

    assert paths == {
        "composition": "composition.svg",
        "manifest": "products.json",
    }


def test_shape_compose_consumes_structural_partition_parameters() -> None:
    """
    Registered composition owns the relative structural partition.

    Ridge width is a physical Shape policy expressed in registered space
    relative to shape_size. Ridge style determines whether the structural
    regions must remain distinguishable for downstream component
    dimensionalization.

    Ridge raise remains a physical Z dimension and therefore does not belong
    to registered composition.
    """

    compose_stage = _compose_stage()

    assert compose_stage.parameters == (
        "shape_size",
        "shape_outer_ridge_width",
        "shape_outer_ridge_style",
    )


# =========================================================
# Physical dimensionalization boundary
# =========================================================


def test_shape_declares_extrude_stage_after_registered_composition() -> None:
    """
    Shape declares physical extrusion downstream of registered composition.

    Numeric stage IDs establish deterministic presentation order rather than
    semantic identity or dependency.
    """

    structure_stage = _structure_stage()
    compose_stage = _compose_stage()
    extrude_stage = _extrude_stage()

    assert structure_stage.id < compose_stage.id < extrude_stage.id


def test_shape_extrude_depends_on_compose_stage() -> None:
    """
    Shape extrusion follows registered composition.

    The composed Shape product belongs to the same model-local stage closure
    and therefore does not require an external product dependency binding.
    """

    extrude_stage = _extrude_stage()

    assert extrude_stage.dependencies == ("compose",)
    assert extrude_stage.product_dependencies == ()


def test_shape_extrude_consumes_physical_dimensionalization_parameters() -> None:
    """
    Shape extrusion owns physical dimensionalization of the complete composition.

    Structural dimensions and colors remain extrusion policy. Incorporated
    Artwork receives its Shape-owned physical raise here, and the optional
    Artwork fill color determines whether a corresponding physical fill
    component is produced.

    Standalone Artwork dimensionalization parameters do not participate in
    Shape extrusion.
    """

    extrude_stage = _extrude_stage()

    assert extrude_stage.parameters == (
        "shape_size",
        "shape_base_raise",
        "shape_base_color",
        "shape_outer_ridge_raise",
        "shape_outer_ridge_style",
        "shape_outer_ridge_color",
        "shape_artwork_raise",
        "shape_artwork_fill_color",
    )


def test_shape_extrude_produces_physical_component_manifest() -> None:
    """
    Shape extrusion declares one persistent manifest describing its physical
    manufacturing components.

    Component membership varies with Shape structure. A no-ridge Shape has
    only a base component, while a Shape with a ridge has distinct base and
    ridge component geometry. The manifest provides the stable declared
    product through which downstream packaging discovers those components.
    """

    extrude_stage = _extrude_stage()

    assert tuple(product.name for product in extrude_stage.products) == ("manifest",)

    product = extrude_stage.products[0]

    assert product.path == "products.json"


def test_shape_extrude_does_not_produce_final_artifact() -> None:
    """
    Shape extrusion does not own final artifact packaging.

    Physical component production and final 3MF assembly are separate stage
    responsibilities.
    """

    extrude_stage = _extrude_stage()

    assert all(product.name != "artifact" for product in extrude_stage.products)

    assert all(product.path != "artifact.3mf" for product in extrude_stage.products)


# =========================================================
# Packaging boundary
# =========================================================


def test_shape_declares_package_stage_after_extrusion() -> None:
    """
    Shape declares packaging downstream of physical extrusion.

    Numeric stage IDs preserve deterministic presentation order while the
    explicit dependency establishes the semantic prerequisite.
    """

    extrude_stage = _extrude_stage()
    package_stage = _package_stage()

    assert extrude_stage.id < package_stage.id


def test_shape_package_depends_on_extrude_stage() -> None:
    """
    Shape packaging follows production of physical manufacturing geometry.

    The extrusion products belong to the same model-local stage closure.
    """

    package_stage = _package_stage()

    assert package_stage.dependencies == ("extrude",)
    assert package_stage.product_dependencies == ()


def test_shape_package_declares_no_geometry_parameters() -> None:
    """
    Shape packaging does not construct or dimensionalize geometry.

    Geometry policy and physical dimensions belong to upstream stages.
    Packaging assembles already produced physical components.
    """

    package_stage = _package_stage()

    assert package_stage.parameters == ()


def test_shape_package_produces_final_artifact() -> None:
    """
    Shape packaging produces the canonical final 3MF artifact.
    """

    package_stage = _package_stage()

    assert tuple(product.name for product in package_stage.products) == ("artifact",)

    product = package_stage.products[0]

    assert product.path == "artifact.3mf"


def test_shape_final_artifact_has_single_package_producer() -> None:
    """
    The canonical final Shape artifact has exactly one producer.

    artifact.3mf belongs exclusively to the package stage rather than to
    structural, composition, or extrusion production.
    """

    producers = tuple(
        stage.name
        for stage in MODEL.stages
        for product in stage.products
        if product.path == "artifact.3mf"
    )

    assert producers == ("package",)
