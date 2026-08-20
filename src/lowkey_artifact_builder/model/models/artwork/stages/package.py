"""
Artwork packaging stage.

The package stage combines the independently printable artwork STL
components into the final multicomponent 3MF artifact.

Filesystem layout and dependency resolution are responsibilities of
the build engine. This implementation consumes only the paths supplied
through StageContext.

The extrusion manifest identifies the dynamically generated STL
components that participate in the final artifact. The package stage
must use that manifest rather than discover components by scanning the
extrusion directory.
"""

from __future__ import annotations

from lowkey_artifact_builder.engine import (
    StageContext,
)

# =========================================================
# Errors
# =========================================================


class PackageError(RuntimeError):
    """
    Raised when artwork packaging cannot be completed.
    """


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

    The actual STL-to-3MF packaging implementation has not yet been
    introduced.
    """

    extrude_manifest = context.input(
        "extrude.manifest",
    )

    artifact = context.output(
        "artifact",
    )

    if not extrude_manifest.is_file():
        raise PackageError(f"Extrusion product manifest does not exist: {extrude_manifest}")

    raise PackageError(
        "Artwork 3MF packaging is not yet implemented. "
        f"Input manifest: {extrude_manifest}; "
        f"output artifact: {artifact}"
    )


__all__ = [
    "PackageError",
    "execute",
]
