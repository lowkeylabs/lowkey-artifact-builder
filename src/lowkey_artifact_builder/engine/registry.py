"""
Stage implementation registry.

The engine registry maps declarative model stages to their executable
implementations.

Model specifications describe what may be built. The stage registry
associates those declarations with the callables that perform the work.

Registration is intentionally separate from discovery. Model packages
may register implementations directly today. A future plugin subsystem
may discover extensions and register their implementations through the
same interface without changing the build engine.

The registry does not construct models, resolve configuration, resolve
filesystem paths, execute stages, or discover plugins.
"""

from __future__ import annotations

from collections.abc import Callable

from .specs import StageContext

# =========================================================
# Types
# =========================================================


StageImplementation = Callable[
    [StageContext],
    None,
]


# =========================================================
# Errors
# =========================================================


class StageRegistryError(Exception):
    """
    Base exception for stage implementation registry errors.
    """


class StageImplementationNotFoundError(StageRegistryError):
    """
    Raised when a stage implementation is not registered.
    """


class DuplicateStageImplementationError(StageRegistryError):
    """
    Raised when a stage implementation is registered more than once.
    """


# =========================================================
# Registry
# =========================================================


class StageRegistry:
    """
    Registry of executable model stage implementations.

    Implementations are identified by model name and stage name.

    The registry deliberately knows only these stable identifiers and
    the callable implementing the stage. It does not depend on model
    package layout or on how implementations are discovered.

    This permits model packages and future feature plugins to contribute
    stage implementations through the same registration interface.
    """

    def __init__(
        self,
    ) -> None:
        self._implementations: dict[
            tuple[str, str],
            StageImplementation,
        ] = {}

    # =====================================================
    # Registration
    # =====================================================

    def register(
        self,
        model_name: str,
        stage_name: str,
        implementation: StageImplementation,
    ) -> None:
        """
        Register an implementation for a model stage.

        A model/stage pair may have only one implementation.
        """

        key = (
            model_name,
            stage_name,
        )

        if key in self._implementations:
            raise DuplicateStageImplementationError(
                f"Stage implementation already registered: {model_name}.{stage_name}"
            )

        self._implementations[key] = implementation

    # =====================================================
    # Lookup
    # =====================================================

    def get(
        self,
        model_name: str,
        stage_name: str,
    ) -> StageImplementation:
        """
        Return the implementation registered for a model stage.
        """

        key = (
            model_name,
            stage_name,
        )

        try:
            return self._implementations[key]

        except KeyError as exc:
            raise StageImplementationNotFoundError(
                f"Stage implementation not found: {model_name}.{stage_name}"
            ) from exc

    def has(
        self,
        model_name: str,
        stage_name: str,
    ) -> bool:
        """
        Return whether an implementation is registered for a model
        stage.
        """

        return (
            model_name,
            stage_name,
        ) in self._implementations

    def all(
        self,
    ) -> list[
        tuple[
            str,
            str,
            StageImplementation,
        ]
    ]:
        """
        Return all registered implementations in deterministic order.

        Each result contains:

            model name
            stage name
            implementation
        """

        return [
            (
                model_name,
                stage_name,
                implementation,
            )
            for (
                model_name,
                stage_name,
            ), implementation in sorted(
                self._implementations.items(),
                key=lambda item: item[0],
            )
        ]

    def __len__(
        self,
    ) -> int:
        """
        Return the number of registered stage implementations.
        """

        return len(self._implementations)


__all__ = [
    "DuplicateStageImplementationError",
    "StageImplementation",
    "StageImplementationNotFoundError",
    "StageRegistry",
    "StageRegistryError",
]
