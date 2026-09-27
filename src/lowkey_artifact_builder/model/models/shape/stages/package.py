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

Structural Shape components may already carry resolved semantic printer-color
identity. Incorporated Artwork components instead preserve persistent
Artifact-color identity through extrusion. Packaging resolves those logical
Artwork colors to physical printer colors.
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

    Structural Shape components may carry a resolved semantic printer color
    established by Shape policy upstream.

    Incorporated Artwork components instead preserve persistent Artifact-color
    identity through extrusion. Packaging resolves those logical colors to
    physical printer colors.
    """

    name: str

    path: Path

    color: PaletteColor | None

    artifact_color_index: int | None

    artifact_color: (
        tuple[
            int,
            int,
            int,
        ]
        | None
    )


# =========================================================
# Stage implementation
# =========================================================


def execute(
    context: StageContext,
) -> None:
    """
    Execute the Shape package stage.

    The stage consumes:

        extrude.manifest
            Persistent products.json manifest describing independently
            printable physical Shape components.

    Parameters:

        printer_colors
            Physical printer colors available for one-to-one assignment to
            incorporated registered Artwork colors.

            This parameter is required only when incorporated Artwork
            components participate in the Shape.

    The stage produces:

        artifact
            Final Shape 3MF artifact.

    Structural Shape components preserve their resolved semantic printer
    colors.

    Incorporated Artwork components preserve Artifact-color identity through
    extrusion. Packaging resolves those logical colors against printer_colors
    using the shared global one-to-one color assignment.
    """

    manifest = context.input(
        "extrude.manifest",
    )

    artifact = context.output(
        "artifact",
    )

    if not manifest.is_file():
        raise PackageError(f"Shape component manifest does not exist: {manifest}")

    try:
        physical_components = _load_components(
            manifest,
        )

        artwork_components = tuple(
            component
            for component in physical_components
            if component.artifact_color_index is not None
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

            printer_color_names = context.resolver(
                "printer_colors",
            )

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
                mesh=load_stl(
                    physical_component.path,
                ),
                color=color,
            )
            for physical_component, color in component_colors
        )

        write(
            components,
            artifact,
        )

        if not artifact.is_file():
            raise PackageError(
                f"3MF packaging completed without creating the expected artifact: {artifact}"
            )

    except PackageError:
        raise

    except ColorError as exc:
        raise PackageError(f"Could not resolve incorporated Artwork printer colors: {exc}") from exc

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


def _resolve_component_color(
    component: PhysicalComponent,
    *,
    assigned_colors: dict[int, PaletteColor],
) -> PaletteColor:
    """
    Resolve the physical printer color for one Shape component.

    Structural Shape components preserve their upstream semantic printer
    color. Incorporated Artwork components use the globally assigned printer
    color for their persistent Artifact-color identity.
    """

    artifact_color_index = component.artifact_color_index

    if artifact_color_index is None:
        if component.color is None:
            raise PackageError(f"Shape component {component.name!r} has no physical color.")

        return component.color

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


def _load_components(
    manifest: Path,
) -> tuple[
    PhysicalComponent,
    ...,
]:
    """
    Load physical Shape components from an extrusion manifest.

    Component paths are interpreted relative to the manifest location. This
    keeps packaging independent from artifact workspace layout while allowing
    extrusion to describe a variable set of physical manufacturing components.

    Structural Shape components carry resolved semantic printer-color
    metadata.

    Incorporated Artwork components carry persistent Artifact-color identity.
    Their physical printer-color assignment is resolved during packaging.
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

    components: list[PhysicalComponent] = []

    for raw_component in raw_components:
        components.append(
            _load_component(
                raw_component,
                manifest=manifest,
            )
        )

    return tuple(
        components,
    )


def _load_component(
    raw_component: Any,
    *,
    manifest: Path,
) -> PhysicalComponent:
    """
    Load and validate one physical component declared by a Shape manifest.

    Structural Shape components carry resolved semantic printer-color
    metadata.

    Incorporated Artwork components carry persistent Artifact-color identity;
    physical printer-color assignment is deferred until packaging.
    """

    if not isinstance(
        raw_component,
        dict,
    ):
        raise PackageError(
            f"Shape component manifest contains an invalid component entry: {manifest}"
        )

    name = raw_component.get(
        "name",
    )

    relative_path = raw_component.get(
        "path",
    )

    if (
        not isinstance(
            name,
            str,
        )
        or not name
    ):
        raise PackageError(
            f"Shape component manifest contains a component without a valid name: {manifest}"
        )

    if (
        not isinstance(
            relative_path,
            str,
        )
        or not relative_path
    ):
        raise PackageError(f"Shape component {name!r} does not declare a valid path: {manifest}")

    component_path = manifest.parent / relative_path

    if not component_path.is_file():
        raise PackageError(f"Shape {name} component does not exist: {component_path}")

    raw_color = raw_component.get(
        "color",
    )

    if not isinstance(
        raw_color,
        dict,
    ):
        raise PackageError(
            f"Shape component {name!r} does not declare valid color metadata: {manifest}"
        )

    if "index" in raw_color:
        (
            artifact_color_index,
            artifact_color,
        ) = _load_artifact_color(
            raw_color,
            component_name=name,
            manifest=manifest,
        )

        return PhysicalComponent(
            name=name,
            path=component_path,
            color=None,
            artifact_color_index=artifact_color_index,
            artifact_color=artifact_color,
        )

    color = _load_component_color(
        raw_color,
        component_name=name,
        manifest=manifest,
    )

    return PhysicalComponent(
        name=name,
        path=component_path,
        color=color,
        artifact_color_index=None,
        artifact_color=None,
    )


def _load_component_color(
    raw_color: Any,
    *,
    component_name: str,
    manifest: Path,
) -> PaletteColor:
    """
    Load resolved semantic printer-color metadata for one Shape component.

    Structural Shape components contain the authoritative semantic name and
    RGB value established upstream. Packaging validates and preserves those
    values.
    """

    if not isinstance(
        raw_color,
        dict,
    ):
        raise PackageError(
            f"Shape component {component_name!r} does not declare valid color metadata: {manifest}"
        )

    color_name = raw_color.get(
        "name",
    )

    raw_rgb = raw_color.get(
        "rgb",
    )

    if (
        not isinstance(
            color_name,
            str,
        )
        or not color_name
    ):
        raise PackageError(
            f"Shape component {component_name!r} does not declare a valid color name: {manifest}"
        )

    if (
        not isinstance(
            raw_rgb,
            list,
        )
        or len(raw_rgb) != 3
        or any(
            not isinstance(
                channel,
                int,
            )
            or isinstance(
                channel,
                bool,
            )
            or channel < 0
            or channel > 255
            for channel in raw_rgb
        )
    ):
        raise PackageError(
            f"Shape component {component_name!r} does not declare a valid RGB color: {manifest}"
        )

    return PaletteColor(
        name=color_name,
        rgb=(
            raw_rgb[0],
            raw_rgb[1],
            raw_rgb[2],
        ),
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
