"""
Coin packaging stage.

The package stage converts the persistent physical Coin component collection
into the final multi-component 3MF artifact.

Physical component membership, geometry, semantic identity, and resolved
physical color are established upstream by Coin composition. Packaging
preserves those properties without reopening Shape configuration or performing
new color assignment.
"""
# File: src/lowkey_artifact_builder/model/models/coin/stages/package.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from lowkey_artifact_builder.colors import PaletteColor
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
    Raised when Coin packaging cannot be completed.
    """


# =========================================================
# Stage implementation
# =========================================================


def execute(
    context: StageContext,
) -> None:
    """
    Package the complete physical Coin Product as a multi-component 3MF.

    Component membership, geometry, semantic identity, and resolved physical
    color are consumed directly from the persistent physical Coin Product.
    Package performs no new color assignment or physical transformation.
    """

    manifest = context.input(
        "compose.physical",
    )

    artifact = context.output(
        "artifact",
    )

    if not manifest.is_file():
        raise PackageError(f"Coin physical component manifest does not exist: {manifest}")

    try:
        physical_components = _load_manifest(
            manifest,
        )

        components = tuple(
            Component(
                name=component_name(
                    context.artifact_id,
                    name,
                    color.name,
                ),
                mesh=load_stl(
                    path,
                ),
                color=color,
            )
            for name, path, color in physical_components
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
            f"Could not package Coin components from manifest {manifest}: {exc}"
        ) from exc
    except (
        OSError,
        ValueError,
        TypeError,
        KeyError,
        json.JSONDecodeError,
    ) as exc:
        raise PackageError(
            f"Could not package Coin components from manifest {manifest}: {exc}"
        ) from exc


# =========================================================
# Physical Product
# =========================================================


def _load_manifest(
    manifest: Path,
) -> tuple[
    tuple[
        str,
        Path,
        PaletteColor,
    ],
    ...,
]:
    """
    Load the persistent physical Coin component collection.

    Every physical component already owns its semantic identity, physical
    geometry, and resolved physical color. Package validates and preserves
    those facts without reinterpreting them.
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
        raise PackageError(f"Coin physical manifest must contain a JSON object: {manifest}")

    raw_components = data.get(
        "components",
    )

    if not isinstance(
        raw_components,
        list,
    ):
        raise PackageError(f"Coin physical manifest must contain a components list: {manifest}")

    if not raw_components:
        raise PackageError(f"Coin physical manifest contains no components: {manifest}")

    return tuple(
        _load_component(
            raw_component,
            manifest=manifest,
        )
        for raw_component in raw_components
    )


def _load_component(
    raw_component: Any,
    *,
    manifest: Path,
) -> tuple[
    str,
    Path,
    PaletteColor,
]:
    """
    Load one physical Coin component from its persistent manifest entry.
    """

    if not isinstance(
        raw_component,
        dict,
    ):
        raise PackageError(
            f"Coin physical manifest contains an invalid component entry: {manifest}"
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
            f"Coin physical manifest contains a component without a valid name: {manifest}"
        )

    if (
        not isinstance(
            relative_path,
            str,
        )
        or not relative_path
    ):
        raise PackageError(f"Coin component {name!r} does not declare a valid path: {manifest}")

    component_path = manifest.parent / relative_path

    if not component_path.is_file():
        raise PackageError(f"Coin component {name!r} does not exist: {component_path}")

    color = _load_color(
        raw_component.get(
            "color",
        ),
        component_name_=name,
        manifest=manifest,
    )

    return (
        name,
        component_path,
        color,
    )


def _load_color(
    raw_color: Any,
    *,
    component_name_: str,
    manifest: Path,
) -> PaletteColor:
    """
    Load one already-resolved physical Coin component color.
    """

    if not isinstance(
        raw_color,
        dict,
    ):
        raise PackageError(
            f"Coin component {component_name_!r} does not declare "
            f"resolved physical color metadata: {manifest}"
        )

    name = raw_color.get(
        "name",
    )

    rgb = raw_color.get(
        "rgb",
    )

    if (
        not isinstance(
            name,
            str,
        )
        or not name
    ):
        raise PackageError(
            f"Coin component {component_name_!r} does not declare "
            f"a valid physical color name: {manifest}"
        )

    if (
        not isinstance(
            rgb,
            list,
        )
        or len(rgb) != 3
        or any(
            isinstance(channel, bool)
            or not isinstance(
                channel,
                int,
            )
            or channel < 0
            or channel > 255
            for channel in rgb
        )
    ):
        raise PackageError(
            f"Coin component {component_name_!r} does not declare "
            f"valid physical RGB metadata: {manifest}"
        )

    return PaletteColor(
        name=name,
        rgb=(
            rgb[0],
            rgb[1],
            rgb[2],
        ),
    )


__all__ = [
    "PackageError",
    "execute",
]
