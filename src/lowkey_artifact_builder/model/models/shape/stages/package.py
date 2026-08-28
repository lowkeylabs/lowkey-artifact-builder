"""
Shape packaging stage.

The package stage combines independently produced physical Shape components
into the final multicomponent 3MF artifact.

Filesystem layout and dependency resolution are responsibilities of the build
engine. This implementation consumes the physical-component manifest supplied
through StageContext and resolves component files relative to that manifest.

Packaging does not determine which physical components a Shape contains.
Component membership is established by the upstream extrusion stage.
"""
# File: src/lowkey_artifact_builder/model/models/shape/stages/package.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from lowkey_artifact_builder.engine import StageContext
from lowkey_artifact_builder.formats.threemf import (
    ThreeMFError,
    write_stls,
)

# =========================================================
# Errors
# =========================================================


class PackageError(RuntimeError):
    """
    Raised when Shape packaging cannot be completed.
    """


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

    Packaging does not construct, dimensionalize, or otherwise interpret
    Shape geometry. It packages every physical component declared by the
    extrusion manifest using the component's semantic role as its stable
    object identity.
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
        components = _load_components(
            manifest,
        )

        stls = tuple(
            (
                _component_name(
                    context.artifact_id,
                    component_name,
                ),
                component_path,
            )
            for component_name, component_path in components
        )

        write_stls(
            stls,
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
    tuple[
        str,
        Path,
    ],
    ...,
]:
    """
    Load physical Shape components from an extrusion manifest.

    Component paths are interpreted relative to the manifest location. This
    keeps packaging independent from artifact workspace layout while allowing
    extrusion to describe a variable set of physical manufacturing components.
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

    components: list[
        tuple[
            str,
            Path,
        ]
    ] = []

    for raw_component in raw_components:
        component_name, component_path = _load_component(
            raw_component,
            manifest=manifest,
        )

        components.append(
            (
                component_name,
                component_path,
            )
        )

    return tuple(
        components,
    )


def _load_component(
    raw_component: Any,
    *,
    manifest: Path,
) -> tuple[
    str,
    Path,
]:
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

    return (
        name,
        component_path,
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
