"""RED acceptance tests for ARTWORK source + none Products (Phase 3, Slice B).

A source-preserving Product must retain the materialized source bytes and
format without invoking the existing vector manufacturing pipeline.
"""
# File: tests/model/artwork/test_source_preserving_products.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from lowkey_artifact_builder.config import write_artifact_config
from lowkey_artifact_builder.engine.dependency_build import execute_dependency_build
from lowkey_artifact_builder.engine.plan import create_build_plans
from lowkey_artifact_builder.model.specs import ProductRef


@pytest.fixture(params=["png", "svg"])
def source_file(tmp_path: Path, request: pytest.FixtureRequest) -> Path:
    """Provide distinct, valid source formats with known exact bytes."""
    suffix = str(request.param)
    source = tmp_path / f"customer.{suffix}"
    if suffix == "png":
        image = Image.new("RGBA", (19, 13), (0, 0, 0, 0))
        image.putpixel((0, 0), (23, 67, 201, 255))
        image.putpixel((18, 12), (180, 35, 80, 128))
        image.save(source, format="PNG")
        image.close()
    else:
        source.write_bytes(
            b'<svg xmlns="http://www.w3.org/2000/svg" '
            b'viewBox="0 0 19 13">\n'
            b'  <path fill="#123456" d="M0 0H19V13Z"/>\n'
            b"</svg>\n"
        )
    return source


def _source_plan(tmp_path: Path, source: Path):
    """Plan the canonical source Product for a configured ARTWORK Realization."""
    artifact_id = "source-example"
    realization = "original"
    write_artifact_config(
        artifact_id,
        {
            "source": str(source),
            "realizations": {
                realization: {
                    "model": "artwork",
                    "parameters": {
                        "artwork_representation": "source",
                        "artwork_processing": "none",
                    },
                },
            },
        },
        project_root=tmp_path,
    )
    target = ProductRef(
        artifact=artifact_id,
        model="artwork",
        realization=realization,
        stage="source",
        product="artifact",
    )
    plans = create_build_plans(
        artifact_id,
        realization=realization,
        targets=(target,),
        project_root=tmp_path,
    )
    assert len(plans) == 1
    return plans[0], target


def _product_path(plan, target: ProductRef) -> Path:
    """Locate the declared canonical Product, not an assumed output filename."""
    for stage in plan.stages:
        if stage.name == target.stage:
            for product in stage.products:
                if product.spec.name == target.product:
                    return product.path
    pytest.fail(f"Planned Product {target} was not declared")


def test_source_product_preserves_original_bytes_and_format(
    tmp_path: Path,
    source_file: Path,
) -> None:
    """The registered Product is a byte-identical copy of the supplied source."""
    expected = source_file.read_bytes()
    plan, target = _source_plan(tmp_path, source_file)
    product_path = _product_path(plan, target)

    execute_dependency_build(plan)

    assert product_path.is_file()
    assert product_path.read_bytes() == expected
    if source_file.suffix == ".png":
        assert product_path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    else:
        assert product_path.read_bytes().lstrip().startswith(b"<svg")


def test_source_product_does_not_run_vector_manufacturing(
    tmp_path: Path,
    source_file: Path,
) -> None:
    """Source registration does not require Prepare, Raster, Vector, or 3MF."""
    plan, target = _source_plan(tmp_path, source_file)
    assert target.stage == "source"
    assert {stage.name for stage in plan.stages}.isdisjoint(
        {"prepare", "raster", "vector", "extrude", "package"}
    )
    execute_dependency_build(plan)
    assert _product_path(plan, target).is_file()


def test_unchanged_source_product_is_reused(
    tmp_path: Path,
    source_file: Path,
) -> None:
    """Repeated requests preserve the canonical registered Product."""
    plan, target = _source_plan(tmp_path, source_file)
    execute_dependency_build(plan)
    product_path = _product_path(plan, target)
    before = (product_path.read_bytes(), product_path.stat().st_mtime_ns)

    refreshed_plans = create_build_plans(
        target.artifact,
        realization=target.realization,
        targets=(target,),
        project_root=tmp_path,
    )
    assert len(refreshed_plans) == 1
    execute_dependency_build(refreshed_plans[0])

    assert (product_path.read_bytes(), product_path.stat().st_mtime_ns) == before
