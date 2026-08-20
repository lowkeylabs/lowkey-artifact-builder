"""
Artwork vector stage.

The vector stage converts registered raster color layers into
registered vector geometry at the configured physical artwork size.

Filesystem layout, dependency resolution, and configuration resolution
are responsibilities of the build engine. This implementation consumes
only the paths and values supplied through StageContext.

The raster manifest identifies the dynamically generated raster layers
that participate in this stage. The generated vector layers are dynamic
products whose filenames, dimensions, and color associations are
recorded in the declared vector manifest.
"""

from __future__ import annotations

from lowkey_artifact_builder.engine import (
    StageContext,
)

# =========================================================
# Errors
# =========================================================


class VectorError(RuntimeError):
    """
    Raised when artwork vector generation cannot be completed.
    """


# =========================================================
# Stage implementation
# =========================================================


def execute(
    context: StageContext,
) -> None:
    """
    Execute the artwork vector stage.

    The stage consumes:

        raster.manifest
            Manifest describing the registered raster color layers
            produced by the raster stage.

        artwork_size
            Physical size of the resulting artwork geometry in
            millimeters.

    The stage produces:

        manifest
            Manifest describing the dynamically generated registered
            vector color layers.

    The actual raster-to-vector conversion implementation has not yet
    been introduced.
    """

    raster_manifest = context.input(
        "raster.manifest",
    )

    vector_manifest = context.output(
        "manifest",
    )

    artwork_size = context.parameter(
        "artwork_size",
    )

    if not raster_manifest.is_file():
        raise VectorError(f"Raster product manifest does not exist: {raster_manifest}")

    if artwork_size <= 0:
        raise VectorError("Artwork size must be greater than zero.")

    raise VectorError(
        "Artwork vector generation is not yet implemented. "
        f"Input manifest: {raster_manifest}; "
        f"output manifest: {vector_manifest}"
    )


__all__ = [
    "VectorError",
    "execute",
]
