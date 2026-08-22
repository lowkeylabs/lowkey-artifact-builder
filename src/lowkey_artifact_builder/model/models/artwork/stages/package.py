"""
Artwork packaging stage.

The package stage combines the independently printable artwork STL
components into the final multicomponent 3MF artifact.

Filesystem layout and dependency resolution are responsibilities of
the build engine. This implementation consumes only the paths supplied
through StageContext.

The extrusion manifest identifies the dynamically generated STL
components that participate in the final artifact. The package stage
uses that manifest rather than discovering components by scanning the
extrusion directory.

Semantic artwork color names assigned during rasterization are
preserved through the pipeline and used to construct meaningful 3MF
object names.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from lowkey_artifact_builder.engine import (
    StageContext,
)
from lowkey_artifact_builder.formats.threemf import (
    ThreeMFError,
    write_stls,
)

# =========================================================
# Errors
# =========================================================


class PackageError(RuntimeError):
    """
    Raised when artwork packaging cannot be completed.
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
    One STL component described by the extrusion manifest.

    name is the semantic artwork color assigned by the raster stage
    and propagated through vectorization and extrusion.
    """

    index: int

    path: Path

    name: str

    color: tuple[
        int,
        int,
        int,
    ]


# =========================================================
# Stage implementation
# =========================================================


def execute(
    context: StageContext,
) -> None:
    """
    Execute the artwork package stage.

    The stage consumes:

        extrude.manifest
            Manifest describing the independently printable STL
            components produced by the extrusion stage.

    The stage produces:

        artifact
            Final multicomponent 3MF artifact.
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
        components = _load_extrude_manifest(extrude_manifest)

        stls = tuple(
            (
                _component_name(
                    context.artifact_id,
                    component,
                ),
                component.path,
            )
            for component in components
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
            f"Could not package artwork components from {extrude_manifest}: {exc}"
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
    Load STL components from the extrusion manifest.
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

    products = data.get("products")

    if not isinstance(
        products,
        list,
    ):
        raise PackageError("Extrusion manifest does not contain a products list.")

    if not products:
        raise PackageError("Extrusion manifest contains no STL products.")

    result: list[ExtrudedComponent] = []

    for product in products:
        result.append(
            _load_component(
                manifest,
                product,
            )
        )

    indexes = [component.index for component in result]

    if len(indexes) != len(set(indexes)):
        raise PackageError("Extrusion product indexes must be unique.")

    names = [component.name for component in result]

    if len(names) != len(set(names)):
        raise PackageError("Extrusion product color names must be unique.")

    result.sort(key=lambda component: component.index)

    return result


def _load_component(
    manifest: Path,
    product: Any,
) -> ExtrudedComponent:
    """
    Load and validate one extrusion product.
    """

    if not isinstance(
        product,
        dict,
    ):
        raise PackageError("Extrusion manifest contains an invalid product.")

    index = product.get("index")

    filename = product.get("path")

    name = product.get("name")

    color_data = product.get("color")

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

    if (
        not isinstance(
            name,
            str,
        )
        or not name.strip()
    ):
        raise PackageError(f"Extrusion product {index} has no valid color name.")

    name = name.strip()

    if not isinstance(
        color_data,
        dict,
    ):
        raise PackageError(f"Extrusion product {index} has no valid color.")

    color = (
        _color_component(
            color_data,
            "red",
            index,
        ),
        _color_component(
            color_data,
            "green",
            index,
        ),
        _color_component(
            color_data,
            "blue",
            index,
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
        name=name,
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

    value = color.get(name)

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
    Return the semantic 3MF object name for one artwork component.

    Object names combine the artifact identity with the semantic
    artwork color assigned during rasterization.

    For example:

        nydeli-black
        nydeli-red
        nydeli-white
    """

    return f"{artifact_id}-{component.name}"


__all__ = [
    "PackageError",
    "execute",
]
