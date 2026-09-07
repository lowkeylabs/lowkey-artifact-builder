"""
Tests for persistent Artifact Realization identity.

Realization identity, rather than the selected Variant identity, owns
persistent build state.

Multiple Realizations may select the same Model Variant while retaining
independent Product namespaces.
"""
# File: tests/engine/test_realization_identity.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path

from lowkey_artifact_builder.config import write_artifact_config
from lowkey_artifact_builder.engine import (
    ProductFingerprint,
    ProductState,
    StageCompletion,
    create_build_plan,
    create_product_state_resolver,
    write_stage_completion,
)


def _write_workspace(
    project_root: Path,
) -> None:
    """
    Write the minimal workspace configuration required by Shape planning.
    """

    (project_root / "workspace.toml").write_text(
        "[parameters]\n",
        encoding="utf-8",
    )


def test_additional_realizations_of_same_variant_own_distinct_product_namespaces(
    tmp_path: Path,
) -> None:
    """
    Additional Realizations selecting the same qualified Variant retain
    independent persistent Product namespaces.

    Variant identity supplies reusable configuration. Realization identity
    owns build state.
    """

    _write_workspace(tmp_path)

    write_artifact_config(
        "example",
        {
            "source": "source.png",
            "realizations": {
                "small": {
                    "variant": "shape.ornament",
                    "shape_size": 100.0,
                },
                "large": {
                    "variant": "shape.ornament",
                    "shape_size": 150.0,
                },
            },
        },
        project_root=tmp_path,
    )

    small = create_build_plan(
        "example",
        realization="small",
        project_root=tmp_path,
    )

    large = create_build_plan(
        "example",
        realization="large",
        project_root=tmp_path,
    )

    assert small.model_name == large.model_name == "shape"

    assert small.resolver("variant") == "ornament"
    assert large.resolver("variant") == "ornament"

    assert small.realization_name == "small"
    assert large.realization_name == "large"

    assert small.resolver("realization") == "small"
    assert large.resolver("realization") == "large"

    small_directory = tmp_path / "artifacts" / "example" / "shape" / "small"

    large_directory = tmp_path / "artifacts" / "example" / "shape" / "large"

    small_products = {product.path for stage in small.stages for product in stage.products}

    large_products = {product.path for stage in large.stages for product in stage.products}

    assert small_products
    assert large_products

    assert small_products.isdisjoint(large_products)

    assert all(path.is_relative_to(small_directory) for path in small_products)

    assert all(path.is_relative_to(large_directory) for path in large_products)


def test_canonical_default_realization_owns_its_product_namespace(
    tmp_path: Path,
) -> None:
    """
    A derived default Realization owns persistent Products under its canonical
    Realization identity rather than under the local Variant name.

    shape_ornament selects shape.ornament, but its persistent Realization
    namespace is shape_ornament.
    """

    _write_workspace(tmp_path)

    write_artifact_config(
        "example",
        {
            "source": "source.png",
        },
        project_root=tmp_path,
    )

    plan = create_build_plan(
        "example",
        realization="shape_ornament",
        project_root=tmp_path,
    )

    assert plan.model_name == "shape"
    assert plan.resolver("variant") == "ornament"

    assert plan.realization_name == "shape_ornament"
    assert plan.resolver("realization") == "shape_ornament"

    realization_directory = tmp_path / "artifacts" / "example" / "shape" / "shape_ornament"

    products = {product.path for stage in plan.stages for product in stage.products}

    assert products

    assert all(path.is_relative_to(realization_directory) for path in products)


def test_persistent_state_for_same_variant_is_isolated_by_realization(
    tmp_path: Path,
) -> None:
    """
    Persistent completion and freshness state belongs to the Realization.

    Completing a Product for one Realization must not make the corresponding
    Product of another Realization selecting the same Variant current.
    """

    _write_workspace(tmp_path)

    write_artifact_config(
        "example",
        {
            "source": "source.png",
            "realizations": {
                "small": {
                    "variant": "shape.ornament",
                    "shape_size": 100.0,
                },
                "large": {
                    "variant": "shape.ornament",
                    "shape_size": 150.0,
                },
            },
        },
        project_root=tmp_path,
    )

    small = create_build_plan(
        "example",
        realization="small",
        project_root=tmp_path,
    )

    large = create_build_plan(
        "example",
        realization="large",
        project_root=tmp_path,
    )

    small_stage = small.stages[0]
    large_stage = large.stages[0]

    assert small_stage.name == large_stage.name
    assert small_stage.products
    assert large_stage.products

    small_product = small_stage.products[0]
    large_product = large_stage.products[0]

    assert small_product.spec.name == large_product.spec.name
    assert small_product.spec.path == large_product.spec.path

    small_working_dir = small_product.path.parent
    large_working_dir = large_product.path.parent

    assert small_working_dir != large_working_dir

    small_working_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    fingerprint = ProductFingerprint(
        algorithm="sha256",
        value="same-build-context",
    )

    small_product.path.write_text(
        "small realization product",
        encoding="utf-8",
    )

    write_stage_completion(
        small_working_dir,
        StageCompletion(
            artifact_id="example",
            model_name="shape",
            realization="small",
            stage_name=small_stage.name,
            products=(small_product.spec.name,),
            fingerprint=fingerprint,
        ),
    )

    resolve_small = create_product_state_resolver(
        working_dir=small_working_dir,
        required_fingerprints={
            small_product.spec.name: fingerprint,
        },
    )

    resolve_large = create_product_state_resolver(
        working_dir=large_working_dir,
        required_fingerprints={
            large_product.spec.name: fingerprint,
        },
    )

    assert (
        resolve_small(
            small_product.spec.name,
            Path(small_product.spec.path),
        )
        is ProductState.CURRENT
    )

    assert (
        resolve_large(
            large_product.spec.name,
            Path(large_product.spec.path),
        )
        is ProductState.ABSENT
    )
