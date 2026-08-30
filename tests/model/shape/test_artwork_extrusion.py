"""
Tests for physical dimensionalization of Artwork incorporated into Shape.
"""
# File: tests/model/shape/test_artwork_extrusion.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path

import pytest

from lowkey_artifact_builder.model.models.shape.stages import extrude

# =========================================================
# Test support
# =========================================================


def _write_registered_artwork(
    path: Path,
) -> None:
    """
    Write asymmetric Artwork in its registered coordinate system.

    The registered Artwork extent is 100 units. The occupied rectangle spans:

        X = 10 through 30
        Y = 20 through 60

    The asymmetry makes both position and vertical orientation observable
    after Shape physical dimensionalization.
    """

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        """
<svg
    xmlns="http://www.w3.org/2000/svg"
    width="100"
    height="100"
    viewBox="0 0 100 100"
>
    <g>
        <rect
            x="10"
            y="20"
            width="20"
            height="40"
        />
    </g>
</svg>
""".strip(),
        encoding="utf-8",
    )


def _stl_bounds(
    path: Path,
) -> tuple[
    float,
    float,
    float,
    float,
    float,
    float,
]:
    """
    Return X/Y/Z bounds from an ASCII STL produced by OpenSCAD.
    """

    vertices: list[
        tuple[
            float,
            float,
            float,
        ]
    ] = []

    for line in path.read_text(
        encoding="utf-8",
    ).splitlines():
        fields = line.strip().split()

        if len(fields) != 4 or fields[0] != "vertex":
            continue

        vertices.append(
            (
                float(fields[1]),
                float(fields[2]),
                float(fields[3]),
            )
        )

    if not vertices:
        raise AssertionError(
            f"STL contains no readable vertices: {path}",
        )

    xs = tuple(vertex[0] for vertex in vertices)
    ys = tuple(vertex[1] for vertex in vertices)
    zs = tuple(vertex[2] for vertex in vertices)

    return (
        min(xs),
        max(xs),
        min(ys),
        max(ys),
        min(zs),
        max(zs),
    )


# =========================================================
# Registered Artwork physical dimensionalization
# =========================================================


@pytest.mark.slow
def test_incorporated_registered_artwork_preserves_physical_xy_orientation(
    tmp_path: Path,
) -> None:
    """
    Shape dimensionalization preserves registered Artwork position and
    orientation when mapping the composition into physical X/Y space.

    Registered Artwork occupies:

        X = 10..30
        Y = 20..60

    within a 100-unit registered extent.

    Mapping that extent into the canonical Shape coordinate system gives:

        X = -0.4..-0.2
        Y = -0.3..+0.1

    A 100 mm Shape must therefore produce physical geometry at:

        X = -40..-20 mm
        Y = -30..+10 mm

    Artwork begins at the 2 mm Shape base top and rises 1 mm.
    """

    artwork = tmp_path / "artwork-1.svg"
    output = tmp_path / "artwork-1.stl"

    _write_registered_artwork(
        artwork,
    )

    source = extrude._build_artwork_component_scad(
        str(
            artwork.resolve(),
        ),
        shape_size=100.0,
        shape_base_raise=2.0,
        shape_artwork_raise=1.0,
        artwork_registered_width=100.0,
        artwork_registered_height=100.0,
        artwork_scale=0.01,
        artwork_translate_x=-0.5,
        artwork_translate_y=-0.5,
    )

    extrude.render_stl_source(
        source,
        output,
    )

    bounds = _stl_bounds(
        output,
    )

    assert bounds == pytest.approx(
        (
            -40.0,
            -20.0,
            -30.0,
            10.0,
            2.0,
            3.0,
        )
    )


@pytest.mark.slow
def test_openscad_import_preserves_registered_artwork_xy_coordinates(
    tmp_path: Path,
) -> None:
    """
    OpenSCAD SVG import preserves the registered Artwork coordinate
    relationships needed by Shape dimensionalization.
    """

    artwork = tmp_path / "artwork.svg"
    output = tmp_path / "artwork.stl"

    _write_registered_artwork(
        artwork,
    )

    source = f'linear_extrude(height = 1)\n    import("{artwork.resolve()}", dpi = 25.4);\n'

    extrude.render_stl_source(
        source,
        output,
    )

    bounds = _stl_bounds(
        output,
    )

    assert bounds == pytest.approx(
        (
            10.0,
            30.0,
            40.0,
            80.0,
            0.0,
            1.0,
        )
    )


def test_artwork_extrusion_passes_registered_extent_to_scad_builder(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Artwork extrusion passes its registered coordinate extent to physical
    SCAD construction.
    """

    component = tmp_path / "color-1.svg"

    component.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg"/>',
        encoding="utf-8",
    )

    artwork = {
        "registered_extent": {
            "width": 100.0,
            "height": 80.0,
        },
        "transform": {
            "scale": 0.01,
            "translate_x": -0.5,
            "translate_y": -0.4,
        },
        "components": [
            {
                "index": 1,
                "path": "color-1.svg",
                "name": "red",
                "color": {
                    "hex": "#ff0000",
                },
            },
        ],
    }

    received: dict[str, float] = {}

    def build_artwork_component_scad(
        source: str,
        *,
        shape_size: float,
        shape_base_raise: float,
        shape_artwork_raise: float,
        artwork_registered_width: float,
        artwork_registered_height: float,
        artwork_scale: float,
        artwork_translate_x: float,
        artwork_translate_y: float,
    ) -> str:
        received["width"] = artwork_registered_width
        received["height"] = artwork_registered_height

        return ""

    monkeypatch.setattr(
        extrude,
        "_build_artwork_component_scad",
        build_artwork_component_scad,
    )
    monkeypatch.setattr(
        extrude,
        "render_stl_source",
        lambda source, output: output.touch(),
    )

    extrude._render_artwork_components(
        artwork,
        tmp_path,
        tmp_path,
        shape_size=100.0,
        shape_base_raise=2.0,
        shape_artwork_raise=1.0,
    )

    assert received == {
        "width": 100.0,
        "height": 80.0,
    }
