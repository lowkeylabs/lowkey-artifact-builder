"""
Tests for logical product references.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from lowkey_artifact_builder.model.specs import ProductRef


def test_product_ref_stores_logical_identity() -> None:
    ref = ProductRef(
        artifact="nydeli",
        model="artwork",
        realization="default",
        stage="vector",
        product="colors",
    )

    assert ref.artifact == "nydeli"
    assert ref.model == "artwork"
    assert ref.realization == "default"
    assert ref.stage == "vector"
    assert ref.product == "colors"


def test_product_ref_equality_is_structural() -> None:
    left = ProductRef(
        artifact="nydeli",
        model="artwork",
        realization="default",
        stage="vector",
        product="colors",
    )

    right = ProductRef(
        artifact="nydeli",
        model="artwork",
        realization="default",
        stage="vector",
        product="colors",
    )

    assert left == right


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("artifact", "other"),
        ("model", "coaster"),
        ("realization", "ridged"),
        ("stage", "raster"),
        ("product", "geometry"),
    ],
)
def test_product_ref_identity_includes_every_component(
    field: str,
    value: str,
) -> None:
    values = {
        "artifact": "nydeli",
        "model": "artwork",
        "realization": "default",
        "stage": "vector",
        "product": "colors",
    }

    left = ProductRef(**values)

    values[field] = value
    right = ProductRef(**values)

    assert left != right


def test_product_ref_is_hashable() -> None:
    left = ProductRef(
        artifact="nydeli",
        model="artwork",
        realization="default",
        stage="vector",
        product="colors",
    )

    right = ProductRef(
        artifact="nydeli",
        model="artwork",
        realization="default",
        stage="vector",
        product="colors",
    )

    assert hash(left) == hash(right)

    refs = {left, right}

    assert refs == {left}


def test_product_ref_can_be_used_as_dictionary_key() -> None:
    ref = ProductRef(
        artifact="nydeli",
        model="artwork",
        realization="default",
        stage="vector",
        product="colors",
    )

    products = {
        ref: "registered geometry",
    }

    equivalent_ref = ProductRef(
        artifact="nydeli",
        model="artwork",
        realization="default",
        stage="vector",
        product="colors",
    )

    assert products[equivalent_ref] == "registered geometry"


def test_product_ref_is_immutable() -> None:
    ref = ProductRef(
        artifact="nydeli",
        model="artwork",
        realization="default",
        stage="vector",
        product="colors",
    )

    with pytest.raises(FrozenInstanceError):
        ref.product = "geometry"  # type: ignore[misc]


def test_product_ref_formats_canonical_reference() -> None:
    ref = ProductRef(
        artifact="nydeli",
        model="artwork",
        realization="default",
        stage="vector",
        product="colors",
    )

    assert str(ref) == "nydeli:artwork:default:vector:colors"
