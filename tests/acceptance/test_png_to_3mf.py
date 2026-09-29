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
from lowkey_artifact_builder.config import materialize_artifact
from lowkey_artifact_builder.engine import (
    create_build_plans,
)
from lowkey_artifact_builder.formats.threemf import CORE_NS, component_name
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

    Registered Artwork preserves logical Artifact-color identity through
    extrusion. Physical printer-color assignment occurs only during Package.

    Extrusion products use stage-local color-N filenames. Package exposes
    registered Artwork as independently printable artwork-N components with
    resolved physical printer colors.
    """

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
            "--artifact-id=nydeli",
            "--source=nydeli-clean.png",
        ],
    )

    assert config_result.exit_code == 0, (
        f"Artifact configuration failed:\n{config_result.output}\n{config_result.exception!r}"
    )

    # -----------------------------------------------------
    # Materialize Artifact workspace
    # -----------------------------------------------------

    materialize_artifact(
        "nydeli",
        project_root=project_root,
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
    # Build through public CLI
    # -----------------------------------------------------

    build_result = runner.invoke(
        cli,
        [
            "build",
            "nydeli",
            "--realization",
            "artwork_default",
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
    # Verify logical extrusion contract
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

    for product in products:
        assert "printer_color" not in product

        artifact_color = product.get(
            "artifact_color",
        )

        if artifact_color is not None:
            assert isinstance(
                artifact_color,
                dict,
            )

            assert isinstance(
                artifact_color["index"],
                int,
            )

            rgb = artifact_color["rgb"]

            assert isinstance(
                rgb,
                dict,
            )

            assert set(rgb) == {
                "red",
                "green",
                "blue",
            }

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
            )
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

    #
    # Every extruded physical component must survive
    # packaging as exactly one independently printable
    # 3MF object.
    #
    # Registered Artwork uses stage-local color-N filenames
    # during Extrude and canonical artwork-N semantic names
    # after Package.
    #
    assert len(objects_by_name) == len(products)

    packaged_names = {name for name in objects_by_name if name is not None}

    for product in products:
        artifact_color = product.get(
            "artifact_color",
        )

        if isinstance(
            artifact_color,
            dict,
        ):
            component_semantic_name = f"artwork-{artifact_color['index']}"
        else:
            component_semantic_name = Path(
                product["path"],
            ).stem

        matching_names = [
            name
            for name in packaged_names
            if name.startswith(
                f"{component_semantic_name} - ",
            )
        ]

        assert len(matching_names) == 1, (
            "Expected exactly one packaged object for "
            f"extruded component {product['path']!r} as "
            f"{component_semantic_name!r}; "
            f"found {matching_names!r} in "
            f"{sorted(packaged_names)!r}"
        )

    # -----------------------------------------------------
    # Verify physical printer-color assignment occurs
    # in the packaged 3MF
    # -----------------------------------------------------

    materials_by_id = {material.get("id"): material for material in materials}

    assert materials_by_id

    for object_ in objects:
        pid = object_.get("pid")

        assert pid is not None
        assert pid in materials_by_id

        material = materials_by_id[pid]

        color = material.find(
            f"{{{CORE_NS}}}base",
        )

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


@pytest.mark.slow
def test_png_artwork_with_loop_builds_complete_3mf(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """
    Standalone Artwork with a participating Loop builds through the normal
    pipeline into a complete 3MF.

    Extrude preserves the Loop's logical attachment to an Artifact-color layer
    without assigning a physical printer color. Package resolves the physical
    printer assignment for that Artifact-color layer and applies the same
    assignment to the Loop when no explicit loop_color override exists.

    Registered Artwork is packaged using canonical artwork-N component
    identities rather than stage-local color-N extrusion filenames.
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
            "--artifact-id=nydeli",
            "--source=nydeli-clean.png",
        ],
    )

    assert config_result.exit_code == 0, (
        f"Artifact configuration failed:\n{config_result.output}\n{config_result.exception!r}"
    )

    # -----------------------------------------------------
    # Materialize Artifact workspace from preserved original
    # -----------------------------------------------------

    materialize_artifact(
        "nydeli",
        project_root=project_root,
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
            "--realization",
            "artwork_default",
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
    # Verify Loop extrusion contract
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

    loop_product = next(product for product in products if product["path"] == "loop.stl")

    #
    # Extrude owns geometry and logical attachment,
    # not physical printer assignment.
    #
    assert "printer_color" not in loop_product

    loop_artifact_color_index = loop_product.get(
        "artifact_color_index",
    )

    assert isinstance(
        loop_artifact_color_index,
        int,
    )

    assert loop_artifact_color_index > 0

    attached_artwork_product = next(
        product
        for product in products
        if (
            isinstance(
                product.get("artifact_color"),
                dict,
            )
            and product["artifact_color"].get("index") == loop_artifact_color_index
        )
    )

    assert "printer_color" not in attached_artwork_product

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
            )
        )

    # -----------------------------------------------------
    # Verify Loop survives as independently printable
    # component and inherits its Artifact-layer color
    # -----------------------------------------------------

    objects = model.findall(
        f".//{{{CORE_NS}}}object",
    )

    materials = model.findall(
        f".//{{{CORE_NS}}}basematerials",
    )

    objects_by_name = {object_.get("name"): object_ for object_ in objects}

    materials_by_id = {material.get("id"): material for material in materials}

    loop_matches = [
        object_
        for name, object_ in objects_by_name.items()
        if (name is not None and name.startswith("loop - "))
    ]

    assert len(loop_matches) == 1

    loop_object = loop_matches[0]

    attached_artifact_color = attached_artwork_product.get(
        "artifact_color",
    )

    assert isinstance(
        attached_artifact_color,
        dict,
    )

    attached_semantic_name = f"artwork-{attached_artifact_color['index']}"

    attached_matches = [
        object_
        for name, object_ in objects_by_name.items()
        if (
            name is not None
            and name.startswith(
                f"{attached_semantic_name} - ",
            )
        )
    ]

    assert len(attached_matches) == 1

    attached_object = attached_matches[0]

    loop_pid = loop_object.get("pid")
    attached_pid = attached_object.get("pid")

    assert loop_pid is not None
    assert attached_pid is not None

    assert loop_pid in materials_by_id
    assert attached_pid in materials_by_id

    loop_material = materials_by_id[loop_pid]
    attached_material = materials_by_id[attached_pid]

    loop_color = loop_material.find(
        f"{{{CORE_NS}}}base",
    )

    attached_color = attached_material.find(
        f"{{{CORE_NS}}}base",
    )

    assert loop_color is not None
    assert attached_color is not None

    #
    # No loop_color override exists. Package must therefore
    # apply the same physical printer color to the Loop as
    # to the Artifact-color layer referenced by
    # artifact_color_index.
    #
    assert loop_color.get("name") == attached_color.get("name")

    assert loop_color.get("displaycolor") == attached_color.get("displaycolor")

    assert loop_object.get("pindex") == "0"
    assert attached_object.get("pindex") == "0"


@pytest.mark.slow
def test_png_artwork_with_base_builds_complete_3mf(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """
    An ordinary Artwork Realization may enable Base through parameter
    overrides and build through the normal pipeline.

    Extrude preserves Base's logical attachment to an Artifact-color layer
    without assigning a physical printer color. Package applies the explicit
    artwork_base_color override and emits Base as an independently printable
    physical component.
    """

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
    # Configure through public CLI
    # -----------------------------------------------------

    config_result = runner.invoke(
        cli,
        [
            "create",
            "--artifact-id=nydeli",
            "--source=nydeli-clean.png",
        ],
    )

    assert config_result.exit_code == 0, (
        f"Artifact configuration failed:\n{config_result.output}\n{config_result.exception!r}"
    )

    materialize_artifact(
        "nydeli",
        project_root=project_root,
    )

    # -----------------------------------------------------
    # Enable Base with explicit physical override
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
    # Plan customized realization
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
    # Build through public CLI
    # -----------------------------------------------------

    build_result = runner.invoke(
        cli,
        [
            "build",
            "nydeli",
            "--realization",
            "artwork_default",
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
    # Verify Base extrusion contract
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

    #
    # Extrude owns geometry and logical attachment,
    # not physical printer assignment.
    #
    assert "printer_color" not in base_product

    artifact_color_index = base_product.get(
        "artifact_color_index",
    )

    assert isinstance(
        artifact_color_index,
        int,
    )

    assert artifact_color_index > 0

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
    # Verify explicit Base physical override is applied
    # by Package
    # -----------------------------------------------------

    objects = model.findall(
        f".//{{{CORE_NS}}}object",
    )

    materials = model.findall(
        f".//{{{CORE_NS}}}basematerials",
    )

    objects_by_name = {object_.get("name"): object_ for object_ in objects}

    base_name = component_name(
        "nydeli",
        "base",
        "test-black",
    )

    assert base_name in objects_by_name

    base_object = objects_by_name[base_name]

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

    Extrude preserves logical Artifact-color attachment for both Features
    without assigning physical printer colors.

    Package applies the explicit artwork_base_color override to Base. Loop has
    no explicit loop_color override, so Package gives it the same physical
    printer color as the Artifact-color layer referenced by its
    artifact_color_index.

    Registered Artwork extrusion products retain stage-local color-N
    filenames while Package exposes them as canonical artwork-N components.
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
            "--artifact-id=nydeli",
            "--source=nydeli-clean.png",
        ],
    )

    assert config_result.exit_code == 0, (
        f"Artifact configuration failed:\n{config_result.output}\n{config_result.exception!r}"
    )

    # -----------------------------------------------------
    # Materialize Artifact workspace from preserved original
    # -----------------------------------------------------

    materialize_artifact(
        "nydeli",
        project_root=project_root,
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
            "--realization",
            "artwork_default",
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
    # Verify logical extrusion contract
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

    #
    # Extrude owns geometry and logical attachment,
    # not physical printer assignment.
    #
    assert "printer_color" not in base_product
    assert "printer_color" not in loop_product

    base_artifact_color_index = base_product.get(
        "artifact_color_index",
    )

    loop_artifact_color_index = loop_product.get(
        "artifact_color_index",
    )

    assert isinstance(
        base_artifact_color_index,
        int,
    )

    assert base_artifact_color_index > 0

    assert isinstance(
        loop_artifact_color_index,
        int,
    )

    assert loop_artifact_color_index > 0

    loop_attached_artwork_product = next(
        product
        for product in artwork_products
        if (
            isinstance(
                product.get("artifact_color"),
                dict,
            )
            and product["artifact_color"].get("index") == loop_artifact_color_index
        )
    )

    for product in (
        base_product,
        loop_product,
    ):
        stl = extrude_manifest.parent / product["path"]

        assert stl.is_file()
        assert stl.stat().st_size > 0

    # -----------------------------------------------------
    # Verify complete packaged 3MF
    # -----------------------------------------------------

    assert output.is_relative_to(
        project_root,
    )

    assert output.is_file()
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
    # Verify all extrusion components survive packaging
    # -----------------------------------------------------

    objects = model.findall(
        f".//{{{CORE_NS}}}object",
    )

    materials = model.findall(
        f".//{{{CORE_NS}}}basematerials",
    )

    objects_by_name = {object_.get("name"): object_ for object_ in objects}

    assert len(objects_by_name) == len(products)

    packaged_names = {name for name in objects_by_name if name is not None}

    for product in products:
        artifact_color = product.get(
            "artifact_color",
        )

        if isinstance(
            artifact_color,
            dict,
        ):
            component_semantic_name = f"artwork-{artifact_color['index']}"
        else:
            component_semantic_name = Path(
                product["path"],
            ).stem

        matching_names = [
            name
            for name in packaged_names
            if name.startswith(
                f"{component_semantic_name} - ",
            )
        ]

        assert len(matching_names) == 1, (
            "Expected exactly one packaged object for "
            f"extruded component {product['path']!r} as "
            f"{component_semantic_name!r}; "
            f"found {matching_names!r} in "
            f"{sorted(packaged_names)!r}"
        )

    materials_by_id = {material.get("id"): material for material in materials}

    # -----------------------------------------------------
    # Verify explicit Base physical override is applied
    # only by Package
    # -----------------------------------------------------

    base_name = component_name(
        "nydeli",
        "base",
        "test-black",
    )

    assert base_name in objects_by_name

    base_object = objects_by_name[base_name]

    base_pid = base_object.get("pid")

    assert base_pid is not None
    assert base_pid in materials_by_id

    base_material = materials_by_id[base_pid]

    base_color = base_material.find(
        f"{{{CORE_NS}}}base",
    )

    assert base_color is not None
    assert base_color.get("name") == "test-black"
    assert base_color.get("displaycolor") == "#000000"
    assert base_object.get("pindex") == "0"

    # -----------------------------------------------------
    # Verify Loop inherits the packaged physical color of
    # its attached Artifact-color layer
    # -----------------------------------------------------

    loop_matches = [
        object_
        for name, object_ in objects_by_name.items()
        if (name is not None and name.startswith("loop - "))
    ]

    assert len(loop_matches) == 1

    loop_object = loop_matches[0]

    attached_artifact_color = loop_attached_artwork_product.get(
        "artifact_color",
    )

    assert isinstance(
        attached_artifact_color,
        dict,
    )

    attached_semantic_name = f"artwork-{attached_artifact_color['index']}"

    attached_matches = [
        object_
        for name, object_ in objects_by_name.items()
        if (
            name is not None
            and name.startswith(
                f"{attached_semantic_name} - ",
            )
        )
    ]

    assert len(attached_matches) == 1

    attached_object = attached_matches[0]

    loop_pid = loop_object.get("pid")
    attached_pid = attached_object.get("pid")

    assert loop_pid is not None
    assert attached_pid is not None

    assert loop_pid in materials_by_id
    assert attached_pid in materials_by_id

    loop_material = materials_by_id[loop_pid]
    attached_material = materials_by_id[attached_pid]

    loop_color = loop_material.find(
        f"{{{CORE_NS}}}base",
    )

    attached_color = attached_material.find(
        f"{{{CORE_NS}}}base",
    )

    assert loop_color is not None
    assert attached_color is not None

    #
    # No loop_color override exists. Package must therefore
    # apply the physical printer assignment of the referenced
    # Artifact-color layer.
    #
    assert loop_color.get("name") == attached_color.get("name")

    assert loop_color.get("displaycolor") == attached_color.get("displaycolor")

    assert loop_object.get("pindex") == "0"
    assert attached_object.get("pindex") == "0"


@pytest.mark.slow
def test_png_artwork_with_hole_builds_complete_3mf(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """
    Standalone Artwork with Base, Outer Ridge, and Hole builds end to end.

    Hole is configured through ordinary Artwork Realization parameters and
    remains subtractive geometry rather than an independently printable
    component.

    Extrude preserves logical Artifact-color attachment for printable
    components without assigning physical printer colors. Package resolves
    physical colors, including explicit Base and Outer Ridge overrides.

    Registered Artwork extrusion products retain stage-local color-N
    filenames while Package exposes them as canonical artwork-N components.
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
    # Configure through public CLI
    # -----------------------------------------------------

    config_result = runner.invoke(
        cli,
        [
            "create",
            "--artifact-id=nydeli",
            "--source=nydeli-clean.png",
        ],
    )

    assert config_result.exit_code == 0, (
        f"Artifact configuration failed:\n{config_result.output}\n{config_result.exception!r}"
    )

    materialize_artifact(
        "nydeli",
        project_root=project_root,
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
    # Plan customized realization
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

    assert plan.resolver("artwork_outer_ridge_width") == 2.0
    assert plan.resolver("artwork_outer_ridge_raise") == 1.0
    assert plan.resolver("artwork_outer_ridge_color") == "test-white"

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
            "--realization",
            "artwork_default",
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
    # Verify logical extrusion contract
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

    #
    # Hole is subtractive geometry, never an independently
    # printable product.
    #
    assert "hole.stl" not in product_paths

    assert all(
        "hole"
        not in Path(
            product["path"],
        ).stem
        for product in products
    )

    #
    # Extrude owns geometry and logical color relationships.
    # It must not contain physical printer assignments.
    #
    assert all("printer_color" not in product for product in products)

    base_product = next(product for product in products if product["path"] == "base.stl")

    ridge_product = next(product for product in products if product["path"] == "outer-ridge.stl")

    assert isinstance(
        base_product.get("artifact_color_index"),
        int,
    )

    assert isinstance(
        ridge_product.get("artifact_color_index"),
        int,
    )

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

    #
    # Every extruded component survives Package exactly once.
    #
    assert len(objects_by_name) == len(products)

    packaged_names = {name for name in objects_by_name if name is not None}

    for product in products:
        artifact_color = product.get(
            "artifact_color",
        )

        if isinstance(
            artifact_color,
            dict,
        ):
            component_semantic_name = f"artwork-{artifact_color['index']}"
        else:
            component_semantic_name = Path(
                product["path"],
            ).stem

        matching_names = [
            name
            for name in packaged_names
            if name.startswith(
                f"{component_semantic_name} - ",
            )
        ]

        assert len(matching_names) == 1, (
            "Expected exactly one packaged object for "
            f"extruded component {product['path']!r} as "
            f"{component_semantic_name!r}; "
            f"found {matching_names!r} in "
            f"{sorted(packaged_names)!r}"
        )

    # -----------------------------------------------------
    # Verify explicit feature-color overrides are applied
    # only by Package
    # -----------------------------------------------------

    base_name = component_name(
        "nydeli",
        "base",
        "test-black",
    )

    ridge_name = component_name(
        "nydeli",
        "outer-ridge",
        "test-white",
    )

    assert base_name in objects_by_name
    assert ridge_name in objects_by_name

    materials_by_id = {material.get("id"): material for material in materials}

    base_object = objects_by_name[base_name]

    base_material = materials_by_id[base_object.get("pid")]

    base_color = base_material.find(
        f"{{{CORE_NS}}}base",
    )

    assert base_color is not None
    assert base_color.get("name") == "test-black"
    assert base_color.get("displaycolor") == "#000000"
    assert base_object.get("pindex") == "0"

    ridge_object = objects_by_name[ridge_name]

    ridge_material = materials_by_id[ridge_object.get("pid")]

    ridge_color = ridge_material.find(
        f"{{{CORE_NS}}}base",
    )

    assert ridge_color is not None
    assert ridge_color.get("name") == "test-white"
    assert ridge_color.get("displaycolor") == "#FFFFFF"
    assert ridge_object.get("pindex") == "0"

    #
    # Hole remains subtractive after Package as well.
    #
    assert all("hole" not in name for name in packaged_names)


@pytest.mark.slow
def test_png_artwork_with_hole_preserves_through_hole_in_packaged_geometry(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """
    The final packaged 3MF preserves the configured Artwork through-hole.

    The Hole is subtractive rather than an independently printable component.
    At the resolved Hole center, no packaged Artwork, Base, or Outer Ridge
    triangle may cross the vertical centerline of the Hole.
    """

    # -----------------------------------------------------
    # Arrange temporary project
    # -----------------------------------------------------

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
    # Configure through the public CLI
    # -----------------------------------------------------

    config_result = runner.invoke(
        cli,
        [
            "create",
            "--artifact-id=nydeli",
            "--source=nydeli-clean.png",
        ],
    )

    assert config_result.exit_code == 0, (
        f"Artifact configuration failed:\n{config_result.output}\n{config_result.exception!r}"
    )

    # -----------------------------------------------------
    # Materialize Artifact workspace from preserved original
    # -----------------------------------------------------

    materialize_artifact(
        "nydeli",
        project_root=project_root,
    )

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
    # Plan and build ordinary Artwork Realization
    # -----------------------------------------------------

    plans = create_build_plans(
        "nydeli",
        realization="artwork_default",
        project_root=project_root,
    )

    assert len(plans) == 1

    plan = plans[0]

    build_result = runner.invoke(
        cli,
        [
            "build",
            "nydeli",
            "--realization",
            "artwork_default",
        ],
    )

    assert build_result.exit_code == 0, (
        f"Artifact build failed:\n{build_result.output}\n{build_result.exception!r}"
    )

    # -----------------------------------------------------
    # Recover resolved physical Hole geometry
    # -----------------------------------------------------

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

    envelope_bounds = extrude._envelope_bounds(
        envelope,
    )

    physical_bounds = extrude._physical_envelope_bounds(
        envelope_bounds,
        artwork_size=plan.resolver("artwork_size"),
    )

    hole_geometry = create_hole_geometry(
        envelope_bounds=physical_bounds,
        diameter=plan.resolver("artwork_hole_diameter"),
        edge_distance=plan.resolver("artwork_hole_edge_distance"),
        position=plan.resolver("artwork_hole_position"),
    )

    hole_x = hole_geometry.center_x
    hole_y = hole_geometry.center_y

    # -----------------------------------------------------
    # Open the actual packaged 3MF
    # -----------------------------------------------------

    package_stage = next(stage for stage in plan.stages if stage.spec.name == "package")

    artifact_product = next(
        product for product in package_stage.products if product.spec.name == "artifact"
    )

    output = artifact_product.path

    assert output.is_file()
    assert zipfile.is_zipfile(output)

    with zipfile.ZipFile(output) as archive:
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
    # Test whether a triangle contains the Hole center in XY
    # -----------------------------------------------------

    def triangle_contains_xy(
        point_x: float,
        point_y: float,
        a: tuple[float, float],
        b: tuple[float, float],
        c: tuple[float, float],
    ) -> bool:
        """
        Return whether an XY point lies inside or on a nondegenerate triangle.

        Three-dimensional mesh triangles representing vertical walls may
        collapse to a line or point when projected into XY. Such projections
        have no planar area and therefore cannot cover the Hole centerline in
        XY.
        """

        def cross(
            p1: tuple[float, float],
            p2: tuple[float, float],
            p3: tuple[float, float],
        ) -> float:
            return (p2[0] - p1[0]) * (p3[1] - p1[1]) - (p2[1] - p1[1]) * (p3[0] - p1[0])

        epsilon = 1e-6

        # A 3-D triangle may project to a line or point in XY.
        # Such a projection has no planar area and cannot cover
        # the Hole centerline.
        area_twice = cross(
            a,
            b,
            c,
        )

        if abs(area_twice) <= epsilon:
            return False

        point = (
            point_x,
            point_y,
        )

        d1 = cross(
            a,
            b,
            point,
        )

        d2 = cross(
            b,
            c,
            point,
        )

        d3 = cross(
            c,
            a,
            point,
        )

        has_negative = d1 < -epsilon or d2 < -epsilon or d3 < -epsilon

        has_positive = d1 > epsilon or d2 > epsilon or d3 > epsilon

        return not (has_negative and has_positive)

    # -----------------------------------------------------
    # Verify the Hole centerline is empty in every packaged
    # physical component that intersects the Hole region.
    # -----------------------------------------------------

    objects = model.findall(
        f".//{{{CORE_NS}}}object",
    )

    assert objects

    inspected_objects = 0

    for object_ in objects:
        mesh = object_.find(
            f"{{{CORE_NS}}}mesh",
        )

        assert mesh is not None

        vertices_element = mesh.find(
            f"{{{CORE_NS}}}vertices",
        )

        triangles_element = mesh.find(
            f"{{{CORE_NS}}}triangles",
        )

        assert vertices_element is not None
        assert triangles_element is not None

        vertices: list[
            tuple[
                float,
                float,
                float,
            ]
        ] = []

        for vertex in vertices_element.findall(
            f"{{{CORE_NS}}}vertex",
        ):
            x = vertex.get("x")
            y = vertex.get("y")
            z = vertex.get("z")

            assert x is not None
            assert y is not None
            assert z is not None

            vertices.append(
                (
                    float(x),
                    float(y),
                    float(z),
                )
            )

        triangles = triangles_element.findall(
            f"{{{CORE_NS}}}triangle",
        )

        assert vertices
        assert triangles

        min_x = min(vertex[0] for vertex in vertices)
        max_x = max(vertex[0] for vertex in vertices)
        min_y = min(vertex[1] for vertex in vertices)
        max_y = max(vertex[1] for vertex in vertices)

        # Components that cannot reach the Hole center are
        # irrelevant to this through-hole assertion.
        if not (min_x <= hole_x <= max_x and min_y <= hole_y <= max_y):
            continue

        inspected_objects += 1

        for triangle in triangles:
            v1_index = triangle.get("v1")
            v2_index = triangle.get("v2")
            v3_index = triangle.get("v3")

            assert v1_index is not None
            assert v2_index is not None
            assert v3_index is not None

            v1 = vertices[int(v1_index)]
            v2 = vertices[int(v2_index)]
            v3 = vertices[int(v3_index)]

            assert not triangle_contains_xy(
                hole_x,
                hole_y,
                (v1[0], v1[1]),
                (v2[0], v2[1]),
                (v3[0], v3[1]),
            ), (
                "Packaged component contains material across "
                f"the Hole centerline: {object_.get('name')}"
            )

    assert inspected_objects > 0
