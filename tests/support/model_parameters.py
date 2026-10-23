"""
Shared production-backed Model parameter resolvers for tests.
"""

# File: tests/support/model_parameters.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from lowkey_artifact_builder.config import ConfigError, Resolver, get_resolver


def model_test_resolver(
    model: str,
    *,
    overrides: Mapping[str, Any] | None = None,
    project_root: Path | None = None,
) -> Resolver:
    """
    Construct a production-backed Model resolver for tests.

    Model defaults, variants, and derivations are resolved by the
    authoritative configuration engine.

    Explicit overrides replace selected values without requiring
    tests to enumerate unrelated Model parameters.

    Unknown override names are rejected.
    """

    root = project_root if project_root is not None else Path(__file__).resolve().parent

    resolver = get_resolver(
        "model-test",
        model=model,
        project_root=root,
    )

    if not overrides:
        return resolver

    unknown = set(overrides).difference(resolver.names())

    if unknown:
        names = ", ".join(sorted(unknown))
        raise ConfigError(f"Unknown test configuration parameter(s): {names}")

    return resolver.with_values(
        overrides,
        provenance="test",
    )
