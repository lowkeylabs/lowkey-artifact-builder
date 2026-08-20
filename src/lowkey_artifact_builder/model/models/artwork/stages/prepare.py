"""
Artwork prepare stage.

The prepare stage converts the materialized source raster artwork into
a multicolor vector trace using the resolved artwork palette.

Filesystem layout and configuration resolution are responsibilities of
the build engine. This implementation consumes only the paths and
values supplied through StageContext.
"""

from __future__ import annotations

from lowkey_artifact_builder.engine import (
    StageContext,
)

# =========================================================
# Errors
# =========================================================


class PrepareError(RuntimeError):
    """
    Raised when artwork preparation cannot be completed.
    """


# =========================================================
# Stage implementation
# =========================================================


def execute(
    context: StageContext,
) -> None:
    """
    Execute the artwork prepare stage.

    The stage consumes:

        source
            Materialized source raster artwork.

        artwork_colors
            Resolved artwork palette.

    The stage produces:

        trace
            Multicolor SVG trace of the source artwork.

    The actual raster-to-vector tracing implementation has not yet
    been introduced.
    """

    source = context.input(
        "source",
    )

    trace = context.output(
        "trace",
    )

    artwork_colors = context.parameter(
        "artwork_colors",
    )

    if not source.is_file():
        raise PrepareError(f"Artwork source does not exist: {source}")

    if not artwork_colors:
        raise PrepareError("Artwork palette is empty.")

    raise PrepareError(
        f"Artwork prepare tracing is not yet implemented. Source: {source}; output: {trace}"
    )


__all__ = [
    "PrepareError",
    "execute",
]
