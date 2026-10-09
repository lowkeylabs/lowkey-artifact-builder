"""
Compose two packaged Shape Products into one physical Coin.
"""

# File: src/lowkey_artifact_builder/model/models/coin/stages/compose.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from lowkey_artifact_builder.engine import StageContext
from lowkey_artifact_builder.formats.threemf import (
    Component,
    Mesh,
    read,
    read_metadata,
)

# =========================================================
# Face orientation
# =========================================================


def _orient_xy(
    x: float,
    y: float,
    *,
    orientation: str,
) -> tuple[float, float]:
    """
    Orient one Face B planar coordinate into Coin coordinates.

    Aligned orientation rotates Face B 180 degrees around the Y axis.
    Inverted orientation rotates Face B 180 degrees around the X axis.
    """

    if orientation == "aligned":
        return (
            -x,
            y,
        )

    if orientation == "inverted":
        return (
            x,
            -y,
        )

    raise ValueError(f"Unsupported Coin orientation: {orientation!r}.")


# =========================================================
# Compatibility
# =========================================================


def _load_shape_metadata(
    face: Path,
) -> tuple[
    dict[str, str],
    dict[str, Any],
]:
    """
    Load persistent compatibility metadata from a packaged Shape Product.

    Packaged Shape metadata is authoritative for compatibility properties that
    cannot be recovered safely from component geometry, identity, or colors.
    """

    metadata = read_metadata(
        face,
    )

    serialized_compatibility = metadata.get(
        "shape_compatibility",
    )

    if serialized_compatibility is None:
        raise ValueError("Packaged Shape Product is missing Shape compatibility metadata.")

    try:
        compatibility = json.loads(
            serialized_compatibility,
        )
    except json.JSONDecodeError as exc:
        raise ValueError(
            "Packaged Shape Product contains invalid Shape compatibility metadata."
        ) from exc

    if not isinstance(
        compatibility,
        dict,
    ):
        raise ValueError("Packaged Shape Product contains invalid Shape compatibility metadata.")

    return (
        metadata,
        compatibility,
    )


def _validate_face_b(
    metadata: dict[str, str],
) -> None:
    """
    Validate Face B dimensionalization.

    Face B must already use inlaid Shape dimensionalization. Coin consumes
    this producer-owned information from the packaged Shape Product and does
    not reopen Shape configuration or regenerate the Shape.
    """

    raise_style = metadata.get(
        "raise_style",
    )

    if raise_style != "inlaid":
        raise ValueError("Coin Face B must use inlaid Shape dimensionalization.")


def _orient_feature_geometry(
    geometry: Any,
    *,
    orientation: str,
) -> Any:
    """
    Orient bilateral Face B Feature geometry into Coin coordinates.

    Hole and Loop compatibility geometry is producer-owned. Their planar
    centers receive the same orientation used for the physical Face while
    scalar dimensions remain unchanged.
    """

    if geometry is None:
        return None

    if not isinstance(
        geometry,
        dict,
    ):
        return geometry

    center = geometry.get(
        "center",
    )

    if (
        not isinstance(
            center,
            list,
        )
        or len(center) != 2
    ):
        return geometry

    x = center[0]
    y = center[1]

    if not isinstance(
        x,
        int | float,
    ) or not isinstance(
        y,
        int | float,
    ):
        return geometry

    oriented_x, oriented_y = _orient_xy(
        float(x),
        float(y),
        orientation=orientation,
    )

    return {
        **geometry,
        "center": [
            oriented_x,
            oriented_y,
        ],
    }


def _orient_boundary(
    boundary: Any,
    *,
    orientation: str,
) -> Any:
    """
    Orient one producer-owned Face B boundary into Coin coordinates.

    Circle centers and polygon vertices receive the same planar orientation
    used for the complete physical Face. Scalar dimensions remain unchanged.
    Unknown or malformed boundary structures are preserved so compatibility
    validation rejects them rather than manufacturing new semantics.
    """

    if not isinstance(
        boundary,
        dict,
    ):
        return boundary

    kind = boundary.get(
        "kind",
    )

    if kind == "circle":
        center = boundary.get(
            "center",
        )

        if (
            not isinstance(
                center,
                list,
            )
            or len(center) != 2
        ):
            return boundary

        x = center[0]
        y = center[1]

        if not isinstance(
            x,
            int | float,
        ) or not isinstance(
            y,
            int | float,
        ):
            return boundary

        oriented_x, oriented_y = _orient_xy(
            float(x),
            float(y),
            orientation=orientation,
        )

        return {
            **boundary,
            "center": [
                oriented_x,
                oriented_y,
            ],
        }

    if kind == "polygon":
        vertices = boundary.get(
            "vertices",
        )

        if not isinstance(
            vertices,
            list,
        ):
            return boundary

        oriented_vertices: list[list[float]] = []

        for vertex in vertices:
            if (
                not isinstance(
                    vertex,
                    list,
                )
                or len(vertex) != 2
            ):
                return boundary

            x = vertex[0]
            y = vertex[1]

            if not isinstance(
                x,
                int | float,
            ) or not isinstance(
                y,
                int | float,
            ):
                return boundary

            oriented_x, oriented_y = _orient_xy(
                float(x),
                float(y),
                orientation=orientation,
            )

            oriented_vertices.append(
                [
                    oriented_x,
                    oriented_y,
                ]
            )

        return {
            **boundary,
            "vertices": oriented_vertices,
        }

    return boundary


def _canonical_polygon_vertices(
    vertices: Any,
) -> tuple[tuple[float, float], ...] | None:
    """
    Canonicalize one serialized polygon boundary.

    Polygon compatibility is independent of serialized starting vertex and
    winding direction, while preserving the polygon's cyclic edge topology.
    """

    if not isinstance(
        vertices,
        list,
    ):
        return None

    normalized: list[tuple[float, float]] = []

    for vertex in vertices:
        if (
            not isinstance(
                vertex,
                list,
            )
            or len(vertex) != 2
        ):
            return None

        x = vertex[0]
        y = vertex[1]

        if not isinstance(
            x,
            int | float,
        ) or not isinstance(
            y,
            int | float,
        ):
            return None

        normalized.append(
            (
                float(x),
                float(y),
            )
        )

    if not normalized:
        return ()

    forward = tuple(
        normalized,
    )

    reverse = tuple(
        reversed(
            normalized,
        )
    )

    candidates: list[tuple[tuple[float, float], ...]] = []

    for sequence in (
        forward,
        reverse,
    ):
        for offset in range(
            len(sequence),
        ):
            candidates.append(sequence[offset:] + sequence[:offset])

    return min(
        candidates,
    )


def _boundaries_match(
    face_a_boundary: Any,
    face_b_boundary: Any,
    *,
    orientation: str,
) -> bool:
    """
    Compare two physical Shape boundaries in Coin coordinates.

    Face B first receives the same planar orientation used for its complete
    physical Face. Circle boundaries compare their producer-owned geometry
    directly. Polygon boundaries compare canonical cyclic vertex sequences so
    equivalent boundaries are independent of starting vertex and winding.
    """

    oriented_face_b = _orient_boundary(
        face_b_boundary,
        orientation=orientation,
    )

    if not isinstance(
        face_a_boundary,
        dict,
    ) or not isinstance(
        oriented_face_b,
        dict,
    ):
        return face_a_boundary == oriented_face_b

    face_a_kind = face_a_boundary.get(
        "kind",
    )
    face_b_kind = oriented_face_b.get(
        "kind",
    )

    if face_a_kind != face_b_kind:
        return False

    if face_a_kind == "circle":
        return face_a_boundary == oriented_face_b

    if face_a_kind == "polygon":
        face_a_vertices = _canonical_polygon_vertices(
            face_a_boundary.get(
                "vertices",
            )
        )

        face_b_vertices = _canonical_polygon_vertices(
            oriented_face_b.get(
                "vertices",
            )
        )

        if face_a_vertices is None or face_b_vertices is None:
            return False

        face_a_remainder = {
            key: value for key, value in face_a_boundary.items() if key != "vertices"
        }

        face_b_remainder = {
            key: value for key, value in oriented_face_b.items() if key != "vertices"
        }

        return face_a_remainder == face_b_remainder and face_a_vertices == face_b_vertices

    return face_a_boundary == oriented_face_b


def _validate_compatibility(
    face_a: dict[str, Any],
    face_b: dict[str, Any],
    *,
    orientation: str,
) -> None:
    """
    Validate physical compatibility between the two packaged Faces.

    Compatibility is evaluated in Coin coordinates. Face B boundary, Hole,
    and Loop geometry therefore receives the same planar orientation as its
    physical Face before comparison.

    Polygon boundary identity is physical rather than serialization-order
    dependent: equivalent cyclic boundaries may differ in starting vertex or
    winding direction.
    """

    if not _boundaries_match(
        face_a.get(
            "boundary",
        ),
        face_b.get(
            "boundary",
        ),
        orientation=orientation,
    ):
        raise ValueError("Coin Face boundaries are incompatible.")

    face_b_hole = _orient_feature_geometry(
        face_b.get(
            "hole",
        ),
        orientation=orientation,
    )

    if (
        face_a.get(
            "hole",
        )
        != face_b_hole
    ):
        raise ValueError("Coin Face hole geometry is incompatible.")

    face_b_loop = _orient_feature_geometry(
        face_b.get(
            "loop",
        ),
        orientation=orientation,
    )

    if (
        face_a.get(
            "loop",
        )
        != face_b_loop
    ):
        raise ValueError("Coin Face loop geometry is incompatible.")


# =========================================================
# Physical composition
# =========================================================


def _transform_face_b_mesh(
    mesh: Mesh,
    *,
    orientation: str,
) -> Mesh:
    """
    Rigidly transform one Face B mesh across the Z=0 mating plane.

    The planar orientation is shared with compatibility validation. Z is
    negated so Face B occupies the opposite side of the common mating plane.
    """

    vertices = tuple(
        (
            *_orient_xy(
                x,
                y,
                orientation=orientation,
            ),
            -z,
        )
        for x, y, z in mesh.vertices
    )

    return Mesh(
        vertices=vertices,
        triangles=mesh.triangles,
    )


def _compose_faces(
    face_a_components: tuple[Component, ...],
    face_b_components: tuple[Component, ...],
    *,
    orientation: str,
) -> tuple[Component, ...]:
    """
    Compose complete packaged Shape Faces into Coin coordinates.

    Face A retains its packaged placement. Face B receives one common rigid
    transform that places it on the opposite side of the Z=0 mating plane.

    Source component identity is preserved beneath the semantic Face role.
    Resolved physical colors are carried through unchanged.
    """

    face_a = tuple(
        Component(
            name=f"faceA-{component.name}",
            mesh=component.mesh,
            color=component.color,
        )
        for component in face_a_components
    )

    face_b = tuple(
        Component(
            name=f"faceB-{component.name}",
            mesh=_transform_face_b_mesh(
                component.mesh,
                orientation=orientation,
            ),
            color=component.color,
        )
        for component in face_b_components
    )

    return face_a + face_b


# =========================================================
# Physical Product
# =========================================================


def _write_ascii_stl(
    mesh: Mesh,
    path: Path,
) -> None:
    """
    Materialize one physical mesh as an ASCII STL file.

    Coin currently owns this small serialization boundary because no shared
    in-memory Mesh-to-STL writer exists. The persistent Coin Product remains
    the manifest describing the resulting variable physical component set.
    """

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    lines = [
        "solid component",
    ]

    for v1, v2, v3 in mesh.triangles:
        vertices = (
            mesh.vertices[v1],
            mesh.vertices[v2],
            mesh.vertices[v3],
        )

        lines.extend(
            (
                "  facet normal 0 0 0",
                "    outer loop",
            )
        )

        for x, y, z in vertices:
            lines.append(f"      vertex {x:.9g} {y:.9g} {z:.9g}")

        lines.extend(
            (
                "    endloop",
                "  endfacet",
            )
        )

    lines.append("endsolid component")

    path.write_text(
        "\n".join(
            lines,
        )
        + "\n",
        encoding="ascii",
    )


def _write_physical_product(
    components: tuple[Component, ...],
    manifest: Path,
) -> None:
    """
    Persist the physical Coin component collection.

    Component files are deliberately assigned neutral positional filenames.
    """

    manifest.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    physical_components: list[dict[str, object]] = []

    for index, component in enumerate(
        components,
        start=1,
    ):
        component_path = Path(f"component-{index}.stl")

        _write_ascii_stl(
            component.mesh,
            manifest.parent / component_path,
        )

        entry: dict[str, object] = {
            "name": component.name,
            "path": component_path.as_posix(),
        }

        if component.color is not None:
            entry["color"] = {
                "name": component.color.name,
                "rgb": list(
                    component.color.rgb,
                ),
            }

        physical_components.append(
            entry,
        )

    manifest.write_text(
        json.dumps(
            {
                "components": physical_components,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


# =========================================================
# Stage execution
# =========================================================


def execute(
    context: StageContext,
) -> None:
    """
    Compose two packaged Shape Products into one physical Coin.

    Compatibility is determined entirely from producer-owned information
    persisted in the packaged Shape Products. Compatible Faces are consumed
    as complete physical component collections and rigidly composed around
    their shared Z=0 mating plane.
    """

    face_a = context.input(
        "faceA",
    )

    face_b = context.input(
        "faceB",
    )

    _, face_a_compatibility = _load_shape_metadata(
        face_a,
    )

    face_b_metadata, face_b_compatibility = _load_shape_metadata(
        face_b,
    )

    _validate_face_b(
        face_b_metadata,
    )

    orientation = str(
        context.resolver(
            "coin_orientation",
        )
    )

    _validate_compatibility(
        face_a_compatibility,
        face_b_compatibility,
        orientation=orientation,
    )

    face_a_components = read(
        face_a,
    )

    face_b_components = read(
        face_b,
    )

    components = _compose_faces(
        face_a_components,
        face_b_components,
        orientation=orientation,
    )

    physical = context.output(
        "physical",
    )

    _write_physical_product(
        components,
        physical,
    )
