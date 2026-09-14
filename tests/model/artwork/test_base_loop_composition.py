"""
Artwork Base and Loop composition tests.

These tests protect behavior that exists specifically because the optional
Artwork Base and Loop Features participate, or do not participate, together.

Individual Base and Loop semantics belong in their focused tests. This module
protects only their composition and independence.
"""
# File: tests/model/artwork/test_base_loop_composition.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from lowkey_artifact_builder.config import (
    Resolver,
    get_resolver,
    write_artifact_config,
)
from lowkey_artifact_builder.engine import create_build_plan
from lowkey_artifact_builder.model import ProductRef
from lowkey_artifact_builder.model.models.artwork.stages import extrude


class StubContext:
    """Minimal stage context used by Artwork Feature-composition tests."""

    def __init__(
        self,
        *,
        inputs: dict[str, Path],
        outputs: dict[str, Path],
        resolver: Resolver,
    ) -> None:
        self.inputs = inputs
        self.outputs = outputs
        self.resolver = resolver

    def input(self, name: str) -> Path:
        return self.inputs[name]

    def output(self, name: str) -> Path:
        return self.outputs[name]


def _product(
    *,
    index: int,
    path: str,
    artifact_color_index: int,
    artifact_rgb: tuple[int, int, int],
    printer_color_name: str,
    printer_rgb: tuple[int, int, int],
    distance: float,
) -> dict[str, object]:
    """Return one registered Artwork vector product."""

    return {
        "index": index,
        "path": path,
        "artifact_color": {
            "index": artifact_color_index,
            "rgb": {
                "red": artifact_rgb[0],
                "green": artifact_rgb[1],
                "blue": artifact_rgb[2],
            },
        },
        "printer_color": {
            "name": printer_color_name,
            "rgb": {
                "red": printer_rgb[0],
                "green": printer_rgb[1],
                "blue": printer_rgb[2],
            },
        },
        "distance": distance,
    }


def _write_vector_manifest(
    path: Path,
    products: list[dict[str, Any]],
    *,
    registered_extent: int = 20,
) -> None:
    """
    Write a minimal registered vector manifest.

    The registered envelope occupies the complete registered extent unless
    a test constructs a more specific manifest explicitly.
    """

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    envelope = path.parent / "envelope.svg"

    envelope.write_text(
        f"""
        <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 {registered_extent} {registered_extent}"
        >
            <rect
                x="0"
                y="0"
                width="{registered_extent}"
                height="{registered_extent}"
            />
        </svg>
        """,
        encoding="utf-8",
    )

    path.write_text(
        json.dumps(
            {
                "registered_extent": registered_extent,
                "envelope": envelope.name,
                "products": products,
            }
        ),
        encoding="utf-8",
    )


def _fake_render_stl_source(
    source: str,
    output: Path,
) -> None:
    """Replace physical STL rendering with a deterministic test artifact."""

    del source

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output.write_text(
        "solid test\nendsolid test\n",
        encoding="utf-8",
    )


@pytest.mark.parametrize(
    (
        "artwork_base_raise",
        "loop_inner_diameter",
        "expected_feature_products",
    ),
    [
        (
            0.0,
            0.0,
            set(),
        ),
        (
            1.5,
            0.0,
            {
                "base.stl",
            },
        ),
        (
            0.0,
            5.0,
            {
                "loop.stl",
            },
        ),
        (
            1.5,
            5.0,
            {
                "base.stl",
                "loop.stl",
            },
        ),
    ],
)
def test_base_and_loop_participate_independently(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    artwork_base_raise: float,
    loop_inner_diameter: float,
    expected_feature_products: set[str],
) -> None:
    """
    Base and Loop participation are independent.

    Each combination produces exactly the standalone Feature components
    implied by its effective Feature parameters.

    Parameters unrelated to this composition inherit their ordinary Artwork
    defaults rather than being duplicated by this test.
    """

    vector_directory = tmp_path / "vector"
    svg = vector_directory / "layer.svg"

    vector_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

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

    vector_manifest = vector_directory / "products.json"

    _write_vector_manifest(
        vector_manifest,
        [
            _product(
                index=1,
                path=svg.name,
                artifact_color_index=1,
                artifact_rgb=(
                    255,
                    0,
                    0,
                ),
                printer_color_name="red",
                printer_rgb=(
                    255,
                    0,
                    0,
                ),
                distance=0.0,
            )
        ],
    )

    extrude_manifest = tmp_path / "extrude" / "products.json"

    resolver = get_resolver(
        "feature-artwork",
        model="artwork",
        project_root=tmp_path,
    ).with_values(
        {
            "artwork_size": 100.0,
            "artwork_raise": 1.0,
            "artwork_base_raise": artwork_base_raise,
            "loop_inner_diameter": loop_inner_diameter,
            "loop_width": 2.0,
            "loop_position": 0,
            "loop_raise": 1.0,
        },
        provenance="test",
    )

    context = StubContext(
        inputs={
            "vector.manifest": vector_manifest,
        },
        outputs={
            "manifest": extrude_manifest,
        },
        resolver=resolver,
    )

    monkeypatch.setattr(
        extrude,
        "render_stl_source",
        _fake_render_stl_source,
    )

    extrude.execute(context)  # type: ignore[arg-type]

    data: dict[str, Any] = json.loads(
        extrude_manifest.read_text(
            encoding="utf-8",
        )
    )

    feature_products = {
        product["path"]
        for product in data["products"]
        if product["path"]
        in {
            "base.stl",
            "loop.stl",
        }
    }

    assert feature_products == expected_feature_products


def test_base_and_loop_do_not_enter_registered_artwork_dependency_plan(
    tmp_path: Path,
) -> None:
    """
    Standalone Base and Loop Features do not enter Registered Artwork.

    Even when both Features are enabled for the Artwork Realization, a
    dependency plan targeting only Registered Artwork stops at vectorization.
    Standalone physical extrusion and packaging remain downstream work.
    """

    source = tmp_path / "source.png"

    source.write_bytes(b"test-source")

    write_artifact_config(
        "feature-artwork",
        {
            "model": "artwork",
            "source": str(source),
            "artwork_base_raise": 1.5,
            "loop_inner_diameter": 5.0,
        },
        project_root=tmp_path,
    )

    target = ProductRef(
        artifact="feature-artwork",
        model="artwork",
        realization="artwork_default",
        stage="vector",
        product="manifest",
    )

    plan = create_build_plan(
        "feature-artwork",
        project_root=tmp_path,
        targets=(target,),
    )

    assert plan.resolver("artwork_base_raise") == 1.5
    assert plan.resolver("loop_inner_diameter") == 5.0

    assert tuple(stage.name for stage in plan.stages) == (
        "prepare",
        "raster",
        "vector",
    )

    assert all(
        stage.name
        not in {
            "extrude",
            "package",
        }
        for stage in plan.stages
    )
