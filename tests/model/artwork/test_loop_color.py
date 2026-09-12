"""
Tests for Artwork Loop color semantics.

Loop color may be configured explicitly. Otherwise its effective value is
selected by Artwork-owned color policy from Registered Artwork.
"""
# File: tests/model/artwork/test_loop_color.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path

import pytest

from lowkey_artifact_builder.config import (
    get_resolver,
    write_artifact_config,
)
from lowkey_artifact_builder.model.models.artwork.loop_color import (
    resolve_loop_color,
)
from lowkey_artifact_builder.model.models.artwork.stages.extrude import (
    VectorLayer,
    VectorManifest,
)

pytestmark = pytest.mark.slow


def _resolver_with_parameters(
    tmp_path: Path,
    parameters: dict[str, object],
):
    """
    Return an ordinary Artwork Realization resolver with parameter overrides.
    """

    write_artifact_config(
        "example",
        {
            "realizations": {
                "custom": {
                    "model": "artwork",
                    "variant": "default",
                    "parameters": parameters,
                },
            },
        },
        project_root=tmp_path,
    )

    return get_resolver(
        "example",
        realization="custom",
        project_root=tmp_path,
    )


def _write_rect(
    path: Path,
    *,
    x: float,
    y: float,
    width: float,
    height: float,
) -> None:
    """
    Write one simple SVG rectangle for attachment-color inspection.
    """

    path.write_text(
        f"""\
<svg xmlns="http://www.w3.org/2000/svg"
     width="100"
     height="100"
     viewBox="0 0 100 100">
  <rect
      x="{x}"
      y="{y}"
      width="{width}"
      height="{height}"
      fill="#000000" />
</svg>
""",
        encoding="utf-8",
    )


def _vector_manifest(
    tmp_path: Path,
) -> VectorManifest:
    """
    Return Registered Artwork whose cardinal attachment colors differ.

    The envelope occupies 0..100 in both axes.

    Red occupies the top attachment axis.
    Green occupies the right attachment axis.
    Blue occupies the bottom attachment axis.
    Black occupies the left attachment axis.
    """

    envelope = tmp_path / "envelope.svg"
    top = tmp_path / "top.svg"
    right = tmp_path / "right.svg"
    bottom = tmp_path / "bottom.svg"
    left = tmp_path / "left.svg"

    _write_rect(
        envelope,
        x=0,
        y=0,
        width=100,
        height=100,
    )

    _write_rect(
        top,
        x=45,
        y=0,
        width=10,
        height=20,
    )

    _write_rect(
        right,
        x=80,
        y=45,
        width=20,
        height=10,
    )

    _write_rect(
        bottom,
        x=45,
        y=80,
        width=10,
        height=20,
    )

    _write_rect(
        left,
        x=0,
        y=45,
        width=20,
        height=10,
    )

    return VectorManifest(
        registered_extent=100,
        envelope=envelope,
        layers=(
            VectorLayer(
                index=1,
                path=top,
                artifact_color_index=1,
                artifact_color=(255, 0, 0),
                printer_color_name="red",
                printer_color=(255, 0, 0),
                distance=0.0,
            ),
            VectorLayer(
                index=2,
                path=right,
                artifact_color_index=2,
                artifact_color=(0, 255, 0),
                printer_color_name="green",
                printer_color=(0, 255, 0),
                distance=0.0,
            ),
            VectorLayer(
                index=3,
                path=bottom,
                artifact_color_index=3,
                artifact_color=(0, 0, 255),
                printer_color_name="blue",
                printer_color=(0, 0, 255),
                distance=0.0,
            ),
            VectorLayer(
                index=4,
                path=left,
                artifact_color_index=4,
                artifact_color=(0, 0, 0),
                printer_color_name="black",
                printer_color=(0, 0, 0),
                distance=0.0,
            ),
        ),
    )


def test_explicit_loop_color_is_authoritative(
    tmp_path: Path,
) -> None:
    """
    Explicit Loop color overrides attachment-derived color policy.
    """

    resolver = _resolver_with_parameters(
        tmp_path,
        {
            "loop_color": "black",
            "loop_position": 0,
        },
    )

    artwork = _vector_manifest(
        tmp_path,
    )

    assert (
        resolve_loop_color(
            artwork,
            resolver=resolver,
        )
        == "black"
    )


@pytest.mark.parametrize(
    ("position", "expected"),
    (
        (0, "red"),
        (90, "green"),
        (180, "blue"),
        (-90, "black"),
    ),
)
def test_loop_color_defaults_to_attachment_color(
    tmp_path: Path,
    position: int,
    expected: str,
) -> None:
    """
    Without explicit Loop color, color follows the effective attachment point.
    """

    resolver = _resolver_with_parameters(
        tmp_path,
        {
            "loop_position": position,
        },
    )

    artwork = _vector_manifest(
        tmp_path,
    )

    assert (
        resolve_loop_color(
            artwork,
            resolver=resolver,
        )
        == expected
    )


def test_changing_loop_position_changes_derived_color(
    tmp_path: Path,
) -> None:
    """
    Attachment-derived Loop color follows the effective Loop position.
    """

    artwork = _vector_manifest(
        tmp_path,
    )

    top_resolver = _resolver_with_parameters(
        tmp_path,
        {
            "loop_position": 0,
        },
    )

    assert (
        resolve_loop_color(
            artwork,
            resolver=top_resolver,
        )
        == "red"
    )

    right_resolver = _resolver_with_parameters(
        tmp_path,
        {
            "loop_position": 90,
        },
    )

    assert (
        resolve_loop_color(
            artwork,
            resolver=right_resolver,
        )
        == "green"
    )


def test_attachment_derived_loop_color_preserves_semantic_identity(
    tmp_path: Path,
) -> None:
    """
    Loop color is the semantic printer-color identity, not an RGB value.
    """

    resolver = _resolver_with_parameters(
        tmp_path,
        {
            "loop_position": 180,
        },
    )

    artwork = _vector_manifest(
        tmp_path,
    )

    color = resolve_loop_color(
        artwork,
        resolver=resolver,
    )

    assert color == "blue"
    assert isinstance(color, str)


def test_attachment_derived_loop_color_is_deterministic(
    tmp_path: Path,
) -> None:
    """
    Repeated resolution against identical inputs produces the same color.
    """

    resolver = _resolver_with_parameters(
        tmp_path,
        {
            "loop_position": -90,
        },
    )

    artwork = _vector_manifest(
        tmp_path,
    )

    first = resolve_loop_color(
        artwork,
        resolver=resolver,
    )

    second = resolve_loop_color(
        artwork,
        resolver=resolver,
    )

    assert first == second == "black"
