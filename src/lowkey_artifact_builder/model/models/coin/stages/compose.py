"""
Compose two packaged Shape Products into one physical Coin.
"""
# File: src/lowkey_artifact_builder/model/models/coin/stages/compose.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from lowkey_artifact_builder.engine import StageContext
from lowkey_artifact_builder.formats.threemf import read_metadata

# =========================================================
# Compatibility
# =========================================================


def _load_shape_metadata(
    face: Path,
) -> tuple[
    dict[str, str],
    dict[str, Any],
]:
    """
    Load persistent compatibility metadata from a packaged Shape Product.

    Packaged Shape metadata is authoritative for compatibility properties that
    cannot be recovered safely from component geometry, identity, or colors.
    """

    metadata = read_metadata(
        face,
    )

    serialized_compatibility = metadata.get(
        "shape_compatibility",
    )

    if serialized_compatibility is None:
        raise ValueError("Packaged Shape Product is missing Shape compatibility metadata.")

    try:
        compatibility = json.loads(
            serialized_compatibility,
        )
    except json.JSONDecodeError as exc:
        raise ValueError(
            "Packaged Shape Product contains invalid Shape compatibility metadata."
        ) from exc

    if not isinstance(
        compatibility,
        dict,
    ):
        raise ValueError("Packaged Shape Product contains invalid Shape compatibility metadata.")

    return (
        metadata,
        compatibility,
    )


def _validate_face_b(
    metadata: dict[str, str],
) -> None:
    """
    Validate Face B dimensionalization.

    Face B must already use inlaid Shape dimensionalization. Coin consumes
    this producer-owned information from the packaged Shape Product and does
    not reopen Shape configuration or regenerate the Shape.
    """

    raise_style = metadata.get(
        "raise_style",
    )

    if raise_style != "inlaid":
        raise ValueError("Coin Face B must use inlaid Shape dimensionalization.")


def _validate_compatibility(
    face_a: dict[str, Any],
    face_b: dict[str, Any],
) -> None:
    """
    Validate physical compatibility between the two packaged Faces.

    The structural mating boundary must coincide. Hole and Loop participation
    and resolved physical geometry must also agree bilaterally.
    """

    if face_a.get(
        "boundary",
    ) != face_b.get(
        "boundary",
    ):
        raise ValueError("Coin Face boundaries are incompatible.")

    if face_a.get(
        "hole",
    ) != face_b.get(
        "hole",
    ):
        raise ValueError("Coin Face hole geometry is incompatible.")

    if face_a.get(
        "loop",
    ) != face_b.get(
        "loop",
    ):
        raise ValueError("Coin Face loop geometry is incompatible.")


# =========================================================
# Stage execution
# =========================================================


def execute(
    context: StageContext,
) -> None:
    """
    Compose two packaged Shape Products into one physical Coin.

    Compatibility is determined entirely from producer-owned information
    persisted in the packaged Shape Products. Successful validation publishes
    the persistent physical Coin Product consumed by downstream composition
    and packaging work.
    """

    face_a = context.input(
        "faceA",
    )

    face_b = context.input(
        "faceB",
    )

    _, face_a_compatibility = _load_shape_metadata(
        face_a,
    )

    face_b_metadata, face_b_compatibility = _load_shape_metadata(
        face_b,
    )

    _validate_face_b(
        face_b_metadata,
    )

    _validate_compatibility(
        face_a_compatibility,
        face_b_compatibility,
    )

    physical = context.output(
        "physical",
    )

    physical.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    physical.write_text(
        json.dumps(
            {
                "faceA": str(
                    face_a,
                ),
                "faceB": str(
                    face_b,
                ),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
