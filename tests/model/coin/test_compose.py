"""Tests for Coin physical composition."""
# File: tests/model/coin/test_compose.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from pathlib import Path
from unittest.mock import Mock

import pytest

from lowkey_artifact_builder.colors import PaletteColor
from lowkey_artifact_builder.engine import StageContext
from lowkey_artifact_builder.formats.threemf import (
    Component,
    Mesh,
    write,
)
from lowkey_artifact_builder.model.models.coin.stages import compose

# =========================================================
# Helpers
# =========================================================


def _mesh() -> Mesh:
    """Return representative physical Face geometry."""

    return Mesh(
        vertices=(
            (0.0, 0.0, 0.0),
            (1.0, 0.0, 0.0),
            (0.0, 1.0, 0.0),
        ),
        triangles=((0, 1, 2),),
    )


def _write_shape(
    path: Path,
    *,
    raise_style: str,
) -> None:
    """Write one complete packaged Shape Product."""

    write(
        (
            Component(
                name="base",
                mesh=_mesh(),
                color=PaletteColor(
                    name="white",
                    rgb=(255, 255, 255),
                ),
            ),
        ),
        path,
        metadata={
            "raise_style": raise_style,
        },
    )


# =========================================================
# Face compatibility
# =========================================================


def test_coin_rejects_non_inlaid_face_b(
    tmp_path: Path,
) -> None:
    """
    Coin rejects a packaged Face B that is not inlaid.

    Compatibility is determined from persistent metadata embedded in the
    packaged Shape Product. Coin does not reopen Shape configuration or
    regenerate an incompatible Face.
    """

    face_a = tmp_path / "face-a.3mf"
    face_b = tmp_path / "face-b.3mf"

    _write_shape(
        face_a,
        raise_style="raised",
    )
    _write_shape(
        face_b,
        raise_style="raised",
    )

    context = Mock(
        spec=StageContext,
    )

    context.input.side_effect = {
        "faceA": face_a,
        "faceB": face_b,
    }.__getitem__

    with pytest.raises(
        ValueError,
        match="Face B.*inlaid",
    ):
        compose.execute(
            context,
        )
