"""
Tests for Artwork Outer Ridge extrusion integration.

Outer Ridge reserves physical space inside artwork_size by uniformly
scaling Artwork proper while preserving its existing center and
registration.
"""
# File: tests/model/artwork/test_outer_ridge_extrusion.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from lowkey_artifact_builder.config import Resolver, get_resolver
from lowkey_artifact_builder.model.models.artwork.stages import extrude


def _write_svg(
    path: Path,
) -> None:
    path.write_text(
        """
<svg xmlns="http://www.w3.org/2000/svg"
     width="100"
     height="100"
     viewBox="0 0 100 100">
  <rect x="20" y="10" width="40" height="30"/>
</svg>
""".strip(),
        encoding="utf-8",
    )


class _StubContext:
    def __init__(
        self,
        *,
        vector_manifest: Path,
        extrude_manifest: Path,
        resolver: Resolver,
    ) -> None:
        self._vector_manifest = vector_manifest
        self._extrude_manifest = extrude_manifest
        self.resolver = resolver

    def input(
        self,
        name: str,
    ) -> Path:
        assert name == "vector.manifest"
        return self._vector_manifest

    def output(
        self,
        name: str,
    ) -> Path:
        assert name == "manifest"
        return self._extrude_manifest


def _resolver(
    tmp_path: Path,
    **overrides: Any,
) -> Resolver:
    resolver = get_resolver(
        "outer-ridge-extrusion",
        model="artwork",
        project_root=tmp_path,
    )

    return resolver.with_values(
        overrides,
        provenance="test",
    )


def _write_vector_manifest(
    path: Path,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    envelope = path.parent / "envelope.svg"
    first = path.parent / "color-1.svg"
    second = path.parent / "color-2.svg"

    _write_svg(envelope)
    _write_svg(first)
    _write_svg(second)

    path.write_text(
        json.dumps(
            {
                "registered_extent": 100,
                "envelope": envelope.name,
                "products": [
                    {
                        "index": 1,
                        "path": first.name,
                        "artifact_color": {
                            "index": 1,
                            "rgb": {
                                "red": 255,
                                "green": 0,
                                "blue": 0,
                            },
                        },
                        "printer_color": {
                            "name": "test-red",
                            "rgb": {
                                "red": 255,
                                "green": 0,
                                "blue": 0,
                            },
                        },
                        "distance": 0.0,
                    },
                    {
                        "index": 2,
                        "path": second.name,
                        "artifact_color": {
                            "index": 2,
                            "rgb": {
                                "red": 0,
                                "green": 0,
                                "blue": 255,
                            },
                        },
                        "printer_color": {
                            "name": "test-blue",
                            "rgb": {
                                "red": 0,
                                "green": 0,
                                "blue": 255,
                            },
                        },
                        "distance": 0.0,
                    },
                ],
            }
        ),
        encoding="utf-8",
    )


def _fake_render_stl_source(
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


@pytest.mark.slow
def test_execute_applies_outer_ridge_scale_to_every_artwork_layer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    A participating Outer Ridge reserves its perimeter from Artwork proper.

    Every registered Artwork color layer receives the same model-owned
    uniform scale so registration between layers is preserved.
    """

    vector_manifest = tmp_path / "vector" / "products.json"
    extrude_manifest = tmp_path / "extrude" / "products.json"

    _write_vector_manifest(
        vector_manifest,
    )

    context = _StubContext(
        vector_manifest=vector_manifest,
        extrude_manifest=extrude_manifest,
        resolver=_resolver(
            tmp_path,
            artwork_size=40.0,
            artwork_raise=1.0,
            artwork_outer_ridge_width=2.0,
        ),
    )

    scales: list[float] = []

    original_build_scad = extrude._build_scad

    def capture_build_scad(
        svg_path: Path,
        *,
        registered_extent: int,
        envelope_bounds: tuple[
            float,
            float,
            float,
            float,
        ],
        artwork_size: float,
        artwork_raise: float,
        artwork_z: float = 0.0,
        artwork_scale: float = 1.0,
    ) -> str:
        scales.append(
            artwork_scale,
        )

        return original_build_scad(
            svg_path,
            registered_extent=registered_extent,
            envelope_bounds=envelope_bounds,
            artwork_size=artwork_size,
            artwork_raise=artwork_raise,
            artwork_z=artwork_z,
            artwork_scale=artwork_scale,
        )

    monkeypatch.setattr(
        extrude,
        "_build_scad",
        capture_build_scad,
    )

    monkeypatch.setattr(
        extrude,
        "render_stl_source",
        _fake_render_stl_source,
    )

    extrude.execute(
        context,  # type: ignore[arg-type]
    )

    assert scales == pytest.approx(
        [
            0.9,
            0.9,
        ]
    )


@pytest.mark.slow
def test_execute_uses_neutral_artwork_scale_when_outer_ridge_is_disabled(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Disabled Outer Ridge preserves ordinary Artwork dimensionalization.

    artwork_outer_ridge_width == 0 therefore supplies the neutral scale to
    every registered Artwork color layer.
    """

    vector_manifest = tmp_path / "vector" / "products.json"
    extrude_manifest = tmp_path / "extrude" / "products.json"

    _write_vector_manifest(
        vector_manifest,
    )

    context = _StubContext(
        vector_manifest=vector_manifest,
        extrude_manifest=extrude_manifest,
        resolver=_resolver(
            tmp_path,
            artwork_size=40.0,
            artwork_raise=1.0,
            artwork_outer_ridge_width=0.0,
        ),
    )

    scales: list[float] = []

    original_build_scad = extrude._build_scad

    def capture_build_scad(
        svg_path: Path,
        *,
        registered_extent: int,
        envelope_bounds: tuple[
            float,
            float,
            float,
            float,
        ],
        artwork_size: float,
        artwork_raise: float,
        artwork_z: float = 0.0,
        artwork_scale: float = 1.0,
    ) -> str:
        scales.append(
            artwork_scale,
        )

        return original_build_scad(
            svg_path,
            registered_extent=registered_extent,
            envelope_bounds=envelope_bounds,
            artwork_size=artwork_size,
            artwork_raise=artwork_raise,
            artwork_z=artwork_z,
            artwork_scale=artwork_scale,
        )

    monkeypatch.setattr(
        extrude,
        "_build_scad",
        capture_build_scad,
    )

    monkeypatch.setattr(
        extrude,
        "render_stl_source",
        _fake_render_stl_source,
    )

    extrude.execute(
        context,  # type: ignore[arg-type]
    )

    assert scales == pytest.approx(
        [
            1.0,
            1.0,
        ]
    )


def test_outer_ridge_scales_artwork_proper_inside_full_artwork_size(
    tmp_path: Path,
) -> None:
    """
    Participating Outer Ridge uniformly scales Artwork proper inside the
    ordinary standalone artwork_size.

    A 2 mm ridge on 40 mm Artwork leaves a 36 mm size-controlled Artwork
    extent, giving a uniform scale factor of 0.9.
    """

    svg = tmp_path / "layer.svg"
    _write_svg(svg)

    source = extrude._build_scad(
        svg,
        registered_extent=100,
        envelope_bounds=(
            20.0,
            10.0,
            60.0,
            40.0,
        ),
        artwork_size=40.0,
        artwork_raise=1.0,
        artwork_scale=0.9,
    )

    assert "artwork_scale = 0.9;" in source
    assert "artwork_size * artwork_scale / envelope_extent" in source


def test_disabled_outer_ridge_preserves_ordinary_artwork_dimensionalization(
    tmp_path: Path,
) -> None:
    """
    A scale of one preserves the existing standalone Artwork
    dimensionalization exactly.
    """

    svg = tmp_path / "layer.svg"
    _write_svg(svg)

    source = extrude._build_scad(
        svg,
        registered_extent=100,
        envelope_bounds=(
            20.0,
            10.0,
            60.0,
            40.0,
        ),
        artwork_size=40.0,
        artwork_raise=1.0,
        artwork_scale=1.0,
    )

    assert "artwork_scale = 1;" in source
    assert "artwork_size * artwork_scale / envelope_extent" in source


def test_outer_ridge_artwork_scaling_preserves_existing_centering(
    tmp_path: Path,
) -> None:
    """
    Outer Ridge scaling changes only the common physical scale.

    Registered Artwork continues to be centered from the occupied envelope,
    so every color layer retains the same center and registration.
    """

    svg = tmp_path / "layer.svg"
    _write_svg(svg)

    source = extrude._build_scad(
        svg,
        registered_extent=100,
        envelope_bounds=(
            20.0,
            10.0,
            60.0,
            40.0,
        ),
        artwork_size=40.0,
        artwork_raise=1.0,
        artwork_scale=0.9,
    )

    assert "envelope_center_x = 40;" in source

    # SVG center Y is 25. OpenSCAD reverses the registered Y axis:
    # 100 - 25 = 75.
    assert "envelope_openscad_center_y = 75;" in source

    assert "-envelope_center_x" in source
    assert "-envelope_openscad_center_y" in source


def test_build_scad_uses_neutral_artwork_scale_without_outer_ridge(
    tmp_path: Path,
) -> None:
    """
    Ordinary Artwork dimensionalization uses a neutral Artwork scale.

    The occupied envelope continues to be fitted to artwork_size when no
    Outer Ridge space has been reserved.
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
        envelope_bounds=(
            0.0,
            0.0,
            20.0,
            20.0,
        ),
        artwork_size=150.0,
        artwork_raise=1.0,
    )

    assert "registered_extent = 20;" in source
    assert "envelope_width = 20;" in source
    assert "envelope_height = 20;" in source
    assert "envelope_extent = 20;" in source
    assert "envelope_center_x = 10;" in source
    assert "envelope_openscad_center_y = 10;" in source

    assert "artwork_size = 150;" in source
    assert "artwork_scale = 1;" in source

    assert "artwork_size * artwork_scale / envelope_extent" in source

    assert "dpi = 25.4" in source


def test_build_scad_artwork_scale_is_independent_of_z_raise(
    tmp_path: Path,
) -> None:
    """
    Outer-Ridge-aware X/Y scaling remains independent of Artwork Z height.

    artwork_size and artwork_scale dimensionalize the registered coordinate
    system in X/Y while artwork_raise independently supplies extrusion height.
    """

    svg = tmp_path / "layer.svg"

    svg.write_text(
        "<svg/>",
        encoding="utf-8",
    )

    low = extrude._build_scad(
        svg,
        registered_extent=25,
        envelope_bounds=(
            0.0,
            0.0,
            25.0,
            25.0,
        ),
        artwork_size=100.0,
        artwork_raise=0.5,
        artwork_scale=0.9,
    )

    high = extrude._build_scad(
        svg,
        registered_extent=25,
        envelope_bounds=(
            0.0,
            0.0,
            25.0,
            25.0,
        ),
        artwork_size=100.0,
        artwork_raise=2.0,
        artwork_scale=0.9,
    )

    assert "artwork_scale = 0.9;" in low
    assert "artwork_scale = 0.9;" in high

    assert "artwork_size * artwork_scale / envelope_extent" in low
    assert "artwork_size * artwork_scale / envelope_extent" in high

    assert "artwork_raise = 0.5;" in low
    assert "artwork_raise = 2;" in high

    assert "height = artwork_raise" in low
    assert "height = artwork_raise" in high


# =========================================================
# Outer Ridge solid
# =========================================================


def test_outer_ridge_scad_builds_ring_from_full_and_scaled_envelope(
    tmp_path: Path,
) -> None:
    """
    Outer Ridge occupies the region between the full-size Artwork envelope
    and the uniformly scaled envelope reserved for Artwork proper.
    """

    envelope = tmp_path / "envelope.svg"
    _write_svg(envelope)

    source = extrude._build_outer_ridge_scad(
        envelope,
        registered_extent=100,
        envelope_bounds=(
            20.0,
            10.0,
            60.0,
            40.0,
        ),
        artwork_size=40.0,
        outer_ridge_width=2.0,
        outer_ridge_raise=1.0,
    )

    assert "difference()" in source

    assert "artwork_size / envelope_extent" in source
    assert "artwork_size * outer_ridge_scale / envelope_extent" in source

    assert "outer_ridge_scale = 0.9;" in source


def test_outer_ridge_scad_preserves_common_envelope_center(
    tmp_path: Path,
) -> None:
    """
    The full outer envelope and scaled inner envelope share one center.

    Scaling therefore reserves the Outer Ridge perimeter without shifting
    Artwork registration.
    """

    envelope = tmp_path / "envelope.svg"
    _write_svg(envelope)

    source = extrude._build_outer_ridge_scad(
        envelope,
        registered_extent=100,
        envelope_bounds=(
            20.0,
            10.0,
            60.0,
            40.0,
        ),
        artwork_size=40.0,
        outer_ridge_width=2.0,
        outer_ridge_raise=1.0,
    )

    assert "envelope_center_x = 40;" in source
    assert "envelope_openscad_center_y = 75;" in source

    assert source.count("-envelope_center_x") == 2
    assert source.count("-envelope_openscad_center_y") == 2


def test_outer_ridge_scad_uses_configured_total_raise(
    tmp_path: Path,
) -> None:
    """
    Outer Ridge raise is its total extrusion height from its supporting
    plane rather than an amount added above Artwork proper.
    """

    envelope = tmp_path / "envelope.svg"
    _write_svg(envelope)

    source = extrude._build_outer_ridge_scad(
        envelope,
        registered_extent=100,
        envelope_bounds=(
            20.0,
            10.0,
            60.0,
            40.0,
        ),
        artwork_size=40.0,
        outer_ridge_width=2.0,
        outer_ridge_raise=1.75,
    )

    assert "outer_ridge_raise = 1.75;" in source
    assert "height = outer_ridge_raise" in source


def test_outer_ridge_scad_accepts_supporting_plane_z(
    tmp_path: Path,
) -> None:
    """
    Outer Ridge begins at the common standalone Artwork supporting plane.

    The default is Z=0. A participating Base may later supply its top
    surface as that supporting plane without changing Outer Ridge raise.
    """

    envelope = tmp_path / "envelope.svg"
    _write_svg(envelope)

    source = extrude._build_outer_ridge_scad(
        envelope,
        registered_extent=100,
        envelope_bounds=(
            20.0,
            10.0,
            60.0,
            40.0,
        ),
        artwork_size=40.0,
        outer_ridge_width=2.0,
        outer_ridge_raise=1.25,
        outer_ridge_z=1.5,
    )

    assert "outer_ridge_raise = 1.25;" in source
    assert "outer_ridge_z = 1.5;" in source
    assert "height = outer_ridge_raise" in source
    assert "outer_ridge_z" in source


@pytest.mark.slow
def test_execute_creates_outer_ridge_stl_when_ridge_participates(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    A positive Outer Ridge width causes the extrusion stage to manufacture
    the independently printable Outer Ridge solid.
    """

    vector_manifest = tmp_path / "vector" / "products.json"
    extrude_manifest = tmp_path / "extrude" / "products.json"

    _write_vector_manifest(
        vector_manifest,
    )

    context = _StubContext(
        vector_manifest=vector_manifest,
        extrude_manifest=extrude_manifest,
        resolver=_resolver(
            tmp_path,
            artwork_size=40.0,
            artwork_raise=1.0,
            artwork_outer_ridge_width=2.0,
            artwork_outer_ridge_raise=1.25,
        ),
    )

    rendered: list[
        tuple[
            str,
            Path,
        ]
    ] = []

    def capture_render_stl_source(
        source: str,
        output: Path,
    ) -> None:
        rendered.append(
            (
                source,
                output,
            )
        )
        _fake_render_stl_source(
            source,
            output,
        )

    monkeypatch.setattr(
        extrude,
        "render_stl_source",
        capture_render_stl_source,
    )

    extrude.execute(
        context,  # type: ignore[arg-type]
    )

    ridge_output = extrude_manifest.parent / "outer-ridge.stl"

    assert ridge_output.is_file()

    ridge_sources = [source for source, output in rendered if output == ridge_output]

    assert len(ridge_sources) == 1

    ridge_source = ridge_sources[0]

    assert "outer_ridge_scale = 0.9;" in ridge_source
    assert "outer_ridge_raise = 1.25;" in ridge_source
    assert "outer_ridge_z = 0;" in ridge_source


@pytest.mark.slow
def test_execute_does_not_create_outer_ridge_stl_when_ridge_is_disabled(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Width zero disables Outer Ridge participation completely.

    The extrusion stage therefore does not manufacture an Outer Ridge STL.
    """

    vector_manifest = tmp_path / "vector" / "products.json"
    extrude_manifest = tmp_path / "extrude" / "products.json"

    _write_vector_manifest(
        vector_manifest,
    )

    context = _StubContext(
        vector_manifest=vector_manifest,
        extrude_manifest=extrude_manifest,
        resolver=_resolver(
            tmp_path,
            artwork_size=40.0,
            artwork_raise=1.0,
            artwork_outer_ridge_width=0.0,
        ),
    )

    rendered_outputs: list[Path] = []

    def capture_render_stl_source(
        source: str,
        output: Path,
    ) -> None:
        rendered_outputs.append(
            output,
        )
        _fake_render_stl_source(
            source,
            output,
        )

    monkeypatch.setattr(
        extrude,
        "render_stl_source",
        capture_render_stl_source,
    )

    extrude.execute(
        context,  # type: ignore[arg-type]
    )

    ridge_output = extrude_manifest.parent / "outer-ridge.stl"

    assert not ridge_output.exists()
    assert ridge_output not in rendered_outputs


@pytest.mark.slow
def test_execute_places_outer_ridge_on_top_of_participating_base(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    When Base participates, Outer Ridge begins at the top of that Base.

    Outer Ridge raise remains its own total height measured from the common
    standalone Artwork supporting plane.
    """

    vector_manifest = tmp_path / "vector" / "products.json"
    extrude_manifest = tmp_path / "extrude" / "products.json"

    _write_vector_manifest(
        vector_manifest,
    )

    context = _StubContext(
        vector_manifest=vector_manifest,
        extrude_manifest=extrude_manifest,
        resolver=_resolver(
            tmp_path,
            artwork_size=40.0,
            artwork_raise=1.0,
            artwork_base_raise=1.5,
            artwork_outer_ridge_width=2.0,
            artwork_outer_ridge_raise=1.25,
        ),
    )

    rendered: list[
        tuple[
            str,
            Path,
        ]
    ] = []

    def capture_render_stl_source(
        source: str,
        output: Path,
    ) -> None:
        rendered.append(
            (
                source,
                output,
            )
        )
        _fake_render_stl_source(
            source,
            output,
        )

    monkeypatch.setattr(
        extrude,
        "render_stl_source",
        capture_render_stl_source,
    )

    extrude.execute(
        context,  # type: ignore[arg-type]
    )

    ridge_output = extrude_manifest.parent / "outer-ridge.stl"

    ridge_source = next(source for source, output in rendered if output == ridge_output)

    assert "outer_ridge_z = 1.5;" in ridge_source
    assert "outer_ridge_raise = 1.25;" in ridge_source
    assert "height = outer_ridge_raise" in ridge_source


@pytest.mark.slow
def test_base_shifts_artwork_and_outer_ridge_by_same_supporting_plane(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Base participation establishes one common supporting plane for Artwork
    proper and Outer Ridge.

    Their independently configured raises do not alter that common Z origin.
    """

    vector_manifest = tmp_path / "vector" / "products.json"
    extrude_manifest = tmp_path / "extrude" / "products.json"

    _write_vector_manifest(
        vector_manifest,
    )

    context = _StubContext(
        vector_manifest=vector_manifest,
        extrude_manifest=extrude_manifest,
        resolver=_resolver(
            tmp_path,
            artwork_size=40.0,
            artwork_raise=2.0,
            artwork_base_raise=1.5,
            artwork_outer_ridge_width=2.0,
            artwork_outer_ridge_raise=3.0,
        ),
    )

    rendered: list[
        tuple[
            str,
            Path,
        ]
    ] = []

    def capture_render_stl_source(
        source: str,
        output: Path,
    ) -> None:
        rendered.append(
            (
                source,
                output,
            )
        )
        _fake_render_stl_source(
            source,
            output,
        )

    monkeypatch.setattr(
        extrude,
        "render_stl_source",
        capture_render_stl_source,
    )

    extrude.execute(
        context,  # type: ignore[arg-type]
    )

    artwork_sources = [source for source, output in rendered if output.name.startswith("color-")]

    ridge_source = next(source for source, output in rendered if output.name == "outer-ridge.stl")

    assert artwork_sources

    for source in artwork_sources:
        assert "artwork_z = 1.5;" in source
        assert "artwork_raise = 2;" in source

    assert "outer_ridge_z = 1.5;" in ridge_source
    assert "outer_ridge_raise = 3;" in ridge_source


@pytest.mark.slow
def test_execute_declares_outer_ridge_with_resolved_semantic_color(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    A participating Outer Ridge is declared as an independently printable
    extrusion product with its complete resolved semantic physical color
    identity.
    """

    vector_manifest = tmp_path / "vector" / "products.json"
    extrude_manifest = tmp_path / "extrude" / "products.json"

    _write_vector_manifest(
        vector_manifest,
    )

    context = _StubContext(
        vector_manifest=vector_manifest,
        extrude_manifest=extrude_manifest,
        resolver=_resolver(
            tmp_path,
            artwork_size=40.0,
            artwork_raise=1.0,
            artwork_outer_ridge_width=2.0,
            artwork_outer_ridge_raise=1.25,
            artwork_outer_ridge_color="test-black",
        ),
    )

    monkeypatch.setattr(
        extrude,
        "render_stl_source",
        _fake_render_stl_source,
    )

    extrude.execute(
        context,  # type: ignore[arg-type]
    )

    data = json.loads(
        extrude_manifest.read_text(
            encoding="utf-8",
        )
    )

    ridge_products = [
        product for product in data["products"] if product["path"] == "outer-ridge.stl"
    ]

    assert ridge_products == [
        {
            "path": "outer-ridge.stl",
            "printer_color": {
                "name": "test-black",
                "rgb": {
                    "red": 0,
                    "green": 0,
                    "blue": 0,
                },
            },
        }
    ]
