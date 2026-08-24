"""
Tests for the model registry.
"""
# File: tests/model/test_registry.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

import pytest

from lowkey_artifact_builder.model.registry import (
    DuplicateModelError,
    ModelNotFoundError,
    ModelRegistry,
)
from lowkey_artifact_builder.model.specs import (
    ModelSpec,
)

# =========================================================
# Helpers
# =========================================================


def make_model(
    name: str,
) -> ModelSpec:
    """
    Create a simple model specification for registry tests.
    """

    return ModelSpec(
        name=name,
        title=name.title(),
    )


# =========================================================
# Registration
# =========================================================


def test_registry_starts_empty() -> None:
    """
    A new registry contains no models.
    """

    registry = ModelRegistry()

    assert len(registry) == 0
    assert registry.all_models() == []


def test_register_model() -> None:
    """
    A model can be registered.
    """

    registry = ModelRegistry()

    model = make_model(
        "example",
    )

    registry.register_model(
        model,
    )

    assert len(registry) == 1
    assert registry.has_model("example")


def test_register_duplicate_model_rejected() -> None:
    """
    Model names must be unique.
    """

    registry = ModelRegistry()

    registry.register_model(
        make_model("example"),
    )

    with pytest.raises(
        DuplicateModelError,
        match="Model already registered: example",
    ):
        registry.register_model(
            make_model("example"),
        )


# =========================================================
# Lookup
# =========================================================


def test_get_model() -> None:
    """
    Registered models can be retrieved by name.
    """

    registry = ModelRegistry()

    model = make_model(
        "example",
    )

    registry.register_model(
        model,
    )

    assert registry.get_model("example") is model


def test_get_unknown_model_rejected() -> None:
    """
    Looking up an unknown model raises ModelNotFoundError.
    """

    registry = ModelRegistry()

    with pytest.raises(
        ModelNotFoundError,
        match="Model not found: missing",
    ):
        registry.get_model(
            "missing",
        )


def test_has_model() -> None:
    """
    Model existence can be queried without raising an exception.
    """

    registry = ModelRegistry()

    registry.register_model(
        make_model("example"),
    )

    assert registry.has_model("example")
    assert not registry.has_model("missing")


# =========================================================
# Enumeration
# =========================================================


def test_all_models_sorted_by_name() -> None:
    """
    Registered models are returned in deterministic name order.
    """

    registry = ModelRegistry()

    registry.register_model(
        make_model("zulu"),
    )

    registry.register_model(
        make_model("alpha"),
    )

    registry.register_model(
        make_model("middle"),
    )

    names = [model.name for model in registry.all_models()]

    assert names == [
        "alpha",
        "middle",
        "zulu",
    ]
