"""
Tests for persistent-state-aware execution planning.

Execution planning composes a realized BuildPlan with persistent product
state resolution to determine which realized stages require execution.

Cross-artifact product dependencies participate in the same planning
boundary. Their persistent states determine whether an already-produced
upstream product may be reused or requires production before the consumer
can execute.

These tests exercise the high-level planning boundary using actual
filesystem products, completion metadata, and required build-context
fingerprints.

They do not execute stages, materialize external inputs, emit execution
events, construct producer build plans, or modify products except where
persistent evidence is required to establish test state.
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
    PlannedProductDependency,
    PlannedStage,
    ProductFingerprint,
    ProductState,
    StageCompletion,
    plan_execution,
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


def _dependency_fingerprint(
    dependency: PlannedProductDependency,
) -> ProductFingerprint:
    """
    Create deterministic representative provenance for one product dependency.
    """

    product_ref = dependency.product_ref

    return ProductFingerprint(
        algorithm="sha256",
        value=(
            f"{product_ref.artifact}:"
            f"{product_ref.model}:"
            f"{product_ref.realization}:"
            f"{product_ref.stage}:"
            f"{product_ref.product}"
        ),
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


def _product_dependency_plan(
    *,
    tmp_path: Path,
    resolver,
) -> tuple[
    BuildPlan,
    PlannedProductDependency,
]:
    """
    Create a consumer plan with one bound cross-artifact dependency.

    The producer product is intentionally represented only by its bound
    logical identity and already-resolved persistent path. No producer
    BuildPlan or producer downstream workflow participates in the consumer
    plan.
    """

    dependency = ProductDependencySpec(
        model="producer",
        stage="prepare",
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
        / "10-prepare"
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
        products=(),
    )

    model = ModelSpec(
        name="consumer",
        title="Consumer",
        stages=(stage_spec,),
    )

    build_plan = BuildPlan(
        artifact_id="consumer-artifact",
        model=model,
        realization_name="default",
        resolver=resolver,
        project_root=tmp_path,
        artifact_dir=(tmp_path / "artifacts" / "consumer-artifact"),
        stages=(stage,),
        product_dependencies=(dependency,),
        product_dependency_bindings=(binding,),
        planned_product_dependencies=(planned_dependency,),
    )

    return (
        build_plan,
        planned_dependency,
    )


def _materialize_product_dependency(
    dependency: PlannedProductDependency,
    *,
    fingerprint: ProductFingerprint | None,
) -> None:
    """
    Materialize one producer product and its completion metadata.
    """

    product_ref = dependency.product_ref
    working_dir = dependency.path.parent

    working_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    dependency.path.write_text(
        product_ref.product,
        encoding="utf-8",
    )

    write_stage_completion(
        working_dir,
        StageCompletion(
            artifact_id=product_ref.artifact,
            model_name=product_ref.model,
            realization=product_ref.realization,
            stage_name=product_ref.stage,
            products=(product_ref.product,),
            fingerprint=fingerprint,
        ),
    )


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
# Cross-artifact product dependencies
# =========================================================


def test_plan_execution_preserves_product_dependency_identity(
    tmp_path: Path,
    test_resolver,
) -> None:
    """
    Execution planning preserves the bound producer product identity.
    """

    build_plan, dependency = _product_dependency_plan(
        tmp_path=tmp_path,
        resolver=test_resolver,
    )

    execution_plan = plan_execution(
        build_plan,
        required_fingerprint=_fingerprint,
        required_product_dependency_fingerprint=_dependency_fingerprint,
    )

    assert (
        len(
            execution_plan.product_dependencies,
        )
        == 1
    )

    planned_dependency = execution_plan.product_dependencies[0]

    assert planned_dependency.product_ref == dependency.product_ref


def test_missing_product_dependency_requires_production(
    tmp_path: Path,
    test_resolver,
) -> None:
    """
    An absent upstream product is identified as requiring production.
    """

    build_plan, dependency = _product_dependency_plan(
        tmp_path=tmp_path,
        resolver=test_resolver,
    )

    execution_plan = plan_execution(
        build_plan,
        required_fingerprint=_fingerprint,
        required_product_dependency_fingerprint=_dependency_fingerprint,
    )

    planned_dependency = execution_plan.product_dependencies[0]

    assert planned_dependency.product_ref == dependency.product_ref
    assert planned_dependency.state is ProductState.ABSENT
    assert planned_dependency.requires_production


def test_current_product_dependency_is_reusable(
    tmp_path: Path,
    test_resolver,
) -> None:
    """
    A current upstream product may be reused without producer work.
    """

    build_plan, dependency = _product_dependency_plan(
        tmp_path=tmp_path,
        resolver=test_resolver,
    )

    _materialize_product_dependency(
        dependency,
        fingerprint=_dependency_fingerprint(
            dependency,
        ),
    )

    execution_plan = plan_execution(
        build_plan,
        required_fingerprint=_fingerprint,
        required_product_dependency_fingerprint=_dependency_fingerprint,
    )

    planned_dependency = execution_plan.product_dependencies[0]

    assert planned_dependency.state is ProductState.CURRENT
    assert not planned_dependency.requires_production


def test_stale_product_dependency_requires_production(
    tmp_path: Path,
    test_resolver,
) -> None:
    """
    A stale upstream product is identified as requiring production.
    """

    build_plan, dependency = _product_dependency_plan(
        tmp_path=tmp_path,
        resolver=test_resolver,
    )

    _materialize_product_dependency(
        dependency,
        fingerprint=ProductFingerprint(
            algorithm="sha256",
            value="old-producer-context",
        ),
    )

    execution_plan = plan_execution(
        build_plan,
        required_fingerprint=_fingerprint,
        required_product_dependency_fingerprint=_dependency_fingerprint,
    )

    planned_dependency = execution_plan.product_dependencies[0]

    assert planned_dependency.state is ProductState.STALE
    assert planned_dependency.requires_production


def test_current_product_dependency_does_not_require_producer_pipeline(
    tmp_path: Path,
    test_resolver,
) -> None:
    """
    Reusing an upstream product does not require the producer's downstream work.

    Only the bound producer product is represented by the consumer BuildPlan.
    No producer BuildPlan, downstream producer stage, or final producer
    artifact is required to prove that product reusable.
    """

    build_plan, dependency = _product_dependency_plan(
        tmp_path=tmp_path,
        resolver=test_resolver,
    )

    _materialize_product_dependency(
        dependency,
        fingerprint=_dependency_fingerprint(
            dependency,
        ),
    )

    producer_final_product = (
        tmp_path
        / "artifacts"
        / "producer-artifact"
        / "producer"
        / "default"
        / "50-package"
        / "artifact.dat"
    )

    assert not producer_final_product.exists()

    execution_plan = plan_execution(
        build_plan,
        required_fingerprint=_fingerprint,
        required_product_dependency_fingerprint=_dependency_fingerprint,
    )

    planned_dependency = execution_plan.product_dependencies[0]

    assert planned_dependency.state is ProductState.CURRENT
    assert not planned_dependency.requires_production
    assert not producer_final_product.exists()


def test_execution_plan_exposes_only_dependencies_requiring_production(
    tmp_path: Path,
    test_resolver,
) -> None:
    """
    Required product dependencies contain only nonreusable upstream products.
    """

    build_plan, dependency = _product_dependency_plan(
        tmp_path=tmp_path,
        resolver=test_resolver,
    )

    execution_plan = plan_execution(
        build_plan,
        required_fingerprint=_fingerprint,
        required_product_dependency_fingerprint=_dependency_fingerprint,
    )

    assert tuple(
        planned.product_ref for planned in execution_plan.required_product_dependencies
    ) == (dependency.product_ref,)


def test_current_product_dependency_is_omitted_from_required_dependencies(
    tmp_path: Path,
    test_resolver,
) -> None:
    """
    A reusable upstream product is omitted from required producer work.
    """

    build_plan, dependency = _product_dependency_plan(
        tmp_path=tmp_path,
        resolver=test_resolver,
    )

    _materialize_product_dependency(
        dependency,
        fingerprint=_dependency_fingerprint(
            dependency,
        ),
    )

    execution_plan = plan_execution(
        build_plan,
        required_fingerprint=_fingerprint,
        required_product_dependency_fingerprint=_dependency_fingerprint,
    )

    assert execution_plan.required_product_dependencies == ()


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


def test_plan_execution_resolves_required_fingerprint_per_product_dependency(
    tmp_path: Path,
    test_resolver,
) -> None:
    """
    Planning requests current provenance for every bound producer product.
    """

    build_plan, dependency = _product_dependency_plan(
        tmp_path=tmp_path,
        resolver=test_resolver,
    )

    calls: list[PlannedProductDependency] = []

    def required_product_dependency_fingerprint(
        candidate: PlannedProductDependency,
    ) -> ProductFingerprint:
        calls.append(
            candidate,
        )

        return _dependency_fingerprint(
            candidate,
        )

    plan_execution(
        build_plan,
        required_fingerprint=_fingerprint,
        required_product_dependency_fingerprint=(required_product_dependency_fingerprint),
    )

    assert calls == [
        dependency,
    ]
