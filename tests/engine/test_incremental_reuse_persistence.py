"""
Tests for persistence behavior when incremental products are reusable.
"""
# File: tests/engine/test_incremental_reuse_persistence.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path
from typing import Protocol

import pytest

import lowkey_artifact_builder.engine.incremental as incremental
from lowkey_artifact_builder.engine import (
    BuildPlan,
    PlannedStage,
    execute_incremental_build,
)

# =========================================================
# Test protocol
# =========================================================


class ArtworkPlanFactory(Protocol):
    """
    Factory for a realized artwork build plan.
    """

    def __call__(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> BuildPlan:
        """
        Create one realized artwork build plan.
        """
        ...


# =========================================================
# Helpers
# =========================================================


def _materialize_external_inputs(
    build_plan: BuildPlan,
) -> None:
    """
    Materialize external inputs required by the realized plan.
    """

    product_paths = {product.path for stage in build_plan.stages for product in stage.products}

    for stage in build_plan.stages:
        for planned_input in stage.inputs:
            if planned_input.path in product_paths:
                continue

            planned_input.path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            planned_input.path.write_text(
                f"external:{planned_input.name}",
                encoding="utf-8",
            )


def _materialize_stage_products(
    stage: PlannedStage,
) -> None:
    """
    Materialize every persistent product produced by one stage.
    """

    for product in stage.products:
        product.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        product.path.write_text(
            f"product:{stage.name}:{product.name}",
            encoding="utf-8",
        )


def _prepare_reusable_build(
    build_plan: BuildPlan,
) -> None:
    """
    Execute once so every persistent stage becomes reusable.
    """

    _materialize_external_inputs(
        build_plan,
    )

    execute_incremental_build(
        build_plan,
        execute_stage=_materialize_stage_products,
    )


# =========================================================
# Reuse persistence
# =========================================================


def test_reusable_build_writes_no_completion_metadata(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Fully reusable execution does not rewrite completion metadata.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    _prepare_reusable_build(
        build_plan,
    )

    written: list[str] = []

    def unexpected_completion_write(
        *,
        build_plan: BuildPlan,
        stage: PlannedStage,
        fingerprint,
    ) -> None:
        written.append(stage.name)

    monkeypatch.setattr(
        incremental,
        "_write_successful_completion",
        unexpected_completion_write,
    )

    execute_incremental_build(
        build_plan,
        execute_stage=_materialize_stage_products,
    )

    assert written == []


def test_partially_reused_build_writes_completion_only_for_executed_stage(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Completion persistence occurs only for stages actually re-executed.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    _prepare_reusable_build(
        build_plan,
    )

    affected = next(stage for stage in build_plan.stages if stage.products)

    affected.products[0].path.unlink()

    written: list[str] = []

    original_write = incremental._write_successful_completion

    def observe_completion_write(
        *,
        build_plan: BuildPlan,
        stage: PlannedStage,
        fingerprint,
    ) -> None:
        written.append(stage.name)

        original_write(
            build_plan=build_plan,
            stage=stage,
            fingerprint=fingerprint,
        )

    monkeypatch.setattr(
        incremental,
        "_write_successful_completion",
        observe_completion_write,
    )

    execute_incremental_build(
        build_plan,
        execute_stage=_materialize_stage_products,
    )

    assert written == [
        affected.name,
    ]
