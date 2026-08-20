"""
External tool interfaces.

This package provides low-level interfaces to external applications
used by lowkey-artifact-builder.

Tool modules are intentionally independent of artifact models and build
stages. They provide reusable operations that higher-level subsystems
may use without embedding application-specific invocation details.
"""

from .inkscape import (
    InkscapeError,
    find_inkscape,
)
from .openscad import (
    OpenSCADError,
    find_openscad,
)

__all__ = [
    "InkscapeError",
    "OpenSCADError",
    "find_inkscape",
    "find_openscad",
]
