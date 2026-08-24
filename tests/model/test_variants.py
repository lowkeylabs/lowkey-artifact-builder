"""
Tests for model-scoped variant specifications.

Variants are reusable named parameter presets defined by a model.

These tests establish only the declarative specification boundary.
Configuration resolution, realization selection, planning, and filesystem
placement belong to later Phase 5 changes.
"""
# File: tests/model/test_variants.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from lowkey_artifact_builder.model.specs import (
    ModelSpec,
    VariantSpec,
)

# =========================================================
# VariantSpec
# =========================================================


def test_variant_spec_stores_named_parameter_preset() -> None:
    """
    A variant retains its name, parameter preset, and description.
    """

    variant = VariantSpec(
        name="ridged",
        parameters={
            "ridge": True,
            "ridge_width": 3.0,
        },
        description="Raised perimeter ridge",
    )

    assert variant.name == "ridged"

    assert variant.parameters == {
        "ridge": True,
        "ridge_width": 3.0,
    }

    assert variant.description == "Raised perimeter ridge"


def test_variant_spec_defaults_to_empty_parameter_preset() -> None:
    """
    A variant may exist without overriding any parameters.
    """

    variant = VariantSpec(
        name="default",
    )

    assert variant.parameters == {}
    assert variant.description == ""


def test_variant_spec_is_immutable() -> None:
    """
    Variant definitions cannot be replaced after construction.
    """

    variant = VariantSpec(
        name="ridged",
        parameters={
            "ridge": True,
        },
    )

    with pytest.raises(FrozenInstanceError):
        variant.name = "plain"  # type: ignore[misc]


# =========================================================
# Model-scoped variants
# =========================================================


def test_model_spec_stores_variants() -> None:
    """
    Variants belong to the model that defines them.
    """

    default = VariantSpec(
        name="default",
    )

    ridged = VariantSpec(
        name="ridged",
        parameters={
            "ridge": True,
        },
    )

    model = ModelSpec(
        name="coaster",
        title="Coaster",
        variants=(
            default,
            ridged,
        ),
    )

    assert model.variants == (
        default,
        ridged,
    )


def test_model_spec_defaults_to_default_variant() -> None:
    """
    Every model has an implicitly available default variant.

    Models that do not declare variants explicitly therefore retain the
    existing simple-model behavior while gaining a well-defined variant
    identity.
    """

    model = ModelSpec(
        name="artwork",
        title="Artwork",
    )

    assert model.variants == (
        VariantSpec(
            name="default",
        ),
    )


def test_model_spec_adds_default_to_explicit_variants() -> None:
    """
    A model that declares named variants still has an implicit default
    variant when it does not declare one itself.
    """

    ridged = VariantSpec(
        name="ridged",
        parameters={
            "ridge": True,
        },
    )

    model = ModelSpec(
        name="coaster",
        title="Coaster",
        variants=(ridged,),
    )

    assert model.variants == (
        VariantSpec(
            name="default",
        ),
        ridged,
    )


def test_model_spec_preserves_explicit_default_variant() -> None:
    """
    An explicitly defined default variant supplies the model's default
    parameter preset.
    """

    default = VariantSpec(
        name="default",
        parameters={
            "ridge": False,
        },
    )

    ridged = VariantSpec(
        name="ridged",
        parameters={
            "ridge": True,
        },
    )

    model = ModelSpec(
        name="coaster",
        title="Coaster",
        variants=(
            default,
            ridged,
        ),
    )

    assert model.variants == (
        default,
        ridged,
    )


def test_model_spec_rejects_duplicate_variant_names() -> None:
    """
    Variant names must be unique within a model.
    """

    first = VariantSpec(
        name="ridged",
        parameters={
            "ridge_width": 2.0,
        },
    )

    second = VariantSpec(
        name="ridged",
        parameters={
            "ridge_width": 3.0,
        },
    )

    with pytest.raises(
        ValueError,
        match="variant name",
    ):
        ModelSpec(
            name="coaster",
            title="Coaster",
            variants=(
                first,
                second,
            ),
        )


def test_same_variant_name_is_valid_in_different_models() -> None:
    """
    Variant identity is model-scoped.

    Two models may independently define variants having the same name
    without establishing any relationship between those variants.
    """

    coaster_default = VariantSpec(
        name="default",
        parameters={
            "diameter": 100.0,
        },
    )

    ornament_default = VariantSpec(
        name="default",
        parameters={
            "diameter": 80.0,
        },
    )

    coaster = ModelSpec(
        name="coaster",
        title="Coaster",
        variants=(coaster_default,),
    )

    ornament = ModelSpec(
        name="ornament",
        title="Ornament",
        variants=(ornament_default,),
    )

    assert coaster.variants == (coaster_default,)

    assert ornament.variants == (ornament_default,)

    assert coaster.variants[0] != ornament.variants[0]
