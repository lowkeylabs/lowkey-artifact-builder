"""
Physical extrusion for the Shape model.

The extrude stage is the Shape physical-dimensionalization boundary.

It consumes registered composed Shape geometry, applies the configured
physical X/Y size and Z thickness, and renders the resulting manufacturing
geometry as an independently printable STL component.

Final 3MF assembly belongs to the downstream package stage.
"""
# File: src/lowkey_artifact_builder/model/models/shape/stages/extrude.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path

from lowkey_artifact_builder.engine import StageContext
from lowkey_artifact_builder.model.models.artwork.stages.extrude import (
    render_stl_source,
)

# =========================================================
# Errors
# =========================================================


class ExtrudeError(RuntimeError):
    """
    Raised when Shape extrusion cannot be completed.
    """


# =========================================================
# Public interface
# =========================================================


def execute(
    context: StageContext,
) -> None:
    """
    Execute physical Shape extrusion.

    The stage consumes:

        compose.composition
            Registered composed Shape geometry.

    The stage resolves:

        shape_size
            Physical X/Y extent of the Shape in millimeters.

        shape_base_raise
            Physical Z thickness of the structural base in millimeters.

    The stage produces:

        base
            Independently printable physical Shape base STL.

    Packaging the physical component into artifact.3mf belongs to the
    downstream package stage.
    """

    composition = context.input(
        "compose.composition",
    )

    base = context.output(
        "base",
    )

    shape_size = context.resolver(
        "shape_size",
    )

    shape_base_raise = context.resolver(
        "shape_base_raise",
    )

    if not composition.is_file():
        raise ExtrudeError(f"Registered Shape composition does not exist: {composition}")

    try:
        source = _build_scad(
            composition,
            shape_size=shape_size,
            shape_base_raise=shape_base_raise,
        )

        render_stl_source(
            source,
            base,
        )

        if not base.is_file():
            raise ExtrudeError(
                f"Shape extrusion completed without creating the expected base STL: {base}"
            )

    except ExtrudeError:
        raise

    except (
        OSError,
        TypeError,
        ValueError,
    ) as exc:
        raise ExtrudeError(
            f"Could not extrude registered Shape composition {composition}: {exc}"
        ) from exc


# =========================================================
# OpenSCAD construction
# =========================================================


def _build_scad(
    composition: Path,
    *,
    shape_size: float,
    shape_base_raise: float,
) -> str:
    """
    Build OpenSCAD source for physical Shape base extrusion.

    The registered composition uses the canonical unit Shape envelope
    centered about the origin. shape_size dimensionalizes that envelope
    uniformly in X/Y and shape_base_raise supplies its physical Z thickness.
    """

    source = composition.resolve()

    return (
        f"shape_size = {shape_size:g};\n"
        f"shape_base_raise = {shape_base_raise:g};\n"
        "\n"
        "linear_extrude(\n"
        "    height = shape_base_raise,\n"
        "    center = false\n"
        ")\n"
        "    scale([shape_size, shape_size, 1])\n"
        f'        import("{source}");\n'
    )


def _scad_path(
    path: Path,
) -> str:
    """
    Return a filesystem path suitable for an OpenSCAD string literal.

    OpenSCAD accepts forward slashes on supported platforms. Converting here
    also avoids introducing platform-specific backslash escaping into the
    generated source.
    """

    return path.resolve().as_posix()


__all__ = [
    "ExtrudeError",
    "execute",
]
