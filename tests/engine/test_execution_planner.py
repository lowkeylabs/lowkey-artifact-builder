"""
Tests for persistent-state-aware execution planning.

Execution planning composes a realized BuildPlan with persistent product
state resolution to determine which realized stages require execution.

These tests exercise the high-level planning boundary using actual
filesystem products, completion metadata, and required build-context
fingerprints.

They do not execute stages, materialize external inputs, emit execution
events, or modify products except where persistent evidence is required
to establish test state.
"""
# File: tests/engine/test_execution_planner.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path

import pytest

from lowkey_artifact_builder.engine import (
    BuildPlan,
    PlannedStage,
    ProductFingerprint,
    ProductState,
    StageCompletion,
    plan_execution,
    write_stage_completion,
)

type ArtworkPlanFactory = Callable[..., BuildPlan]


# =========================================================
# Helpers
# =========================================================


def _fingerprint(
    stage: PlannedStage,
) -> ProductFingerprint:
    """
    Create deterministic representative provenance for one stage.
    """

    return ProductFingerprint(
        algorithm="sha256",
        value=stage.name,
    )


def _stage_working_dir(
    build_plan: BuildPlan,
    stage: PlannedStage,
) -> Path:
    """
    Return the established working directory for one realized stage.
    """

    if not stage.products:
        return build_plan.artifact_dir

    return Path(os.path.commonpath([product.path.parent for product in stage.products]))


def _materialize_stage(
    build_plan: BuildPlan,
    stage: PlannedStage,
    *,
    fingerprint: ProductFingerprint | None,
) -> None:
    """
    Materialize all persistent products and completion for one stage.
    """

    working_dir = _stage_working_dir(
        build_plan,
        stage,
    )

    working_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    for product in stage.products:
        product.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        product.path.write_text(
            product.name,
            encoding="utf-8",
        )

    write_stage_completion(
        working_dir,
        StageCompletion(
            artifact_id=build_plan.artifact_id,
            model_name=build_plan.model_name,
            realization=build_plan.realization_name,
            stage_name=stage.name,
            products=tuple(product.name for product in stage.products),
            fingerprint=fingerprint,
        ),
    )


def _persistent_stages(
    build_plan: BuildPlan,
) -> tuple[PlannedStage, ...]:
    """
    Return realized stages declaring persistent products.
    """

    return tuple(stage for stage in build_plan.stages if stage.products)


# =========================================================
# Execution planning
# =========================================================


def test_plan_execution_preserves_build_identity(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Persistent-state-aware planning preserves artifact realization identity.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    execution_plan = plan_execution(
        build_plan,
        required_fingerprint=_fingerprint,
    )

    assert execution_plan.artifact_id == build_plan.artifact_id
    assert execution_plan.model_name == build_plan.model_name
    assert execution_plan.realization == build_plan.realization_name


def test_plan_execution_preserves_complete_stage_order(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Execution planning retains the complete realized workflow.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    execution_plan = plan_execution(
        build_plan,
        required_fingerprint=_fingerprint,
    )

    assert tuple(stage.stage_name for stage in execution_plan.stages) == tuple(
        stage.name for stage in build_plan.stages
    )


def test_missing_products_require_execution(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    A fresh workspace requires all realized persistent work.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    execution_plan = plan_execution(
        build_plan,
        required_fingerprint=_fingerprint,
    )

    for stage in execution_plan.stages:
        if stage.product_states:
            assert stage.product_states == tuple(ProductState.ABSENT for _ in stage.product_states)
            assert stage.requires_execution


def test_current_persistent_stages_are_reusable(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Completed stages with matching provenance need not execute again.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    for stage in _persistent_stages(
        build_plan,
    ):
        _materialize_stage(
            build_plan,
            stage,
            fingerprint=_fingerprint(
                stage,
            ),
        )

    execution_plan = plan_execution(
        build_plan,
        required_fingerprint=_fingerprint,
    )

    for stage in execution_plan.stages:
        if stage.product_states:
            assert stage.product_states == tuple(ProductState.CURRENT for _ in stage.product_states)
            assert not stage.requires_execution


def test_stale_stage_requires_execution(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Changed provenance causes the affected producing stage to execute.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    persistent_stages = _persistent_stages(
        build_plan,
    )

    stale_stage = persistent_stages[0]

    for stage in persistent_stages:
        fingerprint = (
            ProductFingerprint(
                algorithm="sha256",
                value="old",
            )
            if stage is stale_stage
            else _fingerprint(
                stage,
            )
        )

        _materialize_stage(
            build_plan,
            stage,
            fingerprint=fingerprint,
        )

    execution_plan = plan_execution(
        build_plan,
        required_fingerprint=_fingerprint,
    )

    planned_stale_stage = next(
        stage for stage in execution_plan.stages if stage.stage_name == stale_stage.name
    )

    assert all(state is ProductState.STALE for state in planned_stale_stage.product_states)
    assert planned_stale_stage.requires_execution


def test_only_noncurrent_persistent_stage_is_required(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Reusable persistent stages are omitted from required execution work.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    persistent_stages = _persistent_stages(
        build_plan,
    )

    missing_stage = persistent_stages[-1]

    for stage in persistent_stages:
        if stage is missing_stage:
            continue

        _materialize_stage(
            build_plan,
            stage,
            fingerprint=_fingerprint(
                stage,
            ),
        )

    execution_plan = plan_execution(
        build_plan,
        required_fingerprint=_fingerprint,
    )

    required_persistent_names = tuple(
        stage.stage_name for stage in execution_plan.required_stages if stage.product_states
    )

    assert required_persistent_names == (missing_stage.name,)


def test_missing_required_fingerprint_makes_completed_stage_stale(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Completion cannot prove reuse when current provenance is unavailable.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    stage = _persistent_stages(
        build_plan,
    )[0]

    _materialize_stage(
        build_plan,
        stage,
        fingerprint=_fingerprint(
            stage,
        ),
    )

    execution_plan = plan_execution(
        build_plan,
        required_fingerprint=lambda candidate: (
            None if candidate is stage else _fingerprint(candidate)
        ),
    )

    planned_stage = next(
        candidate for candidate in execution_plan.stages if candidate.stage_name == stage.name
    )

    assert planned_stage.product_states == tuple(ProductState.STALE for _ in stage.products)

    assert planned_stage.requires_execution


# =========================================================
# Fingerprint resolution
# =========================================================


def test_plan_execution_resolves_required_fingerprint_per_product(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Planning requests current provenance for every declared product state.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    calls: list[PlannedStage] = []

    def required_fingerprint(
        stage: PlannedStage,
    ) -> ProductFingerprint:
        calls.append(
            stage,
        )

        return _fingerprint(
            stage,
        )

    plan_execution(
        build_plan,
        required_fingerprint=required_fingerprint,
    )

    expected = [stage for stage in build_plan.stages for _ in stage.products]

    assert calls == expected
