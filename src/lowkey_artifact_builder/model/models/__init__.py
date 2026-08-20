"""
Model package discovery.

Discovers and registers all model packages contained in this directory.

Each public package in this directory represents an artifact model and
must export:

    register_models(registry)

A model package may additionally export:

    register_stage_implementations(registry)

to contribute executable stage implementations to the build engine.

Private packages whose names begin with an underscore are ignored.
"""

from __future__ import annotations

import importlib
import pkgutil
from pathlib import Path
from types import ModuleType
from typing import Protocol

from lowkey_artifact_builder.model.registry import ModelRegistry

# =========================================================
# Package resources
# =========================================================


RESOURCE_DIR = Path(__file__).parent


# =========================================================
# Registration protocols
# =========================================================


class StageImplementationRegistry(
    Protocol,
):
    """
    Minimal registry interface required by model packages.

    The concrete stage registry belongs to the build engine. Model
    discovery depends only on the registration operation required to
    contribute executable implementations.
    """

    def register(
        self,
        model_name: str,
        stage_name: str,
        implementation,
    ) -> None:
        """
        Register an executable implementation for a model stage.
        """

        ...


# =========================================================
# Exceptions
# =========================================================


class ModelDiscoveryError(Exception):
    """
    Raised when a discovered model package is invalid.
    """


# =========================================================
# Discovery
# =========================================================


def _discover_modules() -> list[ModuleType]:
    """
    Discover public model packages.

    Discovery is deterministic. Packages are returned in lexical order
    by package name.

    Private modules and packages are ignored. Public modules that are
    not packages are also ignored because artifact models are package
    scoped.
    """

    modules: list[ModuleType] = []

    for module_info in sorted(
        pkgutil.iter_modules(
            [str(RESOURCE_DIR)],
        ),
        key=lambda item: item.name,
    ):
        if module_info.name.startswith("_"):
            continue

        if not module_info.ispkg:
            continue

        modules.append(
            importlib.import_module(
                f"{__name__}.{module_info.name}",
            )
        )

    return modules


# =========================================================
# Model registration
# =========================================================


def register_all_models(
    registry: ModelRegistry,
) -> None:
    """
    Discover and register every model package.

    Every public model package must provide a callable
    register_models(registry) entry point.
    """

    for module in _discover_modules():
        register_fn = getattr(
            module,
            "register_models",
            None,
        )

        if register_fn is None:
            raise ModelDiscoveryError(
                f"Model package {module.__name__!r} does not define register_models()."
            )

        if not callable(register_fn):
            raise ModelDiscoveryError(
                f"Model package {module.__name__!r} "
                "defines register_models, but it is not callable."
            )

        register_fn(
            registry,
        )


# =========================================================
# Stage implementation registration
# =========================================================


def register_all_stage_implementations(
    registry: StageImplementationRegistry,
) -> None:
    """
    Discover and register executable model stage implementations.

    Stage implementation registration is optional for a model package.

    A package that provides a callable
    register_stage_implementations(registry) entry point contributes
    its implementations to the supplied registry.

    Packages without that entry point are skipped. This allows models
    to exist declaratively before executable implementations are
    available and provides a natural extension point for future model
    features and plugins.

    If the entry point exists but is not callable, discovery fails
    rather than silently ignoring an invalid model package.
    """

    for module in _discover_modules():
        register_fn = getattr(
            module,
            "register_stage_implementations",
            None,
        )

        if register_fn is None:
            continue

        if not callable(register_fn):
            raise ModelDiscoveryError(
                f"Model package {module.__name__!r} "
                "defines register_stage_implementations, "
                "but it is not callable."
            )

        register_fn(
            registry,
        )


__all__ = [
    "RESOURCE_DIR",
    "ModelDiscoveryError",
    "register_all_models",
    "register_all_stage_implementations",
]
