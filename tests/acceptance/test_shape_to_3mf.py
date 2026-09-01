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

    assert base_object.get("name") == "testshape-base"

    assert len(materials) == 1

    base_material = materials[0]

    base_color = base_material.find(
        f"{{{CORE_NS}}}base",
    )

    assert base_color is not None

    assert base_color.get("name") == "white"
    assert base_color.get("displaycolor") == "#FFFFFF"

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

    # -----------------------------------------------------
    # Configure Shape through the public CLI
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # Configure physical ridge and semantic colors
    # -----------------------------------------------------

    update_artifact_config(
        "colored-shape",
        {
            "parameters": {
                "shape_base_color": "white",
                "shape_outer_ridge_width": 2.0,
                "shape_outer_ridge_raise": 1.0,
                "shape_outer_ridge_style": ridge_style,
                "shape_outer_ridge_color": "red",
            },
        },
        project_root=project_root,
    )

    # -----------------------------------------------------
    # Build through the public CLI
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # Locate final artifact through the build plan
    # -----------------------------------------------------

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
    assert zipfile.is_zipfile(output)

    # -----------------------------------------------------
    # Read packaged 3MF model
    # -----------------------------------------------------

    with zipfile.ZipFile(
        output,
    ) as archive:
        model_name = next(
            name
            for name in archive.namelist()
            if name.startswith("3D/") and name.endswith(".model")
        )

        model = ET.fromstring(
            archive.read(model_name),
        )

    # -----------------------------------------------------
    # Verify component identities
    # -----------------------------------------------------

    objects = model.findall(
        f".//{{{CORE_NS}}}object",
    )

    materials = model.findall(
        f".//{{{CORE_NS}}}basematerials",
    )

    objects_by_name = {object_.get("name"): object_ for object_ in objects}

    assert set(objects_by_name) == {
        "colored-shape-base",
        "colored-shape-ridge",
    }

    assert len(materials) == 2

    materials_by_id = {material.get("id"): material for material in materials}

    # -----------------------------------------------------
    # Verify base semantic color
    # -----------------------------------------------------

    base_object = objects_by_name["colored-shape-base"]

    base_material = materials_by_id[base_object.get("pid")]

    base_color = base_material.find(
        f"{{{CORE_NS}}}base",
    )

    assert base_color is not None

    assert base_color.get("name") == "white"
    assert base_color.get("displaycolor") == "#FFFFFF"

    assert base_object.get("pindex") == "0"

    # -----------------------------------------------------
    # Verify ridge semantic color
    # -----------------------------------------------------

    ridge_object = objects_by_name["colored-shape-ridge"]

    ridge_material = materials_by_id[ridge_object.get("pid")]

    ridge_color = ridge_material.find(
        f"{{{CORE_NS}}}base",
    )

    assert ridge_color is not None

    assert ridge_color.get("name") == "red"
    assert ridge_color.get("displaycolor") == "#DC2626"

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

    # -----------------------------------------------------
    # Configure equivalent Shapes
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # Build both Shapes
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # Read packaged mesh geometry
    # -----------------------------------------------------

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
                archive.read(model_name),
            )

        result: dict[str, bytes] = {}

        for object_ in model.findall(
            f".//{{{CORE_NS}}}object",
        ):
            name = object_.get("name")

            assert name is not None

            role = name.removeprefix(
                f"{artifact_id}-",
            )

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

    # -----------------------------------------------------
    # Colors change semantics, not geometry
    # -----------------------------------------------------

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

    fixture_source = repository_root / "projects" / "nydeli-clean.png"

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

    assert "artwork-shape-base" in objects_by_name

    artwork_objects = {
        name: object_
        for name, object_ in objects_by_name.items()
        if name is not None
        and name.startswith(
            "artwork-shape-artwork-",
        )
    }

    expected_artwork_object_names = {
        f"artwork-shape-artwork-{product['index']}" for product in artwork_products
    }

    assert (
        set(
            artwork_objects,
        )
        == expected_artwork_object_names
    )

    # -----------------------------------------------------
    # Verify semantic colors survived complete pipeline
    # -----------------------------------------------------

    materials_by_id = {material.get("id"): material for material in materials}

    base_object = objects_by_name["artwork-shape-base"]

    base_material = materials_by_id[base_object.get("pid")]

    base_color = base_material.find(
        f"{{{CORE_NS}}}base",
    )

    assert base_color is not None
    assert base_color.get("name") == "white"
    assert base_color.get("displaycolor") == "#FFFFFF"
    assert base_object.get("pindex") == "0"

    for product in artwork_products:
        index = product["index"]

        expected_name = product["name"]

        expected_color = product["color"]

        expected_display_color = (
            f"#{expected_color['red']:02X}{expected_color['green']:02X}{expected_color['blue']:02X}"
        )

        artwork_object = artwork_objects[f"artwork-shape-artwork-{index}"]

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

    fixture_source = repository_root / "projects" / "nydeli-clean.png"

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

    fixture_source = repository_root / "projects" / "nydeli-clean.png"

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

    fixture_source = repository_root / "projects" / "nydeli-clean.png"

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
def test_shape_rebuilds_after_size_change(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """
    A completed Shape can be rebuilt after its physical size changes.

    Changing Shape physical size invalidates and rebuilds the downstream
    Shape manufacturing products through normal dependency-aware
    orchestration.
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

    initial_artifact = shape_root / "40-package" / "artifact.3mf"

    existing_base = shape_root / "30-extrude" / "base.stl"

    assert initial_artifact.is_file()
    assert zipfile.is_zipfile(
        initial_artifact,
    )

    assert existing_base.is_file()
    assert existing_base.stat().st_size > 0

    initial_base_bytes = existing_base.read_bytes()

    # -----------------------------------------------------
    # Change Shape size
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
    # Verify extrusion was rebuilt in place
    # -----------------------------------------------------

    assert existing_base.is_file()
    assert existing_base.stat().st_size > 0

    resized_base_bytes = existing_base.read_bytes()

    assert resized_base_bytes != initial_base_bytes

    # -----------------------------------------------------
    # Verify rebuilt package
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
