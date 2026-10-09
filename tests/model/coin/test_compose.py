"""Tests for Coin physical composition."""
# File: tests/model/coin/test_compose.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

import json
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
    boundary: dict[str, object] | None = None,
    hole: dict[str, object] | None = None,
    loop: dict[str, object] | None = None,
) -> None:
    """Write one complete packaged Shape Product."""

    if boundary is None:
        boundary = {
            "kind": "circle",
            "center": [0.0, 0.0],
            "radius": 50.0,
        }

    compatibility = {
        "boundary": boundary,
        "hole": hole,
        "loop": loop,
    }

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
            "shape_compatibility": json.dumps(
                compatibility,
                separators=(",", ":"),
                sort_keys=True,
            ),
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


def test_coin_accepts_compatible_packaged_faces(
    tmp_path: Path,
) -> None:
    """
    Coin accepts compatible packaged Faces when Face B is inlaid.

    Compatibility is determined from the packaged Shape Products rather
    than producer Artifact or Realization identity. Successful composition
    publishes the declared physical Coin Product.
    """

    face_a = tmp_path / "face-a.3mf"
    face_b = tmp_path / "face-b.3mf"
    physical = tmp_path / "physical.json"

    _write_shape(
        face_a,
        raise_style="raised",
    )
    _write_shape(
        face_b,
        raise_style="inlaid",
    )

    context = Mock(
        spec=StageContext,
    )

    context.input.side_effect = {
        "faceA": face_a,
        "faceB": face_b,
    }.__getitem__

    context.output.side_effect = {
        "physical": physical,
    }.__getitem__

    compose.execute(
        context,
    )

    assert physical.is_file()


def test_coin_rejects_structurally_incompatible_faces(
    tmp_path: Path,
) -> None:
    """
    Coin rejects Faces whose physical mating boundaries do not coincide.

    Compatibility is determined from producer-owned physical metadata embedded
    in the packaged Shape Products rather than reconstructed from their meshes.
    """

    face_a = tmp_path / "face-a.3mf"
    face_b = tmp_path / "face-b.3mf"

    _write_shape(
        face_a,
        raise_style="raised",
    )
    _write_shape(
        face_b,
        raise_style="inlaid",
        boundary={
            "kind": "circle",
            "center": [0.0, 0.0],
            "radius": 45.0,
        },
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
        match="boundar",
    ):
        compose.execute(
            context,
        )


@pytest.mark.parametrize(
    (
        "feature",
        "face_a_geometry",
        "face_b_geometry",
    ),
    [
        (
            "hole",
            {
                "center": [47.1, 0.0],
                "radius": 2.5,
            },
            None,
        ),
        (
            "loop",
            {
                "center": [52.0, 0.0],
                "inner_radius": 2.0,
                "outer_radius": 3.5,
            },
            {
                "center": [52.0, 0.0],
                "inner_radius": 2.0,
                "outer_radius": 4.0,
            },
        ),
    ],
)
def test_coin_rejects_incompatible_bilateral_features(
    tmp_path: Path,
    feature: str,
    face_a_geometry: dict[str, object] | None,
    face_b_geometry: dict[str, object] | None,
) -> None:
    """
    Coin requires bilateral Hole and Loop compatibility between its Faces.

    Participation and resolved physical geometry come from the packaged Shape
    compatibility contract rather than inference from component meshes.
    """

    face_a = tmp_path / "face-a.3mf"
    face_b = tmp_path / "face-b.3mf"

    face_a_features: dict[str, dict[str, object] | None] = {
        "hole": None,
        "loop": None,
    }

    face_b_features: dict[str, dict[str, object] | None] = {
        "hole": None,
        "loop": None,
    }

    face_a_features[feature] = face_a_geometry
    face_b_features[feature] = face_b_geometry

    _write_shape(
        face_a,
        raise_style="raised",
        hole=face_a_features["hole"],
        loop=face_a_features["loop"],
    )
    _write_shape(
        face_b,
        raise_style="inlaid",
        hole=face_b_features["hole"],
        loop=face_b_features["loop"],
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
        match=feature,
    ):
        compose.execute(
            context,
        )
