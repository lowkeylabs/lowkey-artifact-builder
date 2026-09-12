"""
Tests for Artwork attachment-color selection.

Attachment-color selection is Artwork-owned Model policy. Given a
cardinal attachment position, Artwork determines the semantic physical
printer color belonging to the Artwork at that envelope attachment
point.
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
    color: str,
) -> VectorLayer:
    """
    Return one registered Artwork color layer.
    """

    return VectorLayer(
        index=index,
        path=path,
        artifact_color_index=index,
        artifact_color=(index, index, index),
        printer_color_name=color,
        printer_color=(index, index, index),
        distance=0.0,
    )


def _artwork(
    tmp_path: Path,
) -> VectorManifest:
    """
    Return registered Artwork with a different color at each cardinal edge.

    The occupied envelope is the square:

        x = 20 .. 80
        y = 20 .. 80

    Color regions occupy strips at its four cardinal edges while a fifth
    color occupies the center.
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
            _layer(
                top,
                index=1,
                color="top-color",
            ),
            _layer(
                right,
                index=2,
                color="right-color",
            ),
            _layer(
                bottom,
                index=3,
                color="bottom-color",
            ),
            _layer(
                left,
                index=4,
                color="left-color",
            ),
            _layer(
                center,
                index=5,
                color="center-color",
            ),
        ),
    )


# =========================================================
# Cardinal attachment tests
# =========================================================


@pytest.mark.parametrize(
    ("position", "expected"),
    [
        (0, "top-color"),
        (90, "right-color"),
        (180, "bottom-color"),
        (-90, "left-color"),
    ],
)
def test_attachment_selects_artwork_color_at_cardinal_edge(
    tmp_path: Path,
    position: int,
    expected: str,
) -> None:
    """
    Each cardinal attachment selects the Artwork color at that edge.
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
    Boundary ambiguity resolves to the nearest occupied Artwork color inward.

    The top envelope boundary is y=20. No color layer contains the exact
    cardinal boundary point at x=50. The first occupied color encountered
    inward along the same axis is the inset strip.
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
            _layer(
                inset,
                index=1,
                color="nearest-color",
            ),
            _layer(
                center,
                index=2,
                color="center-color",
            ),
        ),
    )

    assert (
        attachment.select_attachment_color(
            artwork,
            position=0,
        )
        == "nearest-color"
    )


# =========================================================
# Semantic identity
# =========================================================


def test_attachment_returns_semantic_printer_color_identity(
    tmp_path: Path,
) -> None:
    """
    Attachment selection preserves semantic physical printer color identity.

    Selection does not replace the printer color identity with Artifact RGB
    or printer RGB.
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
                printer_color_name="physical-gold",
                printer_color=(200, 150, 40),
                distance=12.5,
            ),
        ),
    )

    result = attachment.select_attachment_color(
        artwork,
        position=0,
    )

    assert result == "physical-gold"


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
        "right-color",
    }
