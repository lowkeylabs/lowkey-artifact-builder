"""
Architectural dependency tests for the Shape model.
"""
# File: tests/model/shape/test_dependencies.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import ast
from pathlib import Path

import lowkey_artifact_builder.model.models.shape.stages.extrude as shape_extrude

# =========================================================
# Architectural dependency tests
# =========================================================


def test_shape_extrude_does_not_depend_on_artwork_stage_implementation() -> None:
    """
    Shape composes shared mechanics without depending on Artwork stages.
    """

    source_path = Path(shape_extrude.__file__)
    source = source_path.read_text(
        encoding="utf-8",
    )

    tree = ast.parse(
        source,
    )

    forbidden_prefix = "lowkey_artifact_builder.model.models.artwork.stages"

    imported_modules = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }

    assert not any(
        module == forbidden_prefix or module.startswith(f"{forbidden_prefix}.")
        for module in imported_modules
    )
