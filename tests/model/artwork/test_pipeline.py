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
    execute_artifact_build,
    execute_build,
)
from lowkey_artifact_builder.formats.threemf import (
    CORE_NS,
    component_name,
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
printer_colors = ["black", "brown", "gold", "silver", "cold-white"]
artifact_color_count = 5
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

    return project_root / "artifacts" / "clean_bg_house" / "artwork" / "artwork_default"


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

    return project_root / "artifacts" / "example" / "artwork" / "artwork_default"


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
    Dynamic Artwork products preserve Artifact-color identity through
    rasterization, vectorization, and extrusion.

    Downstream geometry stages consume persistent logical Artifact-color
    identity rather than rediscovering color identity from geometry.
    Physical printer-color assignment is introduced only during packaging.
    """

    realization = _build_artwork(
        tmp_path,
    )

    raster = _read_manifest(
        realization / "20-raster" / "products.json",
    )

    vector = _read_manifest(
        realization / "30-vector" / "products.json",
    )

    extrude = _read_manifest(
        realization / "40-extrude" / "products.json",
    )

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
        [product["artifact_color"] for product in raster_products]
        == [product["artifact_color"] for product in vector_products]
        == [product["artifact_color"] for product in extrude_products]
    )

    assert all("printer_color" not in product for product in raster_products)

    assert all("printer_color" not in product for product in vector_products)

    assert all("printer_color" not in product for product in extrude_products)


def test_artwork_pipeline_products_are_functionally_equivalent(
    tmp_path: Path,
) -> None:
    """
    The complete Artwork pipeline preserves logical color identity and
    meaningful geometry through raster, vector, STL, and 3MF representations.

    Raster, Vector, and Extrude preserve Artifact-color identity without
    physical printer assignment. Package resolves the configured physical
    printer colors into the final printable 3MF.

    Physical printer-color assignment is determined by color matching rather
    than by the ordering of printer_colors.
    """

    realization = _build_artwork(
        tmp_path,
    )

    raster_directory = realization / "20-raster"
    vector_directory = realization / "30-vector"
    extrude_directory = realization / "40-extrude"
    package_directory = realization / "50-package"

    raster_manifest = _read_manifest(
        raster_directory / "products.json",
    )

    vector_manifest = _read_manifest(
        vector_directory / "products.json",
    )

    extrude_manifest = _read_manifest(
        extrude_directory / "products.json",
    )

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
    # Logical Artifact-color identity
    # -----------------------------------------------------

    assert (
        [product["artifact_color"] for product in raster_products]
        == [product["artifact_color"] for product in vector_products]
        == [product["artifact_color"] for product in extrude_products]
    )

    for products in (
        raster_products,
        vector_products,
        extrude_products,
    ):
        assert all("printer_color" not in product for product in products)

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

    object_names = {object_element.get("name") for object_element in objects}

    # Package performs physical color matching. The configured printer
    # palette is not a positional mapping from Artifact-color index to
    # printer-color entry, so verify the resulting component/color pairs
    # without assuming palette ordering.
    expected_component_names = {
        component_name(
            "example",
            "color-1",
            "test-red",
        ),
        component_name(
            "example",
            "color-2",
            "test-white",
        ),
    }

    assert object_names == expected_component_names

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


def test_artwork_pipeline_reuses_canonical_vector_across_named_realizations(
    tmp_path: Path,
) -> None:
    """
    Named Artwork manufacturing reuses one canonical registered Vector Product.

    The Artifact owns the source artwork. artwork_default therefore owns the
    canonical Prepare, Raster, and Vector Products.

    Named Realizations consume artwork_default's Vector manifest and begin
    their own persistent Product namespaces at Extrude. Their dimensional
    parameters and final packaged Artifacts remain independent.

    Manufacturing a second named Realization reuses the already-current
    canonical registered Artwork rather than reproducing Prepare, Raster, or
    Vector beneath that Realization.
    """

    _write_workspace(tmp_path)

    source = tmp_path / "source.png"

    _write_source(source)

    write_artifact_config(
        "example",
        {
            "source": "source.png",
            "realizations": {
                "ornament": {
                    "model": "artwork",
                    "variant": "default",
                    "parameters": {
                        "artwork_size": 20.0,
                        "artwork_raise": 1.0,
                    },
                },
                "coaster": {
                    "model": "artwork",
                    "variant": "default",
                    "parameters": {
                        "artwork_size": 24.0,
                        "artwork_raise": 1.5,
                    },
                },
            },
        },
        project_root=tmp_path,
    )

    # -----------------------------------------------------
    # Manufacture both named Realizations
    # -----------------------------------------------------

    execute_artifact_build(
        "example",
        realization="ornament",
        project_root=tmp_path,
    )

    execute_artifact_build(
        "example",
        realization="coaster",
        project_root=tmp_path,
    )

    artwork_directory = tmp_path / "artifacts" / "example" / "artwork"

    canonical_directory = artwork_directory / "artwork_default"
    ornament_directory = artwork_directory / "ornament"
    coaster_directory = artwork_directory / "coaster"

    # -----------------------------------------------------
    # Canonical registered Artwork
    # -----------------------------------------------------

    canonical_prepare_directory = canonical_directory / "10-prepare"
    canonical_raster_directory = canonical_directory / "20-raster"
    canonical_vector_directory = canonical_directory / "30-vector"

    assert (canonical_prepare_directory / "trace.svg").is_file()
    assert (canonical_prepare_directory / "envelope.svg").is_file()

    canonical_raster_manifest = _read_manifest(
        canonical_raster_directory / "products.json",
    )

    canonical_vector_manifest = _read_manifest(
        canonical_vector_directory / "products.json",
    )

    canonical_raster_products = _manifest_products(
        canonical_raster_manifest,
    )

    canonical_vector_products = _manifest_products(
        canonical_vector_manifest,
    )

    assert canonical_raster_products
    assert canonical_vector_products

    assert [product["artifact_color"] for product in canonical_raster_products] == [
        product["artifact_color"] for product in canonical_vector_products
    ]

    assert all("printer_color" not in product for product in canonical_raster_products)

    assert all("printer_color" not in product for product in canonical_vector_products)

    canonical_vector_colors = [product["artifact_color"] for product in canonical_vector_products]

    # -----------------------------------------------------
    # Named Realizations do not reproduce registered Artwork
    # -----------------------------------------------------

    for realization_directory in (
        ornament_directory,
        coaster_directory,
    ):
        assert not (realization_directory / "10-prepare").exists()
        assert not (realization_directory / "20-raster").exists()
        assert not (realization_directory / "30-vector").exists()

        assert (realization_directory / "40-extrude" / "products.json").is_file()

        assert (realization_directory / "50-package" / "artifact.3mf").is_file()

    # -----------------------------------------------------
    # Both named Realizations preserve canonical color identity
    # -----------------------------------------------------

    ornament_extrude_manifest = _read_manifest(
        ornament_directory / "40-extrude" / "products.json",
    )

    coaster_extrude_manifest = _read_manifest(
        coaster_directory / "40-extrude" / "products.json",
    )

    ornament_products = _manifest_products(
        ornament_extrude_manifest,
    )

    coaster_products = _manifest_products(
        coaster_extrude_manifest,
    )

    assert [product["artifact_color"] for product in ornament_products] == canonical_vector_colors

    assert [product["artifact_color"] for product in coaster_products] == canonical_vector_colors

    assert all("printer_color" not in product for product in ornament_products)

    assert all("printer_color" not in product for product in coaster_products)

    # -----------------------------------------------------
    # Dimensional manufacturing remains realization-specific
    # -----------------------------------------------------

    assert ornament_extrude_manifest != coaster_extrude_manifest

    ornament_package = ornament_directory / "50-package" / "artifact.3mf"

    coaster_package = coaster_directory / "50-package" / "artifact.3mf"

    assert zipfile.is_zipfile(ornament_package)
    assert zipfile.is_zipfile(coaster_package)


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


def test_create_build_plan_without_selection_uses_canonical_default_realization(
    tmp_path: Path,
) -> None:
    """
    Omitted selection means the effective Model's default Variant.

    Planning resolves that Variant through the Artifact realization catalog,
    so the resulting execution identity is the canonical default Realization.
    """

    write_artifact_config(
        "example",
        {
            "model": "artwork",
            "source": "source.png",
        },
        project_root=tmp_path,
    )

    plan = create_build_plan(
        "example",
        project_root=tmp_path,
    )

    assert plan.model_name == "artwork"
    assert plan.realization_name == "artwork_default"
    assert plan.resolver("variant") == "default"
    assert plan.resolver("realization") == "artwork_default"


def test_artwork_pipeline_packages_participating_outer_ridge(
    tmp_path: Path,
) -> None:
    """
    A participating Artwork Outer Ridge survives the complete public build
    pipeline as an independently printable physical component.

    Extrude records the Outer Ridge's logical Artifact-color attachment
    identity. Package applies the configured physical Outer Ridge color to
    the final 3MF component.

    The test enters through create_build_plan() and execute_build() rather
    than invoking extrusion or packaging stages directly.
    """

    _write_workspace(
        tmp_path,
    )

    source = tmp_path / "source.png"

    _write_source(
        source,
    )

    write_artifact_config(
        "example",
        {
            "model": "artwork",
            "source": "source.png",
            "artwork_outer_ridge_width": 2.0,
            "artwork_outer_ridge_color": "test-red",
        },
        project_root=tmp_path,
    )

    plan = create_build_plan(
        "example",
        project_root=tmp_path,
    )

    execute_build(
        plan,
    )

    realization = tmp_path / "artifacts" / "example" / "artwork" / "artwork_default"

    extrude_directory = realization / "40-extrude"
    package_directory = realization / "50-package"

    # -----------------------------------------------------
    # Extrude
    # -----------------------------------------------------

    outer_ridge_stl = extrude_directory / "outer-ridge.stl"

    assert outer_ridge_stl.is_file()

    ridge_mesh = load_stl(
        outer_ridge_stl,
    )

    assert ridge_mesh.vertices
    assert ridge_mesh.triangles

    extrude_manifest = _read_manifest(
        extrude_directory / "products.json",
    )

    extrude_products = _manifest_products(
        extrude_manifest,
    )

    ridge_products = [
        product for product in extrude_products if product["path"] == "outer-ridge.stl"
    ]

    assert ridge_products == [
        {
            "path": "outer-ridge.stl",
            "artifact_color_index": 2,
        }
    ]

    # -----------------------------------------------------
    # Package
    # -----------------------------------------------------

    artifact = package_directory / "artifact.3mf"

    assert artifact.is_file()
    assert artifact.stat().st_size > 0

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

    ridge_name = component_name(
        "example",
        "outer-ridge",
        "test-red",
    )

    ridge_objects = [
        object_element for object_element in objects if object_element.get("name") == ridge_name
    ]

    assert len(ridge_objects) == 1

    ridge_object = ridge_objects[0]

    vertices = ridge_object.findall(
        "./m:mesh/m:vertices/m:vertex",
        namespace,
    )

    triangles = ridge_object.findall(
        "./m:mesh/m:triangles/m:triangle",
        namespace,
    )

    assert vertices
    assert triangles

    ridge_object_id = ridge_object.get("id")

    assert ridge_object_id is not None

    assert any(item.get("objectid") == ridge_object_id for item in build_items)
