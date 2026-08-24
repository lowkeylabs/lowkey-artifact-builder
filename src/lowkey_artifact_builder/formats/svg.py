"""
Utilities for parsing, inspecting, and manipulating SVG documents.

This module provides format-level operations for SVG files, including
support for document structures and metadata commonly produced by
Inkscape.

It contains no artifact-model or build-stage behavior. Higher-level
subsystems use these operations to inspect and manipulate SVG documents
without depending directly on XML representation details.
"""
# File: src/lowkey_artifact_builder/formats/svg.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import copy
import re
import xml.etree.ElementTree as ET
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

# =========================================================
# Namespaces
# =========================================================


SVG_NS = "http://www.w3.org/2000/svg"
INKSCAPE_NS = "http://www.inkscape.org/namespaces/inkscape"

NS = {
    "svg": SVG_NS,
    "inkscape": INKSCAPE_NS,
}

INKSCAPE_GROUPMODE = f"{{{INKSCAPE_NS}}}groupmode"

INKSCAPE_LABEL = f"{{{INKSCAPE_NS}}}label"


# =========================================================
# Path parsing
# =========================================================


PATH_COMMAND_RE = re.compile(r"[MmLlHhVvCcSsQqTtAaZz]")


# =========================================================
# Errors
# =========================================================


class SVGError(RuntimeError):
    """
    Raised when an SVG document cannot be processed.
    """


# =========================================================
# Internal helpers
# =========================================================


def _root(
    tree: ET.ElementTree[ET.Element[str]],
) -> ET.Element[str]:
    """
    Return the root element of an SVG document.

    Raises:
        SVGError:
            If the document has no root element.
    """

    root = tree.getroot()

    if root is None:
        raise SVGError("SVG document has no root element.")

    return root


# =========================================================
# Specifications
# =========================================================


@dataclass(
    frozen=True,
    slots=True,
)
class SVGSize:
    """
    SVG document dimensions.

    Values are retained exactly as represented in the SVG document.
    """

    width: str | None

    height: str | None

    viewbox: str | None


@dataclass(
    frozen=True,
    slots=True,
)
class SVGLayer:
    """
    An Inkscape layer.
    """

    id: str

    label: str | None


# =========================================================
# Document I/O
# =========================================================


def load(
    path: Path,
) -> ET.ElementTree[ET.Element[str]]:
    """
    Load an SVG document.

    Raises:
        SVGError:
            If the file does not exist or cannot be parsed.
    """

    path = Path(path)

    if not path.is_file():
        raise SVGError(f"SVG file does not exist: {path}")

    try:
        return ET.parse(path)

    except (
        ET.ParseError,
        OSError,
    ) as exc:
        raise SVGError(f"Could not load SVG document {path}: {exc}") from exc


def save(
    tree: ET.ElementTree[ET.Element[str]],
    path: Path,
) -> None:
    """
    Save an SVG document.

    Parent directories are created when necessary.
    """

    path = Path(path)

    try:
        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        ET.register_namespace(
            "",
            SVG_NS,
        )

        ET.register_namespace(
            "inkscape",
            INKSCAPE_NS,
        )

        tree.write(
            path,
            encoding="utf-8",
            xml_declaration=True,
        )

    except OSError as exc:
        raise SVGError(f"Could not save SVG document {path}: {exc}") from exc


# =========================================================
# Document geometry
# =========================================================


def get_size(
    tree: ET.ElementTree[ET.Element[str]],
) -> SVGSize:
    """
    Return the SVG document dimensions.
    """

    root = _root(tree)

    return SVGSize(
        width=root.get("width"),
        height=root.get("height"),
        viewbox=root.get("viewBox"),
    )


def copy_document_geometry(
    source: ET.ElementTree[ET.Element[str]],
    destination: ET.ElementTree[ET.Element[str]],
) -> None:
    """
    Copy document/page geometry from one SVG to another.

    Root-level x, y, width, height, and viewBox attributes are copied
    exactly from source to destination.

    If an attribute does not exist in the source, it is removed from
    the destination.

    Artwork, groups, transforms, and path geometry in the destination
    are left untouched.

    This is useful when independently generated SVG files must retain
    identical registration.
    """

    source_root = _root(source)

    destination_root = _root(destination)

    for attribute in (
        "x",
        "y",
        "width",
        "height",
        "viewBox",
    ):
        value = source_root.get(attribute)

        if value is None:
            destination_root.attrib.pop(
                attribute,
                None,
            )

        else:
            destination_root.set(
                attribute,
                value,
            )


# =========================================================
# Layers
# =========================================================


def get_layers(
    tree: ET.ElementTree[ET.Element[str]],
) -> list[SVGLayer]:
    """
    Return all Inkscape layers in document order.

    Groups without IDs are ignored.
    """

    root = _root(tree)

    layers: list[SVGLayer] = []

    for group in root.findall(
        ".//svg:g",
        NS,
    ):
        if group.get(INKSCAPE_GROUPMODE) != "layer":
            continue

        layer_id = group.get("id")

        if layer_id is None:
            continue

        layers.append(
            SVGLayer(
                id=layer_id,
                label=group.get(INKSCAPE_LABEL),
            )
        )

    return layers


# =========================================================
# Object lookup
# =========================================================


def get_ids(
    tree: ET.ElementTree[ET.Element[str]],
) -> set[str]:
    """
    Return all object IDs in an SVG document.
    """

    return {element_id for element in tree.iter() if (element_id := element.get("id")) is not None}


def has_id(
    tree: ET.ElementTree[ET.Element[str]],
    object_id: str,
) -> bool:
    """
    Return whether an object with the specified ID exists.
    """

    return object_id in get_ids(tree)


def require_ids(
    tree: ET.ElementTree[ET.Element[str]],
    object_ids: Iterable[str],
) -> None:
    """
    Verify that all requested object IDs exist.

    Raises:
        SVGError:
            If one or more IDs are missing.
    """

    ids = get_ids(tree)

    missing = [object_id for object_id in object_ids if object_id not in ids]

    if missing:
        raise SVGError("Missing expected SVG objects: " + ", ".join(missing))


def get_object(
    tree: ET.ElementTree[ET.Element[str]],
    object_id: str,
) -> ET.Element[str]:
    """
    Return the SVG element having the specified ID.

    Raises:
        SVGError:
            If the object does not exist.
    """

    for element in tree.iter():
        if element.get("id") == object_id:
            return element

    raise SVGError(f"SVG object does not exist: {object_id}")


def get_parent(
    tree: ET.ElementTree[ET.Element[str]],
    object_id: str,
) -> ET.Element[str]:
    """
    Return the parent of the object having the specified ID.

    Raises:
        SVGError:
            If the object does not exist or is the document root.
    """

    root = _root(tree)

    for parent in root.iter():
        for child in parent:
            if child.get("id") == object_id:
                return parent

    if root.get("id") == object_id:
        raise SVGError(f"SVG object has no parent: {object_id}")

    raise SVGError(f"SVG object does not exist: {object_id}")


def get_ancestors(
    tree: ET.ElementTree[ET.Element[str]],
    object_id: str,
) -> list[ET.Element[str]]:
    """
    Return the ancestors of an SVG object.

    Ancestors are returned from the document root down to the object's
    immediate parent.

    Raises:
        SVGError:
            If the object does not exist.
    """

    target = get_object(
        tree,
        object_id,
    )

    root = _root(tree)

    def find(
        element: ET.Element[str],
        ancestors: list[ET.Element[str]],
    ) -> list[ET.Element[str]] | None:
        for child in element:
            if child is target:
                return ancestors + [element]

            result = find(
                child,
                ancestors + [element],
            )

            if result is not None:
                return result

        return None

    result = find(
        root,
        [],
    )

    if result is None:
        raise SVGError(f"Could not determine ancestors of SVG object: {object_id}")

    return result


# =========================================================
# Object manipulation
# =========================================================


def copy_object(
    tree: ET.ElementTree[ET.Element[str]],
    object_id: str,
    new_id: str,
) -> ET.Element[str]:
    """
    Copy an SVG object.

    The copy is inserted immediately after the original object in the
    same parent.

    Raises:
        SVGError:
            If the source object does not exist or the new ID already
            exists.
    """

    if has_id(
        tree,
        new_id,
    ):
        raise SVGError(f"SVG object already exists: {new_id}")

    element = get_object(
        tree,
        object_id,
    )

    parent = get_parent(
        tree,
        object_id,
    )

    duplicate = copy.deepcopy(element)

    duplicate.set(
        "id",
        new_id,
    )

    children = list(parent)

    index = children.index(element)

    parent.insert(
        index + 1,
        duplicate,
    )

    return duplicate


def remove_object(
    tree: ET.ElementTree[ET.Element[str]],
    object_id: str,
) -> None:
    """
    Remove an SVG object from the document.

    Raises:
        SVGError:
            If the object does not exist.
    """

    element = get_object(
        tree,
        object_id,
    )

    parent = get_parent(
        tree,
        object_id,
    )

    parent.remove(element)


def rename_object(
    tree: ET.ElementTree[ET.Element[str]],
    object_id: str,
    new_id: str,
) -> ET.Element[str]:
    """
    Rename an SVG object by changing its ID.

    Returns:
        The renamed SVG element.

    Raises:
        SVGError:
            If the source object does not exist or the new ID already
            exists.
    """

    if object_id == new_id:
        return get_object(
            tree,
            object_id,
        )

    if has_id(
        tree,
        new_id,
    ):
        raise SVGError(f"SVG object already exists: {new_id}")

    element = get_object(
        tree,
        object_id,
    )

    element.set(
        "id",
        new_id,
    )

    return element


# =========================================================
# Groups
# =========================================================


def get_first_group_objects(
    tree: ET.ElementTree[ET.Element[str]],
) -> list[str]:
    """
    Return IDs of direct children in the first SVG group.

    Objects without IDs are ignored.

    Raises:
        SVGError:
            If the document contains no group.
    """

    root = _root(tree)

    group = root.find(
        ".//svg:g",
        NS,
    )

    if group is None:
        raise SVGError("SVG document contains no group.")

    return [object_id for child in group if (object_id := child.get("id")) is not None]


# =========================================================
# Inkscape trace structure
# =========================================================


def get_artwork_objects(
    tree: ET.ElementTree[ET.Element[str]],
) -> list[str]:
    """
    Return object IDs from the first group in the first Inkscape layer.

    Expected structure:

        Inkscape layer
            group
                object
                object
                ...

    SVG document order is bottom-to-top for stacked objects. Objects are
    returned top-to-bottom.

    Raises:
        SVGError:
            If the expected structure is not present.
    """

    root = _root(tree)

    layer: ET.Element[str] | None = None

    for group in root.findall(
        ".//svg:g",
        NS,
    ):
        if group.get(INKSCAPE_GROUPMODE) == "layer":
            layer = group
            break

    if layer is None:
        raise SVGError("SVG document contains no Inkscape layer.")

    artwork_group = layer.find(
        "svg:g",
        NS,
    )

    if artwork_group is None:
        raise SVGError("First Inkscape layer contains no group.")

    objects = [object_id for child in artwork_group if (object_id := child.get("id")) is not None]

    if not objects:
        raise SVGError("Artwork group contains no objects with IDs.")

    return list(reversed(objects))


def get_trace_objects(
    tree: ET.ElementTree[ET.Element[str]],
) -> list[str]:
    """
    Return object IDs produced by an Inkscape multicolor bitmap trace.

    Expected structure:

        Inkscape layer
            image
            group
                traced object
                traced object
                ...

    The original raster image is ignored.

    SVG document order is bottom-to-top. Trace objects are returned
    top-to-bottom.

    Raises:
        SVGError:
            If the document contains no multicolor trace group.
    """

    root = _root(tree)

    for layer in root.findall(
        ".//svg:g",
        NS,
    ):
        if layer.get(INKSCAPE_GROUPMODE) != "layer":
            continue

        for child in layer:
            if child.tag != f"{{{SVG_NS}}}g":
                continue

            objects = [
                object_id for element in child if (object_id := element.get("id")) is not None
            ]

            if objects:
                return list(reversed(objects))

    raise SVGError("SVG document contains no multicolor trace group.")


# =========================================================
# Transforms
# =========================================================


def copy_transform(
    source: ET.ElementTree[ET.Element[str]],
    destination: ET.ElementTree[ET.Element[str]],
    object_id: str,
) -> None:
    """
    Copy an object's transform from one SVG document to another.

    If the source object has no transform, the transform is removed
    from the destination object.
    """

    source_object = get_object(
        source,
        object_id,
    )

    destination_object = get_object(
        destination,
        object_id,
    )

    transform = source_object.get("transform")

    if transform is None:
        destination_object.attrib.pop(
            "transform",
            None,
        )

    else:
        destination_object.set(
            "transform",
            transform,
        )


def flatten_ancestor_transforms(
    tree: ET.ElementTree[ET.Element[str]],
    object_id: str,
) -> None:
    """
    Move ancestor transforms onto an SVG object.

    The object's geometry is not rewritten.

    Ancestor transforms are applied from the outermost ancestor toward
    the object. A transform already present directly on the object is
    applied after the ancestor transforms.

    Ancestor transform attributes are removed after being transferred
    so that the transforms are not applied twice.

    This operation changes only where transforms are stored. It does
    not modify path data, points, coordinates, or document geometry.
    """

    element = get_object(
        tree,
        object_id,
    )

    ancestors = get_ancestors(
        tree,
        object_id,
    )

    transforms: list[str] = []

    for ancestor in ancestors:
        transform = ancestor.get("transform")

        if transform:
            transforms.append(transform)

    object_transform = element.get("transform")

    if object_transform:
        transforms.append(object_transform)

    if transforms:
        element.set(
            "transform",
            " ".join(transforms),
        )

    else:
        element.attrib.pop(
            "transform",
            None,
        )

    for ancestor in ancestors:
        ancestor.attrib.pop(
            "transform",
            None,
        )


# =========================================================
# Path inspection
# =========================================================


def count_path_commands(
    element: ET.Element[str],
) -> int:
    """
    Return the number of SVG path commands in a path.

    This provides a useful approximation of path complexity.

    Raises:
        SVGError:
            If the element is not an SVG path.
    """

    if element.tag != f"{{{SVG_NS}}}path":
        raise SVGError("Element is not an SVG path.")

    data = element.get(
        "d",
        "",
    )

    return len(PATH_COMMAND_RE.findall(data))


def get_path_command_counts(
    tree: ET.ElementTree[ET.Element[str]],
) -> dict[str, int]:
    """
    Return path-command counts keyed by object ID.

    Paths without IDs are ignored.
    """

    root = _root(tree)

    counts: dict[str, int] = {}

    for path in root.findall(
        ".//svg:path",
        NS,
    ):
        path_id = path.get("id")

        if path_id is None:
            continue

        counts[path_id] = count_path_commands(path)

    return counts


# =========================================================
# Fill colors
# =========================================================


def get_fill(
    tree: ET.ElementTree[ET.Element[str]],
    object_id: str,
) -> str:
    """
    Return the fill explicitly assigned to an SVG object.

    Fill may be represented as a presentation attribute:

        fill="#aabbcc"

    or within the style attribute:

        style="fill:#aabbcc;stroke:none"

    Inherited fill values are not resolved.

    Raises:
        SVGError:
            If the object does not explicitly define a fill.
    """

    element = get_object(
        tree,
        object_id,
    )

    fill = element.get("fill")

    if fill:
        return fill.strip()

    style = element.get(
        "style",
        "",
    )

    for declaration in style.split(";"):
        if ":" not in declaration:
            continue

        name, value = declaration.split(
            ":",
            1,
        )

        if name.strip() != "fill":
            continue

        value = value.strip()

        if value:
            return value

    raise SVGError(f"SVG object does not define a fill: {object_id}")


def parse_hex_color(
    value: str,
) -> tuple[int, int, int]:
    """
    Parse an SVG hexadecimal color into an RGB tuple.

    Supported forms:

        #rrggbb
        #rgb

    Examples:

        #ff0000 -> (255, 0, 0)
        #abc     -> (170, 187, 204)

    Raises:
        SVGError:
            If the value is not a supported hexadecimal color.
    """

    value = value.strip()

    if len(value) == 7 and value.startswith("#"):
        digits = value[1:]

    elif len(value) == 4 and value.startswith("#"):
        digits = "".join(digit * 2 for digit in value[1:])

    else:
        raise SVGError(f"Unsupported SVG color value: {value}")

    try:
        return (
            int(
                digits[0:2],
                16,
            ),
            int(
                digits[2:4],
                16,
            ),
            int(
                digits[4:6],
                16,
            ),
        )

    except ValueError as exc:
        raise SVGError(f"Invalid SVG hexadecimal color: {value}") from exc


def get_fill_rgb(
    tree: ET.ElementTree[ET.Element[str]],
    object_id: str,
) -> tuple[int, int, int]:
    """
    Return the RGB fill explicitly assigned to an SVG object.
    """

    return parse_hex_color(
        get_fill(
            tree,
            object_id,
        )
    )


def set_fill_rgb(
    tree: ET.ElementTree[ET.Element[str]],
    object_id: str,
    rgb: tuple[int, int, int],
) -> None:
    """
    Set an SVG object's fill to an RGB color.

    An existing fill presentation attribute is replaced.

    If fill is present in the style attribute, that declaration is
    replaced instead so unrelated style properties are preserved.

    If neither representation exists, a fill presentation attribute is
    added.

    Raises:
        SVGError:
            If rgb does not contain exactly three integer values from
            0 through 255.
    """

    if len(rgb) != 3 or any(
        not isinstance(
            component,
            int,
        )
        or component < 0
        or component > 255
        for component in rgb
    ):
        raise SVGError("RGB color must contain three integer values from 0 through 255.")

    element = get_object(
        tree,
        object_id,
    )

    value = f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"

    #
    # Prefer an existing presentation attribute.
    #

    if element.get("fill") is not None:
        element.set(
            "fill",
            value,
        )

        return

    #
    # Otherwise preserve style representation if the
    # fill currently lives there.
    #

    style = element.get("style")

    if style is not None:
        declarations: list[str] = []

        found = False

        for declaration in style.split(";"):
            declaration = declaration.strip()

            if not declaration:
                continue

            if ":" not in declaration:
                declarations.append(declaration)

                continue

            name, existing_value = declaration.split(
                ":",
                1,
            )

            name = name.strip()

            if name == "fill":
                declarations.append(f"fill:{value}")

                found = True

            else:
                declarations.append(f"{name}:{existing_value.strip()}")

        if found:
            element.set(
                "style",
                ";".join(declarations),
            )

            return

    #
    # No explicit fill currently exists.
    #

    element.set(
        "fill",
        value,
    )


__all__ = [
    "INKSCAPE_GROUPMODE",
    "INKSCAPE_LABEL",
    "INKSCAPE_NS",
    "NS",
    "PATH_COMMAND_RE",
    "SVGLayer",
    "SVGError",
    "SVGSize",
    "SVG_NS",
    "copy_document_geometry",
    "copy_object",
    "copy_transform",
    "count_path_commands",
    "flatten_ancestor_transforms",
    "get_ancestors",
    "get_artwork_objects",
    "get_fill",
    "get_fill_rgb",
    "get_first_group_objects",
    "get_ids",
    "get_layers",
    "get_object",
    "get_parent",
    "get_path_command_counts",
    "get_size",
    "get_trace_objects",
    "has_id",
    "load",
    "parse_hex_color",
    "remove_object",
    "rename_object",
    "require_ids",
    "save",
    "set_fill_rgb",
]
