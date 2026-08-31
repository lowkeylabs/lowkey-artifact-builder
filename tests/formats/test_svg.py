"""
Tests for SVG format utilities.
"""
# File: tests/formats/test_svg.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from lowkey_artifact_builder.formats import svg

# =========================================================
# Helpers
# =========================================================


def _tree(
    content: str,
) -> ET.ElementTree[ET.Element[str]]:
    """
    Construct an SVG element tree from text.
    """

    root = ET.fromstring(content)

    return ET.ElementTree(root)


def _root(
    tree: ET.ElementTree[ET.Element[str]],
) -> ET.Element[str]:
    """
    Return the root element of a test SVG document.
    """

    root = tree.getroot()

    assert root is not None

    return root


def _simple_svg() -> ET.ElementTree[ET.Element[str]]:
    """
    Return a simple SVG document containing one Inkscape layer.
    """

    return _tree(
        f"""
        <svg
            xmlns="{svg.SVG_NS}"
            xmlns:inkscape="{svg.INKSCAPE_NS}"
            width="100mm"
            height="80mm"
            viewBox="0 0 100 80"
        >
            <g
                id="layer1"
                inkscape:groupmode="layer"
                inkscape:label="Artwork"
            >
                <path
                    id="path1"
                    d="M 0 0 L 10 10 Z"
                    fill="#ff0000"
                />
                <path
                    id="path2"
                    d="M 10 10 L 20 20 Z"
                    style="fill:#00ff00;stroke:none"
                />
            </g>
        </svg>
        """
    )


# =========================================================
# Document I/O
# =========================================================


def test_load(
    tmp_path: Path,
) -> None:
    """
    SVG documents are loaded from the filesystem.
    """

    path = tmp_path / "example.svg"

    path.write_text(
        f"""
        <svg xmlns="{svg.SVG_NS}">
            <path id="path1" />
        </svg>
        """,
        encoding="utf-8",
    )

    tree = svg.load(path)

    assert _root(tree).tag == f"{{{svg.SVG_NS}}}svg"

    assert svg.has_id(
        tree,
        "path1",
    )


def test_load_rejects_missing_file(
    tmp_path: Path,
) -> None:
    """
    Missing SVG files are rejected.
    """

    with pytest.raises(
        svg.SVGError,
        match="SVG file does not exist",
    ):
        svg.load(tmp_path / "missing.svg")


def test_load_rejects_invalid_xml(
    tmp_path: Path,
) -> None:
    """
    Malformed SVG documents are rejected.
    """

    path = tmp_path / "invalid.svg"

    path.write_text(
        "<svg>",
        encoding="utf-8",
    )

    with pytest.raises(
        svg.SVGError,
        match="Could not load SVG document",
    ):
        svg.load(path)


def test_save(
    tmp_path: Path,
) -> None:
    """
    SVG documents are saved and parent directories are created.
    """

    tree = _simple_svg()

    path = tmp_path / "nested" / "example.svg"

    svg.save(
        tree,
        path,
    )

    assert path.is_file()

    loaded = svg.load(path)

    assert svg.has_id(
        loaded,
        "path1",
    )


# =========================================================
# Specifications
# =========================================================


def test_svg_size_is_immutable() -> None:
    """
    SVG document-size values are immutable.
    """

    size = svg.SVGSize(
        width="100mm",
        height="80mm",
        viewbox="0 0 100 80",
    )

    with pytest.raises(FrozenInstanceError):
        size.width = "200mm"  # type: ignore[misc]


def test_svg_layer_is_immutable() -> None:
    """
    SVG layer values are immutable.
    """

    layer = svg.SVGLayer(
        id="layer1",
        label="Artwork",
    )

    with pytest.raises(FrozenInstanceError):
        layer.id = "changed"  # type: ignore[misc]


# =========================================================
# Document geometry
# =========================================================


def test_get_size() -> None:
    """
    Document dimensions are retained exactly as represented.
    """

    size = svg.get_size(_simple_svg())

    assert size == svg.SVGSize(
        width="100mm",
        height="80mm",
        viewbox="0 0 100 80",
    )


def test_get_size_allows_missing_values() -> None:
    """
    SVG geometry attributes are optional.
    """

    tree = _tree(
        f"""
        <svg xmlns="{svg.SVG_NS}" />
        """
    )

    assert svg.get_size(tree) == svg.SVGSize(
        width=None,
        height=None,
        viewbox=None,
    )


def test_copy_document_geometry() -> None:
    """
    Document geometry is copied without modifying artwork.
    """

    source = _tree(
        f"""
        <svg
            xmlns="{svg.SVG_NS}"
            x="1"
            y="2"
            width="100mm"
            height="80mm"
            viewBox="0 0 100 80"
        />
        """
    )

    destination = _tree(
        f"""
        <svg
            xmlns="{svg.SVG_NS}"
            width="1"
            height="1"
            viewBox="0 0 1 1"
        >
            <path id="path1" />
        </svg>
        """
    )

    svg.copy_document_geometry(
        source,
        destination,
    )

    root = _root(destination)

    assert root.get("x") == "1"
    assert root.get("y") == "2"
    assert root.get("width") == "100mm"
    assert root.get("height") == "80mm"
    assert root.get("viewBox") == "0 0 100 80"

    assert svg.has_id(
        destination,
        "path1",
    )


def test_copy_document_geometry_removes_missing_values() -> None:
    """
    Geometry absent from the source is removed from the destination.
    """

    source = _tree(
        f"""
        <svg
            xmlns="{svg.SVG_NS}"
            width="100mm"
        />
        """
    )

    destination = _tree(
        f"""
        <svg
            xmlns="{svg.SVG_NS}"
            x="1"
            y="2"
            width="1"
            height="1"
            viewBox="0 0 1 1"
        />
        """
    )

    svg.copy_document_geometry(
        source,
        destination,
    )

    root = _root(destination)

    assert root.get("width") == "100mm"

    assert root.get("x") is None
    assert root.get("y") is None
    assert root.get("height") is None
    assert root.get("viewBox") is None


# =========================================================
# Layers
# =========================================================


def test_get_layers() -> None:
    """
    Inkscape layers are returned in document order.
    """

    tree = _tree(
        f"""
        <svg
            xmlns="{svg.SVG_NS}"
            xmlns:inkscape="{svg.INKSCAPE_NS}"
        >
            <g
                id="layer1"
                inkscape:groupmode="layer"
                inkscape:label="First"
            />
            <g id="ordinary-group" />
            <g
                id="layer2"
                inkscape:groupmode="layer"
            />
        </svg>
        """
    )

    assert svg.get_layers(tree) == [
        svg.SVGLayer(
            id="layer1",
            label="First",
        ),
        svg.SVGLayer(
            id="layer2",
            label=None,
        ),
    ]


def test_get_layers_ignores_layers_without_ids() -> None:
    """
    Layers without IDs are not returned.
    """

    tree = _tree(
        f"""
        <svg
            xmlns="{svg.SVG_NS}"
            xmlns:inkscape="{svg.INKSCAPE_NS}"
        >
            <g
                inkscape:groupmode="layer"
                inkscape:label="Unnamed"
            />
        </svg>
        """
    )

    assert svg.get_layers(tree) == []


# =========================================================
# Object lookup
# =========================================================


def test_get_ids() -> None:
    """
    All explicitly assigned SVG IDs are returned.
    """

    assert svg.get_ids(_simple_svg()) == {
        "layer1",
        "path1",
        "path2",
    }


def test_has_id() -> None:
    """
    Object existence can be queried by ID.
    """

    tree = _simple_svg()

    assert svg.has_id(
        tree,
        "path1",
    )

    assert not svg.has_id(
        tree,
        "missing",
    )


def test_require_ids() -> None:
    """
    Existing required IDs are accepted.
    """

    svg.require_ids(
        _simple_svg(),
        (
            "path1",
            "path2",
        ),
    )


def test_require_ids_rejects_missing_objects() -> None:
    """
    Missing required IDs are reported together.
    """

    with pytest.raises(
        svg.SVGError,
        match="path3",
    ) as exc_info:
        svg.require_ids(
            _simple_svg(),
            (
                "path1",
                "path3",
                "path4",
            ),
        )

    assert "path4" in str(exc_info.value)


def test_get_object() -> None:
    """
    SVG objects are located by ID.
    """

    element = svg.get_object(
        _simple_svg(),
        "path1",
    )

    assert element.get("id") == "path1"


def test_get_object_rejects_missing_object() -> None:
    """
    Missing object IDs are rejected.
    """

    with pytest.raises(
        svg.SVGError,
        match="SVG object does not exist",
    ):
        svg.get_object(
            _simple_svg(),
            "missing",
        )


def test_get_parent() -> None:
    """
    The direct parent of an SVG object can be obtained.
    """

    parent = svg.get_parent(
        _simple_svg(),
        "path1",
    )

    assert parent.get("id") == "layer1"


def test_get_parent_rejects_document_root() -> None:
    """
    The document root has no parent.
    """

    tree = _tree(
        f"""
        <svg
            xmlns="{svg.SVG_NS}"
            id="root"
        />
        """
    )

    with pytest.raises(
        svg.SVGError,
        match="has no parent",
    ):
        svg.get_parent(
            tree,
            "root",
        )


def test_get_ancestors() -> None:
    """
    Ancestors are returned from root to immediate parent.
    """

    tree = _tree(
        f"""
        <svg
            xmlns="{svg.SVG_NS}"
            id="root"
        >
            <g id="outer">
                <g id="inner">
                    <path id="path1" />
                </g>
            </g>
        </svg>
        """
    )

    ancestors = svg.get_ancestors(
        tree,
        "path1",
    )

    assert [element.get("id") for element in ancestors] == [
        "root",
        "outer",
        "inner",
    ]


# =========================================================
# Object manipulation
# =========================================================


def test_copy_object() -> None:
    """
    SVG objects can be copied beside their originals.
    """

    tree = _simple_svg()

    duplicate = svg.copy_object(
        tree,
        "path1",
        "path1-copy",
    )

    assert duplicate.get("id") == "path1-copy"

    parent = svg.get_parent(
        tree,
        "path1",
    )

    assert [child.get("id") for child in parent] == [
        "path1",
        "path1-copy",
        "path2",
    ]


def test_copy_object_is_deep_copy() -> None:
    """
    Descendants of copied objects are independently copied.
    """

    tree = _tree(
        f"""
        <svg xmlns="{svg.SVG_NS}">
            <g id="group1">
                <path id="child1" />
            </g>
        </svg>
        """
    )

    duplicate = svg.copy_object(
        tree,
        "group1",
        "group2",
    )

    duplicate_child = list(duplicate)[0]

    duplicate_child.set(
        "data-test",
        "changed",
    )

    original_child = svg.get_object(
        tree,
        "child1",
    )

    assert original_child.get("data-test") is None


def test_copy_object_rejects_duplicate_id() -> None:
    """
    A copied object cannot reuse an existing ID.
    """

    with pytest.raises(
        svg.SVGError,
        match="already exists",
    ):
        svg.copy_object(
            _simple_svg(),
            "path1",
            "path2",
        )


def test_remove_object() -> None:
    """
    SVG objects can be removed.
    """

    tree = _simple_svg()

    svg.remove_object(
        tree,
        "path1",
    )

    assert not svg.has_id(
        tree,
        "path1",
    )


def test_rename_object() -> None:
    """
    SVG object IDs can be renamed.
    """

    tree = _simple_svg()

    element = svg.rename_object(
        tree,
        "path1",
        "renamed",
    )

    assert element.get("id") == "renamed"

    assert not svg.has_id(
        tree,
        "path1",
    )

    assert svg.has_id(
        tree,
        "renamed",
    )


def test_rename_object_to_same_id() -> None:
    """
    Renaming an object to its current ID is harmless.
    """

    tree = _simple_svg()

    element = svg.rename_object(
        tree,
        "path1",
        "path1",
    )

    assert element.get("id") == "path1"


def test_rename_object_rejects_duplicate_id() -> None:
    """
    Object IDs must remain unique.
    """

    with pytest.raises(
        svg.SVGError,
        match="already exists",
    ):
        svg.rename_object(
            _simple_svg(),
            "path1",
            "path2",
        )


# =========================================================
# Groups
# =========================================================


def test_get_first_group_objects() -> None:
    """
    Direct children of the first SVG group are returned.
    """

    assert svg.get_first_group_objects(_simple_svg()) == [
        "path1",
        "path2",
    ]


def test_get_first_group_objects_rejects_missing_group() -> None:
    """
    Documents without groups are rejected.
    """

    tree = _tree(
        f"""
        <svg xmlns="{svg.SVG_NS}">
            <path id="path1" />
        </svg>
        """
    )

    with pytest.raises(
        svg.SVGError,
        match="contains no group",
    ):
        svg.get_first_group_objects(tree)


# =========================================================
# Inkscape trace structure
# =========================================================


def test_get_artwork_objects() -> None:
    """
    Artwork objects are returned top-to-bottom.
    """

    tree = _tree(
        f"""
        <svg
            xmlns="{svg.SVG_NS}"
            xmlns:inkscape="{svg.INKSCAPE_NS}"
        >
            <g
                id="layer1"
                inkscape:groupmode="layer"
            >
                <g id="artwork">
                    <path id="bottom" />
                    <path id="middle" />
                    <path id="top" />
                </g>
            </g>
        </svg>
        """
    )

    assert svg.get_artwork_objects(tree) == [
        "top",
        "middle",
        "bottom",
    ]


def test_get_artwork_objects_requires_layer() -> None:
    """
    Artwork inspection requires an Inkscape layer.
    """

    tree = _tree(
        f"""
        <svg xmlns="{svg.SVG_NS}">
            <g id="group1" />
        </svg>
        """
    )

    with pytest.raises(
        svg.SVGError,
        match="no Inkscape layer",
    ):
        svg.get_artwork_objects(tree)


def test_get_artwork_objects_requires_group() -> None:
    """
    The first Inkscape layer must contain an artwork group.
    """

    tree = _tree(
        f"""
        <svg
            xmlns="{svg.SVG_NS}"
            xmlns:inkscape="{svg.INKSCAPE_NS}"
        >
            <g
                id="layer1"
                inkscape:groupmode="layer"
            >
                <path id="path1" />
            </g>
        </svg>
        """
    )

    with pytest.raises(
        svg.SVGError,
        match="contains no group",
    ):
        svg.get_artwork_objects(tree)


def test_get_trace_objects() -> None:
    """
    Multicolor trace objects are returned top-to-bottom.
    """

    tree = _tree(
        f"""
        <svg
            xmlns="{svg.SVG_NS}"
            xmlns:inkscape="{svg.INKSCAPE_NS}"
        >
            <g
                id="layer1"
                inkscape:groupmode="layer"
            >
                <image id="image1" />
                <g id="trace">
                    <path id="bottom" />
                    <path id="middle" />
                    <path id="top" />
                </g>
            </g>
        </svg>
        """
    )

    assert svg.get_trace_objects(tree) == [
        "top",
        "middle",
        "bottom",
    ]


def test_get_trace_objects_ignores_original_image() -> None:
    """
    The raster image accompanying an Inkscape trace is ignored.
    """

    tree = _tree(
        f"""
        <svg
            xmlns="{svg.SVG_NS}"
            xmlns:inkscape="{svg.INKSCAPE_NS}"
        >
            <g
                id="layer1"
                inkscape:groupmode="layer"
            >
                <image id="source-image" />
                <g id="trace">
                    <path id="path1" />
                </g>
            </g>
        </svg>
        """
    )

    assert svg.get_trace_objects(tree) == [
        "path1",
    ]


def test_get_trace_objects_rejects_missing_trace() -> None:
    """
    Documents without a multicolor trace group are rejected.
    """

    tree = _tree(
        f"""
        <svg
            xmlns="{svg.SVG_NS}"
            xmlns:inkscape="{svg.INKSCAPE_NS}"
        >
            <g
                id="layer1"
                inkscape:groupmode="layer"
            >
                <image id="source-image" />
            </g>
        </svg>
        """
    )

    with pytest.raises(
        svg.SVGError,
        match="no multicolor trace group",
    ):
        svg.get_trace_objects(tree)


# =========================================================
# Transforms
# =========================================================


def test_copy_transform() -> None:
    """
    Object transforms can be copied between documents.
    """

    source = _tree(
        f"""
        <svg xmlns="{svg.SVG_NS}">
            <path
                id="path1"
                transform="translate(10,20)"
            />
        </svg>
        """
    )

    destination = _tree(
        f"""
        <svg xmlns="{svg.SVG_NS}">
            <path id="path1" />
        </svg>
        """
    )

    svg.copy_transform(
        source,
        destination,
        "path1",
    )

    assert (
        svg.get_object(
            destination,
            "path1",
        ).get("transform")
        == "translate(10,20)"
    )


def test_copy_transform_removes_missing_transform() -> None:
    """
    Absence of a source transform removes the destination transform.
    """

    source = _tree(
        f"""
        <svg xmlns="{svg.SVG_NS}">
            <path id="path1" />
        </svg>
        """
    )

    destination = _tree(
        f"""
        <svg xmlns="{svg.SVG_NS}">
            <path
                id="path1"
                transform="scale(2)"
            />
        </svg>
        """
    )

    svg.copy_transform(
        source,
        destination,
        "path1",
    )

    assert (
        svg.get_object(
            destination,
            "path1",
        ).get("transform")
        is None
    )


def test_flatten_ancestor_transforms() -> None:
    """
    Ancestor transforms are transferred to the object in order.
    """

    tree = _tree(
        f"""
        <svg
            xmlns="{svg.SVG_NS}"
            id="root"
            transform="translate(1,2)"
        >
            <g
                id="outer"
                transform="translate(10,20)"
            >
                <g
                    id="inner"
                    transform="scale(2)"
                >
                    <path
                        id="path1"
                        transform="rotate(45)"
                    />
                </g>
            </g>
        </svg>
        """
    )

    svg.flatten_ancestor_transforms(
        tree,
        "path1",
    )

    path = svg.get_object(
        tree,
        "path1",
    )

    assert path.get("transform") == ("translate(1,2) translate(10,20) scale(2) rotate(45)")

    assert _root(tree).get("transform") is None

    assert (
        svg.get_object(
            tree,
            "outer",
        ).get("transform")
        is None
    )

    assert (
        svg.get_object(
            tree,
            "inner",
        ).get("transform")
        is None
    )


def test_flatten_ancestor_transforms_without_transforms() -> None:
    """
    Flattening an untransformed object leaves no transform attribute.
    """

    tree = _tree(
        f"""
        <svg xmlns="{svg.SVG_NS}">
            <g id="group1">
                <path id="path1" />
            </g>
        </svg>
        """
    )

    svg.flatten_ancestor_transforms(
        tree,
        "path1",
    )

    assert (
        svg.get_object(
            tree,
            "path1",
        ).get("transform")
        is None
    )


def test_materialize_transform_translates_linear_path_geometry() -> None:
    """
    Translation can be materialized directly into linear path geometry.
    """

    tree = _tree(
        f"""
        <svg xmlns="{svg.SVG_NS}">
            <path
                id="path1"
                d="M 10 20 L 30 20 L 30 40 L 10 40 Z"
            />
        </svg>
        """
    )

    svg.materialize_transform(
        svg.get_object(
            tree,
            "path1",
        ),
        translate_x=-10.0,
        translate_y=-20.0,
    )

    path = svg.get_object(
        tree,
        "path1",
    )

    assert path.get("d") == ("M 0 0 L 20 0 L 20 20 L 0 20 Z")

    assert path.get("transform") is None


def test_materialize_transform_scales_and_translates_rect_geometry() -> None:
    """
    Uniform scale and translation can be materialized into rectangle geometry.
    """

    tree = _tree(
        f"""
        <svg xmlns="{svg.SVG_NS}">
            <rect
                x="36"
                y="42"
                width="128"
                height="96"
            />
        </svg>
        """
    )

    rect = next(_root(tree).iter(f"{{{svg.SVG_NS}}}rect"))

    svg.materialize_transform(
        rect,
        scale=0.625,
        translate_x=-22.5,
        translate_y=-16.25,
    )

    assert rect.get("x") == "0"
    assert rect.get("y") == "10"
    assert rect.get("width") == "80"
    assert rect.get("height") == "60"
    assert rect.get("transform") is None


def test_materialize_transform_scales_and_translates_linear_path_geometry() -> None:
    """
    Uniform scale and translation can be materialized into path geometry.
    """

    tree = _tree(
        f"""
        <svg xmlns="{svg.SVG_NS}">
            <path
                id="path1"
                d="M 36 42 L 164 42 L 164 138 L 36 138 Z"
            />
        </svg>
        """
    )

    svg.materialize_transform(
        svg.get_object(
            tree,
            "path1",
        ),
        scale=0.625,
        translate_x=-22.5,
        translate_y=-16.25,
    )

    path = svg.get_object(
        tree,
        "path1",
    )

    assert path.get("d") == ("M 0 10 L 80 10 L 80 70 L 0 70 Z")

    assert path.get("transform") is None


# =========================================================
# Path inspection
# =========================================================


def test_count_path_commands() -> None:
    """
    SVG path commands provide a simple path-complexity measurement.
    """

    tree = _tree(
        f"""
        <svg xmlns="{svg.SVG_NS}">
            <path
                id="path1"
                d="M 0 0 L 10 10 C 1 2 3 4 5 6 Z"
            />
        </svg>
        """
    )

    element = svg.get_object(
        tree,
        "path1",
    )

    assert svg.count_path_commands(element) == 4


def test_count_path_commands_handles_relative_commands() -> None:
    """
    Relative SVG path commands are counted.
    """

    tree = _tree(
        f"""
        <svg xmlns="{svg.SVG_NS}">
            <path
                id="path1"
                d="m 0 0 l 10 10 h 5 v 5 z"
            />
        </svg>
        """
    )

    assert (
        svg.count_path_commands(
            svg.get_object(
                tree,
                "path1",
            )
        )
        == 5
    )


def test_count_path_commands_rejects_non_path() -> None:
    """
    Path-command counting requires an SVG path element.
    """

    tree = _tree(
        f"""
        <svg xmlns="{svg.SVG_NS}">
            <rect id="rect1" />
        </svg>
        """
    )

    with pytest.raises(
        svg.SVGError,
        match="not an SVG path",
    ):
        svg.count_path_commands(
            svg.get_object(
                tree,
                "rect1",
            )
        )


def test_get_path_command_counts() -> None:
    """
    Path-command counts are returned by object ID.
    """

    tree = _tree(
        f"""
        <svg xmlns="{svg.SVG_NS}">
            <path
                id="path1"
                d="M 0 0 L 1 1 Z"
            />
            <path
                id="path2"
                d="M 0 0 C 1 2 3 4 5 6 Z"
            />
            <path
                d="M 0 0 Z"
            />
        </svg>
        """
    )

    assert svg.get_path_command_counts(tree) == {
        "path1": 3,
        "path2": 3,
    }


# =========================================================
# Fill colors
# =========================================================


def test_get_fill_from_attribute() -> None:
    """
    Presentation-attribute fills are returned.
    """

    assert (
        svg.get_fill(
            _simple_svg(),
            "path1",
        )
        == "#ff0000"
    )


def test_get_fill_from_style() -> None:
    """
    Style-declaration fills are returned.
    """

    assert (
        svg.get_fill(
            _simple_svg(),
            "path2",
        )
        == "#00ff00"
    )


def test_get_fill_prefers_attribute() -> None:
    """
    A presentation fill takes precedence over a style fill.
    """

    tree = _tree(
        f"""
        <svg xmlns="{svg.SVG_NS}">
            <path
                id="path1"
                fill="#ff0000"
                style="fill:#00ff00"
            />
        </svg>
        """
    )

    assert (
        svg.get_fill(
            tree,
            "path1",
        )
        == "#ff0000"
    )


def test_get_fill_rejects_missing_fill() -> None:
    """
    Objects without explicit fill values are rejected.
    """

    tree = _tree(
        f"""
        <svg xmlns="{svg.SVG_NS}">
            <path id="path1" />
        </svg>
        """
    )

    with pytest.raises(
        svg.SVGError,
        match="does not define a fill",
    ):
        svg.get_fill(
            tree,
            "path1",
        )


@pytest.mark.parametrize(
    (
        "value",
        "expected",
    ),
    [
        (
            "#ff0000",
            (255, 0, 0),
        ),
        (
            "#00FF80",
            (0, 255, 128),
        ),
        (
            "#abc",
            (170, 187, 204),
        ),
        (
            " #123456 ",
            (18, 52, 86),
        ),
    ],
)
def test_parse_hex_color(
    value: str,
    expected: tuple[int, int, int],
) -> None:
    """
    Supported SVG hexadecimal colors are converted to RGB.
    """

    assert svg.parse_hex_color(value) == expected


@pytest.mark.parametrize(
    "value",
    [
        "red",
        "rgb(1,2,3)",
        "#12",
        "#12345",
        "#12345678",
    ],
)
def test_parse_hex_color_rejects_unsupported_values(
    value: str,
) -> None:
    """
    Unsupported SVG color representations are rejected.
    """

    with pytest.raises(
        svg.SVGError,
        match="Unsupported SVG color value",
    ):
        svg.parse_hex_color(value)


def test_parse_hex_color_rejects_invalid_hexadecimal() -> None:
    """
    Invalid hexadecimal digits are rejected.
    """

    with pytest.raises(
        svg.SVGError,
        match="Invalid SVG hexadecimal color",
    ):
        svg.parse_hex_color("#gg0000")


def test_get_fill_rgb() -> None:
    """
    Object fill values can be obtained directly as RGB.
    """

    assert svg.get_fill_rgb(
        _simple_svg(),
        "path2",
    ) == (
        0,
        255,
        0,
    )


def test_set_fill_rgb_updates_attribute() -> None:
    """
    Existing presentation fill attributes are replaced.
    """

    tree = _simple_svg()

    svg.set_fill_rgb(
        tree,
        "path1",
        (
            1,
            2,
            255,
        ),
    )

    element = svg.get_object(
        tree,
        "path1",
    )

    assert element.get("fill") == "#0102ff"


def test_set_fill_rgb_updates_style() -> None:
    """
    Existing style fills are replaced without losing other declarations.
    """

    tree = _simple_svg()

    svg.set_fill_rgb(
        tree,
        "path2",
        (
            1,
            2,
            3,
        ),
    )

    element = svg.get_object(
        tree,
        "path2",
    )

    assert element.get("style") == ("fill:#010203;stroke:none")

    assert element.get("fill") is None


def test_set_fill_rgb_adds_attribute() -> None:
    """
    A presentation fill is added when no explicit fill exists.
    """

    tree = _tree(
        f"""
        <svg xmlns="{svg.SVG_NS}">
            <path
                id="path1"
                style="stroke:none"
            />
        </svg>
        """
    )

    svg.set_fill_rgb(
        tree,
        "path1",
        (
            10,
            20,
            30,
        ),
    )

    element = svg.get_object(
        tree,
        "path1",
    )

    assert element.get("fill") == "#0a141e"

    assert element.get("style") == "stroke:none"


@pytest.mark.parametrize(
    "rgb",
    [
        (),
        (1, 2),
        (1, 2, 3, 4),
        (-1, 2, 3),
        (1, 2, 256),
        (1.0, 2, 3),
    ],
)
def test_set_fill_rgb_rejects_invalid_color(
    rgb: tuple[object, ...],
) -> None:
    """
    RGB colors must contain exactly three byte-sized integers.
    """

    with pytest.raises(
        svg.SVGError,
        match="three integer values",
    ):
        svg.set_fill_rgb(
            _simple_svg(),
            "path1",
            rgb,  # type: ignore[arg-type]
        )
