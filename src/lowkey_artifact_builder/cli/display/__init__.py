"""
CLI display helpers.

This package provides presentation functions and shared display
primitives used by the command-line interface.

Display implementation is divided by presentation domain while this
module preserves a single public import surface for CLI callers.
"""

from __future__ import annotations

from lowkey_artifact_builder.cli.display.build import (
    display_build_plan,
)
from lowkey_artifact_builder.cli.display.common import (
    console,
    create_table,
    format_value,
)
from lowkey_artifact_builder.cli.display.config import (
    display_artifact_config,
)
from lowkey_artifact_builder.cli.display.models import (
    display_model,
    display_model_workplan,
    display_model_workplans,
    display_models,
)

__all__ = [
    "console",
    "create_table",
    "display_artifact_config",
    "display_build_plan",
    "display_model",
    "display_model_workplan",
    "display_model_workplans",
    "display_models",
    "format_value",
]
