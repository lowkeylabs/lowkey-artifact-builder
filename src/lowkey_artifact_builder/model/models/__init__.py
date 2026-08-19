"""
Model package discovery.

Discovers and registers all model packages contained in this directory.

Each public package in this directory represents an artifact model and
must export:

    register_models(registry)

Private packages whose names begin with an underscore are ignored.
"""

from __future__ import annotations

import importlib
import pkgutil
from pathlib import Path
from types import ModuleType

from lowkey_artifact_builder.model.registry import ModelRegistry

# =========================================================
# Package resources
# =========================================================


RESOURCE_DIR = Path(__file__).parent


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
    """

    modules: list[ModuleType] = []

    for module_info in sorted(
        pkgutil.iter_modules(
            [str(RESOURCE_DIR)],
        ),
        key=lambda item: item.name,
    ):
        #
        # Ignore private modules and packages.
        #

        if module_info.name.startswith("_"):
            continue

        #
        # Models must be packages.
        #

        if not module_info.ispkg:
            continue

        modules.append(
            importlib.import_module(
                f"{__name__}.{module_info.name}",
            )
        )

    return modules


# =========================================================
# Registration
# =========================================================


def register_all_models(
    registry: ModelRegistry,
) -> None:
    """
    Discover and register every model package.

    Every public package must provide a callable
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


__all__ = [
    "RESOURCE_DIR",
    "ModelDiscoveryError",
    "register_all_models",
]
