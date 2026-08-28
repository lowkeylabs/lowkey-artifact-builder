"""
Shape packaging stage.

The package stage combines independently produced physical Shape components
into the final multicomponent 3MF artifact.

Filesystem layout and dependency resolution are responsibilities of the build
engine. This implementation consumes the physical-component manifest supplied
through StageContext and resolves component files relative to that manifest.

Packaging does not determine which physical components a Shape contains.
Component membership and semantic color identity are established by the
upstream extrusion stage.
"""
# File: src/lowkey_artifact_builder/model/models/shape/stages/package.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from lowkey_artifact_builder.colors import PaletteColor
from lowkey_artifact_builder.engine import StageContext
from lowkey_artifact_builder.formats.threemf import (
    Component,
    ThreeMFError,
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

    The extrusion stage establishes component membership, semantic role,
    physical geometry, and resolved semantic color identity. Packaging
    preserves that metadata without re-resolving Shape policy.
    """

    name: str

    path: Path

    color: PaletteColor


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

    The stage produces:

        artifact
            Final Shape 3MF artifact.

    Packaging does not construct, dimensionalize, recolor, or otherwise
    interpret Shape geometry. It packages every physical component declared
    by the extrusion manifest using the component's semantic role and resolved
    semantic color identity.
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

        components = tuple(
            Component(
                name=_component_name(
                    context.artifact_id,
                    physical_component.name,
                ),
                mesh=load_stl(
                    physical_component.path,
                ),
                color=physical_component.color,
            )
            for physical_component in physical_components
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

    except ThreeMFError as exc:
        raise PackageError(
            f"Could not package Shape components from manifest {manifest}: {exc}"
        ) from exc

    except (
        OSError,
        ValueError,
        TypeError,
        json.JSONDecodeError,
    ) as exc:
        raise PackageError(
            f"Could not package Shape components from manifest {manifest}: {exc}"
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

    Component color metadata is consumed exactly as supplied by extrusion.
    Packaging does not resolve model color parameters or consult the shared
    color catalog.
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

    color = _load_component_color(
        raw_component.get(
            "color",
        ),
        component_name=name,
        manifest=manifest,
    )

    return PhysicalComponent(
        name=name,
        path=component_path,
        color=color,
    )


def _load_component_color(
    raw_color: Any,
    *,
    component_name: str,
    manifest: Path,
) -> PaletteColor:
    """
    Load resolved semantic color metadata for one physical component.

    The manifest contains the authoritative semantic name and RGB value
    established by extrusion. Packaging validates and preserves those values;
    it does not resolve the color again.
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
            not isinstance(channel, int)
            or isinstance(channel, bool)
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


# =========================================================
# Component naming
# =========================================================


def _component_name(
    artifact_id: str,
    component_name: str,
) -> str:
    """
    Return the semantic 3MF object name for a Shape component.

    Object identity combines artifact identity with the semantic role declared
    by extrusion rather than depending on the component's filesystem name.

    For example:

        coaster-base
        coaster-ridge
        ornament-base
        ornament-ridge
    """

    return f"{artifact_id}-{component_name}"


__all__ = [
    "PackageError",
    "execute",
]
