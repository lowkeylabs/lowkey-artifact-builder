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

from dataclasses import dataclass


@dataclass(
    frozen=True,
    slots=True,
)
class OuterRidgeGeometry:
    """
    Dimensional relationship between the full Artwork envelope and the
    uniformly scaled Artwork proper inside a participating Outer Ridge.
    """

    outer_width: float
    outer_height: float
    inner_width: float
    inner_height: float
    inner_offset_x: float
    inner_offset_y: float


def create_outer_ridge_geometry(
    *,
    envelope_width: float,
    envelope_height: float,
    artwork_size: float,
    outer_ridge_width: float,
) -> OuterRidgeGeometry:
    """
    Create dimensional Outer Ridge geometry for a standalone Artwork.

    The outer envelope retains the full dimensionalized Artwork extent.
    Artwork proper is uniformly scaled about the envelope center to reserve
    the configured Outer Ridge width on the size-controlling extent.
    """

    scale = artwork_scale_for_outer_ridge(
        artwork_size=artwork_size,
        outer_ridge_width=outer_ridge_width,
    )

    inner_width = envelope_width * scale
    inner_height = envelope_height * scale

    return OuterRidgeGeometry(
        outer_width=envelope_width,
        outer_height=envelope_height,
        inner_width=inner_width,
        inner_height=inner_height,
        inner_offset_x=(envelope_width - inner_width) / 2.0,
        inner_offset_y=(envelope_height - inner_height) / 2.0,
    )


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
    "OuterRidgeGeometry",
    "artwork_scale_for_outer_ridge",
    "create_outer_ridge_geometry",
]
