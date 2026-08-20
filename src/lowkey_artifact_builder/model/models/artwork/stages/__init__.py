"""
Artwork stage implementations.

This package contains the executable implementations of the artwork
model workflow.

The artwork model declares its workflow independently of these
implementations. This package connects the declarative stage names to
the functions that perform the corresponding work.

Stage implementations receive a StageContext from the build engine.
They should use the paths and resolved values provided by that context
rather than resolve configuration, interpret project layout, or
construct artifact filesystem paths themselves.

Future artwork features and plugins may contribute additional stage
implementations through the same registration interface.
"""

from __future__ import annotations

from typing import Protocol

from .extrude import execute as execute_extrude
from .package import execute as execute_package
from .prepare import execute as execute_prepare
from .raster import execute as execute_raster
from .vector import execute as execute_vector

# =========================================================
# Registration protocol
# =========================================================


class StageImplementationRegistry(
    Protocol,
):
    """
    Minimal registry interface required by artwork stages.

    The concrete registry belongs to the build engine. This package
    depends only on the operation required to register executable stage
    implementations.
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
# Registration
# =========================================================


def register_stage_implementations(
    registry: StageImplementationRegistry,
) -> None:
    """
    Register executable implementations for the artwork workflow.
    """

    registry.register(
        "artwork",
        "prepare",
        execute_prepare,
    )

    registry.register(
        "artwork",
        "raster",
        execute_raster,
    )

    registry.register(
        "artwork",
        "vector",
        execute_vector,
    )

    registry.register(
        "artwork",
        "extrude",
        execute_extrude,
    )

    registry.register(
        "artwork",
        "package",
        execute_package,
    )


__all__ = [
    "register_stage_implementations",
]
