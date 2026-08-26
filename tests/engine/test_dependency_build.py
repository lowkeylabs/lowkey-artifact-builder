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
    DependencyCycleError,
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
    ProductRef,
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
# Transitive dependency construction
# =========================================================


def _transitive_producer_build_plan(
    tmp_path: Path,
    *,
    resolver,
) -> BuildPlan:
    """
    Construct producer B requiring one product from upstream producer C.
    """

    dependency = ProductDependencySpec(
        model="upstream",
        stage="vector",
        product="geometry",
    )

    binding = ProductDependencyBinding(
        dependency=dependency,
        artifact="upstream-artifact",
        realization="default",
    )

    planned_dependency = PlannedProductDependency(
        binding=binding,
        path=(
            tmp_path
            / "artifacts"
            / "upstream-artifact"
            / "upstream"
            / "default"
            / "30-vector"
            / "geometry.dat"
        ),
    )

    stage_spec = StageSpec(
        id=20,
        name="transform",
        product_dependencies=(dependency,),
        products=(
            ProductSpec(
                name="geometry",
                path="geometry.dat",
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
            stages=(stage_spec,),
        ),
        realization_name="default",
        resolver=resolver,
        project_root=tmp_path,
        artifact_dir=(tmp_path / "artifacts" / "producer-artifact"),
        stages=(stage,),
        product_dependencies=(dependency,),
        product_dependency_bindings=(binding,),
        planned_product_dependencies=(planned_dependency,),
    )


def _upstream_build_plan(
    tmp_path: Path,
    *,
    resolver,
) -> BuildPlan:
    """
    Construct targeted upstream producer C.

    The complete model contains downstream manufacturing stages, but this
    realized BuildPlan intentionally ends at the required vector product.
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

    raster_spec = StageSpec(
        id=20,
        name="raster",
        dependencies=("prepare",),
        products=(
            ProductSpec(
                name="pixels",
                path="pixels.dat",
            ),
        ),
    )

    vector_spec = StageSpec(
        id=30,
        name="vector",
        dependencies=("raster",),
        products=(
            ProductSpec(
                name="geometry",
                path="geometry.dat",
            ),
        ),
    )

    extrude_spec = StageSpec(
        id=40,
        name="extrude",
        dependencies=("vector",),
        products=(
            ProductSpec(
                name="solid",
                path="solid.dat",
            ),
        ),
    )

    package_spec = StageSpec(
        id=50,
        name="package",
        dependencies=("extrude",),
        products=(
            ProductSpec(
                name="artifact",
                path="artifact.dat",
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
                    / "upstream-artifact"
                    / "upstream"
                    / "default"
                    / "10-prepare"
                    / "prepared.dat"
                ),
            ),
        ),
    )

    raster = PlannedStage(
        spec=raster_spec,
        products=(
            PlannedProduct(
                spec=raster_spec.products[0],
                path=(
                    tmp_path
                    / "artifacts"
                    / "upstream-artifact"
                    / "upstream"
                    / "default"
                    / "20-raster"
                    / "pixels.dat"
                ),
            ),
        ),
    )

    vector = PlannedStage(
        spec=vector_spec,
        products=(
            PlannedProduct(
                spec=vector_spec.products[0],
                path=(
                    tmp_path
                    / "artifacts"
                    / "upstream-artifact"
                    / "upstream"
                    / "default"
                    / "30-vector"
                    / "geometry.dat"
                ),
            ),
        ),
    )

    return BuildPlan(
        artifact_id="upstream-artifact",
        model=ModelSpec(
            name="upstream",
            title="Upstream",
            stages=(
                prepare_spec,
                raster_spec,
                vector_spec,
                extrude_spec,
                package_spec,
            ),
        ),
        realization_name="default",
        resolver=resolver,
        project_root=tmp_path,
        artifact_dir=(tmp_path / "artifacts" / "upstream-artifact"),
        stages=(
            prepare,
            raster,
            vector,
        ),
        targets=(
            ProductRef(
                artifact="upstream-artifact",
                model="upstream",
                realization="default",
                stage="vector",
                product="geometry",
            ),
        ),
    )


def _cyclic_build_plan(
    tmp_path: Path,
    *,
    artifact_id: str,
    model_name: str,
    dependency_artifact: str,
    dependency_model: str,
    resolver,
) -> BuildPlan:
    """
    Construct one single-stage artifact participating in a dependency cycle.
    """

    dependency = ProductDependencySpec(
        model=dependency_model,
        stage="build",
        product="product",
    )

    binding = ProductDependencyBinding(
        dependency=dependency,
        artifact=dependency_artifact,
        realization="default",
    )

    planned_dependency = PlannedProductDependency(
        binding=binding,
        path=(
            tmp_path
            / "artifacts"
            / dependency_artifact
            / dependency_model
            / "default"
            / "10-build"
            / "product.dat"
        ),
    )

    stage_spec = StageSpec(
        id=10,
        name="build",
        product_dependencies=(dependency,),
        products=(
            ProductSpec(
                name="product",
                path="product.dat",
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
                    / artifact_id
                    / model_name
                    / "default"
                    / "10-build"
                    / "product.dat"
                ),
            ),
        ),
    )

    return BuildPlan(
        artifact_id=artifact_id,
        model=ModelSpec(
            name=model_name,
            title=model_name.title(),
            stages=(stage_spec,),
        ),
        realization_name="default",
        resolver=resolver,
        project_root=tmp_path,
        artifact_dir=(tmp_path / "artifacts" / artifact_id),
        stages=(stage,),
        product_dependencies=(dependency,),
        product_dependency_bindings=(binding,),
        planned_product_dependencies=(planned_dependency,),
    )


def _record_plan_current(
    build_plan: BuildPlan,
) -> None:
    """
    Materialize every realized stage with matching completion metadata.
    """

    fingerprints = create_required_fingerprints(
        build_plan,
    )

    for stage in build_plan.stages:
        _record_stage_current(
            build_plan,
            stage,
            fingerprints[stage.name],
        )


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
        if build_plan is consumer_plan:
            assert execution_plan.required_product_dependencies

            return (producer_plan,)

        if build_plan is producer_plan:
            assert execution_plan.required_product_dependencies == ()

            return ()

        raise AssertionError(f"Unexpected BuildPlan {build_plan.artifact_id!r}")

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

        if build_plan is producer_plan:
            return ExecutionPlan(
                artifact_id=producer_plan.artifact_id,
                model_name=producer_plan.model_name,
                realization=producer_plan.realization_name,
                stages=(),
            )

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
        if build_plan is producer_plan:
            return ()

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
        if build_plan is consumer_plan:
            return (producer_plan,)

        if build_plan is producer_plan:
            return ()

        raise AssertionError(f"Unexpected BuildPlan {build_plan.artifact_id!r}")

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


# =========================================================
# Transitive dependency orchestration
# =========================================================


def test_dependency_build_executes_transitive_dependencies_in_order(
    consumer_plan: BuildPlan,
    tmp_path: Path,
    test_resolver,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    A -> B -> C executes C before B before A.
    """

    producer_plan = _transitive_producer_build_plan(
        tmp_path,
        resolver=test_resolver,
    )

    upstream_plan = _upstream_build_plan(
        tmp_path,
        resolver=test_resolver,
    )

    execution_order: list[str] = []

    real_execute_dependency_build = dependency_build_module.execute_dependency_build

    def create_producer_plans(
        build_plan: BuildPlan,
        execution_plan: ExecutionPlan,
    ) -> tuple[BuildPlan, ...]:
        if build_plan is consumer_plan:
            assert execution_plan.required_product_dependencies

            return (producer_plan,)

        if build_plan is producer_plan:
            assert execution_plan.required_product_dependencies

            return (upstream_plan,)

        return ()

    def execute_artifact(
        build_plan: BuildPlan,
        **kwargs,
    ) -> ExecutionPlan:
        execution_order.append(
            build_plan.artifact_id,
        )

        _record_plan_current(
            build_plan,
        )

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

    real_execute_dependency_build(
        consumer_plan,
    )

    assert execution_order == [
        "upstream-artifact",
        "producer-artifact",
        "consumer-artifact",
    ]


def test_dependency_build_reuses_current_transitive_dependency(
    consumer_plan: BuildPlan,
    tmp_path: Path,
    test_resolver,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    A current C product is reused while required B and A work still executes.
    """

    producer_plan = _transitive_producer_build_plan(
        tmp_path,
        resolver=test_resolver,
    )

    upstream_plan = _upstream_build_plan(
        tmp_path,
        resolver=test_resolver,
    )

    _record_plan_current(
        upstream_plan,
    )

    upstream_fingerprints = create_required_fingerprints(
        upstream_plan,
    )

    required_upstream_fingerprint = upstream_fingerprints["vector"]

    execution_order: list[str] = []

    def create_producer_plans(
        build_plan: BuildPlan,
        execution_plan: ExecutionPlan,
    ) -> tuple[BuildPlan, ...]:
        if build_plan is consumer_plan:
            return (producer_plan,)

        if build_plan is producer_plan:
            assert execution_plan.required_product_dependencies == ()

            return ()

        return ()

    def supplied_fingerprint(
        dependency: PlannedProductDependency,
    ) -> ProductFingerprint | None:
        if dependency.product_ref.artifact == "upstream-artifact":
            return required_upstream_fingerprint

        return None

    def execute_artifact(
        build_plan: BuildPlan,
        **kwargs,
    ) -> ExecutionPlan:
        execution_order.append(
            build_plan.artifact_id,
        )

        _record_plan_current(
            build_plan,
        )

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

    execute_dependency_build(
        consumer_plan,
        product_dependency_fingerprint=supplied_fingerprint,
    )

    assert execution_order == [
        "producer-artifact",
        "consumer-artifact",
    ]


def test_dependency_build_targets_only_required_transitive_product(
    consumer_plan: BuildPlan,
    tmp_path: Path,
    test_resolver,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Transitive execution stops at the specifically required upstream product.
    """

    producer_plan = _transitive_producer_build_plan(
        tmp_path,
        resolver=test_resolver,
    )

    upstream_plan = _upstream_build_plan(
        tmp_path,
        resolver=test_resolver,
    )

    executed_stages: list[
        tuple[
            str,
            str,
        ]
    ] = []

    def create_producer_plans(
        build_plan: BuildPlan,
        execution_plan: ExecutionPlan,
    ) -> tuple[BuildPlan, ...]:
        if build_plan is consumer_plan:
            return (producer_plan,)

        if build_plan is producer_plan:
            return (upstream_plan,)

        return ()

    def execute_artifact(
        build_plan: BuildPlan,
        **kwargs,
    ) -> ExecutionPlan:
        for stage in build_plan.stages:
            executed_stages.append(
                (
                    build_plan.artifact_id,
                    stage.name,
                )
            )

        _record_plan_current(
            build_plan,
        )

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

    execute_dependency_build(
        consumer_plan,
    )

    upstream_stages = [
        stage_name
        for artifact_id, stage_name in executed_stages
        if artifact_id == "upstream-artifact"
    ]

    assert upstream_stages == [
        "prepare",
        "raster",
        "vector",
    ]

    assert "extrude" not in upstream_stages
    assert "package" not in upstream_stages


def test_dependency_build_propagates_transitive_producer_failure(
    consumer_plan: BuildPlan,
    tmp_path: Path,
    test_resolver,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Failure in C prevents execution of both dependent B and consumer A.
    """

    producer_plan = _transitive_producer_build_plan(
        tmp_path,
        resolver=test_resolver,
    )

    upstream_plan = _upstream_build_plan(
        tmp_path,
        resolver=test_resolver,
    )

    executed: list[str] = []

    class ExpectedUpstreamError(Exception):
        """
        Expected transitive producer failure.
        """

    def create_producer_plans(
        build_plan: BuildPlan,
        execution_plan: ExecutionPlan,
    ) -> tuple[BuildPlan, ...]:
        if build_plan is consumer_plan:
            return (producer_plan,)

        if build_plan is producer_plan:
            return (upstream_plan,)

        return ()

    def execute_artifact(
        build_plan: BuildPlan,
        **kwargs,
    ) -> ExecutionPlan:
        executed.append(
            build_plan.artifact_id,
        )

        if build_plan is upstream_plan:
            raise ExpectedUpstreamError

        _record_plan_current(
            build_plan,
        )

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
        ExpectedUpstreamError,
    ):
        execute_dependency_build(
            consumer_plan,
        )

    assert executed == [
        "upstream-artifact",
    ]


# =========================================================
# Dependency-cycle detection
# =========================================================


def test_dependency_build_rejects_direct_dependency_cycle(
    tmp_path: Path,
    test_resolver,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    A -> B -> A fails explicitly rather than recursing indefinitely.
    """

    plan_a = _cyclic_build_plan(
        tmp_path,
        artifact_id="artifact-a",
        model_name="model-a",
        dependency_artifact="artifact-b",
        dependency_model="model-b",
        resolver=test_resolver,
    )

    plan_b = _cyclic_build_plan(
        tmp_path,
        artifact_id="artifact-b",
        model_name="model-b",
        dependency_artifact="artifact-a",
        dependency_model="model-a",
        resolver=test_resolver,
    )

    def create_producer_plans(
        build_plan: BuildPlan,
        execution_plan: ExecutionPlan,
    ) -> tuple[BuildPlan, ...]:
        assert execution_plan.required_product_dependencies

        if build_plan is plan_a:
            return (plan_b,)

        if build_plan is plan_b:
            return (plan_a,)

        raise AssertionError(f"Unexpected BuildPlan {build_plan.artifact_id!r}")

    monkeypatch.setattr(
        dependency_build_module,
        "create_required_product_dependency_build_plans",
        create_producer_plans,
    )

    with pytest.raises(
        DependencyCycleError,
    ):
        execute_dependency_build(
            plan_a,
        )


def test_dependency_build_rejects_long_dependency_cycle(
    tmp_path: Path,
    test_resolver,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    A -> B -> C -> A fails explicitly.
    """

    plan_a = _cyclic_build_plan(
        tmp_path,
        artifact_id="artifact-a",
        model_name="model-a",
        dependency_artifact="artifact-b",
        dependency_model="model-b",
        resolver=test_resolver,
    )

    plan_b = _cyclic_build_plan(
        tmp_path,
        artifact_id="artifact-b",
        model_name="model-b",
        dependency_artifact="artifact-c",
        dependency_model="model-c",
        resolver=test_resolver,
    )

    plan_c = _cyclic_build_plan(
        tmp_path,
        artifact_id="artifact-c",
        model_name="model-c",
        dependency_artifact="artifact-a",
        dependency_model="model-a",
        resolver=test_resolver,
    )

    def create_producer_plans(
        build_plan: BuildPlan,
        execution_plan: ExecutionPlan,
    ) -> tuple[BuildPlan, ...]:
        assert execution_plan.required_product_dependencies

        if build_plan is plan_a:
            return (plan_b,)

        if build_plan is plan_b:
            return (plan_c,)

        if build_plan is plan_c:
            return (plan_a,)

        raise AssertionError(f"Unexpected BuildPlan {build_plan.artifact_id!r}")

    monkeypatch.setattr(
        dependency_build_module,
        "create_required_product_dependency_build_plans",
        create_producer_plans,
    )

    with pytest.raises(
        DependencyCycleError,
    ):
        execute_dependency_build(
            plan_a,
        )


def test_dependency_cycle_error_identifies_dependency_path(
    tmp_path: Path,
    test_resolver,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Cycle failure identifies the artifact realizations in the cycle.
    """

    plan_a = _cyclic_build_plan(
        tmp_path,
        artifact_id="artifact-a",
        model_name="model-a",
        dependency_artifact="artifact-b",
        dependency_model="model-b",
        resolver=test_resolver,
    )

    plan_b = _cyclic_build_plan(
        tmp_path,
        artifact_id="artifact-b",
        model_name="model-b",
        dependency_artifact="artifact-c",
        dependency_model="model-c",
        resolver=test_resolver,
    )

    plan_c = _cyclic_build_plan(
        tmp_path,
        artifact_id="artifact-c",
        model_name="model-c",
        dependency_artifact="artifact-a",
        dependency_model="model-a",
        resolver=test_resolver,
    )

    def create_producer_plans(
        build_plan: BuildPlan,
        execution_plan: ExecutionPlan,
    ) -> tuple[BuildPlan, ...]:
        if build_plan is plan_a:
            return (plan_b,)

        if build_plan is plan_b:
            return (plan_c,)

        if build_plan is plan_c:
            return (plan_a,)

        raise AssertionError(f"Unexpected BuildPlan {build_plan.artifact_id!r}")

    monkeypatch.setattr(
        dependency_build_module,
        "create_required_product_dependency_build_plans",
        create_producer_plans,
    )

    with pytest.raises(
        DependencyCycleError,
    ) as exc_info:
        execute_dependency_build(
            plan_a,
        )

    message = str(
        exc_info.value,
    )

    assert "artifact-a/model-a/default" in message
    assert "artifact-b/model-b/default" in message
    assert "artifact-c/model-c/default" in message

    assert "artifact-a/model-a/default" in message[message.find("artifact-c/model-c/default") :]
