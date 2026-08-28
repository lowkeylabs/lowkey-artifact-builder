"""
Tests for 3MF format utilities.
"""
# File: tests/formats/test_threemf.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import struct
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import pytest

from lowkey_artifact_builder.colors import PaletteColor
from lowkey_artifact_builder.formats.threemf import (
    CONTENT_TYPES_NS,
    CORE_NS,
    MODEL_CONTENT_TYPE,
    MODEL_RELATIONSHIP_TYPE,
    RELATIONSHIPS_NS,
    Component,
    Mesh,
    ThreeMFError,
    load_stl,
    write,
    write_stls,
)

# =========================================================
# Helpers
# =========================================================


def _mesh() -> Mesh:
    """
    Return a simple triangular mesh.
    """

    return Mesh(
        vertices=(
            (0.0, 0.0, 0.0),
            (10.0, 0.0, 0.0),
            (0.0, 10.0, 0.0),
        ),
        triangles=((0, 1, 2),),
    )


def _component(
    name: str = "example",
) -> Component:
    """
    Return a simple 3MF component.
    """

    return Component(
        name=name,
        mesh=_mesh(),
    )


def _write_ascii_stl(
    path: Path,
) -> None:
    """
    Write a simple ASCII STL file.
    """

    path.write_text(
        """\
solid example
  facet normal 0 0 1
    outer loop
      vertex 0 0 0
      vertex 10 0 0
      vertex 0 10 0
    endloop
  endfacet
endsolid example
""",
        encoding="utf-8",
    )


def _write_binary_stl(
    path: Path,
) -> None:
    """
    Write a simple binary STL file.
    """

    header = bytes(80)

    triangle_count = struct.pack(
        "<I",
        1,
    )

    triangle = struct.pack(
        "<12fH",
        #
        # Normal.
        #
        0.0,
        0.0,
        1.0,
        #
        # Vertex 1.
        #
        0.0,
        0.0,
        0.0,
        #
        # Vertex 2.
        #
        10.0,
        0.0,
        0.0,
        #
        # Vertex 3.
        #
        0.0,
        10.0,
        0.0,
        #
        # Attribute byte count.
        #
        0,
    )

    path.write_bytes(header + triangle_count + triangle)


def _read_model(
    path: Path,
) -> ET.Element:
    """
    Read the primary model XML from a 3MF package.
    """

    with zipfile.ZipFile(
        path,
        mode="r",
    ) as package:
        data = package.read("3D/3dmodel.model")

    return ET.fromstring(data)


# =========================================================
# Mesh
# =========================================================


def test_mesh_retains_geometry() -> None:
    """
    Mesh retains its vertices and triangles.
    """

    mesh = _mesh()

    assert mesh.vertices == (
        (0.0, 0.0, 0.0),
        (10.0, 0.0, 0.0),
        (0.0, 10.0, 0.0),
    )

    assert mesh.triangles == ((0, 1, 2),)


def test_mesh_is_immutable() -> None:
    """
    Mesh definitions are immutable.
    """

    mesh = _mesh()

    with pytest.raises(AttributeError):
        mesh.vertices = ()  # type: ignore[misc]


# =========================================================
# Component
# =========================================================


def test_component_retains_semantic_color() -> None:
    """
    Components may retain semantic printing-color identity.

    Color belongs to the independently printable component and remains
    distinct from its mesh geometry and physical printer-head assignment.
    """

    color = PaletteColor(
        name="red",
        rgb=(
            220,
            38,
            38,
        ),
    )

    component = Component(
        name="ridge",
        mesh=_mesh(),
        color=color,
    )

    assert component.color == color


def test_component_retains_definition() -> None:
    """
    Components retain their name and mesh.
    """

    mesh = _mesh()

    component = Component(
        name="artwork-red",
        mesh=mesh,
    )

    assert component.name == "artwork-red"
    assert component.mesh == mesh


def test_component_is_immutable() -> None:
    """
    Component definitions are immutable.
    """

    component = _component()

    with pytest.raises(AttributeError):
        component.name = "changed"  # type: ignore[misc]


# =========================================================
# ASCII STL
# =========================================================


def test_load_ascii_stl(
    tmp_path: Path,
) -> None:
    """
    ASCII STL files are loaded into mesh geometry.
    """

    path = tmp_path / "example.stl"

    _write_ascii_stl(path)

    mesh = load_stl(path)

    assert mesh.vertices == (
        (0.0, 0.0, 0.0),
        (10.0, 0.0, 0.0),
        (0.0, 10.0, 0.0),
    )

    assert mesh.triangles == ((0, 1, 2),)


def test_load_ascii_stl_reuses_vertices(
    tmp_path: Path,
) -> None:
    """
    Identical STL vertices are represented only once.
    """

    path = tmp_path / "example.stl"

    path.write_text(
        """\
solid example
facet normal 0 0 1
outer loop
vertex 0 0 0
vertex 10 0 0
vertex 0 10 0
endloop
endfacet
facet normal 0 0 1
outer loop
vertex 0 0 0
vertex 0 10 0
vertex -10 0 0
endloop
endfacet
endsolid example
""",
        encoding="utf-8",
    )

    mesh = load_stl(path)

    assert len(mesh.vertices) == 4

    assert mesh.triangles == (
        (0, 1, 2),
        (0, 2, 3),
    )


# =========================================================
# Binary STL
# =========================================================


def test_load_binary_stl(
    tmp_path: Path,
) -> None:
    """
    Binary STL files are loaded into mesh geometry.
    """

    path = tmp_path / "example.stl"

    _write_binary_stl(path)

    mesh = load_stl(path)

    assert mesh.vertices == (
        (0.0, 0.0, 0.0),
        (10.0, 0.0, 0.0),
        (0.0, 10.0, 0.0),
    )

    assert mesh.triangles == ((0, 1, 2),)


# =========================================================
# STL errors
# =========================================================


def test_load_stl_rejects_missing_file(
    tmp_path: Path,
) -> None:
    """
    Missing STL files are rejected.
    """

    path = tmp_path / "missing.stl"

    with pytest.raises(
        ThreeMFError,
        match="does not exist",
    ):
        load_stl(path)


def test_load_stl_rejects_empty_file(
    tmp_path: Path,
) -> None:
    """
    Empty STL files are rejected.
    """

    path = tmp_path / "empty.stl"

    path.write_bytes(b"")

    with pytest.raises(
        ThreeMFError,
        match="contains no vertices",
    ):
        load_stl(path)


def test_load_ascii_stl_rejects_invalid_vertex(
    tmp_path: Path,
) -> None:
    """
    Invalid ASCII STL vertex coordinates are rejected.
    """

    path = tmp_path / "invalid.stl"

    path.write_text(
        """\
solid example
facet normal 0 0 1
outer loop
vertex 0 nope 0
vertex 10 0 0
vertex 0 10 0
endloop
endfacet
endsolid example
""",
        encoding="utf-8",
    )

    with pytest.raises(
        ThreeMFError,
        match="Invalid STL vertex",
    ):
        load_stl(path)


def test_load_ascii_stl_rejects_incomplete_triangle(
    tmp_path: Path,
) -> None:
    """
    ASCII STL files with incomplete triangles are rejected.
    """

    path = tmp_path / "invalid.stl"

    path.write_text(
        """\
solid example
vertex 0 0 0
vertex 10 0 0
endsolid example
""",
        encoding="utf-8",
    )

    with pytest.raises(
        ThreeMFError,
        match="Incomplete triangle",
    ):
        load_stl(path)


# =========================================================
# 3MF writing
# =========================================================


def test_write_creates_package(
    tmp_path: Path,
) -> None:
    """
    Writing creates a valid ZIP-based 3MF package.
    """

    path = tmp_path / "example.3mf"

    write(
        (_component(),),
        path,
    )

    assert path.is_file()

    assert zipfile.is_zipfile(path)


def test_write_creates_parent_directories(
    tmp_path: Path,
) -> None:
    """
    Writing creates missing parent directories.
    """

    path = tmp_path / "nested" / "output" / "example.3mf"

    write(
        (_component(),),
        path,
    )

    assert path.is_file()


def test_write_creates_required_package_parts(
    tmp_path: Path,
) -> None:
    """
    A generated 3MF contains the required package parts.
    """

    path = tmp_path / "example.3mf"

    write(
        (_component(),),
        path,
    )

    with zipfile.ZipFile(
        path,
        mode="r",
    ) as package:
        names = set(package.namelist())

    assert names == {
        "[Content_Types].xml",
        "_rels/.rels",
        "3D/3dmodel.model",
    }


def test_write_rejects_no_components(
    tmp_path: Path,
) -> None:
    """
    A 3MF document requires at least one component.
    """

    path = tmp_path / "example.3mf"

    with pytest.raises(
        ThreeMFError,
        match="without components",
    ):
        write(
            (),
            path,
        )


def test_write_rejects_empty_component_name(
    tmp_path: Path,
) -> None:
    """
    Components require non-empty names.
    """

    path = tmp_path / "example.3mf"

    component = Component(
        name="",
        mesh=_mesh(),
    )

    with pytest.raises(
        ThreeMFError,
        match="must not be empty",
    ):
        write(
            (component,),
            path,
        )


def test_write_rejects_duplicate_component_names(
    tmp_path: Path,
) -> None:
    """
    Component names must be unique.
    """

    path = tmp_path / "example.3mf"

    with pytest.raises(
        ThreeMFError,
        match="Duplicate 3MF component name",
    ):
        write(
            (
                _component("artwork"),
                _component("artwork"),
            ),
            path,
        )


def test_write_rejects_empty_mesh(
    tmp_path: Path,
) -> None:
    """
    Components must contain mesh geometry.
    """

    path = tmp_path / "example.3mf"

    component = Component(
        name="empty",
        mesh=Mesh(
            vertices=(),
            triangles=(),
        ),
    )

    with pytest.raises(
        ThreeMFError,
        match="contains no vertices",
    ):
        write(
            (component,),
            path,
        )


def test_write_rejects_invalid_triangle_index(
    tmp_path: Path,
) -> None:
    """
    Triangle indexes must refer to existing vertices.
    """

    path = tmp_path / "example.3mf"

    component = Component(
        name="invalid",
        mesh=Mesh(
            vertices=(
                (0.0, 0.0, 0.0),
                (1.0, 0.0, 0.0),
                (0.0, 1.0, 0.0),
            ),
            triangles=((0, 1, 10),),
        ),
    )

    with pytest.raises(
        ThreeMFError,
        match="invalid vertex",
    ):
        write(
            (component,),
            path,
        )


# =========================================================
# Model XML
# =========================================================


def test_write_preserves_component_color(
    tmp_path: Path,
) -> None:
    """
    A colored component retains its printing color in the 3MF model.

    The format representation preserves RGB identity without assigning the
    component to a physical printer head.
    """

    path = tmp_path / "example.3mf"

    write(
        (
            Component(
                name="ridge",
                mesh=_mesh(),
                color=PaletteColor(
                    name="red",
                    rgb=(
                        220,
                        38,
                        38,
                    ),
                ),
            ),
        ),
        path,
    )

    model = _read_model(path)

    colors = model.findall(f".//{{{CORE_NS}}}basematerials/{{{CORE_NS}}}base")

    assert len(colors) == 1

    assert colors[0].get("displaycolor") == "#DC2626"


def test_write_preserves_component_semantic_color_name(
    tmp_path: Path,
) -> None:
    """
    A colored component retains its semantic color name in the 3MF model.

    Semantic identity survives independently from the RGB representation used
    by the 3MF material resource.
    """

    path = tmp_path / "example.3mf"

    write(
        (
            Component(
                name="ridge",
                mesh=_mesh(),
                color=PaletteColor(
                    name="red",
                    rgb=(
                        220,
                        38,
                        38,
                    ),
                ),
            ),
        ),
        path,
    )

    model = _read_model(path)

    colors = model.findall(f".//{{{CORE_NS}}}basematerials/{{{CORE_NS}}}base")

    assert len(colors) == 1

    assert colors[0].get("name") == "red"


def test_write_model_uses_millimeters(
    tmp_path: Path,
) -> None:
    """
    Generated 3MF geometry uses millimeters.
    """

    path = tmp_path / "example.3mf"

    write(
        (_component(),),
        path,
    )

    model = _read_model(path)

    assert model.tag == (f"{{{CORE_NS}}}model")

    assert model.get("unit") == "millimeter"


def test_write_creates_mesh_object(
    tmp_path: Path,
) -> None:
    """
    Components become independent model objects.
    """

    path = tmp_path / "example.3mf"

    write(
        (_component("artwork-red"),),
        path,
    )

    model = _read_model(path)

    objects = model.findall(f".//{{{CORE_NS}}}object")

    assert len(objects) == 1

    assert objects[0].get("id") == "1"

    assert objects[0].get("name") == "artwork-red"

    assert objects[0].get("type") == "model"


def test_write_creates_vertices(
    tmp_path: Path,
) -> None:
    """
    Mesh vertices are represented in model XML.
    """

    path = tmp_path / "example.3mf"

    write(
        (_component(),),
        path,
    )

    model = _read_model(path)

    vertices = model.findall(f".//{{{CORE_NS}}}vertex")

    assert len(vertices) == 3

    assert vertices[0].attrib == {
        "x": "0",
        "y": "0",
        "z": "0",
    }

    assert vertices[1].attrib == {
        "x": "10",
        "y": "0",
        "z": "0",
    }

    assert vertices[2].attrib == {
        "x": "0",
        "y": "10",
        "z": "0",
    }


def test_write_creates_triangles(
    tmp_path: Path,
) -> None:
    """
    Mesh triangles reference generated vertices.
    """

    path = tmp_path / "example.3mf"

    write(
        (_component(),),
        path,
    )

    model = _read_model(path)

    triangles = model.findall(f".//{{{CORE_NS}}}triangle")

    assert len(triangles) == 1

    assert triangles[0].attrib == {
        "v1": "0",
        "v2": "1",
        "v3": "2",
    }


def test_write_creates_multiple_objects(
    tmp_path: Path,
) -> None:
    """
    Multiple components become independent model objects.
    """

    path = tmp_path / "example.3mf"

    write(
        (
            _component("red"),
            _component("white"),
            _component("green"),
        ),
        path,
    )

    model = _read_model(path)

    objects = model.findall(f".//{{{CORE_NS}}}object")

    assert [element.get("id") for element in objects] == [
        "1",
        "2",
        "3",
    ]

    assert [element.get("name") for element in objects] == [
        "red",
        "white",
        "green",
    ]


def test_write_adds_every_object_to_build(
    tmp_path: Path,
) -> None:
    """
    Every component is independently included in the build.
    """

    path = tmp_path / "example.3mf"

    write(
        (
            _component("red"),
            _component("white"),
        ),
        path,
    )

    model = _read_model(path)

    items = model.findall(f".//{{{CORE_NS}}}build/{{{CORE_NS}}}item")

    assert [item.get("objectid") for item in items] == [
        "1",
        "2",
    ]


# =========================================================
# Package metadata
# =========================================================


def test_write_creates_model_content_type(
    tmp_path: Path,
) -> None:
    """
    Package content types identify the 3MF model part.
    """

    path = tmp_path / "example.3mf"

    write(
        (_component(),),
        path,
    )

    with zipfile.ZipFile(
        path,
        mode="r",
    ) as package:
        root = ET.fromstring(package.read("[Content_Types].xml"))

    overrides = root.findall(f"{{{CONTENT_TYPES_NS}}}Override")

    assert len(overrides) == 1

    assert overrides[0].get("PartName") == "/3D/3dmodel.model"

    assert overrides[0].get("ContentType") == MODEL_CONTENT_TYPE


def test_write_creates_model_relationship(
    tmp_path: Path,
) -> None:
    """
    Package relationships identify the primary 3MF model.
    """

    path = tmp_path / "example.3mf"

    write(
        (_component(),),
        path,
    )

    with zipfile.ZipFile(
        path,
        mode="r",
    ) as package:
        root = ET.fromstring(package.read("_rels/.rels"))

    relationships = root.findall(f"{{{RELATIONSHIPS_NS}}}Relationship")

    assert len(relationships) == 1

    relationship = relationships[0]

    assert relationship.get("Target") == "/3D/3dmodel.model"

    assert relationship.get("Type") == MODEL_RELATIONSHIP_TYPE


# =========================================================
# STL convenience writer
# =========================================================


def test_write_stls(
    tmp_path: Path,
) -> None:
    """
    Named STL files can be written directly to a 3MF package.
    """

    first = tmp_path / "first.stl"
    second = tmp_path / "second.stl"

    _write_ascii_stl(first)

    _write_binary_stl(second)

    output = tmp_path / "example.3mf"

    write_stls(
        (
            (
                "first",
                first,
            ),
            (
                "second",
                second,
            ),
        ),
        output,
    )

    model = _read_model(output)

    objects = model.findall(f".//{{{CORE_NS}}}object")

    assert [element.get("name") for element in objects] == [
        "first",
        "second",
    ]


def test_write_restores_model_default_namespace(
    tmp_path: Path,
) -> None:
    """
    Model serialization restores the 3MF core default namespace.

    ElementTree namespace registration is process-global. Another XML
    subsystem may therefore replace the default namespace before a 3MF
    document is written.
    """

    ET.register_namespace(
        "",
        "http://www.w3.org/2000/svg",
    )

    output = tmp_path / "artifact.3mf"

    write(
        (
            Component(
                name="triangle",
                mesh=Mesh(
                    vertices=(
                        (0.0, 0.0, 0.0),
                        (1.0, 0.0, 0.0),
                        (0.0, 1.0, 0.0),
                    ),
                    triangles=((0, 1, 2),),
                ),
            ),
        ),
        output,
    )

    with zipfile.ZipFile(
        output,
        "r",
    ) as package:
        model = package.read("3D/3dmodel.model").decode("utf-8")

    assert f'xmlns="{CORE_NS}"' in model

    assert "ns0:model" not in model


def test_write_restores_package_default_namespaces(
    tmp_path: Path,
) -> None:
    """
    Package metadata is serialized with its required default namespaces.
    """

    ET.register_namespace(
        "",
        "http://www.w3.org/2000/svg",
    )

    output = tmp_path / "artifact.3mf"

    write(
        (
            Component(
                name="triangle",
                mesh=Mesh(
                    vertices=(
                        (0.0, 0.0, 0.0),
                        (1.0, 0.0, 0.0),
                        (0.0, 1.0, 0.0),
                    ),
                    triangles=((0, 1, 2),),
                ),
            ),
        ),
        output,
    )

    with zipfile.ZipFile(
        output,
        "r",
    ) as package:
        content_types = package.read("[Content_Types].xml").decode("utf-8")

        relationships = package.read("_rels/.rels").decode("utf-8")

    assert f'xmlns="{CONTENT_TYPES_NS}"' in content_types

    assert f'xmlns="{RELATIONSHIPS_NS}"' in relationships

    assert "ns0:Types" not in content_types
    assert "ns0:Relationships" not in relationships


def test_write_associates_component_with_its_color(
    tmp_path: Path,
) -> None:
    """
    A colored component references its own 3MF material resource.
    """

    path = tmp_path / "example.3mf"

    write(
        (
            Component(
                name="ridge",
                mesh=_mesh(),
                color=PaletteColor(
                    name="red",
                    rgb=(
                        220,
                        38,
                        38,
                    ),
                ),
            ),
        ),
        path,
    )

    model = _read_model(path)

    objects = model.findall(f".//{{{CORE_NS}}}object")

    materials = model.findall(f".//{{{CORE_NS}}}basematerials")

    assert len(objects) == 1
    assert len(materials) == 1

    assert objects[0].get("pid") == materials[0].get("id")
    assert objects[0].get("pindex") == "0"
