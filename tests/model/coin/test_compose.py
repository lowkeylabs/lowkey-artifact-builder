"""Tests for Coin physical composition."""
# File: tests/model/coin/test_compose.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from lowkey_artifact_builder.colors import PaletteColor
from lowkey_artifact_builder.engine import StageContext
from lowkey_artifact_builder.formats.threemf import (
    Component,
    Mesh,
    component_name,
    load_stl,
    write,
)
from lowkey_artifact_builder.model.models.coin.stages import compose

# =========================================================
# Helpers
# =========================================================


def _mesh() -> Mesh:
    """Return representative physical Face geometry."""

    return Mesh(
        vertices=(
            (0.0, 0.0, 0.0),
            (1.0, 0.0, 0.0),
            (0.0, 1.0, 0.0),
        ),
        triangles=((0, 1, 2),),
    )


def _asymmetric_mesh(
    *,
    z_top: float,
) -> Mesh:
    """
    Return asymmetric physical geometry with a visible semantic top.

    The mesh occupies positive Z as an ordinary packaged Shape does.
    Its asymmetric X/Y coordinates make rigid Face orientation observable.
    """

    return Mesh(
        vertices=(
            (-2.0, -3.0, 0.0),
            (4.0, -3.0, 0.0),
            (-2.0, 7.0, z_top),
            (1.0, 2.0, z_top),
        ),
        triangles=(
            (0, 1, 2),
            (1, 3, 2),
        ),
    )


def _write_asymmetric_shape(
    path: Path,
    *,
    raise_style: str,
    components: tuple[Component, ...],
) -> None:
    """Write an asymmetric packaged Shape Product for Coin composition."""

    compatibility = {
        "boundary": {
            "kind": "circle",
            "center": [0.0, 0.0],
            "radius": 50.0,
        },
        "hole": None,
        "loop": None,
    }

    default_color = PaletteColor(
        name="white",
        rgb=(255, 255, 255),
    )

    packaged_components = tuple(
        Component(
            name=component_name(
                "test-shape",
                component.name,
                (component.color or default_color).name,
            ),
            mesh=component.mesh,
            color=component.color or default_color,
        )
        for component in components
    )

    write(
        packaged_components,
        path,
        metadata={
            "raise_style": raise_style,
            "shape_compatibility": json.dumps(
                compatibility,
                separators=(",", ":"),
                sort_keys=True,
            ),
        },
    )


def _physical_meshes(
    manifest: Path,
) -> tuple[Mesh, ...]:
    """
    Load the materialized component meshes described by a physical manifest.

    The test intentionally depends only upon the established dynamic-component
    manifest boundary: each component identifies its physical file by path.
    """

    products = json.loads(
        manifest.read_text(
            encoding="utf-8",
        )
    )

    return tuple(
        load_stl(
            manifest.parent / component["path"],
        )
        for component in products["components"]
    )


def _vertices(
    mesh: Mesh,
) -> set[tuple[float, float, float]]:
    """Return mesh vertices independent of serialization order."""

    return set(
        mesh.vertices,
    )


def _write_shape(
    path: Path,
    *,
    raise_style: str,
    boundary: dict[str, object] | None = None,
    hole: dict[str, object] | None = None,
    loop: dict[str, object] | None = None,
) -> None:
    """Write one complete packaged Shape Product."""

    if boundary is None:
        boundary = {
            "kind": "circle",
            "center": [0.0, 0.0],
            "radius": 50.0,
        }

    compatibility = {
        "boundary": boundary,
        "hole": hole,
        "loop": loop,
    }

    color = PaletteColor(
        name="white",
        rgb=(255, 255, 255),
    )

    write(
        (
            Component(
                name=component_name(
                    "test-shape",
                    "base",
                    color.name,
                ),
                mesh=_mesh(),
                color=color,
            ),
        ),
        path,
        metadata={
            "raise_style": raise_style,
            "shape_compatibility": json.dumps(
                compatibility,
                separators=(",", ":"),
                sort_keys=True,
            ),
        },
    )


# =========================================================
# Face compatibility
# =========================================================


def test_coin_rejects_non_inlaid_face_b(
    tmp_path: Path,
) -> None:
    """
    Coin rejects a packaged Face B that is not inlaid.

    Compatibility is determined from persistent metadata embedded in the
    packaged Shape Product. Coin does not reopen Shape configuration or
    regenerate an incompatible Face.
    """

    face_a = tmp_path / "face-a.3mf"
    face_b = tmp_path / "face-b.3mf"

    _write_shape(
        face_a,
        raise_style="raised",
    )
    _write_shape(
        face_b,
        raise_style="raised",
    )

    context = Mock(
        spec=StageContext,
    )

    context.input.side_effect = {
        "faceA": face_a,
        "faceB": face_b,
    }.__getitem__

    with pytest.raises(
        ValueError,
        match="Face B.*inlaid",
    ):
        compose.execute(
            context,
        )


def test_coin_accepts_compatible_packaged_faces(
    tmp_path: Path,
) -> None:
    """
    Coin accepts compatible packaged Faces when Face B is inlaid.

    Compatibility is determined from the packaged Shape Products rather
    than producer Artifact or Realization identity. Successful composition
    publishes the declared physical Coin Product.
    """

    face_a = tmp_path / "face-a.3mf"
    face_b = tmp_path / "face-b.3mf"
    physical = tmp_path / "physical.json"

    _write_shape(
        face_a,
        raise_style="raised",
    )
    _write_shape(
        face_b,
        raise_style="inlaid",
    )

    context = Mock(
        spec=StageContext,
    )

    context.input.side_effect = {
        "faceA": face_a,
        "faceB": face_b,
    }.__getitem__

    context.output.side_effect = {
        "physical": physical,
    }.__getitem__

    context.resolver.side_effect = {
        "coin_orientation": "aligned",
    }.__getitem__

    compose.execute(
        context,
    )

    assert physical.is_file()


def test_coin_rejects_structurally_incompatible_faces(
    tmp_path: Path,
) -> None:
    """
    Coin rejects Faces whose physical mating boundaries do not coincide.

    Compatibility is determined from producer-owned physical metadata embedded
    in the packaged Shape Products rather than reconstructed from their meshes.
    """

    face_a = tmp_path / "face-a.3mf"
    face_b = tmp_path / "face-b.3mf"

    _write_shape(
        face_a,
        raise_style="raised",
    )
    _write_shape(
        face_b,
        raise_style="inlaid",
        boundary={
            "kind": "circle",
            "center": [0.0, 0.0],
            "radius": 45.0,
        },
    )

    context = Mock(
        spec=StageContext,
    )

    context.input.side_effect = {
        "faceA": face_a,
        "faceB": face_b,
    }.__getitem__

    context.resolver.side_effect = {
        "coin_orientation": "aligned",
    }.__getitem__

    with pytest.raises(
        ValueError,
        match="boundar",
    ):
        compose.execute(
            context,
        )


@pytest.mark.parametrize(
    (
        "feature",
        "face_a_geometry",
        "face_b_geometry",
    ),
    [
        (
            "hole",
            {
                "center": [47.1, 0.0],
                "radius": 2.5,
            },
            None,
        ),
        (
            "loop",
            {
                "center": [52.0, 0.0],
                "inner_radius": 2.0,
                "outer_radius": 3.5,
            },
            {
                "center": [-52.0, 0.0],
                "inner_radius": 2.0,
                "outer_radius": 4.0,
            },
        ),
    ],
)
def test_coin_rejects_incompatible_bilateral_features(
    tmp_path: Path,
    feature: str,
    face_a_geometry: dict[str, object] | None,
    face_b_geometry: dict[str, object] | None,
) -> None:
    """
    Coin requires bilateral Hole and Loop compatibility between its Faces.

    Participation and resolved physical geometry come from the packaged Shape
    compatibility contract rather than inference from component meshes.
    Feature geometry is compared after Face B orientation.
    """

    face_a = tmp_path / "face-a.3mf"
    face_b = tmp_path / "face-b.3mf"

    face_a_features: dict[str, dict[str, object] | None] = {
        "hole": None,
        "loop": None,
    }

    face_b_features: dict[str, dict[str, object] | None] = {
        "hole": None,
        "loop": None,
    }

    face_a_features[feature] = face_a_geometry
    face_b_features[feature] = face_b_geometry

    _write_shape(
        face_a,
        raise_style="raised",
        hole=face_a_features["hole"],
        loop=face_a_features["loop"],
    )

    _write_shape(
        face_b,
        raise_style="inlaid",
        hole=face_b_features["hole"],
        loop=face_b_features["loop"],
    )

    context = Mock(
        spec=StageContext,
    )

    context.input.side_effect = {
        "faceA": face_a,
        "faceB": face_b,
    }.__getitem__

    context.resolver.side_effect = {
        "coin_orientation": "aligned",
    }.__getitem__

    with pytest.raises(
        ValueError,
        match=feature,
    ):
        compose.execute(
            context,
        )


# =========================================================
# Physical Face composition
# =========================================================


@pytest.mark.parametrize(
    (
        "orientation",
        "expected_face_b_vertices",
    ),
    [
        (
            "aligned",
            {
                (2.0, -3.0, 0.0),
                (-4.0, -3.0, 0.0),
                (2.0, 7.0, -2.0),
                (-1.0, 2.0, -2.0),
            },
        ),
        (
            "inverted",
            {
                (-2.0, 3.0, 0.0),
                (4.0, 3.0, 0.0),
                (-2.0, -7.0, -2.0),
                (1.0, -2.0, -2.0),
            },
        ),
    ],
)
def test_coin_composes_complete_faces_with_rigid_orientation(
    tmp_path: Path,
    orientation: str,
    expected_face_b_vertices: set[
        tuple[
            float,
            float,
            float,
        ]
    ],
) -> None:
    """
    Coin rigidly composes complete packaged Faces around the Z=0 mating plane.

    Face A retains its packaged physical placement. Face B is flipped to the
    opposite side as one rigid Face. Aligned orientation preserves semantic
    top at the same physical end; inverted orientation places Face B semantic
    top at the opposite physical end.
    """

    face_a = tmp_path / "face-a.3mf"
    face_b = tmp_path / "face-b.3mf"
    physical = tmp_path / "physical.json"

    face_a_mesh = _asymmetric_mesh(
        z_top=3.0,
    )

    face_b_mesh = _asymmetric_mesh(
        z_top=2.0,
    )

    _write_asymmetric_shape(
        face_a,
        raise_style="raised",
        components=(
            Component(
                name="base",
                mesh=face_a_mesh,
            ),
            Component(
                name="marker",
                mesh=face_a_mesh,
            ),
        ),
    )

    _write_asymmetric_shape(
        face_b,
        raise_style="inlaid",
        components=(
            Component(
                name="base",
                mesh=face_b_mesh,
            ),
            Component(
                name="marker",
                mesh=face_b_mesh,
            ),
        ),
    )

    context = Mock(
        spec=StageContext,
    )

    context.input.side_effect = {
        "faceA": face_a,
        "faceB": face_b,
    }.__getitem__

    context.output.side_effect = {
        "physical": physical,
    }.__getitem__

    context.resolver.side_effect = {
        "coin_orientation": orientation,
    }.__getitem__

    compose.execute(
        context,
    )

    meshes = _physical_meshes(
        physical,
    )

    assert len(meshes) == 4

    face_a_vertices = _vertices(
        face_a_mesh,
    )

    assert sum(_vertices(mesh) == face_a_vertices for mesh in meshes) == 2

    assert sum(_vertices(mesh) == expected_face_b_vertices for mesh in meshes) == 2


@pytest.mark.parametrize(
    (
        "orientation",
        "feature",
        "face_a_geometry",
        "face_b_geometry",
    ),
    [
        (
            "aligned",
            "hole",
            {
                "center": [47.1, 8.0],
                "radius": 2.5,
            },
            {
                "center": [-47.1, 8.0],
                "radius": 2.5,
            },
        ),
        (
            "aligned",
            "loop",
            {
                "center": [52.0, 9.0],
                "inner_radius": 2.0,
                "outer_radius": 3.5,
            },
            {
                "center": [-52.0, 9.0],
                "inner_radius": 2.0,
                "outer_radius": 3.5,
            },
        ),
        (
            "inverted",
            "hole",
            {
                "center": [47.1, 8.0],
                "radius": 2.5,
            },
            {
                "center": [47.1, -8.0],
                "radius": 2.5,
            },
        ),
        (
            "inverted",
            "loop",
            {
                "center": [52.0, 9.0],
                "inner_radius": 2.0,
                "outer_radius": 3.5,
            },
            {
                "center": [52.0, -9.0],
                "inner_radius": 2.0,
                "outer_radius": 3.5,
            },
        ),
    ],
)
def test_coin_compares_bilateral_features_after_face_orientation(
    tmp_path: Path,
    orientation: str,
    feature: str,
    face_a_geometry: dict[str, object],
    face_b_geometry: dict[str, object],
) -> None:
    """
    Coin evaluates bilateral compatibility after orienting Face B.

    Hole and Loop geometry is producer-owned in each Face's coordinate
    system. Coin applies the same planar orientation semantics used for
    physical Face composition before comparing the resulting geometry.
    """

    face_a = tmp_path / "face-a.3mf"
    face_b = tmp_path / "face-b.3mf"
    physical = tmp_path / "physical.json"

    face_a_features: dict[str, dict[str, object] | None] = {
        "hole": None,
        "loop": None,
    }

    face_b_features: dict[str, dict[str, object] | None] = {
        "hole": None,
        "loop": None,
    }

    face_a_features[feature] = face_a_geometry
    face_b_features[feature] = face_b_geometry

    _write_shape(
        face_a,
        raise_style="raised",
        hole=face_a_features["hole"],
        loop=face_a_features["loop"],
    )

    _write_shape(
        face_b,
        raise_style="inlaid",
        hole=face_b_features["hole"],
        loop=face_b_features["loop"],
    )

    context = Mock(
        spec=StageContext,
    )

    context.input.side_effect = {
        "faceA": face_a,
        "faceB": face_b,
    }.__getitem__

    context.output.side_effect = {
        "physical": physical,
    }.__getitem__

    context.resolver.side_effect = {
        "coin_orientation": orientation,
    }.__getitem__

    compose.execute(
        context,
    )

    assert physical.is_file()


@pytest.mark.parametrize(
    (
        "orientation",
        "face_b_vertices",
    ),
    [
        (
            "aligned",
            [
                [6.0, -3.0],
                [-4.0, -3.0],
                [-4.0, 7.0],
                [6.0, 7.0],
            ],
        ),
        (
            "inverted",
            [
                [-6.0, 3.0],
                [4.0, 3.0],
                [4.0, -7.0],
                [-6.0, -7.0],
            ],
        ),
    ],
)
def test_coin_compares_polygon_boundary_after_face_orientation(
    tmp_path: Path,
    orientation: str,
    face_b_vertices: list[list[float]],
) -> None:
    """
    Coin compares structural boundaries in composed coordinates.

    Polygon compatibility describes a physical boundary, so equivalent
    polygons remain compatible when Face B orientation reverses winding or
    changes the serialized starting vertex.
    """

    face_a = tmp_path / "face-a.3mf"
    face_b = tmp_path / "face-b.3mf"
    physical = tmp_path / "products.json"

    face_a_boundary = {
        "kind": "polygon",
        "vertices": [
            [-6.0, -3.0],
            [4.0, -3.0],
            [4.0, 7.0],
            [-6.0, 7.0],
        ],
    }

    face_b_boundary = {
        "kind": "polygon",
        "vertices": face_b_vertices,
    }

    _write_shape(
        face_a,
        raise_style="raised",
        boundary=face_a_boundary,
    )
    _write_shape(
        face_b,
        raise_style="inlaid",
        boundary=face_b_boundary,
    )

    context = Mock(
        spec=StageContext,
    )

    context.input.side_effect = {
        "faceA": face_a,
        "faceB": face_b,
    }.__getitem__

    context.output.return_value = physical

    context.resolver.side_effect = {
        "coin_orientation": orientation,
    }.__getitem__

    compose.execute(
        context,
    )

    assert physical.is_file()


def test_coin_physical_product_preserves_face_identity_and_colors(
    tmp_path: Path,
) -> None:
    """
    Coin preserves source component identity and resolved physical color.

    Every source component remains independently represented. Coin namespaces
    semantic identity by Face without reassigning colors or merging components
    that share names or physical colors.
    """

    face_a = tmp_path / "face-a.3mf"
    face_b = tmp_path / "face-b.3mf"
    physical = tmp_path / "physical.json"

    white = PaletteColor(
        name="white",
        rgb=(255, 255, 255),
    )
    red = PaletteColor(
        name="red",
        rgb=(255, 0, 0),
    )
    blue = PaletteColor(
        name="blue",
        rgb=(0, 0, 255),
    )

    face_a_mesh = _asymmetric_mesh(
        z_top=3.0,
    )
    face_b_mesh = _asymmetric_mesh(
        z_top=2.0,
    )

    _write_asymmetric_shape(
        face_a,
        raise_style="raised",
        components=(
            Component(
                name="base",
                mesh=face_a_mesh,
                color=white,
            ),
            Component(
                name="artwork-1",
                mesh=face_a_mesh,
                color=red,
            ),
        ),
    )

    _write_asymmetric_shape(
        face_b,
        raise_style="inlaid",
        components=(
            Component(
                name="base",
                mesh=face_b_mesh,
                color=white,
            ),
            Component(
                name="artwork-1",
                mesh=face_b_mesh,
                color=blue,
            ),
        ),
    )

    context = Mock(
        spec=StageContext,
    )

    context.input.side_effect = {
        "faceA": face_a,
        "faceB": face_b,
    }.__getitem__

    context.output.side_effect = {
        "physical": physical,
    }.__getitem__

    context.resolver.side_effect = {
        "coin_orientation": "aligned",
    }.__getitem__

    compose.execute(
        context,
    )

    products = json.loads(
        physical.read_text(
            encoding="utf-8",
        )
    )

    components = products["components"]

    assert len(components) == 4

    assert {component["name"] for component in components} == {
        "faceA-base",
        "faceA-artwork-1",
        "faceB-base",
        "faceB-artwork-1",
    }

    colors = {component["name"]: component["color"] for component in components}

    assert colors == {
        "faceA-base": {
            "name": "white",
            "rgb": [255, 255, 255],
        },
        "faceA-artwork-1": {
            "name": "red",
            "rgb": [255, 0, 0],
        },
        "faceB-base": {
            "name": "white",
            "rgb": [255, 255, 255],
        },
        "faceB-artwork-1": {
            "name": "blue",
            "rgb": [0, 0, 255],
        },
    }

    assert all((physical.parent / component["path"]).is_file() for component in components)
