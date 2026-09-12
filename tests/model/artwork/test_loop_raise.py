"""
Tests for Artwork Loop raise semantics.

Loop raise may be configured explicitly. Otherwise its effective value derives
from the effective Artwork raise.
"""
# File: tests/model/artwork/test_loop_raise.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path

import pytest

from lowkey_artifact_builder.config import (
    get_resolver,
    write_artifact_config,
)


def _resolver_with_parameters(
    tmp_path: Path,
    parameters: dict[str, object],
):
    """
    Return an ordinary Artwork Realization resolver with parameter overrides.
    """

    write_artifact_config(
        "example",
        {
            "realizations": {
                "custom": {
                    "model": "artwork",
                    "variant": "default",
                    "parameters": parameters,
                },
            },
        },
        project_root=tmp_path,
    )

    return get_resolver(
        "example",
        realization="custom",
        project_root=tmp_path,
    )


def test_loop_raise_defaults_to_artwork_raise(
    tmp_path: Path,
) -> None:
    """
    Loop raise derives from Artwork raise when not explicitly configured.
    """

    resolver = get_resolver(
        "example",
        model="artwork",
        project_root=tmp_path,
    )

    assert resolver("loop_raise") == pytest.approx(resolver("artwork_raise"))


def test_changing_artwork_raise_changes_derived_loop_raise(
    tmp_path: Path,
) -> None:
    """
    Derived Loop raise follows an explicitly configured Artwork raise.
    """

    resolver = _resolver_with_parameters(
        tmp_path,
        {
            "artwork_raise": 2.75,
        },
    )

    assert resolver("artwork_raise") == pytest.approx(2.75)
    assert resolver("loop_raise") == pytest.approx(2.75)


def test_explicit_loop_raise_overrides_artwork_raise(
    tmp_path: Path,
) -> None:
    """
    Explicit Loop raise is authoritative over its derived value.
    """

    resolver = _resolver_with_parameters(
        tmp_path,
        {
            "artwork_raise": 2.75,
            "loop_raise": 1.25,
        },
    )

    assert resolver("artwork_raise") == pytest.approx(2.75)
    assert resolver("loop_raise") == pytest.approx(1.25)


def test_explicit_loop_raise_is_independent_of_artwork_raise(
    tmp_path: Path,
) -> None:
    """
    Changing Artwork raise does not replace an explicit Loop raise.
    """

    resolver = _resolver_with_parameters(
        tmp_path,
        {
            "artwork_raise": 4.0,
            "loop_raise": 0.75,
        },
    )

    assert resolver("artwork_raise") == pytest.approx(4.0)
    assert resolver("loop_raise") == pytest.approx(0.75)


def test_default_loop_raise_is_derived(
    tmp_path: Path,
) -> None:
    """
    Default Loop raise is derived rather than independently model-defaulted.
    """

    resolver = get_resolver(
        "example",
        model="artwork",
        project_root=tmp_path,
    )

    assert resolver.source("loop_raise") == "derived"
