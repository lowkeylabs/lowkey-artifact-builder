"""
Artifact creation presentation.

This module contains CLI presentation for source-intake status.
"""

# File: src/lowkey_artifact_builder/cli/display/create.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from lowkey_artifact_builder.cli.display.common import (
    console,
    create_table,
)

# =========================================================
# Create status
# =========================================================


def display_create_status(
    artifact_ids: Sequence[str],
    sources: Sequence[Path],
) -> None:
    """
    Display the read-only source-intake overview for CREATE.
    """

    artifacts_table = create_table(
        title="Existing Artifacts",
    )

    artifacts_table.add_column(
        "Artifact",
    )

    for artifact_id in artifact_ids:
        artifacts_table.add_row(
            artifact_id,
        )

    console.print(artifacts_table)

    console.print()

    sources_table = create_table(
        title="Incoming PNGs",
    )

    sources_table.add_column(
        "Source",
    )

    for source in sources:
        sources_table.add_row(
            source.name,
        )

    console.print(sources_table)


__all__ = [
    "display_create_status",
]
