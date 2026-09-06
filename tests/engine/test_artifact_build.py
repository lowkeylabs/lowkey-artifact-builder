"""
Tests for the public artifact-build engine boundary.

A caller identifies the configured artifact it wants built. The engine owns
planning, dependency resolution, incremental execution, and production of
the requested artifact.

Callers of this boundary do not construct BuildPlans or select an execution
strategy.
"""
# File: tests/engine/test_artifact_build.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import shutil
import zipfile
from pathlib import Path

import pytest

import lowkey_artifact_builder.engine.artifact_build as artifact_build
from lowkey_artifact_builder.config import (
    write_artifact_config,
)
from lowkey_artifact_builder.engine import (
    execute_artifact_build,
)

# =========================================================
# Public artifact-build boundary
# =========================================================


def test_artifact_build_accepts_configured_artifact_identity(
    tmp_path: Path,
) -> None:
    """
    The public engine build boundary accepts an artifact identity.

    Callers do not construct a BuildPlan or select an execution strategy.
    """

    write_artifact_config(
        "shape-artifact",
        {
            "model": "shape",
        },
        project_root=tmp_path,
    )

    execute_artifact_build(
        "shape-artifact",
        project_root=tmp_path,
    )

    output = (
        tmp_path
        / "artifacts"
        / "shape-artifact"
        / "shape"
        / "default"
        / "40-package"
        / "artifact.3mf"
    )

    assert output.is_file()
    assert output.stat().st_size > 0
    assert zipfile.is_zipfile(
        output,
    )


@pytest.mark.slow
def test_artifact_build_satisfies_cross_artifact_dependencies(
    tmp_path: Path,
) -> None:
    """
    The public engine build boundary satisfies configured dependencies.

    The caller requests only the consumer artifact. The engine determines
    and executes the required producer closure before completing the
    requested artifact.

    Producer stages outside the required dependency closure do not execute.
    """

    # -----------------------------------------------------
    # Create canonical Artwork source
    # -----------------------------------------------------

    repository_root = Path(__file__).resolve().parents[2]

    fixture_source = repository_root / "tests" / "assets" / "nydeli-clean.png"

    assert fixture_source.is_file(), f"Test artwork does not exist: {fixture_source}"

    artwork_directory = tmp_path / "artifacts" / "source-artwork"

    artwork_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    artwork_input = artwork_directory / "artifact.png"

    shutil.copy2(
        fixture_source,
        artwork_input,
    )

    # -----------------------------------------------------
    # Configure producer artifact
    # -----------------------------------------------------

    write_artifact_config(
        "source-artwork",
        {
            "model": "artwork",
            "source": str(
                artwork_input,
            ),
        },
        project_root=tmp_path,
    )

    # -----------------------------------------------------
    # Configure consumer artifact
    # -----------------------------------------------------

    write_artifact_config(
        "artwork-shape",
        {
            "model": "shape",
            "product_dependencies": {
                "manifest": {
                    "model": "artwork",
                    "stage": "vector",
                    "product": "manifest",
                    "artifact": "source-artwork",
                    "realization": "default",
                },
            },
        },
        project_root=tmp_path,
    )

    artwork_root = tmp_path / "artifacts" / "source-artwork" / "artwork" / "default"

    shape_root = tmp_path / "artifacts" / "artwork-shape" / "shape" / "default"

    assert not artwork_root.exists()
    assert not shape_root.exists()

    # -----------------------------------------------------
    # Request only the consumer artifact
    # -----------------------------------------------------

    execute_artifact_build(
        "artwork-shape",
        project_root=tmp_path,
    )

    # -----------------------------------------------------
    # Required producer closure exists
    # -----------------------------------------------------

    assert (artwork_root / "10-prepare" / "trace.svg").is_file()

    assert (artwork_root / "20-raster" / "products.json").is_file()

    assert (artwork_root / "30-vector" / "products.json").is_file()

    # -----------------------------------------------------
    # Unrequired producer stages remain absent
    # -----------------------------------------------------

    assert not (artwork_root / "40-extrude" / "products.json").exists()

    assert not (artwork_root / "50-package" / "artifact.3mf").exists()

    # -----------------------------------------------------
    # Requested consumer artifact exists
    # -----------------------------------------------------

    output = shape_root / "40-package" / "artifact.3mf"

    assert output.is_file()
    assert output.stat().st_size > 0
    assert zipfile.is_zipfile(
        output,
    )


def test_artifact_build_selects_requested_realization(
    tmp_path: Path,
) -> None:
    """
    The public artifact-build boundary may build one selected realization.

    Other configured realizations are not built merely because they belong
    to the same artifact.
    """

    write_artifact_config(
        "shape-artifact",
        {
            "realizations": {
                "default": {
                    "model": "shape",
                },
                "alternate": {
                    "model": "shape",
                },
            },
        },
        project_root=tmp_path,
    )

    execute_artifact_build(
        "shape-artifact",
        realization="default",
        project_root=tmp_path,
    )

    default_output = (
        tmp_path
        / "artifacts"
        / "shape-artifact"
        / "shape"
        / "default"
        / "40-package"
        / "artifact.3mf"
    )

    alternate_output = (
        tmp_path
        / "artifacts"
        / "shape-artifact"
        / "shape"
        / "alternate"
        / "40-package"
        / "artifact.3mf"
    )

    assert default_output.is_file()
    assert default_output.stat().st_size > 0
    assert zipfile.is_zipfile(
        default_output,
    )

    assert not alternate_output.exists()


def test_artifact_build_selects_model_with_local_variant_name(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    The artifact-build boundary normalizes Variant identity.

    A Model name and local Variant name supplied by the caller become the
    decomposed runtime identity of Model plus realization/local Variant name.
    No independent Variant coordinate is forwarded into planning.
    """

    requested: list[
        tuple[
            str,
            str | None,
            str | None,
            Path | None,
        ]
    ] = []

    def fake_create_build_plans(
        artifact_id: str,
        *,
        model_name: str | None = None,
        realization: str | None = None,
        project_root: Path | None = None,
    ):
        requested.append(
            (
                artifact_id,
                model_name,
                realization,
                project_root,
            )
        )

        return ()

    monkeypatch.setattr(
        artifact_build,
        "create_build_plans",
        fake_create_build_plans,
    )

    plans = execute_artifact_build(
        "example",
        model_name="shape",
        variant_name="ornament",
        project_root=tmp_path,
    )

    assert plans == ()

    assert requested == [
        (
            "example",
            "shape",
            "ornament",
            tmp_path,
        )
    ]


def test_artifact_build_selects_local_variant_as_realization_name(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    A local Variant name becomes the runtime realization/local-name coordinate.

    Variant selection does not create an independent runtime identity beside
    Artifact, Model, and realization.
    """

    requested: list[tuple[str | None,]] = []

    def fake_create_build_plans(
        artifact_id: str,
        *,
        realization: str | None = None,
        project_root: Path | None = None,
    ):
        requested.append((realization,))

        return ()

    monkeypatch.setattr(
        artifact_build,
        "create_build_plans",
        fake_create_build_plans,
    )

    plans = execute_artifact_build(
        "example",
        variant_name="ornament",
        project_root=tmp_path,
    )

    assert plans == ()

    assert requested == [("ornament",)]


def test_artifact_build_all_variants_plans_each_model_variant(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    All-Variant execution plans every Variant owned by the artifact's Model.

    Each Variant is normalized to its Model plus realization/local Variant
    name before entering ordinary build planning.
    """

    write_artifact_config(
        "example",
        {
            "model": "shape",
        },
        project_root=tmp_path,
    )

    requested: list[
        tuple[
            str,
            str | None,
            str | None,
            Path | None,
        ]
    ] = []

    def fake_create_build_plans(
        artifact_id: str,
        *,
        model_name: str | None = None,
        realization: str | None = None,
        project_root: Path | None = None,
    ):
        requested.append(
            (
                artifact_id,
                model_name,
                realization,
                project_root,
            )
        )

        return ()

    monkeypatch.setattr(
        artifact_build,
        "create_build_plans",
        fake_create_build_plans,
    )

    plans = execute_artifact_build(
        "example",
        all_variants=True,
        project_root=tmp_path,
    )

    assert plans == ()

    assert requested == [
        (
            "example",
            "shape",
            "default",
            tmp_path,
        ),
        (
            "example",
            "shape",
            "ornament",
            tmp_path,
        ),
    ]


def test_artifact_build_rejects_realization_with_all_variants(
    tmp_path: Path,
) -> None:
    """
    All-Variant selection cannot be combined with one local Variant name.

    Historical realization is the runtime local-name component of Variant
    identity, so selecting it together with all Variants would create two
    competing Variant selections.
    """

    with pytest.raises(
        ValueError,
        match="realization and all_variants cannot be used together",
    ):
        execute_artifact_build(
            "example",
            realization="alternate",
            all_variants=True,
            project_root=tmp_path,
        )


def test_artifact_build_planning_rejects_variant_with_all_variants(
    tmp_path: Path,
) -> None:
    """
    Artifact-level planning rejects contradictory Variant selection.

    A caller may request one Variant or all Model Variants, but not both.
    """

    with pytest.raises(
        ValueError,
        match="variant_name and all_variants cannot be used together",
    ):
        artifact_build.create_artifact_build_plans(
            "example",
            variant_name="ornament",
            all_variants=True,
            project_root=tmp_path,
        )


def test_artifact_build_execution_rejects_variant_with_all_variants(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    Artifact execution preserves the artifact-planning selection contract.

    Invalid Variant selection fails before dependency execution begins.
    """

    executed: list[object] = []

    monkeypatch.setattr(
        artifact_build,
        "execute_dependency_build",
        lambda plan, **kwargs: executed.append(plan),
    )

    with pytest.raises(
        ValueError,
        match="variant_name and all_variants cannot be used together",
    ):
        execute_artifact_build(
            "example",
            variant_name="ornament",
            all_variants=True,
            project_root=tmp_path,
        )

    assert executed == []


def test_artifact_build_without_selection_plans_default_realization_only(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    Ordinary artifact build does not expand across configured Realizations.

    Omitting Variant and Realization selection means ordinary/default
    behavior rather than requesting every configured Artifact Realization.
    """

    write_artifact_config(
        "example",
        {
            "realizations": {
                "default": {
                    "model": "shape",
                },
                "alternate": {
                    "model": "shape",
                },
            },
        },
        project_root=tmp_path,
    )

    requested: list[
        tuple[
            str,
            str | None,
            str | None,
            str | None,
            Path | None,
        ]
    ] = []

    def fake_create_build_plans(
        artifact_id: str,
        *,
        model_name: str | None = None,
        variant_name: str | None = None,
        realization: str | None = None,
        project_root: Path | None = None,
    ):
        requested.append(
            (
                artifact_id,
                model_name,
                variant_name,
                realization,
                project_root,
            )
        )

        return ()

    monkeypatch.setattr(
        artifact_build,
        "create_build_plans",
        fake_create_build_plans,
    )

    plans = artifact_build.create_artifact_build_plans(
        "example",
        project_root=tmp_path,
    )

    assert plans == ()

    assert requested == [
        (
            "example",
            None,
            None,
            "default",
            tmp_path,
        )
    ]


def test_artifact_build_qualified_variant_uses_effective_variant_configuration(
    tmp_path: Path,
) -> None:
    """
    Artifact build planning resolves the effective configuration of the
    selected qualified Variant.

    The resulting plan uses the same Model and Variant configuration that
    artifact inspection resolves for shape.ornament.
    """

    write_artifact_config(
        "skippy",
        {
            "model": "shape",
        },
        project_root=tmp_path,
    )

    plans = artifact_build.create_artifact_build_plans(
        "skippy",
        model_name="shape",
        variant_name="ornament",
        project_root=tmp_path,
    )

    assert len(plans) == 1

    plan = plans[0]

    assert plan.resolver("model") == "shape"
    assert plan.resolver("variant") == "ornament"
    assert plan.resolver("realization") == "ornament"

    assert plan.resolver("shape_outer_ridge_width") == 2.0
    assert plan.resolver.source("shape_outer_ridge_width") == "variant 'ornament'"


def test_artifact_build_omitted_variant_matches_explicit_default_variant(
    tmp_path: Path,
) -> None:
    """
    Omitted Variant selection and explicit default Variant selection resolve
    to the same ordinary build configuration.
    """

    write_artifact_config(
        "skippy",
        {
            "model": "shape",
        },
        project_root=tmp_path,
    )

    implicit_plans = artifact_build.create_artifact_build_plans(
        "skippy",
        project_root=tmp_path,
    )

    explicit_plans = artifact_build.create_artifact_build_plans(
        "skippy",
        variant_name="default",
        project_root=tmp_path,
    )

    assert len(implicit_plans) == 1
    assert len(explicit_plans) == 1

    implicit = implicit_plans[0].resolver
    explicit = explicit_plans[0].resolver

    assert implicit("model") == explicit("model") == "shape"
    assert implicit("variant") == explicit("variant") == "default"
    assert implicit("realization") == explicit("realization") == "default"

    assert implicit("shape_outer_ridge_width") == explicit("shape_outer_ridge_width") == 0.0
