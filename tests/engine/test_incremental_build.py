"""
Tests for persistent-state-aware incremental build execution.

Incremental build execution combines persistent-state-aware planning with
the established stage-execution boundary.

Only stages whose persistent products cannot be reused are executed.
Successful stage execution records completion metadata using the required
fingerprint for the current build context.

These tests exercise incremental execution of an already-realized
BuildPlan. They do not test CLI behavior or BuildPlan construction.
"""
# File: tests/engine/test_incremental_build.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from lowkey_artifact_builder.engine import (
    BuildPlan,
    PlannedStage,
    ProductFingerprint,
    StageCompletion,
    create_required_fingerprints,
    execute_incremental_build,
    read_stage_completion,
    write_stage_completion,
)

type ArtworkPlanFactory = Callable[..., BuildPlan]


# =========================================================
# Helpers
# =========================================================


def _materialize_external_inputs(
    build_plan: BuildPlan,
    *,
    content: bytes = b"incremental-build-input",
) -> None:
    """
    Materialize deterministic content for all external inputs.
    """

    for stage in build_plan.stages:
        for planned_input in stage.inputs:
            planned_input.path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            planned_input.path.write_bytes(
                content,
            )


def _stage_working_dir(
    stage: PlannedStage,
) -> Path:
    """
    Return the realized working directory of one persistent stage.
    """

    if not stage.products:
        raise AssertionError(f"Stage {stage.name!r} declares no persistent products.")

    working_dirs = {product.path.parent for product in stage.products}

    if len(working_dirs) != 1:
        raise AssertionError(f"Stage {stage.name!r} products do not share one working directory.")

    return next(
        iter(
            working_dirs,
        )
    )


def _materialize_stage_products(
    stage: PlannedStage,
) -> None:
    """
    Materialize every declared persistent product of one stage.
    """

    for product in stage.products:
        product.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        product.path.write_bytes(
            b"persistent-product",
        )


def _record_stage_current(
    build_plan: BuildPlan,
    stage: PlannedStage,
    fingerprint: ProductFingerprint,
) -> None:
    """
    Materialize one stage and record current completion metadata.
    """

    _materialize_stage_products(
        stage,
    )

    write_stage_completion(
        _stage_working_dir(
            stage,
        ),
        StageCompletion(
            artifact_id=build_plan.artifact_id,
            model_name=build_plan.model_name,
            realization=build_plan.realization_name,
            stage_name=stage.name,
            products=tuple(product.name for product in stage.products),
            fingerprint=fingerprint,
        ),
    )


def _record_all_stages_current(
    build_plan: BuildPlan,
) -> dict[str, ProductFingerprint]:
    """
    Record every persistent stage as current.
    """

    fingerprints = create_required_fingerprints(
        build_plan,
    )

    for stage in build_plan.stages:
        if not stage.products:
            continue

        _record_stage_current(
            build_plan,
            stage,
            fingerprints[stage.name],
        )

    return fingerprints


def _descendant_stage_names(
    build_plan: BuildPlan,
    stage_name: str,
) -> tuple[str, ...]:
    """
    Return realized stages transitively depending on stage_name.
    """

    descendants: list[str] = []
    reached = {
        stage_name,
    }

    for stage in build_plan.stages:
        if any(dependency in reached for dependency in stage.spec.dependencies):
            reached.add(
                stage.name,
            )

            descendants.append(
                stage.name,
            )

    return tuple(
        descendants,
    )


def _persistent_stage_names(
    build_plan: BuildPlan,
) -> tuple[str, ...]:
    """
    Return realized stages declaring persistent products.
    """

    return tuple(stage.name for stage in build_plan.stages if stage.products)


# =========================================================
# Empty persistent workspace
# =========================================================


def test_incremental_build_executes_all_stages_when_products_are_absent(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    An empty persistent workspace requires execution of every stage.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    _materialize_external_inputs(
        build_plan,
    )

    executed: list[str] = []

    def execute(
        stage: PlannedStage,
    ) -> None:
        executed.append(
            stage.name,
        )

        _materialize_stage_products(
            stage,
        )

    execute_incremental_build(
        build_plan,
        execute_stage=execute,
    )

    assert tuple(
        executed,
    ) == tuple(stage.name for stage in build_plan.stages)


def test_incremental_build_preserves_stage_order(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Required stages execute in realized build-plan order.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    _materialize_external_inputs(
        build_plan,
    )

    executed: list[str] = []

    def execute(
        stage: PlannedStage,
    ) -> None:
        executed.append(
            stage.name,
        )

        _materialize_stage_products(
            stage,
        )

    execute_incremental_build(
        build_plan,
        execute_stage=execute,
    )

    assert tuple(
        executed,
    ) == tuple(stage.name for stage in build_plan.stages)


# =========================================================
# Fully current realization
# =========================================================


def test_incremental_build_skips_fully_current_realization(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    A completely current realization executes no stages.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    _materialize_external_inputs(
        build_plan,
    )

    _record_all_stages_current(
        build_plan,
    )

    executed: list[str] = []

    def execute(
        stage: PlannedStage,
    ) -> None:
        executed.append(
            stage.name,
        )

    execute_incremental_build(
        build_plan,
        execute_stage=execute,
    )

    assert executed == []


# =========================================================
# Completion persistence
# =========================================================


def test_incremental_build_records_completion_for_executed_stages(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Successful execution records completion for persistent stages.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    _materialize_external_inputs(
        build_plan,
    )

    def execute(
        stage: PlannedStage,
    ) -> None:
        _materialize_stage_products(
            stage,
        )

    execute_incremental_build(
        build_plan,
        execute_stage=execute,
    )

    for stage in build_plan.stages:
        if not stage.products:
            continue

        completion = read_stage_completion(
            _stage_working_dir(
                stage,
            )
        )

        assert completion is not None
        assert completion.stage_name == stage.name
        assert completion.products == tuple(product.name for product in stage.products)


def test_incremental_build_records_required_fingerprint(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Completion provenance records the fingerprint required by the build.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    _materialize_external_inputs(
        build_plan,
    )

    required = create_required_fingerprints(
        build_plan,
    )

    def execute(
        stage: PlannedStage,
    ) -> None:
        _materialize_stage_products(
            stage,
        )

    execute_incremental_build(
        build_plan,
        execute_stage=execute,
    )

    for stage in build_plan.stages:
        if not stage.products:
            continue

        completion = read_stage_completion(
            _stage_working_dir(
                stage,
            )
        )

        assert completion is not None
        assert completion.fingerprint == required[stage.name]


# =========================================================
# Selective rebuilding
# =========================================================


def test_missing_product_reexecutes_its_stage(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    A missing persistent product causes its producing stage to execute.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    _materialize_external_inputs(
        build_plan,
    )

    _record_all_stages_current(
        build_plan,
    )

    affected_stage = next(stage for stage in build_plan.stages if stage.products)

    affected_stage.products[0].path.unlink()

    executed: list[str] = []

    def execute(
        stage: PlannedStage,
    ) -> None:
        executed.append(
            stage.name,
        )

        _materialize_stage_products(
            stage,
        )

    execute_incremental_build(
        build_plan,
        execute_stage=execute,
    )

    assert affected_stage.name in executed


def test_changed_external_input_reexecutes_invalidated_chain(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Changed external input executes its consumer and dependent descendants.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    _materialize_external_inputs(
        build_plan,
        content=b"original-input",
    )

    _record_all_stages_current(
        build_plan,
    )

    consuming_stage = next(stage for stage in build_plan.stages if stage.inputs)

    expected = (
        consuming_stage.name,
        *_descendant_stage_names(
            build_plan,
            consuming_stage.name,
        ),
    )

    for planned_input in consuming_stage.inputs:
        planned_input.path.write_bytes(
            b"changed-input",
        )

    executed: list[str] = []

    def execute(
        stage: PlannedStage,
    ) -> None:
        executed.append(
            stage.name,
        )

        _materialize_stage_products(
            stage,
        )

    execute_incremental_build(
        build_plan,
        execute_stage=execute,
    )

    assert (
        tuple(
            executed,
        )
        == expected
    )


# =========================================================
# Failure behavior
# =========================================================


def test_failed_stage_does_not_record_completion(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Completion metadata is written only after successful stage execution.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    _materialize_external_inputs(
        build_plan,
    )

    failing_stage = next(stage for stage in build_plan.stages if stage.products)

    class ExpectedError(Exception):
        """
        Expected execution failure.
        """

    def execute(
        stage: PlannedStage,
    ) -> None:
        if stage.name == failing_stage.name:
            raise ExpectedError

        _materialize_stage_products(
            stage,
        )

    with pytest.raises(
        ExpectedError,
    ):
        execute_incremental_build(
            build_plan,
            execute_stage=execute,
        )

    assert (
        read_stage_completion(
            _stage_working_dir(
                failing_stage,
            )
        )
        is None
    )


def test_failed_stage_stops_later_execution(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Execution stops when a required stage fails.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    _materialize_external_inputs(
        build_plan,
    )

    failing_stage = next(stage for stage in build_plan.stages if stage.products)

    executed: list[str] = []

    class ExpectedError(Exception):
        """
        Expected execution failure.
        """

    def execute(
        stage: PlannedStage,
    ) -> None:
        executed.append(
            stage.name,
        )

        if stage.name == failing_stage.name:
            raise ExpectedError

        _materialize_stage_products(
            stage,
        )

    with pytest.raises(
        ExpectedError,
    ):
        execute_incremental_build(
            build_plan,
            execute_stage=execute,
        )

    failing_index = tuple(stage.name for stage in build_plan.stages).index(
        failing_stage.name,
    )

    assert tuple(
        executed,
    ) == tuple(stage.name for stage in build_plan.stages[: failing_index + 1])
