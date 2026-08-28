"""
Tests for Shape physical-component packaging.
"""
# File: tests/model/shape/test_package.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

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


def _write_base_stl(
    path: Path,
) -> None:
    """
    Write a minimal representative Shape base STL.
    """

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        """solid shape-base
facet normal 0 0 1
    outer loop
        vertex 0 0 0
        vertex 1 0 0
        vertex 0 1 0
    endloop
endfacet
endsolid shape-base
""",
        encoding="utf-8",
    )


# =========================================================
# Package stage execution
# =========================================================


def test_package_stage_materializes_declared_artifact(
    tmp_path: Path,
) -> None:
    """
    Shape packaging materializes the declared final 3MF artifact.

    Packaging consumes physical manufacturing geometry supplied through
    StageContext and does not construct artifact filesystem paths itself.
    """

    base = tmp_path / "base.stl"
    artifact = tmp_path / "artifact.3mf"

    _write_base_stl(
        base,
    )

    context = Mock(
        spec=StageContext,
    )
    context.artifact_id = "example"
    context.input.return_value = base
    context.output.return_value = artifact

    package.execute(
        context,
    )

    context.input.assert_called_once_with(
        "extrude.base",
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

    base = tmp_path / "base.stl"
    artifact = tmp_path / "artifact.3mf"

    _write_base_stl(
        base,
    )

    context = Mock(
        spec=StageContext,
    )
    context.artifact_id = "example"
    context.input.return_value = base
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


def test_package_stage_uses_semantic_base_component_name(
    tmp_path: Path,
) -> None:
    """
    The packaged Shape base has a stable semantic object identity.

    Object naming combines artifact identity with the role of the physical
    component rather than depending on temporary filesystem names.
    """

    base = tmp_path / "arbitrary-name.stl"
    artifact = tmp_path / "artifact.3mf"

    _write_base_stl(
        base,
    )

    context = Mock(
        spec=StageContext,
    )
    context.artifact_id = "example"
    context.input.return_value = base
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


def test_package_stage_does_not_resolve_geometry_parameters(
    tmp_path: Path,
) -> None:
    """
    Shape packaging does not construct or dimensionalize geometry.

    Physical Shape parameters belong to upstream production stages.
    """

    base = tmp_path / "base.stl"
    artifact = tmp_path / "artifact.3mf"

    _write_base_stl(
        base,
    )

    resolver = Mock()

    context = Mock(
        spec=StageContext,
    )
    context.artifact_id = "example"
    context.resolver = resolver
    context.input.return_value = base
    context.output.return_value = artifact

    package.execute(
        context,
    )

    resolver.assert_not_called()


def test_package_stage_rejects_missing_base_component(
    tmp_path: Path,
) -> None:
    """
    Shape packaging rejects a missing physical base component.

    Packaging must not silently create an empty final artifact.
    """

    base = tmp_path / "missing-base.stl"
    artifact = tmp_path / "artifact.3mf"

    context = Mock(
        spec=StageContext,
    )
    context.artifact_id = "example"
    context.input.return_value = base
    context.output.return_value = artifact

    with pytest.raises(
        package.PackageError,
        match="base",
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
