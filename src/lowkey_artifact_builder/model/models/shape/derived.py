"""
Derived configuration values for the shape model.

Derived values are calculated from resolved artifact configuration.
They are not stored in parameters.toml.

Each derivation receives the artifact Resolver and may consume values
from any resolved configuration scope.

Explicitly configured values take precedence over derivations.
"""
# File: src/lowkey_artifact_builder/model/models/shape/derived.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lowkey_artifact_builder.config import Resolver


# =========================================================
# Derivations
# =========================================================


def derive_shape_outer_ridge_color(
    resolver: Resolver,
) -> str:
    """
    Derive the outer-ridge color from the resolved base color.

    By default, the outer ridge uses the same semantic printing color
    as the Shape base.

    Because the base color is resolved through the artifact Resolver,
    workspace or artifact overrides of shape_base_color are reflected
    in the derived ridge color.

    An explicitly configured shape_outer_ridge_color value overrides
    this derivation through normal configuration resolution.
    """

    shape_base_color = resolver(
        "shape_base_color",
    )

    if (
        not isinstance(
            shape_base_color,
            str,
        )
        or not shape_base_color.strip()
    ):
        raise ValueError("shape_base_color must be a non-empty color name.")

    return shape_base_color.strip()


# =========================================================
# Registry
# =========================================================


DERIVED = {
    "shape_outer_ridge_color": derive_shape_outer_ridge_color,
}


# =========================================================
# Exports
# =========================================================


__all__ = [
    "DERIVED",
    "derive_shape_outer_ridge_color",
]
