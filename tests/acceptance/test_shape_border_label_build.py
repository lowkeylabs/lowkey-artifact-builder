"""
End-to-end acceptance tests for Shape Border Label production.
"""

# File: tests/acceptance/test_border_label_build.py
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
def test_shape_border_labels_survive_complete_build_value_chain(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """
    Enabled Top and Bottom Border Labels survive the complete Shape
    manufacturing value chain.

    Compose establishes the shared Border Label region, preserves independent
    Top and Bottom semantic paths, and materializes their registered glyph
    geometry as persistent products. Extrude consumes those products and
    preserves Top and Bottom as independently identifiable physical
    components. Package resolves their independent Shape-owned physical colors
    without merging either label into the Base or Outer Ridge.

    This acceptance test intentionally exercises those major stage boundaries
    through normal planning and dependency-aware execution rather than
    repeating the detailed fitting, path, and geometry contracts owned by
    focused feature tests.
    """

    project_root = tmp_path

    monkeypatch.chdir(
        project_root,
    )

    artifact_id = "border-label-shape"

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
                    "shape_inner_ridge_width": 0.0,
                    "shape_border_label_width": 1.0,
                    "shape_border_label_max_glyph_height": 5.0,
                    "shape_border_label_arc_degrees": 140.0,
                    "shape_border_label_end_margin": 1.0,
                    "shape_border_label_font_family": "DejaVu Sans",
                    "shape_top_border_label_text": "RICHMOND",
                    "shape_top_border_label_raise": 1.0,
                    "shape_top_border_label_color": "test-blue",
                    "shape_bottom_border_label_text": "VIRGINIA",
                    "shape_bottom_border_label_raise": 1.5,
                    "shape_bottom_border_label_color": "test-green",
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

    compose_root = shape_root / "20-compose"

    extrude_root = shape_root / "30-extrude"

    package_root = shape_root / "40-package"

    composition = compose_root / "composition.svg"

    compose_manifest = compose_root / "products.json"

    top_registered_label = compose_root / "top-border-label.svg"

    bottom_registered_label = compose_root / "bottom-border-label.svg"

    extrude_manifest = extrude_root / "products.json"

    top_border_label = extrude_root / "top-border-label.stl"

    bottom_border_label = extrude_root / "bottom-border-label.stl"

    artifact = package_root / "artifact.3mf"

    assert composition.is_file()
    assert compose_manifest.is_file()

    assert top_registered_label.is_file()
    assert top_registered_label.stat().st_size > 0

    assert bottom_registered_label.is_file()
    assert bottom_registered_label.stat().st_size > 0

    assert extrude_manifest.is_file()

    assert top_border_label.is_file()
    assert top_border_label.stat().st_size > 0

    assert bottom_border_label.is_file()
    assert bottom_border_label.stat().st_size > 0

    assert artifact.is_file()
    assert artifact.stat().st_size > 0

    assert zipfile.is_zipfile(
        artifact,
    )

    # -----------------------------------------------------
    # Compose: semantic Border Label geometry survives and
    # persistent registered glyph products are published
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

    assert "border-label-bottom-baseline" in elements_by_id

    assert "border-label-top-baseline" in elements_by_id

    assert "border-label-inner-boundary" in elements_by_id

    assert "top-border-label-path" in elements_by_id

    assert "bottom-border-label-path" in elements_by_id

    outer_ridge_inner = elements_by_id["ridge-inner-boundary"]

    bottom_baseline = elements_by_id["border-label-bottom-baseline"]

    top_baseline = elements_by_id["border-label-top-baseline"]

    border_label_inner = elements_by_id["border-label-inner-boundary"]

    assert float(
        outer_ridge_inner.get(
            "r",
            "nan",
        )
    ) == pytest.approx(
        0.45,
    )

    assert float(
        bottom_baseline.get(
            "r",
            "nan",
        )
    ) == pytest.approx(
        0.44,
    )

    assert float(
        top_baseline.get(
            "r",
            "nan",
        )
    ) == pytest.approx(
        0.39,
    )

    assert float(
        border_label_inner.get(
            "r",
            "nan",
        )
    ) == pytest.approx(
        0.38,
    )

    compose_data = json.loads(
        compose_manifest.read_text(
            encoding="utf-8",
        )
    )

    border_labels = compose_data["border_labels"]

    assert border_labels["top"] == {
        "path": "top-border-label.svg",
    }

    assert border_labels["bottom"] == {
        "path": "bottom-border-label.svg",
    }

    # Persistent registered label products contain ordinary
    # path geometry rather than unresolved text/textPath
    # typography.

    for registered_label in (
        top_registered_label,
        bottom_registered_label,
    ):
        registered_root = ET.parse(
            registered_label,
        ).getroot()

        text_elements = registered_root.findall(
            f".//{{{registered_root.tag.split('}')[0][1:]}}}text"
        )

        text_path_elements = registered_root.findall(
            f".//{{{registered_root.tag.split('}')[0][1:]}}}textPath"
        )

        path_elements = registered_root.findall(
            f".//{{{registered_root.tag.split('}')[0][1:]}}}path"
        )

        assert not text_elements
        assert not text_path_elements
        assert path_elements

    # -----------------------------------------------------
    # Extrude: Top and Bottom remain independent physical
    # components with no Package-owned color assignment
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

    assert components_by_name["top-border-label"] == {
        "name": "top-border-label",
        "path": "top-border-label.stl",
    }

    assert components_by_name["bottom-border-label"] == {
        "name": "bottom-border-label",
        "path": "bottom-border-label.stl",
    }

    # -----------------------------------------------------
    # Package: Top and Bottom keep independent component
    # identity and receive their configured physical colors
    # -----------------------------------------------------

    with zipfile.ZipFile(
        artifact,
    ) as archive:
        model_name = next(
            name
            for name in archive.namelist()
            if (name.startswith("3D/") and name.endswith(".model"))
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

    top_border_label_name = component_name(
        artifact_id,
        "top-border-label",
        "test-blue",
    )

    bottom_border_label_name = component_name(
        artifact_id,
        "bottom-border-label",
        "test-green",
    )

    assert base_name in objects_by_name
    assert outer_ridge_name in objects_by_name
    assert top_border_label_name in objects_by_name
    assert bottom_border_label_name in objects_by_name

    base_object = objects_by_name[base_name]

    outer_ridge_object = objects_by_name[outer_ridge_name]

    top_border_label_object = objects_by_name[top_border_label_name]

    bottom_border_label_object = objects_by_name[bottom_border_label_name]

    assert (
        len(
            {
                base_object.get("id"),
                outer_ridge_object.get("id"),
                top_border_label_object.get("id"),
                bottom_border_label_object.get("id"),
            }
        )
        == 4
    )

    materials_by_id = {material.get("id"): material for material in materials}

    top_material_id = top_border_label_object.get(
        "pid",
    )

    bottom_material_id = bottom_border_label_object.get(
        "pid",
    )

    assert top_material_id is not None
    assert bottom_material_id is not None

    assert top_material_id in materials_by_id

    assert bottom_material_id in materials_by_id

    top_material = materials_by_id[top_material_id]

    bottom_material = materials_by_id[bottom_material_id]

    top_color = top_material.find(
        f"{{{CORE_NS}}}base",
    )

    bottom_color = bottom_material.find(
        f"{{{CORE_NS}}}base",
    )

    assert top_color is not None
    assert bottom_color is not None

    assert top_color.get("name") == "test-blue"

    assert top_color.get("displaycolor") == "#0000FF"

    assert (
        top_border_label_object.get(
            "pindex",
        )
        == "0"
    )

    assert bottom_color.get("name") == "test-green"

    assert bottom_color.get("displaycolor") == "#00FF00"

    assert (
        bottom_border_label_object.get(
            "pindex",
        )
        == "0"
    )
