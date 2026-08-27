"""
Stage implementations for the Shape model.

This package connects declarative Shape stage identities to their executable
implementations.

Stage implementations receive a StageContext from the build engine and use
resolved values and product paths supplied by that context.
"""
# File: src/lowkey_artifact_builder/model/models/shape/stages/__init__.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import Protocol

from .compose import execute as execute_compose
from .structure import execute as execute_structure

# =========================================================
# Registration protocol
# =========================================================


class StageImplementationRegistry(
    Protocol,
):
    """
    Minimal registry interface required by Shape stages.

    The concrete registry belongs to the build engine. This package depends
    only on the operation required to register executable stage
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
    Register executable implementations for the Shape workflow.
    """

    registry.register(
        "shape",
        "structure",
        execute_structure,
    )

    registry.register(
        "shape",
        "compose",
        execute_compose,
    )


__all__ = [
    "register_stage_implementations",
]
