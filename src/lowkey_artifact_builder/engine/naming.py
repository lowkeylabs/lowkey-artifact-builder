"""
Engine-owned presentation naming utilities.

This module owns naming policies for user-facing files materialized by the
engine. These names are presentation conveniences and do not define Product
identity or canonical Product filesystem locations.
"""
# File: src/lowkey_artifact_builder/engine/naming.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations


def realization_3mf_filename(
    realization_name: str,
) -> str:
    """
    Return the convenience 3MF filename for a Realization.

    Realization identity is preserved verbatim. A period is introduced only
    to separate the Realization name from the 3MF extension.
    """

    return f"{realization_name}.3mf"


__all__ = [
    "realization_3mf_filename",
]
