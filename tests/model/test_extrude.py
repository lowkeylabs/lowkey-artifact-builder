"""
Tests for the artwork extrusion stage.

These tests characterize the storage boundary between the build engine
and the extrusion-stage implementation.

The extrusion stage must consume only the paths supplied through
StageContext. Dynamic STL products are stage-local products whose
locations are determined by the declared extrusion manifest.
"""
# File: tests/model/test_extrude.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from lowkey_artifact_builder.model.models.artwork.stages import extrude

# =========================================================
# Test support
# =========================================================


class StubResolver:
    """
    Minimal Resolver-compatible object for extrusion-stage tests.
    """

    def __init__(
        self,
        values: dict[str, Any],
    ) -> None:
        self._values = values

    def __call__(
        self,
        name: str,
    ) -> Any:
        return self._values[name]


class StubContext:
    """
    Minimal StageContext-compatible object for extrusion-stage tests.
    """

    def __init__(
        self,
        *,
        inputs: dict[str, Path],
        outputs: dict[str, Path],
        resolver: StubResolver,
    ) -> None:
        self._inputs = inputs
        self._outputs = outputs
        self.resolver = resolver

    def input(
        self,
        name: str,
    ) -> Path:
        return self._inputs[name]

    def output(
        self,
        name: str,
    ) -> Path:
        return self._outputs[name]


def _color(
    red: int,
    green: int,
    blue: int,
) -> dict[str, int]:
    """
    Return a vector-manifest RGB color.
    """

    return {
        "red": red,
        "green": green,
        "blue": blue,
    }


def _write_vector_manifest(
    path: Path,
    products: list[dict[str, Any]],
    *,
    registered_extent: int = 20,
) -> None:
    """
    Write a minimal registered vector manifest.
    """

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        json.dumps(
            {
                "registered_extent": registered_extent,
                "products": products,
            }
        ),
        encoding="utf-8",
    )


def _resolver() -> StubResolver:
    """
    Return the standard extrusion-stage configuration.
    """

    return StubResolver(
        {
            "artwork_colors": [
                "white",
                "black",
            ],
            "artwork_size": 150.0,
            "artwork_raise": 1.0,
        }
    )


# =========================================================
# Storage-boundary tests
# =========================================================


def test_extrude_uses_declared_vector_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    The extrusion stage consumes the vector manifest supplied by
    StageContext without reconstructing its filesystem location.
    """

    vector_directory = tmp_path / "deliberately" / "unrelated" / "vector-input"

    svg = vector_directory / "layer.svg"

    vector_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    svg.write_text(
        "<svg/>",
        encoding="utf-8",
    )

    vector_manifest = vector_directory / "anything.json"

    _write_vector_manifest(
        vector_manifest,
        [
            {
                "index": 1,
                "path": svg.name,
                "name": "white",
                "color": _color(
                    255,
                    255,
                    255,
                ),
            }
        ],
    )

    extrude_manifest = tmp_path / "completely-different" / "output" / "manifest.json"

    context = StubContext(
        inputs={
            "vector.manifest": vector_manifest,
        },
        outputs={
            "manifest": extrude_manifest,
        },
        resolver=_resolver(),
    )

    rendered_sources: list[str] = []

    def fake_render_stl_source(
        source: str,
        output: Path,
    ) -> None:
        rendered_sources.append(source)

        output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        output.write_text(
            "stl",
            encoding="utf-8",
        )

    monkeypatch.setattr(
        extrude,
        "render_stl_source",
        fake_render_stl_source,
    )

    extrude.execute(context)  # type: ignore[arg-type]

    assert len(rendered_sources) == 1

    assert str(svg.resolve()) in rendered_sources[0]

    assert extrude_manifest.is_file()


def test_extrude_places_dynamic_stls_beside_declared_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Dynamic STL products are placed beside the extrusion manifest
    supplied by StageContext.
    """

    vector_directory = tmp_path / "vector"

    first_svg = vector_directory / "first.svg"
    second_svg = vector_directory / "second.svg"

    vector_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    first_svg.write_text(
        "<svg/>",
        encoding="utf-8",
    )

    second_svg.write_text(
        "<svg/>",
        encoding="utf-8",
    )

    vector_manifest = vector_directory / "products.json"

    _write_vector_manifest(
        vector_manifest,
        [
            {
                "index": 2,
                "path": second_svg.name,
                "name": "black",
                "color": _color(
                    0,
                    0,
                    0,
                ),
            },
            {
                "index": 1,
                "path": first_svg.name,
                "name": "white",
                "color": _color(
                    255,
                    255,
                    255,
                ),
            },
        ],
    )

    output_directory = tmp_path / "arbitrary" / "extrusion-products"

    extrude_manifest = output_directory / "custom-name.json"

    context = StubContext(
        inputs={
            "vector.manifest": vector_manifest,
        },
        outputs={
            "manifest": extrude_manifest,
        },
        resolver=_resolver(),
    )

    rendered_outputs: list[Path] = []

    def fake_render_stl_source(
        source: str,
        output: Path,
    ) -> None:
        rendered_outputs.append(output)

        output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        output.write_text(
            "stl",
            encoding="utf-8",
        )

    monkeypatch.setattr(
        extrude,
        "render_stl_source",
        fake_render_stl_source,
    )

    extrude.execute(context)  # type: ignore[arg-type]

    assert rendered_outputs == [
        output_directory / "color-1.stl",
        output_directory / "color-2.stl",
    ]

    assert all(path.is_file() for path in rendered_outputs)


def test_extrude_manifest_describes_stage_local_products(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    The extrusion manifest records dynamic STL products using filenames
    relative to the manifest rather than canonical artifact paths.
    """

    vector_directory = tmp_path / "input"

    svg = vector_directory / "layer.svg"

    vector_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    svg.write_text(
        "<svg/>",
        encoding="utf-8",
    )

    vector_manifest = vector_directory / "manifest.json"

    _write_vector_manifest(
        vector_manifest,
        [
            {
                "index": 1,
                "path": svg.name,
                "name": "gold",
                "color": _color(
                    255,
                    215,
                    0,
                ),
            }
        ],
    )

    extrude_manifest = tmp_path / "wherever" / "extruded" / "products.json"

    context = StubContext(
        inputs={
            "vector.manifest": vector_manifest,
        },
        outputs={
            "manifest": extrude_manifest,
        },
        resolver=_resolver(),
    )

    def fake_render_stl_source(
        source: str,
        output: Path,
    ) -> None:
        output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        output.write_text(
            "stl",
            encoding="utf-8",
        )

    monkeypatch.setattr(
        extrude,
        "render_stl_source",
        fake_render_stl_source,
    )

    extrude.execute(context)  # type: ignore[arg-type]

    data = json.loads(
        extrude_manifest.read_text(
            encoding="utf-8",
        )
    )

    assert data == {
        "artwork_raise": 1.0,
        "products": [
            {
                "index": 1,
                "path": "color-1.stl",
                "name": "gold",
                "color": {
                    "red": 255,
                    "green": 215,
                    "blue": 0,
                },
            }
        ],
    }


# =========================================================
# Dimensionalization tests
# =========================================================


def test_build_scad_fits_registered_geometry_to_physical_size(
    tmp_path: Path,
) -> None:
    """
    Extrusion fits registered vector geometry to the configured
    physical artwork size.

    Registered vector coordinates are dimensionless until extrusion.
    The consuming extrusion stage therefore scales the common vector
    coordinate system to artwork_size before creating physical geometry.
    """

    svg = tmp_path / "layer.svg"

    svg.write_text(
        """
        <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 20 20"
        >
            <rect
                x="0"
                y="0"
                width="20"
                height="20"
            />
        </svg>
        """,
        encoding="utf-8",
    )

    source = extrude._build_scad(
        svg,
        registered_extent=20,
        artwork_size=150.0,
        artwork_raise=1.0,
    )

    assert "registered_extent = 20;" in source
    assert "artwork_size = 150;" in source
    assert "scale(" in source
    assert "artwork_size / registered_extent" in source
