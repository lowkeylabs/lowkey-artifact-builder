#!/usr/bin/env python3
"""
Verify external tools required to develop and test lowkey-artifact-builder.
"""
# File: scripts/check_dependencies.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import shutil
import subprocess
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class Dependency:
    name: str
    command: tuple[str, ...]


DEPENDENCIES = (
    Dependency(
        name="Pyright",
        command=("pyright", "--version"),
    ),
    Dependency(
        name="Inkscape",
        command=("inkscape", "--version"),
    ),
    Dependency(
        name="OpenSCAD",
        command=("openscad", "--version"),
    ),
)


def check_dependency(dependency: Dependency) -> bool:
    executable = dependency.command[0]

    path = shutil.which(executable)

    if path is None:
        print(f"FAIL  {dependency.name}: {executable!r} not found on PATH")
        return False

    try:
        result = subprocess.run(
            dependency.command,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"FAIL  {dependency.name}: {exc}")
        return False

    output = (result.stdout or result.stderr).strip().splitlines()

    version = output[0] if output else "version unknown"

    print(f"OK    {dependency.name}: {version}")
    print(f"      {path}")

    return True


def main() -> int:
    print("Checking development dependencies...")
    print()

    results = [check_dependency(dependency) for dependency in DEPENDENCIES]

    print()

    if all(results):
        print("All development dependencies are available.")
        return 0

    print("One or more development dependencies are unavailable.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
