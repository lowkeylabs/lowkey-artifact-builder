"""JPEG normalization for source-preserving Artwork Realizations."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image

from lowkey_artifact_builder.config import configure_artifact
from lowkey_artifact_builder.engine.dependency_build import (
    execute_dependency_build,
    plan_dependency_build,
)
from lowkey_artifact_builder.engine.plan import create_build_plans
from lowkey_artifact_builder.model.specs import ProductRef

ARTIFACT_ID = "jpeg-source"


def _configure(tmp_path: Path) -> Path:
    """Ingest JPEG through the normal Artifact configuration API."""

    source = tmp_path / "customer" / "artifact.jpg"
    source.parent.mkdir(parents=True, exist_ok=True)

    image = Image.new("RGB", (32, 24), (40, 100, 180))
    try:
        image.save(source, format="JPEG", quality=95)
    finally:
        image.close()

    configure_artifact(
        ARTIFACT_ID,
        input_files={"artwork": source},
        values={
            "realizations": {
                "original": {
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

    return source


def _plan(tmp_path: Path):
    target = ProductRef(
        artifact=ARTIFACT_ID,
        model="artwork",
        realization="original",
        stage="source",
        product="artifact",
    )

    plans = create_build_plans(
        ARTIFACT_ID,
        realization="original",
        targets=(target,),
        project_root=tmp_path,
    )

    assert len(plans) == 1
    return plans[0]


def _outputs(plan) -> dict[str, Path]:
    stage = next(stage for stage in plan.stages if stage.name == "source")

    return {product.spec.name: product.path for product in stage.products}


def test_jpeg_source_registers_png_product(tmp_path: Path) -> None:
    source = _configure(tmp_path)
    plan = _plan(tmp_path)
    outputs = _outputs(plan)

    execute_dependency_build(plan)

    assert source.is_file()
    assert outputs["artifact"].is_file()

    with Image.open(source) as original:
        original.load()
        original_pixels = original.convert("RGB").tobytes()
        original_size = original.size

    with Image.open(outputs["artifact"]) as registered:
        registered.load()

        assert registered.format == "PNG"
        assert registered.size == original_size
        assert registered.convert("RGB").tobytes() == original_pixels


def test_jpeg_normalization_preserves_original_source(
    tmp_path: Path,
) -> None:
    source = _configure(tmp_path)
    original_bytes = source.read_bytes()

    artifact_source = tmp_path / "artifacts" / ARTIFACT_ID / "artifact.jpg"

    assert artifact_source.is_file()
    assert artifact_source.read_bytes() == original_bytes

    plan = _plan(tmp_path)

    execute_dependency_build(plan)

    assert source.read_bytes() == original_bytes
    assert artifact_source.read_bytes() == original_bytes

    assert not (tmp_path / "artifacts" / ARTIFACT_ID / "artifact.png").exists()


def test_jpeg_source_registers_accurate_provenance(
    tmp_path: Path,
) -> None:
    source = _configure(tmp_path)
    outputs = _outputs(_plan(tmp_path))

    execute_dependency_build(_plan(tmp_path))

    metadata = json.loads(outputs["metadata"].read_text(encoding="utf-8"))

    assert metadata["representation"] == "source"
    assert metadata["processing"] == "none"
    assert metadata["format"] == "png"
    assert metadata["source_format"] in {"jpg", "jpeg"}
    assert metadata["width"] == 32
    assert metadata["height"] == 24
    assert metadata["sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()


def test_normalized_jpeg_source_is_reusable(
    tmp_path: Path,
) -> None:
    _configure(tmp_path)
    plan = _plan(tmp_path)

    execute_dependency_build(plan)

    execution = plan_dependency_build(_plan(tmp_path))

    assert not execution.required_product_dependencies
    assert not any(stage.requires_execution for stage in execution.stages)


def test_jpeg_source_requires_only_source_stage(
    tmp_path: Path,
) -> None:
    _configure(tmp_path)

    stages = {stage.name for stage in _plan(tmp_path).stages}

    assert stages == {"source"}
