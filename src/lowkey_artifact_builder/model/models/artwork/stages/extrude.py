"""
Artwork extrusion stage.

The extrusion stage converts registered vector color layers into
independently printable STL components.

Filesystem layout, dependency resolution, and configuration resolution
are responsibilities of the build engine. This implementation consumes
only the paths and values supplied through StageContext.

The vector manifest identifies the dynamically generated vector layers
that participate in this stage. The generated STL components are
dynamic products whose filenames, geometry associations, and color
assignments are recorded in the declared extrusion manifest.
"""

from __future__ import annotations

from lowkey_artifact_builder.engine import (
    StageContext,
)

# =========================================================
# Errors
# =========================================================


class ExtrudeError(RuntimeError):
    """
    Raised when artwork extrusion cannot be completed.
    """


# =========================================================
# Stage implementation
# =========================================================


def execute(
    context: StageContext,
) -> None:
    """
    Execute the artwork extrusion stage.

    The stage consumes:

        vector.manifest
            Manifest describing the registered vector color layers
            produced by the vector stage.

        artwork_colors
            Resolved artwork palette.

        artwork_raise
            Physical extrusion height of the artwork geometry in
            millimeters.

    The stage produces:

        manifest
            Manifest describing the dynamically generated STL
            components and their artwork color assignments.

    The actual SVG-to-STL extrusion implementation has not yet been
    introduced.
    """

    vector_manifest = context.input(
        "vector.manifest",
    )

    extrude_manifest = context.output(
        "manifest",
    )

    artwork_colors = context.parameter(
        "artwork_colors",
    )

    artwork_raise = context.parameter(
        "artwork_raise",
    )

    if not vector_manifest.is_file():
        raise ExtrudeError(f"Vector product manifest does not exist: {vector_manifest}")

    if not artwork_colors:
        raise ExtrudeError("Artwork palette is empty.")

    if artwork_raise <= 0:
        raise ExtrudeError("Artwork raise must be greater than zero.")

    raise ExtrudeError(
        "Artwork extrusion is not yet implemented. "
        f"Input manifest: {vector_manifest}; "
        f"output manifest: {extrude_manifest}"
    )


__all__ = [
    "ExtrudeError",
    "execute",
]
