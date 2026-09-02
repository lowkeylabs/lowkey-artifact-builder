"""
Artwork packaging stage.

The package stage combines independently printable Artwork STL components into
the final multicomponent 3MF artifact.

Filesystem layout and dependency resolution are responsibilities of the build
engine. This implementation consumes only paths supplied through StageContext.

The extrusion manifest identifies the dynamically generated STL components
that participate in the final artifact. Packaging preserves the physical
printer color assignment established upstream without re-resolving Artwork
color policy.
"""
# File: src/lowkey_artifact_builder/model/models/artwork/stages/package.py
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
    Raised when Artwork packaging cannot be completed.
    """


# =========================================================
# Specifications
# =========================================================


@dataclass(
    frozen=True,
    slots=True,
)
class ExtrudedComponent:
    """
    One independently printable Artwork component.

    The extrusion manifest establishes component order, path, and physical
    printer color assignment. Packaging preserves that assignment while
    constructing the final 3MF.
    """

    index: int

    path: Path

    color: PaletteColor


# =========================================================
# Stage implementation
# =========================================================


def execute(
    context: StageContext,
) -> None:
    """
    Execute the Artwork package stage.

    The stage consumes:

        extrude.manifest
            Manifest describing independently printable STL components
            produced by the extrusion stage.

    The stage produces:

        artifact
            Final multicomponent 3MF artifact.

    Packaging does not determine Artwork component membership or assign
    physical printer colors. Those properties are established upstream.
    Packaging uses the preserved printer assignment when constructing the
    shared 3MF component representation.
    """

    extrude_manifest = context.input(
        "extrude.manifest",
    )

    artifact = context.output(
        "artifact",
    )

    if not extrude_manifest.is_file():
        raise PackageError(f"Extrusion product manifest does not exist: {extrude_manifest}")

    try:
        extruded_components = _load_extrude_manifest(
            extrude_manifest,
        )

        components = tuple(
            Component(
                name=_component_name(
                    context.artifact_id,
                    component,
                ),
                mesh=load_stl(
                    component.path,
                ),
                color=component.color,
            )
            for component in extruded_components
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
            f"Could not package Artwork components from {extrude_manifest}: {exc}"
        ) from exc

    except (
        OSError,
        ValueError,
        TypeError,
        KeyError,
        json.JSONDecodeError,
    ) as exc:
        raise PackageError(
            f"Could not process extrusion manifest {extrude_manifest}: {exc}"
        ) from exc


# =========================================================
# Manifest loading
# =========================================================


def _load_extrude_manifest(
    manifest: Path,
) -> list[ExtrudedComponent]:
    """
    Load independently printable components from an extrusion manifest.
    """

    try:
        data = json.loads(
            manifest.read_text(
                encoding="utf-8",
            )
        )

    except (
        OSError,
        json.JSONDecodeError,
    ) as exc:
        raise PackageError(f"Could not read extrusion manifest: {manifest}") from exc

    if not isinstance(
        data,
        dict,
    ):
        raise PackageError("Extrusion manifest must contain a JSON object.")

    products = data.get(
        "products",
    )

    if not isinstance(
        products,
        list,
    ):
        raise PackageError("Extrusion manifest does not contain a products list.")

    if not products:
        raise PackageError("Extrusion manifest contains no STL products.")

    result = [
        _load_component(
            manifest,
            product,
        )
        for product in products
    ]

    indexes = [component.index for component in result]

    if len(indexes) != len(set(indexes)):
        raise PackageError("Extrusion product indexes must be unique.")

    names = [component.color.name for component in result]

    if len(names) != len(set(names)):
        raise PackageError("Extrusion product printer color names must be unique.")

    result.sort(
        key=lambda component: component.index,
    )

    return result


def _load_component(
    manifest: Path,
    product: Any,
) -> ExtrudedComponent:
    """
    Load and validate one extrusion product.

    The physical 3MF component color is determined exclusively by the
    printer assignment preserved in the extrusion manifest.
    """

    if not isinstance(
        product,
        dict,
    ):
        raise PackageError("Extrusion manifest contains an invalid product.")

    index = product.get(
        "index",
    )

    filename = product.get(
        "path",
    )

    printer_color_data = product.get(
        "printer_color",
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
        raise PackageError("Extrusion product index must be a positive integer.")

    if (
        not isinstance(
            filename,
            str,
        )
        or not filename
    ):
        raise PackageError(f"Extrusion product {index} has no valid path.")

    if not isinstance(
        printer_color_data,
        dict,
    ):
        raise PackageError(f"Extrusion product {index} has no valid printer color.")

    printer_color_name = printer_color_data.get(
        "name",
    )

    printer_rgb_data = printer_color_data.get(
        "rgb",
    )

    if (
        not isinstance(
            printer_color_name,
            str,
        )
        or not printer_color_name.strip()
    ):
        raise PackageError(f"Extrusion product {index} has no valid printer color name.")

    printer_color_name = printer_color_name.strip()

    if not isinstance(
        printer_rgb_data,
        dict,
    ):
        raise PackageError(f"Extrusion product {index} has no valid printer RGB.")

    color = PaletteColor(
        name=printer_color_name,
        rgb=(
            _color_component(
                printer_rgb_data,
                "red",
                index,
            ),
            _color_component(
                printer_rgb_data,
                "green",
                index,
            ),
            _color_component(
                printer_rgb_data,
                "blue",
                index,
            ),
        ),
    )

    path = manifest.parent / filename

    if not path.is_file():
        raise PackageError(f"Extrusion product does not exist: {path}")

    if path.suffix.lower() != ".stl":
        raise PackageError(f"Extrusion product must be an STL file: {path}")

    return ExtrudedComponent(
        index=index,
        path=path,
        color=color,
    )


# =========================================================
# Color validation
# =========================================================


def _color_component(
    color: dict[str, Any],
    name: str,
    index: int,
) -> int:
    """
    Return one validated RGB component.
    """

    value = color.get(
        name,
    )

    if (
        isinstance(
            value,
            bool,
        )
        or not isinstance(
            value,
            int,
        )
        or value < 0
        or value > 255
    ):
        raise PackageError(f"Extrusion product {index} has invalid {name} color component.")

    return value


# =========================================================
# Component naming
# =========================================================


def _component_name(
    artifact_id: str,
    component: ExtrudedComponent,
) -> str:
    """
    Return the semantic 3MF object name for one Artwork component.

    Independently printable components are identified by their assigned
    physical printer color. Object names therefore combine artifact identity
    with the printer color identity established upstream.

    For example:

        nydeli-black
        nydeli-red
        nydeli-white
    """

    return f"{artifact_id}-{component.color.name}"


__all__ = [
    "PackageError",
    "execute",
]
