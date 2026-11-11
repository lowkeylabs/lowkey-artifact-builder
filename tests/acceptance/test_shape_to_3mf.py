"""
End-to-end acceptance tests for Shape artifact production.
"""
# File: tests/acceptance/test_shape_to_3mf.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0


# DEFERRED — SHAPE physical realization
#
# The acceptance tests prefixed with deferred_test_ document
# intended future Extrude behavior.
#
# They are intentionally excluded from pytest collection while
# SVG manufacturing development takes priority.
#
# See FUTURE.md:
# "SHAPE Physical Realization — Optional Base and
# Independent Components"
#
# Restore the test_ prefix when this work is promoted
# into CHANGEPLAN.md.

from __future__ import annotations

import json
import shutil
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import pytest
from click.testing import CliRunner

from lowkey_artifact_builder.cli._main import cli
from lowkey_artifact_builder.config import (
    configure_artifact,
    materialize_artifact,
    update_artifact_config,
    write_artifact_config,
)
from lowkey_artifact_builder.engine import (
    create_build_plans,
    execute_dependency_build,
)
from lowkey_artifact_builder.formats.threemf import (
    CORE_NS,
    component_name,
)

# ---
#
# ---


def _materialize_artwork_source(
    artifact_id: str,
    *,
    project_root: Path,
) -> None:
    """
    Establish one Artwork-producing Artifact from the acceptance PNG.

    The known-good acceptance artwork is preserved at the canonical
    ingestion boundary and then materialized into the Artifact workspace
    before direct engine planning or dependency execution.
    """

    repository_root = Path(__file__).resolve().parents[2]

    fixture_source = repository_root / "tests" / "assets" / "nydeli-clean.png"

    assert fixture_source.is_file(), f"Acceptance artwork does not exist: {fixture_source}"

    originals_directory = project_root / "originals"

    originals_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    original = originals_directory / f"{artifact_id}.png"

    shutil.copy2(
        fixture_source,
        original,
    )

    materialize_artifact(
        artifact_id,
        project_root=project_root,
    )


# =========================================================
# Acceptance tests
# =========================================================


@pytest.mark.slow
def test_shape_builds_complete_3mf_without_artwork(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """
    A Shape without source Artwork produces a complete 3MF.

    Base and Artwork Region Fill are distinct Shape-owned components.
    Neither requires an Artwork dependency.
    """
    project_root = tmp_path
    monkeypatch.chdir(project_root)

    write_artifact_config(
        "testshape",
        {},
        project_root=project_root,
    )

    plans = create_build_plans(
        "testshape",
        model_name="shape",
        variant_name="default",
        project_root=project_root,
    )

    assert len(plans) == 1
    plan = plans[0]

    assert plan.artifact_id == "testshape"
    assert plan.model_name == "shape"
    assert plan.realization_name == "shape_default"
    assert plan.artifact_dir.is_relative_to(project_root)

    assert tuple(stage.spec.name for stage in plan.stages) == (
        "structure",
        "compose",
        "extrude",
        "package",
    )

    result = CliRunner().invoke(
        cli,
        [
            "build",
            "testshape",
            "--realization",
            "shape_default",
        ],
    )

    assert result.exit_code == 0, f"Shape build failed:\n{result.output}\n{result.exception!r}"

    package_stage = next(stage for stage in plan.stages if stage.spec.name == "package")

    output = next(
        product.path for product in package_stage.products if product.spec.name == "artifact"
    )

    assert output.is_relative_to(project_root)
    assert output.is_file()
    assert output.stat().st_size > 0
    assert zipfile.is_zipfile(output)

    with zipfile.ZipFile(output) as archive:
        names = set(archive.namelist())

        model_names = [name for name in names if name.startswith("3D/") and name.endswith(".model")]

        assert "[Content_Types].xml" in names
        assert len(model_names) == 1

        model = ET.fromstring(archive.read(model_names[0]))

    objects = model.findall(f".//{{{CORE_NS}}}object")
    materials = model.findall(f".//{{{CORE_NS}}}basematerials")

    objects_by_name = {object_.get("name"): object_ for object_ in objects}

    materials_by_id = {material.get("id"): material for material in materials}

    base_name = component_name(
        "testshape",
        "base",
        "white",
    )

    region_name = component_name(
        "testshape",
        "artwork-region-fill",
        "white",
    )

    assert set(objects_by_name) == {
        base_name,
        region_name,
    }

    assert materials_by_id

    for name in (base_name, region_name):
        object_ = objects_by_name[name]

        material_id = object_.get("pid")
        assert material_id is not None
        assert material_id in materials_by_id

        material = materials_by_id[material_id]
        color = material.find(f"{{{CORE_NS}}}base")

        assert color is not None
        assert color.get("name") == "white"
        assert object_.get("pindex") == "0"

        assert object_.findall(f".//{{{CORE_NS}}}vertex")
        assert object_.findall(f".//{{{CORE_NS}}}triangle")

    assert objects_by_name[base_name].get("id") != objects_by_name[region_name].get("id")


@pytest.mark.slow
@pytest.mark.parametrize(
    "ridge_style",
    [
        "separate",
        "integrated",
    ],
)
def deferred_test_shape_ridge_preserves_distinct_component_colors(
    tmp_path: Path,
    monkeypatch,
    ridge_style: str,
) -> None:
    """
    A physical Shape ridge may retain a semantic color distinct from
    the base through the complete build pipeline.

    Both separate ridges and positive integrated ridges produce an
    independently identifiable ridge-color volume in artifact.3mf.
    """

    project_root = tmp_path

    monkeypatch.chdir(
        project_root,
    )

    runner = CliRunner()

    # -----------------------------------------------------
    # Configure Shape default Realization
    # -----------------------------------------------------

    write_artifact_config(
        "colored-shape",
        {
            "realizations": {
                "shape_default": {
                    "shape_base_color": "test-white",
                    "shape_outer_ridge_width": 2.0,
                    "shape_outer_ridge_raise": 1.0,
                    "shape_outer_ridge_style": ridge_style,
                    "shape_outer_ridge_color": "test-red",
                },
            },
        },
        project_root=project_root,
    )

    # -----------------------------------------------------
    # Plan the Shape Variant underlying the Realization
    # -----------------------------------------------------

    plans = create_build_plans(
        "colored-shape",
        model_name="shape",
        variant_name="default",
        project_root=project_root,
    )

    assert len(plans) == 1

    plan = plans[0]

    assert plan.artifact_id == "colored-shape"
    assert plan.model_name == "shape"
    assert plan.realization_name == "shape_default"

    # -----------------------------------------------------
    # Build canonical Shape Realization through public CLI
    # -----------------------------------------------------

    build_result = runner.invoke(
        cli,
        [
            "build",
            "colored-shape",
            "--realization",
            "shape_default",
        ],
    )

    assert build_result.exit_code == 0, (
        f"Shape build failed:\n{build_result.output}\n{build_result.exception!r}"
    )

    # -----------------------------------------------------
    # Locate packaged artifact
    # -----------------------------------------------------

    package_stage = next(stage for stage in plan.stages if stage.spec.name == "package")

    artifact_product = next(
        product for product in package_stage.products if product.spec.name == "artifact"
    )

    output = artifact_product.path

    assert output.is_file(), f"Build did not produce the expected Shape 3MF: {output}"

    assert output.stat().st_size > 0
    assert zipfile.is_zipfile(output)

    # -----------------------------------------------------
    # Inspect packaged component identities and colors
    # -----------------------------------------------------

    with zipfile.ZipFile(
        output,
    ) as archive:
        names = set(
            archive.namelist(),
        )

        model_name = next(
            name for name in names if name.startswith("3D/") and name.endswith(".model")
        )

        model_data = archive.read(
            model_name,
        )

    assert "[Content_Types].xml" in names

    model = ET.fromstring(
        model_data,
    )

    objects = model.findall(
        f".//{{{CORE_NS}}}object",
    )

    materials = model.findall(
        f".//{{{CORE_NS}}}basematerials",
    )

    objects_by_name = {obj.get("name"): obj for obj in objects}

    materials_by_id = {material.get("id"): material for material in materials}

    base_object = objects_by_name[component_name("colored-shape", "base", "test-white")]

    ridge_object = objects_by_name[component_name("colored-shape", "ridge", "test-red")]

    assert base_object is not ridge_object

    base_material = materials_by_id[base_object.get("pid")]

    ridge_material = materials_by_id[ridge_object.get("pid")]

    base_color = base_material.find(
        f"{{{CORE_NS}}}base",
    )

    ridge_color = ridge_material.find(
        f"{{{CORE_NS}}}base",
    )

    assert base_color is not None
    assert ridge_color is not None

    assert base_color.get("name") == "test-white"
    assert ridge_color.get("name") == "test-red"

    assert base_object.get("pindex") == "0"
    assert ridge_object.get("pindex") == "0"


@pytest.mark.slow
@pytest.mark.parametrize(
    ("color_overrides", "expected_top", "expected_bottom"),
    [
        pytest.param(
            {"shape_label_color": "test-red"},
            "test-red",
            "test-red",
            id="shared-label-color",
        ),
        pytest.param(
            {
                "shape_label_color": "test-red",
                "shape_top_border_label_color": "test-green",
            },
            "test-green",
            "test-red",
            id="top-label-override",
        ),
    ],
)
def test_shape_shared_label_color_survives_3mf_packaging(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    color_overrides: dict[str, str],
    expected_top: str,
    expected_bottom: str,
) -> None:
    """
    SHAPE shared label colors survive complete 3MF manufacturing.

    Both Border Labels inherit shape_label_color unless independently
    overridden. Package preserves their component identities and
    assigns the expected physical materials.

    The Base color remains independent of label colors.
    """
    project_root = tmp_path
    monkeypatch.chdir(project_root)

    artifact_id = "shared-label-shape"

    # -----------------------------------------------------
    # Configure Shape with two physical Border Labels
    # -----------------------------------------------------

    write_artifact_config(
        artifact_id,
        {
            "realizations": {
                "shape_default": {
                    "shape_geometry": "circle",
                    "shape_size": 100.0,
                    "shape_base_color": "test-white",
                    "shape_border_label_font_family": "DejaVu Sans",
                    "shape_outer_ridge_width": 2.0,
                    "shape_top_border_label_text": "TOP",
                    "shape_bottom_border_label_text": "BOTTOM",
                    "shape_top_border_label_raise": 1.0,
                    "shape_bottom_border_label_raise": 1.0,
                    **color_overrides,
                },
            },
        },
        project_root=project_root,
    )

    # -----------------------------------------------------
    # Build through normal Shape manufacturing
    # -----------------------------------------------------

    plans = create_build_plans(
        artifact_id,
        model_name="shape",
        variant_name="default",
        project_root=project_root,
    )

    assert len(plans) == 1

    plan = plans[0]

    assert plan.model_name == "shape"
    assert plan.realization_name == "shape_default"

    execute_dependency_build(plan)

    package_stage = next(stage for stage in plan.stages if stage.spec.name == "package")

    artifact_product = next(
        product for product in package_stage.products if product.spec.name == "artifact"
    )

    artifact = artifact_product.path

    assert artifact.is_file()
    assert artifact.stat().st_size > 0
    assert zipfile.is_zipfile(artifact)

    # -----------------------------------------------------
    # Inspect packaged 3MF objects and materials
    # -----------------------------------------------------

    with zipfile.ZipFile(artifact) as archive:
        names = set(archive.namelist())

        assert "[Content_Types].xml" in names

        model_names = [name for name in names if name.startswith("3D/") and name.endswith(".model")]

        assert len(model_names) == 1

        model = ET.fromstring(archive.read(model_names[0]))

    objects = model.findall(f".//{{{CORE_NS}}}object")

    materials = model.findall(f".//{{{CORE_NS}}}basematerials")

    objects_by_name = {object_.get("name"): object_ for object_ in objects}

    materials_by_id = {material.get("id"): material for material in materials}

    # -----------------------------------------------------
    # Verify distinct component identities and colors
    # -----------------------------------------------------

    expected_components = {
        "base": ("test-white", "#FFFFFF"),
        "top-border-label": (
            expected_top,
            {
                "test-red": "#FF0000",
                "test-green": "#00FF00",
            }[expected_top],
        ),
        "bottom-border-label": (
            expected_bottom,
            {
                "test-red": "#FF0000",
                "test-green": "#00FF00",
            }[expected_bottom],
        ),
    }

    component_objects = {}

    for identity, (color_name, expected_rgb) in expected_components.items():
        name = component_name(
            artifact_id,
            identity,
            color_name,
        )

        assert name in objects_by_name, (
            f"Missing packaged component {name!r}; "
            f"available objects: {sorted(str(n) for n in objects_by_name)}"
        )

        object_ = objects_by_name[name]
        component_objects[identity] = object_

        material_id = object_.get("pid")

        assert material_id is not None
        assert material_id in materials_by_id

        material = materials_by_id[material_id]

        color = material.find(f"{{{CORE_NS}}}base")

        assert color is not None
        assert color.get("name") == color_name
        assert color.get("displaycolor") == expected_rgb

        assert object_.get("pindex") == "0"

        # Each component must contain manufactured mesh geometry.
        assert object_.findall(f".//{{{CORE_NS}}}vertex")
        assert object_.findall(f".//{{{CORE_NS}}}triangle")

    # -----------------------------------------------------
    # Shared material does not merge component identities
    # -----------------------------------------------------

    object_ids = {object_.get("id") for object_ in component_objects.values()}

    assert None not in object_ids
    assert len(object_ids) == 3


@pytest.mark.slow
def test_shape_component_colors_do_not_change_geometry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Shape semantic colors affect presentation and material assignment,
    but do not affect registered or manufactured geometry.

    Swapping Base and Outer Ridge colors changes canonical SVG fills
    and packaged 3MF material assignments without changing geometry.

    Use an integrated ridge so this test isolates color invariance
    rather than separate-ridge extrusion behavior.
    """
    project_root = tmp_path
    monkeypatch.chdir(project_root)

    configurations = {
        "white-red-shape": ("test-white", "test-red"),
        "red-white-shape": ("test-red", "test-white"),
    }

    svg_roots: dict[str, ET.Element] = {}
    packaged_geometry = {}

    for artifact_id, (base_color, ridge_color) in configurations.items():
        write_artifact_config(
            artifact_id,
            {
                "realizations": {
                    "shape_default": {
                        "shape_geometry": "circle",
                        "shape_size": 100.0,
                        "shape_base_color": base_color,
                        "shape_outer_ridge_width": 2.0,
                        "shape_outer_ridge_raise": 1.0,
                        "shape_outer_ridge_style": "integrated",
                        "shape_outer_ridge_color": ridge_color,
                    },
                },
            },
            project_root=project_root,
        )

        plans = create_build_plans(
            artifact_id,
            model_name="shape",
            variant_name="default",
            project_root=project_root,
        )

        assert len(plans) == 1
        plan = plans[0]

        assert plan.model_name == "shape"
        assert plan.realization_name == "shape_default"

        execute_dependency_build(plan)

        compose_stage = next(stage for stage in plan.stages if stage.spec.name == "compose")

        svg_product = next(
            product for product in compose_stage.products if product.spec.name == "artifact"
        )

        assert svg_product.path.is_file()

        svg_roots[artifact_id] = ET.parse(svg_product.path).getroot()

        package_stage = next(stage for stage in plan.stages if stage.spec.name == "package")

        package_product = next(
            product for product in package_stage.products if product.spec.name == "artifact"
        )

        assert package_product.path.is_file()
        assert zipfile.is_zipfile(package_product.path)

        with zipfile.ZipFile(package_product.path) as archive:
            model_names = [
                name
                for name in archive.namelist()
                if name.startswith("3D/") and name.endswith(".model")
            ]

            assert len(model_names) == 1

            model = ET.fromstring(archive.read(model_names[0]))

        objects = model.findall(f".//{{{CORE_NS}}}object")

        materials = model.findall(f".//{{{CORE_NS}}}basematerials")

        objects_by_name = {object_.get("name"): object_ for object_ in objects}

        materials_by_id = {material.get("id"): material for material in materials}

        geometry = {}

        for identity, color_name in (
            ("base", base_color),
            ("ridge", ridge_color),
        ):
            name = component_name(
                artifact_id,
                identity,
                color_name,
            )

            assert name in objects_by_name

            object_ = objects_by_name[name]

            material_id = object_.get("pid")

            assert material_id is not None
            assert material_id in materials_by_id

            material = materials_by_id[material_id]

            color = material.find(f"{{{CORE_NS}}}base")

            assert color is not None
            assert color.get("name") == color_name

            expected_rgb = {
                "test-white": "#FFFFFF",
                "test-red": "#FF0000",
            }[color_name]

            assert color.get("displaycolor") == expected_rgb
            assert object_.get("pindex") == "0"

            vertices = tuple(
                (
                    vertex.get("x"),
                    vertex.get("y"),
                    vertex.get("z"),
                )
                for vertex in object_.findall(f".//{{{CORE_NS}}}vertex")
            )

            triangles = tuple(
                (
                    triangle.get("v1"),
                    triangle.get("v2"),
                    triangle.get("v3"),
                )
                for triangle in object_.findall(f".//{{{CORE_NS}}}triangle")
            )

            assert vertices
            assert triangles

            geometry[identity] = (
                vertices,
                triangles,
            )

        packaged_geometry[artifact_id] = geometry

    white_red = svg_roots["white-red-shape"]
    red_white = svg_roots["red-white-shape"]

    namespace = "http://www.w3.org/2000/svg"

    def component_fill(
        root: ET.Element,
        identity: str,
    ) -> str:
        component = root.find(f".//{{{namespace}}}path[@id='{identity}']")

        assert component is not None

        fill = component.get("fill")

        assert fill is not None
        return fill

    # Presentation reflects the configured colors.
    assert (
        component_fill(
            white_red,
            "outer-ridge",
        )
        == "#ff0000"
    )

    assert (
        component_fill(
            red_white,
            "outer-ridge",
        )
        == "#ffffff"
    )

    assert (
        component_fill(
            white_red,
            "artwork-region-fill",
        )
        == "#ffffff"
    )

    assert (
        component_fill(
            red_white,
            "artwork-region-fill",
        )
        == "#ff0000"
    )

    # Registered SVG geometry is independent of color.
    def geometry_only(root: ET.Element) -> bytes:
        copy = ET.fromstring(ET.tostring(root))

        for element in copy.iter():
            element.attrib.pop("fill", None)
            element.attrib.pop("stroke", None)

        return ET.tostring(copy)

    assert geometry_only(white_red) == geometry_only(red_white)

    # Physical component identities and meshes are preserved.
    assert packaged_geometry["white-red-shape"].keys() == {
        "base",
        "ridge",
    }

    assert packaged_geometry["red-white-shape"].keys() == {
        "base",
        "ridge",
    }

    assert packaged_geometry["white-red-shape"] == packaged_geometry["red-white-shape"]


@pytest.mark.slow
def test_shape_builds_complete_3mf_with_registered_artwork(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """
    Shape consumes registered Artwork and produces a complete 3MF.

    Only Artwork's reusable Vector representation is required.
    Shape-owned Artwork Region Fill must not be counted as
    incorporated source Artwork.
    """
    project_root = tmp_path
    monkeypatch.chdir(project_root)

    _materialize_artwork_source(
        "source-artwork",
        project_root=project_root,
    )

    write_artifact_config(
        "artwork-shape",
        {
            "realizations": {
                "shape_default": {
                    "shape_base_color": "test-white",
                },
            },
            "product_dependencies": {
                "manifest": {
                    "model": "artwork",
                    "stage": "vector",
                    "product": "manifest",
                    "artifact": "source-artwork",
                    "realization": "artwork_default",
                },
            },
        },
        project_root=project_root,
    )

    plans = create_build_plans(
        "artwork-shape",
        model_name="shape",
        variant_name="default",
        project_root=project_root,
    )

    assert len(plans) == 1
    plan = plans[0]

    assert plan.artifact_id == "artwork-shape"
    assert plan.model_name == "shape"
    assert plan.realization_name == "shape_default"

    assert tuple(stage.spec.name for stage in plan.stages) == (
        "structure",
        "compose",
        "extrude",
        "package",
    )

    execute_dependency_build(plan)

    artwork_root = project_root / "artifacts" / "source-artwork" / "artwork" / "artwork_default"

    assert (artwork_root / "10-prepare" / "trace.svg").is_file()
    assert (artwork_root / "20-raster" / "products.json").is_file()

    vector_manifest = artwork_root / "30-vector" / "products.json"
    assert vector_manifest.is_file()

    assert not (artwork_root / "40-extrude" / "products.json").exists()

    assert not (artwork_root / "50-package" / "artifact.3mf").exists()

    vector_data = json.loads(vector_manifest.read_text(encoding="utf-8"))

    artwork_products = vector_data["products"]

    assert isinstance(artwork_products, list)
    assert artwork_products

    for product in artwork_products:
        assert "printer_color" not in product
        assert "distance" not in product

        artifact_color = product.get("artifact_color")
        assert isinstance(artifact_color, dict)
        assert artifact_color["index"] == product["index"]

        rgb = artifact_color["rgb"]
        assert isinstance(rgb, dict)
        assert set(rgb) == {"red", "green", "blue"}

        for channel in ("red", "green", "blue"):
            assert isinstance(rgb[channel], int)
            assert 0 <= rgb[channel] <= 255

    package_stage = next(stage for stage in plan.stages if stage.spec.name == "package")

    output = next(
        product.path for product in package_stage.products if product.spec.name == "artifact"
    )

    assert output.is_file()
    assert output.stat().st_size > 0
    assert zipfile.is_zipfile(output)

    with zipfile.ZipFile(output) as archive:
        names = set(archive.namelist())

        assert "[Content_Types].xml" in names

        model_names = [name for name in names if name.startswith("3D/") and name.endswith(".model")]

        assert len(model_names) == 1

        model = ET.fromstring(archive.read(model_names[0]))

    objects = model.findall(f".//{{{CORE_NS}}}object")
    materials = model.findall(f".//{{{CORE_NS}}}basematerials")

    objects_by_name = {object_.get("name"): object_ for object_ in objects}

    materials_by_id = {material.get("id"): material for material in materials}

    base_name = component_name(
        "artwork-shape",
        "base",
        "test-white",
    )

    assert base_name in objects_by_name

    region_name = component_name(
        "artwork-shape",
        "artwork-region-fill",
        "test-white",
    )

    assert region_name in objects_by_name

    # Source Artwork is distinct from Shape-owned fill components.
    artwork_objects = {
        name: object_
        for name, object_ in objects_by_name.items()
        if name is not None
        and name.startswith("artwork-")
        and not name.startswith("artwork-region-fill")
        and not name.startswith("artwork-fill")
    }

    assert len(artwork_objects) == len(artwork_products)

    for product in artwork_products:
        identity = f"artwork-{product['index']}"

        matching_names = [name for name in artwork_objects if name.startswith(f"{identity} - ")]

        assert len(matching_names) == 1, (
            f"Expected one packaged object for {identity!r}; found {matching_names!r}"
        )

    assert materials_by_id

    for object_ in artwork_objects.values():
        pid = object_.get("pid")

        assert pid is not None
        assert pid in materials_by_id

        material = materials_by_id[pid]
        color = material.find(f"{{{CORE_NS}}}base")

        assert color is not None

        semantic_name = color.get("name")
        display_color = color.get("displaycolor")

        assert semantic_name
        assert display_color
        assert display_color.startswith("#")
        assert len(display_color) == 7

        assert object_.get("pindex") == "0"

        object_name = object_.get("name")
        assert object_name is not None
        assert object_name.endswith(f" - {semantic_name}")

        assert object_.findall(f".//{{{CORE_NS}}}vertex")
        assert object_.findall(f".//{{{CORE_NS}}}triangle")


@pytest.mark.slow
def test_shape_physical_change_reuses_registered_artwork(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """
    Shape physical changes reuse current registered Artwork.

    Changing Shape physical size rebuilds the Shape manufacturing path
    without repeating Artwork interpretation when the reusable registered
    Artwork vector product remains current.
    """

    project_root = tmp_path

    monkeypatch.chdir(
        project_root,
    )

    # -----------------------------------------------------
    # Create canonical Artwork producer
    # -----------------------------------------------------

    _materialize_artwork_source(
        "source-artwork",
        project_root=project_root,
    )

    # -----------------------------------------------------
    # Configure Shape consumer
    # -----------------------------------------------------

    write_artifact_config(
        "artwork-shape",
        {
            "realizations": {
                "shape_default": {
                    "shape_size": 100.0,
                },
            },
            "product_dependencies": {
                "manifest": {
                    "model": "artwork",
                    "stage": "vector",
                    "product": "manifest",
                    "artifact": "source-artwork",
                    "realization": "artwork_default",
                },
            },
        },
        project_root=project_root,
    )

    # -----------------------------------------------------
    # Build initial Shape
    # -----------------------------------------------------

    initial_plans = create_build_plans(
        "artwork-shape",
        model_name="shape",
        variant_name="default",
        project_root=project_root,
    )

    assert len(initial_plans) == 1

    initial_plan = initial_plans[0]

    assert initial_plan.model_name == "shape"
    assert initial_plan.realization_name == "shape_default"

    execute_dependency_build(
        initial_plan,
    )

    artwork_root = project_root / "artifacts" / "source-artwork" / "artwork" / "artwork_default"

    artwork_products = artwork_root / "30-vector" / "products.json"

    assert artwork_products.is_file()

    assert not (artwork_root / "40-extrude" / "products.json").exists()

    assert not (artwork_root / "50-package" / "artifact.3mf").exists()

    initial_vector_bytes = artwork_products.read_bytes()

    initial_component_bytes = {
        path.name: path.read_bytes() for path in (artwork_root / "30-vector").glob("*.svg")
    }

    assert initial_component_bytes

    # -----------------------------------------------------
    # Change only Shape physical size
    # -----------------------------------------------------

    update_artifact_config(
        "artwork-shape",
        {
            "realizations": {
                "shape_default": {
                    "shape_size": 90.0,
                },
            },
        },
        project_root=project_root,
    )

    resized_plans = create_build_plans(
        "artwork-shape",
        model_name="shape",
        variant_name="default",
        project_root=project_root,
    )

    assert len(resized_plans) == 1

    resized_plan = resized_plans[0]

    assert resized_plan.model_name == "shape"
    assert resized_plan.realization_name == "shape_default"

    assert resized_plan.resolver("shape_size") == 90.0

    execute_dependency_build(
        resized_plan,
    )

    # -----------------------------------------------------
    # Verify registered Artwork was reused unchanged
    # -----------------------------------------------------

    assert artwork_products.read_bytes() == initial_vector_bytes

    resized_component_bytes = {
        path.name: path.read_bytes() for path in (artwork_root / "30-vector").glob("*.svg")
    }

    assert resized_component_bytes == initial_component_bytes

    assert not (artwork_root / "40-extrude" / "products.json").exists()

    assert not (artwork_root / "50-package" / "artifact.3mf").exists()

    # -----------------------------------------------------
    # Verify resized Shape artifact exists
    # -----------------------------------------------------

    package_stage = next(stage for stage in resized_plan.stages if stage.spec.name == "package")

    artifact_product = next(
        product for product in package_stage.products if product.spec.name == "artifact"
    )

    output = artifact_product.path

    assert output.is_file()
    assert output.stat().st_size > 0
    assert zipfile.is_zipfile(
        output,
    )


@pytest.mark.slow
def test_registered_artwork_is_reused_across_different_shapes(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """
    One registered Artwork product can feed physically different Shapes.

    Building a second Shape with different geometry and physical size reuses
    the current registered Artwork representation without requiring standalone
    Artwork extrusion or packaging.
    """

    project_root = tmp_path

    monkeypatch.chdir(
        project_root,
    )

    _materialize_artwork_source(
        "source-artwork",
        project_root=project_root,
    )

    artwork_dependency = {
        "manifest": {
            "model": "artwork",
            "stage": "vector",
            "product": "manifest",
            "artifact": "source-artwork",
            "realization": "artwork_default",
        },
    }

    write_artifact_config(
        "circle-shape",
        {
            "realizations": {
                "shape_default": {
                    "shape_geometry": "circle",
                    "shape_size": 100.0,
                },
            },
            "product_dependencies": artwork_dependency,
        },
        project_root=project_root,
    )

    circle_plans = create_build_plans(
        "circle-shape",
        model_name="shape",
        variant_name="default",
        project_root=project_root,
    )

    assert len(circle_plans) == 1

    circle_plan = circle_plans[0]

    assert circle_plan.model_name == "shape"
    assert circle_plan.realization_name == "shape_default"

    execute_dependency_build(
        circle_plan,
    )

    artwork_root = project_root / "artifacts" / "source-artwork" / "artwork" / "artwork_default"

    artwork_vector_manifest = artwork_root / "30-vector" / "products.json"

    assert artwork_vector_manifest.is_file()

    initial_vector_bytes = artwork_vector_manifest.read_bytes()

    initial_component_bytes = {
        path.name: path.read_bytes() for path in (artwork_root / "30-vector").glob("*.svg")
    }

    assert initial_component_bytes

    assert not (artwork_root / "40-extrude" / "products.json").exists()

    assert not (artwork_root / "50-package" / "artifact.3mf").exists()

    write_artifact_config(
        "polygon-shape",
        {
            "realizations": {
                "shape_default": {
                    "shape_geometry": "polygon",
                    "shape_sides": 7,
                    "shape_size": 120.0,
                },
            },
            "product_dependencies": artwork_dependency,
        },
        project_root=project_root,
    )

    polygon_plans = create_build_plans(
        "polygon-shape",
        model_name="shape",
        variant_name="default",
        project_root=project_root,
    )

    assert len(polygon_plans) == 1

    polygon_plan = polygon_plans[0]

    assert polygon_plan.model_name == "shape"
    assert polygon_plan.realization_name == "shape_default"

    execute_dependency_build(
        polygon_plan,
    )

    assert artwork_vector_manifest.read_bytes() == initial_vector_bytes

    reused_component_bytes = {
        path.name: path.read_bytes() for path in (artwork_root / "30-vector").glob("*.svg")
    }

    assert reused_component_bytes == initial_component_bytes

    assert not (artwork_root / "40-extrude" / "products.json").exists()

    assert not (artwork_root / "50-package" / "artifact.3mf").exists()

    for plan in (
        circle_plan,
        polygon_plan,
    ):
        package_stage = next(stage for stage in plan.stages if stage.spec.name == "package")

        artifact_product = next(
            product for product in package_stage.products if product.spec.name == "artifact"
        )

        output = artifact_product.path

        assert output.is_file()
        assert output.stat().st_size > 0
        assert zipfile.is_zipfile(
            output,
        )


@pytest.mark.slow
def deferred_test_second_shape_does_not_reexecute_registered_artwork_stages(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """
    A second Shape reuses current registered Artwork without reexecuting it.

    When registered Artwork has already been produced for one Shape,
    building a physically different Shape does not reexecute Artwork
    preparation, rasterization, or vectorization.
    """

    project_root = tmp_path

    monkeypatch.chdir(
        project_root,
    )

    _materialize_artwork_source(
        "source-artwork",
        project_root=project_root,
    )

    artwork_dependency = {
        "manifest": {
            "model": "artwork",
            "stage": "vector",
            "product": "manifest",
            "artifact": "source-artwork",
            "realization": "artwork_default",
        },
    }

    write_artifact_config(
        "circle-shape",
        {
            "realizations": {
                "shape_default": {
                    "shape_geometry": "circle",
                    "shape_size": 100.0,
                },
            },
            "product_dependencies": artwork_dependency,
        },
        project_root=project_root,
    )

    write_artifact_config(
        "polygon-shape",
        {
            "realizations": {
                "shape_default": {
                    "shape_geometry": "polygon",
                    "shape_sides": 7,
                    "shape_size": 120.0,
                },
            },
            "product_dependencies": artwork_dependency,
        },
        project_root=project_root,
    )

    circle_plans = create_build_plans(
        "circle-shape",
        model_name="shape",
        variant_name="default",
        project_root=project_root,
    )

    assert len(circle_plans) == 1

    circle_plan = circle_plans[0]

    assert circle_plan.model_name == "shape"
    assert circle_plan.realization_name == "shape_default"

    execute_dependency_build(
        circle_plan,
    )

    artwork_root = project_root / "artifacts" / "source-artwork" / "artwork" / "artwork_default"

    assert (artwork_root / "10-prepare" / "trace.svg").is_file()
    assert (artwork_root / "20-raster" / "products.json").is_file()
    assert (artwork_root / "30-vector" / "products.json").is_file()

    events = []

    polygon_plans = create_build_plans(
        "polygon-shape",
        model_name="shape",
        variant_name="default",
        project_root=project_root,
    )

    assert len(polygon_plans) == 1

    polygon_plan = polygon_plans[0]

    assert polygon_plan.model_name == "shape"
    assert polygon_plan.realization_name == "shape_default"

    execute_dependency_build(
        polygon_plan,
        event_sink=events.append,
    )

    artwork_started = tuple(
        event.stage_name
        for event in events
        if event.kind == "stage.started"
        and event.artifact_id == "source-artwork"
        and event.model_name == "artwork"
    )

    assert artwork_started == ()

    shape_started = tuple(
        event.stage_name
        for event in events
        if event.kind == "stage.started"
        and event.artifact_id == "polygon-shape"
        and event.model_name == "shape"
    )

    assert shape_started == (
        "structure",
        "compose",
        "extrude",
        "package",
    )

    assert not (artwork_root / "40-extrude" / "products.json").exists()

    assert not (artwork_root / "50-package" / "artifact.3mf").exists()


@pytest.mark.slow
def deferred_test_shape_policy_changes_do_not_reexecute_registered_artwork(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """
    Downstream Shape policy changes do not invalidate registered Artwork.

    Polygon rotation, base thickness, ridge dimensions and style, and
    structural colors belong to Shape manufacturing policy. Changing those
    values must not cause reusable registered Artwork to be reinterpreted.
    """

    project_root = tmp_path

    monkeypatch.chdir(
        project_root,
    )

    _materialize_artwork_source(
        "source-artwork",
        project_root=project_root,
    )

    artwork_dependency = {
        "manifest": {
            "model": "artwork",
            "stage": "vector",
            "product": "manifest",
            "artifact": "source-artwork",
            "realization": "artwork_default",
        },
    }

    write_artifact_config(
        "initial-shape",
        {
            "realizations": {
                "shape_default": {
                    "shape_geometry": "polygon",
                    "shape_sides": 6,
                    "shape_rotation": 0.0,
                    "shape_size": 100.0,
                    "shape_base_raise": 2.0,
                    "shape_base_color": "white",
                    "shape_outer_ridge_width": 1.0,
                    "shape_outer_ridge_raise": 1.0,
                    "shape_outer_ridge_style": "integrated",
                    "shape_outer_ridge_color": "white",
                },
            },
            "product_dependencies": artwork_dependency,
        },
        project_root=project_root,
    )

    initial_plans = create_build_plans(
        "initial-shape",
        model_name="shape",
        variant_name="default",
        project_root=project_root,
    )

    assert len(initial_plans) == 1

    initial_plan = initial_plans[0]

    assert initial_plan.model_name == "shape"
    assert initial_plan.realization_name == "shape_default"

    execute_dependency_build(
        initial_plan,
    )

    artwork_root = project_root / "artifacts" / "source-artwork" / "artwork" / "artwork_default"

    assert (artwork_root / "10-prepare" / "trace.svg").is_file()
    assert (artwork_root / "20-raster" / "products.json").is_file()
    assert (artwork_root / "30-vector" / "products.json").is_file()

    assert not (artwork_root / "40-extrude" / "products.json").exists()
    assert not (artwork_root / "50-package" / "artifact.3mf").exists()

    write_artifact_config(
        "changed-shape",
        {
            "realizations": {
                "shape_default": {
                    "shape_geometry": "polygon",
                    "shape_sides": 7,
                    "shape_rotation": 22.5,
                    "shape_size": 120.0,
                    "shape_base_raise": 3.0,
                    "shape_base_color": "black",
                    "shape_outer_ridge_width": 2.0,
                    "shape_outer_ridge_raise": 1.5,
                    "shape_outer_ridge_style": "separate",
                    "shape_outer_ridge_color": "red",
                },
            },
            "product_dependencies": artwork_dependency,
        },
        project_root=project_root,
    )

    events = []

    changed_plans = create_build_plans(
        "changed-shape",
        model_name="shape",
        variant_name="default",
        project_root=project_root,
    )

    assert len(changed_plans) == 1

    changed_plan = changed_plans[0]

    assert changed_plan.model_name == "shape"
    assert changed_plan.realization_name == "shape_default"

    execute_dependency_build(
        changed_plan,
        event_sink=events.append,
    )

    artwork_started = tuple(
        event.stage_name
        for event in events
        if event.kind == "stage.started"
        and event.artifact_id == "source-artwork"
        and event.model_name == "artwork"
    )

    assert artwork_started == ()

    shape_started = tuple(
        event.stage_name
        for event in events
        if event.kind == "stage.started"
        and event.artifact_id == "changed-shape"
        and event.model_name == "shape"
    )

    assert shape_started == (
        "structure",
        "compose",
        "extrude",
        "package",
    )

    assert not (artwork_root / "40-extrude" / "products.json").exists()

    assert not (artwork_root / "50-package" / "artifact.3mf").exists()


@pytest.mark.slow
def test_shape_size_change_preserves_registered_geometry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Changing Shape size preserves registered geometry while changing
    the physical dimensions of the canonical SVG.

    Structure and composition remain in registered coordinates.
    The canonical SVG uses physical millimeter dimensions while
    retaining the registered viewBox and component geometry.
    """
    project_root = tmp_path
    monkeypatch.chdir(project_root)

    artifact_id = "resized-shape"

    write_artifact_config(
        artifact_id,
        {
            "realizations": {
                "shape_default": {
                    "shape_size": 100.0,
                },
            },
        },
        project_root=project_root,
    )

    initial_plan = create_build_plans(
        artifact_id,
        model_name="shape",
        variant_name="default",
        project_root=project_root,
    )[0]

    execute_dependency_build(initial_plan)

    shape_root = project_root / "artifacts" / artifact_id / "shape" / "shape_default"

    structure = shape_root / "10-structure" / "structure.svg"
    composition = shape_root / "20-compose" / "composition.svg"

    compose_stage = next(stage for stage in initial_plan.stages if stage.spec.name == "compose")

    svg_product = next(
        product for product in compose_stage.products if product.spec.name == "artifact"
    )

    canonical_svg = svg_product.path

    assert structure.is_file()
    assert composition.is_file()
    assert canonical_svg.is_file()

    initial_structure_bytes = structure.read_bytes()
    initial_composition_bytes = composition.read_bytes()
    initial_svg_bytes = canonical_svg.read_bytes()

    initial_root = ET.fromstring(initial_svg_bytes)

    assert initial_root.get("width") == "100mm"
    assert initial_root.get("height") == "100mm"
    assert initial_root.get("viewBox") == "-0.5 -0.5 1 1"

    update_artifact_config(
        artifact_id,
        {
            "realizations": {
                "shape_default": {
                    "shape_size": 90.0,
                },
            },
        },
        project_root=project_root,
    )

    resized_plan = create_build_plans(
        artifact_id,
        model_name="shape",
        variant_name="default",
        project_root=project_root,
    )[0]

    execute_dependency_build(resized_plan)

    assert structure.read_bytes() == initial_structure_bytes
    assert composition.read_bytes() == initial_composition_bytes

    resized_compose_stage = next(
        stage for stage in resized_plan.stages if stage.spec.name == "compose"
    )

    resized_svg_product = next(
        product for product in resized_compose_stage.products if product.spec.name == "artifact"
    )

    assert resized_svg_product.path == canonical_svg
    assert canonical_svg.is_file()

    resized_svg_bytes = canonical_svg.read_bytes()
    resized_root = ET.fromstring(resized_svg_bytes)

    assert resized_svg_bytes != initial_svg_bytes

    assert resized_root.get("width") == "90mm"
    assert resized_root.get("height") == "90mm"
    assert resized_root.get("viewBox") == "-0.5 -0.5 1 1"

    # Physical dimensions change, but the registered geometry
    # remains unchanged. The CUT contour's stroke width is
    # deliberately expressed as a physical 0.1 mm dimension.
    for root, size in (
        (initial_root, 100.0),
        (resized_root, 90.0),
    ):
        root.attrib.pop("width")
        root.attrib.pop("height")

        cut = root.find("{http://www.w3.org/2000/svg}path[@id='cut-contour']")

        assert cut is not None
        assert float(cut.attrib.pop("stroke-width")) == pytest.approx(
            0.1 / size,
            rel=1e-5,
        )

    assert ET.tostring(initial_root) == ET.tostring(resized_root)


@pytest.mark.slow
def test_shape_size_change_rebuilds_physical_products(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """
    Changing Shape physical size rebuilds physical manufacturing products.

    shape_size is introduced at physical dimensionalization. Changing it
    therefore changes the extruded Shape while normal dependency-aware
    orchestration still produces a valid final artifact.3mf.
    """

    project_root = tmp_path

    monkeypatch.chdir(
        project_root,
    )

    # -----------------------------------------------------
    # Configure Shape
    # -----------------------------------------------------

    write_artifact_config(
        "resized-shape",
        {
            "realizations": {
                "shape_default": {
                    "shape_size": 100.0,
                },
            },
        },
        project_root=project_root,
    )

    # -----------------------------------------------------
    # Build initial Shape
    # -----------------------------------------------------

    initial_plan = create_build_plans(
        "resized-shape",
        model_name="shape",
        variant_name="default",
        project_root=project_root,
    )[0]

    execute_dependency_build(
        initial_plan,
    )

    shape_root = project_root / "artifacts" / "resized-shape" / "shape" / "shape_default"

    base = shape_root / "30-extrude" / "base.stl"
    artifact = shape_root / "40-package" / "artifact.3mf"

    assert base.is_file()
    assert base.stat().st_size > 0

    assert artifact.is_file()
    assert artifact.stat().st_size > 0
    assert zipfile.is_zipfile(
        artifact,
    )

    initial_base_bytes = base.read_bytes()
    initial_artifact_bytes = artifact.read_bytes()

    # -----------------------------------------------------
    # Change only physical Shape size
    # -----------------------------------------------------

    update_artifact_config(
        "resized-shape",
        {
            "realizations": {
                "shape_default": {
                    "shape_size": 90.0,
                },
            },
        },
        project_root=project_root,
    )

    # -----------------------------------------------------
    # Rebuild through normal orchestration
    # -----------------------------------------------------

    resized_plan = create_build_plans(
        "resized-shape",
        model_name="shape",
        variant_name="default",
        project_root=project_root,
    )[0]

    execute_dependency_build(
        resized_plan,
    )

    # -----------------------------------------------------
    # Physical extrusion changed
    # -----------------------------------------------------

    assert base.is_file()
    assert base.stat().st_size > 0

    resized_base_bytes = base.read_bytes()

    assert resized_base_bytes != initial_base_bytes

    # -----------------------------------------------------
    # Final package was rebuilt successfully
    # -----------------------------------------------------

    package_stage = next(stage for stage in resized_plan.stages if stage.spec.name == "package")

    artifact_product = next(
        product for product in package_stage.products if product.spec.name == "artifact"
    )

    output = artifact_product.path

    assert output == artifact
    assert output.is_file()
    assert output.stat().st_size > 0
    assert zipfile.is_zipfile(
        output,
    )

    assert output.read_bytes() != initial_artifact_bytes


@pytest.mark.slow
def test_shape_registered_artwork_defaults_to_no_artwork_fill(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """
    A normal Shape build does not manufacture Artwork fill by default.

    Shape Compose may preserve the potential registered Artwork-fill region,
    but the default shape_artwork_fill_raise of zero means that region does
    not participate in physical extrusion or final packaging.

    Artwork-fill participation is independent of physical fill color.
    """

    project_root = tmp_path

    monkeypatch.chdir(
        project_root,
    )

    _materialize_artwork_source(
        "fill-source",
        project_root=project_root,
    )

    update_artifact_config(
        "fill-source",
        {
            "realizations": {
                "artwork_default": {
                    "artwork_size": 200.0,
                },
            },
        },
        project_root=project_root,
    )

    write_artifact_config(
        "shape-no-fill",
        {
            "realizations": {
                "shape_default": {
                    "shape_geometry": "circle",
                    "shape_size": 100.0,
                    "shape_base_color": "test-white",
                },
            },
            "product_dependencies": {
                "manifest": {
                    "artifact": "fill-source",
                    "model": "artwork",
                    "realization": "artwork_default",
                    "stage": "vector",
                    "product": "manifest",
                },
            },
        },
        project_root=project_root,
    )

    plans = create_build_plans(
        "shape-no-fill",
        model_name="shape",
        variant_name="default",
        project_root=project_root,
    )

    assert len(plans) == 1

    execute_dependency_build(
        plans[0],
    )

    shape_root = project_root / "artifacts" / "shape-no-fill" / "shape" / "shape_default"

    compose_manifest = shape_root / "20-compose" / "products.json"
    extrude_manifest = shape_root / "30-extrude" / "products.json"
    artifact = shape_root / "40-package" / "artifact.3mf"

    assert compose_manifest.is_file()
    assert extrude_manifest.is_file()
    assert artifact.is_file()

    composition_data = json.loads(
        compose_manifest.read_text(
            encoding="utf-8",
        )
    )

    assert composition_data["artwork"] is not None

    #
    # Compose preserves the potential registered fill region independently
    # of whether that region later participates in physical manufacturing.
    #
    assert composition_data["artwork_fill"] is not None

    extrusion_data = json.loads(
        extrude_manifest.read_text(
            encoding="utf-8",
        )
    )

    component_names = {component["name"] for component in extrusion_data["components"]}

    assert "base" in component_names
    assert "artwork-fill" not in component_names
    assert any(str(name).startswith("artwork-") for name in component_names)

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

    packaged_names = {
        object_.get("name")
        for object_ in model.findall(
            f".//{{{CORE_NS}}}object",
        )
    }

    assert (
        component_name(
            "shape-no-fill",
            "base",
            "test-white",
        )
        in packaged_names
    )

    assert not any(
        name is not None
        and name.startswith(
            "artwork-fill - ",
        )
        for name in packaged_names
    )

    assert any(
        name is not None
        and name.startswith(
            "artwork-",
        )
        for name in packaged_names
    )

    artwork_root = project_root / "artifacts" / "fill-source" / "artwork" / "artwork_default"

    assert (artwork_root / "30-vector" / "products.json").is_file()
    assert not (artwork_root / "40-extrude" / "products.json").exists()
    assert not (artwork_root / "50-package" / "artifact.3mf").exists()


@pytest.mark.slow
def test_shape_registered_artwork_builds_artwork_fill_into_final_3mf(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """
    A normal Shape build carries enabled Artwork fill into artifact.3mf.

    Shape consumes reusable registered Artwork, constructs the registered fill
    region, dimensionalizes that region when shape_artwork_fill_raise is
    positive, preserves its Shape-owned component identity through Extrude,
    and resolves its physical color during Package.
    """

    project_root = tmp_path

    monkeypatch.chdir(
        project_root,
    )

    _materialize_artwork_source(
        "fill-source",
        project_root=project_root,
    )

    update_artifact_config(
        "fill-source",
        {
            "realizations": {
                "artwork_default": {
                    "artwork_size": 200.0,
                },
            },
        },
        project_root=project_root,
    )

    write_artifact_config(
        "shape-with-fill",
        {
            "realizations": {
                "shape_default": {
                    "shape_geometry": "circle",
                    "shape_size": 100.0,
                    "shape_base_color": "test-white",
                    "shape_artwork_fill_raise": 0.6,
                    "shape_artwork_fill_color": "test-blue",
                },
            },
            "product_dependencies": {
                "manifest": {
                    "artifact": "fill-source",
                    "model": "artwork",
                    "realization": "artwork_default",
                    "stage": "vector",
                    "product": "manifest",
                },
            },
        },
        project_root=project_root,
    )

    plans = create_build_plans(
        "shape-with-fill",
        model_name="shape",
        variant_name="default",
        project_root=project_root,
    )

    assert len(plans) == 1

    execute_dependency_build(
        plans[0],
    )

    shape_root = project_root / "artifacts" / "shape-with-fill" / "shape" / "shape_default"

    compose_manifest = shape_root / "20-compose" / "products.json"
    extrude_manifest = shape_root / "30-extrude" / "products.json"
    artifact = shape_root / "40-package" / "artifact.3mf"

    assert compose_manifest.is_file()
    assert extrude_manifest.is_file()
    assert artifact.is_file()

    composition_data = json.loads(
        compose_manifest.read_text(
            encoding="utf-8",
        )
    )

    assert composition_data["artwork"] is not None
    assert composition_data["artwork_fill"] is not None

    extrusion_data = json.loads(
        extrude_manifest.read_text(
            encoding="utf-8",
        )
    )

    components_by_name = {
        component["name"]: component for component in extrusion_data["components"]
    }

    assert "base" in components_by_name
    assert "artwork-fill" in components_by_name

    artwork_component_names = {
        name
        for name in components_by_name
        if str(name).startswith("artwork-") and name != "artwork-fill"
    }

    assert artwork_component_names

    fill_component = components_by_name["artwork-fill"]

    #
    # Extrude owns physical geometry and component participation, not
    # physical Shape-owned color assignment.
    #
    assert fill_component == {
        "name": "artwork-fill",
        "path": "artwork-fill.stl",
    }

    fill_path = extrude_manifest.parent / str(fill_component["path"])

    assert fill_path.is_file()
    assert fill_path.stat().st_size > 0

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
    materials_by_id = {material.get("id"): material for material in materials}

    assert component_name("shape-with-fill", "base", "test-white") in objects_by_name
    assert component_name("shape-with-fill", "artwork-fill", "test-blue") in objects_by_name

    artwork_object_names = {
        name
        for name in objects_by_name
        if name is not None
        and name.startswith(
            "artwork-",
        )
        and name != component_name("shape-with-fill", "artwork-fill", "test-blue")
    }

    assert artwork_object_names

    fill_object = objects_by_name[
        component_name(
            "shape-with-fill",
            "artwork-fill",
            "test-blue",
        )
    ]

    fill_material_id = fill_object.get(
        "pid",
    )

    assert fill_material_id is not None

    fill_material = materials_by_id[fill_material_id]

    fill_color = fill_material.find(
        f"{{{CORE_NS}}}base",
    )

    assert fill_color is not None
    assert fill_color.get("name") == "test-blue"
    assert fill_color.get("displaycolor") == "#0000FF"
    assert fill_object.get("pindex") == "0"

    base_object = objects_by_name[
        component_name(
            "shape-with-fill",
            "base",
            "test-white",
        )
    ]

    assert fill_object.get("id") != base_object.get("id")

    for artwork_name in artwork_object_names:
        assert fill_object.get("id") != objects_by_name[artwork_name].get("id")

    artwork_root = project_root / "artifacts" / "fill-source" / "artwork" / "artwork_default"

    assert (artwork_root / "30-vector" / "products.json").is_file()
    assert not (artwork_root / "40-extrude" / "products.json").exists()
    assert not (artwork_root / "50-package" / "artifact.3mf").exists()


@pytest.mark.slow
def test_shape_artwork_fill_remains_distinct_when_base_uses_same_color(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """
    Shape base and Artwork fill may share one physical color while remaining
    independently identifiable physical components in the final 3MF.

    Extrude preserves their distinct Shape-owned component identities without
    assigning physical colors. Package may then resolve both components to the
    same physical color without merging them.
    """

    project_root = tmp_path

    monkeypatch.chdir(
        project_root,
    )

    _materialize_artwork_source(
        "fill-source",
        project_root=project_root,
    )

    update_artifact_config(
        "fill-source",
        {
            "realizations": {
                "artwork_default": {
                    "artwork_size": 200.0,
                },
            },
        },
        project_root=project_root,
    )

    write_artifact_config(
        "shared-color-fill-shape",
        {
            "realizations": {
                "shape_default": {
                    "shape_geometry": "circle",
                    "shape_size": 100.0,
                    "shape_base_color": "test-blue",
                    "shape_artwork_fill_raise": 0.6,
                    "shape_artwork_fill_color": "test-blue",
                },
            },
            "product_dependencies": {
                "manifest": {
                    "artifact": "fill-source",
                    "model": "artwork",
                    "realization": "artwork_default",
                    "stage": "vector",
                    "product": "manifest",
                },
            },
        },
        project_root=project_root,
    )

    plans = create_build_plans(
        "shared-color-fill-shape",
        model_name="shape",
        variant_name="default",
        project_root=project_root,
    )

    assert len(plans) == 1

    execute_dependency_build(
        plans[0],
    )

    shape_root = project_root / "artifacts" / "shared-color-fill-shape" / "shape" / "shape_default"

    extrude_manifest = shape_root / "30-extrude" / "products.json"
    artifact = shape_root / "40-package" / "artifact.3mf"

    assert extrude_manifest.is_file()
    assert artifact.is_file()

    extrusion_data = json.loads(
        extrude_manifest.read_text(
            encoding="utf-8",
        )
    )

    components_by_name = {
        component["name"]: component for component in extrusion_data["components"]
    }

    assert "base" in components_by_name
    assert "artwork-fill" in components_by_name

    #
    # Shape-owned physical colors are Package policy. Extrude preserves
    # component identity and geometry only.
    #
    assert components_by_name["base"] == {
        "name": "base",
        "path": "base.stl",
    }

    assert components_by_name["artwork-fill"] == {
        "name": "artwork-fill",
        "path": "artwork-fill.stl",
    }

    assert components_by_name["base"]["path"] != components_by_name["artwork-fill"]["path"]

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
    materials_by_id = {material.get("id"): material for material in materials}

    base_object = objects_by_name[
        component_name(
            "shared-color-fill-shape",
            "base",
            "test-blue",
        )
    ]

    fill_object = objects_by_name[
        component_name(
            "shared-color-fill-shape",
            "artwork-fill",
            "test-blue",
        )
    ]

    assert base_object.get("id") != fill_object.get("id")

    for object_ in (
        base_object,
        fill_object,
    ):
        material_id = object_.get(
            "pid",
        )

        assert material_id is not None

        material = materials_by_id[material_id]

        color = material.find(
            f"{{{CORE_NS}}}base",
        )

        assert color is not None
        assert color.get("name") == "test-blue"
        assert color.get("displaycolor") == "#0000FF"
        assert object_.get("pindex") == "0"

    artwork_object_names = {
        name
        for name in objects_by_name
        if name is not None
        and name.startswith(
            "artwork-",
        )
        and name
        != component_name(
            "shared-color-fill-shape",
            "artwork-fill",
            "test-blue",
        )
    }

    assert artwork_object_names

    artwork_root = project_root / "artifacts" / "fill-source" / "artwork" / "artwork_default"

    assert (artwork_root / "30-vector" / "products.json").is_file()
    assert not (artwork_root / "40-extrude" / "products.json").exists()
    assert not (artwork_root / "50-package" / "artifact.3mf").exists()


@pytest.mark.slow
@pytest.mark.parametrize(
    "ridge_style",
    [
        "integrated",
        "separate",
    ],
)
def deferred_test_shape_artwork_fill_preserves_physical_interval_with_outer_ridge(
    tmp_path: Path,
    monkeypatch,
    ridge_style: str,
) -> None:
    """
    A physical outer ridge does not alter Artwork-fill Z semantics.

    Integrated and separate outer ridges both preserve the Shape-owned
    Artwork-fill interval from shape_base_raise through
    shape_base_raise + shape_artwork_fill_raise.

    Artwork fill has an independent physical raise from incorporated Artwork.
    """

    project_root = tmp_path

    monkeypatch.chdir(
        project_root,
    )

    _materialize_artwork_source(
        "ridge-fill-source",
        project_root=project_root,
    )

    update_artifact_config(
        "ridge-fill-source",
        {
            "realizations": {
                "artwork_default": {
                    "artwork_size": 200.0,
                },
            },
        },
        project_root=project_root,
    )

    artifact_id = f"{ridge_style}-ridge-fill-shape"

    shape_base_raise = 2.0
    shape_artwork_raise = 1.25
    shape_artwork_fill_raise = 0.6

    write_artifact_config(
        artifact_id,
        {
            "realizations": {
                "shape_default": {
                    "shape_geometry": "circle",
                    "shape_size": 100.0,
                    "shape_base_raise": shape_base_raise,
                    "shape_artwork_raise": shape_artwork_raise,
                    "shape_artwork_fill_raise": shape_artwork_fill_raise,
                    "shape_base_color": "test-white",
                    "shape_artwork_fill_color": "test-blue",
                    "shape_outer_ridge_width": 2.0,
                    "shape_outer_ridge_raise": 1.5,
                    "shape_outer_ridge_style": ridge_style,
                    "shape_outer_ridge_color": "test-red",
                },
            },
            "product_dependencies": {
                "manifest": {
                    "artifact": "ridge-fill-source",
                    "model": "artwork",
                    "realization": "artwork_default",
                    "stage": "vector",
                    "product": "manifest",
                },
            },
        },
        project_root=project_root,
    )

    plans = create_build_plans(
        artifact_id,
        model_name="shape",
        variant_name="default",
        project_root=project_root,
    )

    assert len(plans) == 1

    execute_dependency_build(
        plans[0],
    )

    shape_root = project_root / "artifacts" / artifact_id / "shape" / "shape_default"

    extrude_root = shape_root / "30-extrude"

    extrude_manifest = extrude_root / "products.json"

    artifact = shape_root / "40-package" / "artifact.3mf"

    assert extrude_manifest.is_file()
    assert artifact.is_file()

    extrusion_data = json.loads(
        extrude_manifest.read_text(
            encoding="utf-8",
        )
    )

    components_by_name = {
        component["name"]: component for component in extrusion_data["components"]
    }

    assert "base" in components_by_name
    assert "ridge" in components_by_name
    assert "artwork-fill" in components_by_name

    artwork_component_names = {
        name
        for name in components_by_name
        if str(name).startswith("artwork-") and name != "artwork-fill"
    }

    assert artwork_component_names

    fill_component = components_by_name["artwork-fill"]

    #
    # Extrude preserves Shape-owned fill component identity without resolving
    # its physical Package color.
    #
    assert fill_component == {
        "name": "artwork-fill",
        "path": "artwork-fill.stl",
    }

    fill_path = extrude_root / str(fill_component["path"])

    assert fill_path.is_file()
    assert fill_path.stat().st_size > 0

    fill_text = fill_path.read_text(
        encoding="utf-8",
    )

    z_values: list[float] = []

    for line in fill_text.splitlines():
        stripped = line.strip()

        if not stripped.startswith("vertex "):
            continue

        coordinates = stripped.split()

        assert len(coordinates) == 4

        z_values.append(
            float(
                coordinates[3],
            )
        )

    assert z_values

    assert min(z_values) == pytest.approx(
        shape_base_raise,
    )

    assert max(z_values) == pytest.approx(
        shape_base_raise + shape_artwork_fill_raise,
    )

    #
    # The deliberately different Artwork raise proves that fill height is
    # controlled independently.
    #
    assert shape_artwork_fill_raise != shape_artwork_raise

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

    objects_by_name = {
        object_.get("name"): object_
        for object_ in model.findall(
            f".//{{{CORE_NS}}}object",
        )
    }

    base_name = component_name(artifact_id, "base", "test-white")
    ridge_name = component_name(artifact_id, "ridge", "test-red")
    fill_name = component_name(artifact_id, "artwork-fill", "test-blue")

    assert base_name in objects_by_name
    assert ridge_name in objects_by_name
    assert fill_name in objects_by_name

    artwork_object_names = {
        name
        for name in objects_by_name
        if name is not None
        and name.startswith(
            "artwork-",
        )
        and name != fill_name
    }

    assert artwork_object_names

    base_object = objects_by_name[base_name]
    ridge_object = objects_by_name[ridge_name]
    fill_object = objects_by_name[fill_name]

    assert (
        len(
            {
                base_object.get("id"),
                ridge_object.get("id"),
                fill_object.get("id"),
            }
        )
        == 3
    )

    artwork_root = project_root / "artifacts" / "ridge-fill-source" / "artwork" / "artwork_default"

    assert (artwork_root / "30-vector" / "products.json").is_file()

    assert not (artwork_root / "40-extrude" / "products.json").exists()

    assert not (artwork_root / "50-package" / "artifact.3mf").exists()


@pytest.mark.slow
def test_shape_dependency_does_not_realize_standalone_artwork_base(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """
    Shape consumes registered Artwork without realizing standalone Base.

    Enabling Base on the producing Artwork Realization does not extend a
    dependency build beyond registered vector Artwork. Base belongs to
    standalone Artwork dimensionalization, not to the reusable registered
    representation consumed by Shape.
    """

    project_root = tmp_path

    monkeypatch.chdir(
        project_root,
    )

    _materialize_artwork_source(
        "source-artwork",
        project_root=project_root,
    )

    update_artifact_config(
        "source-artwork",
        {
            "realizations": {
                "artwork_default": {
                    "artwork_base_raise": 2.0,
                    "artwork_base_color": "black",
                },
            },
        },
        project_root=project_root,
    )

    write_artifact_config(
        "artwork-shape",
        {
            "product_dependencies": {
                "manifest": {
                    "model": "artwork",
                    "stage": "vector",
                    "product": "manifest",
                    "artifact": "source-artwork",
                    "realization": "artwork_default",
                },
            },
        },
        project_root=project_root,
    )

    plans = create_build_plans(
        "artwork-shape",
        model_name="shape",
        variant_name="default",
        project_root=project_root,
    )

    assert len(plans) == 1

    execute_dependency_build(
        plans[0],
    )

    artwork_root = project_root / "artifacts" / "source-artwork" / "artwork" / "artwork_default"

    vector_manifest = artwork_root / "30-vector" / "products.json"

    assert vector_manifest.is_file()

    vector_data = json.loads(
        vector_manifest.read_text(
            encoding="utf-8",
        )
    )

    assert vector_data["products"]

    assert all(product["path"] != "base.stl" for product in vector_data["products"])

    assert not (artwork_root / "40-extrude" / "products.json").exists()
    assert not (artwork_root / "40-extrude" / "base.stl").exists()

    assert not (artwork_root / "50-package" / "artifact.3mf").exists()

    shape_root = project_root / "artifacts" / "artwork-shape" / "shape" / "shape_default"

    assert (shape_root / "40-package" / "artifact.3mf").is_file()


# =========================================================
# Native SVG Artwork → Shape acceptance
# =========================================================


def _native_svg_acceptance_source(
    *,
    inner_width: int = 20,
) -> str:
    """
    Two-color native SVG with a document transform and a genuine hole.

    The red region is a frame with an even-odd interior hole.
    The blue region is an independent filled rectangle.
    Both are authored in the same transformed coordinate system.

    Stable path IDs preserve native SVG object identity.

    Changing inner_width changes the manufactured red geometry while
    preserving source identity and the logical two-color structure.
    """
    return f"""\
<svg xmlns="http://www.w3.org/2000/svg"
     width="120" height="80" viewBox="0 0 120 80">
  <g transform="translate(10 10)">
    <path id="red-region"
          fill="#FF0000"
          fill-rule="evenodd"
          d="M 0 0 H 40 V 40 H 0 Z
             M 10 10 H {10 + inner_width} V 30 H 10 Z"/>
    <path id="blue-region"
          fill="#0000FF"
          d="M 50 0 H 90 V 40 H 50 Z"/>
  </g>
</svg>
"""


def _native_svg_acceptance_project(
    project_root: Path,
) -> tuple[Path, Path]:
    """
    Establish a canonical SVG Artwork producer and a Shape consumer.

    The source is preserved in originals/ and materialized through the
    same configuration operation used by existing acceptance tests.
    """
    originals = project_root / "originals"
    originals.mkdir(parents=True, exist_ok=True)

    original = originals / "svg-source.svg"
    original.write_text(
        _native_svg_acceptance_source(),
        encoding="utf-8",
    )

    materialize_artifact(
        "svg-source",
        project_root=project_root,
    )

    configure_artifact(
        "svg-source",
        input_files={"artwork": original},
        project_root=project_root,
    )

    write_artifact_config(
        "svg-shape",
        {
            "realizations": {
                "shape_default": {
                    "shape_geometry": "circle",
                    "shape_size": 100.0,
                    "shape_base_color": "test-white",
                },
            },
            "product_dependencies": {
                "manifest": {
                    "artifact": "svg-source",
                    "model": "artwork",
                    "realization": "artwork_default",
                    "stage": "vector",
                    "product": "manifest",
                },
            },
        },
        project_root=project_root,
    )

    artwork_root = project_root / "artifacts" / "svg-source" / "artwork" / "artwork_default"
    shape_root = project_root / "artifacts" / "svg-shape" / "shape" / "shape_default"

    return artwork_root, shape_root


def _native_svg_shape_plan(project_root: Path):
    plans = create_build_plans(
        "svg-shape",
        model_name="shape",
        variant_name="default",
        project_root=project_root,
    )

    assert len(plans) == 1
    return plans[0]


def _native_svg_packaged_objects(
    artifact: Path,
) -> dict[str, ET.Element]:
    assert artifact.is_file()
    assert zipfile.is_zipfile(artifact)

    with zipfile.ZipFile(artifact) as archive:
        model_names = [
            name
            for name in archive.namelist()
            if name.startswith("3D/") and name.endswith(".model")
        ]
        assert len(model_names) == 1

        model = ET.fromstring(archive.read(model_names[0]))

    objects = model.findall(f".//{{{CORE_NS}}}object")
    named = {name: object_ for object_ in objects if (name := object_.get("name")) is not None}

    assert len(named) == len(objects)
    return named


@pytest.mark.slow
def test_shape_builds_complete_3mf_with_native_svg_artwork(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """
    Shape consumes native SVG Artwork through registered Vector.

    Authored colors, transforms, and holes survive registration,
    composition, extrusion, and 3MF packaging.

    Shape-owned Artwork Region Fill is not source Artwork.
    """
    monkeypatch.chdir(tmp_path)

    artwork_root, shape_root = _native_svg_acceptance_project(tmp_path)

    plan = _native_svg_shape_plan(tmp_path)
    execute_dependency_build(plan)

    vector_manifest = artwork_root / "30-vector" / "products.json"
    assert vector_manifest.is_file()

    vector_data = json.loads(vector_manifest.read_text(encoding="utf-8"))

    products = vector_data["products"]

    assert len(products) == 2
    assert {product["artifact_color"]["index"] for product in products} == {1, 2}

    rgb_colors = {
        tuple(product["artifact_color"]["rgb"][channel] for channel in ("red", "green", "blue"))
        for product in products
    }

    assert rgb_colors == {
        (255, 0, 0),
        (0, 0, 255),
    }

    for product in products:
        assert (vector_manifest.parent / product["path"]).is_file()

        assert "printer_color" not in product
        assert "distance" not in product

    assert not (artwork_root / "40-extrude" / "products.json").exists()

    assert not (artwork_root / "50-package" / "artifact.3mf").exists()

    artifact = shape_root / "40-package" / "artifact.3mf"

    objects = _native_svg_packaged_objects(artifact)

    assert (
        component_name(
            "svg-shape",
            "base",
            "test-white",
        )
        in objects
    )

    assert (
        component_name(
            "svg-shape",
            "artwork-region-fill",
            "test-white",
        )
        in objects
    )

    artwork_objects = {
        name: object_
        for name, object_ in objects.items()
        if name.startswith("artwork-")
        and not name.startswith("artwork-fill")
        and not name.startswith("artwork-region-fill")
    }

    assert len(artwork_objects) == 2

    for index in (1, 2):
        matches = [
            object_
            for name, object_ in artwork_objects.items()
            if name.startswith(f"artwork-{index} - ")
        ]

        assert len(matches) == 1

        xml_vertices = matches[0].findall(f".//{{{CORE_NS}}}vertex")

        xml_triangles = matches[0].findall(f".//{{{CORE_NS}}}triangle")

        assert xml_vertices
        assert xml_triangles

        assert all(
            vertex.get(axis) is not None for vertex in xml_vertices for axis in ("x", "y", "z")
        )

    # Locate the registered red component.
    red_product = next(
        product
        for product in products
        if product["artifact_color"]["rgb"]
        == {
            "red": 255,
            "green": 0,
            "blue": 0,
        }
    )

    red_index = red_product["index"]

    red_object = next(
        object_
        for name, object_ in artwork_objects.items()
        if name.startswith(f"artwork-{red_index} - ")
    )

    vertices: list[tuple[float, float, float]] = []

    for vertex in red_object.findall(f".//{{{CORE_NS}}}vertex"):
        x = vertex.get("x")
        y = vertex.get("y")
        z = vertex.get("z")

        assert x is not None
        assert y is not None
        assert z is not None

        vertices.append((float(x), float(y), float(z)))

    triangles: list[tuple[int, int, int]] = []

    for triangle in red_object.findall(f".//{{{CORE_NS}}}triangle"):
        v1 = triangle.get("v1")
        v2 = triangle.get("v2")
        v3 = triangle.get("v3")

        assert v1 is not None
        assert v2 is not None
        assert v3 is not None

        triangles.append((int(v1), int(v2), int(v3)))

    assert vertices
    assert triangles

    xs = [vertex[0] for vertex in vertices]
    ys = [vertex[1] for vertex in vertices]

    center_x = (min(xs) + max(xs)) / 2
    center_y = (min(ys) + max(ys)) / 2

    def contains_xy(
        point: tuple[float, float],
        triangle: tuple[int, int, int],
    ) -> bool:
        px, py = point
        a, b, c = (vertices[index] for index in triangle)

        def cross(
            u: tuple[float, float, float],
            v: tuple[float, float, float],
        ) -> float:
            return (v[0] - u[0]) * (py - u[1]) - (v[1] - u[1]) * (px - u[0])

        d1 = cross(a, b)
        d2 = cross(b, c)
        d3 = cross(c, a)

        return not (
            (d1 < -1e-7 or d2 < -1e-7 or d3 < -1e-7) and (d1 > 1e-7 or d2 > 1e-7 or d3 > 1e-7)
        )

    horizontal_triangles = [
        triangle
        for triangle in triangles
        if (
            max(vertices[index][2] for index in triangle)
            - min(vertices[index][2] for index in triangle)
        )
        < 1e-7
    ]

    assert horizontal_triangles

    # The red frame's interior hole remains unfilled.
    assert not any(contains_xy((center_x, center_y), triangle) for triangle in horizontal_triangles)


@pytest.mark.slow
def test_native_svg_source_change_invalidates_dependent_shape_products(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """
    Editing the configured SVG source invalidates registered Artwork
    and the dependent SHAPE manufacturing path.

    An unchanged subsequent build reuses both producers and consumers
    without reexecuting stages.
    """
    monkeypatch.chdir(tmp_path)

    artwork_root, shape_root = _native_svg_acceptance_project(tmp_path)

    initial_plan = _native_svg_shape_plan(tmp_path)
    execute_dependency_build(initial_plan)

    vector_manifest = artwork_root / "30-vector" / "products.json"
    vector_dir = artwork_root / "30-vector"
    artifact = shape_root / "40-package" / "artifact.3mf"

    assert vector_manifest.is_file()
    assert artifact.is_file()

    initial_vector = vector_manifest.read_bytes()
    initial_package = artifact.read_bytes()

    def vector_snapshot() -> dict[str, bytes]:
        return {
            str(path.relative_to(vector_dir)): path.read_bytes()
            for path in sorted(vector_dir.rglob("*"))
            if path.is_file() and path.suffix.lower() == ".svg"
        }

    initial_vector_svgs = vector_snapshot()

    # Confirm an unchanged build is completely reusable.
    unchanged_events = []

    execute_dependency_build(
        _native_svg_shape_plan(tmp_path),
        event_sink=unchanged_events.append,
    )

    assert not [
        event
        for event in unchanged_events
        if event.kind == "stage.started" and event.artifact_id in {"svg-source", "svg-shape"}
    ]

    # Resolve the configured Artwork source.
    from lowkey_artifact_builder.config import get_resolver

    artwork_resolver = get_resolver(
        "svg-source",
        realization="artwork_default",
        project_root=tmp_path,
    )

    configured_source = Path(artwork_resolver("source"))

    managed_source = (
        configured_source if configured_source.is_absolute() else tmp_path / configured_source
    )

    assert managed_source.is_file()
    assert managed_source.suffix.lower() == ".svg"

    # Change source geometry without changing color identity,
    # printer palette, or SHAPE manufacturing policy.
    managed_source.write_text(
        _native_svg_acceptance_source(inner_width=12),
        encoding="utf-8",
    )

    changed_events = []

    execute_dependency_build(
        _native_svg_shape_plan(tmp_path),
        event_sink=changed_events.append,
    )

    artwork_started = {
        event.stage_name
        for event in changed_events
        if event.kind == "stage.started"
        and event.artifact_id == "svg-source"
        and event.model_name == "artwork"
    }

    shape_started = {
        event.stage_name
        for event in changed_events
        if event.kind == "stage.started"
        and event.artifact_id == "svg-shape"
        and event.model_name == "shape"
    }

    updated_vector_svgs = vector_snapshot()

    # Source changes invalidate registered Artwork and dependent Shape.
    assert {"prepare", "raster", "vector"} <= artwork_started
    assert {"compose", "extrude", "package"} <= shape_started

    # Registered product identity remains stable while geometry changes.
    assert vector_manifest.read_bytes() == initial_vector
    assert initial_vector_svgs
    assert initial_vector_svgs.keys() == updated_vector_svgs.keys()
    assert updated_vector_svgs != initial_vector_svgs

    # The changed registered geometry propagates into the final 3MF.
    assert artifact.read_bytes() != initial_package
    assert zipfile.is_zipfile(artifact)

    # The consumer still requires only registered Artwork.
    assert not (artwork_root / "40-extrude" / "products.json").exists()
    assert not (artwork_root / "50-package" / "artifact.3mf").exists()


@pytest.mark.slow
def test_shape_rejects_overlapping_native_svg_artwork_colors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Invalid native SVG Artwork must fail before dependent SHAPE
    manufacturing.

    Overlapping interiors of differently colored SVG regions are
    prohibited. The build must not silently apply SVG painting order,
    subtract overlapping geometry, or produce a final 3MF.
    """
    monkeypatch.chdir(tmp_path)

    artwork_root, shape_root = _native_svg_acceptance_project(tmp_path)

    from lowkey_artifact_builder.config import get_resolver

    artwork_resolver = get_resolver(
        "svg-source",
        realization="artwork_default",
        project_root=tmp_path,
    )

    configured_source = Path(artwork_resolver("source"))
    managed_source = (
        configured_source if configured_source.is_absolute() else tmp_path / configured_source
    )

    assert managed_source.is_file()
    assert managed_source.suffix.lower() == ".svg"

    managed_source.write_text(
        """\
    <svg xmlns="http://www.w3.org/2000/svg"
        width="100" height="100" viewBox="0 0 100 100">
    <path id="red-region"
            fill="#FF0000"
            d="M 10 10 H 70 V 70 H 10 Z"/>
    <path id="blue-region"
            fill="#0000FF"
            d="M 40 40 H 90 V 90 H 40 Z"/>
    </svg>
    """,
        encoding="utf-8",
    )

    with pytest.raises(Exception, match="(?i)overlap"):
        execute_dependency_build(
            _native_svg_shape_plan(tmp_path),
        )

    assert not (shape_root / "40-package" / "artifact.3mf").exists()

    assert not (artwork_root / "50-package" / "artifact.3mf").exists()


@pytest.mark.slow
def test_shape_exports_physically_dimensioned_svg(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    A Shape with registered native SVG Artwork produces a canonical,
    physically dimensioned, colorized SVG alongside its final 3MF.

    Shape structural colors come from the shared color catalog.
    Incorporated Artwork retains its measured Artifact RGB values.
    Physical printer assignment remains downstream in Package.
    """
    monkeypatch.chdir(tmp_path)

    artwork_root, shape_root = _native_svg_acceptance_project(tmp_path)

    plan = _native_svg_shape_plan(tmp_path)
    execute_dependency_build(plan)

    compose_stage = next(stage for stage in plan.stages if stage.spec.name == "compose")

    svg_product = next(
        product for product in compose_stage.products if product.spec.name == "artifact"
    )

    svg_path = svg_product.path

    assert svg_path.is_file()
    assert svg_path.stat().st_size > 0

    namespace = "http://www.w3.org/2000/svg"
    root = ET.parse(svg_path).getroot()

    assert root.tag == f"{{{namespace}}}svg"
    assert root.get("width") == "100mm"
    assert root.get("height") == "100mm"
    assert root.get("viewBox") == "-0.5 -0.5 1 1"

    # The canonical SVG retains an independent CUT contour.
    cut = root.find(f"./{{{namespace}}}path[@id='cut-contour']")

    assert cut is not None
    assert cut.get("fill") == "none"
    assert cut.get("d")

    # The Shape interior is rendered with the configured Base-derived
    # default color, independent of the Artwork components.
    region = root.find(f".//{{{namespace}}}path[@id='artwork-region-fill']")

    assert region is not None
    assert region.get("fill") == "#ffffff"
    assert region.get("d")

    # Read the registered Artwork colors from the producer rather
    # than assuming an ordering of the red and blue components.
    vector_manifest = artwork_root / "30-vector" / "products.json"

    assert vector_manifest.is_file()

    vector_data = json.loads(vector_manifest.read_text(encoding="utf-8"))

    products = vector_data["products"]

    assert len(products) == 2

    expected_colors = {}

    for product in products:
        index = product["index"]
        rgb = product["artifact_color"]["rgb"]

        expected_colors[f"artwork-{index}"] = (
            f"#{rgb['red']:02x}{rgb['green']:02x}{rgb['blue']:02x}"
        )

    assert set(expected_colors.values()) == {
        "#ff0000",
        "#0000ff",
    }

    artwork_group = root.find(f"./{{{namespace}}}g[@id='artwork']")

    assert artwork_group is not None

    for identity, expected_fill in expected_colors.items():
        component = artwork_group.find(f"./{{{namespace}}}g[@id='{identity}']")

        assert component is not None
        assert component.get("fill") == expected_fill
        assert component.get("transform")
        assert len(component) > 0

    # The same dependency-aware build still produces a valid 3MF.
    package_stage = next(stage for stage in plan.stages if stage.spec.name == "package")

    package_product = next(
        product for product in package_stage.products if product.spec.name == "artifact"
    )

    assert package_product.path.is_file()
    assert zipfile.is_zipfile(package_product.path)

    # Consuming Artwork does not require its standalone manufacturing.
    assert not (artwork_root / "40-extrude" / "products.json").exists()

    assert not (artwork_root / "50-package" / "artifact.3mf").exists()

    assert (shape_root / "40-package" / "artifact.3mf").is_file()


@pytest.mark.slow
def deferred_test_shape_separate_outer_ridge_preserves_base_and_artwork_region_fill(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    A separate inset Outer Ridge must preserve nonempty Base geometry
    and the independently manufactured Artwork Region Fill.

    The Base retains the Shape's full outer envelope. The Ridge is
    inset from that envelope, and Artwork Region Fill remains a
    distinct physical component.

    This test deliberately does not prescribe the Ridge's Z interval:
    that is governed by the existing extrusion contract.
    """
    monkeypatch.chdir(tmp_path)

    artifact_id = "separate-inset-ridge-shape"

    shape_size = 100.0
    ridge_inset = 4.0
    ridge_width = 2.0

    write_artifact_config(
        artifact_id,
        {
            "realizations": {
                "shape_default": {
                    "shape_geometry": "circle",
                    "shape_size": shape_size,
                    "shape_base_raise": 2.0,
                    "shape_base_color": "test-white",
                    "shape_outer_ridge_style": "separate",
                    "shape_outer_ridge_inset": ridge_inset,
                    "shape_outer_ridge_width": ridge_width,
                    "shape_outer_ridge_raise": 1.0,
                    "shape_outer_ridge_color": "test-red",
                }
            }
        },
        project_root=tmp_path,
    )

    plans = create_build_plans(
        artifact_id,
        model_name="shape",
        variant_name="default",
        project_root=tmp_path,
    )
    assert len(plans) == 1

    plan = plans[0]
    execute_dependency_build(plan)

    package_path = (
        tmp_path
        / "artifacts"
        / artifact_id
        / "shape"
        / "shape_default"
        / "40-package"
        / "artifact.3mf"
    )
    assert package_path.is_file()
    assert zipfile.is_zipfile(package_path)

    with zipfile.ZipFile(package_path) as archive:
        model_paths = [
            name
            for name in archive.namelist()
            if name.startswith("3D/") and name.endswith(".model")
        ]
        assert len(model_paths) == 1
        model = ET.fromstring(archive.read(model_paths[0]))

    objects = model.findall(f".//{{{CORE_NS}}}object")

    def find_component(identity: str) -> ET.Element:
        """Locate a physical mesh by its Shape component identity."""

        matches = []

        for obj in objects:
            name = obj.get("name")

            if name is None:
                continue

            if (
                name == identity
                or name.startswith(f"{identity}:")
                or name.endswith(f":{identity}")
                or f":{identity}:" in name
            ):
                matches.append(obj)

        assert len(matches) == 1, (
            f"Expected one {identity!r} object; "
            f"available names: {[obj.get('name') for obj in objects]}"
        )

        return matches[0]

    def mesh_vertices(
        obj: ET.Element,
    ) -> list[tuple[float, float, float]]:
        vertices = obj.findall(f".//{{{CORE_NS}}}vertex")
        triangles = obj.findall(f".//{{{CORE_NS}}}triangle")

        assert vertices, f"Empty mesh: {obj.get('name')}"
        assert triangles, f"No triangles: {obj.get('name')}"

        return [
            (
                float(vertex.attrib["x"]),
                float(vertex.attrib["y"]),
                float(vertex.attrib["z"]),
            )
            for vertex in vertices
        ]

    base = find_component("base")
    ridge = find_component("ridge")
    region_fill = find_component("artwork-region-fill")

    assert (
        len(
            {
                base.attrib["id"],
                ridge.attrib["id"],
                region_fill.attrib["id"],
            }
        )
        == 3
    )

    base_vertices = mesh_vertices(base)
    ridge_vertices = mesh_vertices(ridge)
    region_vertices = mesh_vertices(region_fill)

    def xy_bounds(
        vertices: list[tuple[float, float, float]],
    ) -> tuple[float, float, float, float]:
        xs = [x for x, _, _ in vertices]
        ys = [y for _, y, _ in vertices]
        return min(xs), max(xs), min(ys), max(ys)

    base_bounds = xy_bounds(base_vertices)
    ridge_bounds = xy_bounds(ridge_vertices)
    region_bounds = xy_bounds(region_vertices)

    def xy_width(
        bounds: tuple[float, float, float, float],
    ) -> float:
        return bounds[1] - bounds[0]

    def xy_height(
        bounds: tuple[float, float, float, float],
    ) -> float:
        return bounds[3] - bounds[2]

    expected_ridge_diameter = shape_size - 2.0 * ridge_inset
    expected_region_diameter = expected_ridge_diameter - 2.0 * ridge_width

    # Base retains the complete Shape footprint.
    assert xy_width(base_bounds) == pytest.approx(shape_size, abs=0.2)
    assert xy_height(base_bounds) == pytest.approx(shape_size, abs=0.2)

    # Separate Ridge is physically inset from the outer edge.
    assert xy_width(ridge_bounds) == pytest.approx(expected_ridge_diameter, abs=0.2)
    assert xy_height(ridge_bounds) == pytest.approx(expected_ridge_diameter, abs=0.2)

    # Artwork Region Fill remains inside the Ridge.
    assert xy_width(region_bounds) == pytest.approx(expected_region_diameter, abs=0.2)
    assert xy_height(region_bounds) == pytest.approx(expected_region_diameter, abs=0.2)

    # Base and Artwork Region Fill preserve the configured base
    # height. The Ridge's Z interval is intentionally not assumed.
    for identity, vertices in (
        ("base", base_vertices),
        ("artwork-region-fill", region_vertices),
    ):
        z_values = [z for _, _, z in vertices]
        assert min(z_values) == pytest.approx(0.0, abs=1e-5), identity
        assert max(z_values) == pytest.approx(2.0, abs=1e-5), identity

    # The inset leaves a real Base margin outside the Ridge.
    assert base_bounds[0] < ridge_bounds[0]
    assert base_bounds[1] > ridge_bounds[1]
    assert base_bounds[2] < ridge_bounds[2]
    assert base_bounds[3] > ridge_bounds[3]
