"""
End-to-end regression tests for the artwork model.

These tests exercise the complete artwork model through the public build
planner and execution engine.

The purpose is to verify that the migrated artwork pipeline operates
through the canonical product hierarchy while preserving the complete
prepare -> raster -> vector -> extrude -> package transformation.
"""
# File: tests/model/artwork/test_pipeline.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
import shutil
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Any

import pytest
from PIL import Image

from lowkey_artifact_builder.config import write_artifact_config
from lowkey_artifact_builder.engine import (
    create_build_plan,
    execute_build,
)
from lowkey_artifact_builder.formats.threemf import (
    CORE_NS,
    load_stl,
)

# Mark all tests in this suite as slow

pytestmark = pytest.mark.slow


# =========================================================
# Test support
# =========================================================


def _build_clean_bg_house_artwork(
    project_root: Path,
) -> Path:
    """
    Build the real clean_bg_house Artwork fixture.

    The fixture reproduces the registered Artwork consumed by Shape in the
    regression case under investigation. Its physical artwork_size matches
    the real artifact configuration, although registered vector Artwork
    remains dimension-independent.
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
artwork_colors = ["black", "brown", "gold", "silver", "cold-white"]
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

    return project_root / "artifacts" / "clean_bg_house" / "artwork" / "default"


def _svg_occupied_bounds(
    path: Path,
) -> tuple[
    float,
    float,
    float,
    float,
]:
    """
    Return occupied X/Y bounds of linear SVG path geometry.

    Bounds are derived from path coordinates rather than from the SVG document
    extent. The Artwork vector products may use absolute or relative move,
    line, horizontal-line, and vertical-line commands.
    """

    root = ET.parse(
        path,
    ).getroot()

    points: list[
        tuple[
            float,
            float,
        ]
    ] = []

    command_letters = set(
        "MmLlHhVvZz",
    )

    for element in root.iter():
        if (
            element.tag.rsplit(
                "}",
                maxsplit=1,
            )[-1]
            != "path"
        ):
            continue

        data = element.get(
            "d",
            "",
        )

        for command in command_letters:
            data = data.replace(
                command,
                f" {command} ",
            )

        tokens = data.replace(
            ",",
            " ",
        ).split()

        index = 0
        command: str | None = None

        current_x = 0.0
        current_y = 0.0

        subpath_x = 0.0
        subpath_y = 0.0

        while index < len(tokens):
            token = tokens[index]

            if token in command_letters:
                command = token
                index += 1

                if command in {
                    "Z",
                    "z",
                }:
                    current_x = subpath_x
                    current_y = subpath_y

                    points.append(
                        (
                            current_x,
                            current_y,
                        )
                    )

                    command = None

                continue

            if command is None:
                raise AssertionError(
                    f"clean_bg_house regression fixture contains unexpected SVG path token: {token!r}"
                )

            if command in {
                "M",
                "m",
                "L",
                "l",
            }:
                if index + 1 >= len(tokens):
                    raise AssertionError(
                        f"Incomplete SVG path command in {path}",
                    )

                x = float(
                    tokens[index],
                )
                y = float(
                    tokens[index + 1],
                )

                if command.islower():
                    x += current_x
                    y += current_y

                current_x = x
                current_y = y

                points.append(
                    (
                        current_x,
                        current_y,
                    )
                )

                if command in {
                    "M",
                    "m",
                }:
                    subpath_x = current_x
                    subpath_y = current_y

                    command = "L" if command == "M" else "l"

                index += 2
                continue

            if command in {
                "H",
                "h",
            }:
                x = float(
                    tokens[index],
                )

                if command == "h":
                    x += current_x

                current_x = x

                points.append(
                    (
                        current_x,
                        current_y,
                    )
                )

                index += 1
                continue

            if command in {
                "V",
                "v",
            }:
                y = float(
                    tokens[index],
                )

                if command == "v":
                    y += current_y

                current_y = y

                points.append(
                    (
                        current_x,
                        current_y,
                    )
                )

                index += 1
                continue

            raise AssertionError(
                f"clean_bg_house regression fixture contains unsupported SVG path command: {command!r}"
            )

    assert points, f"SVG contains no supported occupied path geometry: {path}"

    xs = tuple(x for x, _y in points)

    ys = tuple(y for _x, y in points)

    return (
        min(xs),
        max(xs),
        min(ys),
        max(ys),
    )


def _write_workspace(
    project_root: Path,
) -> None:
    """
    Write workspace overrides required by the artwork integration test.

    Workspace configuration participates in the normal parameter
    resolution hierarchy through its [parameters] table.
    """

    (project_root / "workspace.toml").write_text(
        """
[parameters]
printer_colors = ["test-white", "test-red"]
artifact_color_count = 2
artwork_pixels = 64
artwork_size = 20.0
artwork_min_island_area = 1
artwork_island_connectivity = 8
artwork_raise = 1.0
""".lstrip(),
        encoding="utf-8",
    )


def _write_source(
    path: Path,
) -> None:
    """
    Write deterministic two-color source artwork.

    The image is intentionally small and geometrically simple so that
    the integration test exercises the real artwork tools without
    introducing unnecessary processing cost.
    """

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    image = Image.new(
        "RGBA",
        (64, 64),
        (
            0,
            0,
            0,
            0,
        ),
    )

    try:
        pixels = image.load()

        assert pixels is not None

        for y in range(8, 56):
            for x in range(8, 56):
                pixels[x, y] = (
                    255,
                    255,
                    255,
                    255,
                )

        for y in range(20, 44):
            for x in range(20, 44):
                pixels[x, y] = (
                    0,
                    0,
                    0,
                    255,
                )

        image.save(
            path,
            format="PNG",
        )

    finally:
        image.close()


def _read_manifest(
    path: Path,
) -> dict[str, Any]:
    """
    Read one artwork dynamic-product manifest.
    """

    data = json.loads(
        path.read_text(
            encoding="utf-8",
        )
    )

    assert isinstance(
        data,
        dict,
    )

    return data


def _build_artwork(
    project_root: Path,
) -> Path:
    """
    Build the deterministic artwork fixture and return its realization
    directory.
    """

    _write_workspace(project_root)

    source = project_root / "source.png"

    _write_source(source)

    write_artifact_config(
        "example",
        {
            "model": "artwork",
            "source": "source.png",
        },
        project_root=project_root,
    )

    plan = create_build_plan(
        "example",
        project_root=project_root,
    )

    execute_build(plan)

    return project_root / "artifacts" / "example" / "artwork" / "default"


def _manifest_products(
    manifest: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    Return the dynamic products from a stage manifest.
    """

    products = manifest["products"]

    assert isinstance(
        products,
        list,
    )

    assert all(isinstance(product, dict) for product in products)

    return products


def _assert_raster_has_geometry(
    path: Path,
) -> None:
    """
    Verify that a raster product contains visible geometry.
    """

    with Image.open(path) as image:
        rgba = image.convert("RGBA")

        try:
            alpha = rgba.getchannel("A")

            assert alpha.getbbox() is not None

        finally:
            rgba.close()


def _assert_svg_has_geometry(
    path: Path,
) -> None:
    """
    Verify that an SVG product contains vector geometry.
    """

    root = ET.parse(path).getroot()

    geometry_tags = {
        "path",
        "rect",
        "circle",
        "ellipse",
        "line",
        "polyline",
        "polygon",
    }

    geometry = tuple(
        element
        for element in root.iter()
        if element.tag.rsplit(
            "}",
            maxsplit=1,
        )[-1]
        in geometry_tags
    )

    assert geometry


def _read_3mf_model(
    path: Path,
) -> ET.Element:
    """
    Read the primary model document from a 3MF package.
    """

    with zipfile.ZipFile(
        path,
        mode="r",
    ) as package:
        members = set(package.namelist())

        assert "[Content_Types].xml" in members
        assert "_rels/.rels" in members
        assert "3D/3dmodel.model" in members

        model_data = package.read("3D/3dmodel.model")

    return ET.fromstring(model_data)


# =========================================================
# Complete artwork pipeline
# =========================================================


def test_artwork_pipeline_produces_canonical_products(
    tmp_path: Path,
) -> None:
    """
    A complete artwork build produces every declared and dynamic product
    beneath the canonical model/realization/stage hierarchy.

    This is the Phase 4 regression boundary for the migrated artwork
    model. It deliberately enters through create_build_plan() and
    execute_build() rather than invoking stage implementations directly.
    """

    realization = _build_artwork(
        tmp_path,
    )

    prepare_directory = realization / "10-prepare"
    raster_directory = realization / "20-raster"
    vector_directory = realization / "30-vector"
    extrude_directory = realization / "40-extrude"
    package_directory = realization / "50-package"

    # -----------------------------------------------------
    # Prepare
    # -----------------------------------------------------

    trace = prepare_directory / "trace.svg"
    envelope = prepare_directory / "envelope.svg"

    assert trace.is_file()
    assert envelope.is_file()

    # -----------------------------------------------------
    # Raster
    # -----------------------------------------------------

    raster_manifest_path = raster_directory / "products.json"

    assert raster_manifest_path.is_file()

    raster_manifest = _read_manifest(
        raster_manifest_path,
    )

    raster_products = _manifest_products(
        raster_manifest,
    )

    assert raster_products

    raster_paths = tuple(raster_directory / product["path"] for product in raster_products)

    assert all(path.is_file() for path in raster_paths)

    assert all(path.parent == raster_directory for path in raster_paths)

    assert all(path.suffix == ".png" for path in raster_paths)

    # -----------------------------------------------------
    # Vector
    # -----------------------------------------------------

    vector_manifest_path = vector_directory / "products.json"

    assert vector_manifest_path.is_file()

    vector_manifest = _read_manifest(
        vector_manifest_path,
    )

    vector_products = _manifest_products(
        vector_manifest,
    )

    assert vector_products

    vector_paths = tuple(vector_directory / product["path"] for product in vector_products)

    assert all(path.is_file() for path in vector_paths)

    assert all(path.parent == vector_directory for path in vector_paths)

    assert all(path.suffix == ".svg" for path in vector_paths)

    # -----------------------------------------------------
    # Extrude
    # -----------------------------------------------------

    extrude_manifest_path = extrude_directory / "products.json"

    assert extrude_manifest_path.is_file()

    extrude_manifest = _read_manifest(
        extrude_manifest_path,
    )

    extrude_products = _manifest_products(
        extrude_manifest,
    )

    assert extrude_products

    extrude_paths = tuple(extrude_directory / product["path"] for product in extrude_products)

    assert all(path.is_file() for path in extrude_paths)

    assert all(path.parent == extrude_directory for path in extrude_paths)

    assert all(path.suffix == ".stl" for path in extrude_paths)

    # -----------------------------------------------------
    # Package
    # -----------------------------------------------------

    artifact = package_directory / "artifact.3mf"

    assert artifact.is_file()
    assert artifact.stat().st_size > 0


def test_artwork_pipeline_preserves_dynamic_product_identity(
    tmp_path: Path,
) -> None:
    """
    Dynamic artwork products preserve their semantic identity through
    rasterization, vectorization, and extrusion.

    Each downstream manifest must describe the same ordered collection
    of color products rather than rediscovering products from the
    filesystem.
    """

    realization = _build_artwork(
        tmp_path,
    )

    raster = _read_manifest(realization / "20-raster" / "products.json")

    vector = _read_manifest(realization / "30-vector" / "products.json")

    extrude = _read_manifest(realization / "40-extrude" / "products.json")

    raster_products = _manifest_products(
        raster,
    )

    vector_products = _manifest_products(
        vector,
    )

    extrude_products = _manifest_products(
        extrude,
    )

    assert len(raster_products) == len(vector_products)
    assert len(vector_products) == len(extrude_products)

    assert (
        [product["index"] for product in raster_products]
        == [product["index"] for product in vector_products]
        == [product["index"] for product in extrude_products]
    )

    assert (
        [product["name"] for product in raster_products]
        == [product["name"] for product in vector_products]
        == [product["name"] for product in extrude_products]
    )

    assert (
        [product["color"] for product in raster_products]
        == [product["color"] for product in vector_products]
        == [product["color"] for product in extrude_products]
    )


def test_artwork_pipeline_products_are_functionally_equivalent(
    tmp_path: Path,
) -> None:
    """
    The complete artwork pipeline preserves meaningful geometry through
    raster, vector, STL, and 3MF representations.

    This test deliberately verifies semantic properties rather than
    exact serialized bytes so that harmless differences between external
    tool versions do not make the regression test brittle.
    """

    realization = _build_artwork(
        tmp_path,
    )

    raster_directory = realization / "20-raster"
    vector_directory = realization / "30-vector"
    extrude_directory = realization / "40-extrude"
    package_directory = realization / "50-package"

    raster_manifest = _read_manifest(raster_directory / "products.json")

    vector_manifest = _read_manifest(vector_directory / "products.json")

    extrude_manifest = _read_manifest(extrude_directory / "products.json")

    raster_products = _manifest_products(
        raster_manifest,
    )

    vector_products = _manifest_products(
        vector_manifest,
    )

    extrude_products = _manifest_products(
        extrude_manifest,
    )

    # -----------------------------------------------------
    # Expected semantic products
    # -----------------------------------------------------

    expected_names = {
        "test-white",
        "test-red",
    }

    assert {product["name"] for product in raster_products} == expected_names

    assert {product["name"] for product in vector_products} == expected_names

    assert {product["name"] for product in extrude_products} == expected_names

    # -----------------------------------------------------
    # Raster geometry
    # -----------------------------------------------------

    raster_paths = tuple(raster_directory / product["path"] for product in raster_products)

    for path in raster_paths:
        _assert_raster_has_geometry(
            path,
        )

    # -----------------------------------------------------
    # Vector geometry
    # -----------------------------------------------------

    vector_paths = tuple(vector_directory / product["path"] for product in vector_products)

    for path in vector_paths:
        _assert_svg_has_geometry(
            path,
        )

    # -----------------------------------------------------
    # STL geometry
    # -----------------------------------------------------

    extrude_paths = tuple(extrude_directory / product["path"] for product in extrude_products)

    meshes = tuple(load_stl(path) for path in extrude_paths)

    assert all(mesh.vertices for mesh in meshes)

    assert all(mesh.triangles for mesh in meshes)

    # Extrusion must produce actual three-dimensional geometry.
    for mesh in meshes:
        z_values = {vertex[2] for vertex in mesh.vertices}

        assert len(z_values) > 1

        assert max(z_values) > min(z_values)

    # -----------------------------------------------------
    # 3MF package
    # -----------------------------------------------------

    artifact = package_directory / "artifact.3mf"

    model = _read_3mf_model(
        artifact,
    )

    namespace = {
        "m": CORE_NS,
    }

    objects = model.findall(
        "./m:resources/m:object",
        namespace,
    )

    build_items = model.findall(
        "./m:build/m:item",
        namespace,
    )

    assert len(objects) == len(extrude_products)
    assert len(build_items) == len(extrude_products)

    expected_component_names = {f"example-{name}" for name in expected_names}

    assert {object_element.get("name") for object_element in objects} == expected_component_names

    for object_element in objects:
        vertices = object_element.findall(
            "./m:mesh/m:vertices/m:vertex",
            namespace,
        )

        triangles = object_element.findall(
            "./m:mesh/m:triangles/m:triangle",
            namespace,
        )

        assert vertices
        assert triangles

    object_ids = [object_element.get("id") for object_element in objects]

    assert [item.get("objectid") for item in build_items] == object_ids


def test_artwork_pipeline_executes_named_realizations_independently(
    tmp_path: Path,
) -> None:
    """
    Two named realizations of one artifact execute independently.

    Both realizations may consume the same source artwork while using
    different resolved parameters and distinct persistent product
    namespaces.
    """

    _write_workspace(tmp_path)

    source = tmp_path / "source.png"

    _write_source(source)

    write_artifact_config(
        "example",
        {
            "realizations": {
                "ornament": {
                    "model": "artwork",
                    "variant": "default",
                    "source": "source.png",
                    "parameters": {
                        "artwork_size": 20.0,
                        "artwork_raise": 1.0,
                    },
                },
                "coaster": {
                    "model": "artwork",
                    "variant": "default",
                    "source": "source.png",
                    "parameters": {
                        "artwork_size": 24.0,
                        "artwork_raise": 1.5,
                    },
                },
            },
        },
        project_root=tmp_path,
    )

    ornament = create_build_plan(
        "example",
        realization="ornament",
        project_root=tmp_path,
    )

    coaster = create_build_plan(
        "example",
        realization="coaster",
        project_root=tmp_path,
    )

    assert ornament.realization_name == "ornament"
    assert coaster.realization_name == "coaster"

    assert ornament.resolver("source") == "source.png"
    assert coaster.resolver("source") == "source.png"

    assert ornament.resolver("artwork_size") == 20.0
    assert coaster.resolver("artwork_size") == 24.0

    assert ornament.resolver("artwork_raise") == 1.0
    assert coaster.resolver("artwork_raise") == 1.5

    execute_build(ornament)
    execute_build(coaster)

    ornament_directory = tmp_path / "artifacts" / "example" / "artwork" / "ornament"

    coaster_directory = tmp_path / "artifacts" / "example" / "artwork" / "coaster"

    # -----------------------------------------------------
    # Declared products
    # -----------------------------------------------------

    ornament_trace = ornament_directory / "10-prepare" / "trace.svg"

    coaster_trace = coaster_directory / "10-prepare" / "trace.svg"

    assert ornament_trace.is_file()
    assert coaster_trace.is_file()

    assert ornament_trace != coaster_trace

    # -----------------------------------------------------
    # Dynamic raster products
    # -----------------------------------------------------

    ornament_raster_directory = ornament_directory / "20-raster"

    coaster_raster_directory = coaster_directory / "20-raster"

    ornament_raster_manifest = _read_manifest(ornament_raster_directory / "products.json")

    coaster_raster_manifest = _read_manifest(coaster_raster_directory / "products.json")

    ornament_raster_products = ornament_raster_manifest["products"]

    coaster_raster_products = coaster_raster_manifest["products"]

    assert ornament_raster_products
    assert coaster_raster_products

    assert [product["name"] for product in ornament_raster_products] == [
        product["name"] for product in coaster_raster_products
    ]

    ornament_raster_paths = {
        ornament_raster_directory / product["path"] for product in ornament_raster_products
    }

    coaster_raster_paths = {
        coaster_raster_directory / product["path"] for product in coaster_raster_products
    }

    assert all(path.is_file() for path in ornament_raster_paths)

    assert all(path.is_file() for path in coaster_raster_paths)

    assert ornament_raster_paths.isdisjoint(coaster_raster_paths)

    # -----------------------------------------------------
    # Dynamic extrusion products
    # -----------------------------------------------------

    ornament_extrude_directory = ornament_directory / "40-extrude"

    coaster_extrude_directory = coaster_directory / "40-extrude"

    ornament_extrude_manifest = _read_manifest(ornament_extrude_directory / "products.json")

    coaster_extrude_manifest = _read_manifest(coaster_extrude_directory / "products.json")

    ornament_extrude_products = ornament_extrude_manifest["products"]

    coaster_extrude_products = coaster_extrude_manifest["products"]

    ornament_stls = {
        ornament_extrude_directory / product["path"] for product in ornament_extrude_products
    }

    coaster_stls = {
        coaster_extrude_directory / product["path"] for product in coaster_extrude_products
    }

    assert all(path.is_file() for path in ornament_stls)

    assert all(path.is_file() for path in coaster_stls)

    assert ornament_stls.isdisjoint(coaster_stls)

    # -----------------------------------------------------
    # Final artifacts
    # -----------------------------------------------------

    ornament_artifact = ornament_directory / "50-package" / "artifact.3mf"

    coaster_artifact = coaster_directory / "50-package" / "artifact.3mf"

    assert ornament_artifact.is_file()
    assert coaster_artifact.is_file()

    assert ornament_artifact.stat().st_size > 0
    assert coaster_artifact.stat().st_size > 0

    assert ornament_artifact != coaster_artifact


def test_clean_bg_house_registered_envelope_matches_registered_component_extent(
    tmp_path: Path,
) -> None:
    """
    The real clean_bg_house registered envelope and registered color components
    share one common occupied coordinate extent.

    The authoritative envelope used by Shape for placement must describe the
    same outer occupied region as the registered Artwork components that Shape
    subsequently dimensionalizes.
    """

    realization = _build_clean_bg_house_artwork(
        tmp_path,
    )

    vector_directory = realization / "30-vector"

    manifest = _read_manifest(
        vector_directory / "products.json",
    )

    envelope_path = vector_directory / str(manifest["envelope"])

    products = _manifest_products(
        manifest,
    )

    component_paths = tuple(vector_directory / str(product["path"]) for product in products)

    assert envelope_path.is_file()
    assert component_paths
    assert all(path.is_file() for path in component_paths)

    envelope_bounds = _svg_occupied_bounds(
        envelope_path,
    )

    component_bounds = tuple(_svg_occupied_bounds(path) for path in component_paths)

    union_bounds = (
        min(bounds[0] for bounds in component_bounds),
        max(bounds[1] for bounds in component_bounds),
        min(bounds[2] for bounds in component_bounds),
        max(bounds[3] for bounds in component_bounds),
    )

    assert envelope_bounds == pytest.approx(
        union_bounds,
        abs=1.0,
    )


def test_clean_bg_house_registered_envelope_and_components_share_occupied_center(
    tmp_path: Path,
) -> None:
    """
    The real clean_bg_house envelope and registered component union have the
    same occupied center.

    Shape centers the authoritative envelope in its placement circle. The
    visible registered Artwork must therefore share that center rather than
    being displaced within the envelope used for fitting.
    """

    realization = _build_clean_bg_house_artwork(
        tmp_path,
    )

    vector_directory = realization / "30-vector"

    manifest = _read_manifest(
        vector_directory / "products.json",
    )

    envelope_path = vector_directory / str(manifest["envelope"])

    products = _manifest_products(
        manifest,
    )

    component_bounds = tuple(
        _svg_occupied_bounds(
            vector_directory / str(product["path"]),
        )
        for product in products
    )

    envelope_bounds = _svg_occupied_bounds(
        envelope_path,
    )

    component_union = (
        min(bounds[0] for bounds in component_bounds),
        max(bounds[1] for bounds in component_bounds),
        min(bounds[2] for bounds in component_bounds),
        max(bounds[3] for bounds in component_bounds),
    )

    envelope_center_x = (envelope_bounds[0] + envelope_bounds[1]) / 2.0

    envelope_center_y = (envelope_bounds[2] + envelope_bounds[3]) / 2.0

    component_center_x = (component_union[0] + component_union[1]) / 2.0

    component_center_y = (component_union[2] + component_union[3]) / 2.0

    assert component_center_x == pytest.approx(
        envelope_center_x,
        abs=0.5,
    )

    assert component_center_y == pytest.approx(
        envelope_center_y,
        abs=0.5,
    )
