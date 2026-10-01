"""
End-to-end acceptance tests for Shape Inner Ridge production.
"""

# File: tests/acceptance/test_inner_ridge_build.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import pytest

from lowkey_artifact_builder.config import write_artifact_config
from lowkey_artifact_builder.engine import (
    create_build_plans,
    execute_dependency_build,
)
from lowkey_artifact_builder.formats.threemf import (
    CORE_NS,
    component_name,
)


@pytest.mark.slow
def test_shape_inner_ridge_survives_complete_build_value_chain(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """
    Enabled Inner Ridge survives the complete Shape manufacturing value chain.

    Compose establishes Inner Ridge registered geometry and makes its inside
    boundary the current available interior. Extrude preserves Inner Ridge as
    an independently identifiable physical component. Package resolves its
    Shape-owned physical color without merging that component into the base or
    Outer Ridge.

    This acceptance test intentionally exercises those major stage boundaries
    through normal planning and dependency-aware execution rather than
    repeating the detailed geometry contracts owned by focused stage tests.
    """

    project_root = tmp_path

    monkeypatch.chdir(
        project_root,
    )

    artifact_id = "inner-ridge-shape"

    # -----------------------------------------------------
    # Configure representative Shape
    # -----------------------------------------------------

    write_artifact_config(
        artifact_id,
        {
            "realizations": {
                "shape_default": {
                    "shape_geometry": "circle",
                    "shape_size": 100.0,
                    "shape_base_raise": 2.0,
                    "shape_base_color": "test-white",
                    "shape_outer_ridge_width": 5.0,
                    "shape_outer_ridge_raise": 1.0,
                    "shape_outer_ridge_style": "integrated",
                    "shape_outer_ridge_color": "test-red",
                    "shape_inner_ridge_width": 2.0,
                    "shape_inner_ridge_raise": 1.5,
                    "shape_inner_to_outer_ridge_dist": 10.0,
                    "shape_inner_ridge_color": "test-blue",
                },
            },
        },
        project_root=project_root,
    )

    # -----------------------------------------------------
    # Plan and execute through public engine boundaries
    # -----------------------------------------------------

    plans = create_build_plans(
        artifact_id,
        model_name="shape",
        variant_name="default",
        project_root=project_root,
    )

    assert len(plans) == 1

    plan = plans[0]

    assert plan.artifact_id == artifact_id
    assert plan.model_name == "shape"
    assert plan.realization_name == "shape_default"

    assert tuple(stage.spec.name for stage in plan.stages) == (
        "structure",
        "compose",
        "extrude",
        "package",
    )

    execute_dependency_build(
        plan,
    )

    shape_root = project_root / "artifacts" / artifact_id / "shape" / "shape_default"

    composition = shape_root / "20-compose" / "composition.svg"
    extrude_manifest = shape_root / "30-extrude" / "products.json"
    inner_ridge = shape_root / "30-extrude" / "inner-ridge.stl"
    artifact = shape_root / "40-package" / "artifact.3mf"

    assert composition.is_file()
    assert extrude_manifest.is_file()
    assert inner_ridge.is_file()
    assert inner_ridge.stat().st_size > 0
    assert artifact.is_file()
    assert artifact.stat().st_size > 0
    assert zipfile.is_zipfile(
        artifact,
    )

    # -----------------------------------------------------
    # Compose: semantic Inner Ridge geometry exists and
    # becomes the current registered interior boundary
    # -----------------------------------------------------

    composition_root = ET.parse(
        composition,
    ).getroot()

    elements_by_id = {
        element.get("id"): element
        for element in composition_root.iter()
        if element.get("id") is not None
    }

    assert "ridge-inner-boundary" in elements_by_id
    assert "inner-ridge-outer-boundary" in elements_by_id
    assert "inner-ridge-inner-boundary" in elements_by_id

    outer_ridge_inner = elements_by_id["ridge-inner-boundary"]
    inner_ridge_outer = elements_by_id["inner-ridge-outer-boundary"]
    inner_ridge_inner = elements_by_id["inner-ridge-inner-boundary"]

    assert float(outer_ridge_inner.get("r", "nan")) == pytest.approx(
        0.45,
    )
    assert float(inner_ridge_outer.get("r", "nan")) == pytest.approx(
        0.35,
    )
    assert float(inner_ridge_inner.get("r", "nan")) == pytest.approx(
        0.33,
    )

    # -----------------------------------------------------
    # Extrude: Inner Ridge remains an independent physical
    # component with no Package-owned color assignment
    # -----------------------------------------------------

    extrusion_data = json.loads(
        extrude_manifest.read_text(
            encoding="utf-8",
        )
    )

    components = extrusion_data["components"]

    assert isinstance(
        components,
        list,
    )

    components_by_name = {component["name"]: component for component in components}

    assert components_by_name["inner-ridge"] == {
        "name": "inner-ridge",
        "path": "inner-ridge.stl",
    }

    # -----------------------------------------------------
    # Package: Inner Ridge keeps independent component
    # identity and receives its configured physical color
    # -----------------------------------------------------

    with zipfile.ZipFile(
        artifact,
    ) as archive:
        model_name = next(
            name
            for name in archive.namelist()
            if name.startswith("3D/") and name.endswith(".model")
        )

        model = ET.fromstring(
            archive.read(
                model_name,
            )
        )

    objects = model.findall(
        f".//{{{CORE_NS}}}object",
    )

    materials = model.findall(
        f".//{{{CORE_NS}}}basematerials",
    )

    objects_by_name = {object_.get("name"): object_ for object_ in objects}

    base_name = component_name(
        artifact_id,
        "base",
        "test-white",
    )
    outer_ridge_name = component_name(
        artifact_id,
        "ridge",
        "test-red",
    )
    inner_ridge_name = component_name(
        artifact_id,
        "inner-ridge",
        "test-blue",
    )

    assert base_name in objects_by_name
    assert outer_ridge_name in objects_by_name
    assert inner_ridge_name in objects_by_name

    base_object = objects_by_name[base_name]
    outer_ridge_object = objects_by_name[outer_ridge_name]
    inner_ridge_object = objects_by_name[inner_ridge_name]

    assert (
        len(
            {
                base_object.get("id"),
                outer_ridge_object.get("id"),
                inner_ridge_object.get("id"),
            }
        )
        == 3
    )

    materials_by_id = {material.get("id"): material for material in materials}

    inner_ridge_material_id = inner_ridge_object.get(
        "pid",
    )

    assert inner_ridge_material_id is not None
    assert inner_ridge_material_id in materials_by_id

    inner_ridge_material = materials_by_id[inner_ridge_material_id]

    inner_ridge_color = inner_ridge_material.find(
        f"{{{CORE_NS}}}base",
    )

    assert inner_ridge_color is not None
    assert inner_ridge_color.get("name") == "test-blue"
    assert inner_ridge_color.get("displaycolor") == "#0000FF"
    assert inner_ridge_object.get("pindex") == "0"
