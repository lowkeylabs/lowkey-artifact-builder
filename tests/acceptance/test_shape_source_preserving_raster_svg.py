"""
Acceptance tests for source-preserving raster Artwork in Shape SVG.

Phase 4: Raster-Preserving SVG Manufacturing.

A Shape consumer must select the raster Artifact and metadata Products
from the same Artwork Realization, build the required producer stages,
and incorporate the source-preserving image into its canonical SVG.

Vector and raster Artwork are alternative representations. A raster
representation requires both its registered image and metadata.

SVG-only manufacturing must not require vector tracing, extrusion,
or 3MF packaging.
"""

# File: tests/acceptance/test_shape_source_preserving_raster_svg.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import base64
import io
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image

from lowkey_artifact_builder.config import write_artifact_config
from lowkey_artifact_builder.engine import (
    BuildPlan,
    create_build_plan,
)
from lowkey_artifact_builder.engine.dependency_build import (
    execute_dependency_build,
)
from lowkey_artifact_builder.model import ProductRef

ARTIFACT_ID = "raster-shape"
ARTWORK_REALIZATION = "artwork_raster"
VECTOR_REALIZATION = "artwork_vector"
SHAPE_REALIZATION = "coaster_print"

SVG_NS = "http://www.w3.org/2000/svg"
XLINK_HREF = "{http://www.w3.org/1999/xlink}href"


# =========================================================
# Fixtures and helpers
# =========================================================


def _create_source(project_root: Path) -> Path:
    """
    Create a small RGBA PNG with inspectable pixel values.

    The source includes opaque, partially transparent, and fully
    transparent pixels so accidental flattening or recoloring is
    detectable.
    """
    source = project_root / "customer.png"

    image = Image.new(
        "RGBA",
        (19, 13),
        (0, 0, 0, 0),
    )

    image.putpixel(
        (0, 0),
        (23, 67, 201, 255),
    )

    image.putpixel(
        (18, 12),
        (180, 35, 80, 128),
    )

    image.putpixel(
        (9, 6),
        (40, 200, 100, 255),
    )

    image.save(
        source,
        format="PNG",
    )

    image.close()

    return source


def _shape_target() -> ProductRef:
    """Return the canonical Shape Compose SVG Product."""
    return ProductRef(
        artifact=ARTIFACT_ID,
        model="shape",
        realization=SHAPE_REALIZATION,
        stage="compose",
        product="artifact",
    )


def _configure_raster_shape(
    project_root: Path,
) -> tuple[Path, BuildPlan]:
    """
    Configure source-preserving raster Artwork and its Shape consumer.

    Both raster Products are explicitly bound to the same producer
    Realization.

    The vector alternative is also bound to that producer so
    representation selection can exclude it.
    """
    source = _create_source(project_root)

    write_artifact_config(
        ARTIFACT_ID,
        {
            "source": str(source),
            "realizations": {
                ARTWORK_REALIZATION: {
                    "variant": "artwork.default",
                    "artwork_representation": "raster",
                    "artwork_processing": "none",
                },
                SHAPE_REALIZATION: {
                    "variant": "shape.coaster",
                    "product_dependencies": {
                        "manifest": {
                            "artifact": ARTIFACT_ID,
                            "realization": ARTWORK_REALIZATION,
                        },
                        "raster_artwork": {
                            "artifact": ARTIFACT_ID,
                            "realization": ARTWORK_REALIZATION,
                        },
                        "raster_metadata": {
                            "artifact": ARTIFACT_ID,
                            "realization": ARTWORK_REALIZATION,
                        },
                    },
                },
            },
        },
        project_root=project_root,
    )

    plan = create_build_plan(
        ARTIFACT_ID,
        realization=SHAPE_REALIZATION,
        targets=(_shape_target(),),
        project_root=project_root,
    )

    return source, plan


def _configure_vector_shape(
    project_root: Path,
) -> BuildPlan:
    """
    Configure a vector Artwork producer and Shape consumer.

    Raster alternatives are bound to the same producer but must
    be excluded by representation-aware dependency selection.
    """
    write_artifact_config(
        ARTIFACT_ID,
        {
            "source": "customer.png",
            "realizations": {
                VECTOR_REALIZATION: {
                    "variant": "artwork.default",
                },
                SHAPE_REALIZATION: {
                    "variant": "shape.coaster",
                    "product_dependencies": {
                        "manifest": {
                            "artifact": ARTIFACT_ID,
                            "realization": VECTOR_REALIZATION,
                        },
                        "raster_artwork": {
                            "artifact": ARTIFACT_ID,
                            "realization": VECTOR_REALIZATION,
                        },
                        "raster_metadata": {
                            "artifact": ARTIFACT_ID,
                            "realization": VECTOR_REALIZATION,
                        },
                    },
                },
            },
        },
        project_root=project_root,
    )

    return create_build_plan(
        ARTIFACT_ID,
        realization=SHAPE_REALIZATION,
        targets=(_shape_target(),),
        project_root=project_root,
    )


def _selected_dependencies(
    plan: BuildPlan,
) -> dict[str, ProductRef]:
    """
    Return selected cross-Product dependencies by semantic input name.
    """
    return {
        (
            dependency.binding.dependency.name or dependency.binding.dependency.product
        ): dependency.product_ref
        for dependency in plan.planned_product_dependencies
    }


def _svg_product_path(plan: BuildPlan) -> Path:
    """Find the declared canonical Shape SVG Product."""
    compose = next(stage for stage in plan.stages if stage.name == "compose")

    return next(product.path for product in compose.products if product.spec.name == "artifact")


def _embedded_png(root: ET.Element) -> bytes:
    """Extract the single embedded PNG from an SVG document."""
    images = root.findall(f".//{{{SVG_NS}}}image")

    assert len(images) == 1

    element = images[0]

    href = element.get("href") or element.get(XLINK_HREF)

    assert href is not None
    assert href.startswith("data:image/png;base64,")

    return base64.b64decode(
        href.partition(",")[2],
        validate=True,
    )


# =========================================================
# Representation-aware dependency selection
# =========================================================


def test_raster_shape_selects_artifact_and_metadata(
    tmp_path: Path,
) -> None:
    """
    Raster Shape consumption requires both registered Products.

    Both Products must come from the selected Artwork Realization,
    not from an implicit default producer.
    """
    _, plan = _configure_raster_shape(tmp_path)

    dependencies = {
        (dependency.binding.dependency.name or dependency.binding.dependency.product): dependency
        for dependency in plan.planned_product_dependencies
    }

    assert set(dependencies) == {
        "raster_artwork",
        "raster_metadata",
    }

    artifact = dependencies["raster_artwork"]
    metadata = dependencies["raster_metadata"]

    assert artifact.product_ref == ProductRef(
        artifact=ARTIFACT_ID,
        model="artwork",
        realization=ARTWORK_REALIZATION,
        stage="raster_source",
        product="artifact",
    )

    assert metadata.product_ref == ProductRef(
        artifact=ARTIFACT_ID,
        model="artwork",
        realization=ARTWORK_REALIZATION,
        stage="raster_source",
        product="metadata",
    )

    assert artifact.path.name == "artifact.png"
    assert metadata.path.name == "metadata.json"

    assert artifact.path.parent == metadata.path.parent

    assert "manifest" not in dependencies


def test_vector_shape_does_not_select_raster_metadata(
    tmp_path: Path,
) -> None:
    """
    Vector Shape consumption excludes both raster Products.

    Raster metadata must not become an unconditional dependency
    merely because Shape Compose declares it.
    """
    plan = _configure_vector_shape(tmp_path)

    dependencies = _selected_dependencies(plan)

    assert set(dependencies) == {"manifest"}

    assert dependencies["manifest"] == ProductRef(
        artifact=ARTIFACT_ID,
        model="artwork",
        realization=VECTOR_REALIZATION,
        stage="vector",
        product="manifest",
    )

    assert "raster_artwork" not in dependencies
    assert "raster_metadata" not in dependencies


# =========================================================
# Raster SVG manufacturing
# =========================================================


def test_raster_shape_build_embeds_original_png(
    tmp_path: Path,
) -> None:
    """
    A Shape SVG contains the selected raster producer's PNG.

    Raster Artwork is not silently omitted or traced into vector
    geometry.

    The embedded image must preserve decoded RGBA pixel values.
    """
    source, plan = _configure_raster_shape(tmp_path)

    assert set(_selected_dependencies(plan)) == {
        "raster_artwork",
        "raster_metadata",
    }

    execute_dependency_build(plan)

    svg_path = _svg_product_path(plan)

    assert svg_path.is_file()

    root = ET.parse(svg_path).getroot()

    assert root.tag == f"{{{SVG_NS}}}svg"

    embedded = _embedded_png(root)

    with (
        Image.open(source) as original,
        Image.open(io.BytesIO(embedded)) as reproduced,
    ):
        assert reproduced.size == original.size
        assert reproduced.mode == "RGBA"

        assert reproduced.tobytes() == original.tobytes()

    # The canonical Shape remains physically dimensioned.
    assert root.get("width", "").endswith("mm")
    assert root.get("height", "").endswith("mm")

    # Structural manufacturing geometry remains independent.
    assert root.find(".//*[@id='cut-contour']") is not None

    assert root.find(".//*[@id='structure']") is not None

    # The raster content retains its own SVG group identity.
    artwork_group = root.find(".//*[@id='artwork']")

    assert artwork_group is not None

    assert artwork_group.find(f"{{{SVG_NS}}}image") is not None


def test_raster_shape_svg_does_not_require_vector_or_3mf(
    tmp_path: Path,
) -> None:
    """
    A raster SVG request avoids vector tracing and physical extrusion.

    Only the selected producer Products and required Shape stages
    participate.
    """
    _, plan = _configure_raster_shape(tmp_path)

    assert tuple(stage.name for stage in plan.stages) == (
        "structure",
        "compose",
    )

    dependencies = _selected_dependencies(plan)

    assert set(dependencies) == {
        "raster_artwork",
        "raster_metadata",
    }

    execute_dependency_build(plan)

    assert _svg_product_path(plan).is_file()

    artwork_root = tmp_path / "artifacts" / ARTIFACT_ID / "artwork" / ARTWORK_REALIZATION

    shape_root = tmp_path / "artifacts" / ARTIFACT_ID / "shape" / SHAPE_REALIZATION

    # The registered raster Products must exist.
    raster_root = artwork_root / "15-raster_source"

    assert (raster_root / "artifact.png").is_file()
    assert (raster_root / "metadata.json").is_file()

    # Vector tracing and standalone Artwork manufacturing
    # are unnecessary for raster Shape SVG production.
    assert not (artwork_root / "10-prepare").exists()
    assert not (artwork_root / "20-raster").exists()
    assert not (artwork_root / "30-vector").exists()
    assert not (artwork_root / "40-extrude").exists()
    assert not (artwork_root / "50-package").exists()

    # Shape physical manufacturing is also unnecessary.
    assert not (shape_root / "30-extrude").exists()
    assert not (shape_root / "40-package").exists()
