"""
End-to-end acceptance tests for artifact production.
"""
# File: tests/acceptance/test_png_to_3mf.py
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
from lowkey_artifact_builder.engine import (
    create_build_plans,
)
from lowkey_artifact_builder.formats.threemf import CORE_NS
from lowkey_artifact_builder.model.models.artwork.hole import (
    create_hole_geometry,
)
from lowkey_artifact_builder.model.models.artwork.stages import (
    extrude,
)

# =========================================================
# Acceptance tests
# =========================================================


@pytest.mark.slow
def test_png_builds_complete_3mf(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """
    A PNG Artwork input builds into a semantically colored standalone 3MF.

    Raster and vector processing preserve registered Artwork independently of
    manufacturing dimensions. Extrusion introduces physical dimensions, and
    packaging preserves each independently printable Artwork component's
    product identity, semantic printer color identity, and RGB representation.
    """

    # -----------------------------------------------------
    # Arrange temporary project
    # -----------------------------------------------------

    repository_root = Path(__file__).resolve().parents[2]

    fixture_source = repository_root / "tests" / "assets" / "nydeli-clean.png"

    assert fixture_source.is_file(), f"Acceptance artwork does not exist: {fixture_source}"

    project_root = tmp_path

    source = project_root / "nydeli-clean.png"

    shutil.copy2(
        fixture_source,
        source,
    )

    monkeypatch.chdir(
        project_root,
    )

    runner = CliRunner()

    # -----------------------------------------------------
    # Configure through the public CLI
    # -----------------------------------------------------

    config_result = runner.invoke(
        cli,
        [
            "create",
            "nydeli",
        ],
        input="1\n",
    )

    assert config_result.exit_code == 0, (
        f"Artifact configuration failed:\n{config_result.output}\n{config_result.exception!r}"
    )

    # -----------------------------------------------------
    # Verify configuration can be inspected
    # -----------------------------------------------------

    inspect_result = runner.invoke(
        cli,
        [
            "config",
            "nydeli",
        ],
    )

    assert inspect_result.exit_code == 0, (
        "Artifact configuration could not be read:\n"
        f"{inspect_result.output}\n"
        f"{inspect_result.exception!r}"
    )

    # -----------------------------------------------------
    # Plan explicit artwork.default Variant
    # -----------------------------------------------------

    plans = create_build_plans(
        "nydeli",
        model_name="artwork",
        variant_name="default",
        project_root=project_root,
    )

    assert len(plans) == 1

    plan = plans[0]

    assert plan.artifact_id == "nydeli"
    assert plan.model_name == "artwork"
    assert plan.realization_name == "artwork_default"

    # -----------------------------------------------------
    # Verify backward-compatible envelope configuration
    # -----------------------------------------------------

    assert plan.resolver("artwork_envelope_mode") == "shrink-wrap"

    assert (
        plan.resolver.source(
            "artwork_envelope_mode",
        )
        == "model"
    )

    assert plan.artifact_dir.is_relative_to(
        project_root,
    )

    # -----------------------------------------------------
    # Build explicit artwork.default through public CLI
    # -----------------------------------------------------

    build_result = runner.invoke(
        cli,
        [
            "build",
            "nydeli",
            "--variant",
            "artwork.default",
        ],
    )

    assert build_result.exit_code == 0, (
        f"Artifact build failed:\n{build_result.output}\n{build_result.exception!r}"
    )

    # -----------------------------------------------------
    # Locate extrusion and package products
    # -----------------------------------------------------

    extrude_stage = next(stage for stage in plan.stages if stage.spec.name == "extrude")

    extrude_manifest_product = next(
        product for product in extrude_stage.products if product.spec.name == "manifest"
    )

    package_stage = next(stage for stage in plan.stages if stage.spec.name == "package")

    artifact_product = next(
        product for product in package_stage.products if product.spec.name == "artifact"
    )

    extrude_manifest = extrude_manifest_product.path
    output = artifact_product.path

    # -----------------------------------------------------
    # Verify physical component contract
    # -----------------------------------------------------

    assert extrude_manifest.is_file()

    extrusion_data = json.loads(
        extrude_manifest.read_text(
            encoding="utf-8",
        )
    )

    products = extrusion_data["products"]

    assert isinstance(
        products,
        list,
    )

    assert products

    # -----------------------------------------------------
    # Verify final product
    # -----------------------------------------------------

    assert output.is_relative_to(
        project_root,
    )

    assert output.is_file(), f"Build did not produce the expected 3MF: {output}"

    assert output.stat().st_size > 0

    assert zipfile.is_zipfile(
        output,
    )

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

    # -----------------------------------------------------
    # Verify independently printable Artwork components
    # -----------------------------------------------------

    objects = model.findall(
        f".//{{{CORE_NS}}}object",
    )

    materials = model.findall(
        f".//{{{CORE_NS}}}basematerials",
    )

    objects_by_name = {object_.get("name"): object_ for object_ in objects}

    expected_names = {f"nydeli-{Path(product['path']).stem}" for product in products}

    assert set(objects_by_name) == expected_names

    assert len(materials) == len(products)

    materials_by_id = {material.get("id"): material for material in materials}

    # -----------------------------------------------------
    # Verify component identity and semantic printer color
    # survive packaging independently
    # -----------------------------------------------------

    for product in products:
        printer_color = product["printer_color"]

        semantic_name = printer_color["name"]
        rgb = printer_color["rgb"]

        component_name = f"nydeli-{Path(product['path']).stem}"

        object_ = objects_by_name[component_name]

        material = materials_by_id[object_.get("pid")]

        color = material.find(
            f"{{{CORE_NS}}}base",
        )

        assert color is not None

        assert color.get("name") == semantic_name

        assert color.get("displaycolor") == (
            f"#{rgb['red']:02X}{rgb['green']:02X}{rgb['blue']:02X}"
        )

        assert object_.get("pindex") == "0"


@pytest.mark.slow
def test_png_artwork_with_loop_builds_complete_3mf(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """
    Standalone Artwork with a participating Loop builds through the normal
    pipeline into a complete 3MF containing the Loop as an independently
    printable physical component with its resolved semantic printer color.
    """

    # -----------------------------------------------------
    # Arrange temporary project
    # -----------------------------------------------------

    repository_root = Path(__file__).resolve().parents[2]

    fixture_source = repository_root / "tests" / "assets" / "nydeli-clean.png"

    assert fixture_source.is_file(), f"Acceptance artwork does not exist: {fixture_source}"

    project_root = tmp_path

    source = project_root / "nydeli-clean.png"

    shutil.copy2(
        fixture_source,
        source,
    )

    monkeypatch.chdir(
        project_root,
    )

    runner = CliRunner()

    # -----------------------------------------------------
    # Configure through the public CLI
    # -----------------------------------------------------

    config_result = runner.invoke(
        cli,
        [
            "create",
            "nydeli",
        ],
        input="1\n",
    )

    assert config_result.exit_code == 0, (
        f"Artifact configuration failed:\n{config_result.output}\n{config_result.exception!r}"
    )

    # -----------------------------------------------------
    # Enable Loop for artwork_default
    # -----------------------------------------------------

    artifact_config = project_root / "artifacts" / "nydeli" / "artifact.toml"

    assert artifact_config.is_file()

    with artifact_config.open(
        "a",
        encoding="utf-8",
    ) as stream:
        stream.write(
            """
[realizations.artwork_default]
loop_inner_diameter = 6.0
loop_width = 2.0
loop_position = 0
"""
        )

    # -----------------------------------------------------
    # Plan customized artwork_default Realization
    # -----------------------------------------------------

    plans = create_build_plans(
        "nydeli",
        realization="artwork_default",
        project_root=project_root,
    )

    assert len(plans) == 1

    plan = plans[0]

    assert plan.artifact_id == "nydeli"
    assert plan.model_name == "artwork"
    assert plan.realization_name == "artwork_default"

    assert plan.resolver("loop_inner_diameter") == 6.0
    assert plan.resolver("loop_width") == 2.0
    assert plan.resolver("loop_position") == 0

    # -----------------------------------------------------
    # Build through public CLI
    # -----------------------------------------------------

    build_result = runner.invoke(
        cli,
        [
            "build",
            "nydeli",
            "--variant",
            "artwork.default",
        ],
    )

    assert build_result.exit_code == 0, (
        f"Artifact build failed:\n{build_result.output}\n{build_result.exception!r}"
    )

    # -----------------------------------------------------
    # Locate extrusion and package products
    # -----------------------------------------------------

    extrude_stage = next(stage for stage in plan.stages if stage.spec.name == "extrude")

    extrude_manifest_product = next(
        product for product in extrude_stage.products if product.spec.name == "manifest"
    )

    package_stage = next(stage for stage in plan.stages if stage.spec.name == "package")

    artifact_product = next(
        product for product in package_stage.products if product.spec.name == "artifact"
    )

    extrude_manifest = extrude_manifest_product.path
    output = artifact_product.path

    # -----------------------------------------------------
    # Verify Loop extrusion product
    # -----------------------------------------------------

    assert extrude_manifest.is_file()

    extrusion_data = json.loads(
        extrude_manifest.read_text(
            encoding="utf-8",
        )
    )

    products = extrusion_data["products"]

    assert isinstance(
        products,
        list,
    )

    loop_product = next(product for product in products if product["path"] == "loop.stl")

    printer_color = loop_product["printer_color"]

    assert isinstance(
        printer_color["name"],
        str,
    )

    assert printer_color["name"]

    rgb = printer_color["rgb"]

    assert isinstance(
        rgb["red"],
        int,
    )

    assert isinstance(
        rgb["green"],
        int,
    )

    assert isinstance(
        rgb["blue"],
        int,
    )

    loop_stl = extrude_manifest.parent / loop_product["path"]

    assert loop_stl.is_file()
    assert loop_stl.stat().st_size > 0

    # -----------------------------------------------------
    # Verify final product
    # -----------------------------------------------------

    assert output.is_relative_to(
        project_root,
    )

    assert output.is_file(), f"Build did not produce the expected 3MF: {output}"

    assert output.stat().st_size > 0

    assert zipfile.is_zipfile(
        output,
    )

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

    # -----------------------------------------------------
    # Verify Loop survives as independently printable
    # component
    # -----------------------------------------------------

    objects = model.findall(
        f".//{{{CORE_NS}}}object",
    )

    materials = model.findall(
        f".//{{{CORE_NS}}}basematerials",
    )

    loop_name = "nydeli-loop"

    objects_by_name = {object_.get("name"): object_ for object_ in objects}

    assert loop_name in objects_by_name

    loop_object = objects_by_name[loop_name]

    materials_by_id = {material.get("id"): material for material in materials}

    loop_material = materials_by_id[loop_object.get("pid")]

    color = loop_material.find(
        f"{{{CORE_NS}}}base",
    )

    assert color is not None

    assert color.get("name") == printer_color["name"]

    assert color.get("displaycolor") == (f"#{rgb['red']:02X}{rgb['green']:02X}{rgb['blue']:02X}")

    assert loop_object.get("pindex") == "0"


@pytest.mark.slow
def test_png_artwork_with_base_builds_complete_3mf(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """
    An ordinary Artwork Realization may enable Base through parameter
    overrides and build through the normal pipeline.

    The resulting standalone 3MF contains Base as an independently printable
    physical component with its resolved semantic physical color identity.
    """

    # -----------------------------------------------------
    # Arrange temporary project
    # -----------------------------------------------------

    repository_root = Path(__file__).resolve().parents[2]

    fixture_source = repository_root / "tests" / "assets" / "nydeli-clean.png"

    assert fixture_source.is_file()

    project_root = tmp_path

    source = project_root / "nydeli-clean.png"

    shutil.copy2(
        fixture_source,
        source,
    )

    monkeypatch.chdir(
        project_root,
    )

    runner = CliRunner()

    # -----------------------------------------------------
    # Configure through the public CLI
    # -----------------------------------------------------

    config_result = runner.invoke(
        cli,
        [
            "create",
            "nydeli",
        ],
        input="1\n",
    )

    assert config_result.exit_code == 0, (
        f"Artifact configuration failed:\n{config_result.output}\n{config_result.exception!r}"
    )

    # -----------------------------------------------------
    # Enable Base on the ordinary artwork_default Realization
    # -----------------------------------------------------

    artifact_config = project_root / "artifacts" / "nydeli" / "artifact.toml"

    assert artifact_config.is_file()

    with artifact_config.open(
        "a",
        encoding="utf-8",
    ) as stream:
        stream.write(
            """
[realizations.artwork_default]
artwork_base_raise = 2.0
artwork_base_color = "test-black"
"""
        )

    # -----------------------------------------------------
    # Plan customized ordinary Artwork Realization
    # -----------------------------------------------------

    plans = create_build_plans(
        "nydeli",
        realization="artwork_default",
        project_root=project_root,
    )

    assert len(plans) == 1

    plan = plans[0]

    assert plan.artifact_id == "nydeli"
    assert plan.model_name == "artwork"
    assert plan.realization_name == "artwork_default"

    assert plan.resolver("artwork_base_raise") == 2.0
    assert plan.resolver("artwork_base_color") == "test-black"

    # -----------------------------------------------------
    # Build through the ordinary public CLI
    # -----------------------------------------------------

    build_result = runner.invoke(
        cli,
        [
            "build",
            "nydeli",
            "--variant",
            "artwork.default",
        ],
    )

    assert build_result.exit_code == 0, (
        f"Artifact build failed:\n{build_result.output}\n{build_result.exception!r}"
    )

    # -----------------------------------------------------
    # Locate extrusion and package products
    # -----------------------------------------------------

    extrude_stage = next(stage for stage in plan.stages if stage.spec.name == "extrude")

    extrude_manifest_product = next(
        product for product in extrude_stage.products if product.spec.name == "manifest"
    )

    package_stage = next(stage for stage in plan.stages if stage.spec.name == "package")

    artifact_product = next(
        product for product in package_stage.products if product.spec.name == "artifact"
    )

    extrude_manifest = extrude_manifest_product.path
    output = artifact_product.path

    # -----------------------------------------------------
    # Verify Base extrusion product
    # -----------------------------------------------------

    assert extrude_manifest.is_file()

    extrusion_data = json.loads(
        extrude_manifest.read_text(
            encoding="utf-8",
        )
    )

    products = extrusion_data["products"]

    assert isinstance(
        products,
        list,
    )

    base_product = next(product for product in products if product["path"] == "base.stl")

    assert base_product["printer_color"] == {
        "name": "test-black",
        "rgb": {
            "red": 0,
            "green": 0,
            "blue": 0,
        },
    }

    base_stl = extrude_manifest.parent / base_product["path"]

    assert base_stl.is_file()
    assert base_stl.stat().st_size > 0

    # -----------------------------------------------------
    # Verify complete packaged 3MF
    # -----------------------------------------------------

    assert output.is_file()
    assert output.stat().st_size > 0

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
            )
        )

    # -----------------------------------------------------
    # Verify independently printable Base identity
    # -----------------------------------------------------

    objects = model.findall(
        f".//{{{CORE_NS}}}object",
    )

    materials = model.findall(
        f".//{{{CORE_NS}}}basematerials",
    )

    objects_by_name = {object_.get("name"): object_ for object_ in objects}

    assert "nydeli-base" in objects_by_name

    base_object = objects_by_name["nydeli-base"]

    materials_by_id = {material.get("id"): material for material in materials}

    base_material = materials_by_id[base_object.get("pid")]

    color = base_material.find(
        f"{{{CORE_NS}}}base",
    )

    assert color is not None

    assert color.get("name") == "test-black"
    assert color.get("displaycolor") == "#000000"

    assert base_object.get("pindex") == "0"


@pytest.mark.slow
def test_png_artwork_with_base_and_loop_builds_complete_3mf(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """
    Base and Loop compose through the ordinary standalone Artwork pipeline.

    An ordinary Artwork Realization may enable both Features through parameter
    overrides. The completed 3MF preserves Artwork, Base, and Loop as
    independently printable physical components with their resolved semantic
    physical color identities.
    """

    # -----------------------------------------------------
    # Arrange temporary project
    # -----------------------------------------------------

    repository_root = Path(__file__).resolve().parents[2]

    fixture_source = repository_root / "tests" / "assets" / "nydeli-clean.png"

    assert fixture_source.is_file()

    project_root = tmp_path

    source = project_root / "nydeli-clean.png"

    shutil.copy2(
        fixture_source,
        source,
    )

    monkeypatch.chdir(
        project_root,
    )

    runner = CliRunner()

    # -----------------------------------------------------
    # Configure through the public CLI
    # -----------------------------------------------------

    config_result = runner.invoke(
        cli,
        [
            "create",
            "nydeli",
        ],
        input="1\n",
    )

    assert config_result.exit_code == 0, (
        f"Artifact configuration failed:\n{config_result.output}\n{config_result.exception!r}"
    )

    # -----------------------------------------------------
    # Enable Base and Loop on ordinary artwork_default
    # -----------------------------------------------------

    artifact_config = project_root / "artifacts" / "nydeli" / "artifact.toml"

    assert artifact_config.is_file()

    with artifact_config.open(
        "a",
        encoding="utf-8",
    ) as stream:
        stream.write(
            """
[realizations.artwork_default]
artwork_base_raise = 2.0
artwork_base_color = "test-black"
loop_inner_diameter = 6.0
loop_width = 2.0
loop_position = 0
loop_raise = 3.0
"""
        )

    # -----------------------------------------------------
    # Plan customized ordinary Artwork Realization
    # -----------------------------------------------------

    plans = create_build_plans(
        "nydeli",
        realization="artwork_default",
        project_root=project_root,
    )

    assert len(plans) == 1

    plan = plans[0]

    assert plan.artifact_id == "nydeli"
    assert plan.model_name == "artwork"
    assert plan.realization_name == "artwork_default"

    assert plan.resolver("artwork_base_raise") == 2.0
    assert plan.resolver("artwork_base_color") == "test-black"
    assert plan.resolver("loop_inner_diameter") == 6.0
    assert plan.resolver("loop_width") == 2.0
    assert plan.resolver("loop_position") == 0
    assert plan.resolver("loop_raise") == 3.0

    # -----------------------------------------------------
    # Build through the ordinary public CLI
    # -----------------------------------------------------

    build_result = runner.invoke(
        cli,
        [
            "build",
            "nydeli",
            "--variant",
            "artwork.default",
        ],
    )

    assert build_result.exit_code == 0, (
        f"Artifact build failed:\n{build_result.output}\n{build_result.exception!r}"
    )

    # -----------------------------------------------------
    # Locate extrusion and package products
    # -----------------------------------------------------

    extrude_stage = next(stage for stage in plan.stages if stage.spec.name == "extrude")

    extrude_manifest_product = next(
        product for product in extrude_stage.products if product.spec.name == "manifest"
    )

    package_stage = next(stage for stage in plan.stages if stage.spec.name == "package")

    artifact_product = next(
        product for product in package_stage.products if product.spec.name == "artifact"
    )

    extrude_manifest = extrude_manifest_product.path
    output = artifact_product.path

    assert extrude_manifest.is_file()

    extrusion_data = json.loads(
        extrude_manifest.read_text(
            encoding="utf-8",
        )
    )

    products = extrusion_data["products"]

    assert isinstance(
        products,
        list,
    )

    # -----------------------------------------------------
    # Verify composed physical component contract
    # -----------------------------------------------------

    products_by_path = {product["path"]: product for product in products}

    assert "base.stl" in products_by_path
    assert "loop.stl" in products_by_path

    artwork_products = [
        product
        for product in products
        if product["path"]
        not in {
            "base.stl",
            "loop.stl",
        }
    ]

    assert artwork_products

    base_product = products_by_path["base.stl"]
    loop_product = products_by_path["loop.stl"]

    assert base_product["printer_color"] == {
        "name": "test-black",
        "rgb": {
            "red": 0,
            "green": 0,
            "blue": 0,
        },
    }

    for product in (
        base_product,
        loop_product,
    ):
        printer_color = product["printer_color"]

        assert isinstance(
            printer_color["name"],
            str,
        )

        assert printer_color["name"]

        rgb = printer_color["rgb"]

        assert isinstance(
            rgb["red"],
            int,
        )
        assert isinstance(
            rgb["green"],
            int,
        )
        assert isinstance(
            rgb["blue"],
            int,
        )

        stl = extrude_manifest.parent / product["path"]

        assert stl.is_file()
        assert stl.stat().st_size > 0

    # -----------------------------------------------------
    # Verify complete packaged 3MF
    # -----------------------------------------------------

    assert output.is_file()
    assert output.stat().st_size > 0

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
            )
        )

    # -----------------------------------------------------
    # Verify all extrusion components survive packaging
    # -----------------------------------------------------

    objects = model.findall(
        f".//{{{CORE_NS}}}object",
    )

    materials = model.findall(
        f".//{{{CORE_NS}}}basematerials",
    )

    objects_by_name = {object_.get("name"): object_ for object_ in objects}

    expected_names = {f"nydeli-{Path(product['path']).stem}" for product in products}

    assert set(objects_by_name) == expected_names

    materials_by_id = {material.get("id"): material for material in materials}

    # -----------------------------------------------------
    # Verify semantic physical identities survive packaging
    # -----------------------------------------------------

    for product in products:
        printer_color = product["printer_color"]

        semantic_name = printer_color["name"]
        rgb = printer_color["rgb"]

        component_name = f"nydeli-{Path(product['path']).stem}"

        object_ = objects_by_name[component_name]

        material = materials_by_id[object_.get("pid")]

        color = material.find(
            f"{{{CORE_NS}}}base",
        )

        assert color is not None

        assert color.get("name") == semantic_name

        assert color.get("displaycolor") == (
            f"#{rgb['red']:02X}{rgb['green']:02X}{rgb['blue']:02X}"
        )

        assert object_.get("pindex") == "0"


@pytest.mark.slow
def test_png_artwork_with_hole_builds_complete_3mf(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """
    Standalone Artwork with Base, Outer Ridge, and Hole builds end to end.

    Hole is configured through ordinary Artwork Realization parameters and
    remains subtractive geometry rather than an independently printable
    component. The final 3MF preserves the printable Artwork, Base, and
    Outer Ridge components and their semantic printer-color identities.
    """

    # -----------------------------------------------------
    # Arrange temporary project
    # -----------------------------------------------------

    repository_root = Path(__file__).resolve().parents[2]

    fixture_source = repository_root / "tests" / "assets" / "nydeli-clean.png"

    assert fixture_source.is_file(), f"Acceptance artwork does not exist: {fixture_source}"

    project_root = tmp_path

    source = project_root / "nydeli-clean.png"

    shutil.copy2(
        fixture_source,
        source,
    )

    monkeypatch.chdir(
        project_root,
    )

    runner = CliRunner()

    # -----------------------------------------------------
    # Configure through the public CLI
    # -----------------------------------------------------

    config_result = runner.invoke(
        cli,
        [
            "create",
            "nydeli",
        ],
        input="1\n",
    )

    assert config_result.exit_code == 0, (
        f"Artifact configuration failed:\n{config_result.output}\n{config_result.exception!r}"
    )

    # -----------------------------------------------------
    # Enable Base, Outer Ridge, and Hole
    # -----------------------------------------------------

    artifact_config = project_root / "artifacts" / "nydeli" / "artifact.toml"

    assert artifact_config.is_file()

    with artifact_config.open(
        "a",
        encoding="utf-8",
    ) as stream:
        stream.write(
            """
[realizations.artwork_default]
artwork_base_raise = 2.0
artwork_base_color = "test-black"

artwork_outer_ridge_width = 2.0
artwork_outer_ridge_raise = 1.0
artwork_outer_ridge_color = "test-white"

artwork_hole_diameter = 6.0
artwork_hole_position = 0
artwork_hole_edge_distance = 1.0
"""
        )

    # -----------------------------------------------------
    # Plan customized ordinary Artwork Realization
    # -----------------------------------------------------

    plans = create_build_plans(
        "nydeli",
        realization="artwork_default",
        project_root=project_root,
    )

    assert len(plans) == 1

    plan = plans[0]

    assert plan.artifact_id == "nydeli"
    assert plan.model_name == "artwork"
    assert plan.realization_name == "artwork_default"

    assert plan.resolver("artwork_base_raise") == 2.0
    assert plan.resolver("artwork_outer_ridge_width") == 2.0

    assert plan.resolver("artwork_hole_diameter") == 6.0
    assert plan.resolver("artwork_hole_position") == 0
    assert plan.resolver("artwork_hole_edge_distance") == 1.0

    # -----------------------------------------------------
    # Build through public CLI
    # -----------------------------------------------------

    build_result = runner.invoke(
        cli,
        [
            "build",
            "nydeli",
            "--variant",
            "artwork.default",
        ],
    )

    assert build_result.exit_code == 0, (
        f"Artifact build failed:\n{build_result.output}\n{build_result.exception!r}"
    )

    # -----------------------------------------------------
    # Locate extrusion and package products
    # -----------------------------------------------------

    extrude_stage = next(stage for stage in plan.stages if stage.spec.name == "extrude")

    extrude_manifest_product = next(
        product for product in extrude_stage.products if product.spec.name == "manifest"
    )

    package_stage = next(stage for stage in plan.stages if stage.spec.name == "package")

    artifact_product = next(
        product for product in package_stage.products if product.spec.name == "artifact"
    )

    extrude_manifest = extrude_manifest_product.path
    output = artifact_product.path

    # -----------------------------------------------------
    # Verify extrusion component contract
    # -----------------------------------------------------

    assert extrude_manifest.is_file()

    extrusion_data = json.loads(
        extrude_manifest.read_text(
            encoding="utf-8",
        )
    )

    products = extrusion_data["products"]

    assert isinstance(
        products,
        list,
    )

    assert products

    product_paths = {product["path"] for product in products}

    assert "base.stl" in product_paths
    assert "outer-ridge.stl" in product_paths

    # Hole is subtractive geometry, never a product.
    assert "hole.stl" not in product_paths

    assert all("hole" not in Path(product["path"]).stem for product in products)

    # -----------------------------------------------------
    # Verify physical STL products exist
    # -----------------------------------------------------

    for product in products:
        stl = extrude_manifest.parent / product["path"]

        assert stl.is_file(), f"Expected extrusion product does not exist: {stl}"

        assert stl.stat().st_size > 0

    # -----------------------------------------------------
    # Verify final 3MF
    # -----------------------------------------------------

    assert output.is_relative_to(
        project_root,
    )

    assert output.is_file(), f"Build did not produce the expected 3MF: {output}"

    assert output.stat().st_size > 0

    assert zipfile.is_zipfile(
        output,
    )

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
            )
        )

    # -----------------------------------------------------
    # Verify packaged physical components
    # -----------------------------------------------------

    objects = model.findall(
        f".//{{{CORE_NS}}}object",
    )

    materials = model.findall(
        f".//{{{CORE_NS}}}basematerials",
    )

    objects_by_name = {object_.get("name"): object_ for object_ in objects}

    expected_names = {f"nydeli-{Path(product['path']).stem}" for product in products}

    assert set(objects_by_name) == expected_names

    assert "nydeli-base" in objects_by_name
    assert "nydeli-outer-ridge" in objects_by_name
    assert "nydeli-hole" not in objects_by_name

    assert len(materials) == len(products)

    materials_by_id = {material.get("id"): material for material in materials}

    # -----------------------------------------------------
    # Verify semantic printer colors survive packaging
    # -----------------------------------------------------

    for product in products:
        printer_color = product["printer_color"]

        semantic_name = printer_color["name"]
        rgb = printer_color["rgb"]

        component_name = f"nydeli-{Path(product['path']).stem}"

        object_ = objects_by_name[component_name]

        material = materials_by_id[object_.get("pid")]

        color = material.find(
            f"{{{CORE_NS}}}base",
        )

        assert color is not None

        assert color.get("name") == semantic_name

        assert color.get("displaycolor") == (
            f"#{rgb['red']:02X}{rgb['green']:02X}{rgb['blue']:02X}"
        )

        assert object_.get("pindex") == "0"

    # -----------------------------------------------------
    # Verify configured Feature colors remain authoritative
    # -----------------------------------------------------

    base_product = next(product for product in products if product["path"] == "base.stl")

    outer_ridge_product = next(
        product for product in products if product["path"] == "outer-ridge.stl"
    )

    assert base_product["printer_color"]["name"] == "test-black"

    assert outer_ridge_product["printer_color"]["name"] == "test-white"


@pytest.mark.slow
def test_nydeli_outer_ridge_isolates_hole_rendering_failure(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """
    Isolate Outer Ridge rendering against the real nydeli envelope.

    Establish whether the real registered Artwork envelope can render:

    1. Outer Ridge without Hole.
    2. Outer Ridge with a Hole wholly inward of Ridge material.
    3. Outer Ridge with a Hole intersecting Ridge material.

    This is diagnostic characterization of the OpenSCAD boundary using
    real vectorized Artwork geometry.
    """

    repository_root = Path(__file__).resolve().parents[2]

    fixture_source = repository_root / "tests" / "assets" / "nydeli-clean.png"

    assert fixture_source.is_file()

    project_root = tmp_path

    shutil.copy2(
        fixture_source,
        project_root / "nydeli-clean.png",
    )

    monkeypatch.chdir(
        project_root,
    )

    runner = CliRunner()

    # -----------------------------------------------------
    # Create ordinary Artwork artifact
    # -----------------------------------------------------

    config_result = runner.invoke(
        cli,
        [
            "create",
            "nydeli",
        ],
        input="1\n",
    )

    assert config_result.exit_code == 0, (
        f"Artifact configuration failed:\n{config_result.output}\n{config_result.exception!r}"
    )

    # -----------------------------------------------------
    # Build only far enough to obtain the real vector envelope
    #
    # Disable Outer Ridge and Hole so extrusion itself does
    # not encounter the composition under investigation.
    # -----------------------------------------------------

    artifact_config = project_root / "artifacts" / "nydeli" / "artifact.toml"

    with artifact_config.open(
        "a",
        encoding="utf-8",
    ) as stream:
        stream.write(
            """
[realizations.artwork_default]
artwork_outer_ridge_width = 0.0
artwork_hole_diameter = 0.0
"""
        )

    build_result = runner.invoke(
        cli,
        [
            "build",
            "nydeli",
            "--variant",
            "artwork.default",
        ],
    )

    assert build_result.exit_code == 0, (
        f"Baseline Artwork build failed:\n{build_result.output}\n{build_result.exception!r}"
    )

    # -----------------------------------------------------
    # Recover the actual registered vector envelope
    # -----------------------------------------------------

    plans = create_build_plans(
        "nydeli",
        realization="artwork_default",
        project_root=project_root,
    )

    assert len(plans) == 1

    plan = plans[0]

    vector_stage = next(stage for stage in plan.stages if stage.spec.name == "vector")

    vector_manifest_product = next(
        product for product in vector_stage.products if product.spec.name == "manifest"
    )

    vector_manifest_path = vector_manifest_product.path

    assert vector_manifest_path.is_file()

    vector_manifest = json.loads(
        vector_manifest_path.read_text(
            encoding="utf-8",
        )
    )

    envelope = vector_manifest_path.parent / vector_manifest["envelope"]

    assert envelope.is_file()

    registered_extent = vector_manifest["registered_extent"]

    envelope_bounds = extrude._envelope_bounds(
        envelope,
    )

    # -----------------------------------------------------
    # Use the same physical dimensionalization as the
    # failing Phase 7 acceptance test.
    # -----------------------------------------------------

    artwork_size = 100.0
    outer_ridge_width = 2.0
    outer_ridge_raise = 1.0

    physical_bounds = extrude._physical_envelope_bounds(
        envelope_bounds,
        artwork_size=artwork_size,
    )

    # -----------------------------------------------------
    # Case 1:
    # Real nydeli Outer Ridge without Hole.
    # -----------------------------------------------------

    ridge_only_source = extrude._build_outer_ridge_scad(
        envelope,
        registered_extent=registered_extent,
        envelope_bounds=envelope_bounds,
        artwork_size=artwork_size,
        outer_ridge_width=outer_ridge_width,
        outer_ridge_raise=outer_ridge_raise,
    )

    ridge_only_output = tmp_path / "outer-ridge-without-hole.stl"

    extrude.render_stl_source(
        ridge_only_source,
        ridge_only_output,
    )

    assert ridge_only_output.is_file()
    assert ridge_only_output.stat().st_size > 0

    # -----------------------------------------------------
    # Case 2:
    # Hole lies wholly inward of the 2 mm Ridge.
    #
    # radius = 3 mm
    # edge distance = 4 mm
    #
    # Therefore its nearest edge is 4 mm inward from the
    # outer boundary and does not intersect Ridge material.
    # -----------------------------------------------------

    inward_hole = create_hole_geometry(
        envelope_bounds=physical_bounds,
        diameter=6.0,
        edge_distance=4.0,
        position=0,
    )

    inward_source = extrude._build_outer_ridge_scad(
        envelope,
        registered_extent=registered_extent,
        envelope_bounds=envelope_bounds,
        artwork_size=artwork_size,
        outer_ridge_width=outer_ridge_width,
        outer_ridge_raise=outer_ridge_raise,
        hole_geometry=inward_hole,
    )

    inward_output = tmp_path / "outer-ridge-with-inward-hole.stl"

    extrude.render_stl_source(
        inward_source,
        inward_output,
    )

    assert inward_output.is_file()
    assert inward_output.stat().st_size > 0

    # -----------------------------------------------------
    # Case 3:
    # Match the failing acceptance configuration.
    #
    # radius = 3 mm
    # edge distance = 1 mm
    #
    # The nearest Hole edge is therefore inside the 2 mm
    # Ridge region and the Hole intersects Ridge material.
    # -----------------------------------------------------

    intersecting_hole = create_hole_geometry(
        envelope_bounds=physical_bounds,
        diameter=6.0,
        edge_distance=1.0,
        position=0,
    )

    intersecting_source = extrude._build_outer_ridge_scad(
        envelope,
        registered_extent=registered_extent,
        envelope_bounds=envelope_bounds,
        artwork_size=artwork_size,
        outer_ridge_width=outer_ridge_width,
        outer_ridge_raise=outer_ridge_raise,
        hole_geometry=intersecting_hole,
    )

    intersecting_output = tmp_path / "outer-ridge-with-intersecting-hole.stl"

    extrude.render_stl_source(
        intersecting_source,
        intersecting_output,
    )

    assert intersecting_output.is_file()
    assert intersecting_output.stat().st_size > 0
