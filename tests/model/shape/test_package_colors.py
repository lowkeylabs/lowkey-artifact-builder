"""
Tests for Shape Package physical-color policy.
Shape extrusion establishes physical component membership and geometry while
preserving logical component identity. Package is responsible for resolving
physical printing colors for those components.
Shape-owned color policy is:
    base
        resolves shape_base_color
    ridge
        resolves shape_outer_ridge_color when explicitly configured;
        otherwise inherits the resolved base color
    artwork-fill
        resolves shape_artwork_fill_color when explicitly configured;
        otherwise inherits the resolved base color
Incorporated Artwork color assignment is covered separately by existing
Package tests.
"""

# File: tests/model/shape/test_package_colors.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import json
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from unittest.mock import Mock, call

from lowkey_artifact_builder.engine import StageContext
from lowkey_artifact_builder.formats.threemf import (
    CORE_NS,
    component_name,
)
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


def _write_logical_component_manifest(
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
    Write a Shape extrusion manifest containing logical component identity.
    Shape-owned physical components carry no printer-color metadata.
    Physical color assignment belongs to downstream packaging.
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


def _read_model(
    artifact: Path,
) -> ET.Element:
    """
    Read the primary model document from a packaged Shape artifact.
    """
    with zipfile.ZipFile(
        artifact,
        mode="r",
    ) as archive:
        data = archive.read(
            "3D/3dmodel.model",
        )
    return ET.fromstring(
        data,
    )


def _configure_package_outputs(
    context: Mock,
    artifact: Path,
) -> Path:
    """
    Configure the persistent outputs of the Shape Package stage.
    """
    package_manifest = artifact.with_name("products.json")
    context.output.side_effect = {
        "artifact": artifact,
        "manifest": package_manifest,
    }.__getitem__
    return package_manifest


def _with_raise_style(
    values: dict[str, object],
    *,
    raise_style: str = "raised",
) -> dict[str, object]:
    """
    Add the Shape-level metadata required by Package.

    Color-policy tests use the ordinary raised realization unless the
    raise style itself is under test.
    """
    return {
        **values,
        "shape_raise_style": raise_style,
    }


# =========================================================
# Base color
# =========================================================
def test_package_stage_resolves_shape_base_color(
    tmp_path: Path,
) -> None:
    """
    Package resolves the physical printing color of the structural base.
    Shape Extrude supplies logical component identity only. Physical Shape
    color policy belongs exclusively to Package.
    """
    component_directory = tmp_path / "extrude"
    base = component_directory / "base.stl"
    manifest = component_directory / "products.json"
    artifact = tmp_path / "artifact.3mf"
    _write_component_stl(
        base,
        solid_name="shape-base",
    )
    _write_logical_component_manifest(
        manifest,
        (
            (
                "base",
                "base.stl",
            ),
        ),
    )
    resolver = Mock()
    values = {
        "shape_base_color": "test-blue",
        "shape_raise_style": "raised",
    }
    resolver.side_effect = values.__getitem__
    resolver.colors = {
        "test-blue": {
            "rgb": [
                0,
                0,
                255,
            ],
        },
    }
    context = Mock(
        spec=StageContext,
    )
    context.artifact_id = "example"
    context.resolver = resolver
    context.input.return_value = manifest
    _configure_package_outputs(
        context,
        artifact,
    )
    package.execute(
        context,
    )
    assert resolver.call_args_list == [
        call("shape_base_color"),
        call("shape_raise_style"),
    ]
    model = _read_model(
        artifact,
    )
    objects = model.findall(
        f".//{{{CORE_NS}}}object",
    )
    materials = model.findall(
        f".//{{{CORE_NS}}}basematerials",
    )
    assert len(objects) == 1
    assert objects[0].get("name") == component_name(
        "example",
        "base",
        "test-blue",
    )
    assert len(materials) == 1
    color = materials[0].find(
        f"{{{CORE_NS}}}base",
    )
    assert color is not None
    assert color.get("name") == "test-blue"
    assert color.get("displaycolor") == "#0000FF"


# =========================================================
# Base-color inheritance
# =========================================================
def test_package_stage_outer_ridge_inherits_base_color(
    tmp_path: Path,
) -> None:
    """
    Outer ridge inherits the resolved physical base color when no explicit
    ridge-color override is configured.
    """
    component_directory = tmp_path / "extrude"
    base = component_directory / "base.stl"
    ridge = component_directory / "ridge.stl"
    manifest = component_directory / "products.json"
    artifact = tmp_path / "artifact.3mf"
    _write_component_stl(
        base,
        solid_name="shape-base",
    )
    _write_component_stl(
        ridge,
        solid_name="shape-ridge",
    )
    _write_logical_component_manifest(
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
    resolver = Mock()
    resolver.side_effect = {
        "shape_base_color": "test-blue",
        "shape_raise_style": "raised",
    }.__getitem__
    resolver.has.return_value = False
    resolver.colors = {
        "test-blue": {
            "rgb": [
                0,
                0,
                255,
            ],
        },
    }
    context = Mock(
        spec=StageContext,
    )
    context.artifact_id = "example"
    context.resolver = resolver
    context.input.return_value = manifest
    _configure_package_outputs(
        context,
        artifact,
    )
    package.execute(
        context,
    )
    model = _read_model(
        artifact,
    )
    objects = model.findall(
        f".//{{{CORE_NS}}}object",
    )
    assert {object_.get("name") for object_ in objects} == {
        component_name(
            "example",
            "base",
            "test-blue",
        ),
        component_name(
            "example",
            "ridge",
            "test-blue",
        ),
    }
    resolver.has.assert_called_once_with(
        "shape_outer_ridge_color",
    )


def test_package_stage_artwork_fill_inherits_base_color(
    tmp_path: Path,
) -> None:
    """
    Artwork fill inherits the resolved physical base color when no explicit
    fill-color override is configured.
    Fill participation is established by Extrude and is independent of
    Package-time physical color policy.
    """
    component_directory = tmp_path / "extrude"
    base = component_directory / "base.stl"
    artwork_fill = component_directory / "artwork-fill.stl"
    manifest = component_directory / "products.json"
    artifact = tmp_path / "artifact.3mf"
    _write_component_stl(
        base,
        solid_name="shape-base",
    )
    _write_component_stl(
        artwork_fill,
        solid_name="artwork-fill",
    )
    _write_logical_component_manifest(
        manifest,
        (
            (
                "base",
                "base.stl",
            ),
            (
                "artwork-fill",
                "artwork-fill.stl",
            ),
        ),
    )
    resolver = Mock()
    resolver.side_effect = {
        "shape_base_color": "test-blue",
        "shape_raise_style": "raised",
    }.__getitem__
    resolver.has.return_value = False
    resolver.colors = {
        "test-blue": {
            "rgb": [
                0,
                0,
                255,
            ],
        },
    }
    context = Mock(
        spec=StageContext,
    )
    context.artifact_id = "example"
    context.resolver = resolver
    context.input.return_value = manifest
    _configure_package_outputs(
        context,
        artifact,
    )
    package.execute(
        context,
    )
    model = _read_model(
        artifact,
    )
    objects = model.findall(
        f".//{{{CORE_NS}}}object",
    )
    assert {object_.get("name") for object_ in objects} == {
        component_name(
            "example",
            "base",
            "test-blue",
        ),
        component_name(
            "example",
            "artwork-fill",
            "test-blue",
        ),
    }
    resolver.has.assert_called_once_with(
        "shape_artwork_fill_color",
    )


# =========================================================
# Explicit color overrides
# =========================================================
def test_package_stage_resolves_explicit_shape_color_overrides(
    tmp_path: Path,
) -> None:
    """
    Explicit ridge and Artwork-fill colors override base-color inheritance.
    Shape-owned physical color policy is resolved entirely during Package.
    """
    component_directory = tmp_path / "extrude"
    base = component_directory / "base.stl"
    ridge = component_directory / "ridge.stl"
    artwork_fill = component_directory / "artwork-fill.stl"
    manifest = component_directory / "products.json"
    artifact = tmp_path / "artifact.3mf"
    _write_component_stl(
        base,
        solid_name="shape-base",
    )
    _write_component_stl(
        ridge,
        solid_name="shape-ridge",
    )
    _write_component_stl(
        artwork_fill,
        solid_name="artwork-fill",
    )
    _write_logical_component_manifest(
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
            (
                "artwork-fill",
                "artwork-fill.stl",
            ),
        ),
    )
    resolver = Mock()
    values = {
        "shape_base_color": "test-white",
        "shape_raise_style": "raised",
        "shape_outer_ridge_color": "test-red",
        "shape_artwork_fill_color": "test-blue",
    }
    resolver.side_effect = values.__getitem__
    resolver.has.side_effect = lambda name: name in {
        "shape_outer_ridge_color",
        "shape_artwork_fill_color",
    }
    resolver.colors = {
        "test-white": {
            "rgb": [
                255,
                255,
                255,
            ],
        },
        "test-red": {
            "rgb": [
                255,
                0,
                0,
            ],
        },
        "test-blue": {
            "rgb": [
                0,
                0,
                255,
            ],
        },
    }
    context = Mock(
        spec=StageContext,
    )
    context.artifact_id = "example"
    context.resolver = resolver
    context.input.return_value = manifest
    _configure_package_outputs(
        context,
        artifact,
    )
    package.execute(
        context,
    )
    model = _read_model(
        artifact,
    )
    objects = model.findall(
        f".//{{{CORE_NS}}}object",
    )
    assert {object_.get("name") for object_ in objects} == {
        component_name(
            "example",
            "base",
            "test-white",
        ),
        component_name(
            "example",
            "ridge",
            "test-red",
        ),
        component_name(
            "example",
            "artwork-fill",
            "test-blue",
        ),
    }
    assert resolver.call_args_list == [
        call(
            "shape_base_color",
        ),
        call(
            "shape_outer_ridge_color",
        ),
        call(
            "shape_artwork_fill_color",
        ),
        call(
            "shape_raise_style",
        ),
    ]


def test_package_stage_inner_ridge_inherits_base_color(
    tmp_path: Path,
) -> None:
    """
    Inner Ridge inherits the resolved physical base color when no explicit
    Inner Ridge color override is configured.
    Inner Ridge participation is established by Extrude and is independent
    of Package-time physical color policy.
    """
    component_directory = tmp_path / "extrude"
    base = component_directory / "base.stl"
    inner_ridge = component_directory / "inner-ridge.stl"
    manifest = component_directory / "products.json"
    artifact = tmp_path / "artifact.3mf"
    _write_component_stl(
        base,
        solid_name="shape-base",
    )
    _write_component_stl(
        inner_ridge,
        solid_name="shape-inner-ridge",
    )
    _write_logical_component_manifest(
        manifest,
        (
            (
                "base",
                "base.stl",
            ),
            (
                "inner-ridge",
                "inner-ridge.stl",
            ),
        ),
    )
    resolver = Mock()
    resolver.side_effect = {
        "shape_base_color": "test-blue",
        "shape_raise_style": "raised",
    }.__getitem__
    resolver.has.return_value = False
    resolver.colors = {
        "test-blue": {
            "rgb": [
                0,
                0,
                255,
            ],
        },
    }
    context = Mock(
        spec=StageContext,
    )
    context.artifact_id = "example"
    context.resolver = resolver
    context.input.return_value = manifest
    _configure_package_outputs(
        context,
        artifact,
    )
    package.execute(
        context,
    )
    model = _read_model(
        artifact,
    )
    objects = model.findall(
        f".//{{{CORE_NS}}}object",
    )
    assert {object_.get("name") for object_ in objects} == {
        component_name(
            "example",
            "base",
            "test-blue",
        ),
        component_name(
            "example",
            "inner-ridge",
            "test-blue",
        ),
    }
    resolver.has.assert_called_once_with(
        "shape_inner_ridge_color",
    )


def test_package_stage_resolves_explicit_inner_ridge_color(
    tmp_path: Path,
) -> None:
    """
    An explicit Inner Ridge color overrides base-color inheritance.
    Inner Ridge remains an independently identifiable physical component,
    and its physical color is resolved exclusively during Package.
    """
    component_directory = tmp_path / "extrude"
    base = component_directory / "base.stl"
    inner_ridge = component_directory / "inner-ridge.stl"
    manifest = component_directory / "products.json"
    artifact = tmp_path / "artifact.3mf"
    _write_component_stl(
        base,
        solid_name="shape-base",
    )
    _write_component_stl(
        inner_ridge,
        solid_name="shape-inner-ridge",
    )
    _write_logical_component_manifest(
        manifest,
        (
            (
                "base",
                "base.stl",
            ),
            (
                "inner-ridge",
                "inner-ridge.stl",
            ),
        ),
    )
    resolver = Mock()
    values = {
        "shape_base_color": "test-white",
        "shape_raise_style": "raised",
        "shape_inner_ridge_color": "test-red",
    }
    resolver.side_effect = values.__getitem__
    resolver.has.side_effect = values.__contains__
    resolver.colors = {
        "test-white": {
            "rgb": [
                255,
                255,
                255,
            ],
        },
        "test-red": {
            "rgb": [
                255,
                0,
                0,
            ],
        },
    }
    context = Mock(
        spec=StageContext,
    )
    context.artifact_id = "example"
    context.resolver = resolver
    context.input.return_value = manifest
    _configure_package_outputs(
        context,
        artifact,
    )
    package.execute(
        context,
    )
    model = _read_model(
        artifact,
    )
    objects = model.findall(
        f".//{{{CORE_NS}}}object",
    )
    assert {object_.get("name") for object_ in objects} == {
        component_name(
            "example",
            "base",
            "test-white",
        ),
        component_name(
            "example",
            "inner-ridge",
            "test-red",
        ),
    }
    materials = model.findall(
        f".//{{{CORE_NS}}}basematerials",
    )
    materials_by_id = {material.get("id"): material for material in materials}
    inner_ridge_name = component_name(
        "example",
        "inner-ridge",
        "test-red",
    )
    objects_by_name = {object_.get("name"): object_ for object_ in objects}
    packaged_inner_ridge = objects_by_name[inner_ridge_name]
    material_id = packaged_inner_ridge.get(
        "pid",
    )
    assert material_id is not None
    color = materials_by_id[material_id].find(
        f"{{{CORE_NS}}}base",
    )
    assert color is not None
    assert color.get("name") == "test-red"
    assert color.get("displaycolor") == "#FF0000"
    assert resolver.call_args_list == [
        call(
            "shape_base_color",
        ),
        call(
            "shape_inner_ridge_color",
        ),
        call(
            "shape_raise_style",
        ),
    ]


# =========================================================
# Loop color
# =========================================================
def test_package_stage_loop_inherits_base_color(
    tmp_path: Path,
) -> None:
    """
    Shape Loop inherits the resolved Base color when no explicit override
    is configured.
    """
    component_directory = tmp_path / "extrude"
    base = component_directory / "base.stl"
    loop = component_directory / "loop.stl"
    manifest = component_directory / "products.json"
    artifact = tmp_path / "artifact.3mf"
    _write_component_stl(
        base,
        solid_name="shape-base",
    )
    _write_component_stl(
        loop,
        solid_name="shape-loop",
    )
    _write_logical_component_manifest(
        manifest,
        (
            ("base", "base.stl"),
            ("loop", "loop.stl"),
        ),
    )
    resolver = Mock(
        side_effect={
            "shape_base_color": "test-blue",
            "shape_raise_style": "raised",
        }.__getitem__,
    )
    resolver.has.return_value = False
    resolver.colors = {
        "test-blue": {
            "rgb": [0, 0, 255],
        },
    }
    context = Mock(
        spec=StageContext,
    )
    context.artifact_id = "example"
    context.resolver = resolver
    context.input.return_value = manifest
    _configure_package_outputs(
        context,
        artifact,
    )
    package.execute(
        context,
    )
    model = _read_model(
        artifact,
    )
    objects = model.findall(
        f".//{{{CORE_NS}}}object",
    )
    assert {object_.get("name") for object_ in objects} == {
        component_name(
            "example",
            "base",
            "test-blue",
        ),
        component_name(
            "example",
            "loop",
            "test-blue",
        ),
    }
    resolver.has.assert_called_once_with(
        "shape_loop_color",
    )


def test_package_stage_loop_uses_explicit_color_override(
    tmp_path: Path,
) -> None:
    """
    Explicit Shape Loop color overrides inherited Base color.
    """
    component_directory = tmp_path / "extrude"
    base = component_directory / "base.stl"
    loop = component_directory / "loop.stl"
    manifest = component_directory / "products.json"
    artifact = tmp_path / "artifact.3mf"
    _write_component_stl(
        base,
        solid_name="shape-base",
    )
    _write_component_stl(
        loop,
        solid_name="shape-loop",
    )
    _write_logical_component_manifest(
        manifest,
        (
            ("base", "base.stl"),
            ("loop", "loop.stl"),
        ),
    )
    resolver = Mock(
        side_effect={
            "shape_base_color": "test-blue",
            "shape_raise_style": "raised",
            "shape_loop_color": "test-red",
        }.__getitem__,
    )
    resolver.has.side_effect = lambda name: name == "shape_loop_color"
    resolver.colors = {
        "test-blue": {
            "rgb": [0, 0, 255],
        },
        "test-red": {
            "rgb": [255, 0, 0],
        },
    }
    context = Mock(
        spec=StageContext,
    )
    context.artifact_id = "example"
    context.resolver = resolver
    context.input.return_value = manifest
    _configure_package_outputs(
        context,
        artifact,
    )
    package.execute(
        context,
    )
    model = _read_model(
        artifact,
    )
    objects = model.findall(
        f".//{{{CORE_NS}}}object",
    )
    assert {object_.get("name") for object_ in objects} == {
        component_name(
            "example",
            "base",
            "test-blue",
        ),
        component_name(
            "example",
            "loop",
            "test-red",
        ),
    }
