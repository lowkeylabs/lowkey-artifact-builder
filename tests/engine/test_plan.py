"""
Tests for artifact build planning.

These tests verify construction of concrete build plans from configured
artifacts and declarative model specifications.
"""
# File: tests/engine/test_plan.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path

import pytest

from lowkey_artifact_builder.config import write_artifact_config
from lowkey_artifact_builder.engine import (
    BuildPlan,
    BuildPlanError,
    create_build_plan,
    create_build_plans,
)
from lowkey_artifact_builder.model import (
    ModelSpec,
    ProductDependencySpec,
    ProductRef,
    ProductSpec,
    StageSpec,
    VariantSpec,
)

# =========================================================
# Build planning
# =========================================================


def test_create_build_plan_for_artwork(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    artwork_plan,
) -> None:
    """
    A configured artwork artifact produces the complete artwork build
    workflow in declared stage order.
    """

    plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    assert isinstance(
        plan,
        BuildPlan,
    )

    assert plan.artifact_id == "example"
    assert plan.model_name == "artwork"
    assert plan.project_root == tmp_path
    assert plan.artifact_dir == (tmp_path / "artifacts" / "example")

    assert tuple(stage.name for stage in plan.stages) == (
        "prepare",
        "raster",
        "vector",
        "extrude",
        "package",
    )


def test_create_build_plan_retains_resolver(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    artwork_plan,
) -> None:
    """
    A build plan retains the artifact-specific configuration resolver.

    Stage parameter declarations remain on StageSpec while their
    effective values and provenance come from the shared resolver.
    """

    plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    prepare = plan.stages[0]

    assert prepare.name == "prepare"

    assert prepare.spec.parameters == ("artwork_colors",)

    assert plan.resolver("artwork_colors") == [
        "white",
        "black",
    ]

    assert plan.resolver.source("artwork_colors") == "test"


def test_create_build_plan_resolves_external_input(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    artwork_plan,
) -> None:
    """
    Planning resolves external filesystem inputs to both their original
    source and artifact-owned materialization paths.
    """

    plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    prepare = plan.stages[0]

    assert len(prepare.inputs) == 1

    source = prepare.inputs[0]

    assert source.name == "source"

    assert source.source_path == (tmp_path / "source.png")

    assert source.path == (plan.artifact_dir / "artifact.png")


def test_create_build_plan_materializes_product_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    artwork_plan,
) -> None:
    """
    Declarative products are materialized using the canonical
    artifact/model/realization/stage hierarchy.
    """

    plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    products = {
        stage.name: tuple(product.path for product in stage.products) for stage in plan.stages
    }

    artifact_dir = tmp_path / "artifacts" / "example"

    assert products == {
        "prepare": (
            artifact_dir / "artwork" / "default" / "10-prepare" / "trace.svg",
            artifact_dir / "artwork" / "default" / "10-prepare" / "envelope.svg",
        ),
        "raster": (artifact_dir / "artwork" / "default" / "20-raster" / "products.json",),
        "vector": (artifact_dir / "artwork" / "default" / "30-vector" / "products.json",),
        "extrude": (artifact_dir / "artwork" / "default" / "40-extrude" / "products.json",),
        "package": (artifact_dir / "artwork" / "default" / "50-package" / "artifact.3mf",),
    }


def test_create_build_plan_preserves_dependencies(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    artwork_plan,
) -> None:
    """
    Planned stages preserve their declared workflow dependencies.
    """

    plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    dependencies = {stage.name: stage.dependencies for stage in plan.stages}

    assert dependencies == {
        "prepare": (),
        "raster": ("prepare",),
        "vector": ("raster",),
        "extrude": ("vector",),
        "package": ("extrude",),
    }


# =========================================================
# Planning side effects
# =========================================================


def test_create_build_plan_does_not_create_artifact_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    artwork_plan,
) -> None:
    """
    Planning is read-only and does not create the artifact working
    directory or materialize external inputs.
    """

    plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    assert not plan.artifact_dir.exists()

    assert not (plan.artifact_dir / "artifact.png").exists()


# =========================================================
# Invalid models
# =========================================================


def test_create_build_plan_rejects_unknown_model(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Planning fails when an artifact references a model that is not
    registered.
    """

    class Resolver:
        def __call__(
            self,
            name: str,
        ):
            values = {
                "model": "does-not-exist",
                "realization": "default",
            }

            return values[name]

        def source(
            self,
            name: str,
        ) -> str:
            return "test"

    monkeypatch.setattr(
        "lowkey_artifact_builder.engine.plan.get_resolver",
        lambda artifact_id, *, realization=None, project_root: Resolver(),
    )

    with pytest.raises(
        BuildPlanError,
        match="unknown model",
    ):
        create_build_plan(
            "example",
            project_root=tmp_path,
        )


# =========================================================
# Realization identity
# =========================================================


def test_build_plan_has_default_realization(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    artwork_plan,
) -> None:
    """
    A planned artifact has an explicit realization identity.

    Until artifact configuration supports named realizations, the
    existing single-realization behavior is represented by the
    realization named "default".
    """

    plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    assert plan.realization_name == "default"


def test_default_realization_owns_planned_products(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    artwork_plan,
) -> None:
    """
    Planned products are stored beneath the BuildPlan realization.

    This characterizes the relationship between realization identity
    and canonical product storage without yet introducing configurable
    realization names.
    """

    plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    realization_directory = plan.artifact_dir / plan.model_name / plan.realization_name

    assert plan.realization_name == "default"

    for stage in plan.stages:
        stage_directory = realization_directory / f"{stage.spec.id:02d}-{stage.name}"

        for product in stage.products:
            assert product.path == (stage_directory / product.spec.path)


def test_variant_identity_is_distinct_from_realization_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Selecting a named variant does not rename the realization.

    A variant is a reusable model-scoped parameter preset. A realization
    is one configured invocation of that model. Multiple realizations may
    use the same variant, so their identities must not be conflated.
    """

    from lowkey_artifact_builder.model import (
        ModelSpec,
        VariantSpec,
    )

    model = ModelSpec(
        name="example-model",
        title="Example Model",
        variants=(
            VariantSpec(
                name="default",
            ),
            VariantSpec(
                name="ridged",
                parameters={
                    "ridge": True,
                },
            ),
        ),
    )

    class StubRegistry:
        def get_model(
            self,
            name: str,
        ) -> ModelSpec:
            assert name == "example-model"

            return model

    class Resolver:
        def __call__(
            self,
            name: str,
        ):
            values = {
                "model": "example-model",
                "variant": "ridged",
                "realization": "default",
            }

            return values[name]

        def source(
            self,
            name: str,
        ) -> str:
            return "test"

    monkeypatch.setattr(
        "lowkey_artifact_builder.engine.plan.get_resolver",
        lambda artifact_id, *, realization=None, project_root: Resolver(),
    )

    monkeypatch.setattr(
        "lowkey_artifact_builder.engine.plan.build_model_registry",
        lambda: StubRegistry(),
    )

    plan = create_build_plan(
        "example",
        project_root=tmp_path,
    )

    assert plan.resolver("variant") == "ridged"
    assert plan.realization_name == "default"


def test_create_build_plan_selects_named_realization(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Build planning selects the explicitly requested artifact realization.

    The resulting BuildPlan retains that realization identity and uses
    the resolver belonging to the selected realization.
    """

    model = ModelSpec(
        name="example-model",
        title="Example Model",
        variants=(
            VariantSpec(
                name="default",
            ),
            VariantSpec(
                name="ridged",
                parameters={
                    "ridge": True,
                    "ridge_width": 3.0,
                    "ridge_raise": 1.0,
                },
            ),
        ),
    )

    class StubRegistry:
        def get_model(
            self,
            name: str,
        ) -> ModelSpec:
            assert name == model.name

            return model

    class Resolver:
        def __call__(
            self,
            name: str,
        ):
            values = {
                "model": model.name,
                "variant": "ridged",
                "realization": "ornament",
                "ridge": True,
                "ridge_width": 2.0,
                "ridge_raise": 0.75,
            }

            return values[name]

        def source(
            self,
            name: str,
        ) -> str:
            return "test"

    requested: list[str | None] = []

    def fake_get_resolver(
        artifact_id: str,
        *,
        realization: str | None = None,
        project_root: Path,
    ) -> Resolver:
        assert artifact_id == "example"

        requested.append(realization)

        return Resolver()

    monkeypatch.setattr(
        "lowkey_artifact_builder.engine.plan.get_resolver",
        fake_get_resolver,
    )

    monkeypatch.setattr(
        "lowkey_artifact_builder.engine.plan.build_model_registry",
        lambda: StubRegistry(),
    )

    plan = create_build_plan(
        "example",
        realization="ornament",
        project_root=tmp_path,
    )

    assert requested == ["ornament"]

    assert plan.realization_name == "ornament"

    assert plan.resolver("realization") == "ornament"
    assert plan.resolver("model") == model.name
    assert plan.resolver("variant") == "ridged"

    assert plan.resolver("ridge") is True
    assert plan.resolver("ridge_width") == 2.0
    assert plan.resolver("ridge_raise") == 0.75


def test_named_realization_owns_planned_products(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Products planned for a named realization are stored beneath that
    realization's canonical product hierarchy.
    """

    model = ModelSpec(
        name="example-model",
        title="Example Model",
        stages=(
            StageSpec(
                id=10,
                name="prepare",
                products=(
                    ProductSpec(
                        name="trace",
                        path="trace.svg",
                    ),
                ),
            ),
        ),
    )

    class StubRegistry:
        def get_model(
            self,
            name: str,
        ) -> ModelSpec:
            assert name == model.name

            return model

    class Resolver:
        def __call__(
            self,
            name: str,
        ):
            values = {
                "model": model.name,
                "variant": "default",
                "realization": "ornament",
            }

            return values[name]

        def source(
            self,
            name: str,
        ) -> str:
            return "test"

    monkeypatch.setattr(
        "lowkey_artifact_builder.engine.plan.get_resolver",
        lambda artifact_id, *, realization=None, project_root: Resolver(),
    )

    monkeypatch.setattr(
        "lowkey_artifact_builder.engine.plan.build_model_registry",
        lambda: StubRegistry(),
    )

    plan = create_build_plan(
        "example",
        realization="ornament",
        project_root=tmp_path,
    )

    assert plan.realization_name == "ornament"

    assert plan.stages[0].products[0].path == (
        tmp_path
        / "artifacts"
        / "example"
        / "example-model"
        / "ornament"
        / "10-prepare"
        / "trace.svg"
    )


def test_default_build_plan_preserves_legacy_realization_selection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Planning without an explicit realization preserves the existing
    implicit-default behavior.

    The planner delegates realization selection to configuration rather
    than manufacturing realization identity independently.
    """

    model = ModelSpec(
        name="example-model",
        title="Example Model",
    )

    class StubRegistry:
        def get_model(
            self,
            name: str,
        ) -> ModelSpec:
            assert name == model.name

            return model

    class Resolver:
        def __call__(
            self,
            name: str,
        ):
            values = {
                "model": model.name,
                "variant": "default",
                "realization": "default",
            }

            return values[name]

        def source(
            self,
            name: str,
        ) -> str:
            return "test"

    requested: list[str | None] = []

    def fake_get_resolver(
        artifact_id: str,
        *,
        realization: str | None = None,
        project_root: Path,
    ) -> Resolver:
        requested.append(realization)

        return Resolver()

    monkeypatch.setattr(
        "lowkey_artifact_builder.engine.plan.get_resolver",
        fake_get_resolver,
    )

    monkeypatch.setattr(
        "lowkey_artifact_builder.engine.plan.build_model_registry",
        lambda: StubRegistry(),
    )

    plan = create_build_plan(
        "example",
        project_root=tmp_path,
    )

    assert requested == [None]

    assert plan.realization_name == "default"
    assert plan.resolver("realization") == "default"


def test_create_build_plan_uses_configured_named_realization(
    tmp_path: Path,
) -> None:
    """
    Build planning integrates with artifact realization configuration.

    Selecting a named realization resolves its model, variant, and
    parameter overrides through the real configuration subsystem and
    uses the realization identity for canonical product placement.
    """

    (tmp_path / "workspace.toml").write_text(
        """
[parameters]
artwork_size = 80.0
artwork_raise = 1.0
""".lstrip(),
        encoding="utf-8",
    )

    write_artifact_config(
        "example",
        {
            "realizations": {
                "ornament": {
                    "model": "artwork",
                    "variant": "default",
                    "source": "source.png",
                    "parameters": {
                        "artwork_size": 100.0,
                        "artwork_raise": 1.5,
                    },
                },
                "coaster": {
                    "model": "artwork",
                    "variant": "default",
                    "source": "source.png",
                    "parameters": {
                        "artwork_size": 90.0,
                        "artwork_raise": 0.8,
                    },
                },
            },
        },
        project_root=tmp_path,
    )

    plan = create_build_plan(
        "example",
        realization="ornament",
        project_root=tmp_path,
    )

    assert plan.artifact_id == "example"
    assert plan.model_name == "artwork"
    assert plan.realization_name == "ornament"

    assert plan.resolver("realization") == "ornament"
    assert plan.resolver("model") == "artwork"
    assert plan.resolver("variant") == "default"

    assert plan.resolver("artwork_size") == 100.0
    assert plan.resolver("artwork_raise") == 1.5

    realization_directory = tmp_path / "artifacts" / "example" / "artwork" / "ornament"

    assert plan.stages

    for stage in plan.stages:
        for product in stage.products:
            assert product.path.is_relative_to(realization_directory)


def test_named_realizations_produce_distinct_build_plans(
    tmp_path: Path,
) -> None:
    """
    Two realizations of the same artifact may use the same model while
    retaining independent configuration and product namespaces.
    """

    (tmp_path / "workspace.toml").write_text(
        """
[parameters]
artwork_raise = 1.0
""".lstrip(),
        encoding="utf-8",
    )

    write_artifact_config(
        "example",
        {
            "realizations": {
                "ornament": {
                    "model": "artwork",
                    "variant": "default",
                    "source": "source.png",
                    "parameters": {
                        "artwork_size": 100.0,
                    },
                },
                "coaster": {
                    "model": "artwork",
                    "variant": "default",
                    "source": "source.png",
                    "parameters": {
                        "artwork_size": 90.0,
                    },
                },
            },
        },
        project_root=tmp_path,
    )

    ornament = create_build_plan(
        "example",
        realization="ornament",
        project_root=tmp_path,
    )

    coaster = create_build_plan(
        "example",
        realization="coaster",
        project_root=tmp_path,
    )

    assert ornament.model_name == coaster.model_name == "artwork"

    assert ornament.realization_name == "ornament"
    assert coaster.realization_name == "coaster"

    assert ornament.resolver("artwork_size") == 100.0
    assert coaster.resolver("artwork_size") == 90.0

    ornament_products = {product.path for stage in ornament.stages for product in stage.products}

    coaster_products = {product.path for stage in coaster.stages for product in stage.products}

    assert ornament_products
    assert coaster_products

    assert ornament_products.isdisjoint(coaster_products)


def test_create_build_plans_plans_all_named_realizations(
    tmp_path: Path,
) -> None:
    """
    Artifact-level planning produces one BuildPlan for every explicitly
    configured realization.
    """

    (tmp_path / "workspace.toml").write_text(
        """
[parameters]
artwork_raise = 1.0
""".lstrip(),
        encoding="utf-8",
    )

    write_artifact_config(
        "example",
        {
            "source": "source.png",
            "realizations": {
                "ornament": {
                    "model": "artwork",
                    "variant": "default",
                    "parameters": {
                        "artwork_size": 100.0,
                    },
                },
                "coaster": {
                    "model": "artwork",
                    "variant": "default",
                    "parameters": {
                        "artwork_size": 90.0,
                    },
                },
            },
        },
        project_root=tmp_path,
    )

    plans = create_build_plans(
        "example",
        project_root=tmp_path,
    )

    assert tuple(plan.realization_name for plan in plans) == (
        "ornament",
        "coaster",
    )

    assert all(plan.artifact_id == "example" for plan in plans)

    assert all(plan.model_name == "artwork" for plan in plans)

    assert plans[0].resolver("source") == "source.png"
    assert plans[1].resolver("source") == "source.png"

    assert plans[0].resolver("artwork_size") == 100.0
    assert plans[1].resolver("artwork_size") == 90.0


def test_create_build_plans_preserves_implicit_default_realization(
    tmp_path: Path,
) -> None:
    """
    Legacy single-realization artifacts produce exactly one default
    BuildPlan through artifact-level planning.
    """

    (tmp_path / "workspace.toml").write_text(
        """
[parameters]
artwork_size = 20.0
artwork_raise = 1.0
""".lstrip(),
        encoding="utf-8",
    )

    write_artifact_config(
        "example",
        {
            "model": "artwork",
            "source": "source.png",
        },
        project_root=tmp_path,
    )

    plans = create_build_plans(
        "example",
        project_root=tmp_path,
    )

    assert len(plans) == 1

    plan = plans[0]

    assert plan.artifact_id == "example"
    assert plan.model_name == "artwork"
    assert plan.realization_name == "default"

    assert plan.resolver("source") == "source.png"


# =========================================================
# Product-targeted planning
# =========================================================


def test_create_build_plan_without_targets_is_complete_build(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    artwork_plan,
) -> None:
    """
    Planning without product targets preserves complete-build behavior.

    Phase 7 product targeting must not change the existing default
    behavior of planning every participating stage.
    """

    plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    assert plan.targets is None
    assert plan.targeted is False

    assert tuple(stage.name for stage in plan.stages) == (
        "prepare",
        "raster",
        "vector",
        "extrude",
        "package",
    )


def test_create_build_plan_targets_vector_product(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    artwork_plan,
) -> None:
    """
    Targeting a vector product plans only its dependency closure.

    Downstream extrude and package stages are excluded.
    """

    target = ProductRef(
        artifact="example",
        model="artwork",
        realization="default",
        stage="vector",
        product="manifest",
    )

    plan = artwork_plan(
        tmp_path,
        monkeypatch,
        targets=(target,),
    )

    assert plan.targets == (target,)

    assert plan.targeted is True

    assert tuple(stage.name for stage in plan.stages) == (
        "prepare",
        "raster",
        "vector",
    )


def test_create_build_plan_targets_intermediate_product(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    artwork_plan,
) -> None:
    """
    Any catalog product may serve as the endpoint of a build plan.
    """

    target = ProductRef(
        artifact="example",
        model="artwork",
        realization="default",
        stage="raster",
        product="manifest",
    )

    plan = artwork_plan(
        tmp_path,
        monkeypatch,
        targets=(target,),
    )

    assert tuple(stage.name for stage in plan.stages) == (
        "prepare",
        "raster",
    )


def test_create_build_plan_targets_final_product(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    artwork_plan,
) -> None:
    """
    Targeting the final artifact preserves the complete dependency chain.
    """

    target = ProductRef(
        artifact="example",
        model="artwork",
        realization="default",
        stage="package",
        product="artifact",
    )

    plan = artwork_plan(
        tmp_path,
        monkeypatch,
        targets=(target,),
    )

    assert plan.targets == (target,)

    assert tuple(stage.name for stage in plan.stages) == (
        "prepare",
        "raster",
        "vector",
        "extrude",
        "package",
    )


def test_create_build_plan_supports_multiple_targets(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    artwork_plan,
) -> None:
    """
    Multiple requested products produce the union of their dependencies.
    """

    raster = ProductRef(
        artifact="example",
        model="artwork",
        realization="default",
        stage="raster",
        product="manifest",
    )

    vector = ProductRef(
        artifact="example",
        model="artwork",
        realization="default",
        stage="vector",
        product="manifest",
    )

    plan = artwork_plan(
        tmp_path,
        monkeypatch,
        targets=(
            raster,
            vector,
        ),
    )

    assert plan.targets == (
        raster,
        vector,
    )

    assert tuple(stage.name for stage in plan.stages) == (
        "prepare",
        "raster",
        "vector",
    )


def test_create_build_plan_rejects_empty_target_set(
    tmp_path: Path,
) -> None:
    """
    Explicit targeted planning requires at least one target product.
    """

    with pytest.raises(
        BuildPlanError,
        match="at least one product",
    ):
        create_build_plan(
            "example",
            targets=(),
            project_root=tmp_path,
        )


def test_create_build_plan_rejects_unknown_target_product(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    artwork_plan,
) -> None:
    """
    A requested product must exist in the Product Catalog.
    """

    target = ProductRef(
        artifact="example",
        model="artwork",
        realization="default",
        stage="vector",
        product="missing",
    )

    with pytest.raises(
        BuildPlanError,
        match=("Unknown target product 'artwork/vector/missing'"),
    ):
        artwork_plan(
            tmp_path,
            monkeypatch,
            targets=(target,),
        )


def test_create_build_plan_rejects_target_for_other_artifact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    artwork_plan,
) -> None:
    """
    Product targets must belong to the artifact being planned.
    """

    target = ProductRef(
        artifact="other",
        model="artwork",
        realization="default",
        stage="vector",
        product="manifest",
    )

    with pytest.raises(
        BuildPlanError,
        match="does not match configured artifact",
    ):
        artwork_plan(
            tmp_path,
            monkeypatch,
            targets=(target,),
        )


def test_create_build_plan_rejects_target_for_other_model(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    artwork_plan,
) -> None:
    """
    Product targets must belong to the configured model.
    """

    target = ProductRef(
        artifact="example",
        model="other",
        realization="default",
        stage="vector",
        product="manifest",
    )

    with pytest.raises(
        BuildPlanError,
        match="does not match configured model",
    ):
        artwork_plan(
            tmp_path,
            monkeypatch,
            targets=(target,),
        )


def test_create_build_plan_rejects_target_for_other_realization(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    artwork_plan,
) -> None:
    """
    Product targets must belong to the selected realization.
    """

    target = ProductRef(
        artifact="example",
        model="artwork",
        realization="other",
        stage="vector",
        product="manifest",
    )

    with pytest.raises(
        BuildPlanError,
        match="does not match configured realization",
    ):
        artwork_plan(
            tmp_path,
            monkeypatch,
            targets=(target,),
        )


# =========================================================
# Product-targeted multi-realization planning
# =========================================================


def test_create_build_plans_routes_targets_to_realizations(
    tmp_path: Path,
) -> None:
    """
    Artifact-level targeted planning routes products to their realization.

    Only realizations containing requested products produce BuildPlans.
    """

    (tmp_path / "workspace.toml").write_text(
        """
[parameters]
artwork_raise = 1.0
""".lstrip(),
        encoding="utf-8",
    )

    write_artifact_config(
        "example",
        {
            "source": "source.png",
            "realizations": {
                "ornament": {
                    "model": "artwork",
                    "variant": "default",
                    "parameters": {
                        "artwork_size": 100.0,
                    },
                },
                "coaster": {
                    "model": "artwork",
                    "variant": "default",
                    "parameters": {
                        "artwork_size": 90.0,
                    },
                },
            },
        },
        project_root=tmp_path,
    )

    ornament_target = ProductRef(
        artifact="example",
        model="artwork",
        realization="ornament",
        stage="vector",
        product="manifest",
    )

    plans = create_build_plans(
        "example",
        targets=(ornament_target,),
        project_root=tmp_path,
    )

    assert len(plans) == 1

    plan = plans[0]

    assert plan.realization_name == "ornament"

    assert plan.targets == (ornament_target,)

    assert tuple(stage.name for stage in plan.stages) == (
        "prepare",
        "raster",
        "vector",
    )


def test_create_build_plans_routes_independent_target_closures(
    tmp_path: Path,
) -> None:
    """
    Each realization receives only its own requested dependency closure.
    """

    (tmp_path / "workspace.toml").write_text(
        """
[parameters]
artwork_raise = 1.0
""".lstrip(),
        encoding="utf-8",
    )

    write_artifact_config(
        "example",
        {
            "source": "source.png",
            "realizations": {
                "ornament": {
                    "model": "artwork",
                    "variant": "default",
                    "parameters": {
                        "artwork_size": 100.0,
                    },
                },
                "coaster": {
                    "model": "artwork",
                    "variant": "default",
                    "parameters": {
                        "artwork_size": 90.0,
                    },
                },
            },
        },
        project_root=tmp_path,
    )

    ornament_target = ProductRef(
        artifact="example",
        model="artwork",
        realization="ornament",
        stage="vector",
        product="manifest",
    )

    coaster_target = ProductRef(
        artifact="example",
        model="artwork",
        realization="coaster",
        stage="package",
        product="artifact",
    )

    plans = create_build_plans(
        "example",
        targets=(
            ornament_target,
            coaster_target,
        ),
        project_root=tmp_path,
    )

    assert tuple(plan.realization_name for plan in plans) == (
        "ornament",
        "coaster",
    )

    ornament, coaster = plans

    assert ornament.targets == (ornament_target,)

    assert tuple(stage.name for stage in ornament.stages) == (
        "prepare",
        "raster",
        "vector",
    )

    assert coaster.targets == (coaster_target,)

    assert tuple(stage.name for stage in coaster.stages) == (
        "prepare",
        "raster",
        "vector",
        "extrude",
        "package",
    )


def test_create_build_plans_rejects_target_for_other_artifact(
    tmp_path: Path,
) -> None:
    """
    Artifact-level targeted planning rejects foreign artifact targets.
    """

    target = ProductRef(
        artifact="other",
        model="artwork",
        realization="default",
        stage="vector",
        product="manifest",
    )

    with pytest.raises(
        BuildPlanError,
        match="does not match configured artifact",
    ):
        create_build_plans(
            "example",
            targets=(target,),
            project_root=tmp_path,
        )


def test_build_plan_preserves_product_dependencies() -> None:
    """
    A build plan retains declarative product dependencies required by
    its selected realization graph.
    """

    dependency = ProductDependencySpec(
        model="producer",
        stage="prepare",
        product="geometry",
    )

    plan = BuildPlan(
        artifact_id="consumer",
        model=ModelSpec(
            name="consumer-model",
            title="Consumer Model",
        ),
        realization_name="default",
        resolver=None,  # type: ignore[arg-type]
        project_root=Path("/project"),
        artifact_dir=Path("/project/artifacts/consumer"),
        stages=(),
        targets=(
            ProductRef(
                artifact="consumer",
                model="consumer-model",
                realization="default",
                stage="package",
                product="artifact",
            ),
        ),
        product_dependencies=(dependency,),
    )

    assert plan.product_dependencies == (dependency,)


def test_build_plan_defaults_to_no_product_dependencies(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    artwork_plan,
) -> None:
    """
    Existing builds without cross-product requirements retain an empty
    product dependency set.
    """

    plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    assert plan.product_dependencies == ()


def test_create_build_plan_preserves_realization_product_dependencies(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Targeted planning preserves declarative product dependencies discovered
    by the selected realization graph.
    """

    dependency = ProductDependencySpec(
        model="producer",
        stage="prepare",
        product="geometry",
    )

    producer = ModelSpec(
        name="producer",
        title="Producer",
        stages=(
            StageSpec(
                id=10,
                name="prepare",
                products=(
                    ProductSpec(
                        name="geometry",
                        path="geometry.dat",
                    ),
                ),
            ),
        ),
    )

    consumer = ModelSpec(
        name="consumer",
        title="Consumer",
        stages=(
            StageSpec(
                id=10,
                name="package",
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

    class StubRegistry:
        def get_model(
            self,
            name: str,
        ) -> ModelSpec:
            models = {
                "producer": producer,
                "consumer": consumer,
            }

            return models[name]

        def all_models(
            self,
        ) -> tuple[ModelSpec, ...]:
            return (
                producer,
                consumer,
            )

    class Resolver:
        def __call__(
            self,
            name: str,
        ):
            values = {
                "model": "consumer",
                "variant": "default",
                "realization": "default",
            }

            return values[name]

        def source(
            self,
            name: str,
        ) -> str:
            return "test"

    monkeypatch.setattr(
        "lowkey_artifact_builder.engine.plan.get_resolver",
        lambda artifact_id, *, realization=None, project_root: Resolver(),
    )

    monkeypatch.setattr(
        "lowkey_artifact_builder.engine.plan.build_model_registry",
        lambda: StubRegistry(),
    )

    target = ProductRef(
        artifact="consumer-artifact",
        model="consumer",
        realization="default",
        stage="package",
        product="artifact",
    )

    plan = create_build_plan(
        "consumer-artifact",
        targets=(target,),
        project_root=tmp_path,
    )

    assert plan.product_dependencies == (dependency,)
