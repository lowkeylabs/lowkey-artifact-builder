"""
Tests for Shape physical-component packaging.
"""
# File: tests/model/shape/test_package.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
import shutil
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from unittest.mock import Mock, call

import pytest

from lowkey_artifact_builder.config import write_artifact_config
from lowkey_artifact_builder.engine import (
    StageContext,
    create_build_plan,
    create_build_plans,
    execute_build,
    execute_builds,
)
from lowkey_artifact_builder.engine.bootstrap import build_stage_registry
from lowkey_artifact_builder.formats.threemf import CORE_NS, load_stl
from lowkey_artifact_builder.model.models.shape import stages
from lowkey_artifact_builder.model.models.shape.stages import compose, extrude, package, structure

# =========================================================
# Helpers
# =========================================================


def _build_clean_bg_house_registered_artwork(
    project_root: Path,
) -> Path:
    """
    Build the real clean_bg_house fixture through registered Artwork vectorization.
    """

    fixture = Path(__file__).parents[2] / "assets" / "clean_bg_house.png"

    assert fixture.is_file()

    source = project_root / "clean_bg_house.png"

    shutil.copyfile(
        fixture,
        source,
    )

    (project_root / "workspace.toml").write_text(
        """
[parameters]
printer_colors = ["black", "brown", "gold", "silver", "cold-white"]
artwork_pixels = 973
artwork_min_island_area = 1
artwork_island_connectivity = 8
""".lstrip(),
        encoding="utf-8",
    )

    write_artifact_config(
        "clean_bg_house",
        {
            "model": "artwork",
            "source": "clean_bg_house.png",
            "artwork_size": 200.0,
        },
        project_root=project_root,
    )

    plan = create_build_plan(
        "clean_bg_house",
        project_root=project_root,
    )

    execute_build(
        plan,
    )

    return (
        project_root
        / "artifacts"
        / "clean_bg_house"
        / "artwork"
        / "default"
        / "30-vector"
        / "products.json"
    )


def _build_clean_bg_house_shape_components(
    project_root: Path,
) -> Path:
    """
    Produce the real clean_bg_house physical Artwork components for packaging.

    The Shape reproduces the reported regression case:

        polygon
        7 sides
        120 mm
        2 mm outer ridge
    """

    vector_manifest = _build_clean_bg_house_registered_artwork(
        project_root,
    )

    structure_path = project_root / "structure.svg"
    composition = project_root / "composition.svg"

    geometry = structure.create_polygon_geometry(
        number_of_sides=7,
        rotation=0.0,
    )

    document = structure.create_polygon_svg(
        geometry,
    )

    document.write(
        structure_path,
        encoding="unicode",
    )

    compose._compose_ridge(
        structure_path,
        composition,
        shape_size=120.0,
        ridge_width=2.0,
    )

    registered_artwork = compose.load_registered_artwork(
        vector_manifest,
    )

    transform = compose.fit_registered_artwork_to_shape(
        registered_artwork,
        composition=composition,
    )

    vector_data = json.loads(
        vector_manifest.read_text(
            encoding="utf-8",
        )
    )

    components: list[dict[str, object]] = []

    for product in vector_data["products"]:
        source = vector_manifest.parent / str(
            product["path"],
        )

        destination = project_root / source.name

        shutil.copyfile(
            source,
            destination,
        )

        components.append(
            {
                **product,
                "path": destination.name,
            }
        )

    artwork: dict[str, object] = {
        "registered_extent": {
            "width": registered_artwork.registered_extent.width,
            "height": registered_artwork.registered_extent.height,
        },
        "transform": {
            "scale": transform.scale,
            "translate_x": transform.translate_x,
            "translate_y": transform.translate_y,
        },
        "components": components,
    }

    output_directory = project_root / "extrude"

    output_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    extrude._render_artwork_components(
        artwork,
        project_root,
        output_directory,
        shape_size=120.0,
        shape_base_raise=2.0,
        shape_artwork_raise=1.0,
    )

    physical_components = tuple(
        sorted(
            output_directory.glob(
                "artwork-*.stl",
            )
        )
    )

    assert physical_components

    manifest_components = []

    for index, component in enumerate(
        physical_components,
        start=1,
    ):
        manifest_components.append(
            (
                f"artwork-{index}",
                component.name,
                f"test-color-{index}",
                (100 + index, 100 + index, 100 + index),
            )
        )

    manifest = output_directory / "products.json"

    _write_component_manifest(
        manifest,
        tuple(manifest_components),
    )

    return manifest


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


def _write_geometry_component_stl(
    path: Path,
    *,
    solid_name: str,
    vertices: tuple[
        tuple[float, float, float],
        tuple[float, float, float],
        tuple[float, float, float],
    ],
) -> None:
    """
    Write one triangular STL component with explicit physical coordinates.
    """

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    vertex_1, vertex_2, vertex_3 = vertices

    path.write_text(
        f"""solid {solid_name}
facet normal 0 0 1
    outer loop
        vertex {vertex_1[0]} {vertex_1[1]} {vertex_1[2]}
        vertex {vertex_2[0]} {vertex_2[1]} {vertex_2[2]}
        vertex {vertex_3[0]} {vertex_3[1]} {vertex_3[2]}
    endloop
endfacet
endsolid {solid_name}
""",
        encoding="utf-8",
    )


def _object_vertices(
    object_: ET.Element,
) -> tuple[
    tuple[float, float, float],
    ...,
]:
    """
    Return physical vertices stored directly in one packaged 3MF object.
    """

    vertices = object_.findall(
        f"./{{{CORE_NS}}}mesh/{{{CORE_NS}}}vertices/{{{CORE_NS}}}vertex",
    )

    result: list[
        tuple[
            float,
            float,
            float,
        ]
    ] = []

    for vertex in vertices:
        x = vertex.get("x")
        y = vertex.get("y")
        z = vertex.get("z")

        assert x is not None
        assert y is not None
        assert z is not None

        result.append(
            (
                float(x),
                float(y),
                float(z),
            )
        )

    return tuple(
        result,
    )


def _mesh_bounds(
    vertices: tuple[
        tuple[float, float, float],
        ...,
    ],
) -> tuple[
    float,
    float,
    float,
    float,
    float,
    float,
]:
    """
    Return min/max X, Y, and Z bounds for physical mesh vertices.
    """

    assert vertices

    xs = tuple(vertex[0] for vertex in vertices)
    ys = tuple(vertex[1] for vertex in vertices)
    zs = tuple(vertex[2] for vertex in vertices)

    return (
        min(xs),
        max(xs),
        min(ys),
        max(ys),
        min(zs),
        max(zs),
    )


def _write_component_manifest(
    path: Path,
    components: tuple[
        tuple[
            str,
            str,
            str,
            tuple[int, int, int],
        ],
        ...,
    ],
) -> None:
    """
    Write a representative Shape physical-component manifest.

    Component paths are relative to the manifest so packaging can discover
    physical manufacturing geometry without constructing artifact workspace
    paths.

    Semantic component colors are supplied by extrusion and must remain
    available to downstream packaging without re-resolving Shape color policy.
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
                        "color": {
                            "name": color_name,
                            "rgb": list(rgb),
                        },
                    }
                    for name, component_path, color_name, rgb in components
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
                "white",
                (255, 255, 255),
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
                "white",
                (255, 255, 255),
            ),
            (
                "ridge",
                "ridge.stl",
                "white",
                (255, 255, 255),
            ),
        ),
    )

    return manifest


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

    return ET.fromstring(data)


# =========================================================
# Package stage execution
# =========================================================


def test_package_stage_preserves_artwork_fill_component(
    tmp_path: Path,
) -> None:
    """
    Shape packaging preserves Artwork fill as an independent physical component.

    Artwork fill membership and semantic color identity are established by
    extrusion. Packaging carries that component into the final 3MF without
    merging it with the structural base or incorporated Artwork.
    """

    component_directory = tmp_path / "extrude"

    base = component_directory / "base.stl"
    artwork_fill = component_directory / "artwork-fill.stl"
    artwork_1 = component_directory / "artwork-1.stl"
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

    _write_component_stl(
        artwork_1,
        solid_name="artwork-1",
    )

    _write_component_manifest(
        manifest,
        (
            (
                "base",
                "base.stl",
                "test-white",
                (255, 255, 255),
            ),
            (
                "artwork-fill",
                "artwork-fill.stl",
                "test-blue",
                (0, 0, 255),
            ),
            (
                "artwork-1",
                "artwork-1.stl",
                "test-red",
                (255, 0, 0),
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

    model = _read_model(
        artifact,
    )

    objects = model.findall(
        f".//{{{CORE_NS}}}object",
    )

    materials = model.findall(
        f".//{{{CORE_NS}}}basematerials",
    )

    objects_by_name = {object_.get("name"): object_ for object_ in objects}

    materials_by_id = {material.get("id"): material for material in materials}

    assert set(objects_by_name) == {
        "example-base-test-white",
        "example-artwork-fill-test-blue",
        "example-artwork-1-test-red",
    }

    fill = objects_by_name["example-artwork-fill-test-blue"]

    material_id = fill.get(
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

    assert fill.get("id") != objects_by_name["example-base-test-white"].get("id")

    assert fill.get("id") != objects_by_name["example-artwork-1-test-red"].get("id")


def test_package_stage_preserves_component_mesh_geometry(
    tmp_path: Path,
) -> None:
    """
    Shape packaging preserves physical component geometry.

    Packaging is a representation boundary. It must not scale, translate,
    rotate, center, or otherwise reinterpret the physical mesh supplied by
    extrusion.
    """

    component_directory = tmp_path / "extrude"

    component = component_directory / "artwork-1.stl"
    manifest = component_directory / "products.json"
    artifact = tmp_path / "artifact.3mf"

    source_vertices = (
        (-37.25, -18.5, 2.0),
        (41.75, -11.25, 2.0),
        (7.5, 46.125, 3.25),
    )

    _write_geometry_component_stl(
        component,
        solid_name="artwork-1",
        vertices=source_vertices,
    )

    _write_component_manifest(
        manifest,
        (
            (
                "artwork-1",
                "artwork-1.stl",
                "test-red",
                (255, 0, 0),
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

    model = _read_model(
        artifact,
    )

    objects = model.findall(
        f".//{{{CORE_NS}}}object",
    )

    assert len(objects) == 1

    packaged_vertices = _object_vertices(
        objects[0],
    )

    assert len(packaged_vertices) == len(source_vertices)

    for packaged_vertex, source_vertex in zip(
        packaged_vertices,
        source_vertices,
        strict=True,
    ):
        assert packaged_vertex == pytest.approx(
            source_vertex,
        )

    assert _mesh_bounds(
        packaged_vertices,
    ) == pytest.approx(
        _mesh_bounds(source_vertices),
    )


def test_package_stage_preserves_relative_component_registration(
    tmp_path: Path,
) -> None:
    """
    Shape packaging preserves physical registration between components.

    Independently printable Artwork components may occupy different portions
    of the common physical coordinate system. Packaging must preserve those
    relative positions without independently centering or transforming them.
    """

    component_directory = tmp_path / "extrude"

    artwork_1 = component_directory / "artwork-1.stl"
    artwork_2 = component_directory / "artwork-2.stl"
    manifest = component_directory / "products.json"
    artifact = tmp_path / "artifact.3mf"

    artwork_1_vertices = (
        (-42.0, -31.0, 2.0),
        (-17.0, -29.0, 2.0),
        (-35.0, 8.0, 3.0),
    )

    artwork_2_vertices = (
        (14.0, -9.0, 2.0),
        (47.0, -4.0, 2.0),
        (32.0, 39.0, 3.0),
    )

    _write_geometry_component_stl(
        artwork_1,
        solid_name="artwork-1",
        vertices=artwork_1_vertices,
    )

    _write_geometry_component_stl(
        artwork_2,
        solid_name="artwork-2",
        vertices=artwork_2_vertices,
    )

    _write_component_manifest(
        manifest,
        (
            (
                "artwork-1",
                "artwork-1.stl",
                "test-red",
                (255, 0, 0),
            ),
            (
                "artwork-2",
                "artwork-2.stl",
                "test-blue",
                (0, 0, 255),
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

    model = _read_model(
        artifact,
    )

    objects = model.findall(
        f".//{{{CORE_NS}}}object",
    )

    objects_by_name = {object_.get("name"): object_ for object_ in objects}

    packaged_artwork_1 = _object_vertices(
        objects_by_name["example-artwork-1-test-red"],
    )

    packaged_artwork_2 = _object_vertices(
        objects_by_name["example-artwork-2-test-blue"],
    )

    assert _mesh_bounds(
        packaged_artwork_1,
    ) == pytest.approx(
        _mesh_bounds(artwork_1_vertices),
    )

    assert _mesh_bounds(
        packaged_artwork_2,
    ) == pytest.approx(
        _mesh_bounds(artwork_2_vertices),
    )

    source_1_bounds = _mesh_bounds(
        artwork_1_vertices,
    )
    source_2_bounds = _mesh_bounds(
        artwork_2_vertices,
    )

    packaged_1_bounds = _mesh_bounds(
        packaged_artwork_1,
    )
    packaged_2_bounds = _mesh_bounds(
        packaged_artwork_2,
    )

    source_center_delta = (
        (source_2_bounds[0] + source_2_bounds[1]) / 2.0
        - (source_1_bounds[0] + source_1_bounds[1]) / 2.0,
        (source_2_bounds[2] + source_2_bounds[3]) / 2.0
        - (source_1_bounds[2] + source_1_bounds[3]) / 2.0,
    )

    packaged_center_delta = (
        (packaged_2_bounds[0] + packaged_2_bounds[1]) / 2.0
        - (packaged_1_bounds[0] + packaged_1_bounds[1]) / 2.0,
        (packaged_2_bounds[2] + packaged_2_bounds[3]) / 2.0
        - (packaged_1_bounds[2] + packaged_1_bounds[3]) / 2.0,
    )

    assert packaged_center_delta == pytest.approx(
        source_center_delta,
    )


def test_package_stage_packages_incorporated_artwork_components(
    tmp_path: Path,
) -> None:
    """
    Shape packaging preserves incorporated Artwork component membership.

    Artwork dimensionalization determines the physical components upstream.
    Packaging includes every component declared by the extrusion manifest
    without rediscovering Artwork structure or applying Artwork policy.
    """

    component_directory = tmp_path / "extrude"

    base = component_directory / "base.stl"
    artwork_1 = component_directory / "artwork-1.stl"
    artwork_2 = component_directory / "artwork-2.stl"
    manifest = component_directory / "products.json"
    artifact = tmp_path / "artifact.3mf"

    _write_component_stl(
        base,
        solid_name="shape-base",
    )

    _write_component_stl(
        artwork_1,
        solid_name="artwork-1",
    )

    _write_component_stl(
        artwork_2,
        solid_name="artwork-2",
    )

    _write_component_manifest(
        manifest,
        (
            (
                "base",
                "base.stl",
                "test-white",
                (255, 255, 255),
            ),
            (
                "artwork-1",
                "artwork-1.stl",
                "test-red",
                (255, 0, 0),
            ),
            (
                "artwork-2",
                "artwork-2.stl",
                "test-blue",
                (0, 0, 255),
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

    model = _read_model(
        artifact,
    )

    objects = model.findall(
        f".//{{{CORE_NS}}}object",
    )

    assert [object_.get("name") for object_ in objects] == [
        "example-base-test-white",
        "example-artwork-1-test-red",
        "example-artwork-2-test-blue",
    ]


def test_package_stage_preserves_incorporated_artwork_colors(
    tmp_path: Path,
) -> None:
    """
    Shape packaging preserves incorporated Artwork semantic color identity.

    Artwork colors are supplied by dimensionalization metadata and survive
    packaging without being re-resolved or assigned to physical printer heads.
    """

    component_directory = tmp_path / "extrude"

    base = component_directory / "base.stl"
    artwork_1 = component_directory / "artwork-1.stl"
    artwork_2 = component_directory / "artwork-2.stl"
    manifest = component_directory / "products.json"
    artifact = tmp_path / "artifact.3mf"

    _write_component_stl(
        base,
        solid_name="shape-base",
    )

    _write_component_stl(
        artwork_1,
        solid_name="artwork-1",
    )

    _write_component_stl(
        artwork_2,
        solid_name="artwork-2",
    )

    _write_component_manifest(
        manifest,
        (
            (
                "base",
                "base.stl",
                "test-white",
                (255, 255, 255),
            ),
            (
                "artwork-1",
                "artwork-1.stl",
                "test-red",
                (255, 0, 0),
            ),
            (
                "artwork-2",
                "artwork-2.stl",
                "test-blue",
                (0, 0, 255),
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

    model = _read_model(
        artifact,
    )

    objects = model.findall(
        f".//{{{CORE_NS}}}object",
    )

    materials = model.findall(
        f".//{{{CORE_NS}}}basematerials",
    )

    objects_by_name = {object_.get("name"): object_ for object_ in objects}

    materials_by_id = {material.get("id"): material for material in materials}

    expected_colors = {
        "example-base-test-white": (
            "test-white",
            "#FFFFFF",
        ),
        "example-artwork-1-test-red": (
            "test-red",
            "#FF0000",
        ),
        "example-artwork-2-test-blue": (
            "test-blue",
            "#0000FF",
        ),
    }

    assert set(objects_by_name) == set(expected_colors)

    for object_name, expected_color in expected_colors.items():
        object_ = objects_by_name[object_name]

        material_id = object_.get(
            "pid",
        )

        assert material_id is not None

        material = materials_by_id[material_id]

        color = material.find(
            f"{{{CORE_NS}}}base",
        )

        assert color is not None
        assert (
            color.get("name"),
            color.get("displaycolor"),
        ) == expected_color


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

    assert "example-base-white" in model
    assert "example-ridge-white" not in model


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

    assert "example-base-white" in model
    assert "example-ridge-white" in model


def test_package_stage_names_components_with_semantic_color_identity(
    tmp_path: Path,
) -> None:
    """
    Packaged Shape components expose semantic role and printing-color identity.

    Object naming combines artifact identity, the component role declared by
    the manifest, and semantic printing color without depending on physical
    STL filenames.
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
                "test-white",
                (255, 255, 255),
            ),
            (
                "ridge",
                "arbitrary-ridge-name.stl",
                "test-red",
                (255, 0, 0),
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

    model = _read_model(
        artifact,
    )

    objects = model.findall(
        f".//{{{CORE_NS}}}object",
    )

    assert [object_.get("name") for object_ in objects] == [
        "example-base-test-white",
        "example-ridge-test-red",
    ]

    assert all("arbitrary-base-name" not in (object_.get("name") or "") for object_ in objects)

    assert all("arbitrary-ridge-name" not in (object_.get("name") or "") for object_ in objects)


def test_package_stage_preserves_base_component_color(
    tmp_path: Path,
) -> None:
    """
    Shape packaging preserves base color identity supplied by extrusion.

    Packaging consumes component metadata rather than independently resolving
    Shape color policy.
    """

    component_directory = tmp_path / "extrude"

    base = component_directory / "base.stl"
    manifest = component_directory / "products.json"
    artifact = tmp_path / "artifact.3mf"

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
                "test-red",
                (255, 0, 0),
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
    assert objects[0].get("name") == "example-base-test-red"

    assert len(materials) == 1

    base_color = materials[0].find(
        f"{{{CORE_NS}}}base",
    )

    assert base_color is not None
    assert base_color.get("name") == "test-red"
    assert base_color.get("displaycolor") == "#FF0000"

    assert objects[0].get("pid") == materials[0].get("id")
    assert objects[0].get("pindex") == "0"


def test_package_stage_preserves_distinct_component_colors(
    tmp_path: Path,
) -> None:
    """
    Shape packaging preserves independent base and ridge color identities.

    Each independently printable component retains the semantic color supplied
    by extrusion without packaging assigning either component to a physical
    printer head.
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

    _write_component_manifest(
        manifest,
        (
            (
                "base",
                "base.stl",
                "test-white",
                (255, 255, 255),
            ),
            (
                "ridge",
                "ridge.stl",
                "test-red",
                (255, 0, 0),
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

    model = _read_model(
        artifact,
    )

    objects = model.findall(
        f".//{{{CORE_NS}}}object",
    )

    materials = model.findall(
        f".//{{{CORE_NS}}}basematerials",
    )

    assert [object_.get("name") for object_ in objects] == [
        "example-base-test-white",
        "example-ridge-test-red",
    ]

    colors = {
        material.get("id"): material.find(
            f"{{{CORE_NS}}}base",
        )
        for material in materials
    }

    base_color = colors[objects[0].get("pid")]
    ridge_color = colors[objects[1].get("pid")]

    assert base_color is not None
    assert base_color.get("name") == "test-white"
    assert base_color.get("displaycolor") == "#FFFFFF"

    assert ridge_color is not None
    assert ridge_color.get("name") == "test-red"
    assert ridge_color.get("displaycolor") == "#FF0000"


def test_package_stage_does_not_resolve_geometry_parameters(
    tmp_path: Path,
) -> None:
    """
    Shape packaging does not construct, dimensionalize, or recolor geometry.

    Physical Shape parameters and semantic component colors belong to upstream
    production stages. Packaging consumes only the physical-component manifest
    and the components it describes.
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
                "white",
                (255, 255, 255),
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


def test_package_stage_preserves_shared_component_color(
    tmp_path: Path,
) -> None:
    """
    Independently printable Shape components may share one semantic color.

    Equal colors do not collapse component identity or alter component
    membership during packaging.
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

    _write_component_manifest(
        manifest,
        (
            (
                "base",
                "base.stl",
                "test-red",
                (255, 0, 0),
            ),
            (
                "ridge",
                "ridge.stl",
                "test-red",
                (255, 0, 0),
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

    model = _read_model(
        artifact,
    )

    objects = model.findall(
        f".//{{{CORE_NS}}}object",
    )

    materials = model.findall(
        f".//{{{CORE_NS}}}basematerials",
    )

    assert [object_.get("name") for object_ in objects] == [
        "example-base-test-red",
        "example-ridge-test-red",
    ]

    assert len(materials) == 2

    for object_ in objects:
        material_id = object_.get("pid")

        material = next(material for material in materials if material.get("id") == material_id)

        color = material.find(
            f"{{{CORE_NS}}}base",
        )

        assert color is not None
        assert color.get("name") == "test-red"
        assert color.get("displaycolor") == "#FF0000"


@pytest.mark.parametrize(
    "color",
    [
        None,
        {},
        {
            "name": "",
            "rgb": [255, 255, 255],
        },
        {
            "name": "white",
            "rgb": None,
        },
        {
            "name": "white",
            "rgb": [255, 255],
        },
        {
            "name": "white",
            "rgb": [255, 255, 256],
        },
    ],
)
def test_package_stage_rejects_invalid_component_color_metadata(
    tmp_path: Path,
    color: object,
) -> None:
    """
    Packaging requires resolved semantic color metadata from extrusion.

    Invalid or absent metadata is not repaired by resolving Shape color
    configuration again.
    """

    component_directory = tmp_path / "extrude"

    base = component_directory / "base.stl"
    manifest = component_directory / "products.json"
    artifact = tmp_path / "artifact.3mf"

    _write_component_stl(
        base,
        solid_name="shape-base",
    )

    manifest.write_text(
        json.dumps(
            {
                "components": [
                    {
                        "name": "base",
                        "path": "base.stl",
                        "color": color,
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    resolver = Mock()

    context = Mock(
        spec=StageContext,
    )
    context.artifact_id = "example"
    context.resolver = resolver
    context.input.return_value = manifest
    context.output.return_value = artifact

    with pytest.raises(
        package.PackageError,
        match="color",
    ):
        package.execute(
            context,
        )

    resolver.assert_not_called()

    assert not artifact.exists()


def test_package_stage_preserves_mixed_structural_and_artwork_components(
    tmp_path: Path,
) -> None:
    """
    Shape packaging preserves the complete physical component partition.

    Structural and incorporated Artwork components remain independently
    printable even when components from different semantic roles share the
    same semantic color.
    """

    component_directory = tmp_path / "extrude"

    base = component_directory / "base.stl"
    ridge = component_directory / "ridge.stl"
    artwork_1 = component_directory / "artwork-1.stl"
    artwork_2 = component_directory / "artwork-2.stl"
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
        artwork_1,
        solid_name="artwork-1",
    )

    _write_component_stl(
        artwork_2,
        solid_name="artwork-2",
    )

    _write_component_manifest(
        manifest,
        (
            (
                "base",
                "base.stl",
                "test-white",
                (255, 255, 255),
            ),
            (
                "ridge",
                "ridge.stl",
                "test-red",
                (255, 0, 0),
            ),
            (
                "artwork-1",
                "artwork-1.stl",
                "test-red",
                (255, 0, 0),
            ),
            (
                "artwork-2",
                "artwork-2.stl",
                "test-blue",
                (0, 0, 255),
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

    model = _read_model(
        artifact,
    )

    objects = model.findall(
        f".//{{{CORE_NS}}}object",
    )

    materials = model.findall(
        f".//{{{CORE_NS}}}basematerials",
    )

    objects_by_name = {object_.get("name"): object_ for object_ in objects}

    materials_by_id = {material.get("id"): material for material in materials}

    assert set(objects_by_name) == {
        "example-base-test-white",
        "example-ridge-test-red",
        "example-artwork-1-test-red",
        "example-artwork-2-test-blue",
    }

    expected_colors = {
        "example-base-test-white": (
            "test-white",
            "#FFFFFF",
        ),
        "example-ridge-test-red": (
            "test-red",
            "#FF0000",
        ),
        "example-artwork-1-test-red": (
            "test-red",
            "#FF0000",
        ),
        "example-artwork-2-test-blue": (
            "test-blue",
            "#0000FF",
        ),
    }

    for object_name, expected_color in expected_colors.items():
        object_ = objects_by_name[object_name]

        material_id = object_.get(
            "pid",
        )

        assert material_id is not None

        material = materials_by_id[material_id]

        color = material.find(
            f"{{{CORE_NS}}}base",
        )

        assert color is not None
        assert (
            color.get("name"),
            color.get("displaycolor"),
        ) == expected_color

    assert objects_by_name["example-ridge-test-red"].get("id") != objects_by_name[
        "example-artwork-1-test-red"
    ].get("id")


@pytest.mark.slow
def test_real_clean_bg_house_package_preserves_artwork_physical_geometry(
    tmp_path: Path,
) -> None:
    """
    Shape packaging preserves the real clean_bg_house physical Artwork geometry.

    The real registered Artwork is composed into the reported 120 mm
    seven-sided Shape with a 2 mm outer ridge and physically dimensionalized
    before packaging.

    Packaging must preserve the union bounds and center of those physical
    Artwork components exactly. It must not independently scale, translate,
    center, crop, or otherwise reinterpret the geometry.
    """

    manifest = _build_clean_bg_house_shape_components(
        tmp_path,
    )

    source_components = tuple(
        sorted(
            manifest.parent.glob(
                "artwork-*.stl",
            )
        )
    )

    assert source_components

    source_bounds = tuple(
        _mesh_bounds(
            tuple(
                load_stl(component).vertices,
            )
        )
        for component in source_components
    )

    source_union = (
        min(bounds[0] for bounds in source_bounds),
        max(bounds[1] for bounds in source_bounds),
        min(bounds[2] for bounds in source_bounds),
        max(bounds[3] for bounds in source_bounds),
        min(bounds[4] for bounds in source_bounds),
        max(bounds[5] for bounds in source_bounds),
    )

    artifact = tmp_path / "artifact.3mf"

    context = Mock(
        spec=StageContext,
    )
    context.artifact_id = "clean_bg_house_shape"
    context.input.return_value = manifest
    context.output.return_value = artifact

    package.execute(
        context,
    )

    model = _read_model(
        artifact,
    )

    artwork_objects = tuple(
        object_
        for object_ in model.findall(
            f".//{{{CORE_NS}}}object",
        )
        if "-artwork-" in (object_.get("name") or "")
    )

    assert len(artwork_objects) == len(source_components)

    packaged_bounds = tuple(
        _mesh_bounds(
            _object_vertices(
                object_,
            )
        )
        for object_ in artwork_objects
    )

    packaged_union = (
        min(bounds[0] for bounds in packaged_bounds),
        max(bounds[1] for bounds in packaged_bounds),
        min(bounds[2] for bounds in packaged_bounds),
        max(bounds[3] for bounds in packaged_bounds),
        min(bounds[4] for bounds in packaged_bounds),
        max(bounds[5] for bounds in packaged_bounds),
    )

    assert packaged_union == pytest.approx(
        source_union,
        abs=1e-5,
    )

    source_center = (
        (source_union[0] + source_union[1]) / 2.0,
        (source_union[2] + source_union[3]) / 2.0,
    )

    packaged_center = (
        (packaged_union[0] + packaged_union[1]) / 2.0,
        (packaged_union[2] + packaged_union[3]) / 2.0,
    )

    assert packaged_center == pytest.approx(
        source_center,
        abs=1e-5,
    )


@pytest.mark.slow
def test_real_clean_bg_house_end_to_end_shape_compose_contains_registered_artwork(
    tmp_path: Path,
) -> None:
    """
    A normal Shape build persists its bound registered Artwork in composition.

    The configured Shape consumes the real clean_bg_house Artwork vector manifest.
    Normal dependency planning and execution must therefore carry that
    registered Artwork into the persistent Shape composition manifest.
    """

    fixture = Path(__file__).parents[2] / "assets" / "clean_bg_house.png"

    assert fixture.is_file()

    source = tmp_path / "clean_bg_house.png"

    shutil.copyfile(
        fixture,
        source,
    )

    (tmp_path / "workspace.toml").write_text(
        """
[parameters]
printer_colors = ["black", "brown", "gold", "silver", "cold-white"]
artwork_pixels = 973
artwork_min_island_area = 1
artwork_island_connectivity = 8
""".lstrip(),
        encoding="utf-8",
    )

    write_artifact_config(
        "clean_bg_house",
        {
            "model": "artwork",
            "source": "clean_bg_house.png",
            "artwork_size": 200.0,
        },
        project_root=tmp_path,
    )

    write_artifact_config(
        "clean_bg_house_shape",
        {
            "model": "shape",
            "shape_geometry": "polygon",
            "shape_sides": 7,
            "shape_size": 120.0,
            "shape_base_color": "white",
            "shape_outer_ridge_width": 2.0,
            "product_dependencies": {
                "manifest": {
                    "artifact": "clean_bg_house",
                    "model": "artwork",
                    "realization": "default",
                    "stage": "vector",
                    "product": "manifest",
                },
            },
        },
        project_root=tmp_path,
    )

    plans = create_build_plans(
        "clean_bg_house_shape",
        project_root=tmp_path,
    )

    execute_builds(
        plans,
    )

    compose_manifest = (
        tmp_path
        / "artifacts"
        / "clean_bg_house_shape"
        / "shape"
        / "default"
        / "20-compose"
        / "products.json"
    )

    assert compose_manifest.is_file()

    data = json.loads(
        compose_manifest.read_text(
            encoding="utf-8",
        )
    )

    artwork = data["artwork"]

    assert artwork is not None

    assert artwork["components"]

    assert artwork["registered_extent"]["width"] > 0.0
    assert artwork["registered_extent"]["height"] > 0.0

    transform = artwork["transform"]

    assert transform["scale"] > 0.0


@pytest.mark.slow
def test_real_clean_bg_house_end_to_end_shape_extrude_contains_artwork_components(
    tmp_path: Path,
) -> None:
    """
    A normal Shape build propagates incorporated Artwork into extrusion.

    The configured Shape consumes the real clean_bg_house registered Artwork
    manifest. Normal dependency planning and execution must therefore produce
    physical Artwork components in the Shape extrusion manifest before
    packaging begins.
    """

    fixture = Path(__file__).parents[2] / "assets" / "clean_bg_house.png"

    assert fixture.is_file()

    source = tmp_path / "clean_bg_house.png"

    shutil.copyfile(
        fixture,
        source,
    )

    (tmp_path / "workspace.toml").write_text(
        """
[parameters]
printer_colors = ["black", "brown", "gold", "silver", "cold-white"]
artwork_pixels = 973
artwork_min_island_area = 1
artwork_island_connectivity = 8
""".lstrip(),
        encoding="utf-8",
    )

    write_artifact_config(
        "clean_bg_house",
        {
            "model": "artwork",
            "source": "clean_bg_house.png",
            "artwork_size": 200.0,
        },
        project_root=tmp_path,
    )

    write_artifact_config(
        "clean_bg_house_shape",
        {
            "model": "shape",
            "shape_geometry": "polygon",
            "shape_sides": 7,
            "shape_size": 120.0,
            "shape_base_color": "white",
            "shape_outer_ridge_width": 2.0,
            "product_dependencies": {
                "manifest": {
                    "artifact": "clean_bg_house",
                    "model": "artwork",
                    "realization": "default",
                    "stage": "vector",
                    "product": "manifest",
                },
            },
        },
        project_root=tmp_path,
    )

    plans = create_build_plans(
        "clean_bg_house_shape",
        project_root=tmp_path,
    )

    execute_builds(
        plans,
    )

    extrude_manifest = (
        tmp_path
        / "artifacts"
        / "clean_bg_house_shape"
        / "shape"
        / "default"
        / "30-extrude"
        / "products.json"
    )

    assert extrude_manifest.is_file()

    data = json.loads(
        extrude_manifest.read_text(
            encoding="utf-8",
        )
    )

    components = data["components"]

    artwork_components = tuple(
        component
        for component in components
        if str(component["name"]).startswith(
            "artwork-",
        )
    )

    assert artwork_components

    for component in artwork_components:
        path = extrude_manifest.parent / str(
            component["path"],
        )

        assert path.is_file()


def test_package_stage_does_not_invent_disabled_artwork_fill(
    tmp_path: Path,
) -> None:
    """
    Shape packaging does not invent an Artwork fill component.

    Artwork-fill existence is established upstream. When extrusion declares
    structural and incorporated Artwork components without Artwork fill,
    packaging preserves that component membership without re-resolving Shape
    fill policy.
    """

    component_directory = tmp_path / "extrude"

    base = component_directory / "base.stl"
    artwork_1 = component_directory / "artwork-1.stl"
    manifest = component_directory / "products.json"
    artifact = tmp_path / "artifact.3mf"

    _write_component_stl(
        base,
        solid_name="shape-base",
    )

    _write_component_stl(
        artwork_1,
        solid_name="artwork-1",
    )

    _write_component_manifest(
        manifest,
        (
            (
                "base",
                "base.stl",
                "test-white",
                (255, 255, 255),
            ),
            (
                "artwork-1",
                "artwork-1.stl",
                "test-red",
                (255, 0, 0),
            ),
        ),
    )

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

    model = _read_model(
        artifact,
    )

    objects = model.findall(
        f".//{{{CORE_NS}}}object",
    )

    assert {object_.get("name") for object_ in objects} == {
        "example-base-test-white",
        "example-artwork-1-test-red",
    }

    resolver.assert_not_called()


def test_package_stage_preserves_same_color_artwork_fill_identity(
    tmp_path: Path,
) -> None:
    """
    Shared semantic color does not merge Shape physical components.

    Structural base, Artwork fill, and incorporated Artwork remain
    independently identifiable packaged components even when all three
    use the same semantic printing color.
    """

    component_directory = tmp_path / "extrude"

    base = component_directory / "base.stl"
    artwork_fill = component_directory / "artwork-fill.stl"
    artwork_1 = component_directory / "artwork-1.stl"
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

    _write_component_stl(
        artwork_1,
        solid_name="artwork-1",
    )

    _write_component_manifest(
        manifest,
        (
            (
                "base",
                "base.stl",
                "test-blue",
                (0, 0, 255),
            ),
            (
                "artwork-fill",
                "artwork-fill.stl",
                "test-blue",
                (0, 0, 255),
            ),
            (
                "artwork-1",
                "artwork-1.stl",
                "test-blue",
                (0, 0, 255),
            ),
        ),
    )

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

    model = _read_model(
        artifact,
    )

    objects = model.findall(
        f".//{{{CORE_NS}}}object",
    )

    materials = model.findall(
        f".//{{{CORE_NS}}}basematerials",
    )

    objects_by_name = {object_.get("name"): object_ for object_ in objects}

    materials_by_id = {material.get("id"): material for material in materials}

    assert set(objects_by_name) == {
        "example-base-test-blue",
        "example-artwork-fill-test-blue",
        "example-artwork-1-test-blue",
    }

    assert len({objects_by_name[name].get("id") for name in objects_by_name}) == 3

    for object_ in objects_by_name.values():
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

    resolver.assert_not_called()
