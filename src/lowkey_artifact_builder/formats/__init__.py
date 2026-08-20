"""
Persistent file-format utilities.

This package provides format-level operations for files consumed and
produced by the artifact build system.

Format modules understand the structure and representation of a file
format but do not contain artifact-model or build-stage behavior.
"""

from lowkey_artifact_builder.formats.svg import (
    SVGError,
    SVGLayer,
    SVGSize,
    copy_document_geometry,
    copy_object,
    copy_transform,
    count_path_commands,
    flatten_ancestor_transforms,
    get_ancestors,
    get_artwork_objects,
    get_fill,
    get_fill_rgb,
    get_first_group_objects,
    get_ids,
    get_layers,
    get_object,
    get_parent,
    get_path_command_counts,
    get_size,
    get_trace_objects,
    has_id,
    load,
    parse_hex_color,
    remove_object,
    rename_object,
    require_ids,
    save,
    set_fill_rgb,
)

__all__ = [
    "SVGLayer",
    "SVGError",
    "SVGSize",
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
