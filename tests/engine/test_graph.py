"""
Tests for the complete defined product graph.
"""
# File: tests/engine/test_graph.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import pytest

from lowkey_artifact_builder.engine.graph import (
    DefinedGraphError,
    build_defined_graph,
)
from lowkey_artifact_builder.model import (
    ModelRegistry,
    ModelSpec,
    ProductSpec,
    StageSpec,
    VariantSpec,
    build_model_registry,
)

# =========================================================
# Defined graph construction
# =========================================================


def test_defined_graph_contains_registered_models() -> None:
    """
    The defined graph contains every registered artifact model.
    """

    registry = build_model_registry()

    graph = build_defined_graph(
        registry,
    )

    assert tuple(graph.models) == tuple(model.name for model in registry.all_models())


def test_defined_graph_contains_artwork_stages() -> None:
    """
    The defined graph contains every stage declared by the artwork model.
    """

    registry = build_model_registry()

    graph = build_defined_graph(
        registry,
    )

    artwork = graph.model(
        "artwork",
    )

    assert tuple(stage.name for stage in artwork.stages) == (
        "prepare",
        "raster",
        "vector",
        "extrude",
        "package",
    )


# =========================================================
# Dependencies
# =========================================================


def test_defined_graph_preserves_artwork_dependencies() -> None:
    """
    Defined graph stages preserve declarative stage dependencies.
    """

    registry = build_model_registry()

    graph = build_defined_graph(
        registry,
    )

    artwork = graph.model(
        "artwork",
    )

    assert artwork.stage("prepare").dependencies == ()
    assert artwork.stage("raster").dependencies == ("prepare",)
    assert artwork.stage("vector").dependencies == ("raster",)
    assert artwork.stage("extrude").dependencies == ("vector",)
    assert artwork.stage("package").dependencies == ("extrude",)


# =========================================================
# Products
# =========================================================


def test_defined_graph_contains_artwork_products() -> None:
    """
    The defined graph contains every product declared by artwork stages.
    """

    registry = build_model_registry()

    graph = build_defined_graph(
        registry,
    )

    artwork = graph.model(
        "artwork",
    )

    assert tuple(product.name for product in artwork.stage("prepare").products) == (
        "trace",
        "envelope",
    )

    assert tuple(product.name for product in artwork.stage("raster").products) == ("manifest",)

    assert tuple(product.name for product in artwork.stage("vector").products) == ("manifest",)

    assert tuple(product.name for product in artwork.stage("extrude").products) == ("manifest",)

    assert tuple(product.name for product in artwork.stage("package").products) == ("artifact",)


# =========================================================
# Graph validation
# =========================================================


def test_defined_graph_rejects_missing_stage_dependency() -> None:
    """
    A stage dependency must identify another stage in the same model.
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
                ),
                StageSpec(
                    id=20,
                    name="package",
                    dependencies=("missing",),
                ),
            ),
            defined_in=__name__,
        )
    )

    with pytest.raises(
        DefinedGraphError,
        match=("Stage 'package' in model 'example' depends on unknown stage 'missing'"),
    ):
        build_defined_graph(
            registry,
        )


def test_defined_graph_rejects_self_dependency_cycle() -> None:
    """
    A stage cannot depend on itself.
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
                    name="build",
                    dependencies=("build",),
                ),
            ),
            defined_in=__name__,
        )
    )

    with pytest.raises(
        DefinedGraphError,
        match="cycle",
    ):
        build_defined_graph(
            registry,
        )


def test_defined_graph_rejects_multi_stage_cycle() -> None:
    """
    Stage dependencies cannot form a cycle through multiple stages.
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
                    dependencies=("package",),
                ),
                StageSpec(
                    id=20,
                    name="build",
                    dependencies=("prepare",),
                ),
                StageSpec(
                    id=30,
                    name="package",
                    dependencies=("build",),
                ),
            ),
            defined_in=__name__,
        )
    )

    with pytest.raises(
        DefinedGraphError,
        match="cycle",
    ):
        build_defined_graph(
            registry,
        )


def test_defined_graph_accepts_branching_dependencies() -> None:
    """
    A valid defined graph may branch and later join.
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
                ),
                StageSpec(
                    id=20,
                    name="left",
                    dependencies=("prepare",),
                ),
                StageSpec(
                    id=30,
                    name="right",
                    dependencies=("prepare",),
                ),
                StageSpec(
                    id=40,
                    name="package",
                    dependencies=(
                        "left",
                        "right",
                    ),
                ),
            ),
            defined_in=__name__,
        )
    )

    graph = build_defined_graph(
        registry,
    )

    example = graph.model(
        "example",
    )

    assert example.stage("prepare").dependencies == ()
    assert example.stage("left").dependencies == ("prepare",)
    assert example.stage("right").dependencies == ("prepare",)
    assert example.stage("package").dependencies == (
        "left",
        "right",
    )


def test_defined_graph_contains_artwork_variants() -> None:
    """
    The defined graph contains every variant declared by the artwork model.
    """

    registry = build_model_registry()

    graph = build_defined_graph(
        registry,
    )

    artwork = graph.model(
        "artwork",
    )

    assert tuple(variant.name for variant in artwork.variants) == tuple(
        variant.name for variant in registry.get_model("artwork").variants
    )


def test_defined_graph_preserves_model_variants() -> None:
    """
    The defined graph preserves model-scoped variants and their presets.
    """

    registry = ModelRegistry()

    registry.register_model(
        ModelSpec(
            name="example",
            title="Example",
            description="Example model.",
            variants=(
                VariantSpec(
                    name="small",
                    parameters={
                        "diameter": 90.0,
                    },
                ),
                VariantSpec(
                    name="large",
                    parameters={
                        "diameter": 100.0,
                    },
                ),
            ),
            stages=(
                StageSpec(
                    id=10,
                    name="build",
                ),
            ),
            defined_in=__name__,
        )
    )

    graph = build_defined_graph(
        registry,
    )

    example = graph.model(
        "example",
    )

    assert tuple(variant.name for variant in example.variants) == (
        "default",
        "small",
        "large",
    )

    assert example.variants[0].spec.parameters == {}
    assert example.variants[1].spec.parameters == {
        "diameter": 90.0,
    }
    assert example.variants[2].spec.parameters == {
        "diameter": 100.0,
    }


def test_defined_graph_rejects_duplicate_product_identity() -> None:
    """
    A stage cannot define multiple products with the same identity.
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
                    name="build",
                    products=(
                        ProductSpec(
                            name="artifact",
                            path="first.3mf",
                        ),
                        ProductSpec(
                            name="artifact",
                            path="second.3mf",
                        ),
                    ),
                ),
            ),
            defined_in=__name__,
        )
    )

    with pytest.raises(
        DefinedGraphError,
        match=("Duplicate product identity 'example/build/artifact'"),
    ):
        build_defined_graph(
            registry,
        )
