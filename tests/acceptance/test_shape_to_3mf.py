"""
End-to-end acceptance tests for Shape artifact production.
"""
# File: tests/acceptance/test_shape_to_3mf.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

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
    update_artifact_config,
    write_artifact_config,
)
from lowkey_artifact_builder.engine import (
    create_build_plans,
    execute_dependency_build,
)
from lowkey_artifact_builder.formats.threemf import CORE_NS

# =========================================================
# Acceptance tests
# =========================================================


@pytest.mark.slow
def test_shape_builds_complete_3mf_without_artwork(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """
    A Shape without Artwork can be interactively configured and built
    into a complete 3MF artifact through the public CLI.

    Shape structural geometry begins in registered nonphysical space.
    Physical X/Y size and base thickness are introduced by extrusion,
    and the resulting physical component is packaged into the final
    artifact.3mf.

    The default Shape base retains its semantic color identity through
    dimensionalization and packaging.

    No Artwork source or completed Artwork artifact is required.
    """

    # -----------------------------------------------------
    # Arrange temporary project
    # -----------------------------------------------------

    project_root = tmp_path

    monkeypatch.chdir(
        project_root,
    )

    runner = CliRunner()

    # -----------------------------------------------------
    # Configure through the public CLI
    # -----------------------------------------------------

    #
    # Interactive response:
    #
    #   2 -> shape model
    #
    # Shape's initial structural parameters are supplied by
    # model defaults, so no additional parameter prompts are
    # required.
    #

    config_result = runner.invoke(
        cli,
        [
            "config",
            "testshape",
        ],
        input="2\n",
    )

    assert config_result.exit_code == 0, (
        f"Shape configuration failed:\n{config_result.output}\n{config_result.exception!r}"
    )

    # -----------------------------------------------------
    # Verify configuration can be inspected
    # -----------------------------------------------------

    inspect_result = runner.invoke(
        cli,
        [
            "config",
            "testshape",
        ],
    )

    assert inspect_result.exit_code == 0, (
        "Shape configuration could not be read:\n"
        f"{inspect_result.output}\n"
        f"{inspect_result.exception!r}"
    )

    # -----------------------------------------------------
    # Plan
    # -----------------------------------------------------

    plans = create_build_plans(
        "testshape",
        project_root=project_root,
    )

    assert len(plans) == 1

    plan = plans[0]

    assert plan.artifact_id == "testshape"
    assert plan.model_name == "shape"
    assert plan.realization_name == "default"

    assert plan.artifact_dir.is_relative_to(
        project_root,
    )

    stage_names = tuple(stage.spec.name for stage in plan.stages)

    assert stage_names == (
        "structure",
        "compose",
        "extrude",
        "package",
    )

    # -----------------------------------------------------
    # Build through the public CLI
    # -----------------------------------------------------

    build_result = runner.invoke(
        cli,
        [
            "build",
            "testshape",
        ],
    )

    assert build_result.exit_code == 0, (
        f"Shape build failed:\n{build_result.output}\n{build_result.exception!r}"
    )

    # -----------------------------------------------------
    # Locate final product through the build plan
    # -----------------------------------------------------

    package_stage = next(stage for stage in plan.stages if stage.spec.name == "package")

    artifact_product = next(
        product for product in package_stage.products if product.spec.name == "artifact"
    )

    output = artifact_product.path

    # -----------------------------------------------------
    # Verify final product
    # -----------------------------------------------------

    assert output.is_relative_to(
        project_root,
    )

    assert output.is_file(), f"Build did not produce the expected Shape 3MF: {output}"

    assert output.stat().st_size > 0

    # 3MF is an OPC/ZIP package. Verify that the result is
    # structurally a 3MF rather than merely a file carrying
    # the .3mf extension.

    assert zipfile.is_zipfile(
        output,
    )

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

    # -----------------------------------------------------
    # Verify packaged component identity and color
    # -----------------------------------------------------

    model = ET.fromstring(
        model_data,
    )

    objects = model.findall(
        f".//{{{CORE_NS}}}object",
    )

    materials = model.findall(
        f".//{{{CORE_NS}}}basematerials",
    )

    assert len(objects) == 1

    base_object = objects[0]

    assert base_object.get("name") == "testshape-base-white"

    assert len(materials) == 1

    base_material = materials[0]

    base_color = base_material.find(
        f"{{{CORE_NS}}}base",
    )

    assert base_color is not None

    #
    # This test intentionally exercises the model default.
    # The semantic default is "white". Its RGB representation
    # belongs to the mutable physical filament catalog and is
    # therefore not asserted here.
    #

    assert base_color.get("name") == "white"

    assert base_object.get("pid") == base_material.get("id")
    assert base_object.get("pindex") == "0"


@pytest.mark.slow
@pytest.mark.parametrize(
    "ridge_style",
    [
        "separate",
        "integrated",
    ],
)
def test_shape_ridge_preserves_distinct_component_colors(
    tmp_path: Path,
    monkeypatch,
    ridge_style: str,
) -> None:
    """
    A physical Shape ridge may retain a semantic color distinct from
    the base through the complete public build pipeline.

    Both separate ridges and positive integrated ridges produce an
    independently identifiable ridge-color volume in artifact.3mf.
    """

    project_root = tmp_path

    monkeypatch.chdir(
        project_root,
    )

    runner = CliRunner()

    config_result = runner.invoke(
        cli,
        [
            "config",
            "colored-shape",
        ],
        input="2\n",
    )

    assert config_result.exit_code == 0, (
        f"Shape configuration failed:\n{config_result.output}\n{config_result.exception!r}"
    )

    update_artifact_config(
        "colored-shape",
        {
            "parameters": {
                "shape_base_color": "test-white",
                "shape_outer_ridge_width": 2.0,
                "shape_outer_ridge_raise": 1.0,
                "shape_outer_ridge_style": ridge_style,
                "shape_outer_ridge_color": "test-red",
            },
        },
        project_root=project_root,
    )

    build_result = runner.invoke(
        cli,
        [
            "build",
            "colored-shape",
        ],
    )

    assert build_result.exit_code == 0, (
        f"Shape build failed:\n{build_result.output}\n{build_result.exception!r}"
    )

    plans = create_build_plans(
        "colored-shape",
        project_root=project_root,
    )

    assert len(plans) == 1

    plan = plans[0]

    package_stage = next(stage for stage in plan.stages if stage.spec.name == "package")

    artifact_product = next(
        product for product in package_stage.products if product.spec.name == "artifact"
    )

    output = artifact_product.path

    assert output.is_file()
    assert zipfile.is_zipfile(
        output,
    )

    with zipfile.ZipFile(
        output,
    ) as archive:
        model_name = next(
            name
            for name in archive.namelist()
            if name.startswith("3D/") and name.endswith(".model")
        )

        model = ET.fromstring(
            archive.read(
                model_name,
            ),
        )

    objects = model.findall(
        f".//{{{CORE_NS}}}object",
    )

    materials = model.findall(
        f".//{{{CORE_NS}}}basematerials",
    )

    objects_by_name = {object_.get("name"): object_ for object_ in objects}

    assert set(objects_by_name) == {
        "colored-shape-base-test-white",
        "colored-shape-ridge-test-red",
    }

    assert len(materials) == 2

    materials_by_id = {material.get("id"): material for material in materials}

    base_object = objects_by_name["colored-shape-base-test-white"]

    base_material = materials_by_id[base_object.get("pid")]

    base_color = base_material.find(
        f"{{{CORE_NS}}}base",
    )

    assert base_color is not None
    assert base_color.get("name") == "test-white"
    assert base_color.get("displaycolor") == "#FFFFFF"
    assert base_object.get("pindex") == "0"

    ridge_object = objects_by_name["colored-shape-ridge-test-red"]

    ridge_material = materials_by_id[ridge_object.get("pid")]

    ridge_color = ridge_material.find(
        f"{{{CORE_NS}}}base",
    )

    assert ridge_color is not None
    assert ridge_color.get("name") == "test-red"
    assert ridge_color.get("displaycolor") == "#FF0000"
    assert ridge_object.get("pindex") == "0"


@pytest.mark.slow
def test_shape_component_colors_do_not_change_geometry(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """
    Shape semantic colors do not affect physical geometry.

    Two Shapes with identical structural parameters but different
    component colors produce identical packaged mesh geometry.
    """

    project_root = tmp_path

    monkeypatch.chdir(
        project_root,
    )

    runner = CliRunner()

    for artifact_id in (
        "white-red-shape",
        "red-white-shape",
    ):
        config_result = runner.invoke(
            cli,
            [
                "config",
                artifact_id,
            ],
            input="2\n",
        )

        assert config_result.exit_code == 0, (
            f"Shape configuration failed for {artifact_id!r}:\n"
            f"{config_result.output}\n"
            f"{config_result.exception!r}"
        )

    structural_parameters = {
        "shape_outer_ridge_width": 2.0,
        "shape_outer_ridge_raise": 1.0,
        "shape_outer_ridge_style": "separate",
    }

    update_artifact_config(
        "white-red-shape",
        {
            "parameters": {
                **structural_parameters,
                "shape_base_color": "white",
                "shape_outer_ridge_color": "red",
            },
        },
        project_root=project_root,
    )

    update_artifact_config(
        "red-white-shape",
        {
            "parameters": {
                **structural_parameters,
                "shape_base_color": "red",
                "shape_outer_ridge_color": "white",
            },
        },
        project_root=project_root,
    )

    for artifact_id in (
        "white-red-shape",
        "red-white-shape",
    ):
        build_result = runner.invoke(
            cli,
            [
                "build",
                artifact_id,
            ],
        )

        assert build_result.exit_code == 0, (
            f"Shape build failed for {artifact_id!r}:\n"
            f"{build_result.output}\n"
            f"{build_result.exception!r}"
        )

    def packaged_meshes(
        artifact_id: str,
    ) -> dict[str, bytes]:
        plans = create_build_plans(
            artifact_id,
            project_root=project_root,
        )

        assert len(plans) == 1

        package_stage = next(stage for stage in plans[0].stages if stage.spec.name == "package")

        artifact_product = next(
            product for product in package_stage.products if product.spec.name == "artifact"
        )

        with zipfile.ZipFile(
            artifact_product.path,
        ) as archive:
            model_name = next(
                name
                for name in archive.namelist()
                if name.startswith("3D/") and name.endswith(".model")
            )

            model = ET.fromstring(
                archive.read(
                    model_name,
                ),
            )

        result: dict[str, bytes] = {}

        for object_ in model.findall(
            f".//{{{CORE_NS}}}object",
        ):
            name = object_.get("name")

            assert name is not None

            component_identity = name.removeprefix(
                f"{artifact_id}-",
            )

            role = component_identity.split(
                "-",
                maxsplit=1,
            )[0]

            assert role in {
                "base",
                "ridge",
            }

            mesh = object_.find(
                f"{{{CORE_NS}}}mesh",
            )

            assert mesh is not None

            result[role] = ET.tostring(
                mesh,
            )

        return result

    white_red_meshes = packaged_meshes(
        "white-red-shape",
    )

    red_white_meshes = packaged_meshes(
        "red-white-shape",
    )

    assert white_red_meshes.keys() == {
        "base",
        "ridge",
    }

    assert red_white_meshes.keys() == {
        "base",
        "ridge",
    }

    assert white_red_meshes == red_white_meshes


@pytest.mark.slow
def test_shape_builds_complete_3mf_with_registered_artwork(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """
    Shape consumes registered Artwork and builds a complete 3MF artifact.

    Building the Shape automatically produces the bound Artwork only through
    its reusable registered vector representation. Artwork extrusion and
    packaging are not prerequisites for Shape manufacturing.

    The final Shape artifact preserves both structural Shape identity and
    incorporated Artwork component/color identity.
    """

    project_root = tmp_path

    monkeypatch.chdir(
        project_root,
    )

    # -----------------------------------------------------
    # Create canonical Artwork input
    # -----------------------------------------------------

    repository_root = Path(__file__).resolve().parents[2]

    fixture_source = repository_root / "tests" / "assets" / "nydeli-clean.png"

    assert fixture_source.is_file(), f"Acceptance artwork does not exist: {fixture_source}"

    artwork_directory = project_root / "artifacts" / "source-artwork"

    artwork_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    artwork_input = artwork_directory / "artifact.png"

    shutil.copy2(
        fixture_source,
        artwork_input,
    )

    # -----------------------------------------------------
    # Configure reusable Artwork producer
    # -----------------------------------------------------

    write_artifact_config(
        "source-artwork",
        {
            "model": "artwork",
            "source": str(
                artwork_input,
            ),
        },
        project_root=project_root,
    )

    # -----------------------------------------------------
    # Configure Shape consumer
    # -----------------------------------------------------

    write_artifact_config(
        "artwork-shape",
        {
            "model": "shape",
            "shape_base_color": "test-white",
            "product_dependencies": {
                "manifest": {
                    "model": "artwork",
                    "stage": "vector",
                    "product": "manifest",
                    "artifact": "source-artwork",
                    "realization": "default",
                },
            },
        },
        project_root=project_root,
    )

    # -----------------------------------------------------
    # Plan Shape
    # -----------------------------------------------------

    plans = create_build_plans(
        "artwork-shape",
        project_root=project_root,
    )

    assert len(plans) == 1

    plan = plans[0]

    assert plan.artifact_id == "artwork-shape"
    assert plan.model_name == "shape"
    assert plan.realization_name == "default"

    assert tuple(stage.spec.name for stage in plan.stages) == (
        "structure",
        "compose",
        "extrude",
        "package",
    )

    # -----------------------------------------------------
    # Build Shape through dependency-aware orchestration
    # -----------------------------------------------------

    execute_dependency_build(
        plan,
    )

    # -----------------------------------------------------
    # Verify targeted Artwork production
    # -----------------------------------------------------

    artwork_root = project_root / "artifacts" / "source-artwork" / "artwork" / "default"

    assert (artwork_root / "10-prepare" / "trace.svg").is_file()

    assert (artwork_root / "20-raster" / "products.json").is_file()

    artwork_vector_manifest = artwork_root / "30-vector" / "products.json"

    assert artwork_vector_manifest.is_file()

    # Shape consumes Artwork's registered vector representation.
    # Standalone Artwork manufacturing is not a prerequisite.

    assert not (artwork_root / "40-extrude" / "products.json").exists()

    assert not (artwork_root / "50-package" / "artifact.3mf").exists()

    # -----------------------------------------------------
    # Read registered Artwork contract
    # -----------------------------------------------------

    artwork_manifest_data = json.loads(
        artwork_vector_manifest.read_text(
            encoding="utf-8",
        )
    )

    artwork_products = artwork_manifest_data["products"]

    assert isinstance(
        artwork_products,
        list,
    )

    assert artwork_products

    # -----------------------------------------------------
    # Locate final Shape artifact through original plan
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # Read final Shape 3MF
    # -----------------------------------------------------

    with zipfile.ZipFile(
        output,
    ) as archive:
        names = set(
            archive.namelist(),
        )

        assert "[Content_Types].xml" in names

        model_name = next(
            name for name in names if name.startswith("3D/") and name.endswith(".model")
        )

        model = ET.fromstring(
            archive.read(
                model_name,
            ),
        )

    objects = model.findall(
        f".//{{{CORE_NS}}}object",
    )

    materials = model.findall(
        f".//{{{CORE_NS}}}basematerials",
    )

    objects_by_name = {object_.get("name"): object_ for object_ in objects}

    # -----------------------------------------------------
    # Verify structural and incorporated component identity
    # -----------------------------------------------------

    assert "artwork-shape-base-test-white" in objects_by_name

    artwork_objects = {
        name: object_
        for name, object_ in objects_by_name.items()
        if name is not None
        and name.startswith(
            "artwork-shape-artwork-",
        )
    }

    expected_artwork_object_names = {
        (f"artwork-shape-artwork-{product['index']}-{product['printer_color']['name']}")
        for product in artwork_products
    }

    assert set(artwork_objects) == expected_artwork_object_names

    # -----------------------------------------------------
    # Verify semantic colors survived complete pipeline
    # -----------------------------------------------------

    materials_by_id = {material.get("id"): material for material in materials}

    base_object = objects_by_name["artwork-shape-base-test-white"]

    base_material = materials_by_id[base_object.get("pid")]

    base_color = base_material.find(
        f"{{{CORE_NS}}}base",
    )

    assert base_color is not None
    assert base_color.get("name") == "test-white"
    assert base_color.get("displaycolor") == "#FFFFFF"
    assert base_object.get("pindex") == "0"

    for product in artwork_products:
        index = product["index"]

        printer_color = product["printer_color"]

        expected_name = printer_color["name"]
        expected_color = printer_color["rgb"]

        expected_display_color = (
            f"#{expected_color['red']:02X}{expected_color['green']:02X}{expected_color['blue']:02X}"
        )

        artwork_object = artwork_objects[f"artwork-shape-artwork-{index}-{expected_name}"]

        artwork_material = materials_by_id[artwork_object.get("pid")]

        artwork_color = artwork_material.find(
            f"{{{CORE_NS}}}base",
        )

        assert artwork_color is not None
        assert artwork_color.get("name") == expected_name
        assert artwork_color.get("displaycolor") == expected_display_color
        assert artwork_object.get("pindex") == "0"


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
    # Create canonical Artwork input
    # -----------------------------------------------------

    repository_root = Path(__file__).resolve().parents[2]

    fixture_source = repository_root / "tests" / "assets" / "nydeli-clean.png"

    assert fixture_source.is_file()

    artwork_directory = project_root / "artifacts" / "source-artwork"

    artwork_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    artwork_input = artwork_directory / "artifact.png"

    shutil.copy2(
        fixture_source,
        artwork_input,
    )

    # -----------------------------------------------------
    # Configure reusable Artwork producer
    # -----------------------------------------------------

    write_artifact_config(
        "source-artwork",
        {
            "model": "artwork",
            "source": str(
                artwork_input,
            ),
        },
        project_root=project_root,
    )

    # -----------------------------------------------------
    # Configure Shape consumer
    # -----------------------------------------------------

    write_artifact_config(
        "artwork-shape",
        {
            "model": "shape",
            "shape_size": 100.0,
            "product_dependencies": {
                "manifest": {
                    "model": "artwork",
                    "stage": "vector",
                    "product": "manifest",
                    "artifact": "source-artwork",
                    "realization": "default",
                },
            },
        },
        project_root=project_root,
    )

    # -----------------------------------------------------
    # Build initial Shape
    # -----------------------------------------------------

    initial_plan = create_build_plans(
        "artwork-shape",
        project_root=project_root,
    )[0]

    execute_dependency_build(
        initial_plan,
    )

    artwork_root = project_root / "artifacts" / "source-artwork" / "artwork" / "default"

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
            "shape_size": 90.0,
        },
        project_root=project_root,
    )

    resized_plan = create_build_plans(
        "artwork-shape",
        project_root=project_root,
    )[0]

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

    # Standalone Artwork manufacturing remains unnecessary.

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

    # -----------------------------------------------------
    # Create canonical Artwork input
    # -----------------------------------------------------

    repository_root = Path(__file__).resolve().parents[2]

    fixture_source = repository_root / "tests" / "assets" / "nydeli-clean.png"

    assert fixture_source.is_file()

    artwork_directory = project_root / "artifacts" / "source-artwork"

    artwork_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    artwork_input = artwork_directory / "artifact.png"

    shutil.copy2(
        fixture_source,
        artwork_input,
    )

    # -----------------------------------------------------
    # Configure reusable Artwork producer
    # -----------------------------------------------------

    write_artifact_config(
        "source-artwork",
        {
            "model": "artwork",
            "source": str(
                artwork_input,
            ),
        },
        project_root=project_root,
    )

    artwork_dependency = {
        "manifest": {
            "model": "artwork",
            "stage": "vector",
            "product": "manifest",
            "artifact": "source-artwork",
            "realization": "default",
        },
    }

    # -----------------------------------------------------
    # Configure first Shape consumer
    # -----------------------------------------------------

    write_artifact_config(
        "circle-shape",
        {
            "model": "shape",
            "shape_geometry": "circle",
            "shape_size": 100.0,
            "product_dependencies": artwork_dependency,
        },
        project_root=project_root,
    )

    # -----------------------------------------------------
    # Build first Shape
    # -----------------------------------------------------

    circle_plan = create_build_plans(
        "circle-shape",
        project_root=project_root,
    )[0]

    execute_dependency_build(
        circle_plan,
    )

    artwork_root = project_root / "artifacts" / "source-artwork" / "artwork" / "default"

    artwork_vector_manifest = artwork_root / "30-vector" / "products.json"

    assert artwork_vector_manifest.is_file()

    initial_vector_bytes = artwork_vector_manifest.read_bytes()

    initial_component_bytes = {
        path.name: path.read_bytes() for path in (artwork_root / "30-vector").glob("*.svg")
    }

    assert initial_component_bytes

    # Shape consumption stops at registered Artwork.

    assert not (artwork_root / "40-extrude" / "products.json").exists()

    assert not (artwork_root / "50-package" / "artifact.3mf").exists()

    # -----------------------------------------------------
    # Configure physically different Shape consumer
    # -----------------------------------------------------

    write_artifact_config(
        "polygon-shape",
        {
            "model": "shape",
            "shape_geometry": "polygon",
            "shape_sides": 7,
            "shape_size": 120.0,
            "product_dependencies": artwork_dependency,
        },
        project_root=project_root,
    )

    # -----------------------------------------------------
    # Build second Shape
    # -----------------------------------------------------

    polygon_plan = create_build_plans(
        "polygon-shape",
        project_root=project_root,
    )[0]

    execute_dependency_build(
        polygon_plan,
    )

    # -----------------------------------------------------
    # Verify registered Artwork was reused unchanged
    # -----------------------------------------------------

    assert artwork_vector_manifest.read_bytes() == initial_vector_bytes

    reused_component_bytes = {
        path.name: path.read_bytes() for path in (artwork_root / "30-vector").glob("*.svg")
    }

    assert reused_component_bytes == initial_component_bytes

    # Neither consumer requires standalone Artwork manufacturing.

    assert not (artwork_root / "40-extrude" / "products.json").exists()

    assert not (artwork_root / "50-package" / "artifact.3mf").exists()

    # -----------------------------------------------------
    # Verify both Shape artifacts exist
    # -----------------------------------------------------

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
def test_second_shape_does_not_reexecute_registered_artwork_stages(
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

    # -----------------------------------------------------
    # Create canonical Artwork input
    # -----------------------------------------------------

    repository_root = Path(__file__).resolve().parents[2]

    fixture_source = repository_root / "tests" / "assets" / "nydeli-clean.png"

    assert fixture_source.is_file()

    artwork_directory = project_root / "artifacts" / "source-artwork"

    artwork_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    artwork_input = artwork_directory / "artifact.png"

    shutil.copy2(
        fixture_source,
        artwork_input,
    )

    # -----------------------------------------------------
    # Configure reusable Artwork producer
    # -----------------------------------------------------

    write_artifact_config(
        "source-artwork",
        {
            "model": "artwork",
            "source": str(
                artwork_input,
            ),
        },
        project_root=project_root,
    )

    artwork_dependency = {
        "manifest": {
            "model": "artwork",
            "stage": "vector",
            "product": "manifest",
            "artifact": "source-artwork",
            "realization": "default",
        },
    }

    # -----------------------------------------------------
    # Configure two different Shape consumers
    # -----------------------------------------------------

    write_artifact_config(
        "circle-shape",
        {
            "model": "shape",
            "shape_geometry": "circle",
            "shape_size": 100.0,
            "product_dependencies": artwork_dependency,
        },
        project_root=project_root,
    )

    write_artifact_config(
        "polygon-shape",
        {
            "model": "shape",
            "shape_geometry": "polygon",
            "shape_sides": 7,
            "shape_size": 120.0,
            "product_dependencies": artwork_dependency,
        },
        project_root=project_root,
    )

    # -----------------------------------------------------
    # Build first Shape and realize registered Artwork
    # -----------------------------------------------------

    circle_plan = create_build_plans(
        "circle-shape",
        project_root=project_root,
    )[0]

    execute_dependency_build(
        circle_plan,
    )

    artwork_root = project_root / "artifacts" / "source-artwork" / "artwork" / "default"

    assert (artwork_root / "10-prepare" / "trace.svg").is_file()
    assert (artwork_root / "20-raster" / "products.json").is_file()
    assert (artwork_root / "30-vector" / "products.json").is_file()

    # -----------------------------------------------------
    # Observe second Shape build
    # -----------------------------------------------------

    events = []

    polygon_plan = create_build_plans(
        "polygon-shape",
        project_root=project_root,
    )[0]

    execute_dependency_build(
        polygon_plan,
        event_sink=events.append,
    )

    # -----------------------------------------------------
    # Registered Artwork is not reexecuted
    # -----------------------------------------------------

    artwork_started = tuple(
        event.stage_name
        for event in events
        if event.kind == "stage.started"
        and event.artifact_id == "source-artwork"
        and event.model_name == "artwork"
    )

    assert artwork_started == ()

    # -----------------------------------------------------
    # Second Shape manufacturing does execute
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # Standalone Artwork manufacturing remains unnecessary
    # -----------------------------------------------------

    assert not (artwork_root / "40-extrude" / "products.json").exists()

    assert not (artwork_root / "50-package" / "artifact.3mf").exists()


@pytest.mark.slow
def test_shape_policy_changes_do_not_reexecute_registered_artwork(
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

    # -----------------------------------------------------
    # Create canonical Artwork input
    # -----------------------------------------------------

    repository_root = Path(__file__).resolve().parents[2]

    fixture_source = repository_root / "tests" / "assets" / "nydeli-clean.png"

    assert fixture_source.is_file()

    artwork_directory = project_root / "artifacts" / "source-artwork"

    artwork_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    artwork_input = artwork_directory / "artifact.png"

    shutil.copy2(
        fixture_source,
        artwork_input,
    )

    # -----------------------------------------------------
    # Configure reusable Artwork producer
    # -----------------------------------------------------

    write_artifact_config(
        "source-artwork",
        {
            "model": "artwork",
            "source": str(
                artwork_input,
            ),
        },
        project_root=project_root,
    )

    artwork_dependency = {
        "manifest": {
            "model": "artwork",
            "stage": "vector",
            "product": "manifest",
            "artifact": "source-artwork",
            "realization": "default",
        },
    }

    # -----------------------------------------------------
    # Configure first Shape consumer
    # -----------------------------------------------------

    write_artifact_config(
        "initial-shape",
        {
            "model": "shape",
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
            "product_dependencies": artwork_dependency,
        },
        project_root=project_root,
    )

    # -----------------------------------------------------
    # Realize registered Artwork through first Shape
    # -----------------------------------------------------

    initial_plan = create_build_plans(
        "initial-shape",
        project_root=project_root,
    )[0]

    execute_dependency_build(
        initial_plan,
    )

    artwork_root = project_root / "artifacts" / "source-artwork" / "artwork" / "default"

    assert (artwork_root / "10-prepare" / "trace.svg").is_file()
    assert (artwork_root / "20-raster" / "products.json").is_file()
    assert (artwork_root / "30-vector" / "products.json").is_file()

    assert not (artwork_root / "40-extrude" / "products.json").exists()

    assert not (artwork_root / "50-package" / "artifact.3mf").exists()

    # -----------------------------------------------------
    # Configure Shape with different downstream policy
    # -----------------------------------------------------

    write_artifact_config(
        "changed-shape",
        {
            "model": "shape",
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
            "product_dependencies": artwork_dependency,
        },
        project_root=project_root,
    )

    # -----------------------------------------------------
    # Observe second Shape build
    # -----------------------------------------------------

    events = []

    changed_plan = create_build_plans(
        "changed-shape",
        project_root=project_root,
    )[0]

    execute_dependency_build(
        changed_plan,
        event_sink=events.append,
    )

    # -----------------------------------------------------
    # Registered Artwork does not reexecute
    # -----------------------------------------------------

    artwork_started = tuple(
        event.stage_name
        for event in events
        if event.kind == "stage.started"
        and event.artifact_id == "source-artwork"
        and event.model_name == "artwork"
    )

    assert artwork_started == ()

    # -----------------------------------------------------
    # Changed Shape does execute
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # Standalone Artwork manufacturing remains unnecessary
    # -----------------------------------------------------

    assert not (artwork_root / "40-extrude" / "products.json").exists()

    assert not (artwork_root / "50-package" / "artifact.3mf").exists()


@pytest.mark.slow
def test_shape_size_change_preserves_registered_geometry(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """
    Changing only Shape physical size does not change registered geometry.

    Shape structure and composition exist in canonical registered space.
    shape_size is a physical dimensionalization parameter and therefore
    must not alter either registered product.
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
            "model": "shape",
            "shape_size": 100.0,
        },
        project_root=project_root,
    )

    # -----------------------------------------------------
    # Build initial Shape
    # -----------------------------------------------------

    initial_plan = create_build_plans(
        "resized-shape",
        project_root=project_root,
    )[0]

    execute_dependency_build(
        initial_plan,
    )

    shape_root = project_root / "artifacts" / "resized-shape" / "shape" / "default"

    structure = shape_root / "10-structure" / "structure.svg"
    composition = shape_root / "20-compose" / "composition.svg"

    assert structure.is_file()
    assert composition.is_file()

    initial_structure_bytes = structure.read_bytes()
    initial_composition_bytes = composition.read_bytes()

    # -----------------------------------------------------
    # Change only physical Shape size
    # -----------------------------------------------------

    update_artifact_config(
        "resized-shape",
        {
            "shape_size": 90.0,
        },
        project_root=project_root,
    )

    # -----------------------------------------------------
    # Rebuild through normal orchestration
    # -----------------------------------------------------

    resized_plan = create_build_plans(
        "resized-shape",
        project_root=project_root,
    )[0]

    execute_dependency_build(
        resized_plan,
    )

    # -----------------------------------------------------
    # Registered geometry remains unchanged
    # -----------------------------------------------------

    assert structure.is_file()
    assert composition.is_file()

    assert structure.read_bytes() == initial_structure_bytes
    assert composition.read_bytes() == initial_composition_bytes


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
            "model": "shape",
            "shape_size": 100.0,
        },
        project_root=project_root,
    )

    # -----------------------------------------------------
    # Build initial Shape
    # -----------------------------------------------------

    initial_plan = create_build_plans(
        "resized-shape",
        project_root=project_root,
    )[0]

    execute_dependency_build(
        initial_plan,
    )

    shape_root = project_root / "artifacts" / "resized-shape" / "shape" / "default"

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
            "shape_size": 90.0,
        },
        project_root=project_root,
    )

    # -----------------------------------------------------
    # Rebuild through normal orchestration
    # -----------------------------------------------------

    resized_plan = create_build_plans(
        "resized-shape",
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
    A normal Shape build does not produce Artwork fill by default.

    The Shape consumes registered Artwork through the normal dependency path.
    The default shape_artwork_fill_color of "none" must survive configuration,
    composition, dimensionalization, and packaging without manufacturing an
    Artwork-fill component.
    """

    project_root = tmp_path

    monkeypatch.chdir(
        project_root,
    )

    # -----------------------------------------------------
    # Create canonical Artwork input
    # -----------------------------------------------------

    repository_root = Path(__file__).resolve().parents[2]

    fixture_source = repository_root / "tests" / "assets" / "nydeli-clean.png"

    assert fixture_source.is_file(), f"Acceptance artwork does not exist: {fixture_source}"

    artwork_directory = project_root / "artifacts" / "fill-source"

    artwork_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    artwork_source = artwork_directory / "artifact.png"

    shutil.copy2(
        fixture_source,
        artwork_source,
    )

    # -----------------------------------------------------
    # Configure reusable Artwork producer
    # -----------------------------------------------------

    write_artifact_config(
        "fill-source",
        {
            "model": "artwork",
            "source": str(
                artwork_source,
            ),
            "artwork_size": 200.0,
        },
        project_root=project_root,
    )

    # -----------------------------------------------------
    # Configure Shape consumer with default no-fill policy
    # -----------------------------------------------------

    write_artifact_config(
        "shape-no-fill",
        {
            "model": "shape",
            "shape_geometry": "circle",
            "shape_size": 100.0,
            "shape_base_color": "test-white",
            "product_dependencies": {
                "manifest": {
                    "artifact": "fill-source",
                    "model": "artwork",
                    "realization": "default",
                    "stage": "vector",
                    "product": "manifest",
                },
            },
        },
        project_root=project_root,
    )

    # -----------------------------------------------------
    # Plan and build through dependency-aware orchestration
    # -----------------------------------------------------

    plans = create_build_plans(
        "shape-no-fill",
        project_root=project_root,
    )

    assert len(plans) == 1

    execute_dependency_build(
        plans[0],
    )

    shape_root = project_root / "artifacts" / "shape-no-fill" / "shape" / "default"

    compose_manifest = shape_root / "20-compose" / "products.json"

    extrude_manifest = shape_root / "30-extrude" / "products.json"

    artifact = shape_root / "40-package" / "artifact.3mf"

    assert compose_manifest.is_file()
    assert extrude_manifest.is_file()
    assert artifact.is_file()

    # -----------------------------------------------------
    # Registered composition contains no fill
    # -----------------------------------------------------

    composition_data = json.loads(
        compose_manifest.read_text(
            encoding="utf-8",
        )
    )

    assert composition_data["artwork"] is not None
    assert composition_data["artwork_fill"] is None

    # -----------------------------------------------------
    # Extrusion does not manufacture fill
    # -----------------------------------------------------

    extrusion_data = json.loads(
        extrude_manifest.read_text(
            encoding="utf-8",
        )
    )

    component_names = {component["name"] for component in extrusion_data["components"]}

    assert "base" in component_names
    assert "artwork-fill" not in component_names

    assert any(str(name).startswith("artwork-") for name in component_names)

    # -----------------------------------------------------
    # Packaging does not manufacture fill
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

    packaged_names = {
        object_.get("name")
        for object_ in model.findall(
            f".//{{{CORE_NS}}}object",
        )
    }

    assert "shape-no-fill-base-test-white" in packaged_names

    assert not any(
        name is not None
        and name.startswith(
            "shape-no-fill-artwork-fill-",
        )
        for name in packaged_names
    )

    assert any(
        name is not None
        and name.startswith(
            "shape-no-fill-artwork-",
        )
        for name in packaged_names
    )

    assert any(
        name is not None
        and name.startswith(
            "shape-no-fill-artwork-",
        )
        for name in packaged_names
    )

    # -----------------------------------------------------
    # Shape consumes only reusable registered Artwork
    # -----------------------------------------------------

    artwork_root = project_root / "artifacts" / "fill-source" / "artwork" / "default"

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
    region, dimensionalizes that region using Shape physical policy, preserves
    its semantic color identity, and packages it as an independently
    identifiable final component.
    """

    project_root = tmp_path

    monkeypatch.chdir(
        project_root,
    )

    # -----------------------------------------------------
    # Create canonical Artwork input
    # -----------------------------------------------------

    repository_root = Path(__file__).resolve().parents[2]

    fixture_source = repository_root / "tests" / "assets" / "nydeli-clean.png"

    assert fixture_source.is_file(), f"Acceptance artwork does not exist: {fixture_source}"

    artwork_directory = project_root / "artifacts" / "fill-source"

    artwork_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    artwork_source = artwork_directory / "artifact.png"

    shutil.copy2(
        fixture_source,
        artwork_source,
    )

    # -----------------------------------------------------
    # Configure reusable Artwork producer
    # -----------------------------------------------------

    write_artifact_config(
        "fill-source",
        {
            "model": "artwork",
            "source": str(
                artwork_source,
            ),
            "artwork_size": 200.0,
        },
        project_root=project_root,
    )

    # -----------------------------------------------------
    # Configure Shape consumer with enabled fill
    # -----------------------------------------------------

    write_artifact_config(
        "shape-with-fill",
        {
            "model": "shape",
            "shape_geometry": "circle",
            "shape_size": 100.0,
            "shape_base_color": "test-white",
            "shape_artwork_fill_color": "test-blue",
            "product_dependencies": {
                "manifest": {
                    "artifact": "fill-source",
                    "model": "artwork",
                    "realization": "default",
                    "stage": "vector",
                    "product": "manifest",
                },
            },
        },
        project_root=project_root,
    )

    # -----------------------------------------------------
    # Plan and build through dependency-aware orchestration
    # -----------------------------------------------------

    plans = create_build_plans(
        "shape-with-fill",
        project_root=project_root,
    )

    assert len(plans) == 1

    execute_dependency_build(
        plans[0],
    )

    shape_root = project_root / "artifacts" / "shape-with-fill" / "shape" / "default"

    compose_manifest = shape_root / "20-compose" / "products.json"

    extrude_manifest = shape_root / "30-extrude" / "products.json"

    artifact = shape_root / "40-package" / "artifact.3mf"

    assert compose_manifest.is_file()
    assert extrude_manifest.is_file()
    assert artifact.is_file()

    # -----------------------------------------------------
    # Registered composition contains fill
    # -----------------------------------------------------

    composition_data = json.loads(
        compose_manifest.read_text(
            encoding="utf-8",
        )
    )

    assert composition_data["artwork"] is not None
    assert composition_data["artwork_fill"] is not None

    # -----------------------------------------------------
    # Fill is independently dimensionalized
    # -----------------------------------------------------

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

    assert fill_component["color"] == {
        "name": "test-blue",
        "rgb": [0, 0, 255],
    }

    fill_path = extrude_manifest.parent / str(fill_component["path"])

    assert fill_path.is_file()
    assert fill_path.stat().st_size > 0

    # -----------------------------------------------------
    # Fill survives final packaging
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

    materials_by_id = {material.get("id"): material for material in materials}

    assert "shape-with-fill-base-test-white" in objects_by_name
    assert "shape-with-fill-artwork-fill-test-blue" in objects_by_name

    artwork_object_names = {
        name
        for name in objects_by_name
        if name is not None
        and name.startswith(
            "shape-with-fill-artwork-",
        )
        and name != "shape-with-fill-artwork-fill-test-blue"
    }

    assert artwork_object_names

    # -----------------------------------------------------
    # Fill preserves semantic color identity
    # -----------------------------------------------------

    fill_object = objects_by_name["shape-with-fill-artwork-fill-test-blue"]

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

    # -----------------------------------------------------
    # Fill remains semantically independent
    # -----------------------------------------------------

    base_object = objects_by_name["shape-with-fill-base-test-white"]

    assert fill_object.get("id") != base_object.get("id")

    for artwork_name in artwork_object_names:
        assert fill_object.get("id") != objects_by_name[artwork_name].get("id")

    # -----------------------------------------------------
    # Shape consumes only reusable registered Artwork
    # -----------------------------------------------------

    artwork_root = project_root / "artifacts" / "fill-source" / "artwork" / "default"

    assert (artwork_root / "30-vector" / "products.json").is_file()

    assert not (artwork_root / "40-extrude" / "products.json").exists()

    assert not (artwork_root / "50-package" / "artifact.3mf").exists()


@pytest.mark.slow
def test_shape_artwork_fill_remains_distinct_when_base_uses_same_color(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """
    Shape base and Artwork fill may share one semantic color while remaining
    independently identifiable physical components in the final 3MF.

    Semantic color identity does not merge the structural base with the
    Shape-owned Artwork fill.
    """

    project_root = tmp_path

    monkeypatch.chdir(
        project_root,
    )

    # -----------------------------------------------------
    # Create canonical Artwork input
    # -----------------------------------------------------

    repository_root = Path(__file__).resolve().parents[2]

    fixture_source = repository_root / "tests" / "assets" / "nydeli-clean.png"

    assert fixture_source.is_file(), f"Acceptance artwork does not exist: {fixture_source}"

    artwork_directory = project_root / "artifacts" / "fill-source"

    artwork_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    artwork_source = artwork_directory / "artifact.png"

    shutil.copy2(
        fixture_source,
        artwork_source,
    )

    # -----------------------------------------------------
    # Configure reusable Artwork producer
    # -----------------------------------------------------

    write_artifact_config(
        "fill-source",
        {
            "model": "artwork",
            "source": str(
                artwork_source,
            ),
            "artwork_size": 200.0,
        },
        project_root=project_root,
    )

    # -----------------------------------------------------
    # Configure Shape with shared base/fill color
    # -----------------------------------------------------

    write_artifact_config(
        "shared-color-fill-shape",
        {
            "model": "shape",
            "shape_geometry": "circle",
            "shape_size": 100.0,
            "shape_base_color": "test-blue",
            "shape_artwork_fill_color": "test-blue",
            "product_dependencies": {
                "manifest": {
                    "artifact": "fill-source",
                    "model": "artwork",
                    "realization": "default",
                    "stage": "vector",
                    "product": "manifest",
                },
            },
        },
        project_root=project_root,
    )

    # -----------------------------------------------------
    # Build through dependency-aware orchestration
    # -----------------------------------------------------

    plans = create_build_plans(
        "shared-color-fill-shape",
        project_root=project_root,
    )

    assert len(plans) == 1

    execute_dependency_build(
        plans[0],
    )

    shape_root = project_root / "artifacts" / "shared-color-fill-shape" / "shape" / "default"

    extrude_manifest = shape_root / "30-extrude" / "products.json"

    artifact = shape_root / "40-package" / "artifact.3mf"

    assert extrude_manifest.is_file()
    assert artifact.is_file()

    # -----------------------------------------------------
    # Physical manifest preserves distinct roles
    # -----------------------------------------------------

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

    assert components_by_name["base"]["color"] == {
        "name": "test-blue",
        "rgb": [0, 0, 255],
    }

    assert components_by_name["artwork-fill"]["color"] == {
        "name": "test-blue",
        "rgb": [0, 0, 255],
    }

    assert components_by_name["base"]["path"] != components_by_name["artwork-fill"]["path"]

    # -----------------------------------------------------
    # Final 3MF preserves distinct component identity
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

    materials_by_id = {material.get("id"): material for material in materials}

    base_object = objects_by_name["shared-color-fill-shape-base-test-blue"]

    fill_object = objects_by_name["shared-color-fill-shape-artwork-fill-test-blue"]

    assert base_object.get("id") != fill_object.get("id")

    # -----------------------------------------------------
    # Both components retain the shared semantic color
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # Incorporated Artwork remains independently present
    # -----------------------------------------------------

    artwork_object_names = {
        name
        for name in objects_by_name
        if name is not None
        and name.startswith(
            "shared-color-fill-shape-artwork-",
        )
        and name != "shared-color-fill-shape-artwork-fill-test-blue"
    }

    assert artwork_object_names

    # -----------------------------------------------------
    # Standalone Artwork manufacturing remains unnecessary
    # -----------------------------------------------------

    artwork_root = project_root / "artifacts" / "fill-source" / "artwork" / "default"

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
def test_shape_artwork_fill_preserves_physical_interval_with_outer_ridge(
    tmp_path: Path,
    monkeypatch,
    ridge_style: str,
) -> None:
    """
    A physical outer ridge does not alter Artwork fill Z semantics.

    Integrated and separate outer ridges both preserve the Shape-owned
    Artwork-fill interval from shape_base_raise through
    shape_base_raise + shape_artwork_raise.
    """

    project_root = tmp_path

    monkeypatch.chdir(
        project_root,
    )

    # -----------------------------------------------------
    # Create canonical Artwork input
    # -----------------------------------------------------

    repository_root = Path(__file__).resolve().parents[2]

    fixture_source = repository_root / "tests" / "assets" / "nydeli-clean.png"

    assert fixture_source.is_file(), f"Acceptance artwork does not exist: {fixture_source}"

    artwork_directory = project_root / "artifacts" / "ridge-fill-source"

    artwork_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    artwork_source = artwork_directory / "artifact.png"

    shutil.copy2(
        fixture_source,
        artwork_source,
    )

    # -----------------------------------------------------
    # Configure reusable Artwork producer
    # -----------------------------------------------------

    write_artifact_config(
        "ridge-fill-source",
        {
            "model": "artwork",
            "source": str(
                artwork_source,
            ),
            "artwork_size": 200.0,
        },
        project_root=project_root,
    )

    # -----------------------------------------------------
    # Configure Shape with physical ridge and fill
    # -----------------------------------------------------

    artifact_id = f"{ridge_style}-ridge-fill-shape"

    shape_base_raise = 2.0
    shape_artwork_raise = 1.25

    write_artifact_config(
        artifact_id,
        {
            "model": "shape",
            "shape_geometry": "circle",
            "shape_size": 100.0,
            "shape_base_raise": shape_base_raise,
            "shape_artwork_raise": shape_artwork_raise,
            "shape_base_color": "test-white",
            "shape_artwork_fill_color": "test-blue",
            "shape_outer_ridge_width": 2.0,
            "shape_outer_ridge_raise": 1.5,
            "shape_outer_ridge_style": ridge_style,
            "shape_outer_ridge_color": "test-red",
            "product_dependencies": {
                "manifest": {
                    "artifact": "ridge-fill-source",
                    "model": "artwork",
                    "realization": "default",
                    "stage": "vector",
                    "product": "manifest",
                },
            },
        },
        project_root=project_root,
    )

    # -----------------------------------------------------
    # Build through dependency-aware orchestration
    # -----------------------------------------------------

    plans = create_build_plans(
        artifact_id,
        project_root=project_root,
    )

    assert len(plans) == 1

    execute_dependency_build(
        plans[0],
    )

    shape_root = project_root / "artifacts" / artifact_id / "shape" / "default"

    extrude_root = shape_root / "30-extrude"

    extrude_manifest = extrude_root / "products.json"

    artifact = shape_root / "40-package" / "artifact.3mf"

    assert extrude_manifest.is_file()
    assert artifact.is_file()

    # -----------------------------------------------------
    # Physical component contract includes ridge and fill
    # -----------------------------------------------------

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

    assert fill_component["color"] == {
        "name": "test-blue",
        "rgb": [0, 0, 255],
    }

    fill_path = extrude_root / str(fill_component["path"])

    assert fill_path.is_file()
    assert fill_path.stat().st_size > 0

    # -----------------------------------------------------
    # Verify actual physical fill Z interval
    # -----------------------------------------------------

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
        shape_base_raise + shape_artwork_raise,
    )

    # -----------------------------------------------------
    # Ridge and fill survive packaging independently
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

    objects_by_name = {
        object_.get("name"): object_
        for object_ in model.findall(
            f".//{{{CORE_NS}}}object",
        )
    }

    base_name = f"{artifact_id}-base-test-white"
    ridge_name = f"{artifact_id}-ridge-test-red"
    fill_name = f"{artifact_id}-artwork-fill-test-blue"

    assert base_name in objects_by_name
    assert ridge_name in objects_by_name
    assert fill_name in objects_by_name

    artwork_object_names = {
        name
        for name in objects_by_name
        if name is not None
        and name.startswith(
            f"{artifact_id}-artwork-",
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

    # -----------------------------------------------------
    # Standalone Artwork manufacturing remains unnecessary
    # -----------------------------------------------------

    artwork_root = project_root / "artifacts" / "ridge-fill-source" / "artwork" / "default"

    assert (artwork_root / "30-vector" / "products.json").is_file()

    assert not (artwork_root / "40-extrude" / "products.json").exists()

    assert not (artwork_root / "50-package" / "artifact.3mf").exists()
