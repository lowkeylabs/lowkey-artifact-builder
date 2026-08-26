"""
Tests for planned stage context construction.

Planned context construction adapts an already-realized BuildPlan and
one of its PlannedStage instances to the established StageContext
execution boundary.

The BuildPlan remains authoritative for resolved configuration,
filesystem locations, realization identity, and selected stage
structure. Planned context construction therefore does not resolve
artifact configuration again or recompute canonical product locations.

Explicit stage inputs use their artifact-owned PlannedInput paths.
Products supplied by direct dependency stages use qualified semantic
names of the form '<stage>.<product>'.

These tests exercise context adaptation only. They do not materialize
external inputs, validate filesystem readiness, execute stages, or
modify persistent products.
"""
# File: tests/engine/test_planned_context.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from lowkey_artifact_builder.engine import (
    BuildPlan,
    PlannedProductDependency,
    PlannedStage,
    StageContext,
    StageContextError,
    create_planned_stage_context,
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


def _stage_by_name(
    build_plan: BuildPlan,
    stage_name: str,
) -> PlannedStage:
    """
    Return one realized stage by name.
    """

    return next(stage for stage in build_plan.stages if stage.name == stage_name)


def _first_stage_with_inputs(
    build_plan: BuildPlan,
) -> PlannedStage:
    """
    Return the first realized stage with an explicit external input.
    """

    for stage in build_plan.stages:
        if stage.inputs:
            return stage

    raise AssertionError("Artwork build plan contains no stage with external inputs.")


def _first_stage_with_products(
    build_plan: BuildPlan,
) -> PlannedStage:
    """
    Return the first realized stage declaring persistent products.
    """

    for stage in build_plan.stages:
        if stage.products:
            return stage

    raise AssertionError("Artwork build plan contains no stage with persistent products.")


def _first_stage_with_dependencies(
    build_plan: BuildPlan,
) -> PlannedStage:
    """
    Return the first realized stage with a direct dependency.
    """

    for stage in build_plan.stages:
        if stage.dependencies:
            return stage

    raise AssertionError("Artwork build plan contains no stage with dependencies.")


# =========================================================
# Context identity
# =========================================================


def test_create_planned_stage_context_returns_stage_context(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Planned context construction returns the engine execution context.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    stage = build_plan.stages[0]

    context = create_planned_stage_context(
        build_plan,
        stage,
    )

    assert isinstance(
        context,
        StageContext,
    )


def test_create_planned_stage_context_preserves_identity(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Planned context construction preserves build and stage identity.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    stage = build_plan.stages[0]

    context = create_planned_stage_context(
        build_plan,
        stage,
    )

    assert context.artifact_id == build_plan.artifact_id
    assert context.model_name == build_plan.model_name
    assert context.stage_name == stage.name


def test_create_planned_stage_context_retains_build_resolver(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Planned execution uses the BuildPlan's authoritative Resolver.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    stage = build_plan.stages[0]

    context = create_planned_stage_context(
        build_plan,
        stage,
    )

    assert context.resolver is build_plan.resolver


# =========================================================
# Filesystem identity
# =========================================================


def test_create_planned_stage_context_preserves_build_directories(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Planned context uses filesystem identity already resolved by the plan.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    stage = build_plan.stages[0]

    context = create_planned_stage_context(
        build_plan,
        stage,
    )

    assert context.project_root == build_plan.project_root
    assert context.artifact_dir == build_plan.artifact_dir


def test_create_planned_stage_context_uses_product_working_directory(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    A persistent stage executes from its realized product directory.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    stage = _first_stage_with_products(
        build_plan,
    )

    context = create_planned_stage_context(
        build_plan,
        stage,
    )

    parents = {product.path.parent for product in stage.products}

    assert len(parents) == 1
    assert context.working_dir == next(iter(parents))


# =========================================================
# Explicit inputs
# =========================================================


def test_create_planned_stage_context_uses_planned_input_path(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Explicit inputs use artifact-owned PlannedInput paths.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    stage = _first_stage_with_inputs(
        build_plan,
    )

    context = create_planned_stage_context(
        build_plan,
        stage,
    )

    for planned_input in stage.inputs:
        assert context.inputs[planned_input.name] == planned_input.path


def test_create_planned_stage_context_does_not_use_source_path(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    StageContext exposes materialized artifact inputs, not external sources.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    stage = _first_stage_with_inputs(
        build_plan,
    )

    context = create_planned_stage_context(
        build_plan,
        stage,
    )

    for planned_input in stage.inputs:
        assert context.inputs[planned_input.name] != planned_input.source_path


# =========================================================
# Dependency products
# =========================================================


def test_create_planned_stage_context_exposes_direct_dependency_products(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Direct dependency products are exposed using qualified input names.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    stage = _first_stage_with_dependencies(
        build_plan,
    )

    context = create_planned_stage_context(
        build_plan,
        stage,
    )

    stages = {candidate.name: candidate for candidate in build_plan.stages}

    for dependency_name in stage.dependencies:
        dependency = stages[dependency_name]

        for product in dependency.products:
            qualified_name = f"{dependency.name}.{product.name}"

            assert context.inputs[qualified_name] == product.path


def test_create_planned_stage_context_exposes_only_direct_dependencies(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Transitive dependency products are not added to StageContext.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    stage = _stage_by_name(
        build_plan,
        "vector",
    )

    context = create_planned_stage_context(
        build_plan,
        stage,
    )

    direct_dependencies = set(
        stage.dependencies,
    )

    for candidate in build_plan.stages:
        if candidate.name in direct_dependencies:
            continue

        for product in candidate.products:
            qualified_name = f"{candidate.name}.{product.name}"

            assert qualified_name not in context.inputs


def test_create_planned_stage_context_exposes_product_dependency(
    tmp_path: Path,
    test_resolver,
) -> None:
    """
    A bound cross-artifact product dependency is exposed as a stage input.

    The BuildPlan owns the already-materialized dependency path. Planned
    context construction exposes that path without resolving the producer
    artifact again.
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
    )

    stage = PlannedStage(
        spec=stage_spec,
    )

    plan = BuildPlan(
        artifact_id="consumer-artifact",
        model=ModelSpec(
            name="consumer",
            title="Consumer",
            stages=(stage_spec,),
        ),
        realization_name="default",
        resolver=test_resolver,
        project_root=tmp_path,
        artifact_dir=tmp_path / "artifacts" / "consumer-artifact",
        stages=(stage,),
        product_dependencies=(dependency,),
        product_dependency_bindings=(binding,),
        planned_product_dependencies=(planned_dependency,),
    )

    context = create_planned_stage_context(
        plan,
        stage,
    )

    assert context.inputs["producer.prepare.geometry"] == dependency_path


# =========================================================
# Outputs
# =========================================================


def test_create_planned_stage_context_uses_planned_product_paths(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Outputs use filesystem locations already resolved by BuildPlan.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    stage = _first_stage_with_products(
        build_plan,
    )

    context = create_planned_stage_context(
        build_plan,
        stage,
    )

    assert context.outputs == {product.name: product.path for product in stage.products}


def test_create_planned_stage_context_preserves_final_artifact_path(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Final artifact output remains exactly the planned product path.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    stage = _stage_by_name(
        build_plan,
        "package",
    )

    context = create_planned_stage_context(
        build_plan,
        stage,
    )

    artifact = next(product for product in stage.products if product.name == "artifact")

    assert context.outputs["artifact"] == artifact.path


# =========================================================
# Plan authority
# =========================================================


def test_create_planned_stage_context_does_not_resolve_configuration_again(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Planned context construction does not perform configuration resolution.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    stage = build_plan.stages[0]

    def fail(
        *args,
        **kwargs,
    ):
        raise AssertionError("Planned context must not resolve configuration again.")

    monkeypatch.setattr(
        "lowkey_artifact_builder.engine.context.get_resolver",
        fail,
    )

    context = create_planned_stage_context(
        build_plan,
        stage,
    )

    assert context.resolver is build_plan.resolver


def test_create_planned_stage_context_does_not_recompute_product_paths(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Planned context construction consumes already-realized product paths.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    stage = _first_stage_with_products(
        build_plan,
    )

    def fail(
        *args,
        **kwargs,
    ):
        raise AssertionError("Planned context must not recompute product paths.")

    monkeypatch.setattr(
        "lowkey_artifact_builder.engine.context.ProductResolver.product_path",
        fail,
    )

    context = create_planned_stage_context(
        build_plan,
        stage,
    )

    assert context.outputs == {product.name: product.path for product in stage.products}


# =========================================================
# Construction side effects
# =========================================================


def test_create_planned_stage_context_does_not_modify_filesystem(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Adapting a planned stage to StageContext is side-effect free.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    stage = build_plan.stages[0]

    assert not build_plan.artifact_dir.exists()

    create_planned_stage_context(
        build_plan,
        stage,
    )

    assert not build_plan.artifact_dir.exists()


# =========================================================
# Validation
# =========================================================


def test_create_planned_stage_context_rejects_foreign_stage(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    A PlannedStage must belong to the supplied BuildPlan.
    """

    first_plan = artwork_plan(
        tmp_path / "first",
        monkeypatch,
    )

    second_plan = artwork_plan(
        tmp_path / "second",
        monkeypatch,
    )

    foreign_stage = second_plan.stages[0]

    with pytest.raises(
        StageContextError,
        match="[Ss]tage",
    ):
        create_planned_stage_context(
            first_plan,
            foreign_stage,
        )


# =========================================================
# Representative contexts
# =========================================================


@pytest.mark.parametrize(
    "stage_name",
    [
        "prepare",
        "raster",
        "vector",
        "extrude",
        "package",
    ],
)
def test_create_planned_stage_context_matches_plan(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    stage_name: str,
) -> None:
    """
    Every representative artwork stage is adapted directly from its plan.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    stage = _stage_by_name(
        build_plan,
        stage_name,
    )

    context = create_planned_stage_context(
        build_plan,
        stage,
    )

    assert context.artifact_id == build_plan.artifact_id
    assert context.model_name == build_plan.model_name
    assert context.stage_name == stage.name
    assert context.project_root == build_plan.project_root
    assert context.artifact_dir == build_plan.artifact_dir
    assert context.resolver is build_plan.resolver

    for planned_input in stage.inputs:
        assert context.inputs[planned_input.name] == planned_input.path

    assert context.outputs == {product.name: product.path for product in stage.products}


def test_create_planned_stage_context_matches_plan_for_every_stage(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Every realized stage can be adapted to the execution-facing context.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    stages = {stage.name: stage for stage in build_plan.stages}

    for stage in build_plan.stages:
        context = create_planned_stage_context(
            build_plan,
            stage,
        )

        assert context.artifact_id == build_plan.artifact_id
        assert context.model_name == build_plan.model_name
        assert context.stage_name == stage.name
        assert context.project_root == build_plan.project_root
        assert context.artifact_dir == build_plan.artifact_dir
        assert context.resolver is build_plan.resolver

        expected_inputs = {planned_input.name: planned_input.path for planned_input in stage.inputs}

        for dependency_name in stage.dependencies:
            dependency = stages[dependency_name]

            for product in dependency.products:
                expected_inputs[f"{dependency.name}.{product.name}"] = product.path

        assert context.inputs == expected_inputs

        assert context.outputs == {product.name: product.path for product in stage.products}
