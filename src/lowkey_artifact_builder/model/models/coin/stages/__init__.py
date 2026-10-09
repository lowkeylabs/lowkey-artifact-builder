"""
Coin stage implementations.
"""
# File: src/lowkey_artifact_builder/model/models/coin/stages/__init__.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from lowkey_artifact_builder.engine.registry import StageRegistry

from . import compose, package


def register_stage_implementations(
    registry: StageRegistry,
) -> None:
    """
    Register executable Coin stage implementations.
    """

    registry.register(
        "coin",
        "compose",
        compose.execute,
    )

    registry.register(
        "coin",
        "package",
        package.execute,
    )


__all__ = [
    "compose",
    "package",
    "register_stage_implementations",
]
