"""
Raster + none Product acceptance tests (RED).
"""
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
from pathlib import Path

import pytest
from PIL import Image

from lowkey_artifact_builder.config import write_artifact_config
from lowkey_artifact_builder.engine.dependency_build import execute_dependency_build
from lowkey_artifact_builder.engine.plan import create_build_plans
from lowkey_artifact_builder.model.specs import ProductRef


@pytest.fixture(params=["rgba-png", "rgb-png", "jpeg"])
def raster_source(tmp_path: Path, request: pytest.FixtureRequest) -> Path:
    """Generate tiny sources with exact, inspectable decoded pixels."""
    kind = str(request.param)
    if kind == "rgba-png":
        image = Image.new("RGBA", (19, 13), (0, 0, 0, 0))
        image.putpixel((0, 0), (23, 67, 201, 255))
        image.putpixel((18, 12), (180, 35, 80, 128))
        path = tmp_path / "customer.png"
        image.save(path, format="PNG")
    elif kind == "rgb-png":
        image = Image.new("RGB", (19, 13), (23, 67, 201))
        image.putpixel((18, 12), (180, 35, 80))
        path = tmp_path / "customer.png"
        image.save(path, format="PNG")
    else:
        image = Image.new("RGB", (19, 13), (23, 67, 201))
        image.putpixel((18, 12), (180, 35, 80))
        path = tmp_path / "customer.jpg"
        image.save(path, format="JPEG", quality=93)
    image.close()
    return path


def _raster_plan(tmp_path: Path, source: Path):
    """Request only the raster-preserving Product for one Realization."""
    artifact_id = "raster-example"
    realization = "preserved"
    write_artifact_config(
        artifact_id,
        {
            "source": str(source),
            "realizations": {
                realization: {
                    "model": "artwork",
                    "parameters": {
                        "artwork_representation": "raster",
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
        stage="raster_source",
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


def _product_path(plan, stage_name: str, product_name: str) -> Path:
    for stage in plan.stages:
        if stage.name == stage_name:
            for product in stage.products:
                if product.spec.name == product_name:
                    return product.path
    pytest.fail(f"Missing planned Product {stage_name}:{product_name}")


def test_raster_none_registers_png_with_identical_decoded_pixels(
    tmp_path: Path,
    raster_source: Path,
) -> None:
    """No resizing, quantization, compositing, or alpha loss is permitted."""
    plan, target = _raster_plan(tmp_path, raster_source)
    execute_dependency_build(plan)
    output = _product_path(plan, target.stage, target.product)

    with Image.open(raster_source) as original, Image.open(output) as produced:
        assert produced.format == "PNG"
        assert produced.size == original.size
        assert produced.mode == original.mode
        assert produced.tobytes() == original.tobytes()


def test_raster_none_avoids_vector_and_manufacturing_stages(
    tmp_path: Path,
    raster_source: Path,
) -> None:
    """Registering a raster Product must not run color-layer processing."""
    plan, target = _raster_plan(tmp_path, raster_source)
    assert {stage.name for stage in plan.stages} == {target.stage}
    execute_dependency_build(plan)
    assert _product_path(plan, target.stage, target.product).is_file()


def test_raster_none_records_format_dimensions_and_provenance(
    tmp_path: Path,
    raster_source: Path,
) -> None:
    """Consumers can identify the representation without inspecting pixels."""
    plan, target = _raster_plan(tmp_path, raster_source)
    execute_dependency_build(plan)
    metadata_path = _product_path(plan, target.stage, "metadata")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

    assert metadata["representation"] == "raster"
    assert metadata["processing"] == "none"
    assert metadata["format"] == "png"
    assert metadata["width"] == 19
    assert metadata["height"] == 13
    assert metadata["source_name"] == "artifact.png"


def test_unchanged_raster_product_is_reused(
    tmp_path: Path,
    raster_source: Path,
) -> None:
    """Rebuilding an unchanged Realization does not rewrite its Product."""
    plan, target = _raster_plan(tmp_path, raster_source)
    execute_dependency_build(plan)
    output = _product_path(plan, target.stage, target.product)
    before = (output.read_bytes(), output.stat().st_mtime_ns)

    plans = create_build_plans(
        target.artifact,
        realization=target.realization,
        targets=(target,),
        project_root=tmp_path,
    )
    assert len(plans) == 1
    execute_dependency_build(plans[0])
    assert (output.read_bytes(), output.stat().st_mtime_ns) == before
