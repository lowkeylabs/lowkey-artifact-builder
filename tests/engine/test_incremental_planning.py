"""
Tests for persistent-state-aware incremental execution planning.

Incremental execution planning composes required build-context fingerprint
generation, persistent product-state resolution, and execution-plan
construction.

The caller supplies only a realized BuildPlan. Required fingerprints are
derived from the plan, persistent product evidence is inspected, and the
resulting ExecutionPlan identifies which realized stages require execution.

These tests exercise planning only. They do not execute stages or modify
persistent completion state through execution.
"""
# File: tests/engine/test_incremental_planning.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from collections.abc import Callable, Iterable
from pathlib import Path

import pytest

from lowkey_artifact_builder.engine import (
    BuildPlan,
    PlannedProduct,
    PlannedProductDependency,
    PlannedProductDependencyExecution,
    PlannedStage,
    PlannedStageExecution,
    ProductFingerprint,
    ProductState,
    StageCompletion,
    create_product_dependency_fingerprint_resolver,
    create_required_fingerprints,
    plan_incremental_execution,
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
    content: bytes = b"incremental-planning-input",
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

    Planned product paths are already fully realized filesystem paths.
    Every persistent product of one stage must therefore share the same
    parent directory.
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


def _record_stage_completion(
    build_plan: BuildPlan,
    stage: PlannedStage,
    fingerprint: ProductFingerprint,
) -> None:
    """
    Record successful completion of one realized stage.
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
    Materialize and record all stages using their required fingerprints.
    """

    fingerprints = create_required_fingerprints(
        build_plan,
    )

    for stage in build_plan.stages:
        if not stage.products:
            continue

        _record_stage_completion(
            build_plan,
            stage,
            fingerprints[stage.name],
        )

    return fingerprints


def _stage_names(
    stages: Iterable[PlannedStageExecution],
) -> tuple[str, ...]:
    """
    Return stage names from planned stage-execution decisions.
    """

    return tuple(stage.stage_name for stage in stages)


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


def _product_dependency_plan(
    *,
    tmp_path: Path,
    resolver,
    dependency_path: Path,
) -> BuildPlan:
    """
    Construct a minimal realized consumer plan with one bound producer product.
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

    planned_dependency = PlannedProductDependency(
        binding=binding,
        path=dependency_path,
    )

    stage_spec = StageSpec(
        id=10,
        name="consume",
        product_dependencies=(dependency,),
    )

    consumer_product_path = (
        tmp_path
        / "artifacts"
        / "consumer-artifact"
        / "consumer"
        / "default"
        / "10-consume"
        / "artifact.dat"
    )

    stage = PlannedStage(
        spec=stage_spec,
        products=(
            PlannedProduct(
                spec=ProductSpec(
                    name="artifact",
                    path="artifact.dat",
                ),
                path=consumer_product_path,
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
    content: bytes = b"producer-product",
) -> ProductFingerprint:
    """
    Materialize one bound producer product with matching completion provenance.
    """

    assert len(build_plan.planned_product_dependencies) == 1

    planned_dependency = build_plan.planned_product_dependencies[0]
    binding = planned_dependency.binding
    dependency = binding.dependency

    planned_dependency.path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    planned_dependency.path.write_bytes(
        content,
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

    return fingerprint


def _producer_product_plan(
    *,
    tmp_path: Path,
    resolver,
) -> BuildPlan:
    """
    Construct a producer plan with an intermediate reusable product.

    The requested geometry product is produced by transform. Package is
    deliberately downstream so tests can prove that resolving geometry
    provenance does not depend upon the producer's complete pipeline.
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

    package_spec = StageSpec(
        id=30,
        name="package",
        dependencies=("transform",),
        products=(
            ProductSpec(
                name="artifact",
                path="artifact.dat",
            ),
        ),
    )

    model = ModelSpec(
        name="producer",
        title="Producer",
        stages=(
            prepare_spec,
            transform_spec,
            package_spec,
        ),
    )

    realization_dir = tmp_path / "artifacts" / "producer-artifact" / "producer" / "default"

    prepare = PlannedStage(
        spec=prepare_spec,
        products=(
            PlannedProduct(
                spec=prepare_spec.products[0],
                path=realization_dir / "10-prepare" / "prepared.dat",
            ),
        ),
    )

    transform = PlannedStage(
        spec=transform_spec,
        products=(
            PlannedProduct(
                spec=transform_spec.products[0],
                path=realization_dir / "20-transform" / "geometry.dat",
            ),
        ),
    )

    package = PlannedStage(
        spec=package_spec,
        products=(
            PlannedProduct(
                spec=package_spec.products[0],
                path=realization_dir / "30-package" / "artifact.dat",
            ),
        ),
    )

    return BuildPlan(
        artifact_id="producer-artifact",
        model=model,
        realization_name="default",
        resolver=resolver,
        project_root=tmp_path,
        artifact_dir=tmp_path / "artifacts" / "producer-artifact",
        stages=(
            prepare,
            transform,
            package,
        ),
    )


# =========================================================
# Empty persistent workspace
# =========================================================


def test_incremental_plan_preserves_build_identity(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Incremental planning preserves realized artifact identity.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    _materialize_external_inputs(
        build_plan,
    )

    execution_plan = plan_incremental_execution(
        build_plan,
    )

    assert execution_plan.artifact_id == build_plan.artifact_id
    assert execution_plan.model_name == build_plan.model_name
    assert execution_plan.realization == build_plan.realization_name


def test_empty_workspace_requires_all_realized_stages(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Without persistent products every realized stage requires execution.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    _materialize_external_inputs(
        build_plan,
    )

    execution_plan = plan_incremental_execution(
        build_plan,
    )

    assert _stage_names(
        execution_plan.required_stages,
    ) == tuple(stage.name for stage in build_plan.stages)


# =========================================================
# Fully current realization
# =========================================================


def test_current_realization_requires_no_stage_execution(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    A fully current persistent realization is completely reusable.
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

    execution_plan = plan_incremental_execution(
        build_plan,
    )

    assert execution_plan.required_stages == ()


def test_current_realization_remains_in_complete_execution_plan(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Reusable stages remain represented in the complete execution plan.
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

    execution_plan = plan_incremental_execution(
        build_plan,
    )

    assert _stage_names(
        execution_plan.stages,
    ) == tuple(stage.name for stage in build_plan.stages)


# =========================================================
# Missing persistent product
# =========================================================


def test_missing_product_requires_its_stage(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Removing one current product makes its producing stage non-reusable.
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

    stage = next(stage for stage in build_plan.stages if stage.products)

    product = stage.products[0]

    product.path.unlink()

    execution_plan = plan_incremental_execution(
        build_plan,
    )

    assert stage.name in _stage_names(
        execution_plan.required_stages,
    )


# =========================================================
# Changed external input
# =========================================================


def test_changed_external_input_makes_consuming_stage_stale(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Changed external input content invalidates its consuming stage.
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

    execution_plan = plan_incremental_execution(
        build_plan,
    )

    assert consuming_stage.name in _stage_names(
        execution_plan.required_stages,
    )


def test_changed_external_input_invalidates_descendants(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Changed external provenance propagates through dependent stages.
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

    descendants = _descendant_stage_names(
        build_plan,
        consuming_stage.name,
    )

    assert descendants

    for planned_input in consuming_stage.inputs:
        planned_input.path.write_bytes(
            b"changed-input",
        )

    execution_plan = plan_incremental_execution(
        build_plan,
    )

    required = set(
        _stage_names(
            execution_plan.required_stages,
        )
    )

    assert consuming_stage.name in required

    for descendant in descendants:
        assert descendant in required


# =========================================================
# Changed parameter
# =========================================================


def test_changed_declared_parameter_invalidates_stage_and_descendants(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Changed declared configuration invalidates affected provenance.
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

    affected_stage = next(stage for stage in build_plan.stages if stage.spec.parameters)

    descendants = _descendant_stage_names(
        build_plan,
        affected_stage.name,
    )

    parameter = affected_stage.spec.parameters[0]

    original_resolver = build_plan.resolver
    original_value = original_resolver(
        parameter,
    )

    def changed_resolver(
        name: str,
    ) -> object:
        if name == parameter:
            return {
                "original": original_value,
                "changed": True,
            }

        return original_resolver(
            name,
        )

    object.__setattr__(
        build_plan,
        "resolver",
        changed_resolver,
    )

    execution_plan = plan_incremental_execution(
        build_plan,
    )

    required = set(
        _stage_names(
            execution_plan.required_stages,
        )
    )

    assert affected_stage.name in required

    for descendant in descendants:
        assert descendant in required


# =========================================================
# Cross-artifact product dependencies
# =========================================================


def test_incremental_plan_preserves_product_dependency(
    tmp_path: Path,
    test_resolver,
) -> None:
    """
    Incremental planning preserves a bound producer product requirement.
    """

    dependency_path = (
        tmp_path
        / "artifacts"
        / "producer-artifact"
        / "producer"
        / "default"
        / "10-prepare"
        / "geometry.dat"
    )

    build_plan = _product_dependency_plan(
        tmp_path=tmp_path,
        resolver=test_resolver,
        dependency_path=dependency_path,
    )

    execution_plan = plan_incremental_execution(
        build_plan,
    )

    assert (
        len(
            execution_plan.product_dependencies,
        )
        == 1
    )

    dependency = execution_plan.product_dependencies[0]

    assert isinstance(
        dependency,
        PlannedProductDependencyExecution,
    )

    assert dependency.product_ref == (build_plan.planned_product_dependencies[0].product_ref)


def test_absent_product_dependency_requires_production(
    tmp_path: Path,
    test_resolver,
) -> None:
    """
    An absent bound producer product requires production.
    """

    dependency_path = (
        tmp_path
        / "artifacts"
        / "producer-artifact"
        / "producer"
        / "default"
        / "10-prepare"
        / "geometry.dat"
    )

    build_plan = _product_dependency_plan(
        tmp_path=tmp_path,
        resolver=test_resolver,
        dependency_path=dependency_path,
    )

    execution_plan = plan_incremental_execution(
        build_plan,
    )

    assert (
        len(
            execution_plan.required_product_dependencies,
        )
        == 1
    )

    dependency = execution_plan.required_product_dependencies[0]

    assert dependency.state is ProductState.ABSENT
    assert dependency.requires_production


def test_absent_product_dependency_does_not_require_unrelated_producer_pipeline(
    tmp_path: Path,
    test_resolver,
) -> None:
    """
    Incremental planning identifies the required producer product itself.

    Producer stages are not injected into the consumer's local realized
    stage sequence.
    """

    dependency_path = (
        tmp_path
        / "artifacts"
        / "producer-artifact"
        / "producer"
        / "default"
        / "10-prepare"
        / "geometry.dat"
    )

    build_plan = _product_dependency_plan(
        tmp_path=tmp_path,
        resolver=test_resolver,
        dependency_path=dependency_path,
    )

    execution_plan = plan_incremental_execution(
        build_plan,
    )

    assert _stage_names(
        execution_plan.stages,
    ) == ("consume",)

    assert (
        len(
            execution_plan.required_product_dependencies,
        )
        == 1
    )

    assert (
        execution_plan.required_product_dependencies[0].product_ref
        == build_plan.planned_product_dependencies[0].product_ref
    )


def test_current_product_dependency_does_not_require_production(
    tmp_path: Path,
    test_resolver,
) -> None:
    """
    A current bound producer product is reusable.
    """

    dependency_path = (
        tmp_path
        / "artifacts"
        / "producer-artifact"
        / "producer"
        / "default"
        / "10-prepare"
        / "geometry.dat"
    )

    build_plan = _product_dependency_plan(
        tmp_path=tmp_path,
        resolver=test_resolver,
        dependency_path=dependency_path,
    )

    producer_fingerprint = _record_product_dependency_current(
        build_plan,
        fingerprint=ProductFingerprint(
            algorithm="sha256",
            value="a" * 64,
        ),
    )

    execution_plan = plan_incremental_execution(
        build_plan,
        product_dependency_fingerprint=(lambda dependency: producer_fingerprint),
    )

    assert len(execution_plan.product_dependencies) == 1

    dependency = execution_plan.product_dependencies[0]

    assert dependency.state is ProductState.CURRENT
    assert not dependency.requires_production
    assert execution_plan.required_product_dependencies == ()


def test_current_product_dependency_allows_consumer_planning(
    tmp_path: Path,
    test_resolver,
) -> None:
    """
    A reusable producer product permits normal consumer-stage planning.

    The consumer product is absent, so normal persistent-state planning
    identifies the consumer stage as requiring execution.
    """

    dependency_path = (
        tmp_path
        / "artifacts"
        / "producer-artifact"
        / "producer"
        / "default"
        / "10-prepare"
        / "geometry.dat"
    )

    build_plan = _product_dependency_plan(
        tmp_path=tmp_path,
        resolver=test_resolver,
        dependency_path=dependency_path,
    )

    producer_fingerprint = _record_product_dependency_current(
        build_plan,
        fingerprint=ProductFingerprint(
            algorithm="sha256",
            value="a" * 64,
        ),
    )

    execution_plan = plan_incremental_execution(
        build_plan,
        product_dependency_fingerprint=(lambda dependency: producer_fingerprint),
    )

    assert execution_plan.product_dependencies[0].state is ProductState.CURRENT

    assert execution_plan.stages[0].product_states == (ProductState.ABSENT,)

    assert _stage_names(
        execution_plan.required_stages,
    ) == ("consume",)


def test_current_product_dependency_does_not_add_producer_stages(
    tmp_path: Path,
    test_resolver,
) -> None:
    """
    Reusing a current producer product adds no producer stages.

    The consumer execution plan contains only its own realized workflow.
    """

    dependency_path = (
        tmp_path
        / "artifacts"
        / "producer-artifact"
        / "producer"
        / "default"
        / "10-prepare"
        / "geometry.dat"
    )

    build_plan = _product_dependency_plan(
        tmp_path=tmp_path,
        resolver=test_resolver,
        dependency_path=dependency_path,
    )

    producer_fingerprint = _record_product_dependency_current(
        build_plan,
        fingerprint=ProductFingerprint(
            algorithm="sha256",
            value="a" * 64,
        ),
    )

    execution_plan = plan_incremental_execution(
        build_plan,
        product_dependency_fingerprint=(lambda dependency: producer_fingerprint),
    )

    assert execution_plan.required_product_dependencies == ()

    assert _stage_names(
        execution_plan.stages,
    ) == ("consume",)


def test_product_dependency_fingerprint_comes_from_producer_plan(
    tmp_path: Path,
    test_resolver,
) -> None:
    """
    A bound dependency resolves to the fingerprint of its producing stage.
    """

    producer_plan = _producer_product_plan(
        tmp_path=tmp_path,
        resolver=test_resolver,
    )

    fingerprints = create_required_fingerprints(
        producer_plan,
    )

    dependency = PlannedProductDependency(
        binding=ProductDependencyBinding(
            dependency=ProductDependencySpec(
                model="producer",
                stage="transform",
                product="geometry",
            ),
            artifact="producer-artifact",
            realization="default",
        ),
        path=(
            tmp_path
            / "artifacts"
            / "producer-artifact"
            / "producer"
            / "default"
            / "20-transform"
            / "geometry.dat"
        ),
    )

    resolver = create_product_dependency_fingerprint_resolver(
        producer_plan,
    )

    assert resolver(dependency) == fingerprints["transform"]


def test_product_dependency_fingerprint_does_not_use_downstream_stage(
    tmp_path: Path,
    test_resolver,
) -> None:
    """
    Intermediate-product provenance is independent of downstream stages.
    """

    producer_plan = _producer_product_plan(
        tmp_path=tmp_path,
        resolver=test_resolver,
    )

    fingerprints = create_required_fingerprints(
        producer_plan,
    )

    dependency = PlannedProductDependency(
        binding=ProductDependencyBinding(
            dependency=ProductDependencySpec(
                model="producer",
                stage="transform",
                product="geometry",
            ),
            artifact="producer-artifact",
            realization="default",
        ),
        path=(
            tmp_path
            / "artifacts"
            / "producer-artifact"
            / "producer"
            / "default"
            / "20-transform"
            / "geometry.dat"
        ),
    )

    resolver = create_product_dependency_fingerprint_resolver(
        producer_plan,
    )

    resolved = resolver(
        dependency,
    )

    assert resolved == fingerprints["transform"]
    assert resolved != fingerprints["package"]


def test_product_dependency_fingerprint_includes_upstream_context(
    tmp_path: Path,
    test_resolver,
) -> None:
    """
    Intermediate-product provenance includes prerequisite-stage provenance.
    """

    producer_plan = _producer_product_plan(
        tmp_path=tmp_path,
        resolver=test_resolver,
    )

    first = create_product_dependency_fingerprint_resolver(
        producer_plan,
    )

    dependency = PlannedProductDependency(
        binding=ProductDependencyBinding(
            dependency=ProductDependencySpec(
                model="producer",
                stage="transform",
                product="geometry",
            ),
            artifact="producer-artifact",
            realization="default",
        ),
        path=(
            tmp_path
            / "artifacts"
            / "producer-artifact"
            / "producer"
            / "default"
            / "20-transform"
            / "geometry.dat"
        ),
    )

    first_fingerprint = first(
        dependency,
    )

    prepare = producer_plan.stages[0]

    changed_prepare_spec = StageSpec(
        id=prepare.spec.id,
        name=prepare.spec.name,
        parameters=("changed_parameter",),
        products=prepare.spec.products,
    )

    object.__setattr__(
        prepare,
        "spec",
        changed_prepare_spec,
    )

    original_resolver = producer_plan.resolver

    def changed_resolver(
        name: str,
    ) -> object:
        if name == "changed_parameter":
            return "changed"

        return original_resolver(
            name,
        )

    object.__setattr__(
        producer_plan,
        "resolver",
        changed_resolver,
    )

    second = create_product_dependency_fingerprint_resolver(
        producer_plan,
    )

    assert second(dependency) != first_fingerprint


def test_current_intermediate_product_dependency_uses_producer_plan_fingerprint(
    tmp_path: Path,
    test_resolver,
) -> None:
    """
    Producer-plan provenance proves an intermediate dependency reusable.
    """

    producer_plan = _producer_product_plan(
        tmp_path=tmp_path,
        resolver=test_resolver,
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

    consumer_plan = _product_dependency_plan(
        tmp_path=tmp_path,
        resolver=test_resolver,
        dependency_path=dependency_path,
    )

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

    planned_dependency = PlannedProductDependency(
        binding=binding,
        path=dependency_path,
    )

    object.__setattr__(
        consumer_plan,
        "product_dependencies",
        (dependency,),
    )

    object.__setattr__(
        consumer_plan,
        "product_dependency_bindings",
        (binding,),
    )

    object.__setattr__(
        consumer_plan,
        "planned_product_dependencies",
        (planned_dependency,),
    )

    consumer_stage = consumer_plan.stages[0]

    object.__setattr__(
        consumer_stage,
        "spec",
        StageSpec(
            id=consumer_stage.spec.id,
            name=consumer_stage.spec.name,
            product_dependencies=(dependency,),
        ),
    )

    producer_fingerprints = create_required_fingerprints(
        producer_plan,
    )

    dependency_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    dependency_path.write_bytes(
        b"producer-geometry",
    )

    write_stage_completion(
        dependency_path.parent,
        StageCompletion(
            artifact_id="producer-artifact",
            model_name="producer",
            realization="default",
            stage_name="transform",
            products=("geometry",),
            fingerprint=producer_fingerprints["transform"],
        ),
    )

    fingerprint_resolver = create_product_dependency_fingerprint_resolver(
        producer_plan,
    )

    execution_plan = plan_incremental_execution(
        consumer_plan,
        product_dependency_fingerprint=fingerprint_resolver,
    )

    assert execution_plan.product_dependencies[0].state is ProductState.CURRENT
    assert execution_plan.required_product_dependencies == ()
    assert _stage_names(execution_plan.stages) == ("consume",)
