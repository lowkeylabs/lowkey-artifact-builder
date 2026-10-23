"""
Manufacturing acceptance tests for SHAPE surface regions.

These tests use real OpenSCAD-rendered STL meshes and the
actual SHAPE 3MF packaging stage.

They verify material volumes, component identity, registration,
and independently assigned physical colors.
"""

from __future__ import annotations

import json
import math
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from unittest.mock import Mock

import pytest

from lowkey_artifact_builder.engine import StageContext
from lowkey_artifact_builder.formats.threemf import (
    CORE_NS,
    Mesh,
    load_stl,
)
from lowkey_artifact_builder.model.models.shape.stages import (
    compose,
    extrude,
    package,
)
from lowkey_artifact_builder.tools.openscad import find_openscad
from tests.support.model_parameters import model_test_resolver

SVG_NS = "http://www.w3.org/2000/svg"

pytestmark = pytest.mark.slow


def _context(
    *,
    inputs: dict[str, Path],
    outputs: dict[str, Path],
    parameters: dict[str, object],
    root: Path,
) -> Mock:
    context = Mock(spec=StageContext)
    context.input.side_effect = inputs.__getitem__
    context.has_input.side_effect = inputs.__contains__
    context.output.side_effect = outputs.__getitem__
    context.resolver.side_effect = model_test_resolver(
        "shape",
        overrides=parameters,
        project_root=root,
    )
    context.resolver.colors = {}
    return context


def _parameters(raise_style: str) -> dict[str, object]:
    return {
        "shape_geometry": "circle",
        "shape_size": 100.0,
        "shape_raise_style": raise_style,
        "shape_base_raise": 2.0,
        "shape_base_color": "white",
        "shape_outer_ridge_width": 5.0,
        "shape_outer_ridge_inset": 0.0,
        "shape_outer_ridge_raise": 0.0,
        "shape_outer_ridge_style": "integrated",
        "shape_inner_ridge_width": 2.0,
        "shape_inner_ridge_raise": 0.0,
        "shape_inner_to_outer_ridge_dist": 10.0,
        "shape_border_fill_color": "red",
        "shape_artwork_region_fill_color": "black",
        "shape_top_border_label_text": "",
        "shape_bottom_border_label_text": "",
        "shape_qr_payload": "",
        "shape_artwork_fill_raise": 0.0,
    }


def _manufacture(
    root: Path,
    *,
    raise_style: str,
) -> tuple[Path, Path, Path]:
    """
    Run Compose, real Extrude, and real Package.

    Return the canonical SVG, extrusion manifest, and 3MF.
    """
    root.mkdir(parents=True, exist_ok=True)

    parameters = _parameters(raise_style)

    structure = root / "structure.svg"
    composition = root / "composition.svg"
    composition_manifest = root / "composition-products.json"
    artifact_svg = root / "artifact.svg"

    structure.write_text(
        f'<svg xmlns="{SVG_NS}" viewBox="-0.5 -0.5 1 1">'
        '<circle id="shape-boundary" cx="0" cy="0" r="0.5"/>'
        "</svg>",
        encoding="utf-8",
    )

    compose.execute(
        _context(
            inputs={"structure.structure": structure},
            outputs={
                "composition": composition,
                "manifest": composition_manifest,
                "artifact": artifact_svg,
            },
            parameters=parameters,
            root=root,
        )
    )

    extrusion_manifest = root / "extrude" / "products.json"

    extrude.execute(
        _context(
            inputs={
                "compose.composition": composition,
                "compose.manifest": composition_manifest,
            },
            outputs={"manifest": extrusion_manifest},
            parameters=parameters,
            root=root,
        )
    )

    artifact_3mf = root / "artifact.3mf"

    package_context = _context(
        inputs={"extrude.manifest": extrusion_manifest},
        outputs={"artifact": artifact_3mf},
        parameters=parameters,
        root=root,
    )
    package_context.artifact_id = "surface-regions"

    package.execute(package_context)

    return artifact_svg, extrusion_manifest, artifact_3mf


def _mesh_volume(mesh: Mesh) -> float:
    """
    Calculate enclosed mesh volume from oriented triangles.

    A watertight, consistently oriented mesh has a signed
    tetrahedral volume independent of its location.
    """
    total = 0.0

    for ia, ib, ic in mesh.triangles:
        a = mesh.vertices[ia]
        b = mesh.vertices[ib]
        c = mesh.vertices[ic]

        cross_x = b[1] * c[2] - b[2] * c[1]
        cross_y = b[2] * c[0] - b[0] * c[2]
        cross_z = b[0] * c[1] - b[1] * c[0]

        total += a[0] * cross_x + a[1] * cross_y + a[2] * cross_z

    return abs(total / 6.0)


def _meshes(manifest: Path) -> dict[str, Mesh]:
    data = json.loads(manifest.read_text(encoding="utf-8"))

    return {
        component["name"]: load_stl(manifest.parent / component["path"])
        for component in data["components"]
    }


def _model_xml(artifact: Path) -> ET.Element:
    with zipfile.ZipFile(artifact) as archive:
        content = archive.read("3D/3dmodel.model")

    return ET.fromstring(content)


@pytest.mark.parametrize("raise_style", ["raised", "inlaid"])
def test_surface_regions_have_correct_physical_material_volumes(
    tmp_path: Path,
    raise_style: str,
) -> None:
    """
    Independently printable regions occupy their registered
    annular and central areas through the full Base thickness.

    This checks actual rendered geometry, not OpenSCAD text.
    """
    find_openscad()

    _, manifest, _ = _manufacture(
        tmp_path,
        raise_style=raise_style,
    )

    meshes = _meshes(manifest)

    assert "base" in meshes
    assert "border-fill" in meshes
    assert "artwork-region-fill" in meshes

    # From the configured 100 mm circle:
    # Outer Ridge inner radius = 45 mm
    # Inner Ridge outer radius = 35 mm
    # Inner Ridge inner radius = 33 mm

    expected_border_volume = math.pi * (45.0**2 - 35.0**2) * 2.0
    expected_artwork_volume = math.pi * 33.0**2 * 2.0

    assert _mesh_volume(meshes["border-fill"]) == pytest.approx(
        expected_border_volume,
        rel=0.01,
    )

    assert _mesh_volume(meshes["artwork-region-fill"]) == pytest.approx(
        expected_artwork_volume,
        rel=0.01,
    )

    for name in ("border-fill", "artwork-region-fill"):
        mesh = meshes[name]

        assert mesh.vertices
        assert mesh.triangles

        z_values = [vertex[2] for vertex in mesh.vertices]

        assert min(z_values) == pytest.approx(0.0, abs=0.01)
        assert max(z_values) == pytest.approx(2.0, abs=0.01)


@pytest.mark.parametrize("raise_style", ["raised", "inlaid"])
def test_surface_regions_preserve_physical_registration(
    tmp_path: Path,
    raise_style: str,
) -> None:
    """
    Physical regions retain their common registered origin
    and do not extend outside the Shape envelope.
    """
    find_openscad()

    _, manifest, _ = _manufacture(
        tmp_path,
        raise_style=raise_style,
    )

    meshes = _meshes(manifest)

    expected_extents = {
        "border-fill": 45.0,
        "artwork-region-fill": 33.0,
    }

    for name, radius in expected_extents.items():
        vertices = meshes[name].vertices

        xs = [vertex[0] for vertex in vertices]
        ys = [vertex[1] for vertex in vertices]

        assert min(xs) == pytest.approx(-radius, abs=0.05)
        assert max(xs) == pytest.approx(radius, abs=0.05)
        assert min(ys) == pytest.approx(-radius, abs=0.05)
        assert max(ys) == pytest.approx(radius, abs=0.05)


@pytest.mark.parametrize("raise_style", ["raised", "inlaid"])
def test_packaged_surface_regions_retain_identity_and_colors(
    tmp_path: Path,
    raise_style: str,
) -> None:
    """
    Final 3MF retains independently manufactured components
    and their Package-assigned physical color identities.
    """
    find_openscad()

    _, _, artifact = _manufacture(
        tmp_path,
        raise_style=raise_style,
    )

    assert artifact.is_file()

    root = _model_xml(artifact)

    assert root.get("unit") == "millimeter"

    namespace = {"m": CORE_NS}

    objects = root.findall(".//m:resources/m:object", namespace)
    names = {element.get("name", "") for element in objects}

    for component, color in (
        ("base", "white"),
        ("border-fill", "red"),
        ("artwork-region-fill", "black"),
    ):
        assert any(component in name and color in name for name in names), (component, color, names)

    build_items = root.findall(".//m:build/m:item", namespace)

    assert len(build_items) == len(objects)


@pytest.mark.parametrize("raise_style", ["raised", "inlaid"])
def test_svg_and_manufactured_regions_share_boundaries(
    tmp_path: Path,
    raise_style: str,
) -> None:
    """
    The canonical SVG identifies the same two surface regions
    whose physical meshes are packaged into the 3MF.
    """
    find_openscad()

    artifact_svg, manifest, artifact_3mf = _manufacture(
        tmp_path,
        raise_style=raise_style,
    )

    svg_root = ET.parse(artifact_svg).getroot()

    svg_ids = {element.get("id") for element in svg_root.iter() if element.get("id") is not None}

    meshes = _meshes(manifest)

    for name in ("border-fill", "artwork-region-fill"):
        assert name in svg_ids
        assert name in meshes

    model = _model_xml(artifact_3mf)

    names = {
        element.get("name", "")
        for element in model.findall(
            ".//m:resources/m:object",
            {"m": CORE_NS},
        )
    }

    for name in ("border-fill", "artwork-region-fill"):
        assert any(name in item for item in names)


@pytest.mark.parametrize("raise_style", ["raised", "inlaid"])
def test_surface_region_meshes_are_watertight(
    tmp_path: Path,
    raise_style: str,
) -> None:
    """
    Every rendered surface-region mesh is topologically closed.

    Each undirected triangle edge must be shared by exactly
    two triangles, with no exposed or nonmanifold edges.
    """
    from collections import Counter

    find_openscad()

    _, manifest, _ = _manufacture(
        tmp_path,
        raise_style=raise_style,
    )

    meshes = _meshes(manifest)

    for name in ("border-fill", "artwork-region-fill"):
        mesh = meshes[name]

        edge_counts: Counter[tuple[int, int]] = Counter()

        for a, b, c in mesh.triangles:
            for start, end in ((a, b), (b, c), (c, a)):
                assert start != end, f"{name}: degenerate triangle edge"

                edge = (min(start, end), max(start, end))
                edge_counts[edge] += 1

        invalid_edges = {edge: count for edge, count in edge_counts.items() if count != 2}

        assert not invalid_edges, (
            f"{name}: {len(invalid_edges)} edges are not "
            "shared by exactly two triangles; "
            f"examples: {list(invalid_edges.items())[:5]}"
        )

        assert _mesh_volume(mesh) > 0.0


@pytest.mark.parametrize("raise_style", ["raised", "inlaid"])
def test_surface_region_meshes_have_disjoint_radial_interiors(
    tmp_path: Path,
    raise_style: str,
) -> None:
    """
    Border Fill and Artwork Region Fill occupy disjoint
    radial interiors in the circular manufacturing fixture.

    The Inner Ridge separates the two material regions.
    """
    find_openscad()

    _, manifest, _ = _manufacture(
        tmp_path,
        raise_style=raise_style,
    )

    meshes = _meshes(manifest)

    border = meshes["border-fill"]
    artwork = meshes["artwork-region-fill"]

    border_radii = [math.hypot(x, y) for x, y, _ in border.vertices]

    artwork_radii = [math.hypot(x, y) for x, y, _ in artwork.vertices]

    assert border_radii
    assert artwork_radii

    # The configured Inner Ridge has a 35 mm outer radius
    # and a 33 mm inner radius.
    assert min(border_radii) == pytest.approx(
        35.0,
        abs=0.05,
    )

    assert max(artwork_radii) == pytest.approx(
        33.0,
        abs=0.05,
    )

    assert max(artwork_radii) < min(border_radii)


@pytest.mark.parametrize("raise_style", ["raised", "inlaid"])
def test_surface_region_meshes_preserve_expected_radial_coverage(
    tmp_path: Path,
    raise_style: str,
) -> None:
    """
    Rendered surface regions preserve their registered
    inner and outer boundaries.

    The Border Fill spans the annulus between the ridges.
    The Artwork Region Fill spans the central disk.
    """
    find_openscad()

    _, manifest, _ = _manufacture(
        tmp_path,
        raise_style=raise_style,
    )

    meshes = _meshes(manifest)

    expected_bounds = {
        "border-fill": (35.0, 45.0),
        "artwork-region-fill": (0.0, 33.0),
    }

    for name, (inner_radius, outer_radius) in expected_bounds.items():
        mesh = meshes[name]

        radii = [math.hypot(x, y) for x, y, _ in mesh.vertices]

        assert max(radii) == pytest.approx(
            outer_radius,
            abs=0.05,
        )

        if inner_radius > 0.0:
            assert min(radii) == pytest.approx(
                inner_radius,
                abs=0.05,
            )
        else:
            # A solid disk mesh may have no vertex at its
            # center. Its volume and outer radius establish
            # the intended central coverage in combination
            # with the earlier acceptance tests.
            expected_volume = math.pi * outer_radius**2 * 2.0

            assert _mesh_volume(mesh) == pytest.approx(
                expected_volume,
                rel=0.01,
            )


def _manufacture_inlaid_o(
    root: Path,
) -> tuple[Path, Path, Path]:
    """
    Manufacture a circular SHAPE with an inlaid top Border Label
    consisting of the glyph O.
    """
    root.mkdir(parents=True, exist_ok=True)

    parameters = {
        **_parameters("inlaid"),
        "shape_top_border_label_text": "O",
        "shape_bottom_border_label_text": "",
        "shape_border_label_font_family": "Liberation Sans",
        "shape_top_border_label_raise": 1.0,
    }

    structure = root / "structure.svg"
    composition = root / "composition.svg"
    composition_manifest = root / "composition-products.json"
    artifact_svg = root / "artifact.svg"

    structure.write_text(
        f'<svg xmlns="{SVG_NS}" viewBox="-0.5 -0.5 1 1">'
        '<circle id="shape-boundary" cx="0" cy="0" r="0.5"/>'
        "</svg>",
        encoding="utf-8",
    )

    compose.execute(
        _context(
            inputs={"structure.structure": structure},
            outputs={
                "composition": composition,
                "manifest": composition_manifest,
                "artifact": artifact_svg,
            },
            parameters=parameters,
            root=root,
        )
    )

    composed = json.loads(composition_manifest.read_text(encoding="utf-8"))
    assert composed["border_labels"]["top"] is not None

    extrusion_manifest = root / "extrude" / "products.json"

    extrude.execute(
        _context(
            inputs={
                "compose.composition": composition,
                "compose.manifest": composition_manifest,
            },
            outputs={"manifest": extrusion_manifest},
            parameters=parameters,
            root=root,
        )
    )

    artifact_3mf = root / "artifact.3mf"
    package_context = _context(
        inputs={"extrude.manifest": extrusion_manifest},
        outputs={"artifact": artifact_3mf},
        parameters=parameters,
        root=root,
    )
    package_context.artifact_id = "surface-regions"

    package.execute(package_context)

    return artifact_svg, extrusion_manifest, artifact_3mf


@pytest.mark.slow
def test_inlaid_o_preserves_enclosed_border_fill_material(
    tmp_path: Path,
) -> None:
    """
    A real inlaid O subtracts its strokes from Border Fill,
    but preserves the enclosed counter as background material.

    The counter is detected as a separate connected shell of
    the rendered Border Fill mesh.
    """
    from collections import defaultdict

    find_openscad()

    _, manifest, _ = _manufacture_inlaid_o(tmp_path)
    meshes = _meshes(manifest)

    assert "border-fill" in meshes
    assert "top-border-label" in meshes

    border = meshes["border-fill"]
    label = meshes["top-border-label"]

    assert _mesh_volume(border) > 0.0
    assert _mesh_volume(label) > 0.0

    # Build vertex adjacency from the rendered triangles.
    adjacency: dict[int, set[int]] = defaultdict(set)

    for a, b, c in border.triangles:
        adjacency[a].update((b, c))
        adjacency[b].update((a, c))
        adjacency[c].update((a, b))

    unvisited = set(adjacency)
    connected_components: list[set[int]] = []

    while unvisited:
        start = unvisited.pop()
        component = {start}
        pending = [start]

        while pending:
            current = pending.pop()

            for neighbor in adjacency[current]:
                if neighbor in unvisited:
                    unvisited.remove(neighbor)
                    component.add(neighbor)
                    pending.append(neighbor)

        connected_components.append(component)

    # The Border Fill annulus is one connected component.
    # The enclosed interior of O is a separate island.
    assert len(connected_components) >= 2, (
        "Inlaid O should leave an isolated Border Fill island inside its enclosed counter."
    )

    component_sizes = sorted(
        (len(component) for component in connected_components),
        reverse=True,
    )

    assert component_sizes[0] > component_sizes[1]

    # The enclosed island must lie within the Border Fill
    # radial interval rather than in the Artwork Region.

    smaller_components = sorted(
        connected_components,
        key=len,
        reverse=True,
    )[1:]

    assert any(
        all(
            33.0
            < math.hypot(
                border.vertices[index][0],
                border.vertices[index][1],
            )
            < 45.0
            for index in component
        )
        for component in smaller_components
    )


@pytest.mark.slow
def test_inlaid_o_preserves_independent_packaged_components(
    tmp_path: Path,
) -> None:
    """
    Inlaid O and Border Fill remain independent, closed,
    printable mesh components in the final 3MF.
    """
    from collections import Counter

    find_openscad()

    _, manifest, artifact = _manufacture_inlaid_o(tmp_path)
    meshes = _meshes(manifest)

    for name in ("border-fill", "top-border-label"):
        assert name in meshes

        mesh = meshes[name]
        edge_counts: Counter[tuple[int, int]] = Counter()

        for a, b, c in mesh.triangles:
            for start, end in ((a, b), (b, c), (c, a)):
                assert start != end

                edge_counts[(min(start, end), max(start, end))] += 1

        assert edge_counts
        assert all(count == 2 for count in edge_counts.values())
        assert _mesh_volume(mesh) > 0.0

    root = _model_xml(artifact)

    objects = root.findall(
        ".//m:resources/m:object",
        {"m": CORE_NS},
    )

    names = {element.get("name", "") for element in objects}

    assert any("border-fill" in name for name in names)
    assert any("top-border-label" in name for name in names)

    build_items = root.findall(
        ".//m:build/m:item",
        {"m": CORE_NS},
    )

    assert len(build_items) == len(objects)
