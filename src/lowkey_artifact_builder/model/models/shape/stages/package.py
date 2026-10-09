"""
Shape packaging stage.

The package stage combines independently produced physical Shape components
into the final multicomponent 3MF artifact.

Filesystem layout and dependency resolution are responsibilities of the build
engine. This implementation consumes the physical-component manifest supplied
through StageContext and resolves component files relative to that manifest.

Packaging does not determine which physical components a Shape contains.
Component membership and geometry are established by the upstream extrusion
stage.

Shape-owned components preserve logical component identity through extrusion.
Package resolves their physical printer colors. Incorporated Artwork components
preserve persistent Artifact-color identity through extrusion; Package resolves
those logical Artwork colors to physical printer colors.
"""

# File: src/lowkey_artifact_builder/model/models/shape/stages/package.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from lowkey_artifact_builder.colors import (
    ColorError,
    MeasuredColor,
    PaletteColor,
    assign_colors,
    resolve_palette,
)
from lowkey_artifact_builder.engine import StageContext
from lowkey_artifact_builder.formats.threemf import (
    Component,
    ThreeMFError,
    component_name,
    load_stl,
    write,
)


# =========================================================
# Errors
# =========================================================
class PackageError(RuntimeError):
    """
    Raised when Shape packaging cannot be completed.
    """


# =========================================================
# Component metadata
# =========================================================
@dataclass(
    frozen=True,
    slots=True,
)
class PhysicalComponent:
    """
    Physical Shape component described by the extrusion manifest.

    Shape-owned components preserve logical component identity only.
    Their physical printer colors are resolved by Package.

    Incorporated Artwork components additionally preserve persistent
    Artifact-color identity so Package can resolve those logical colors
    against printer_colors.
    """

    name: str
    path: Path
    artifact_color_index: int | None
    artifact_color: tuple[int, int, int] | None


# =========================================================
# Stage implementation
# =========================================================


def execute(
    context: StageContext,
) -> None:
    """
    Execute the Shape package stage.

    Shape-owned physical colors are resolved here. Base resolves
    shape_base_color. Outer Ridge, Inner Ridge, Loop, and Artwork Fill inherit the
    resolved base color unless their optional Package-time overrides are
    explicitly configured.

    Incorporated Artwork preserves Artifact-color identity through extrusion.
    Package resolves those logical colors against printer_colors using the
    shared global one-to-one color assignment.

    Package also publishes persistent Shape-level metadata required by
    downstream consumers of the packaged Shape Product.
    """
    manifest = context.input("extrude.manifest")
    artifact = context.output("artifact")

    if not manifest.is_file():
        raise PackageError(f"Shape component manifest does not exist: {manifest}")

    try:
        physical_components, compatibility = _load_manifest(
            manifest,
        )
        shape_components = tuple(
            component for component in physical_components if component.artifact_color_index is None
        )
        artwork_components = tuple(
            component
            for component in physical_components
            if component.artifact_color_index is not None
        )

        shape_colors = _resolve_shape_component_colors(
            shape_components,
            context=context,
        )

        assigned_colors: dict[int, PaletteColor] = {}

        if artwork_components:
            measured_colors = tuple(
                MeasuredColor(
                    index=component.artifact_color_index,
                    rgb=component.artifact_color,
                )
                for component in artwork_components
                if (
                    component.artifact_color_index is not None
                    and component.artifact_color is not None
                )
            )

            if len(measured_colors) != len(artwork_components):
                raise PackageError(
                    "Incorporated Artwork components must preserve Artifact-color identity."
                )

            printer_color_names = context.resolver("printer_colors")
            palette = resolve_palette(
                printer_color_names,
                context.resolver.colors,
            )
            assignment_result = assign_colors(
                measured_colors,
                palette,
            )
            assigned_colors = {
                assignment.measured.index: assignment.color
                for assignment in assignment_result.assignments
            }

        component_colors = tuple(
            (
                physical_component,
                _resolve_component_color(
                    physical_component,
                    shape_colors=shape_colors,
                    assigned_colors=assigned_colors,
                ),
            )
            for physical_component in physical_components
        )

        components = tuple(
            Component(
                name=_component_name(
                    context.artifact_id,
                    physical_component.name,
                    color.name,
                ),
                mesh=load_stl(physical_component.path),
                color=color,
            )
            for physical_component, color in component_colors
        )

        raise_style = context.resolver(
            "shape_raise_style",
        )

        write(
            components,
            artifact,
            metadata={
                "raise_style": raise_style,
                "shape_compatibility": json.dumps(
                    compatibility,
                    separators=(",", ":"),
                    sort_keys=True,
                ),
            },
        )

        if not artifact.is_file():
            raise PackageError(
                f"3MF packaging completed without creating the expected artifact: {artifact}"
            )

    except PackageError:
        raise
    except ColorError as exc:
        raise PackageError(f"Could not resolve Shape physical printer colors: {exc}") from exc
    except ThreeMFError as exc:
        raise PackageError(
            f"Could not package Shape components from manifest {manifest}: {exc}"
        ) from exc
    except (
        OSError,
        ValueError,
        TypeError,
        KeyError,
        json.JSONDecodeError,
    ) as exc:
        raise PackageError(
            f"Could not package Shape components from manifest {manifest}: {exc}"
        ) from exc


def _resolve_shape_component_colors(
    components: tuple[PhysicalComponent, ...],
    *,
    context: StageContext,
) -> dict[str, PaletteColor]:
    """
    Resolve physical printer colors for Shape-owned components.

    The structural base establishes the inherited Shape color. Outer Ridge,
    Inner Ridge, Border Labels, Artwork Fill, and Loop inherit that color
    unless an explicit Package-time override is configured. Physical color
    policy does not determine participation.
    """

    component_names = {component.name for component in components}

    if not component_names:
        return {}

    supported_names = {
        "base",
        "ridge",
        "inner-ridge",
        "top-border-label",
        "bottom-border-label",
        "artwork-fill",
        "loop",
    }

    unsupported_names = component_names - supported_names

    if unsupported_names:
        unsupported = ", ".join(
            sorted(
                unsupported_names,
            )
        )

        raise PackageError(
            "Shape extrusion manifest contains unsupported Shape-owned "
            f"component(s): {unsupported}."
        )

    if "base" not in component_names:
        raise PackageError(
            "Shape extrusion manifest contains Shape-owned components without a structural base."
        )

    base_color_name = context.resolver(
        "shape_base_color",
    )

    base_color = resolve_palette(
        (base_color_name,),
        context.resolver.colors,
    )[0]

    colors: dict[str, PaletteColor] = {
        "base": base_color,
    }

    if "ridge" in component_names:
        if context.resolver.has(
            "shape_outer_ridge_color",
        ):
            ridge_color_name = context.resolver(
                "shape_outer_ridge_color",
            )

            ridge_color = resolve_palette(
                (ridge_color_name,),
                context.resolver.colors,
            )[0]
        else:
            ridge_color = base_color

        colors["ridge"] = ridge_color

    if "inner-ridge" in component_names:
        if context.resolver.has(
            "shape_inner_ridge_color",
        ):
            inner_ridge_color_name = context.resolver(
                "shape_inner_ridge_color",
            )

            inner_ridge_color = resolve_palette(
                (inner_ridge_color_name,),
                context.resolver.colors,
            )[0]
        else:
            inner_ridge_color = base_color

        colors["inner-ridge"] = inner_ridge_color

    if "top-border-label" in component_names:
        if context.resolver.has(
            "shape_top_border_label_color",
        ):
            top_border_label_color_name = context.resolver(
                "shape_top_border_label_color",
            )

            top_border_label_color = resolve_palette(
                (top_border_label_color_name,),
                context.resolver.colors,
            )[0]
        else:
            top_border_label_color = base_color

        colors["top-border-label"] = top_border_label_color

    if "bottom-border-label" in component_names:
        if context.resolver.has(
            "shape_bottom_border_label_color",
        ):
            bottom_border_label_color_name = context.resolver(
                "shape_bottom_border_label_color",
            )

            bottom_border_label_color = resolve_palette(
                (bottom_border_label_color_name,),
                context.resolver.colors,
            )[0]
        else:
            bottom_border_label_color = base_color

        colors["bottom-border-label"] = bottom_border_label_color

    if "artwork-fill" in component_names:
        if context.resolver.has(
            "shape_artwork_fill_color",
        ):
            artwork_fill_color_name = context.resolver(
                "shape_artwork_fill_color",
            )

            artwork_fill_color = resolve_palette(
                (artwork_fill_color_name,),
                context.resolver.colors,
            )[0]
        else:
            artwork_fill_color = base_color

        colors["artwork-fill"] = artwork_fill_color

    if "loop" in component_names:
        if context.resolver.has(
            "shape_loop_color",
        ):
            loop_color_name = context.resolver(
                "shape_loop_color",
            )

            loop_color = resolve_palette(
                (loop_color_name,),
                context.resolver.colors,
            )[0]

        else:
            loop_color = base_color

        colors["loop"] = loop_color

    return colors


def _resolve_component_color(
    component: PhysicalComponent,
    *,
    shape_colors: dict[str, PaletteColor],
    assigned_colors: dict[int, PaletteColor],
) -> PaletteColor:
    """
    Resolve the physical printer color for one Shape component.
    """
    artifact_color_index = component.artifact_color_index

    if artifact_color_index is None:
        try:
            return shape_colors[component.name]
        except KeyError as exc:
            raise PackageError(
                f"Shape component {component.name!r} has no resolved physical color."
            ) from exc

    try:
        return assigned_colors[artifact_color_index]
    except KeyError as exc:
        raise PackageError(
            f"Shape component {component.name!r} references unknown "
            f"Artifact color index {artifact_color_index}."
        ) from exc


# =========================================================
# Component manifest
# =========================================================


def _load_manifest(
    manifest: Path,
) -> tuple[
    tuple[PhysicalComponent, ...],
    dict[str, object],
]:
    """
    Load the physical Shape Product manifest.

    Extrude establishes physical component membership and resolved Shape
    compatibility. Package validates and preserves both without reconstructing
    either from Shape configuration or physical geometry.
    """

    data = json.loads(
        manifest.read_text(
            encoding="utf-8",
        )
    )

    if not isinstance(
        data,
        dict,
    ):
        raise PackageError(f"Shape component manifest must contain a JSON object: {manifest}")

    raw_components = data.get(
        "components",
    )

    if not isinstance(
        raw_components,
        list,
    ):
        raise PackageError(f"Shape component manifest must contain a components list: {manifest}")

    if not raw_components:
        raise PackageError(f"Shape component manifest contains no components: {manifest}")

    compatibility = data.get(
        "compatibility",
    )

    if not isinstance(
        compatibility,
        dict,
    ):
        raise PackageError(
            f"Shape component manifest must contain compatibility metadata: {manifest}"
        )

    components = tuple(
        _load_component(
            raw_component,
            manifest=manifest,
        )
        for raw_component in raw_components
    )

    return (
        components,
        compatibility,
    )


def _load_component(
    raw_component: Any,
    *,
    manifest: Path,
) -> PhysicalComponent:
    """
    Load and validate one physical component declared by a Shape manifest.

    Shape-owned components carry name and path only. Incorporated Artwork
    components additionally carry persistent Artifact-color identity.
    """
    if not isinstance(raw_component, dict):
        raise PackageError(
            f"Shape component manifest contains an invalid component entry: {manifest}"
        )

    name = raw_component.get("name")
    relative_path = raw_component.get("path")

    if not isinstance(name, str) or not name:
        raise PackageError(
            f"Shape component manifest contains a component without a valid name: {manifest}"
        )

    if not isinstance(relative_path, str) or not relative_path:
        raise PackageError(f"Shape component {name!r} does not declare a valid path: {manifest}")

    component_path = manifest.parent / relative_path

    if not component_path.is_file():
        raise PackageError(f"Shape {name} component does not exist: {component_path}")

    raw_color = raw_component.get("color")

    if raw_color is None:
        return PhysicalComponent(
            name=name,
            path=component_path,
            artifact_color_index=None,
            artifact_color=None,
        )

    if not isinstance(raw_color, dict):
        raise PackageError(
            f"Shape component {name!r} does not declare valid Artifact-color metadata: {manifest}"
        )

    if "index" not in raw_color:
        raise PackageError(
            f"Shape component {name!r} declares physical color metadata upstream of Shape Package."
        )

    artifact_color_index, artifact_color = _load_artifact_color(
        raw_color,
        component_name=name,
        manifest=manifest,
    )

    return PhysicalComponent(
        name=name,
        path=component_path,
        artifact_color_index=artifact_color_index,
        artifact_color=artifact_color,
    )


def _load_artifact_color(
    raw_color: dict[str, Any],
    *,
    component_name: str,
    manifest: Path,
) -> tuple[
    int,
    tuple[
        int,
        int,
        int,
    ],
]:
    """
    Load persistent Artifact-color identity for incorporated Artwork.
    Artifact color consists of a stable positive index and measured RGB.
    Physical printer-color identity is deliberately absent at this boundary.
    """
    index = raw_color.get(
        "index",
    )
    if (
        isinstance(
            index,
            bool,
        )
        or not isinstance(
            index,
            int,
        )
        or index < 1
    ):
        raise PackageError(
            f"Shape component {component_name!r} does not declare "
            f"a valid Artifact color index: {manifest}"
        )
    raw_rgb = raw_color.get(
        "rgb",
    )
    if not isinstance(
        raw_rgb,
        dict,
    ):
        raise PackageError(
            f"Shape component {component_name!r} does not declare "
            f"valid Artifact RGB metadata: {manifest}"
        )
    red = _load_artifact_color_channel(
        raw_rgb,
        "red",
        component_name=component_name,
        manifest=manifest,
    )
    green = _load_artifact_color_channel(
        raw_rgb,
        "green",
        component_name=component_name,
        manifest=manifest,
    )
    blue = _load_artifact_color_channel(
        raw_rgb,
        "blue",
        component_name=component_name,
        manifest=manifest,
    )
    return (
        index,
        (
            red,
            green,
            blue,
        ),
    )


def _load_artifact_color_channel(
    raw_rgb: dict[str, Any],
    channel_name: str,
    *,
    component_name: str,
    manifest: Path,
) -> int:
    """
    Load and validate one Artifact RGB channel.
    """
    channel = raw_rgb.get(
        channel_name,
    )
    if (
        isinstance(
            channel,
            bool,
        )
        or not isinstance(
            channel,
            int,
        )
        or channel < 0
        or channel > 255
    ):
        raise PackageError(
            f"Shape component {component_name!r} does not declare "
            f"a valid Artifact {channel_name} value: {manifest}"
        )
    return channel


# =========================================================
# Component naming
# =========================================================
def _component_name(
    artifact_id: str,
    component_name_: str,
    color_name: str,
) -> str:
    """
    Return the shared 3MF presentation name for one Shape component.
    """
    return component_name(
        artifact_id,
        component_name_,
        color_name,
    )


__all__ = [
    "PackageError",
    "execute",
]
