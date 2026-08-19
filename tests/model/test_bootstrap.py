"""
Tests for model subsystem bootstrap and discovery.
"""

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

    assert registry.has_model("circular")
    assert registry.has_model("logo")


def test_builtin_model_names() -> None:
    """
    The initial built-in model set is deterministic.
    """

    registry = build_model_registry()

    names = [model.name for model in registry.all_models()]

    assert names == [
        "circular",
        "logo",
    ]


def test_circular_model_metadata() -> None:
    """
    The circular model exposes its basic identity.
    """

    registry = build_model_registry()

    model = registry.get_model(
        "circular",
    )

    assert model.name == "circular"
    assert model.title == "Circular"
    assert model.defined_in is not None
    assert model.defined_in.endswith(".models.circular")


def test_logo_model_metadata() -> None:
    """
    The logo model exposes its basic identity.
    """

    registry = build_model_registry()

    model = registry.get_model(
        "logo",
    )

    assert model.name == "logo"
    assert model.title == "Logo"
    assert model.defined_in is not None
    assert model.defined_in.endswith(".models.logo")


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

    assert (RESOURCE_DIR / "circular").is_dir()

    assert (RESOURCE_DIR / "logo").is_dir()


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

    assert first.get_model("circular") is second.get_model("circular")
