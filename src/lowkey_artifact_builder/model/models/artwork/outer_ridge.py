"""
Artwork Outer Ridge geometry.

This module owns Artwork-specific geometry used to reserve physical space
for a participating standalone Outer Ridge Feature.

Outer Ridge width is measured against the size-controlling physical Artwork
extent. The Artwork proper is uniformly scaled in X and Y to fit inside the
remaining extent, preserving its aspect ratio and registration.
"""
# File: src/lowkey_artifact_builder/model/models/artwork/outer_ridge.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations


def artwork_scale_for_outer_ridge(
    *,
    artwork_size: float,
    outer_ridge_width: float,
) -> float:
    """
    Return the uniform X/Y scale reserved for Artwork inside an Outer Ridge.

    ``artwork_size`` is the size-controlling physical extent before the
    Outer Ridge reserves space around its perimeter.

    ``outer_ridge_width`` is reserved on both sides of that extent.
    """

    inner_size = artwork_size - (2.0 * outer_ridge_width)

    return inner_size / artwork_size


__all__ = [
    "artwork_scale_for_outer_ridge",
]
