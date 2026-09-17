"""
Tests for engine-owned presentation naming.

These tests verify naming policies for user-facing files materialized by the
engine. Naming remains independent from Product identity and canonical Product
filesystem locations.
"""
# File: tests/engine/test_naming.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import pytest

from lowkey_artifact_builder.engine.naming import realization_3mf_filename


@pytest.mark.parametrize(
    ("realization_name", "expected"),
    [
        (
            "artwork_default",
            "artwork_default.3mf",
        ),
        (
            "shape_default",
            "shape_default.3mf",
        ),
        (
            "shape_ornament",
            "shape_ornament.3mf",
        ),
        (
            "christmas_ornament",
            "christmas_ornament.3mf",
        ),
    ],
)
def test_realization_3mf_filename_preserves_realization_identity(
    realization_name: str,
    expected: str,
) -> None:
    """
    Packaged 3MF convenience filenames preserve Realization identity.

    The Realization name is preserved verbatim, including underscores.
    A period is introduced only to separate the filename from its 3MF
    extension.

    The policy applies equally to canonical and explicitly named
    Realizations rather than reconstructing a filename from Model or
    Variant identity.
    """

    assert realization_3mf_filename(realization_name) == expected
