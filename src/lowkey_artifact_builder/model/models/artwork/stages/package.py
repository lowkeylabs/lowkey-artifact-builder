"""
Artwork packaging stage.

The package stage combines independently printable Artwork STL components into
the final multicomponent 3MF artifact.

Filesystem layout and dependency resolution are responsibilities of the build
engine. This implementation consumes only paths supplied through StageContext.

The extrusion manifest identifies the dynamically generated STL components
that participate in the final artifact. Registered Artwork components preserve
Artifact-color identity through extrusion. Packaging resolves physical printer
color assignment and constructs the final printable 3MF.
"""
# File: src/lowkey_artifact_builder/model/models/artwork/stages/package.py
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

    Registered Artwork components preserve Artifact-color identity through
    extrusion. Physical printer-color assignment is resolved during
    packaging.

    Feature components are handled separately from registered Artwork color
    layers and may omit registered Artwork color identity.
    """

    index: int | None

    path: Path

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
    Execute the Artwork package stage.

    The stage consumes:

        extrude.manifest
            Manifest describing independently printable STL components
            produced by the extrusion stage.

    Parameters:

        printer_colors
            Physical printer colors available for one-to-one assignment to
            registered Artwork colors.

        loop_color
            Optional explicit physical printer color for the Loop.

        artwork_base_color
            Optional explicit physical printer color for the Base.

        artwork_outer_ridge_color
            Optional explicit physical printer color for the Outer Ridge.

    The stage produces:

        artifact
            Final multicomponent 3MF artifact.

    Registered Artwork geometry and Artifact-color identity are established
    upstream. Packaging resolves physical printer-color assignment for
    registered Artwork layers.

    Feature components inherit the physical printer-color assignment of the
    Artifact-color layer identified by their artifact_color_index unless an
    explicit feature-color parameter overrides that inherited assignment.
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

        artwork_components = tuple(
            component for component in extruded_components if component.index is not None
        )

        measured_colors = tuple(
            MeasuredColor(
                index=component.artifact_color_index,
                rgb=component.artifact_color,
            )
            for component in artwork_components
            if (component.artifact_color_index is not None and component.artifact_color is not None)
        )

        if len(measured_colors) != len(artwork_components):
            raise PackageError(
                "Registered Artwork extrusion products must preserve Artifact-color identity."
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

        component_colors: list[
            tuple[
                ExtrudedComponent,
                PaletteColor,
            ]
        ] = []

        for component in extruded_components:
            color = _resolve_component_color(
                component,
                assigned_colors=assigned_colors,
                resolver=context.resolver,
            )

            component_colors.append(
                (
                    component,
                    color,
                )
            )

        components = tuple(
            Component(
                name=_component_name(
                    context.artifact_id,
                    component,
                    color,
                ),
                mesh=load_stl(
                    component.path,
                ),
                color=color,
            )
            for component, color in component_colors
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
        raise PackageError(f"Could not resolve Artwork printer colors: {exc}") from exc

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


def _resolve_component_color(
    component: ExtrudedComponent,
    *,
    assigned_colors: dict[int, PaletteColor],
    resolver: Any,
) -> PaletteColor:
    """
    Resolve the physical printer color for one extrusion component.

    Registered Artwork layers use their globally assigned printer color.

    Feature components normally inherit the assignment of the Artifact-color
    layer identified by artifact_color_index. An explicit feature-color
    parameter overrides that inherited assignment.

    Feature-color parameters are optional. Their absence means inheritance,
    not a configuration error.
    """

    artifact_color_index = component.artifact_color_index

    if artifact_color_index is None:
        raise PackageError(
            f"Extrusion product {component.path.name} has no Artifact color identity."
        )

    try:
        inherited_color = assigned_colors[artifact_color_index]
    except KeyError as exc:
        raise PackageError(
            f"Extrusion product {component.path.name} references "
            f"unknown Artifact color index {artifact_color_index}."
        ) from exc

    if component.index is not None:
        return inherited_color

    override_parameter = _feature_color_parameter(
        component,
    )

    if override_parameter is None:
        return inherited_color

    if not resolver.has(
        override_parameter,
    ):
        return inherited_color

    override_name = resolver(
        override_parameter,
    )

    if override_name is None:
        return inherited_color

    if not isinstance(
        override_name,
        str,
    ):
        raise PackageError(f"{override_parameter} must resolve to a printer-color name.")

    override_palette = resolve_palette(
        [override_name],
        resolver.colors,
    )

    if len(override_palette) != 1:
        raise PackageError(f"Could not resolve {override_parameter} to one printer color.")

    return override_palette[0]


def _feature_color_parameter(
    component: ExtrudedComponent,
) -> str | None:
    """
    Return the physical color-override parameter for a feature component.

    Registered Artwork components do not have feature color overrides.
    Unknown feature component types inherit their referenced Artifact color.
    """

    if component.index is not None:
        return None

    feature = component.path.stem

    parameters = {
        "loop": "loop_color",
        "base": "artwork_base_color",
        "outer-ridge": "artwork_outer_ridge_color",
    }

    return parameters.get(
        feature,
    )


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

    indexes = [component.index for component in result if component.index is not None]

    if len(indexes) != len(set(indexes)):
        raise PackageError("Extrusion product indexes must be unique.")

    result.sort(
        key=lambda component: (
            component.index is None,
            component.index or 0,
        ),
    )

    return result


def _load_component(
    manifest: Path,
    product: Any,
) -> ExtrudedComponent:
    """
    Load and validate one extrusion product.

    Registered Artwork color-layer products preserve complete Artifact-color
    identity: artifact_color index and RGB.

    Feature products preserve the artifact_color_index of the registered
    Artwork layer whose physical printer-color assignment they inherit.

    Physical printer-color assignment itself is a packaging responsibility.
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

    artifact_color_data = product.get(
        "artifact_color",
    )

    feature_artifact_color_index = product.get(
        "artifact_color_index",
    )

    if index is not None and (
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

    artifact_color_index: int | None = None
    artifact_color: (
        tuple[
            int,
            int,
            int,
        ]
        | None
    ) = None

    if index is not None:
        if not isinstance(
            artifact_color_data,
            dict,
        ):
            raise PackageError(f"Extrusion product {index} has no valid Artifact color.")

        artifact_color_index = artifact_color_data.get(
            "index",
        )

        if (
            isinstance(
                artifact_color_index,
                bool,
            )
            or not isinstance(
                artifact_color_index,
                int,
            )
            or artifact_color_index < 1
        ):
            raise PackageError(f"Extrusion product {index} has no valid Artifact color index.")

        artifact_rgb_data = artifact_color_data.get(
            "rgb",
        )

        if not isinstance(
            artifact_rgb_data,
            dict,
        ):
            raise PackageError(f"Extrusion product {index} has no valid Artifact RGB.")

        artifact_color = (
            _color_component(
                artifact_rgb_data,
                "red",
                index,
            ),
            _color_component(
                artifact_rgb_data,
                "green",
                index,
            ),
            _color_component(
                artifact_rgb_data,
                "blue",
                index,
            ),
        )

    else:
        if (
            isinstance(
                feature_artifact_color_index,
                bool,
            )
            or not isinstance(
                feature_artifact_color_index,
                int,
            )
            or feature_artifact_color_index < 1
        ):
            raise PackageError(
                f"Feature extrusion product {filename} has no valid Artifact color index."
            )

        artifact_color_index = feature_artifact_color_index

    path = manifest.parent / filename

    if not path.is_file():
        raise PackageError(f"Extrusion product does not exist: {path}")

    if path.suffix.lower() != ".stl":
        raise PackageError(f"Extrusion product must be an STL file: {path}")

    return ExtrudedComponent(
        index=index,
        path=path,
        artifact_color_index=artifact_color_index,
        artifact_color=artifact_color,
    )


# =========================================================
# Color validation
# =========================================================


def _color_component(
    color: dict[str, Any],
    name: str,
    index: int | None,
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
    color: PaletteColor,
) -> str:
    """
    Return the packaged semantic component name.

    Registered Artwork extrusion products use stage-local color-N filenames,
    but independently printable packaged Artwork components use the shared
    artwork-N semantic identity. Feature components retain their semantic
    filename identity.
    """

    if component.index is not None:
        semantic_name = f"artwork-{component.index}"
    else:
        semantic_name = component.path.stem

    return component_name(
        artifact_id,
        semantic_name,
        color.name,
    )


__all__ = [
    "PackageError",
    "execute",
]
