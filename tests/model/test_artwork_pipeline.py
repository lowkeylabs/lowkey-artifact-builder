"""
End-to-end regression tests for the artwork model.

These tests exercise the complete artwork model through the public build
planner and execution engine.

The purpose is to verify that the migrated artwork pipeline operates
through the canonical product hierarchy while preserving the complete
prepare -> raster -> vector -> extrude -> package transformation.
"""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

from lowkey_artifact_builder.config import write_artifact_config
from lowkey_artifact_builder.engine import (
    create_build_plan,
    execute_build,
)

# =========================================================
# Test support
# =========================================================


def _write_workspace(
    project_root: Path,
) -> None:
    """
    Write workspace overrides required by the artwork integration test.

    Workspace configuration participates in the normal parameter
    resolution hierarchy through its [parameters] table.
    """

    (project_root / "workspace.toml").write_text(
        """
[parameters]
artwork_colors = ["white", "black"]
artwork_pixels = 64
artwork_size = 20.0
artwork_min_island_area = 0.1
artwork_island_connectivity = 8
artwork_raise = 1.0
""".lstrip(),
        encoding="utf-8",
    )


def _write_source(
    path: Path,
) -> None:
    """
    Write deterministic two-color source artwork.

    The image is intentionally small and geometrically simple so that
    the integration test exercises the real artwork tools without
    introducing unnecessary processing cost.
    """

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    image = Image.new(
        "RGBA",
        (64, 64),
        (
            0,
            0,
            0,
            0,
        ),
    )

    try:
        pixels = image.load()

        assert pixels is not None

        for y in range(8, 56):
            for x in range(8, 56):
                pixels[x, y] = (
                    255,
                    255,
                    255,
                    255,
                )

        for y in range(20, 44):
            for x in range(20, 44):
                pixels[x, y] = (
                    0,
                    0,
                    0,
                    255,
                )

        image.save(
            path,
            format="PNG",
        )

    finally:
        image.close()


def _read_manifest(
    path: Path,
) -> dict:
    """
    Read one artwork dynamic-product manifest.
    """

    return json.loads(
        path.read_text(
            encoding="utf-8",
        )
    )


# =========================================================
# Complete artwork pipeline
# =========================================================


def test_artwork_pipeline_produces_canonical_products(
    tmp_path: Path,
) -> None:
    """
    A complete artwork build produces every declared and dynamic product
    beneath the canonical model/realization/stage hierarchy.

    This is the Phase 4 regression boundary for the migrated artwork
    model. It deliberately enters through create_build_plan() and
    execute_build() rather than invoking stage implementations directly.
    """

    _write_workspace(tmp_path)

    source = tmp_path / "source.png"

    _write_source(source)

    write_artifact_config(
        "example",
        {
            "model": "artwork",
            "source": "source.png",
        },
        project_root=tmp_path,
    )

    plan = create_build_plan(
        "example",
        project_root=tmp_path,
    )

    execute_build(plan)

    realization = tmp_path / "artifacts" / "example" / "artwork" / "default"

    prepare_directory = realization / "10-prepare"
    raster_directory = realization / "20-raster"
    vector_directory = realization / "30-vector"
    extrude_directory = realization / "40-extrude"
    package_directory = realization / "50-package"

    # -----------------------------------------------------
    # Prepare
    # -----------------------------------------------------

    trace = prepare_directory / "trace.svg"
    envelope = prepare_directory / "envelope.svg"

    assert trace.is_file()
    assert envelope.is_file()

    # -----------------------------------------------------
    # Raster
    # -----------------------------------------------------

    raster_manifest_path = raster_directory / "products.json"

    assert raster_manifest_path.is_file()

    raster_manifest = _read_manifest(
        raster_manifest_path,
    )

    raster_products = raster_manifest["products"]

    assert raster_products

    raster_paths = tuple(raster_directory / product["path"] for product in raster_products)

    assert all(path.is_file() for path in raster_paths)

    assert all(path.parent == raster_directory for path in raster_paths)

    assert all(path.suffix == ".png" for path in raster_paths)

    # -----------------------------------------------------
    # Vector
    # -----------------------------------------------------

    vector_manifest_path = vector_directory / "products.json"

    assert vector_manifest_path.is_file()

    vector_manifest = _read_manifest(
        vector_manifest_path,
    )

    vector_products = vector_manifest["products"]

    assert vector_products

    vector_paths = tuple(vector_directory / product["path"] for product in vector_products)

    assert all(path.is_file() for path in vector_paths)

    assert all(path.parent == vector_directory for path in vector_paths)

    assert all(path.suffix == ".svg" for path in vector_paths)

    # -----------------------------------------------------
    # Extrude
    # -----------------------------------------------------

    extrude_manifest_path = extrude_directory / "products.json"

    assert extrude_manifest_path.is_file()

    extrude_manifest = _read_manifest(
        extrude_manifest_path,
    )

    extrude_products = extrude_manifest["products"]

    assert extrude_products

    extrude_paths = tuple(extrude_directory / product["path"] for product in extrude_products)

    assert all(path.is_file() for path in extrude_paths)

    assert all(path.parent == extrude_directory for path in extrude_paths)

    assert all(path.suffix == ".stl" for path in extrude_paths)

    # -----------------------------------------------------
    # Package
    # -----------------------------------------------------

    artifact = package_directory / "artifact.3mf"

    assert artifact.is_file()
    assert artifact.stat().st_size > 0


def test_artwork_pipeline_preserves_dynamic_product_identity(
    tmp_path: Path,
) -> None:
    """
    Dynamic artwork products preserve their semantic identity through
    rasterization, vectorization, and extrusion.

    Each downstream manifest must describe the same ordered collection
    of color products rather than rediscovering products from the
    filesystem.
    """

    _write_workspace(tmp_path)

    source = tmp_path / "source.png"

    _write_source(source)

    write_artifact_config(
        "example",
        {
            "model": "artwork",
            "source": "source.png",
        },
        project_root=tmp_path,
    )

    plan = create_build_plan(
        "example",
        project_root=tmp_path,
    )

    execute_build(plan)

    realization = tmp_path / "artifacts" / "example" / "artwork" / "default"

    raster = _read_manifest(realization / "20-raster" / "products.json")

    vector = _read_manifest(realization / "30-vector" / "products.json")

    extrude = _read_manifest(realization / "40-extrude" / "products.json")

    raster_products = raster["products"]
    vector_products = vector["products"]
    extrude_products = extrude["products"]

    assert len(raster_products) == len(vector_products)
    assert len(vector_products) == len(extrude_products)

    assert (
        [product["index"] for product in raster_products]
        == [product["index"] for product in vector_products]
        == [product["index"] for product in extrude_products]
    )

    assert (
        [product["name"] for product in raster_products]
        == [product["name"] for product in vector_products]
        == [product["name"] for product in extrude_products]
    )

    assert (
        [product["color"] for product in raster_products]
        == [product["color"] for product in vector_products]
        == [product["color"] for product in extrude_products]
    )
