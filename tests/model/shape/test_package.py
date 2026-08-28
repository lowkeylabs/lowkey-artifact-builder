"""
Tests for Shape physical-component packaging.
"""
# File: tests/model/shape/test_package.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
import zipfile
from pathlib import Path
from unittest.mock import Mock, call

import pytest

from lowkey_artifact_builder.engine import StageContext
from lowkey_artifact_builder.engine.bootstrap import build_stage_registry
from lowkey_artifact_builder.model.models.shape import stages
from lowkey_artifact_builder.model.models.shape.stages import package

# =========================================================
# Helpers
# =========================================================


def _write_component_stl(
    path: Path,
    *,
    solid_name: str,
) -> None:
    """
    Write a minimal representative Shape physical-component STL.
    """

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        f"""solid {solid_name}
facet normal 0 0 1
    outer loop
        vertex 0 0 0
        vertex 1 0 0
        vertex 0 1 0
    endloop
endfacet
endsolid {solid_name}
""",
        encoding="utf-8",
    )


def _write_component_manifest(
    path: Path,
    components: tuple[
        tuple[
            str,
            str,
        ],
        ...,
    ],
) -> None:
    """
    Write a representative Shape physical-component manifest.

    Component paths are relative to the manifest so packaging can discover
    physical manufacturing geometry without constructing artifact workspace
    paths.
    """

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        json.dumps(
            {
                "components": [
                    {
                        "name": name,
                        "path": component_path,
                    }
                    for name, component_path in components
                ],
            }
        ),
        encoding="utf-8",
    )


def _write_base_manifest(
    directory: Path,
) -> Path:
    """
    Write a representative one-component Shape extrusion result.
    """

    base = directory / "base.stl"
    manifest = directory / "products.json"

    _write_component_stl(
        base,
        solid_name="shape-base",
    )

    _write_component_manifest(
        manifest,
        (
            (
                "base",
                "base.stl",
            ),
        ),
    )

    return manifest


def _write_base_and_ridge_manifest(
    directory: Path,
) -> Path:
    """
    Write a representative two-component Shape extrusion result.
    """

    base = directory / "base.stl"
    ridge = directory / "ridge.stl"
    manifest = directory / "products.json"

    _write_component_stl(
        base,
        solid_name="shape-base",
    )

    _write_component_stl(
        ridge,
        solid_name="shape-ridge",
    )

    _write_component_manifest(
        manifest,
        (
            (
                "base",
                "base.stl",
            ),
            (
                "ridge",
                "ridge.stl",
            ),
        ),
    )

    return manifest


# =========================================================
# Package stage execution
# =========================================================


def test_package_stage_materializes_declared_artifact(
    tmp_path: Path,
) -> None:
    """
    Shape packaging materializes the declared final 3MF artifact.

    Packaging discovers physical manufacturing components through the
    extrusion manifest supplied by StageContext and does not construct
    artifact workspace paths itself.
    """

    manifest = _write_base_manifest(
        tmp_path / "extrude",
    )
    artifact = tmp_path / "package" / "artifact.3mf"

    context = Mock(
        spec=StageContext,
    )
    context.artifact_id = "example"
    context.input.return_value = manifest
    context.output.return_value = artifact

    package.execute(
        context,
    )

    context.input.assert_called_once_with(
        "extrude.manifest",
    )

    context.output.assert_called_once_with(
        "artifact",
    )

    assert artifact.is_file()


def test_package_stage_produces_valid_3mf_container(
    tmp_path: Path,
) -> None:
    """
    Shape packaging produces a structurally valid 3MF ZIP container.
    """

    manifest = _write_base_manifest(
        tmp_path / "extrude",
    )
    artifact = tmp_path / "artifact.3mf"

    context = Mock(
        spec=StageContext,
    )
    context.artifact_id = "example"
    context.input.return_value = manifest
    context.output.return_value = artifact

    package.execute(
        context,
    )

    assert zipfile.is_zipfile(
        artifact,
    )

    with zipfile.ZipFile(
        artifact,
    ) as archive:
        names = set(
            archive.namelist(),
        )

    assert "[Content_Types].xml" in names
    assert "_rels/.rels" in names
    assert "3D/3dmodel.model" in names


def test_package_stage_packages_single_base_component(
    tmp_path: Path,
) -> None:
    """
    A no-ridge Shape packages the base component described by its manifest.

    Component membership comes from the extrusion manifest rather than
    hard-coded knowledge that every Shape contains exactly one STL.
    """

    manifest = _write_base_manifest(
        tmp_path / "extrude",
    )
    artifact = tmp_path / "artifact.3mf"

    context = Mock(
        spec=StageContext,
    )
    context.artifact_id = "example"
    context.input.return_value = manifest
    context.output.return_value = artifact

    package.execute(
        context,
    )

    with zipfile.ZipFile(
        artifact,
    ) as archive:
        model = archive.read(
            "3D/3dmodel.model",
        ).decode(
            "utf-8",
        )

    assert "example-base" in model
    assert "example-ridge" not in model


def test_package_stage_packages_all_manifest_components(
    tmp_path: Path,
) -> None:
    """
    Shape packaging preserves every independently printable component
    described by the extrusion manifest.

    An integrated or separate ridge may therefore retain physical component
    identity independently from the structural relationship between the
    ridge and base.
    """

    manifest = _write_base_and_ridge_manifest(
        tmp_path / "extrude",
    )
    artifact = tmp_path / "artifact.3mf"

    context = Mock(
        spec=StageContext,
    )
    context.artifact_id = "example"
    context.input.return_value = manifest
    context.output.return_value = artifact

    package.execute(
        context,
    )

    with zipfile.ZipFile(
        artifact,
    ) as archive:
        model = archive.read(
            "3D/3dmodel.model",
        ).decode(
            "utf-8",
        )

    assert "example-base" in model
    assert "example-ridge" in model


def test_package_stage_uses_semantic_component_names(
    tmp_path: Path,
) -> None:
    """
    Packaged Shape components have stable semantic object identities.

    Object naming combines artifact identity with the component role declared
    by the manifest rather than depending on physical STL filenames.
    """

    component_directory = tmp_path / "extrude"

    base = component_directory / "arbitrary-base-name.stl"
    ridge = component_directory / "arbitrary-ridge-name.stl"
    manifest = component_directory / "products.json"
    artifact = tmp_path / "artifact.3mf"

    _write_component_stl(
        base,
        solid_name="arbitrary-base",
    )

    _write_component_stl(
        ridge,
        solid_name="arbitrary-ridge",
    )

    _write_component_manifest(
        manifest,
        (
            (
                "base",
                "arbitrary-base-name.stl",
            ),
            (
                "ridge",
                "arbitrary-ridge-name.stl",
            ),
        ),
    )

    context = Mock(
        spec=StageContext,
    )
    context.artifact_id = "example"
    context.input.return_value = manifest
    context.output.return_value = artifact

    package.execute(
        context,
    )

    with zipfile.ZipFile(
        artifact,
    ) as archive:
        model = archive.read(
            "3D/3dmodel.model",
        ).decode(
            "utf-8",
        )

    assert "example-base" in model
    assert "example-ridge" in model

    assert "example-arbitrary-base-name" not in model
    assert "example-arbitrary-ridge-name" not in model


def test_package_stage_does_not_resolve_geometry_parameters(
    tmp_path: Path,
) -> None:
    """
    Shape packaging does not construct or dimensionalize geometry.

    Physical Shape parameters belong to upstream production stages.
    Packaging consumes only the physical-component manifest and the
    components it describes.
    """

    manifest = _write_base_manifest(
        tmp_path / "extrude",
    )
    artifact = tmp_path / "artifact.3mf"

    resolver = Mock()

    context = Mock(
        spec=StageContext,
    )
    context.artifact_id = "example"
    context.resolver = resolver
    context.input.return_value = manifest
    context.output.return_value = artifact

    package.execute(
        context,
    )

    resolver.assert_not_called()


def test_package_stage_rejects_missing_component_manifest(
    tmp_path: Path,
) -> None:
    """
    Shape packaging requires its declared extrusion manifest.
    """

    manifest = tmp_path / "missing-products.json"
    artifact = tmp_path / "artifact.3mf"

    context = Mock(
        spec=StageContext,
    )
    context.artifact_id = "example"
    context.input.return_value = manifest
    context.output.return_value = artifact

    with pytest.raises(
        package.PackageError,
        match="manifest",
    ):
        package.execute(
            context,
        )

    assert not artifact.exists()


@pytest.mark.parametrize(
    ("component_name", "component_path"),
    [
        (
            "base",
            "missing-base.stl",
        ),
        (
            "ridge",
            "missing-ridge.stl",
        ),
    ],
)
def test_package_stage_rejects_missing_manifest_component(
    tmp_path: Path,
    component_name: str,
    component_path: str,
) -> None:
    """
    Shape packaging rejects any physical component missing from the manifest.

    Every component declared by extrusion must exist before final packaging;
    this applies uniformly to the required base and to an optional ridge.
    """

    manifest = tmp_path / "products.json"
    artifact = tmp_path / "artifact.3mf"

    _write_component_manifest(
        manifest,
        (
            (
                component_name,
                component_path,
            ),
        ),
    )

    context = Mock(
        spec=StageContext,
    )
    context.artifact_id = "example"
    context.input.return_value = manifest
    context.output.return_value = artifact

    with pytest.raises(
        package.PackageError,
        match=component_name,
    ):
        package.execute(
            context,
        )

    assert not artifact.exists()


# =========================================================
# Stage registration
# =========================================================


def test_shape_registers_package_stage_implementation() -> None:
    """
    Shape contributes its package implementation through its stage package.

    Registration uses logical model and stage identities rather than numeric
    stage IDs or engine-specific orchestration.
    """

    registry = Mock()

    stages.register_stage_implementations(
        registry,
    )

    assert (
        call(
            "shape",
            "package",
            package.execute,
        )
        in registry.register.call_args_list
    )


def test_engine_bootstrap_discovers_shape_package_implementation() -> None:
    """
    Normal engine bootstrap discovers the executable Shape package stage.

    Shape participates in generic model stage discovery without requiring the
    engine to know about Shape packaging explicitly.
    """

    registry = build_stage_registry()

    implementation = registry.get(
        "shape",
        "package",
    )

    assert implementation is package.execute
