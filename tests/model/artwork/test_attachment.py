"""
Tests for Artwork attachment-layer selection.

Attachment selection is Artwork-owned geometric policy. Given a cardinal
attachment position, Artwork determines which registered Artifact-color
layer occupies the Artwork at that envelope attachment point.

Physical printer-color assignment is not part of registered Artwork and
is resolved downstream during packaging.
"""
# File: tests/model/artwork/test_attachment.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path

import pytest

from lowkey_artifact_builder.model.models.artwork import attachment
from lowkey_artifact_builder.model.models.artwork.stages.extrude import (
    VectorLayer,
    VectorManifest,
)

pytestmark = pytest.mark.slow


# =========================================================
# Test support
# =========================================================


def _write_svg(
    path: Path,
    geometry: str,
) -> None:
    """
    Write registered SVG geometry in a common 100 x 100 coordinate system.
    """

    path.write_text(
        (
            '<svg xmlns="http://www.w3.org/2000/svg" '
            'width="100" height="100" viewBox="0 0 100 100">'
            f"{geometry}"
            "</svg>"
        ),
        encoding="utf-8",
    )


def _layer(
    path: Path,
    *,
    index: int,
) -> VectorLayer:
    """
    Return one registered Artwork color layer.
    """

    return VectorLayer(
        index=index,
        path=path,
        artifact_color_index=index,
        artifact_color=(index, index, index),
    )


def _artwork(
    tmp_path: Path,
) -> VectorManifest:
    """
    Return registered Artwork with a different layer at each cardinal edge.

    The occupied envelope is the square:

        x = 20 .. 80
        y = 20 .. 80

    Artifact-color regions occupy strips at its four cardinal edges while
    a fifth Artifact color occupies the center.
    """

    envelope = tmp_path / "envelope.svg"

    _write_svg(
        envelope,
        '<rect x="20" y="20" width="60" height="60"/>',
    )

    top = tmp_path / "top.svg"
    right = tmp_path / "right.svg"
    bottom = tmp_path / "bottom.svg"
    left = tmp_path / "left.svg"
    center = tmp_path / "center.svg"

    _write_svg(
        top,
        '<rect x="30" y="20" width="40" height="10"/>',
    )
    _write_svg(
        right,
        '<rect x="70" y="30" width="10" height="40"/>',
    )
    _write_svg(
        bottom,
        '<rect x="30" y="70" width="40" height="10"/>',
    )
    _write_svg(
        left,
        '<rect x="20" y="30" width="10" height="40"/>',
    )
    _write_svg(
        center,
        '<rect x="30" y="30" width="40" height="40"/>',
    )

    return VectorManifest(
        registered_extent=100,
        envelope=envelope,
        layers=(
            _layer(top, index=1),
            _layer(right, index=2),
            _layer(bottom, index=3),
            _layer(left, index=4),
            _layer(center, index=5),
        ),
    )


# =========================================================
# Cardinal attachment tests
# =========================================================


@pytest.mark.parametrize(
    ("position", "expected"),
    [
        (0, 1),
        (90, 2),
        (180, 3),
        (-90, 4),
    ],
)
def test_attachment_selects_artifact_color_at_cardinal_edge(
    tmp_path: Path,
    position: int,
    expected: int,
) -> None:
    """
    Each cardinal attachment selects the Artifact-color layer at that edge.
    """

    artwork = _artwork(
        tmp_path,
    )

    assert (
        attachment.select_attachment_color(
            artwork,
            position=position,
        )
        == expected
    )


# =========================================================
# Boundary ambiguity
# =========================================================


def test_attachment_selects_nearest_occupied_color_inward_from_boundary(
    tmp_path: Path,
) -> None:
    """
    Boundary ambiguity resolves to the nearest occupied Artifact-color layer.

    The top envelope boundary is y=20. No color layer contains the exact
    cardinal boundary point at x=50. The first occupied color encountered
    inward along the same axis is the inset layer.
    """

    envelope = tmp_path / "envelope.svg"
    inset = tmp_path / "inset.svg"
    center = tmp_path / "center.svg"

    _write_svg(
        envelope,
        '<rect x="20" y="20" width="60" height="60"/>',
    )

    _write_svg(
        inset,
        '<rect x="40" y="21" width="20" height="9"/>',
    )

    _write_svg(
        center,
        '<rect x="30" y="30" width="40" height="40"/>',
    )

    artwork = VectorManifest(
        registered_extent=100,
        envelope=envelope,
        layers=(
            _layer(inset, index=7),
            _layer(center, index=8),
        ),
    )

    assert (
        attachment.select_attachment_color(
            artwork,
            position=0,
        )
        == 7
    )


# =========================================================
# Logical identity
# =========================================================


def test_attachment_returns_artifact_color_index(
    tmp_path: Path,
) -> None:
    """
    Attachment selection returns logical Artifact-color identity.

    Physical printer color and RGB are downstream packaging concerns.
    """

    envelope = tmp_path / "envelope.svg"
    layer = tmp_path / "layer.svg"

    _write_svg(
        envelope,
        '<rect x="20" y="20" width="60" height="60"/>',
    )

    _write_svg(
        layer,
        '<rect x="20" y="20" width="60" height="60"/>',
    )

    artwork = VectorManifest(
        registered_extent=100,
        envelope=envelope,
        layers=(
            VectorLayer(
                index=1,
                path=layer,
                artifact_color_index=7,
                artifact_color=(10, 20, 30),
            ),
        ),
    )

    result = attachment.select_attachment_color(
        artwork,
        position=0,
    )

    assert result == 7


# =========================================================
# Determinism
# =========================================================


def test_attachment_color_selection_is_deterministic(
    tmp_path: Path,
) -> None:
    """
    Repeated selection from identical registered Artwork gives one result.
    """

    artwork = _artwork(
        tmp_path,
    )

    results = {
        attachment.select_attachment_color(
            artwork,
            position=90,
        )
        for _ in range(10)
    }

    assert results == {
        2,
    }
