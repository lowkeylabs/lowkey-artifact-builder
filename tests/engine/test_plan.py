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
    Declarative product paths are materialized relative to the
    artifact working directory.
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
            artifact_dir / "prepare" / "trace.svg",
            artifact_dir / "prepare" / "envelope.svg",
        ),
        "raster": (artifact_dir / "raster" / "products.json",),
        "vector": (artifact_dir / "vector" / "products.json",),
        "extrude": (artifact_dir / "extrude" / "products.json",),
        "package": (artifact_dir / "artifact.3mf",),
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
            assert name == "model"

            return "does-not-exist"

        def source(
            self,
            name: str,
        ) -> str:
            return "test"

    monkeypatch.setattr(
        "lowkey_artifact_builder.engine.plan.get_resolver",
        lambda artifact_id, project_root: Resolver(),
    )

    with pytest.raises(
        BuildPlanError,
        match="unknown model",
    ):
        create_build_plan(
            "example",
            project_root=tmp_path,
        )
