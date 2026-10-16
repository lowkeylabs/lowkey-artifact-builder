"""
Laser stage implementations.
"""
# File: src/lowkey_artifact_builder/model/models/laser/stages/__init__.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from lowkey_artifact_builder.engine.registry import StageRegistry

from . import package


def register_stage_implementations(
    registry: StageRegistry,
) -> None:
    registry.register(
        "laser",
        "package",
        package.execute,
    )


__all__ = [
    "package",
    "register_stage_implementations",
]
