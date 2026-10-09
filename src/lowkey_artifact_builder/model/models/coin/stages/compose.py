"""
Compose two packaged Shape Products into one physical Coin.
"""
# File: src/lowkey_artifact_builder/model/models/coin/stages/compose.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from lowkey_artifact_builder.engine import StageContext
from lowkey_artifact_builder.formats.threemf import read_metadata

# =========================================================
# Compatibility
# =========================================================


def _validate_face_b(
    context: StageContext,
) -> None:
    """
    Validate that Face B is a compatible packaged Shape Product.

    Face B must already use inlaid Shape dimensionalization. Coin consumes
    this producer-owned compatibility information from metadata embedded in
    the packaged Shape 3MF and does not reopen Shape configuration or
    regenerate the Shape.
    """

    face_b = context.input(
        "faceB",
    )

    metadata = read_metadata(
        face_b,
    )

    raise_style = metadata.get(
        "raise_style",
    )

    if raise_style != "inlaid":
        raise ValueError("Coin Face B must use inlaid Shape dimensionalization.")


# =========================================================
# Stage execution
# =========================================================


def execute(
    context: StageContext,
) -> None:
    """
    Compose two packaged Shape Products into one physical Coin.

    Physical composition is introduced incrementally. The current boundary
    validates compatibility required before a Coin manufacturing Product may
    be produced.
    """

    _validate_face_b(
        context,
    )
