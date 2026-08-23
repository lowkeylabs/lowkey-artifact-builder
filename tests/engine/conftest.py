"""
Shared fixtures for artifact build engine tests.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from lowkey_artifact_builder.config import Resolver
from lowkey_artifact_builder.engine import BuildPlan, create_build_plan


@pytest.fixture
def test_resolver() -> Resolver:
    """
    Construct the standard artifact configuration resolver used by
    engine tests.
    """

    return Resolver(
        values={
            "model": "artwork",
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
    [Path, pytest.MonkeyPatch],
    BuildPlan,
]:
    """
    Return a factory for standard artwork build plans.
    """

    def create(
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> BuildPlan:
        monkeypatch.setattr(
            "lowkey_artifact_builder.engine.plan.get_resolver",
            lambda artifact_id, project_root: test_resolver,
        )

        return create_build_plan(
            "example",
            project_root=tmp_path,
        )

    return create
