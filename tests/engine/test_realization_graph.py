"""
Tests for realization graph construction.
"""
# File: tests/engine/test_realization_graph.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import pytest

from lowkey_artifact_builder.engine.catalog import (
    build_product_catalog,
)
from lowkey_artifact_builder.engine.graph import (
    build_defined_graph,
)
from lowkey_artifact_builder.engine.realization_graph import (
    RealizationGraphError,
    build_realization_graph,
)
from lowkey_artifact_builder.model import (
    ModelRegistry,
    ModelSpec,
    ProductRef,
    ProductSpec,
    StageSpec,
    build_model_registry,
)

# =========================================================
# Helpers
# =========================================================


def _artwork_graph(
    *targets: ProductRef,
):
    """
    Build an artwork Realization Graph for the requested targets.
    """

    registry = build_model_registry()

    defined_graph = build_defined_graph(
        registry,
    )

    catalog = build_product_catalog(
        defined_graph,
    )

    return build_realization_graph(
        defined_graph,
        catalog,
        targets=targets,
    )


def _target(
    *,
    stage: str,
    product: str,
    artifact: str = "nydeli",
    realization: str = "default",
) -> ProductRef:
    """
    Construct one artwork ProductRef used as a realization target.
    """

    return ProductRef(
        artifact=artifact,
        model="artwork",
        realization=realization,
        stage=stage,
        product=product,
    )


# =========================================================
# Realization identity
# =========================================================


def test_realization_graph_preserves_realization_identity() -> None:
    """
    A Realization Graph preserves artifact, model, and realization identity.
    """

    target = _target(
        stage="vector",
        product="manifest",
    )

    graph = _artwork_graph(
        target,
    )

    assert graph.artifact_id == "nydeli"
    assert graph.model_name == "artwork"
    assert graph.realization_name == "default"
    assert graph.targets == (target,)


def test_realization_graph_selects_target_producer() -> None:
    """
    A requested product selects its producing stage.
    """

    graph = _artwork_graph(
        _target(
            stage="vector",
            product="manifest",
        )
    )

    assert tuple(stage.name for stage in graph.stages) == (
        "prepare",
        "raster",
        "vector",
    )


# =========================================================
# Dependency closure
# =========================================================


def test_realization_graph_includes_transitive_dependencies() -> None:
    """
    A target includes every transitive dependency required by its producer.
    """

    graph = _artwork_graph(
        _target(
            stage="extrude",
            product="manifest",
        )
    )

    assert tuple(stage.name for stage in graph.stages) == (
        "prepare",
        "raster",
        "vector",
        "extrude",
    )


def test_realization_graph_excludes_downstream_stages() -> None:
    """
    Stages downstream of the requested product are not realized.
    """

    graph = _artwork_graph(
        _target(
            stage="vector",
            product="manifest",
        )
    )

    stage_names = tuple(stage.name for stage in graph.stages)

    assert "extrude" not in stage_names
    assert "package" not in stage_names


def test_realization_graph_preserves_dependency_order() -> None:
    """
    Required stages are ordered with dependencies before dependents.
    """

    graph = _artwork_graph(
        _target(
            stage="package",
            product="artifact",
        )
    )

    assert tuple(stage.name for stage in graph.stages) == (
        "prepare",
        "raster",
        "vector",
        "extrude",
        "package",
    )


def test_realization_graph_handles_branching_dependencies() -> None:
    """
    Dependency closure includes every branch required by a target.
    """

    registry = ModelRegistry()

    registry.register_model(
        ModelSpec(
            name="example",
            title="Example",
            description="Example model.",
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
                    name="left",
                    dependencies=("prepare",),
                    products=(
                        ProductSpec(
                            name="left",
                            path="left.dat",
                        ),
                    ),
                ),
                StageSpec(
                    id=30,
                    name="right",
                    dependencies=("prepare",),
                    products=(
                        ProductSpec(
                            name="right",
                            path="right.dat",
                        ),
                    ),
                ),
                StageSpec(
                    id=40,
                    name="package",
                    dependencies=(
                        "left",
                        "right",
                    ),
                    products=(
                        ProductSpec(
                            name="artifact",
                            path="artifact.dat",
                        ),
                    ),
                ),
            ),
            defined_in=__name__,
        )
    )

    defined_graph = build_defined_graph(
        registry,
    )

    catalog = build_product_catalog(
        defined_graph,
    )

    graph = build_realization_graph(
        defined_graph,
        catalog,
        targets=(
            ProductRef(
                artifact="example-artifact",
                model="example",
                realization="default",
                stage="package",
                product="artifact",
            ),
        ),
    )

    assert tuple(stage.name for stage in graph.stages) == (
        "prepare",
        "left",
        "right",
        "package",
    )


# =========================================================
# Multiple targets
# =========================================================


def test_realization_graph_supports_multiple_targets() -> None:
    """
    A Realization Graph contains the union of dependencies for its targets.
    """

    vector = _target(
        stage="vector",
        product="manifest",
    )

    package = _target(
        stage="package",
        product="artifact",
    )

    graph = _artwork_graph(
        vector,
        package,
    )

    assert graph.targets == (
        vector,
        package,
    )

    assert tuple(stage.name for stage in graph.stages) == (
        "prepare",
        "raster",
        "vector",
        "extrude",
        "package",
    )


def test_realization_graph_deduplicates_shared_dependencies() -> None:
    """
    Shared dependencies appear only once in a multi-target graph.
    """

    graph = _artwork_graph(
        _target(
            stage="raster",
            product="manifest",
        ),
        _target(
            stage="vector",
            product="manifest",
        ),
    )

    assert tuple(stage.name for stage in graph.stages) == (
        "prepare",
        "raster",
        "vector",
    )


def test_realization_graph_deduplicates_duplicate_targets() -> None:
    """
    Repeated logical targets appear only once.
    """

    target = _target(
        stage="vector",
        product="manifest",
    )

    graph = _artwork_graph(
        target,
        target,
    )

    assert graph.targets == (target,)


# =========================================================
# Target validation
# =========================================================


def test_realization_graph_requires_target() -> None:
    """
    A Realization Graph requires at least one requested product.
    """

    registry = build_model_registry()

    defined_graph = build_defined_graph(
        registry,
    )

    catalog = build_product_catalog(
        defined_graph,
    )

    with pytest.raises(
        RealizationGraphError,
        match="at least one target product",
    ):
        build_realization_graph(
            defined_graph,
            catalog,
            targets=(),
        )


def test_realization_graph_rejects_unknown_target() -> None:
    """
    Every target must identify a product in the Product Catalog.
    """

    with pytest.raises(
        RealizationGraphError,
        match=("Unknown target product 'artwork/vector/missing'"),
    ):
        _artwork_graph(
            _target(
                stage="vector",
                product="missing",
            )
        )


def test_realization_graph_rejects_mixed_artifacts() -> None:
    """
    One Realization Graph cannot contain products from different artifacts.
    """

    with pytest.raises(
        RealizationGraphError,
        match="same artifact",
    ):
        _artwork_graph(
            _target(
                artifact="first",
                stage="raster",
                product="manifest",
            ),
            _target(
                artifact="second",
                stage="vector",
                product="manifest",
            ),
        )


def test_realization_graph_rejects_mixed_models() -> None:
    """
    One Realization Graph cannot contain products from different models.
    """

    registry = build_model_registry()

    defined_graph = build_defined_graph(
        registry,
    )

    catalog = build_product_catalog(
        defined_graph,
    )

    with pytest.raises(
        RealizationGraphError,
        match="same model",
    ):
        build_realization_graph(
            defined_graph,
            catalog,
            targets=(
                ProductRef(
                    artifact="example",
                    model="artwork",
                    realization="default",
                    stage="vector",
                    product="manifest",
                ),
                ProductRef(
                    artifact="example",
                    model="other",
                    realization="default",
                    stage="build",
                    product="artifact",
                ),
            ),
        )


def test_realization_graph_rejects_mixed_realizations() -> None:
    """
    One Realization Graph cannot contain products from different realizations.
    """

    with pytest.raises(
        RealizationGraphError,
        match="same realization",
    ):
        _artwork_graph(
            _target(
                realization="small",
                stage="raster",
                product="manifest",
            ),
            _target(
                realization="large",
                stage="vector",
                product="manifest",
            ),
        )
