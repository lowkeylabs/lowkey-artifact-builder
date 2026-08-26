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
    PlannedProductDependency,
    PlannedProductDependencyExecution,
    PlannedStage,
    PlannedStageExecution,
    ProductFingerprint,
    ProductState,
    StageCompletion,
    create_required_fingerprints,
    plan_incremental_execution,
    write_stage_completion,
)
from lowkey_artifact_builder.model import (
    ModelSpec,
    ProductDependencyBinding,
    ProductDependencySpec,
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

    stage = PlannedStage(
        spec=stage_spec,
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
