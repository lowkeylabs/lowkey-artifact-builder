"""
Utilities for invoking the Inkscape command-line interface.

This module provides the low-level interface between
lowkey-artifact-builder and Inkscape.

It contains no artifact-model or build-stage behavior. Higher-level
subsystems use these operations to perform tracing, SVG manipulation,
rendering, and other Inkscape-backed operations.
"""
# File: src/lowkey_artifact_builder/tools/inkscape.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import os
import shutil
import subprocess
from collections.abc import Iterable, Sequence
from pathlib import Path

PX_PER_INCH = 96.0
MM_PER_INCH = 25.4

INKSCAPE_ENVIRONMENT_VARIABLE = "LOWKEY_ARTIFACT_INKSCAPE"


# =========================================================
# Errors
# =========================================================


class InkscapeError(RuntimeError):
    """
    Raised when an Inkscape operation cannot be completed.
    """


# =========================================================
# Units
# =========================================================


def px_to_mm(
    value: float,
) -> float:
    """
    Convert SVG/CSS pixels to millimeters.

    SVG uses 96 pixels per inch.
    """

    return value * MM_PER_INCH / PX_PER_INCH


# =========================================================
# Executable discovery
# =========================================================


def find_inkscape() -> str:
    """
    Find the Inkscape executable.

    Search order:

        1. LOWKEY_ARTIFACT_INKSCAPE environment variable.
        2. Native ``inkscape`` executable on PATH.
        3. Standard Windows installation paths under WSL.

    Raises:
        InkscapeError:
            If Inkscape cannot be found.
    """

    configured = os.environ.get(INKSCAPE_ENVIRONMENT_VARIABLE)

    if configured:
        executable = Path(configured)

        if executable.is_file():
            return str(executable)

        raise InkscapeError(
            f"{INKSCAPE_ENVIRONMENT_VARIABLE} points to a file that does not exist: {configured}"
        )

    executable = shutil.which("inkscape")

    if executable is not None:
        return executable

    windows_candidates = (
        Path("/mnt/c/Program Files/Inkscape/bin/inkscape.exe"),
        Path("/mnt/c/Program Files/Inkscape/inkscape.exe"),
    )

    for candidate in windows_candidates:
        if candidate.is_file():
            return str(candidate)

    raise InkscapeError(
        "Could not find Inkscape.\n"
        f"Set {INKSCAPE_ENVIRONMENT_VARIABLE} to the "
        "path of the Inkscape executable."
    )


# =========================================================
# Invocation
# =========================================================


def run(
    svg: Path,
    *,
    args: Sequence[str] = (),
    actions: Iterable[str] = (),
) -> str:
    """
    Run Inkscape against an SVG document.

    Args:
        svg:
            SVG document to process.

        args:
            Additional Inkscape command-line arguments,
            such as ``--query-all``.

        actions:
            Inkscape actions. Multiple actions are joined
            with semicolons and passed using ``--actions``.

    Returns:
        Captured stdout from Inkscape.

    Raises:
        InkscapeError:
            If the SVG does not exist, Inkscape cannot be
            found, or Inkscape exits unsuccessfully.
    """

    svg = Path(svg)

    if not svg.is_file():
        raise InkscapeError(f"SVG file does not exist: {svg}")

    executable = find_inkscape()

    command = [
        executable,
        str(svg),
        *args,
    ]

    action_string = ";".join(actions)

    if action_string:
        command.append(f"--actions={action_string}")

    try:
        result = subprocess.run(
            command,
            text=True,
            capture_output=True,
            check=False,
        )

    except OSError as exc:
        raise InkscapeError(f"Could not execute Inkscape.\nCommand: {' '.join(command)}") from exc

    if result.returncode != 0:
        raise InkscapeError(
            "Inkscape failed.\n"
            f"Command: {' '.join(command)}\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )

    return result.stdout


# =========================================================
# Queries
# =========================================================


def query_all(
    svg: Path,
    *,
    millimeters: bool = True,
) -> dict[str, dict[str, float]]:
    """
    Return bounding boxes for all objects in an SVG.

    By default, bounding boxes are returned in millimeters.

    When ``millimeters`` is false, bounding boxes are returned in the
    SVG/CSS coordinate units reported directly by Inkscape.
    """

    stdout = run(
        svg,
        args=("--query-all",),
    )

    bounds: dict[
        str,
        dict[str, float],
    ] = {}

    for line in stdout.splitlines():
        fields = line.split(",")

        if len(fields) != 5:
            continue

        object_id, x, y, width, height = fields

        try:
            values = {
                "x": float(x),
                "y": float(y),
                "width": float(width),
                "height": float(height),
            }

        except ValueError as exc:
            raise InkscapeError(
                f"Inkscape returned an invalid object bounding box for {object_id!r}: {line}"
            ) from exc

        if millimeters:
            values = {name: px_to_mm(value) for name, value in values.items()}

        bounds[object_id] = values

    return bounds


# =========================================================
# Selection actions
# =========================================================


def select_by_id(
    object_ids: Sequence[str],
) -> str:
    """
    Return an Inkscape action selecting objects by ID.

    Multiple IDs are supplied in one select-by-id action.
    """

    if not object_ids:
        raise InkscapeError("At least one object ID is required.")

    return "select-by-id:" + ",".join(object_ids)


# =========================================================
# Path actions
# =========================================================


def union_actions(
    object_ids: Sequence[str],
) -> list[str]:
    """
    Return actions that union the specified objects.
    """

    if len(object_ids) < 2:
        raise InkscapeError("Union requires at least two objects.")

    return [
        "select-clear",
        select_by_id(object_ids),
        "path-union",
    ]


def difference_actions(
    target: str,
    cutter: str,
) -> list[str]:
    """
    Return actions that subtract cutter from target.

    The target must be below the cutter in SVG stacking
    order.
    """

    return [
        "select-clear",
        select_by_id(
            (
                target,
                cutter,
            )
        ),
        "path-difference",
    ]


# =========================================================
# Export actions
# =========================================================


def export_object_actions(
    object_id: str,
    output: Path,
) -> list[str]:
    """
    Return actions that export one object to an SVG.

    Only the requested object is included in the export,
    but the source document's page is retained as the
    export area so independently exported artwork remains
    registered.
    """

    output = Path(output).resolve()

    return [
        "select-clear",
        select_by_id((object_id,)),
        "export-type:svg",
        f"export-filename:{output}",
        f"export-id:{object_id}",
        "export-id-only",
        "export-area-page",
        "export-do",
    ]


__all__ = [
    "INKSCAPE_ENVIRONMENT_VARIABLE",
    "InkscapeError",
    "MM_PER_INCH",
    "PX_PER_INCH",
    "difference_actions",
    "export_object_actions",
    "find_inkscape",
    "px_to_mm",
    "query_all",
    "run",
    "select_by_id",
    "union_actions",
]
