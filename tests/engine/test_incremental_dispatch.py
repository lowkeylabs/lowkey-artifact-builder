"""
Tests for incremental execution through engine stage dispatch.

Incremental artifact execution connects persistent-state-aware build
selection to the established planned StageContext and execute_stage
boundaries.

Only stages requiring execution are dispatched. Each dispatched stage
receives a StageContext adapted directly from the same BuildPlan and
PlannedStage used for incremental planning.

Cross-artifact product dependencies participate in incremental execution
through their required producer-product fingerprints. Current producer
products permit consumer execution, while absent or stale producer
products prevent consumer dispatch until the producer requirement has
been satisfied.

These tests exercise orchestration between incremental execution and
engine stage dispatch. They do not execute model-specific stage
implementations or orchestrate producer builds.
"""
# File: tests/engine/test_incremental_dispatch.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

import lowkey_artifact_builder.engine.incremental as incremental_module
from lowkey_artifact_builder.engine import (
    BuildPlan,
    PlannedProduct,
    PlannedProductDependency,
    PlannedStage,
    ProductFingerprint,
    ProductState,
    StageCompletion,
    StageContext,
    create_required_fingerprints,
    execute_incremental_artifact_build,
    write_stage_completion,
)
from lowkey_artifact_builder.model import (
    ModelSpec,
    ProductDependencyBinding,
    ProductDependencySpec,
    ProductSpec,
    StageSpec,
)

type ArtworkPlanFactory = Callable[..., BuildPlan]


# =========================================================
# Helpers
# =========================================================


def _materialize_external_inputs(
    build_plan: BuildPlan,
    *,
    content: bytes = b"incremental-dispatch-input",
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
    Materialize every persistent product declared by one stage.
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
) -> None:
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


def _stage_by_name(
    build_plan: BuildPlan,
    stage_name: str,
) -> PlannedStage:
    """
    Return one realized stage by name.
    """

    return next(stage for stage in build_plan.stages if stage.name == stage_name)


def _product_dependency_build_plan(
    tmp_path: Path,
    *,
    resolver,
) -> BuildPlan:
    """
    Construct a minimal consumer plan with one cross-artifact dependency.

    The consumer stage requires an intermediate geometry product from a
    different artifact and model. The producer product itself is represented
    by the normal PlannedProductDependency contract.

    Producer execution is intentionally outside this helper and outside
    these tests.
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


def _record_product_dependency_current(
    build_plan: BuildPlan,
    *,
    fingerprint: ProductFingerprint,
) -> None:
    """
    Materialize the bound producer product with matching completion metadata.
    """

    if len(build_plan.planned_product_dependencies) != 1:
        raise AssertionError("Expected exactly one planned product dependency.")

    planned_dependency = build_plan.planned_product_dependencies[0]
    binding = planned_dependency.binding
    dependency = binding.dependency

    planned_dependency.path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    planned_dependency.path.write_bytes(
        b"producer-geometry",
    )

    write_stage_completion(
        planned_dependency.path.parent,
        StageCompletion(
            artifact_id=binding.artifact,
            model_name=dependency.model,
            realization=binding.realization,
            stage_name=dependency.stage,
            products=(dependency.product,),
            fingerprint=fingerprint,
        ),
    )


# =========================================================
# Dispatch
# =========================================================


def test_incremental_artifact_build_dispatches_all_absent_stages(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Every stage is dispatched when no persistent products are reusable.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    _materialize_external_inputs(
        build_plan,
    )

    dispatched: list[str] = []

    def dispatch(
        context: StageContext,
    ) -> None:
        dispatched.append(
            context.stage_name,
        )

        stage = _stage_by_name(
            build_plan,
            context.stage_name,
        )

        _materialize_stage_products(
            stage,
        )

    monkeypatch.setattr(
        incremental_module,
        "execute_stage",
        dispatch,
    )

    execute_incremental_artifact_build(
        build_plan,
    )

    assert tuple(
        dispatched,
    ) == tuple(stage.name for stage in build_plan.stages)


def test_incremental_artifact_build_dispatches_in_build_order(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Engine dispatch preserves realized build-plan order.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    _materialize_external_inputs(
        build_plan,
    )

    dispatched: list[str] = []

    def dispatch(
        context: StageContext,
    ) -> None:
        dispatched.append(
            context.stage_name,
        )

        stage = _stage_by_name(
            build_plan,
            context.stage_name,
        )

        _materialize_stage_products(
            stage,
        )

    monkeypatch.setattr(
        incremental_module,
        "execute_stage",
        dispatch,
    )

    execute_incremental_artifact_build(
        build_plan,
    )

    assert tuple(
        dispatched,
    ) == tuple(stage.name for stage in build_plan.stages)


# =========================================================
# Planned context construction
# =========================================================


def test_incremental_artifact_build_creates_context_for_required_stages(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Every required stage is adapted from the supplied BuildPlan.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    _materialize_external_inputs(
        build_plan,
    )

    requested: list[
        tuple[
            BuildPlan,
            PlannedStage,
        ]
    ] = []

    real_create_planned_stage_context = incremental_module.create_planned_stage_context

    def create_context(
        plan: BuildPlan,
        stage: PlannedStage,
    ) -> StageContext:
        requested.append(
            (
                plan,
                stage,
            )
        )

        return real_create_planned_stage_context(
            plan,
            stage,
        )

    def dispatch(
        context: StageContext,
    ) -> None:
        stage = _stage_by_name(
            build_plan,
            context.stage_name,
        )

        _materialize_stage_products(
            stage,
        )

    monkeypatch.setattr(
        incremental_module,
        "create_planned_stage_context",
        create_context,
    )

    monkeypatch.setattr(
        incremental_module,
        "execute_stage",
        dispatch,
    )

    execute_incremental_artifact_build(
        build_plan,
    )

    assert tuple(stage.name for _, stage in requested) == tuple(
        stage.name for stage in build_plan.stages
    )

    assert all(plan is build_plan for plan, _ in requested)

    assert all(
        requested_stage is planned_stage
        for (_, requested_stage), planned_stage in zip(
            requested,
            build_plan.stages,
            strict=True,
        )
    )


# =========================================================
# Current realization
# =========================================================


def test_incremental_artifact_build_does_not_dispatch_current_stages(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    A fully reusable realization reaches neither context nor dispatch.
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

    context_calls: list[str] = []
    dispatch_calls: list[str] = []

    real_create_planned_stage_context = incremental_module.create_planned_stage_context

    def create_context(
        plan: BuildPlan,
        stage: PlannedStage,
    ) -> StageContext:
        context_calls.append(
            stage.name,
        )

        return real_create_planned_stage_context(
            plan,
            stage,
        )

    def dispatch(
        context: StageContext,
    ) -> None:
        dispatch_calls.append(
            context.stage_name,
        )

    monkeypatch.setattr(
        incremental_module,
        "create_planned_stage_context",
        create_context,
    )

    monkeypatch.setattr(
        incremental_module,
        "execute_stage",
        dispatch,
    )

    execute_incremental_artifact_build(
        build_plan,
    )

    assert context_calls == []
    assert dispatch_calls == []


# =========================================================
# Selective dispatch
# =========================================================


def test_incremental_artifact_build_dispatches_only_invalidated_chain(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Changed external provenance dispatches only invalidated stages.
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

    for planned_input in consuming_stage.inputs:
        planned_input.path.write_bytes(
            b"changed-input",
        )

    dispatched: list[str] = []

    def dispatch(
        context: StageContext,
    ) -> None:
        dispatched.append(
            context.stage_name,
        )

        stage = _stage_by_name(
            build_plan,
            context.stage_name,
        )

        _materialize_stage_products(
            stage,
        )

    monkeypatch.setattr(
        incremental_module,
        "execute_stage",
        dispatch,
    )

    execution_plan = execute_incremental_artifact_build(
        build_plan,
    )

    assert tuple(
        dispatched,
    ) == tuple(stage.stage_name for stage in execution_plan.required_stages)


# =========================================================
# Cross-artifact dependency dispatch
# =========================================================


def test_incremental_artifact_build_accepts_product_dependency_fingerprint(
    tmp_path: Path,
    test_resolver,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Incremental artifact execution accepts authoritative producer-product
    fingerprint provenance.
    """

    build_plan = _product_dependency_build_plan(
        tmp_path,
        resolver=test_resolver,
    )

    producer_fingerprint = ProductFingerprint(
        algorithm="sha256",
        value="a" * 64,
    )

    _record_product_dependency_current(
        build_plan,
        fingerprint=producer_fingerprint,
    )

    dispatched: list[str] = []

    def dispatch(
        context: StageContext,
    ) -> None:
        dispatched.append(
            context.stage_name,
        )

        _materialize_stage_products(
            build_plan.stages[0],
        )

    monkeypatch.setattr(
        incremental_module,
        "execute_stage",
        dispatch,
    )

    execution_plan = execute_incremental_artifact_build(
        build_plan,
        product_dependency_fingerprint=(lambda dependency: producer_fingerprint),
    )

    assert dispatched == [
        "consume",
    ]

    assert execution_plan.product_dependencies[0].state is ProductState.CURRENT


def test_incremental_artifact_build_reuses_current_product_dependency(
    tmp_path: Path,
    test_resolver,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    A current producer product is reused without producer execution.
    """

    build_plan = _product_dependency_build_plan(
        tmp_path,
        resolver=test_resolver,
    )

    producer_fingerprint = ProductFingerprint(
        algorithm="sha256",
        value="b" * 64,
    )

    _record_product_dependency_current(
        build_plan,
        fingerprint=producer_fingerprint,
    )

    dispatched: list[str] = []

    def dispatch(
        context: StageContext,
    ) -> None:
        dispatched.append(
            context.stage_name,
        )

        _materialize_stage_products(
            build_plan.stages[0],
        )

    monkeypatch.setattr(
        incremental_module,
        "execute_stage",
        dispatch,
    )

    execution_plan = execute_incremental_artifact_build(
        build_plan,
        product_dependency_fingerprint=(lambda dependency: producer_fingerprint),
    )

    assert execution_plan.required_product_dependencies == ()

    assert dispatched == [
        "consume",
    ]


def test_incremental_artifact_build_does_not_execute_consumer_when_dependency_is_stale(
    tmp_path: Path,
    test_resolver,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    A stale producer product prevents consumer execution.
    """

    build_plan = _product_dependency_build_plan(
        tmp_path,
        resolver=test_resolver,
    )

    recorded_fingerprint = ProductFingerprint(
        algorithm="sha256",
        value="c" * 64,
    )

    required_fingerprint = ProductFingerprint(
        algorithm="sha256",
        value="d" * 64,
    )

    _record_product_dependency_current(
        build_plan,
        fingerprint=recorded_fingerprint,
    )

    dispatched: list[str] = []

    def dispatch(
        context: StageContext,
    ) -> None:
        dispatched.append(
            context.stage_name,
        )

    monkeypatch.setattr(
        incremental_module,
        "execute_stage",
        dispatch,
    )

    execution_plan = execute_incremental_artifact_build(
        build_plan,
        product_dependency_fingerprint=(lambda dependency: required_fingerprint),
    )

    assert dispatched == []

    assert (
        len(
            execution_plan.required_product_dependencies,
        )
        == 1
    )

    assert execution_plan.required_product_dependencies[0].state is ProductState.STALE


def test_incremental_artifact_build_does_not_execute_consumer_when_dependency_is_absent(
    tmp_path: Path,
    test_resolver,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    An absent required producer product prevents consumer execution.
    """

    build_plan = _product_dependency_build_plan(
        tmp_path,
        resolver=test_resolver,
    )

    producer_fingerprint = ProductFingerprint(
        algorithm="sha256",
        value="e" * 64,
    )

    dispatched: list[str] = []

    def dispatch(
        context: StageContext,
    ) -> None:
        dispatched.append(
            context.stage_name,
        )

    monkeypatch.setattr(
        incremental_module,
        "execute_stage",
        dispatch,
    )

    execution_plan = execute_incremental_artifact_build(
        build_plan,
        product_dependency_fingerprint=(lambda dependency: producer_fingerprint),
    )

    assert dispatched == []

    assert (
        len(
            execution_plan.required_product_dependencies,
        )
        == 1
    )

    assert execution_plan.required_product_dependencies[0].state is ProductState.ABSENT


# =========================================================
# Failure propagation
# =========================================================


def test_dispatch_failure_propagates(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Failure from the established stage-dispatch boundary propagates.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    _materialize_external_inputs(
        build_plan,
    )

    failing_stage = build_plan.stages[0]

    class ExpectedError(Exception):
        """
        Expected dispatch failure.
        """

    def dispatch(
        context: StageContext,
    ) -> None:
        if context.stage_name == failing_stage.name:
            raise ExpectedError

        stage = _stage_by_name(
            build_plan,
            context.stage_name,
        )

        _materialize_stage_products(
            stage,
        )

    monkeypatch.setattr(
        incremental_module,
        "execute_stage",
        dispatch,
    )

    with pytest.raises(
        ExpectedError,
    ):
        execute_incremental_artifact_build(
            build_plan,
        )


def test_dispatch_failure_stops_later_context_creation(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    No later stage is adapted or dispatched after stage failure.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    _materialize_external_inputs(
        build_plan,
    )

    failing_stage = build_plan.stages[0]

    requested: list[str] = []

    real_create_planned_stage_context = incremental_module.create_planned_stage_context

    def create_context(
        plan: BuildPlan,
        stage: PlannedStage,
    ) -> StageContext:
        requested.append(
            stage.name,
        )

        return real_create_planned_stage_context(
            plan,
            stage,
        )

    class ExpectedError(Exception):
        """
        Expected dispatch failure.
        """

    def dispatch(
        context: StageContext,
    ) -> None:
        if context.stage_name == failing_stage.name:
            raise ExpectedError

    monkeypatch.setattr(
        incremental_module,
        "create_planned_stage_context",
        create_context,
    )

    monkeypatch.setattr(
        incremental_module,
        "execute_stage",
        dispatch,
    )

    with pytest.raises(
        ExpectedError,
    ):
        execute_incremental_artifact_build(
            build_plan,
        )

    assert requested == [
        failing_stage.name,
    ]
