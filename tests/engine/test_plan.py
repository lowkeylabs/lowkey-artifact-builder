"""
Tests for artifact build planning.

These tests verify construction of concrete build plans from configured
artifacts and declarative model specifications.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from lowkey_artifact_builder.engine import (
    BuildPlan,
    BuildPlanError,
    create_build_plan,
)
from lowkey_artifact_builder.model import (
    ModelSpec,
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
