"""
Architectural dependency tests for the Shape model.

Shape may consume persistent registered Artwork without depending on Artwork's
physical dimensionalization or packaging stages.

A persistent registered Artwork product is sufficient to satisfy Shape's
cross-artifact dependency. Historical source inputs and configuration needed
only to reproduce that product do not participate when the registered product
already exists.
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
from lowkey_artifact_builder.engine import create_build_plan

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
# Persistent registered Artwork dependencies
# =========================================================


def test_shape_can_consume_persistent_registered_artwork_without_source(
    tmp_path: Path,
) -> None:
    """
    Persistent registered Artwork satisfies Shape without its historical source.

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
                    "realization": "default",
                },
            },
        },
        project_root=tmp_path,
    )

    vector_directory = (
        tmp_path / "artifacts" / "artwork-example" / "artwork" / "default" / "30-vector"
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

    assert len(plan.product_dependencies) == 1
    assert len(plan.product_dependency_bindings) == 1
    assert len(plan.planned_product_dependencies) == 1

    dependency = plan.planned_product_dependencies[0]

    assert dependency.binding.dependency.model == "artwork"
    assert dependency.binding.dependency.stage == "vector"
    assert dependency.binding.dependency.product == "manifest"

    assert dependency.binding.artifact == "artwork-example"
    assert dependency.binding.realization == "default"

    assert dependency.path == manifest

    assert tuple(stage.name for stage in plan.stages) == (
        "structure",
        "compose",
        "extrude",
        "package",
    )
