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
    Construct the standard Artifact configuration resolver used by
    engine tests.

    The resolver represents the canonical default Realization of the
    Artwork Model's default Variant.

    Model defaults and derived values required by the realized Artwork
    stages are represented explicitly because this fixture constructs a
    Resolver directly rather than through model configuration resolution.
    """

    return Resolver(
        values={
            "model": "artwork",
            "variant": "default",
            "realization": "artwork_default",
            "source": "source.png",
            "artifact_color_count": 2,
            "artwork_envelope_mode": "shrink-wrap",
            "printer_colors": [
                "cold-white",
                "black",
            ],
            "artwork_pixels": 1024,
            "artwork_min_island_area": 0.5,
            "artwork_island_connectivity": 8,
            "artwork_size": 150.0,
            "artwork_raise": 1.0,
            "loop_inner_diameter": 0.0,
            "loop_width": 1.0,
            "loop_position": 0,
            "loop_raise": 1.0,
        },
        provenance={
            "model": "test",
            "variant": "test",
            "realization": "test",
            "source": "test",
            "artifact_color_count": "test",
            "artwork_envelope_mode": "test",
            "printer_colors": "test",
            "artwork_pixels": "test",
            "artwork_min_island_area": "test",
            "artwork_island_connectivity": "test",
            "artwork_size": "test",
            "artwork_raise": "test",
            "loop_inner_diameter": "test",
            "loop_width": "test",
            "loop_position": "test",
            "loop_raise": "test",
        },
        colors={
            "cold-white": {},
            "black": {},
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
    Return a factory for standard Artwork build plans.

    The fixture supplies the canonical ``artwork_default`` Realization
    directly so tests using it remain focused on build planning rather than
    Artifact configuration or Variant-to-Realization selection.

    Tests specifically concerned with Variant or default-Realization
    selection should exercise that behavior independently.

    Optional product targets allow tests to construct targeted plans while
    preserving complete-build behavior when targets are omitted.
    """

    def create(
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        targets: tuple[ProductRef, ...] | None = None,
    ) -> BuildPlan:
        def fake_get_resolver(
            artifact_id: str,
            *,
            model: str | None = None,
            realization: str | None = None,
            project_root: Path,
        ) -> Resolver:
            assert artifact_id == "example"
            assert project_root == tmp_path

            # This fixture represents one already-selected execution
            # identity. It intentionally does not emulate realization
            # discovery.
            assert model is None or model == "artwork"
            assert realization == "artwork_default"

            return test_resolver

        monkeypatch.setattr(
            "lowkey_artifact_builder.engine.plan.get_resolver",
            fake_get_resolver,
        )

        return create_build_plan(
            "example",
            realization="artwork_default",
            targets=targets,
            project_root=tmp_path,
        )

    return create
