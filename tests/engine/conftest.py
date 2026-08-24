"""
Shared fixtures for artifact build engine tests.
"""
# File: tests/engine/conftest.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from lowkey_artifact_builder.config import Resolver
from lowkey_artifact_builder.engine import (
    BuildPlan,
    create_build_plan,
)
from lowkey_artifact_builder.model import (
    ProductRef,
)


@pytest.fixture
def test_resolver() -> Resolver:
    """
    Construct the standard artifact configuration resolver used by
    engine tests.

    The resolver represents legacy single-realization artifact
    configuration, which resolves to the implicit realization named
    "default".
    """

    return Resolver(
        values={
            "model": "artwork",
            "realization": "default",
            "source": "source.png",
            "artwork_colors": [
                "white",
                "black",
            ],
            "artwork_pixels": 1024,
            "artwork_min_island_area": 0.5,
            "artwork_island_connectivity": 8,
            "artwork_size": 150.0,
            "artwork_raise": 1.0,
        },
        provenance={
            "model": "test",
            "realization": "test",
            "source": "test",
            "artwork_colors": "test",
            "artwork_pixels": "test",
            "artwork_min_island_area": "test",
            "artwork_island_connectivity": "test",
            "artwork_size": "test",
            "artwork_raise": "test",
        },
    )


@pytest.fixture
def artwork_plan(
    test_resolver: Resolver,
) -> Callable[
    [
        Path,
        pytest.MonkeyPatch,
        tuple[ProductRef, ...] | None,
    ],
    BuildPlan,
]:
    """
    Return a factory for standard artwork build plans.

    The standard plan exercises the legacy implicit-default realization
    while honoring the realization-aware get_resolver() interface.

    Optional product targets allow tests to construct Phase 7 targeted
    plans while preserving complete-build behavior when targets are
    omitted.
    """

    def create(
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        targets: tuple[ProductRef, ...] | None = None,
    ) -> BuildPlan:
        def fake_get_resolver(
            artifact_id: str,
            *,
            realization: str | None = None,
            project_root: Path,
        ) -> Resolver:
            assert artifact_id == "example"
            assert realization is None
            assert project_root == tmp_path

            return test_resolver

        monkeypatch.setattr(
            "lowkey_artifact_builder.engine.plan.get_resolver",
            fake_get_resolver,
        )

        return create_build_plan(
            "example",
            targets=targets,
            project_root=tmp_path,
        )

    return create
