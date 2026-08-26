"""
End-to-end acceptance tests for cross-artifact product dependencies.

These tests verify the complete configured workflow in which one artifact
consumes a persistent product produced by another artifact.

The producer and consumer use small synthetic models so the acceptance
boundary isolates cross-artifact planning, configuration binding,
dependency-aware execution, persistent products, and incremental reuse
without repeating the comparatively expensive PNG-to-3MF workflow.

The important invariant is that the consumer does not begin from the
producer's original source. It begins from a persistent product belonging
to the producer artifact.
"""
# File: tests/acceptance/test_cross_artifact_dependency.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path

import pytest

from lowkey_artifact_builder.config import (
    write_artifact_config,
)
from lowkey_artifact_builder.engine import (
    BuildPlan,
    StageContext,
    create_build_plans,
    execute_dependency_build,
)
from lowkey_artifact_builder.model import (
    ModelRegistry,
    ModelSpec,
    ProductDependencySpec,
    ProductRef,
    ProductSpec,
    StageSpec,
)

# =========================================================
# Synthetic acceptance models
# =========================================================


def _producer_model() -> ModelSpec:
    """
    Return a producer whose intermediate geometry is externally consumable.

    The final package stage deliberately follows the geometry stage so the
    dependency build can demonstrate product-targeted producer execution:
    satisfying the consumer must not require the producer's unrelated final
    package product.
    """

    return ModelSpec(
        name="producer",
        title="Acceptance Producer",
        stages=(
            StageSpec(
                id=10,
                name="prepare",
                products=(
                    ProductSpec(
                        name="prepared",
                        path="prepared.dat",
                    ),
                ),
            ),
            StageSpec(
                id=20,
                name="transform",
                dependencies=("prepare",),
                products=(
                    ProductSpec(
                        name="geometry",
                        path="geometry.dat",
                    ),
                ),
            ),
            StageSpec(
                id=30,
                name="package",
                dependencies=("transform",),
                products=(
                    ProductSpec(
                        name="artifact",
                        path="artifact.dat",
                    ),
                ),
            ),
        ),
    )


def _consumer_model() -> ModelSpec:
    """
    Return a consumer whose only source material is producer geometry.
    """

    dependency = ProductDependencySpec(
        model="producer",
        stage="transform",
        product="geometry",
    )

    return ModelSpec(
        name="consumer",
        title="Acceptance Consumer",
        stages=(
            StageSpec(
                id=10,
                name="consume",
                product_dependencies=(dependency,),
                products=(
                    ProductSpec(
                        name="artifact",
                        path="artifact.dat",
                    ),
                ),
            ),
        ),
    )


def _model_registry() -> ModelRegistry:
    """
    Return the model registry used by the isolated acceptance project.
    """

    registry = ModelRegistry()

    registry.register_model(
        _producer_model(),
    )

    registry.register_model(
        _consumer_model(),
    )

    return registry


# =========================================================
# Synthetic stage implementations
# =========================================================


def _prepare(
    context: StageContext,
) -> None:
    """
    Produce the producer's first persistent product.
    """

    context.output("prepared").write_text(
        "prepared source\n",
        encoding="utf-8",
    )


def _transform(
    context: StageContext,
) -> None:
    """
    Transform the producer's prepared product into reusable geometry.
    """

    prepared = context.input(
        "prepare.prepared",
    ).read_text(
        encoding="utf-8",
    )

    context.output("geometry").write_text(
        f"{prepared.strip()} -> reusable geometry\n",
        encoding="utf-8",
    )


def _package(
    context: StageContext,
) -> None:
    """
    Produce the producer's unrelated final artifact.

    Dependency-targeted producer execution should not need this stage.
    """

    geometry = context.input(
        "transform.geometry",
    ).read_text(
        encoding="utf-8",
    )

    context.output("artifact").write_text(
        f"{geometry.strip()} -> producer package\n",
        encoding="utf-8",
    )


def _consume(
    context: StageContext,
) -> None:
    """
    Produce the consumer artifact from the producer's persistent geometry.
    """

    geometry = context.input(
        "producer.transform.geometry",
    ).read_text(
        encoding="utf-8",
    )

    context.output("artifact").write_text(
        f"{geometry.strip()} -> consumer artifact\n",
        encoding="utf-8",
    )


def _register_stage_implementations(
    registry,
) -> None:
    """
    Register executable implementations for the synthetic models.
    """

    registry.register(
        "producer",
        "prepare",
        _prepare,
    )

    registry.register(
        "producer",
        "transform",
        _transform,
    )

    registry.register(
        "producer",
        "package",
        _package,
    )

    registry.register(
        "consumer",
        "consume",
        _consume,
    )


# =========================================================
# Acceptance project configuration
# =========================================================


def _configure_project(
    *,
    project_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Configure producer and consumer artifacts in an isolated project.

    The acceptance models are synthetic definition-layer models and therefore
    do not have installed model implementation packages. Their parameter and
    derivation configuration is empty.

    The consumer binds its declarative geometry dependency to the concrete
    producer artifact and realization.
    """

    registry = _model_registry()

    monkeypatch.setattr(
        "lowkey_artifact_builder.config.config.build_model_registry",
        lambda: registry,
    )

    monkeypatch.setattr(
        "lowkey_artifact_builder.engine.plan.build_model_registry",
        lambda: registry,
    )

    monkeypatch.setattr(
        "lowkey_artifact_builder.config.config._load_model_parameters",
        lambda model: {},
    )

    monkeypatch.setattr(
        "lowkey_artifact_builder.config.config._load_model_derivations",
        lambda model: {},
    )

    monkeypatch.setattr(
        "lowkey_artifact_builder.engine.stage.register_stage_implementations",
        _register_stage_implementations,
        raising=False,
    )

    monkeypatch.setattr(
        "lowkey_artifact_builder.engine.bootstrap.register_stage_implementations",
        _register_stage_implementations,
    )

    write_artifact_config(
        "producer-artifact",
        {
            "model": "producer",
        },
        project_root=project_root,
    )

    write_artifact_config(
        "consumer-artifact",
        {
            "model": "consumer",
            "product_dependencies": {
                "geometry": {
                    "model": "producer",
                    "stage": "transform",
                    "product": "geometry",
                    "artifact": "producer-artifact",
                    "realization": "default",
                },
            },
        },
        project_root=project_root,
    )


def _consumer_plan(
    project_root: Path,
) -> BuildPlan:
    """
    Return the configured consumer BuildPlan targeted to its artifact product.

    Targeted planning constructs the realization graph and therefore includes
    the declarative cross-artifact product dependencies required by the target
    producer closure.
    """

    target = ProductRef(
        artifact="consumer-artifact",
        model="consumer",
        realization="default",
        stage="consume",
        product="artifact",
    )

    plans = create_build_plans(
        "consumer-artifact",
        project_root=project_root,
        targets=(target,),
    )

    assert len(plans) == 1

    plan = plans[0]

    assert plan.artifact_id == "consumer-artifact"
    assert plan.model_name == "consumer"
    assert plan.realization_name == "default"

    return plan


def _product_path(
    plan: BuildPlan,
    *,
    stage_name: str,
    product_name: str,
) -> Path:
    """
    Return one persistent product path from a realized BuildPlan.
    """

    stage = next(stage for stage in plan.stages if stage.name == stage_name)

    product = next(product for product in stage.products if product.name == product_name)

    return product.path


# =========================================================
# Cross-artifact dependency acceptance
# =========================================================


def test_consumer_builds_required_producer_product_automatically(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Building B automatically builds the product it requires from A.

    The consumer is requested directly. The producer has not previously
    been built.

    Dependency-aware execution must therefore:

        1. discover the configured producer binding,
        2. target the required producer product,
        3. execute the producer prerequisite closure,
        4. replan the consumer,
        5. execute the consumer from that persistent product.
    """

    project_root = tmp_path

    _configure_project(
        project_root=project_root,
        monkeypatch=monkeypatch,
    )

    consumer = _consumer_plan(
        project_root,
    )

    dependency = consumer.planned_product_dependencies

    assert len(dependency) == 1

    producer_geometry = dependency[0].path

    assert not producer_geometry.exists()

    execution = execute_dependency_build(
        consumer,
    )

    assert execution.required_stages

    assert producer_geometry.is_file()

    consumer_output = _product_path(
        consumer,
        stage_name="consume",
        product_name="artifact",
    )

    assert consumer_output.is_file()

    assert consumer_output.read_text(
        encoding="utf-8",
    ) == ("prepared source -> reusable geometry -> consumer artifact\n")


def test_dependency_build_targets_only_required_producer_product(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    A consumer dependency does not force a complete producer build.

    The consumer requires producer/transform/geometry. Producer/package is
    downstream of that product and must therefore remain unexecuted.
    """

    project_root = tmp_path

    _configure_project(
        project_root=project_root,
        monkeypatch=monkeypatch,
    )

    consumer = _consumer_plan(
        project_root,
    )

    execute_dependency_build(
        consumer,
    )

    producer_plans = create_build_plans(
        "producer-artifact",
        project_root=project_root,
    )

    assert len(producer_plans) == 1

    producer = producer_plans[0]

    prepared = _product_path(
        producer,
        stage_name="prepare",
        product_name="prepared",
    )

    geometry = _product_path(
        producer,
        stage_name="transform",
        product_name="geometry",
    )

    package = _product_path(
        producer,
        stage_name="package",
        product_name="artifact",
    )

    assert prepared.is_file()
    assert geometry.is_file()

    assert not package.exists()


def test_completed_cross_artifact_build_is_fully_reusable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    A completed producer/consumer graph converges to no required work.

    The second dependency-aware build reuses both the producer product and
    the consumer product rather than executing either artifact again.
    """

    project_root = tmp_path

    _configure_project(
        project_root=project_root,
        monkeypatch=monkeypatch,
    )

    consumer = _consumer_plan(
        project_root,
    )

    first = execute_dependency_build(
        consumer,
    )

    assert first.required_stages

    producer_geometry = consumer.planned_product_dependencies[0].path

    consumer_output = _product_path(
        consumer,
        stage_name="consume",
        product_name="artifact",
    )

    assert producer_geometry.is_file()
    assert consumer_output.is_file()

    producer_mtime = producer_geometry.stat().st_mtime_ns
    consumer_mtime = consumer_output.stat().st_mtime_ns

    second = execute_dependency_build(
        consumer,
    )

    assert second.required_stages == ()
    assert second.required_product_dependencies == ()

    assert producer_geometry.stat().st_mtime_ns == producer_mtime
    assert consumer_output.stat().st_mtime_ns == consumer_mtime
