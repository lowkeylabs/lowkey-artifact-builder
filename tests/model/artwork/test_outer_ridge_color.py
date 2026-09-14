"""
Tests for Artwork Outer Ridge color semantics.

Outer Ridge color may be configured explicitly. Otherwise its effective
physical color identity is selected by Artwork-owned attachment-color policy
from Registered Artwork at the effective loop_position.
"""
# File: tests/model/artwork/test_outer_ridge_color.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path

import pytest

from lowkey_artifact_builder.config import (
    get_resolver,
    write_artifact_config,
)
from lowkey_artifact_builder.model.models.artwork.outer_ridge_color import (
    resolve_outer_ridge_color_identity,
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


def test_explicit_outer_ridge_color_is_authoritative(
    tmp_path: Path,
) -> None:
    """
    Explicit Outer Ridge color overrides attachment-derived color policy.

    Both semantic identity and physical RGB are preserved.
    """

    resolver = _resolver_with_parameters(
        tmp_path,
        {
            "artwork_outer_ridge_width": 2.0,
            "artwork_outer_ridge_color": "test-black",
            "loop_position": 0,
        },
    )

    artwork = _vector_manifest(
        tmp_path,
    )

    color = resolve_outer_ridge_color_identity(
        artwork,
        resolver=resolver,
    )

    assert color.name == "test-black"
    assert color.rgb == (0, 0, 0)


@pytest.mark.parametrize(
    ("position", "expected_name", "expected_rgb"),
    (
        (0, "red", (255, 0, 0)),
        (90, "green", (0, 255, 0)),
        (180, "blue", (0, 0, 255)),
        (-90, "black", (0, 0, 0)),
    ),
)
def test_outer_ridge_color_defaults_to_attachment_color(
    tmp_path: Path,
    position: int,
    expected_name: str,
    expected_rgb: tuple[int, int, int],
) -> None:
    """
    Without explicit Outer Ridge color, its physical color identity follows
    Registered Artwork at the effective loop_position.

    Loop itself need not participate for loop_position to identify the
    attachment used by Outer Ridge color policy.
    """

    resolver = _resolver_with_parameters(
        tmp_path,
        {
            "artwork_outer_ridge_width": 2.0,
            "loop_position": position,
        },
    )

    artwork = _vector_manifest(
        tmp_path,
    )

    color = resolve_outer_ridge_color_identity(
        artwork,
        resolver=resolver,
    )

    assert color.name == expected_name
    assert color.rgb == expected_rgb
