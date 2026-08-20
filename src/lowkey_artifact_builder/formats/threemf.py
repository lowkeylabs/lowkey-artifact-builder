"""
Utilities for constructing 3MF documents.

This module provides format-level operations for creating 3MF packages
from independently generated mesh components.

A 3MF file is an OPC/ZIP package containing XML resources and model
metadata. This module owns those representation details so higher-level
subsystems can create 3MF artifacts without depending directly on the
package structure.

It contains no artifact-model or build-stage behavior.
"""

from __future__ import annotations

import struct
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass
from pathlib import Path

# =========================================================
# Namespaces
# =========================================================


CORE_NS = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"

CONTENT_TYPES_NS = "http://schemas.openxmlformats.org/package/2006/content-types"

RELATIONSHIPS_NS = "http://schemas.openxmlformats.org/package/2006/relationships"

MODEL_RELATIONSHIP_TYPE = "http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"

MODEL_CONTENT_TYPE = "application/vnd.ms-package.3dmanufacturing-3dmodel+xml"


# =========================================================
# Errors
# =========================================================


class ThreeMFError(RuntimeError):
    """
    Raised when a 3MF document cannot be constructed.
    """


# =========================================================
# Specifications
# =========================================================


@dataclass(
    frozen=True,
    slots=True,
)
class Mesh:
    """
    Triangle mesh geometry.

    Vertices contain XYZ coordinates in millimeters.

    Triangles contain zero-based indexes into vertices.
    """

    vertices: tuple[
        tuple[
            float,
            float,
            float,
        ],
        ...,
    ]

    triangles: tuple[
        tuple[
            int,
            int,
            int,
        ],
        ...,
    ]


@dataclass(
    frozen=True,
    slots=True,
)
class Component:
    """
    A named mesh component included in a 3MF document.
    """

    name: str

    mesh: Mesh


# =========================================================
# STL loading
# =========================================================


def load_stl(
    path: Path,
) -> Mesh:
    """
    Load an STL mesh.

    Both binary and ASCII STL files are supported.

    Raises:
        ThreeMFError:
            If the STL does not exist or cannot be parsed.
    """

    path = Path(path)

    if not path.is_file():
        raise ThreeMFError(f"STL file does not exist: {path}")

    try:
        data = path.read_bytes()

    except OSError as exc:
        raise ThreeMFError(f"Could not read STL file {path}: {exc}") from exc

    if _is_binary_stl(data):
        return _load_binary_stl(
            data,
            path,
        )

    return _load_ascii_stl(
        data,
        path,
    )


def _is_binary_stl(
    data: bytes,
) -> bool:
    """
    Return whether STL data has a valid binary STL size.
    """

    if len(data) < 84:
        return False

    triangle_count = struct.unpack_from(
        "<I",
        data,
        80,
    )[0]

    expected_size = 84 + triangle_count * 50

    return len(data) == expected_size


def _load_binary_stl(
    data: bytes,
    path: Path,
) -> Mesh:
    """
    Parse binary STL data.
    """

    triangle_count = struct.unpack_from(
        "<I",
        data,
        80,
    )[0]

    vertices: list[
        tuple[
            float,
            float,
            float,
        ]
    ] = []

    triangles: list[
        tuple[
            int,
            int,
            int,
        ]
    ] = []

    vertex_indexes: dict[
        tuple[
            float,
            float,
            float,
        ],
        int,
    ] = {}

    offset = 84

    for _ in range(triangle_count):
        #
        # Skip normal vector.
        #

        offset += 12

        triangle: list[int] = []

        for _ in range(3):
            vertex = struct.unpack_from(
                "<fff",
                data,
                offset,
            )

            offset += 12

            index = vertex_indexes.get(vertex)

            if index is None:
                index = len(vertices)

                vertices.append(vertex)

                vertex_indexes[vertex] = index

            triangle.append(index)

        triangles.append(
            (
                triangle[0],
                triangle[1],
                triangle[2],
            )
        )

        #
        # Skip attribute byte count.
        #

        offset += 2

    return _validate_mesh(
        Mesh(
            vertices=tuple(vertices),
            triangles=tuple(triangles),
        ),
        source=path,
    )


def _load_ascii_stl(
    data: bytes,
    path: Path,
) -> Mesh:
    """
    Parse ASCII STL data.
    """

    try:
        text = data.decode("utf-8")

    except UnicodeDecodeError as exc:
        raise ThreeMFError(f"STL file is neither valid binary nor UTF-8 ASCII STL: {path}") from exc

    vertices: list[
        tuple[
            float,
            float,
            float,
        ]
    ] = []

    triangles: list[
        tuple[
            int,
            int,
            int,
        ]
    ] = []

    vertex_indexes: dict[
        tuple[
            float,
            float,
            float,
        ],
        int,
    ] = {}

    triangle: list[int] = []

    for line in text.splitlines():
        fields = line.strip().split()

        if len(fields) != 4 or fields[0].lower() != "vertex":
            continue

        try:
            vertex = (
                float(fields[1]),
                float(fields[2]),
                float(fields[3]),
            )

        except ValueError as exc:
            raise ThreeMFError(f"Invalid STL vertex in {path}: {line.strip()}") from exc

        index = vertex_indexes.get(vertex)

        if index is None:
            index = len(vertices)

            vertices.append(vertex)

            vertex_indexes[vertex] = index

        triangle.append(index)

        if len(triangle) == 3:
            triangles.append(
                (
                    triangle[0],
                    triangle[1],
                    triangle[2],
                )
            )

            triangle = []

    if triangle:
        raise ThreeMFError(f"Incomplete triangle in ASCII STL file: {path}")

    return _validate_mesh(
        Mesh(
            vertices=tuple(vertices),
            triangles=tuple(triangles),
        ),
        source=path,
    )


# =========================================================
# Mesh validation
# =========================================================


def _validate_mesh(
    mesh: Mesh,
    *,
    source: Path | None = None,
) -> Mesh:
    """
    Validate mesh geometry.
    """

    description = str(source) if source is not None else "mesh"

    if not mesh.vertices:
        raise ThreeMFError(f"{description} contains no vertices.")

    if not mesh.triangles:
        raise ThreeMFError(f"{description} contains no triangles.")

    vertex_count = len(mesh.vertices)

    for triangle in mesh.triangles:
        if len(triangle) != 3:
            raise ThreeMFError(f"{description} contains an invalid triangle.")

        if any(index < 0 or index >= vertex_count for index in triangle):
            raise ThreeMFError(f"{description} contains a triangle referencing an invalid vertex.")

    return mesh


# =========================================================
# 3MF construction
# =========================================================


def write(
    components: tuple[
        Component,
        ...,
    ],
    path: Path,
) -> None:
    """
    Write components to a 3MF package.

    Each component becomes an independent 3MF mesh object
    and is added independently to the build section.

    Namespace registration is deliberately performed at
    serialization time. ElementTree namespace registration
    is process-global, so another subsystem such as SVG
    processing may change the default namespace between
    construction and serialization.

    Raises:
        ThreeMFError:
            If no components are supplied, component names
            are duplicated, mesh geometry is invalid, or
            the package cannot be written.
    """

    path = Path(path)

    if not components:
        raise ThreeMFError("Cannot create a 3MF document without components.")

    _validate_components(components)

    model = _build_model(components)

    content_types = _build_content_types()

    relationships = _build_relationships()

    try:
        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with zipfile.ZipFile(
            path,
            mode="w",
            compression=zipfile.ZIP_DEFLATED,
        ) as package:
            package.writestr(
                "[Content_Types].xml",
                _serialize_xml(
                    content_types,
                    CONTENT_TYPES_NS,
                ),
            )

            package.writestr(
                "_rels/.rels",
                _serialize_xml(
                    relationships,
                    RELATIONSHIPS_NS,
                ),
            )

            package.writestr(
                "3D/3dmodel.model",
                _serialize_xml(
                    model,
                    CORE_NS,
                ),
            )

    except (
        OSError,
        zipfile.BadZipFile,
    ) as exc:
        raise ThreeMFError(f"Could not write 3MF document {path}: {exc}") from exc


def write_stls(
    stls: tuple[
        tuple[
            str,
            Path,
        ],
        ...,
    ],
    path: Path,
) -> None:
    """
    Construct a 3MF document directly from named STL files.

    This is a convenience operation around load_stl()
    and write().
    """

    components = tuple(
        Component(
            name=name,
            mesh=load_stl(stl_path),
        )
        for name, stl_path in stls
    )

    write(
        components,
        path,
    )


# =========================================================
# Component validation
# =========================================================


def _validate_components(
    components: tuple[
        Component,
        ...,
    ],
) -> None:
    """
    Validate components before constructing the package.
    """

    names: set[str] = set()

    for component in components:
        if not component.name:
            raise ThreeMFError("3MF component names must not be empty.")

        if component.name in names:
            raise ThreeMFError(f"Duplicate 3MF component name: {component.name}")

        names.add(component.name)

        _validate_mesh(component.mesh)


# =========================================================
# Model XML
# =========================================================


def _build_model(
    components: tuple[
        Component,
        ...,
    ],
) -> ET.Element:
    """
    Construct the primary 3MF model document.

    Namespace registration intentionally does not occur
    here. The correct default namespace is established
    immediately before serialization.
    """

    model = ET.Element(
        f"{{{CORE_NS}}}model",
        {
            "unit": "millimeter",
        },
    )

    resources = ET.SubElement(
        model,
        f"{{{CORE_NS}}}resources",
    )

    build = ET.SubElement(
        model,
        f"{{{CORE_NS}}}build",
    )

    for object_id, component in enumerate(
        components,
        start=1,
    ):
        _add_mesh_object(
            resources,
            object_id,
            component,
        )

        ET.SubElement(
            build,
            f"{{{CORE_NS}}}item",
            {
                "objectid": str(object_id),
            },
        )

    return model


def _add_mesh_object(
    resources: ET.Element,
    object_id: int,
    component: Component,
) -> None:
    """
    Add one mesh object to model resources.
    """

    object_element = ET.SubElement(
        resources,
        f"{{{CORE_NS}}}object",
        {
            "id": str(object_id),
            "type": "model",
            "name": component.name,
        },
    )

    mesh_element = ET.SubElement(
        object_element,
        f"{{{CORE_NS}}}mesh",
    )

    vertices_element = ET.SubElement(
        mesh_element,
        f"{{{CORE_NS}}}vertices",
    )

    for (
        x,
        y,
        z,
    ) in component.mesh.vertices:
        ET.SubElement(
            vertices_element,
            f"{{{CORE_NS}}}vertex",
            {
                "x": _format_float(x),
                "y": _format_float(y),
                "z": _format_float(z),
            },
        )

    triangles_element = ET.SubElement(
        mesh_element,
        f"{{{CORE_NS}}}triangles",
    )

    for (
        v1,
        v2,
        v3,
    ) in component.mesh.triangles:
        ET.SubElement(
            triangles_element,
            f"{{{CORE_NS}}}triangle",
            {
                "v1": str(v1),
                "v2": str(v2),
                "v3": str(v3),
            },
        )


# =========================================================
# Package metadata
# =========================================================


def _build_content_types() -> ET.Element:
    """
    Construct the OPC content-types document.

    Namespace registration intentionally occurs only during
    serialization.
    """

    types = ET.Element(f"{{{CONTENT_TYPES_NS}}}Types")

    ET.SubElement(
        types,
        f"{{{CONTENT_TYPES_NS}}}Default",
        {
            "Extension": "rels",
            "ContentType": ("application/vnd.openxmlformats-package.relationships+xml"),
        },
    )

    ET.SubElement(
        types,
        f"{{{CONTENT_TYPES_NS}}}Override",
        {
            "PartName": ("/3D/3dmodel.model"),
            "ContentType": (MODEL_CONTENT_TYPE),
        },
    )

    return types


def _build_relationships() -> ET.Element:
    """
    Construct the root OPC relationships document.

    Namespace registration intentionally occurs only during
    serialization.
    """

    relationships = ET.Element(f"{{{RELATIONSHIPS_NS}}}Relationships")

    ET.SubElement(
        relationships,
        f"{{{RELATIONSHIPS_NS}}}Relationship",
        {
            "Target": ("/3D/3dmodel.model"),
            "Id": "rel0",
            "Type": (MODEL_RELATIONSHIP_TYPE),
        },
    )

    return relationships


# =========================================================
# Serialization
# =========================================================


def _serialize_xml(
    root: ET.Element,
    namespace: str,
) -> bytes:
    """
    Serialize an XML document with an XML declaration.

    ElementTree namespace registration is process-global.

    Re-establish the namespace belonging to this document
    immediately before serialization. This prevents another
    XML subsystem from changing the default namespace and
    causing ElementTree to emit namespace prefixes such as
    ``ns0`` into a 3MF package.
    """

    ET.register_namespace(
        "",
        namespace,
    )

    return ET.tostring(
        root,
        encoding="utf-8",
        xml_declaration=True,
    )


def _format_float(
    value: float,
) -> str:
    """
    Format a floating-point coordinate for 3MF XML.

    Unnecessary trailing zeroes are removed while retaining
    sufficient precision for STL-derived geometry.
    """

    return format(
        value,
        ".9g",
    )


__all__ = [
    "CONTENT_TYPES_NS",
    "CORE_NS",
    "Component",
    "MODEL_CONTENT_TYPE",
    "MODEL_RELATIONSHIP_TYPE",
    "Mesh",
    "RELATIONSHIPS_NS",
    "ThreeMFError",
    "load_stl",
    "write",
    "write_stls",
]
