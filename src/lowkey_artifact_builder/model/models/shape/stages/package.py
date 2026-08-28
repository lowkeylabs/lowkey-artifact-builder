"""
Shape packaging stage.

The package stage combines independently produced physical Shape components
into the final multicomponent 3MF artifact.

Filesystem layout and dependency resolution are responsibilities of the build
engine. This implementation consumes only paths supplied through StageContext.

The current Shape workflow produces one physical base STL. Later Shape
features may contribute additional independently printable components without
changing the responsibility of this stage.
"""
# File: src/lowkey_artifact_builder/model/models/shape/stages/package.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

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

        extrude.base
            Independently printable physical Shape base STL.

    The stage produces:

        artifact
            Final Shape 3MF artifact.

    Packaging does not construct, dimensionalize, or otherwise interpret
    Shape geometry. Those responsibilities belong to upstream stages.
    """

    base = context.input(
        "extrude.base",
    )

    artifact = context.output(
        "artifact",
    )

    if not base.is_file():
        raise PackageError(f"Shape base component does not exist: {base}")

    try:
        write_stls(
            (
                (
                    _base_component_name(
                        context.artifact_id,
                    ),
                    base,
                ),
            ),
            artifact,
        )

        if not artifact.is_file():
            raise PackageError(
                f"3MF packaging completed without creating the expected artifact: {artifact}"
            )

    except PackageError:
        raise

    except ThreeMFError as exc:
        raise PackageError(f"Could not package Shape base component {base}: {exc}") from exc

    except (
        OSError,
        ValueError,
        TypeError,
    ) as exc:
        raise PackageError(f"Could not package Shape base component {base}: {exc}") from exc


# =========================================================
# Component naming
# =========================================================


def _base_component_name(
    artifact_id: str,
) -> str:
    """
    Return the semantic 3MF object name for the Shape base.

    Object identity combines artifact identity with the semantic role of
    the physical component rather than depending on its filesystem name.

    For example:

        coaster-base
        ornament-base
    """

    return f"{artifact_id}-base"


__all__ = [
    "PackageError",
    "execute",
]
