"""
Acceptance tests for Shape Model Variant behavior.

These tests exercise Variant semantics through normal artifact planning
and execution boundaries.
"""
# File: tests/acceptance/test_shape_variants.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

import shutil
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import pytest
from click.testing import CliRunner

from lowkey_artifact_builder.cli._main import cli
from lowkey_artifact_builder.config import write_artifact_config
from lowkey_artifact_builder.engine import (
    create_build_plans,
    execute_dependency_build,
)
from lowkey_artifact_builder.formats.threemf import CORE_NS


@pytest.mark.slow
def test_shape_ornament_variant_builds_complete_3mf(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """
    The shape.ornament Variant is applied through the public build path.

    Model defaults remain effective except where the sparse ornament
    Variant overrides them. The Variant's positive outer-ridge width
    enables ridge geometry that is present in the manufactured 3MF.
    """

    project_root = tmp_path

    monkeypatch.chdir(
        project_root,
    )

    runner = CliRunner()

    write_artifact_config(
        "ornament-shape",
        {
            "model": "shape",
        },
        project_root=project_root,
    )

    build_result = runner.invoke(
        cli,
        [
            "build",
            "ornament-shape",
            "--variant",
            "shape.ornament",
        ],
    )

    assert build_result.exit_code == 0, (
        f"Shape ornament build failed:\n{build_result.output}\n{build_result.exception!r}"
    )

    plans = create_build_plans(
        "ornament-shape",
        model_name="shape",
        variant_name="ornament",
        project_root=project_root,
    )

    assert len(plans) == 1

    plan = plans[0]

    assert plan.model_name == "shape"
    assert plan.resolver("variant") == "ornament"

    assert plan.resolver("shape_outer_ridge_width") == 2.0
    assert plan.resolver.source("shape_outer_ridge_width") == "variant 'ornament'"

    assert plan.resolver("shape_base_raise") == 2.0
    assert plan.resolver.source("shape_base_raise") == "model"

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

    object_names = {object_.get("name") for object_ in objects}

    assert "ornament-shape-base-white" in object_names
    assert "ornament-shape-ridge-white" in object_names


@pytest.mark.slow
def test_shape_ornament_variant_accepts_artifact_customization(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """
    Artifact customization overlays the selected shape.ornament Variant.

    The customization changes the resulting physical Shape without
    creating a new Variant identity.
    """

    project_root = tmp_path

    monkeypatch.chdir(
        project_root,
    )

    runner = CliRunner()

    write_artifact_config(
        "custom-ornament",
        {
            "model": "shape",
            "shape_size": 80.0,
        },
        project_root=project_root,
    )

    build_result = runner.invoke(
        cli,
        [
            "build",
            "custom-ornament",
            "--variant",
            "shape.ornament",
        ],
    )

    assert build_result.exit_code == 0, (
        f"Customized ornament build failed:\n{build_result.output}\n{build_result.exception!r}"
    )

    plans = create_build_plans(
        "custom-ornament",
        model_name="shape",
        variant_name="ornament",
        project_root=project_root,
    )

    assert len(plans) == 1

    plan = plans[0]

    # Variant identity is unchanged.
    assert plan.model_name == "shape"
    assert plan.resolver("variant") == "ornament"

    # The specialized Variant still supplies its sparse override.
    assert plan.resolver("shape_outer_ridge_width") == 2.0
    assert plan.resolver.source("shape_outer_ridge_width") == "variant 'ornament'"

    # Artifact customization overlays Model/Variant configuration.
    assert plan.resolver("shape_size") == 80.0
    assert plan.resolver.source("shape_size") == "artifact"

    # Artifact customization changes the manufactured Shape without
    # changing the selected Variant's persistent product identity.
    shape_root = project_root / "artifacts" / "custom-ornament" / "shape" / "ornament"

    base = shape_root / "30-extrude" / "base.stl"

    assert base.is_file()
    assert base.stat().st_size > 0

    # Inspect the manufactured STL rather than stopping at resolver
    # assertions. An 80 mm circular Shape should span approximately
    # 80 mm in X and Y.
    x_values: list[float] = []
    y_values: list[float] = []

    for line in base.read_text(
        encoding="utf-8",
    ).splitlines():
        stripped = line.strip()

        if not stripped.startswith("vertex "):
            continue

        coordinates = stripped.split()

        assert len(coordinates) == 4

        x_values.append(float(coordinates[1]))
        y_values.append(float(coordinates[2]))

    assert x_values
    assert y_values

    assert max(x_values) - min(x_values) == pytest.approx(
        80.0,
        abs=0.1,
    )
    assert max(y_values) - min(y_values) == pytest.approx(
        80.0,
        abs=0.1,
    )


@pytest.mark.slow
def test_shape_variants_have_distinct_persistent_product_identity(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """
    Model Variants have distinct canonical persistent product identity.

    Building shape.default and shape.ornament for the same Artifact
    preserves both manufacturing results under their Model-scoped local
    Variant names.
    """

    project_root = tmp_path

    monkeypatch.chdir(
        project_root,
    )

    runner = CliRunner()

    write_artifact_config(
        "multi-variant-shape",
        {
            "model": "shape",
        },
        project_root=project_root,
    )

    default_result = runner.invoke(
        cli,
        [
            "build",
            "multi-variant-shape",
            "--variant",
            "shape.default",
        ],
    )

    assert default_result.exit_code == 0, (
        f"Default Shape build failed:\n{default_result.output}\n{default_result.exception!r}"
    )

    ornament_result = runner.invoke(
        cli,
        [
            "build",
            "multi-variant-shape",
            "--variant",
            "shape.ornament",
        ],
    )

    assert ornament_result.exit_code == 0, (
        f"Ornament Shape build failed:\n{ornament_result.output}\n{ornament_result.exception!r}"
    )

    shape_root = project_root / "artifacts" / "multi-variant-shape" / "shape"

    default_artifact = shape_root / "default" / "40-package" / "artifact.3mf"

    ornament_artifact = shape_root / "ornament" / "40-package" / "artifact.3mf"

    assert default_artifact.is_file()
    assert ornament_artifact.is_file()

    assert zipfile.is_zipfile(
        default_artifact,
    )
    assert zipfile.is_zipfile(
        ornament_artifact,
    )

    def object_names(
        artifact: Path,
    ) -> set[str | None]:
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
                ),
            )

        return {
            object_.get("name")
            for object_ in model.findall(
                f".//{{{CORE_NS}}}object",
            )
        }

    default_names = object_names(
        default_artifact,
    )

    ornament_names = object_names(
        ornament_artifact,
    )

    assert "multi-variant-shape-base-white" in default_names
    assert "multi-variant-shape-ridge-white" not in default_names

    assert "multi-variant-shape-base-white" in ornament_names
    assert "multi-variant-shape-ridge-white" in ornament_names


@pytest.mark.slow
def test_shape_ornament_variant_reuses_current_artwork_product(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """
    shape.ornament reuses an already-current registered Artwork Product.

    Switching from the default Shape Variant to the specialized ornament
    Variant rebuilds Shape manufacturing without reexecuting the registered
    Artwork stages on which Shape depends.
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

    artwork_directory = project_root / "artifacts" / "variant-source-artwork"

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
        "variant-source-artwork",
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
            "artifact": "variant-source-artwork",
            "realization": "default",
        },
    }

    # -----------------------------------------------------
    # Configure Shape consumer
    # -----------------------------------------------------

    write_artifact_config(
        "variant-artwork-shape",
        {
            "model": "shape",
            "product_dependencies": artwork_dependency,
        },
        project_root=project_root,
    )

    # -----------------------------------------------------
    # Build default Shape and realize registered Artwork
    # -----------------------------------------------------

    default_plan = create_build_plans(
        "variant-artwork-shape",
        model_name="shape",
        variant_name="default",
        project_root=project_root,
    )[0]

    execute_dependency_build(
        default_plan,
    )

    artwork_root = project_root / "artifacts" / "variant-source-artwork" / "artwork" / "default"

    assert (artwork_root / "10-prepare" / "trace.svg").is_file()
    assert (artwork_root / "20-raster" / "products.json").is_file()
    assert (artwork_root / "30-vector" / "products.json").is_file()

    # Shape requires only registered Artwork, not standalone
    # Artwork manufacturing.
    assert not (artwork_root / "40-extrude" / "products.json").exists()
    assert not (artwork_root / "50-package" / "artifact.3mf").exists()

    # -----------------------------------------------------
    # Build specialized Shape Variant
    # -----------------------------------------------------

    events = []

    ornament_plan = create_build_plans(
        "variant-artwork-shape",
        model_name="shape",
        variant_name="ornament",
        project_root=project_root,
    )[0]

    assert ornament_plan.resolver("variant") == "ornament"
    assert ornament_plan.resolver("shape_outer_ridge_width") == 2.0
    assert ornament_plan.resolver.source("shape_outer_ridge_width") == "variant 'ornament'"

    execute_dependency_build(
        ornament_plan,
        event_sink=events.append,
    )

    # -----------------------------------------------------
    # Registered Artwork is reused
    # -----------------------------------------------------

    artwork_started = tuple(
        event.stage_name
        for event in events
        if event.kind == "stage.started"
        and event.artifact_id == "variant-source-artwork"
        and event.model_name == "artwork"
    )

    assert artwork_started == ()

    # -----------------------------------------------------
    # Specialized Shape manufacturing executes
    # -----------------------------------------------------

    shape_started = tuple(
        event.stage_name
        for event in events
        if event.kind == "stage.started"
        and event.artifact_id == "variant-artwork-shape"
        and event.model_name == "shape"
    )

    assert shape_started == (
        "structure",
        "compose",
        "extrude",
        "package",
    )

    # -----------------------------------------------------
    # Specialized Variant owns its persistent output
    # -----------------------------------------------------

    ornament_artifact = (
        project_root
        / "artifacts"
        / "variant-artwork-shape"
        / "shape"
        / "ornament"
        / "40-package"
        / "artifact.3mf"
    )

    assert ornament_artifact.is_file()
    assert ornament_artifact.stat().st_size > 0
    assert zipfile.is_zipfile(
        ornament_artifact,
    )

    # Standalone Artwork manufacturing remains unnecessary.
    assert not (artwork_root / "40-extrude" / "products.json").exists()
    assert not (artwork_root / "50-package" / "artifact.3mf").exists()
