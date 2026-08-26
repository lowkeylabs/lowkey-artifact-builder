"""
Tests for required cross-artifact producer build planning.

These tests verify composition of consumer execution decisions with
concrete producer build plans.

Producer planning consumes the already-resolved product dependencies of
a consumer BuildPlan and the producer-product requirements identified by
its ExecutionPlan.

Only producer products requiring production receive targeted BuildPlans.
Reusable producer products do not create producer work.

These tests exercise planning only. They do not execute producer or
consumer stages.
"""
# File: tests/engine/test_dependency_plan.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path

import pytest

from lowkey_artifact_builder.config import (
    Resolver,
)
from lowkey_artifact_builder.engine import (
    BuildPlan,
    ExecutionPlan,
    PlannedProductDependency,
    PlannedProductDependencyExecution,
    ProductState,
    create_required_product_dependency_build_plans,
)
from lowkey_artifact_builder.model import (
    ModelSpec,
    ProductDependencyBinding,
    ProductDependencySpec,
    ProductRef,
)

# =========================================================
# Helpers
# =========================================================


def _planned_product_dependency(
    tmp_path: Path,
    *,
    artifact: str,
    model: str,
    stage: str,
    product: str,
) -> PlannedProductDependency:
    """
    Construct one concrete bound producer-product dependency.
    """

    dependency = ProductDependencySpec(
        model=model,
        stage=stage,
        product=product,
    )

    binding = ProductDependencyBinding(
        dependency=dependency,
        artifact=artifact,
        realization="default",
    )

    return PlannedProductDependency(
        binding=binding,
        path=(tmp_path / "artifacts" / artifact / model / "default" / stage / product),
    )


def _consumer_build_plan(
    tmp_path: Path,
    test_resolver: Resolver,
    *,
    dependencies: tuple[PlannedProductDependency, ...],
) -> BuildPlan:
    """
    Construct a minimal consumer BuildPlan with bound producer products.
    """

    return BuildPlan(
        artifact_id="consumer-artifact",
        model=ModelSpec(
            name="consumer",
            title="Consumer",
        ),
        realization_name="default",
        resolver=test_resolver,
        project_root=tmp_path,
        artifact_dir=tmp_path / "artifacts" / "consumer-artifact",
        stages=(),
        planned_product_dependencies=dependencies,
    )


def _execution_plan(
    *,
    dependencies: tuple[
        tuple[
            PlannedProductDependency,
            ProductState,
        ],
        ...,
    ],
) -> ExecutionPlan:
    """
    Construct producer-product execution decisions for a consumer.
    """

    return ExecutionPlan(
        artifact_id="consumer-artifact",
        model_name="consumer",
        realization="default",
        stages=(),
        product_dependencies=tuple(
            PlannedProductDependencyExecution(
                product_ref=dependency.product_ref,
                state=state,
            )
            for dependency, state in dependencies
        ),
    )


# =========================================================
# Required producer planning
# =========================================================


def test_required_product_dependency_creates_targeted_producer_plan(
    tmp_path: Path,
    test_resolver: Resolver,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    A producer product requiring production creates a targeted producer
    BuildPlan for exactly that product.
    """

    dependency = _planned_product_dependency(
        tmp_path,
        artifact="producer-artifact",
        model="producer",
        stage="transform",
        product="geometry",
    )

    build_plan = _consumer_build_plan(
        tmp_path,
        test_resolver,
        dependencies=(dependency,),
    )

    execution_plan = _execution_plan(
        dependencies=(
            (
                dependency,
                ProductState.ABSENT,
            ),
        ),
    )

    requested: list[PlannedProductDependency] = []

    producer_plan = BuildPlan(
        artifact_id="producer-artifact",
        model=ModelSpec(
            name="producer",
            title="Producer",
        ),
        realization_name="default",
        resolver=test_resolver,
        project_root=tmp_path,
        artifact_dir=tmp_path / "artifacts" / "producer-artifact",
        stages=(),
        targets=(dependency.product_ref,),
    )

    def fake_create_product_dependency_build_plan(
        planned_dependency: PlannedProductDependency,
        *,
        project_root: Path | None = None,
    ) -> BuildPlan:
        requested.append(
            planned_dependency,
        )

        assert project_root == tmp_path

        return producer_plan

    monkeypatch.setattr(
        "lowkey_artifact_builder.engine.dependency_plan.create_product_dependency_build_plan",
        fake_create_product_dependency_build_plan,
    )

    plans = create_required_product_dependency_build_plans(
        build_plan,
        execution_plan,
    )

    assert requested == [
        dependency,
    ]

    assert plans == (producer_plan,)

    assert plans[0].targets == (
        ProductRef(
            artifact="producer-artifact",
            model="producer",
            realization="default",
            stage="transform",
            product="geometry",
        ),
    )


def test_current_product_dependency_creates_no_producer_plan(
    tmp_path: Path,
    test_resolver: Resolver,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    A reusable producer product does not create a producer BuildPlan.
    """

    dependency = _planned_product_dependency(
        tmp_path,
        artifact="producer-artifact",
        model="producer",
        stage="transform",
        product="geometry",
    )

    build_plan = _consumer_build_plan(
        tmp_path,
        test_resolver,
        dependencies=(dependency,),
    )

    execution_plan = _execution_plan(
        dependencies=(
            (
                dependency,
                ProductState.CURRENT,
            ),
        ),
    )

    def unexpected_create_product_dependency_build_plan(
        planned_dependency: PlannedProductDependency,
        *,
        project_root: Path | None = None,
    ) -> BuildPlan:
        raise AssertionError("CURRENT producer product must not be planned")

    monkeypatch.setattr(
        "lowkey_artifact_builder.engine.dependency_plan.create_product_dependency_build_plan",
        unexpected_create_product_dependency_build_plan,
    )

    plans = create_required_product_dependency_build_plans(
        build_plan,
        execution_plan,
    )

    assert plans == ()


def test_required_product_dependency_preserves_producer_identity(
    tmp_path: Path,
    test_resolver: Resolver,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Producer planning preserves producer identity independently of the
    consuming artifact.
    """

    dependency = _planned_product_dependency(
        tmp_path,
        artifact="artwork-a",
        model="producer",
        stage="transform",
        product="geometry",
    )

    build_plan = _consumer_build_plan(
        tmp_path,
        test_resolver,
        dependencies=(dependency,),
    )

    execution_plan = _execution_plan(
        dependencies=(
            (
                dependency,
                ProductState.STALE,
            ),
        ),
    )

    def fake_create_product_dependency_build_plan(
        planned_dependency: PlannedProductDependency,
        *,
        project_root: Path | None = None,
    ) -> BuildPlan:
        assert planned_dependency is dependency
        assert project_root == tmp_path

        return BuildPlan(
            artifact_id=planned_dependency.product_ref.artifact,
            model=ModelSpec(
                name=planned_dependency.product_ref.model,
                title="Producer",
            ),
            realization_name=planned_dependency.product_ref.realization,
            resolver=test_resolver,
            project_root=tmp_path,
            artifact_dir=(tmp_path / "artifacts" / planned_dependency.product_ref.artifact),
            stages=(),
            targets=(planned_dependency.product_ref,),
        )

    monkeypatch.setattr(
        "lowkey_artifact_builder.engine.dependency_plan.create_product_dependency_build_plan",
        fake_create_product_dependency_build_plan,
    )

    plans = create_required_product_dependency_build_plans(
        build_plan,
        execution_plan,
    )

    assert build_plan.artifact_id == "consumer-artifact"

    assert len(plans) == 1

    producer_plan = plans[0]

    assert producer_plan.artifact_id == "artwork-a"
    assert producer_plan.model_name == "producer"
    assert producer_plan.realization_name == "default"

    assert producer_plan.targets == (dependency.product_ref,)


def test_multiple_required_product_dependencies_create_independent_producer_plans(
    tmp_path: Path,
    test_resolver: Resolver,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Required products from different producer artifacts create independent
    targeted producer BuildPlans while reusable producers are omitted.
    """

    geometry = _planned_product_dependency(
        tmp_path,
        artifact="artwork-a",
        model="producer",
        stage="transform",
        product="geometry",
    )

    mask = _planned_product_dependency(
        tmp_path,
        artifact="artwork-c",
        model="mask-producer",
        stage="prepare",
        product="mask",
    )

    reusable = _planned_product_dependency(
        tmp_path,
        artifact="artwork-d",
        model="palette-producer",
        stage="prepare",
        product="palette",
    )

    build_plan = _consumer_build_plan(
        tmp_path,
        test_resolver,
        dependencies=(
            geometry,
            mask,
            reusable,
        ),
    )

    execution_plan = _execution_plan(
        dependencies=(
            (
                geometry,
                ProductState.ABSENT,
            ),
            (
                mask,
                ProductState.STALE,
            ),
            (
                reusable,
                ProductState.CURRENT,
            ),
        ),
    )

    requested: list[ProductRef] = []

    def fake_create_product_dependency_build_plan(
        dependency: PlannedProductDependency,
        *,
        project_root: Path | None = None,
    ) -> BuildPlan:
        requested.append(
            dependency.product_ref,
        )

        assert project_root == tmp_path

        return BuildPlan(
            artifact_id=dependency.product_ref.artifact,
            model=ModelSpec(
                name=dependency.product_ref.model,
                title="Producer",
            ),
            realization_name=dependency.product_ref.realization,
            resolver=test_resolver,
            project_root=tmp_path,
            artifact_dir=(tmp_path / "artifacts" / dependency.product_ref.artifact),
            stages=(),
            targets=(dependency.product_ref,),
        )

    monkeypatch.setattr(
        "lowkey_artifact_builder.engine.dependency_plan.create_product_dependency_build_plan",
        fake_create_product_dependency_build_plan,
    )

    plans = create_required_product_dependency_build_plans(
        build_plan,
        execution_plan,
    )

    assert requested == [
        geometry.product_ref,
        mask.product_ref,
    ]

    assert tuple(plan.artifact_id for plan in plans) == (
        "artwork-a",
        "artwork-c",
    )

    assert tuple(plan.targets for plan in plans) == (
        (geometry.product_ref,),
        (mask.product_ref,),
    )
