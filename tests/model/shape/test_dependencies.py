"""
Architectural dependency tests for the Shape model.

Shape may consume persistent registered Artwork without depending on
Artwork's physical dimensionalization or packaging stages.

Shape Compose supports two optional Artwork representations:

- registered vector Artwork, consumed through its vector manifest;
- source-preserving raster Artwork, consumed through its raster
  artifact and metadata Products.

BuildPlan selects only the representation required by the bound
Artwork producer. Neither representation is selected when Artwork
is absent.

A persistent registered Artwork product is sufficient to satisfy
Shape's cross-artifact dependency. Historical source inputs and
configuration needed only to reproduce that product do not participate
when the registered product already exists.
"""
# File: tests/model/shape/test_dependencies.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import ast
import json
from pathlib import Path

import lowkey_artifact_builder.model.models.shape.stages.extrude as shape_extrude
from lowkey_artifact_builder.config import write_artifact_config
from lowkey_artifact_builder.engine import (
    BuildPlan,
    PlannedProductDependency,
    create_build_plan,
)
from lowkey_artifact_builder.model import ProductDependencySpec

# =========================================================
# Architectural dependency tests
# =========================================================


def test_shape_extrude_does_not_depend_on_artwork_stage_implementation() -> None:
    """
    Shape composes shared mechanics without depending on Artwork stages.
    """

    source_path = Path(shape_extrude.__file__)
    source = source_path.read_text(
        encoding="utf-8",
    )

    tree = ast.parse(
        source,
    )

    forbidden_prefix = "lowkey_artifact_builder.model.models.artwork.stages"

    imported_modules = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }

    assert not any(
        module == forbidden_prefix or module.startswith(f"{forbidden_prefix}.")
        for module in imported_modules
    )


# =========================================================
# Artwork dependency declarations
# =========================================================


def _dependencies_by_name(
    plan: BuildPlan,
) -> dict[str, ProductDependencySpec]:
    """Index dependencies by explicit name or product name."""
    return {
        dependency.name or dependency.product: dependency
        for dependency in plan.product_dependencies
    }


def _planned_dependencies_by_name(
    plan: BuildPlan,
) -> dict[str, PlannedProductDependency]:
    """Index planned dependencies by explicit name or product name."""
    return {
        planned.binding.dependency.name or planned.binding.dependency.product: planned
        for planned in plan.planned_product_dependencies
    }


def test_shape_declares_optional_vector_and_raster_artwork_dependencies(
    tmp_path: Path,
) -> None:
    """
    Shape Compose declares two optional Artwork representations.

    Vector Artwork requires its registered vector manifest.

    Source-preserving raster Artwork requires both its registered
    raster artifact and metadata Products.

    Without a bound Artwork producer, neither representation is
    selected for execution.
    """
    write_artifact_config(
        "shape-only",
        {"model": "shape"},
        project_root=tmp_path,
    )

    plan = create_build_plan(
        "shape-only",
        project_root=tmp_path,
    )

    compose = next(stage for stage in plan.stages if stage.name == "compose")

    declared = {
        dependency.name or dependency.product: dependency
        for dependency in compose.spec.product_dependencies
    }

    assert set(declared) == {
        "manifest",
        "raster_artwork",
        "raster_metadata",
    }

    # Vector Artwork is consumed through its registered manifest.
    vector = declared["manifest"]

    assert vector.model == "artwork"
    assert vector.stage == "vector"
    assert vector.product == "manifest"

    # Raster Artwork is consumed through its registered PNG Product.
    raster = declared["raster_artwork"]

    assert raster.model == "artwork"
    assert raster.stage == "raster_source"
    assert raster.product == "artifact"

    # Raster metadata is a separate registered Product belonging
    # to the same producer stage.
    metadata = declared["raster_metadata"]

    assert metadata.model == "artwork"
    assert metadata.stage == "raster_source"
    assert metadata.product == "metadata"

    # Both Artwork representations are optional. Without an
    # available producer, neither representation is selected.
    assert _dependencies_by_name(plan) == {}
    assert plan.product_dependency_bindings == ()
    assert plan.planned_product_dependencies == ()


# =========================================================
# Persistent registered Artwork dependencies
# =========================================================


def test_shape_can_consume_persistent_registered_artwork_without_source(
    tmp_path: Path,
) -> None:
    """
    Persistent registered vector Artwork satisfies Shape without its source.

    Once Artwork's registered vector manifest and component geometry persist,
    Shape does not require the original raster source merely to consume that
    registered product.
    """

    write_artifact_config(
        "artwork-example",
        {
            "model": "artwork",
            "source": "missing-source.png",
        },
        project_root=tmp_path,
    )

    write_artifact_config(
        "shape-example",
        {
            "model": "shape",
            "product_dependencies": {
                "manifest": {
                    "model": "artwork",
                    "stage": "vector",
                    "product": "manifest",
                    "artifact": "artwork-example",
                    "realization": "artwork_default",
                },
            },
        },
        project_root=tmp_path,
    )

    vector_directory = (
        tmp_path / "artifacts" / "artwork-example" / "artwork" / "artwork_default" / "30-vector"
    )

    vector_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    component = vector_directory / "color-1.svg"

    component.write_text(
        """
<svg
    xmlns="http://www.w3.org/2000/svg"
    width="100"
    height="100"
    viewBox="0 0 100 100"
>
    <rect
        x="10"
        y="10"
        width="80"
        height="80"
    />
</svg>
""".strip(),
        encoding="utf-8",
    )

    manifest = vector_directory / "products.json"

    manifest.write_text(
        json.dumps(
            {
                "registered_extent": {
                    "width": 100,
                    "height": 100,
                },
                "products": [
                    {
                        "index": 1,
                        "path": component.name,
                        "artifact_color": {
                            "index": 1,
                            "rgb": {
                                "red": 17,
                                "green": 43,
                                "blue": 91,
                            },
                        },
                        "printer_color": {
                            "name": "physical-blue",
                            "rgb": {
                                "red": 20,
                                "green": 40,
                                "blue": 90,
                            },
                        },
                        "distance": 1.25,
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    assert not (tmp_path / "missing-source.png").exists()

    plan = create_build_plan(
        "shape-example",
        project_root=tmp_path,
    )

    assert set(_dependencies_by_name(plan)) == {
        "manifest",
    }

    planned = _planned_dependencies_by_name(plan)

    # An explicitly selected persistent vector product must not cause
    # the historical raster source to be required.
    assert set(planned) == {"manifest"}
    assert len(plan.product_dependency_bindings) == 1

    dependency = planned["manifest"]

    assert dependency.binding.dependency.model == "artwork"
    assert dependency.binding.dependency.stage == "vector"
    assert dependency.binding.dependency.product == "manifest"

    assert dependency.binding.artifact == "artwork-example"
    assert dependency.binding.realization == "artwork_default"

    assert dependency.path == manifest

    assert tuple(stage.name for stage in plan.stages) == (
        "structure",
        "compose",
        "extrude",
        "package",
    )


def test_shape_uses_same_artifact_default_artwork_when_available(
    tmp_path: Path,
) -> None:
    """
    Canonical Shape binds the same Artifact's canonical Artwork.

    The default Artwork representation is vector, so Shape selects
    only the registered vector manifest.
    """
    artifact_id = "example"

    write_artifact_config(
        artifact_id,
        {
            "source": "artifact.png",
        },
        project_root=tmp_path,
    )

    plan = create_build_plan(
        artifact_id,
        realization="shape_default",
        project_root=tmp_path,
    )

    # Only the vector representation is selected.
    assert set(_dependencies_by_name(plan)) == {
        "manifest",
    }

    planned = _planned_dependencies_by_name(plan)

    assert set(planned) == {
        "manifest",
    }

    assert len(plan.product_dependency_bindings) == 1

    vector = planned["manifest"]

    assert vector.binding.dependency.model == "artwork"
    assert vector.binding.dependency.stage == "vector"
    assert vector.binding.dependency.product == "manifest"

    # The implicit binding uses the same Artifact and canonical
    # Artwork Realization.
    assert vector.binding.artifact == artifact_id
    assert vector.binding.realization == "artwork_default"

    # The alternative raster product is not selected.
    assert "raster_artwork" not in planned


def test_shape_without_artwork_leaves_artwork_dependency_unbound(
    tmp_path: Path,
) -> None:
    """
    Shape remains valid when its Artifact has no Artwork source.

    Both Artwork representations are optional. Without an available
    producer, neither alternative is selected or bound.
    """
    artifact_id = "shape-only"

    write_artifact_config(
        artifact_id,
        {
            "model": "shape",
        },
        project_root=tmp_path,
    )

    plan = create_build_plan(
        artifact_id,
        project_root=tmp_path,
    )

    # No Artwork representation is selected.
    assert _dependencies_by_name(plan) == {}

    # No producer is bound or planned.
    assert plan.product_dependency_bindings == ()
    assert plan.planned_product_dependencies == ()

    # Shape remains independently buildable.
    assert tuple(stage.name for stage in plan.stages) == (
        "structure",
        "compose",
        "extrude",
        "package",
    )
