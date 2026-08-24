"""
Common CLI display utilities.

This module contains presentation primitives shared by the CLI display
modules.

Domain-specific presentation belongs in the corresponding display
module rather than here.
"""
# File: src/lowkey_artifact_builder/cli/display/common.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import Any

from rich.console import Console
from rich.table import Table

# =========================================================
# Console
# =========================================================


console = Console()


# =========================================================
# Tables
# =========================================================


def create_table(
    *args: Any,
    **kwargs: Any,
) -> Table:
    """
    Create a table using the standard CLI table style.

    Tables have no outer border or vertical column separators. A
    horizontal separator is displayed around the header row.
    """

    defaults: dict[str, Any] = {
        "box": None,
        "show_edge": False,
        "show_lines": False,
        "header_style": "bold",
    }

    defaults.update(kwargs)

    return Table(
        *args,
        **defaults,
    )


# =========================================================
# Formatting
# =========================================================


def format_value(
    value: object,
) -> str:
    """
    Format a general value for CLI presentation.

    Sequences are displayed as comma-separated values. Other values
    use their normal string representation.
    """

    if isinstance(
        value,
        list | tuple,
    ):
        return ", ".join(str(item) for item in value)

    return str(value)


__all__ = [
    "console",
    "create_table",
    "format_value",
]
