"""
Artwork prepare stage.

The prepare stage converts the materialized source raster artwork into
a multicolor SVG trace.

Filesystem layout and configuration resolution are responsibilities of
the build engine. This implementation consumes only the inputs,
parameters, and outputs supplied through StageContext.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

from lowkey_artifact_builder.engine import (
    StageContext,
)
from lowkey_artifact_builder.tools.inkscape import (
    InkscapeError,
    run,
)

# =========================================================
# Errors
# =========================================================


class PrepareError(RuntimeError):
    """
    Raised when artwork preparation cannot be completed.
    """


# =========================================================
# Trace defaults
# =========================================================


DEFAULT_SPECKLES = 2
DEFAULT_SMOOTH_CORNERS = 1.0
DEFAULT_OPTIMIZE = 0.2


# =========================================================
# Public interface
# =========================================================


def execute(
    context: StageContext,
) -> None:
    """
    Execute the artwork prepare stage.

    Inputs:

        source
            Materialized source PNG.

    Parameters:

        artwork_colors
            Ordered sequence of configured artwork color names.

            The number of configured colors determines the number of
            colors retained by the multicolor trace. Color assignment
            is performed by a later stage.

    Outputs:

        trace
            Multicolor SVG trace.

    The traced SVG intentionally contains both the original raster
    image and the generated vector trace. This preserves the behavior
    of the original artwork workflow and makes the intermediate SVG
    useful for visual inspection.
    """

    source = context.input(
        "source",
    )

    output = context.output(
        "trace",
    )

    colors = _require_colors(
        context.parameter(
            "artwork_colors",
        )
    )

    _trace_multicolor(
        source,
        output,
        colors=len(colors),
    )


# =========================================================
# Validation
# =========================================================


def _require_colors(
    value: Any,
) -> tuple[str, ...]:
    """
    Return a validated sequence of artwork color names.

    At least two colors are required for Inkscape's multicolor trace.
    Color names must be unique because later stages perform a
    one-to-one assignment between traced regions and configured
    artwork colors.
    """

    if isinstance(
        value,
        str | bytes,
    ) or not isinstance(
        value,
        Sequence,
    ):
        raise PrepareError("artwork_colors must be a sequence of color names.")

    colors: list[str] = []

    for color in value:
        if (
            not isinstance(
                color,
                str,
            )
            or not color.strip()
        ):
            raise PrepareError("artwork_colors must contain non-empty color names.")

        colors.append(color.strip())

    if len(colors) < 2:
        raise PrepareError("artwork_colors must contain at least two colors.")

    if len(set(colors)) != len(colors):
        raise PrepareError("artwork_colors must contain unique color names.")

    return tuple(colors)


def _require_source(
    source: Path,
) -> None:
    """
    Validate the source raster artwork.
    """

    if not source.is_file():
        raise PrepareError(f"Source artwork does not exist: {source}")

    if source.suffix.lower() != ".png":
        raise PrepareError(f"Source artwork must be a PNG file: {source}")


def _require_output(
    source: Path,
    output: Path,
) -> None:
    """
    Validate the trace output path.
    """

    if output.suffix.lower() != ".svg":
        raise PrepareError(f"Trace output must be an SVG file: {output}")

    if source.resolve() == output.resolve():
        raise PrepareError("Trace output must differ from the source artwork.")


# =========================================================
# Multicolor tracing
# =========================================================


def _trace_multicolor(
    source: Path,
    output: Path,
    *,
    colors: int,
    smooth: bool = True,
    stack: bool = True,
    remove_background: bool = False,
    speckles: int = DEFAULT_SPECKLES,
    smooth_corners: float = DEFAULT_SMOOTH_CORNERS,
    optimize: float = DEFAULT_OPTIMIZE,
) -> None:
    """
    Trace a PNG into an inspectable multicolor SVG.

    Inkscape opens the PNG directly, performs a multicolor bitmap
    trace, and exports the complete page as SVG.

    The action sequence is inherited from the original working artwork
    pipeline.
    """

    source = Path(
        source,
    )

    output = Path(
        output,
    ).resolve()

    _require_source(
        source,
    )

    _require_output(
        source,
        output,
    )

    if colors < 2:
        raise PrepareError("Trace color count must be at least two.")

    if speckles < 0:
        raise PrepareError("Trace speckle size cannot be negative.")

    if smooth_corners < 0:
        raise PrepareError("Trace corner smoothing cannot be negative.")

    if optimize < 0:
        raise PrepareError("Trace optimization tolerance cannot be negative.")

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    trace_parameters = ",".join(
        (
            str(colors),
            _bool_value(smooth),
            _bool_value(stack),
            _bool_value(remove_background),
            str(speckles),
            str(smooth_corners),
            str(optimize),
        )
    )

    actions = (
        "select-all",
        f"object-trace:{trace_parameters}",
        "export-type:svg",
        f"export-filename:{output}",
        "export-area-page",
        "export-do",
    )

    try:
        run(
            source,
            actions=actions,
        )

    except InkscapeError as exc:
        raise PrepareError(f"Could not trace source artwork: {source}") from exc

    if not output.is_file():
        raise PrepareError(f"Inkscape did not create the expected trace output: {output}")


# =========================================================
# Helpers
# =========================================================


def _bool_value(
    value: bool,
) -> str:
    """
    Return the boolean representation expected by Inkscape's
    object-trace action.
    """

    return "true" if value else "false"


__all__ = [
    "PrepareError",
    "execute",
]
