"""
Utilities for invoking the OpenSCAD command-line interface.

This module provides the low-level interface between
lowkey-artifact-builder and OpenSCAD.

It contains no artifact-model or build-stage behavior. Higher-level
subsystems use these operations to render OpenSCAD models into
filesystem products such as STL files.
"""
# File: src/lowkey_artifact_builder/tools/openscad.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path

OPENSCAD_ENVIRONMENT_VARIABLE = "LOWKEY_ARTIFACT_OPENSCAD"

OpenSCADValue = str | int | float | bool


# =========================================================
# Errors
# =========================================================


class OpenSCADError(RuntimeError):
    """
    Raised when an OpenSCAD operation cannot be completed.
    """


# =========================================================
# Executable discovery
# =========================================================


def find_openscad() -> str:
    """
    Find the OpenSCAD executable.

    Search order:

        1. LOWKEY_ARTIFACT_OPENSCAD environment variable.
        2. Native ``openscad`` executable on PATH.
        3. Standard Windows installation paths under WSL.

    Raises:
        OpenSCADError:
            If OpenSCAD cannot be found.
    """

    configured = os.environ.get(OPENSCAD_ENVIRONMENT_VARIABLE)

    if configured:
        executable = Path(configured)

        if executable.is_file():
            return str(executable)

        raise OpenSCADError(
            f"{OPENSCAD_ENVIRONMENT_VARIABLE} points to a file that does not exist: {configured}"
        )

    executable = shutil.which("openscad")

    if executable is not None:
        return executable

    windows_candidates = (
        Path("/mnt/c/Program Files/OpenSCAD/openscad.exe"),
        Path("/mnt/c/Program Files/OpenSCAD (Nightly)/openscad.exe"),
    )

    for candidate in windows_candidates:
        if candidate.is_file():
            return str(candidate)

    raise OpenSCADError(
        "Could not find OpenSCAD.\n"
        f"Set {OPENSCAD_ENVIRONMENT_VARIABLE} to the "
        "path of the OpenSCAD executable."
    )


# =========================================================
# Definitions
# =========================================================


def format_define(
    name: str,
    value: OpenSCADValue,
) -> str:
    """
    Format a Python value for an OpenSCAD ``-D`` definition.

    Examples:

        ornament_od=100
        label_raise=1.5
        enabled=true
        label_svg="/tmp/labels.svg"
    """

    if isinstance(
        value,
        bool,
    ):
        encoded = "true" if value else "false"

    elif isinstance(
        value,
        str,
    ):
        escaped = value.replace(
            "\\",
            "\\\\",
        ).replace(
            '"',
            '\\"',
        )

        encoded = f'"{escaped}"'

    elif isinstance(
        value,
        int | float,
    ):
        encoded = str(value)

    else:
        raise OpenSCADError(
            f"Unsupported OpenSCAD parameter type for {name}: {type(value).__name__}"
        )

    return f"{name}={encoded}"


# =========================================================
# Invocation
# =========================================================


def run(
    scad: Path,
    *,
    output: Path | None = None,
    defines: Mapping[
        str,
        OpenSCADValue,
    ]
    | None = None,
    args: Sequence[str] = (),
) -> str:
    """
    Run OpenSCAD against a SCAD document.

    Args:
        scad:
            OpenSCAD source document.

        output:
            Optional output file. The output format is
            determined by OpenSCAD from the extension.

        defines:
            Values passed to OpenSCAD using ``-D``.

        args:
            Additional OpenSCAD command-line arguments.

    Returns:
        Combined diagnostic output from OpenSCAD.

    Raises:
        OpenSCADError:
            If the SCAD file does not exist, OpenSCAD
            cannot be found, or OpenSCAD exits
            unsuccessfully.
    """

    scad = Path(scad)

    if not scad.is_file():
        raise OpenSCADError(f"OpenSCAD file does not exist: {scad}")

    executable = find_openscad()

    command = [
        executable,
    ]

    if output is not None:
        output = Path(output)

        output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        command.extend(
            [
                "-o",
                str(output),
            ]
        )

    if defines:
        for name, value in defines.items():
            command.extend(
                [
                    "-D",
                    format_define(
                        name,
                        value,
                    ),
                ]
            )

    command.extend(args)

    command.append(str(scad))

    try:
        result = subprocess.run(
            command,
            text=True,
            capture_output=True,
            check=False,
        )

    except OSError as exc:
        raise OpenSCADError(f"Could not execute OpenSCAD.\nCommand: {' '.join(command)}") from exc

    #
    # OpenSCAD writes most diagnostics, including ECHO,
    # to stderr rather than stdout.
    #

    diagnostic_output = "\n".join(
        part
        for part in (
            result.stdout.strip(),
            result.stderr.strip(),
        )
        if part
    )

    if result.returncode != 0:
        raise OpenSCADError(
            "OpenSCAD failed.\n"
            f"Command: {' '.join(command)}\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )

    return diagnostic_output


# =========================================================
# STL rendering
# =========================================================


def render_stl(
    scad: Path,
    output: Path,
    *,
    defines: Mapping[
        str,
        OpenSCADValue,
    ]
    | None = None,
) -> Path:
    """
    Render an OpenSCAD document to STL.

    Returns the output path.
    """

    output = Path(output)

    if output.suffix.lower() != ".stl":
        raise OpenSCADError(f"STL output filename must end in .stl: {output}")

    run(
        scad,
        output=output,
        defines=defines,
    )

    if not output.is_file():
        raise OpenSCADError(f"OpenSCAD completed without creating the expected STL: {output}")

    return output


def render_stl_source(
    source: str,
    output: Path,
) -> Path:
    """
    Render OpenSCAD source text directly to STL.

    The source is materialized temporarily beside the output so relative
    filesystem behavior remains local to the rendering operation.
    """

    output = Path(output)

    if output.suffix.lower() != ".stl":
        raise OpenSCADError(f"STL output filename must end in .stl: {output}")

    if not isinstance(
        source,
        str,
    ):
        raise OpenSCADError("OpenSCAD source must be a string.")

    if not source.strip():
        raise OpenSCADError("OpenSCAD source cannot be empty.")

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_directory = output.parent.resolve()

    scad: Path | None = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".scad",
            prefix=".lowkey-artifact-",
            dir=output_directory,
            encoding="utf-8",
            delete=False,
        ) as file:
            scad = Path(file.name)

            file.write(source)

        return render_stl(
            scad,
            output,
        )

    except OpenSCADError:
        raise

    except OSError as exc:
        raise OpenSCADError(
            f"Could not create temporary OpenSCAD source for {output}: {exc}"
        ) from exc

    finally:
        if scad is not None:
            scad.unlink(
                missing_ok=True,
            )


__all__ = [
    "OPENSCAD_ENVIRONMENT_VARIABLE",
    "OpenSCADError",
    "OpenSCADValue",
    "find_openscad",
    "format_define",
    "render_stl",
    "render_stl_source",
    "run",
]
