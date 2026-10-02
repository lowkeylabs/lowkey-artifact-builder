"""
Shared model-independent planar geometry primitives.

This module contains geometric value objects that are not owned by any
particular artifact model.
"""
# File: src/lowkey_artifact_builder/model/geometry.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from dataclasses import dataclass


@dataclass(
    frozen=True,
    slots=True,
)
class Bounds:
    """
    Axis-aligned physical planar bounds.
    """

    min_x: float
    min_y: float
    max_x: float
    max_y: float

    @property
    def center_x(
        self,
    ) -> float:
        """
        Return the horizontal center of the bounds.
        """

        return (self.min_x + self.max_x) / 2.0

    @property
    def center_y(
        self,
    ) -> float:
        """
        Return the vertical center of the bounds.
        """

        return (self.min_y + self.max_y) / 2.0


__all__ = [
    "Bounds",
]
