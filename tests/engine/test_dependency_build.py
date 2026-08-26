"""
Tests for cross-artifact dependency build orchestration.

Dependency build orchestration connects persistent-state-aware consumer
planning, targeted producer planning, producer execution, and subsequent
consumer execution.

A consumer whose required cross-artifact producer product is absent or
stale cannot execute immediately. Required producer work must first be
planned and executed. The consumer must then be replanned against the
newly reusable producer product before its own stages may execute.

Producer products already reusable for their required build-context
fingerprints do not create producer execution.

Producer failure propagates and prevents dependent consumer execution.

These tests exercise one level of cross-artifact dependency orchestration.
They intentionally do not exercise recursive producer dependencies or
dependency-cycle detection.
"""
# File: tests/engine/test_dependency_build.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

import lowkey_artifact_builder.engine.dependency_build as dependency_build_module
from lowkey_artifact_builder.engine import (
    BuildPlan,
    ExecutionPlan,
    PlannedProduct,
    PlannedProductDependency,
    PlannedProductDependencyExecution,
    PlannedStage,
    ProductFingerprint,
    ProductState,
    StageCompletion,
    create_required_fingerprints,
    execute_dependency_build,
    write_stage_completion,
)
from lowkey_artifact_builder.model import (
    ModelSpec,
    ProductDependencyBinding,
    ProductDependencySpec,
    ProductSpec,
    StageSpec,
)

# =========================================================
# Types
# =========================================================


type StageExecutionObserver = Callable[
    [
        BuildPlan,
    ],
    None,
]


# =========================================================
# Consumer-plan construction
# =========================================================


def _consumer_build_plan(
    tmp_path: Path,
    *,
    resolver,
) -> BuildPlan:
    """
    Construct a consumer requiring one cross-artifact producer product.
    """

    dependency = ProductDependencySpec(
        model="producer",
        stage="transform",
        product="geometry",
    )

    binding = ProductDependencyBinding(
        dependency=dependency,
        artifact="producer-artifact",
        realization="default",
    )

    dependency_path = (
        tmp_path
        / "artifacts"
        / "producer-artifact"
        / "producer"
        / "default"
        / "20-transform"
        / "geometry.dat"
    )

    planned_dependency = PlannedProductDependency(
        binding=binding,
        path=dependency_path,
    )

    stage_spec = StageSpec(
        id=10,
        name="consume",
        product_dependencies=(dependency,),
        products=(
            ProductSpec(
                name="artifact",
                path="artifact.dat",
            ),
        ),
    )

    stage = PlannedStage(
        spec=stage_spec,
        products=(
            PlannedProduct(
                spec=stage_spec.products[0],
                path=(
                    tmp_path
                    / "artifacts"
                    / "consumer-artifact"
                    / "consumer"
                    / "default"
                    / "10-consume"
                    / "artifact.dat"
                ),
            ),
        ),
    )

    return BuildPlan(
        artifact_id="consumer-artifact",
        model=ModelSpec(
            name="consumer",
            title="Consumer",
            stages=(stage_spec,),
        ),
        realization_name="default",
        resolver=resolver,
        project_root=tmp_path,
        artifact_dir=(tmp_path / "artifacts" / "consumer-artifact"),
        stages=(stage,),
        product_dependencies=(dependency,),
        product_dependency_bindings=(binding,),
        planned_product_dependencies=(planned_dependency,),
    )


# =========================================================
# Producer-plan construction
# =========================================================


def _producer_build_plan(
    tmp_path: Path,
    *,
    resolver,
) -> BuildPlan:
    """
    Construct the targeted producer plan used by orchestration tests.
    """

    prepare_spec = StageSpec(
        id=10,
        name="prepare",
        products=(
            ProductSpec(
                name="prepared",
                path="prepared.dat",
            ),
        ),
    )

    transform_spec = StageSpec(
        id=20,
        name="transform",
        dependencies=("prepare",),
        products=(
            ProductSpec(
                name="geometry",
                path="geometry.dat",
            ),
        ),
    )

    prepare = PlannedStage(
        spec=prepare_spec,
        products=(
            PlannedProduct(
                spec=prepare_spec.products[0],
                path=(
                    tmp_path
                    / "artifacts"
                    / "producer-artifact"
                    / "producer"
                    / "default"
                    / "10-prepare"
                    / "prepared.dat"
                ),
            ),
        ),
    )

    transform = PlannedStage(
        spec=transform_spec,
        products=(
            PlannedProduct(
                spec=transform_spec.products[0],
                path=(
                    tmp_path
                    / "artifacts"
                    / "producer-artifact"
                    / "producer"
                    / "default"
                    / "20-transform"
                    / "geometry.dat"
                ),
            ),
        ),
    )

    return BuildPlan(
        artifact_id="producer-artifact",
        model=ModelSpec(
            name="producer",
            title="Producer",
            stages=(
                prepare_spec,
                transform_spec,
            ),
        ),
        realization_name="default",
        resolver=resolver,
        project_root=tmp_path,
        artifact_dir=(tmp_path / "artifacts" / "producer-artifact"),
        stages=(
            prepare,
            transform,
        ),
    )


# =========================================================
# Persistent-product helpers
# =========================================================


def _stage_working_dir(
    stage: PlannedStage,
) -> Path:
    """
    Return the common persistent working directory for one stage.
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
    *,
    content: bytes | None = None,
) -> None:
    """
    Materialize every persistent product of one stage.
    """

    product_content = content if content is not None else f"{stage.name}-product".encode()

    for product in stage.products:
        product.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        product.path.write_bytes(
            product_content,
        )


def _record_stage_current(
    build_plan: BuildPlan,
    stage: PlannedStage,
    fingerprint: ProductFingerprint,
) -> None:
    """
    Materialize one stage and record matching completion metadata.
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


def _record_producer_current(
    producer_plan: BuildPlan,
) -> ProductFingerprint:
    """
    Record every realized producer stage as current.

    Return the required fingerprint of the producer target stage.
    """

    fingerprints = create_required_fingerprints(
        producer_plan,
    )

    for stage in producer_plan.stages:
        _record_stage_current(
            producer_plan,
            stage,
            fingerprints[stage.name],
        )

    return fingerprints[producer_plan.stages[-1].name]


# =========================================================
# Test fixtures
# =========================================================


@pytest.fixture
def consumer_plan(
    tmp_path: Path,
    test_resolver,
) -> BuildPlan:
    """
    Return the consumer BuildPlan used by dependency-build tests.
    """

    return _consumer_build_plan(
        tmp_path,
        resolver=test_resolver,
    )


@pytest.fixture
def producer_plan(
    tmp_path: Path,
    test_resolver,
) -> BuildPlan:
    """
    Return the targeted producer BuildPlan used by dependency-build tests.
    """

    return _producer_build_plan(
        tmp_path,
        resolver=test_resolver,
    )


# =========================================================
# Producer-before-consumer execution
# =========================================================


def test_dependency_build_executes_required_producer_before_consumer(
    consumer_plan: BuildPlan,
    producer_plan: BuildPlan,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    An absent producer product is built before its dependent consumer.
    """

    execution_order: list[
        tuple[
            str,
            str,
        ]
    ] = []

    producer_fingerprints = create_required_fingerprints(
        producer_plan,
    )

    def create_producer_plans(
        build_plan: BuildPlan,
        execution_plan: ExecutionPlan,
    ) -> tuple[BuildPlan, ...]:
        assert build_plan is consumer_plan
        assert execution_plan.required_product_dependencies

        return (producer_plan,)

    def execute_artifact(
        build_plan: BuildPlan,
        **kwargs,
    ) -> ExecutionPlan:
        if build_plan is producer_plan:
            for stage in producer_plan.stages:
                execution_order.append(
                    (
                        producer_plan.artifact_id,
                        stage.name,
                    )
                )

                _record_stage_current(
                    producer_plan,
                    stage,
                    producer_fingerprints[stage.name],
                )

            return ExecutionPlan(
                artifact_id=producer_plan.artifact_id,
                model_name=producer_plan.model_name,
                realization=producer_plan.realization_name,
                stages=(),
            )

        if build_plan is consumer_plan:
            execution_order.append(
                (
                    consumer_plan.artifact_id,
                    "consume",
                )
            )

            return ExecutionPlan(
                artifact_id=consumer_plan.artifact_id,
                model_name=consumer_plan.model_name,
                realization=consumer_plan.realization_name,
                stages=(),
            )

        raise AssertionError(f"Unexpected BuildPlan {build_plan.artifact_id!r}")

    monkeypatch.setattr(
        dependency_build_module,
        "create_required_product_dependency_build_plans",
        create_producer_plans,
    )

    monkeypatch.setattr(
        dependency_build_module,
        "execute_incremental_artifact_build",
        execute_artifact,
    )

    execute_dependency_build(
        consumer_plan,
    )

    assert execution_order == [
        (
            "producer-artifact",
            "prepare",
        ),
        (
            "producer-artifact",
            "transform",
        ),
        (
            "consumer-artifact",
            "consume",
        ),
    ]


# =========================================================
# Reusable producer
# =========================================================


def test_dependency_build_does_not_execute_current_producer(
    consumer_plan: BuildPlan,
    producer_plan: BuildPlan,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    A reusable producer product is not rebuilt before consumer execution.
    """

    required_producer_fingerprint = _record_producer_current(
        producer_plan,
    )

    producer_execution_count = 0
    consumer_execution_count = 0

    def execute_artifact(
        build_plan: BuildPlan,
        **kwargs,
    ) -> ExecutionPlan:
        nonlocal producer_execution_count
        nonlocal consumer_execution_count

        if build_plan is producer_plan:
            producer_execution_count += 1

        if build_plan is consumer_plan:
            consumer_execution_count += 1

        return ExecutionPlan(
            artifact_id=build_plan.artifact_id,
            model_name=build_plan.model_name,
            realization=build_plan.realization_name,
            stages=(),
        )

    def create_producer_plans(
        build_plan: BuildPlan,
        execution_plan: ExecutionPlan,
    ) -> tuple[BuildPlan, ...]:
        assert build_plan is consumer_plan

        assert execution_plan.required_product_dependencies == ()

        return ()

    monkeypatch.setattr(
        dependency_build_module,
        "create_required_product_dependency_build_plans",
        create_producer_plans,
    )

    monkeypatch.setattr(
        dependency_build_module,
        "execute_incremental_artifact_build",
        execute_artifact,
    )

    execute_dependency_build(
        consumer_plan,
        product_dependency_fingerprint=(lambda dependency: required_producer_fingerprint),
    )

    assert producer_execution_count == 0
    assert consumer_execution_count == 1


# =========================================================
# Consumer replanning
# =========================================================


def test_dependency_build_replans_consumer_after_producer_execution(
    consumer_plan: BuildPlan,
    producer_plan: BuildPlan,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Consumer execution is replanned after producer completion.
    """

    consumer_planning_count = 0
    producer_execution_count = 0
    consumer_execution_count = 0

    producer_available = False

    def plan_consumer(
        build_plan: BuildPlan,
        **kwargs,
    ) -> ExecutionPlan:
        nonlocal consumer_planning_count

        assert build_plan is consumer_plan

        consumer_planning_count += 1

        if not producer_available:
            return ExecutionPlan(
                artifact_id=consumer_plan.artifact_id,
                model_name=consumer_plan.model_name,
                realization=consumer_plan.realization_name,
                stages=(),
                product_dependencies=(
                    PlannedProductDependencyExecution(
                        product_ref=(consumer_plan.planned_product_dependencies[0].product_ref),
                        state=ProductState.ABSENT,
                    ),
                ),
            )

        return ExecutionPlan(
            artifact_id=consumer_plan.artifact_id,
            model_name=consumer_plan.model_name,
            realization=consumer_plan.realization_name,
            stages=(),
            product_dependencies=(
                PlannedProductDependencyExecution(
                    product_ref=(consumer_plan.planned_product_dependencies[0].product_ref),
                    state=ProductState.CURRENT,
                ),
            ),
        )

    def create_producer_plans(
        build_plan: BuildPlan,
        execution_plan: ExecutionPlan,
    ) -> tuple[BuildPlan, ...]:
        assert build_plan is consumer_plan

        if execution_plan.required_product_dependencies:
            return (producer_plan,)

        return ()

    def execute_artifact(
        build_plan: BuildPlan,
        **kwargs,
    ) -> ExecutionPlan:
        nonlocal producer_execution_count
        nonlocal consumer_execution_count
        nonlocal producer_available

        if build_plan is producer_plan:
            producer_execution_count += 1

            for stage in producer_plan.stages:
                _materialize_stage_products(
                    stage,
                )

            producer_available = True

        elif build_plan is consumer_plan:
            consumer_execution_count += 1

        else:
            raise AssertionError(f"Unexpected BuildPlan {build_plan.artifact_id!r}")

        return ExecutionPlan(
            artifact_id=build_plan.artifact_id,
            model_name=build_plan.model_name,
            realization=build_plan.realization_name,
            stages=(),
        )

    monkeypatch.setattr(
        dependency_build_module,
        "plan_incremental_execution",
        plan_consumer,
    )

    monkeypatch.setattr(
        dependency_build_module,
        "create_required_product_dependency_build_plans",
        create_producer_plans,
    )

    monkeypatch.setattr(
        dependency_build_module,
        "execute_incremental_artifact_build",
        execute_artifact,
    )

    execute_dependency_build(
        consumer_plan,
    )

    assert consumer_planning_count == 2
    assert producer_execution_count == 1
    assert consumer_execution_count == 1


# =========================================================
# Producer failure
# =========================================================


def test_dependency_build_stops_when_producer_execution_fails(
    consumer_plan: BuildPlan,
    producer_plan: BuildPlan,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Producer failure propagates and the dependent consumer never executes.
    """

    consumer_executed = False

    class ExpectedProducerError(Exception):
        """
        Expected producer execution failure.
        """

    def create_producer_plans(
        build_plan: BuildPlan,
        execution_plan: ExecutionPlan,
    ) -> tuple[BuildPlan, ...]:
        assert build_plan is consumer_plan

        return (producer_plan,)

    def execute_artifact(
        build_plan: BuildPlan,
        **kwargs,
    ) -> ExecutionPlan:
        nonlocal consumer_executed

        if build_plan is producer_plan:
            raise ExpectedProducerError

        if build_plan is consumer_plan:
            consumer_executed = True

        return ExecutionPlan(
            artifact_id=build_plan.artifact_id,
            model_name=build_plan.model_name,
            realization=build_plan.realization_name,
            stages=(),
        )

    monkeypatch.setattr(
        dependency_build_module,
        "create_required_product_dependency_build_plans",
        create_producer_plans,
    )

    monkeypatch.setattr(
        dependency_build_module,
        "execute_incremental_artifact_build",
        execute_artifact,
    )

    with pytest.raises(
        ExpectedProducerError,
    ):
        execute_dependency_build(
            consumer_plan,
        )

    assert consumer_executed is False
