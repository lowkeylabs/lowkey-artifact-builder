"""
Tests for model subsystem bootstrap and discovery.
"""
# File: tests/model/test_bootstrap.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from lowkey_artifact_builder.model.bootstrap import (
    build_model_registry,
)
from lowkey_artifact_builder.model.models import (
    RESOURCE_DIR,
)
from lowkey_artifact_builder.model.registry import (
    ModelRegistry,
)

# =========================================================
# Bootstrap
# =========================================================


def test_build_model_registry() -> None:
    """
    Bootstrap returns a populated ModelRegistry.
    """

    registry = build_model_registry()

    assert isinstance(
        registry,
        ModelRegistry,
    )

    assert len(registry) > 0


def test_builtin_models_are_registered() -> None:
    """
    Bootstrap discovers the built-in model packages.
    """

    registry = build_model_registry()

    assert registry.has_model("artwork")


def test_builtin_model_names() -> None:
    """
    The initial built-in model set is deterministic.
    """

    registry = build_model_registry()

    names = [model.name for model in registry.all_models()]

    assert names == [
        "artwork",
    ]


def test_artwork_model_metadata() -> None:
    """
    The artwork model exposes its basic identity.
    """

    registry = build_model_registry()

    model = registry.get_model(
        "artwork",
    )

    assert model.name == "artwork"
    assert model.title == "Artwork"
    assert model.defined_in is not None
    assert model.defined_in.endswith(".models.artwork")


# =========================================================
# Discovery resources
# =========================================================


def test_model_resource_directory_exists() -> None:
    """
    The model discovery resource directory exists.
    """

    assert RESOURCE_DIR.exists()
    assert RESOURCE_DIR.is_dir()


def test_model_packages_exist() -> None:
    """
    The initial model implementation packages exist.
    """

    assert (RESOURCE_DIR / "artwork").is_dir()


# =========================================================
# Registry independence
# =========================================================


def test_bootstrap_returns_independent_registries() -> None:
    """
    Each bootstrap call creates a new registry.

    Model registration therefore does not depend on global mutable
    registry state.
    """

    first = build_model_registry()
    second = build_model_registry()

    assert first is not second

    assert first.get_model("artwork") is second.get_model("artwork")
