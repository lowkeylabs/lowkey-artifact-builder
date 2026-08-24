"""
Tests for the defined product catalog.
"""
# File: tests/engine/test_catalog.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import pytest

from lowkey_artifact_builder.engine.catalog import (
    ProductNotFoundError,
    build_product_catalog,
)
from lowkey_artifact_builder.engine.graph import (
    build_defined_graph,
)
from lowkey_artifact_builder.model import (
    build_model_registry,
)

# =========================================================
# Product catalog construction
# =========================================================


def test_product_catalog_contains_artwork_products() -> None:
    """
    The product catalog contains every product defined by artwork.
    """

    registry = build_model_registry()

    graph = build_defined_graph(
        registry,
    )

    catalog = build_product_catalog(
        graph,
    )

    assert tuple(
        (
            product.model_name,
            product.stage_name,
            product.product_name,
        )
        for product in catalog.products
    ) == (
        (
            "artwork",
            "prepare",
            "trace",
        ),
        (
            "artwork",
            "prepare",
            "envelope",
        ),
        (
            "artwork",
            "raster",
            "manifest",
        ),
        (
            "artwork",
            "vector",
            "manifest",
        ),
        (
            "artwork",
            "extrude",
            "manifest",
        ),
        (
            "artwork",
            "package",
            "artifact",
        ),
    )


def test_product_catalog_finds_product_by_definition() -> None:
    """
    A catalog product can be located by model, stage, and product name.
    """

    registry = build_model_registry()

    graph = build_defined_graph(
        registry,
    )

    catalog = build_product_catalog(
        graph,
    )

    product = catalog.product(
        model_name="artwork",
        stage_name="package",
        product_name="artifact",
    )

    assert product.model_name == "artwork"
    assert product.stage_name == "package"
    assert product.product_name == "artifact"
    assert product.spec.name == "artifact"
    assert product.spec.path == "artifact.3mf"


# =========================================================
# Product catalog lookup
# =========================================================


def test_product_catalog_rejects_unknown_product() -> None:
    """
    Catalog lookup rejects an unknown product definition.
    """

    registry = build_model_registry()

    graph = build_defined_graph(
        registry,
    )

    catalog = build_product_catalog(
        graph,
    )

    with pytest.raises(
        ProductNotFoundError,
        match=("Product not found: artwork/package/missing"),
    ):
        catalog.product(
            model_name="artwork",
            stage_name="package",
            product_name="missing",
        )


def test_product_catalog_distinguishes_same_name_across_stages() -> None:
    """
    Product identity includes the producing stage.

    Products with the same declared name in different stages remain
    distinct catalog entries.
    """

    registry = build_model_registry()

    graph = build_defined_graph(
        registry,
    )

    catalog = build_product_catalog(
        graph,
    )

    raster = catalog.product(
        model_name="artwork",
        stage_name="raster",
        product_name="manifest",
    )

    vector = catalog.product(
        model_name="artwork",
        stage_name="vector",
        product_name="manifest",
    )

    extrude = catalog.product(
        model_name="artwork",
        stage_name="extrude",
        product_name="manifest",
    )

    assert raster != vector
    assert vector != extrude
    assert raster != extrude

    assert raster.stage_name == "raster"
    assert vector.stage_name == "vector"
    assert extrude.stage_name == "extrude"
