"""
Tests for lifecycle events from fully reusable incremental builds.
"""
# File: tests/engine/test_incremental_reused_build_events.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path
from typing import Protocol

import pytest

from lowkey_artifact_builder.engine import (
    BuildPlan,
    ExecutionEvent,
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
    Materialize every external input required by the realized plan.

    Inputs whose paths correspond to realized stage products are produced
    internally and must not be materialized as external inputs.
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


def _persistent_stage_names(
    build_plan: BuildPlan,
) -> tuple[str, ...]:
    """
    Return realized stages having persistent products.
    """

    return tuple(stage.name for stage in build_plan.stages if stage.products)


def _prepare_reusable_build(
    build_plan: BuildPlan,
) -> None:
    """
    Execute once so every persistent stage is reusable.
    """

    _materialize_external_inputs(
        build_plan,
    )

    execute_incremental_build(
        build_plan,
        execute_stage=_materialize_stage_products,
    )


# =========================================================
# Fully reusable build lifecycle
# =========================================================


def test_reusable_build_executes_no_stage(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    A fully reusable build performs no stage execution.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    _prepare_reusable_build(
        build_plan,
    )

    executed: list[str] = []

    execute_incremental_build(
        build_plan,
        execute_stage=lambda stage: executed.append(stage.name),
    )

    assert executed == []


def test_reusable_build_emits_build_lifecycle(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    A fully reusable build still starts and completes successfully.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    _prepare_reusable_build(
        build_plan,
    )

    events: list[ExecutionEvent] = []

    execute_incremental_build(
        build_plan,
        execute_stage=_materialize_stage_products,
        event_sink=events.append,
    )

    build_events = tuple(event.kind for event in events if event.kind.startswith("build."))

    assert build_events == (
        "build.started",
        "build.completed",
    )


def test_reusable_build_skips_every_persistent_stage(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Every reusable persistent stage is reported as skipped.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    _prepare_reusable_build(
        build_plan,
    )

    events: list[ExecutionEvent] = []

    execute_incremental_build(
        build_plan,
        execute_stage=_materialize_stage_products,
        event_sink=events.append,
    )

    skipped = tuple(event.stage_name for event in events if event.kind == "stage.skipped")

    assert skipped == _persistent_stage_names(
        build_plan,
    )


def test_reusable_build_emits_no_stage_execution_events(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Reused stages emit neither start, completion, nor failure events.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    _prepare_reusable_build(
        build_plan,
    )

    events: list[ExecutionEvent] = []

    execute_incremental_build(
        build_plan,
        execute_stage=_materialize_stage_products,
        event_sink=events.append,
    )

    execution_events = tuple(
        event
        for event in events
        if event.kind
        in {
            "stage.started",
            "stage.completed",
            "stage.failed",
        }
    )

    assert execution_events == ()


def test_reusable_build_events_preserve_build_order(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Fully reusable lifecycle observation preserves realized build order.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    _prepare_reusable_build(
        build_plan,
    )

    events: list[ExecutionEvent] = []

    execute_incremental_build(
        build_plan,
        execute_stage=_materialize_stage_products,
        event_sink=events.append,
    )

    lifecycle = tuple(
        (
            event.kind,
            event.stage_name,
        )
        for event in events
        if event.kind
        in {
            "build.started",
            "stage.skipped",
            "build.completed",
        }
    )

    assert lifecycle == (
        (
            "build.started",
            None,
        ),
        *(
            (
                "stage.skipped",
                stage_name,
            )
            for stage_name in _persistent_stage_names(
                build_plan,
            )
        ),
        (
            "build.completed",
            None,
        ),
    )
