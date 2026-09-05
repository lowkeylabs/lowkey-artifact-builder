"""
Tests for Variant-oriented CLI helpers.
"""
# File: tests/cli/test_variants.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import click
import pytest

from lowkey_artifact_builder.cli.variants import (
    parse_variant_reference,
)


def test_parse_variant_reference_accepts_bare_variant() -> None:
    """
    A bare Variant reference contains only its local Variant name.
    """

    assert parse_variant_reference("default") == (
        None,
        "default",
    )


def test_parse_variant_reference_accepts_qualified_variant() -> None:
    """
    A qualified Variant reference identifies its Model and local name.
    """

    assert parse_variant_reference("shape.ornament") == (
        "shape",
        "ornament",
    )


def test_parse_variant_reference_rejects_malformed_variant() -> None:
    """
    A Variant reference must be either a local name or model.local-name.
    """

    for reference in (
        "",
        ".ornament",
        "shape.",
        "shape.ornament.extra",
    ):
        with pytest.raises(
            click.UsageError,
            match="Invalid Variant",
        ):
            parse_variant_reference(reference)
