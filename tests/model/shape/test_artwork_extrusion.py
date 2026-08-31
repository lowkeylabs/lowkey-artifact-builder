"""
Tests for physical dimensionalization of Artwork incorporated into Shape.
"""
# File: tests/model/shape/test_artwork_extrusion.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from lowkey_artifact_builder.config import write_artifact_config
from lowkey_artifact_builder.engine import (
    create_build_plan,
    execute_build,
)
from lowkey_artifact_builder.model.models.shape.stages import compose, extrude, structure

# =========================================================
# Test support
# =========================================================


def _build_2121_stuart_registered_artwork(
    project_root: Path,
) -> Path:
    """
    Build the real 2121_stuart fixture through registered Artwork vectorization.

    The source Artwork has artwork_size=200.0, matching the real artifact
    configuration. Shape nevertheless consumes its dimension-independent
    registered vector product and owns subsequent physical dimensionalization.
    """

    fixture = Path(__file__).parents[1] / "artwork" / "fixtures" / "2121_stuart.png"

    assert fixture.is_file()

    source = project_root / "2121_stuart.png"

    shutil.copyfile(
        fixture,
        source,
    )

    (project_root / "workspace.toml").write_text(
        """
[parameters]
artwork_colors = ["black", "brown", "gold", "silver", "white"]
artwork_pixels = 973
artwork_min_island_area = 1
artwork_island_connectivity = 8
""".lstrip(),
        encoding="utf-8",
    )

    write_artifact_config(
        "2121_stuart",
        {
            "model": "artwork",
            "source": "2121_stuart.png",
            "artwork_size": 200.0,
        },
        project_root=project_root,
    )

    plan = create_build_plan(
        "2121_stuart",
        project_root=project_root,
    )

    execute_build(
        plan,
    )

    return (
        project_root
        / "artifacts"
        / "2121_stuart"
        / "artwork"
        / "default"
        / "30-vector"
        / "products.json"
    )


def _compose_2121_stuart_into_heptagon(
    project_root: Path,
    vector_manifest: Path,
) -> tuple[
    dict[str, object],
    float,
]:
    """
    Compose real 2121_stuart registered Artwork into the real Shape geometry.

    The Shape matches the reported artifact:

        polygon
        7 sides
        120 mm
        2 mm outer ridge

    Returns the composed Artwork manifest data and the registered placement
    radius computed from the resulting Shape composition.
    """

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

    interior = compose.registered_interior_region(
        composition,
    )

    placement = compose.artwork_placement_circle(
        interior,
    )

    vector_data = json.loads(
        vector_manifest.read_text(
            encoding="utf-8",
        )
    )

    vector_directory = vector_manifest.parent

    components: list[dict[str, object]] = []

    for product in vector_data["products"]:
        source = vector_directory / str(product["path"])

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

    return (
        artwork,
        placement.radius,
    )


def _write_registered_artwork(
    path: Path,
) -> None:
    """
    Write asymmetric Artwork in its registered coordinate system.

    The registered Artwork extent is 100 units. The occupied rectangle spans:

        X = 10 through 30
        Y = 20 through 60

    The asymmetry makes both position and vertical orientation observable
    after Shape physical dimensionalization.
    """

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        """
<svg
    xmlns="http://www.w3.org/2000/svg"
    width="100"
    height="100"
    viewBox="0 0 100 100"
>
    <g>
        <rect
            x="10"
            y="20"
            width="20"
            height="40"
        />
    </g>
</svg>
""".strip(),
        encoding="utf-8",
    )


def _stl_bounds(
    path: Path,
) -> tuple[
    float,
    float,
    float,
    float,
    float,
    float,
]:
    """
    Return X/Y/Z bounds from an ASCII STL produced by OpenSCAD.
    """

    vertices: list[
        tuple[
            float,
            float,
            float,
        ]
    ] = []

    for line in path.read_text(
        encoding="utf-8",
    ).splitlines():
        fields = line.strip().split()

        if len(fields) != 4 or fields[0] != "vertex":
            continue

        vertices.append(
            (
                float(fields[1]),
                float(fields[2]),
                float(fields[3]),
            )
        )

    if not vertices:
        raise AssertionError(
            f"STL contains no readable vertices: {path}",
        )

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


# =========================================================
# Registered Artwork physical dimensionalization
# =========================================================


@pytest.mark.slow
def test_incorporated_registered_artwork_preserves_physical_xy_orientation(
    tmp_path: Path,
) -> None:
    """
    Shape dimensionalization preserves registered Artwork top-view orientation.

    SVG registered coordinates use a downward-positive Y axis. Within the
    100-unit registered Artwork extent, the occupied rectangle spans:

        X = 10..30
        Y = 20..60

    Mapping the registered Artwork into Shape's centered, upward-positive
    coordinate system therefore gives:

        X = -0.4..-0.2
        Y = -0.1..+0.3

    A 100 mm Shape must therefore produce physical geometry at:

        X = -40..-20 mm
        Y = -10..+30 mm

    The SVG-to-OpenSCAD coordinate-system transition must not vertically
    mirror the Artwork when viewed from the top of the Shape.

    Artwork begins at the 2 mm Shape base top and rises 1 mm.
    """

    artwork = tmp_path / "artwork-1.svg"
    output = tmp_path / "artwork-1.stl"

    _write_registered_artwork(
        artwork,
    )

    source = extrude._build_artwork_component_scad(
        str(
            artwork.resolve(),
        ),
        shape_size=100.0,
        shape_base_raise=2.0,
        shape_artwork_raise=1.0,
        artwork_registered_width=100.0,
        artwork_registered_height=100.0,
        artwork_scale=0.01,
        artwork_translate_x=-0.5,
        artwork_translate_y=-0.5,
    )

    extrude.render_stl_source(
        source,
        output,
    )

    bounds = _stl_bounds(
        output,
    )

    assert bounds == pytest.approx(
        (
            -40.0,
            -20.0,
            -10.0,
            30.0,
            2.0,
            3.0,
        )
    )


@pytest.mark.slow
def test_openscad_import_preserves_registered_artwork_xy_coordinates(
    tmp_path: Path,
) -> None:
    """
    OpenSCAD SVG import preserves the registered Artwork coordinate
    relationships needed by Shape dimensionalization.
    """

    artwork = tmp_path / "artwork.svg"
    output = tmp_path / "artwork.stl"

    _write_registered_artwork(
        artwork,
    )

    source = f'linear_extrude(height = 1)\n    import("{artwork.resolve()}", dpi = 25.4);\n'

    extrude.render_stl_source(
        source,
        output,
    )

    bounds = _stl_bounds(
        output,
    )

    assert bounds == pytest.approx(
        (
            10.0,
            30.0,
            40.0,
            80.0,
            0.0,
            1.0,
        )
    )


def test_artwork_extrusion_passes_registered_extent_to_scad_builder(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Artwork extrusion passes its registered coordinate extent to physical
    SCAD construction.
    """

    component = tmp_path / "color-1.svg"

    component.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg"/>',
        encoding="utf-8",
    )

    artwork = {
        "registered_extent": {
            "width": 100.0,
            "height": 80.0,
        },
        "transform": {
            "scale": 0.01,
            "translate_x": -0.5,
            "translate_y": -0.4,
        },
        "components": [
            {
                "index": 1,
                "path": "color-1.svg",
                "name": "red",
                "color": {
                    "red": 220,
                    "green": 38,
                    "blue": 38,
                },
            },
        ],
    }

    received: dict[str, float] = {}

    def build_artwork_component_scad(
        source: str,
        *,
        shape_size: float,
        shape_base_raise: float,
        shape_artwork_raise: float,
        artwork_registered_width: float,
        artwork_registered_height: float,
        artwork_scale: float,
        artwork_translate_x: float,
        artwork_translate_y: float,
    ) -> str:
        received["width"] = artwork_registered_width
        received["height"] = artwork_registered_height

        return ""

    monkeypatch.setattr(
        extrude,
        "_build_artwork_component_scad",
        build_artwork_component_scad,
    )
    monkeypatch.setattr(
        extrude,
        "render_stl_source",
        lambda source, output: output.touch(),
    )

    extrude._render_artwork_components(
        artwork,
        tmp_path,
        tmp_path,
        shape_size=100.0,
        shape_base_raise=2.0,
        shape_artwork_raise=1.0,
    )

    assert received == {
        "width": 100.0,
        "height": 80.0,
    }


@pytest.mark.slow
def test_incorporated_registered_artwork_is_physically_centered(
    tmp_path: Path,
) -> None:
    """
    Shape extrusion preserves registered Artwork centering in physical X/Y.

    The Artwork envelope is deliberately offset within its registered extent.
    Shape composition must fit the occupied envelope into the circular interior
    and extrusion must realize that placement with equal space around the
    Artwork center on both physical axes.

    The physical Artwork bounds must therefore be centered on the Shape origin.
    """

    artwork = tmp_path / "artwork.svg"
    envelope = tmp_path / "envelope.svg"
    composition = tmp_path / "composition.svg"
    output = tmp_path / "artwork.stl"

    _write_registered_artwork(
        artwork,
    )

    envelope.write_text(
        """
<svg
    xmlns="http://www.w3.org/2000/svg"
    width="100"
    height="100"
    viewBox="0 0 100 100"
>
    <rect
        x="10"
        y="20"
        width="20"
        height="40"
    />
</svg>
""".strip(),
        encoding="utf-8",
    )

    composition.write_text(
        """
<svg
    xmlns="http://www.w3.org/2000/svg"
    viewBox="-0.5 -0.5 1 1"
>
    <circle
        id="ridge-inner-boundary"
        cx="0"
        cy="0"
        r="0.45"
    />
</svg>
""".strip(),
        encoding="utf-8",
    )

    registered_artwork = compose.RegisteredArtwork(
        registered_extent=compose.RegisteredExtent(
            width=100.0,
            height=100.0,
        ),
        envelope=envelope,
        components=(),
    )

    transform = compose.fit_registered_artwork_to_shape(
        registered_artwork,
        composition=composition,
    )

    source = extrude._build_artwork_component_scad(
        str(
            artwork.resolve(),
        ),
        shape_size=100.0,
        shape_base_raise=2.0,
        shape_artwork_raise=1.0,
        artwork_registered_width=100.0,
        artwork_registered_height=100.0,
        artwork_scale=transform.scale,
        artwork_translate_x=transform.translate_x,
        artwork_translate_y=transform.translate_y,
    )

    extrude.render_stl_source(
        source,
        output,
    )

    (
        minimum_x,
        maximum_x,
        minimum_y,
        maximum_y,
        minimum_z,
        maximum_z,
    ) = _stl_bounds(
        output,
    )

    assert (minimum_x + maximum_x) / 2.0 == pytest.approx(0.0)
    assert (minimum_y + maximum_y) / 2.0 == pytest.approx(0.0)

    assert minimum_z == pytest.approx(2.0)
    assert maximum_z == pytest.approx(3.0)


@pytest.mark.slow
def test_artwork_extrusion_physically_applies_persisted_composition_transform(
    tmp_path: Path,
) -> None:
    """
    Artwork extrusion physically applies the persisted composition transform.

    The registered Artwork component occupies:

        X = 10..30
        Y = 20..60

    within a 100x100 registered extent.

    The persisted transform deliberately centers that occupied region:

        scale = 0.01
        translate_x = -0.20
        translate_y = -0.40

    In registered Shape coordinates this places the occupied Artwork at:

        X = -0.10..+0.10
        Y = -0.20..+0.20

    Physical dimensionalization to a 100 mm Shape must therefore produce
    Artwork centered on both physical axes.

    This test protects the persistence boundary between Shape composition
    and physical Artwork extrusion.
    """

    component = tmp_path / "color-1.svg"

    _write_registered_artwork(
        component,
    )

    artwork = {
        "registered_extent": {
            "width": 100.0,
            "height": 100.0,
        },
        "transform": {
            "scale": 0.01,
            "translate_x": -0.20,
            "translate_y": -0.40,
        },
        "components": [
            {
                "index": 1,
                "path": "color-1.svg",
                "name": "red",
                "color": {
                    "red": 220,
                    "green": 38,
                    "blue": 38,
                },
            },
        ],
    }

    output_directory = tmp_path / "extrude"

    output_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    extrude._render_artwork_components(
        artwork,
        tmp_path,
        output_directory,
        shape_size=100.0,
        shape_base_raise=2.0,
        shape_artwork_raise=1.0,
    )

    output = output_directory / "artwork-1.stl"

    (
        minimum_x,
        maximum_x,
        minimum_y,
        maximum_y,
        minimum_z,
        maximum_z,
    ) = _stl_bounds(
        output,
    )

    assert minimum_x == pytest.approx(-10.0)
    assert maximum_x == pytest.approx(10.0)

    assert minimum_y == pytest.approx(-20.0)
    assert maximum_y == pytest.approx(20.0)

    assert (minimum_x + maximum_x) / 2.0 == pytest.approx(0.0)
    assert (minimum_y + maximum_y) / 2.0 == pytest.approx(0.0)

    assert minimum_z == pytest.approx(2.0)
    assert maximum_z == pytest.approx(3.0)


@pytest.mark.slow
def test_extrude_stage_physically_preserves_composed_artwork_centering(
    tmp_path: Path,
) -> None:
    """
    Shape extrusion realizes the Artwork transform persisted by composition.

    Registered Artwork has deliberately asymmetric occupancy within its
    registered extent. Composition centers that envelope in the Shape and
    persists one common transform. The extrusion stage must consume that
    persisted composition contract and produce physically centered Artwork.
    """

    artwork_directory = tmp_path / "artwork"
    compose_directory = tmp_path / "20-compose"
    extrude_directory = tmp_path / "30-extrude"

    artwork_directory.mkdir()
    compose_directory.mkdir()
    extrude_directory.mkdir()

    component = compose_directory / "color-1.svg"
    composition = compose_directory / "composition.svg"
    composition_manifest = compose_directory / "products.json"

    _write_registered_artwork(
        component,
    )

    composition.write_text(
        """
<svg
    xmlns="http://www.w3.org/2000/svg"
    viewBox="-0.5 -0.5 1 1"
>
    <circle
        id="shape-boundary"
        cx="0"
        cy="0"
        r="0.5"
    />
    <circle
        id="ridge-inner-boundary"
        cx="0"
        cy="0"
        r="0.45"
    />
</svg>
""".strip(),
        encoding="utf-8",
    )

    envelope = artwork_directory / "envelope.svg"

    envelope.write_text(
        """
<svg
    xmlns="http://www.w3.org/2000/svg"
    width="100"
    height="100"
    viewBox="0 0 100 100"
>
    <rect
        x="10"
        y="20"
        width="20"
        height="40"
    />
</svg>
""".strip(),
        encoding="utf-8",
    )

    registered_artwork = compose.RegisteredArtwork(
        registered_extent=compose.RegisteredExtent(
            width=100.0,
            height=100.0,
        ),
        envelope=envelope,
        components=(),
    )

    transform = compose.fit_registered_artwork_to_shape(
        registered_artwork,
        composition=composition,
    )

    composition_manifest.write_text(
        json.dumps(
            {
                "composition": "composition.svg",
                "artwork": {
                    "registered_extent": {
                        "width": 100.0,
                        "height": 100.0,
                    },
                    "transform": {
                        "scale": transform.scale,
                        "translate_x": transform.translate_x,
                        "translate_y": transform.translate_y,
                    },
                    "components": [
                        {
                            "index": 1,
                            "path": "color-1.svg",
                            "name": "red",
                            "color": {
                                "red": 220,
                                "green": 38,
                                "blue": 38,
                            },
                        },
                    ],
                },
            }
        ),
        encoding="utf-8",
    )

    artwork = extrude._load_composed_artwork(
        composition_manifest,
    )

    assert artwork is not None

    extrude._render_artwork_components(
        artwork,
        composition_manifest.parent,
        extrude_directory,
        shape_size=100.0,
        shape_base_raise=2.0,
        shape_artwork_raise=1.0,
    )

    output = extrude_directory / "artwork-1.stl"

    (
        minimum_x,
        maximum_x,
        minimum_y,
        maximum_y,
        minimum_z,
        maximum_z,
    ) = _stl_bounds(
        output,
    )

    assert (minimum_x + maximum_x) / 2.0 == pytest.approx(0.0)
    assert (minimum_y + maximum_y) / 2.0 == pytest.approx(0.0)

    assert minimum_z == pytest.approx(2.0)
    assert maximum_z == pytest.approx(3.0)


@pytest.mark.slow
def test_small_offset_circular_artwork_physically_fills_placement_circle(
    tmp_path: Path,
) -> None:
    """
    Shape extrusion realizes composition scaling for small circular Artwork.

    The registered Artwork circle is deliberately much smaller than its
    registered extent and offset within that extent. Composition enlarges its
    authoritative envelope to fill the Shape placement circle. OpenSCAD
    dimensionalization must preserve that fitted diameter physically.
    """

    component = tmp_path / "color-1.svg"
    envelope = tmp_path / "envelope.svg"
    composition = tmp_path / "composition.svg"
    output = tmp_path / "artwork-1.stl"

    component.write_text(
        """
<svg
    xmlns="http://www.w3.org/2000/svg"
    width="100"
    height="100"
    viewBox="0 0 100 100"
>
    <circle
        cx="60"
        cy="40"
        r="10"
    />
</svg>
""".strip(),
        encoding="utf-8",
    )

    envelope.write_text(
        """
<svg
    xmlns="http://www.w3.org/2000/svg"
    width="100"
    height="100"
    viewBox="0 0 100 100"
>
    <circle
        cx="60"
        cy="40"
        r="10"
    />
</svg>
""".strip(),
        encoding="utf-8",
    )

    composition.write_text(
        """
<svg
    xmlns="http://www.w3.org/2000/svg"
    viewBox="-0.5 -0.5 1 1"
>
    <circle
        id="shape-boundary"
        cx="0"
        cy="0"
        r="0.5"
    />
    <circle
        id="ridge-inner-boundary"
        cx="0"
        cy="0"
        r="0.4"
    />
</svg>
""".strip(),
        encoding="utf-8",
    )

    registered_artwork = compose.RegisteredArtwork(
        registered_extent=compose.RegisteredExtent(
            width=100.0,
            height=100.0,
        ),
        envelope=envelope,
        components=(),
    )

    transform = compose.fit_registered_artwork_to_shape(
        registered_artwork,
        composition=composition,
    )

    source = extrude._build_artwork_component_scad(
        str(
            component.resolve(),
        ),
        shape_size=120.0,
        shape_base_raise=2.0,
        shape_artwork_raise=1.0,
        artwork_registered_width=100.0,
        artwork_registered_height=100.0,
        artwork_scale=transform.scale,
        artwork_translate_x=transform.translate_x,
        artwork_translate_y=transform.translate_y,
    )

    extrude.render_stl_source(
        source,
        output,
    )

    (
        minimum_x,
        maximum_x,
        minimum_y,
        maximum_y,
        minimum_z,
        maximum_z,
    ) = _stl_bounds(
        output,
    )

    assert minimum_x == pytest.approx(-48.0)
    assert maximum_x == pytest.approx(48.0)

    assert minimum_y == pytest.approx(-48.0)
    assert maximum_y == pytest.approx(48.0)

    assert maximum_x - minimum_x == pytest.approx(96.0)
    assert maximum_y - minimum_y == pytest.approx(96.0)

    assert minimum_z == pytest.approx(2.0)
    assert maximum_z == pytest.approx(3.0)


@pytest.mark.slow
def test_small_offset_circular_artwork_is_physically_centered_after_extrusion(
    tmp_path: Path,
) -> None:
    """
    Shape extrusion realizes composition centering for offset circular Artwork.

    The occupied Artwork circle is offset within its registered coordinate
    extent. Composition centers that occupied envelope in the Shape placement
    circle. OpenSCAD dimensionalization must preserve that center physically
    rather than anchoring Artwork to an edge of its registered extent.
    """

    component = tmp_path / "color-1.svg"
    envelope = tmp_path / "envelope.svg"
    composition = tmp_path / "composition.svg"
    output = tmp_path / "artwork-1.stl"

    source_center_x = 60.0
    source_center_y = 40.0

    component.write_text(
        (
            '<svg xmlns="http://www.w3.org/2000/svg" '
            'width="100" height="100" viewBox="0 0 100 100">'
            f'<circle cx="{source_center_x}" '
            f'cy="{source_center_y}" r="10"/>'
            "</svg>"
        ),
        encoding="utf-8",
    )

    envelope.write_text(
        (
            '<svg xmlns="http://www.w3.org/2000/svg" '
            'width="100" height="100" viewBox="0 0 100 100">'
            f'<circle cx="{source_center_x}" '
            f'cy="{source_center_y}" r="10"/>'
            "</svg>"
        ),
        encoding="utf-8",
    )

    composition.write_text(
        """
<svg
    xmlns="http://www.w3.org/2000/svg"
    viewBox="-0.5 -0.5 1 1"
>
    <circle
        id="shape-boundary"
        cx="0"
        cy="0"
        r="0.5"
    />
    <circle
        id="ridge-inner-boundary"
        cx="0"
        cy="0"
        r="0.4"
    />
</svg>
""".strip(),
        encoding="utf-8",
    )

    registered_artwork = compose.RegisteredArtwork(
        registered_extent=compose.RegisteredExtent(
            width=100.0,
            height=100.0,
        ),
        envelope=envelope,
        components=(),
    )

    transform = compose.fit_registered_artwork_to_shape(
        registered_artwork,
        composition=composition,
    )

    source = extrude._build_artwork_component_scad(
        str(
            component.resolve(),
        ),
        shape_size=120.0,
        shape_base_raise=2.0,
        shape_artwork_raise=1.0,
        artwork_registered_width=100.0,
        artwork_registered_height=100.0,
        artwork_scale=transform.scale,
        artwork_translate_x=transform.translate_x,
        artwork_translate_y=transform.translate_y,
    )

    extrude.render_stl_source(
        source,
        output,
    )

    (
        minimum_x,
        maximum_x,
        minimum_y,
        maximum_y,
        _minimum_z,
        _maximum_z,
    ) = _stl_bounds(
        output,
    )

    physical_center_x = (minimum_x + maximum_x) / 2.0

    physical_center_y = (minimum_y + maximum_y) / 2.0

    assert physical_center_x == pytest.approx(
        0.0,
    )
    assert physical_center_y == pytest.approx(
        0.0,
    )

    assert minimum_x == pytest.approx(-48.0)
    assert maximum_x == pytest.approx(48.0)

    assert minimum_y == pytest.approx(-48.0)
    assert maximum_y == pytest.approx(48.0)


@pytest.mark.slow
def test_real_2121_stuart_physically_fills_heptagon_placement_circle(
    tmp_path: Path,
) -> None:
    """
    Real 2121_stuart Artwork fills the physical placement circle of the
    reported 120 mm seven-sided Shape with a 2 mm outer ridge.

    This protects the complete registered-Artwork-to-physical-Shape scaling
    boundary using the real regression fixture rather than synthetic geometry.
    """

    vector_manifest = _build_2121_stuart_registered_artwork(
        tmp_path,
    )

    artwork, placement_radius = _compose_2121_stuart_into_heptagon(
        tmp_path,
        vector_manifest,
    )

    output_directory = tmp_path / "extrude"

    output_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    extrude._render_artwork_components(
        artwork,
        tmp_path,
        output_directory,
        shape_size=120.0,
        shape_base_raise=2.0,
        shape_artwork_raise=1.0,
    )

    products = tuple(
        output_directory.glob(
            "artwork-*.stl",
        )
    )

    assert products

    bounds = tuple(_stl_bounds(path) for path in products)

    minimum_x = min(item[0] for item in bounds)
    maximum_x = max(item[1] for item in bounds)
    minimum_y = min(item[2] for item in bounds)
    maximum_y = max(item[3] for item in bounds)

    expected_radius = placement_radius * 120.0

    assert minimum_x == pytest.approx(
        -expected_radius,
        abs=0.25,
    )
    assert maximum_x == pytest.approx(
        expected_radius,
        abs=0.25,
    )

    assert minimum_y == pytest.approx(
        -expected_radius,
        abs=0.25,
    )
    assert maximum_y == pytest.approx(
        expected_radius,
        abs=0.25,
    )


@pytest.mark.slow
def test_real_2121_stuart_is_physically_centered_in_heptagon_placement_circle(
    tmp_path: Path,
) -> None:
    """
    Real 2121_stuart Artwork remains centered after physical extrusion into
    the reported 120 mm seven-sided Shape with a 2 mm outer ridge.

    The union of all physically rendered Artwork components must share the
    Shape origin used by the common Artwork placement circle.
    """

    vector_manifest = _build_2121_stuart_registered_artwork(
        tmp_path,
    )

    artwork, _placement_radius = _compose_2121_stuart_into_heptagon(
        tmp_path,
        vector_manifest,
    )

    output_directory = tmp_path / "extrude"

    output_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    extrude._render_artwork_components(
        artwork,
        tmp_path,
        output_directory,
        shape_size=120.0,
        shape_base_raise=2.0,
        shape_artwork_raise=1.0,
    )

    products = tuple(
        output_directory.glob(
            "artwork-*.stl",
        )
    )

    assert products

    bounds = tuple(_stl_bounds(path) for path in products)

    minimum_x = min(item[0] for item in bounds)
    maximum_x = max(item[1] for item in bounds)
    minimum_y = min(item[2] for item in bounds)
    maximum_y = max(item[3] for item in bounds)

    center_x = (minimum_x + maximum_x) / 2.0

    center_y = (minimum_y + maximum_y) / 2.0

    assert center_x == pytest.approx(
        0.0,
        abs=0.25,
    )

    assert center_y == pytest.approx(
        0.0,
        abs=0.25,
    )
