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

    Shape configuration validity is enforced separately by the model's
    configuration validators.
    """

    return resolver(
        "shape_base_color",
    )


def derive_shape_artwork_fill_color(
    resolver: Resolver,
) -> None:
    """
    Derive the default Artwork fill color.

    By default, Shape does not produce Artwork fill geometry.

    An explicitly configured shape_artwork_fill_color value overrides
    this derivation through normal configuration resolution.
    """

    del resolver

    return None


# =========================================================
# Registry
# =========================================================


DERIVED = {
    "shape_outer_ridge_color": derive_shape_outer_ridge_color,
    "shape_artwork_fill_color": derive_shape_artwork_fill_color,
}

# =========================================================
# Exports
# =========================================================


__all__ = [
    "DERIVED",
    "derive_shape_artwork_fill_color",
    "derive_shape_outer_ridge_color",
]
