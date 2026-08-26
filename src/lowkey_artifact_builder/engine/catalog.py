"""
Defined product catalog.

The product catalog enumerates every product definition known to the
artifact builder. It is derived from the validated Defined Graph and
contains no artifact- or realization-specific state.
"""
# File: src/lowkey_artifact_builder/engine/catalog.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from dataclasses import dataclass

from lowkey_artifact_builder.engine.graph import (
    DefinedGraph,
)
from lowkey_artifact_builder.model import (
    ProductDependencySpec,
    ProductSpec,
)

# =========================================================
# Errors
# =========================================================


class ProductCatalogError(RuntimeError):
    """
    Base exception for product catalog errors.
    """


class ProductNotFoundError(ProductCatalogError):
    """
    Raised when a requested product is not present in the catalog.
    """


# =========================================================
# Catalog products
# =========================================================


@dataclass(
    frozen=True,
    slots=True,
)
class CatalogProduct:
    """
    One product definition in the product catalog.

    Catalog identity is definition-level and therefore consists of the
    model, producing stage, and product name. Artifact and realization
    identities belong to concrete ProductRef values created later.
    """

    model_name: str
    stage_name: str
    spec: ProductSpec

    @property
    def product_name(
        self,
    ) -> str:
        """
        Return the declared product name.
        """

        return self.spec.name


# =========================================================
# Product catalog
# =========================================================


@dataclass(
    frozen=True,
    slots=True,
)
class ProductCatalog:
    """
    Complete catalog of defined products.

    Product order follows the validated Defined Graph: model order,
    followed by stage declaration order, followed by product declaration
    order.
    """

    products: tuple[CatalogProduct, ...]

    def product(
        self,
        *,
        model_name: str,
        stage_name: str,
        product_name: str,
    ) -> CatalogProduct:
        """
        Return the product matching a definition-level identity.

        Raises ProductNotFoundError when the catalog contains no
        matching product.
        """

        for product in self.products:
            if (
                product.model_name == model_name
                and product.stage_name == stage_name
                and product.product_name == product_name
            ):
                return product

        raise ProductNotFoundError(f"Product not found: {model_name}/{stage_name}/{product_name}")

    def resolve_dependency(
        self,
        dependency: ProductDependencySpec,
    ) -> CatalogProduct:
        """
        Resolve a declarative product dependency to its catalog product.

        ProductDependencySpec and CatalogProduct share the same
        definition-level product identity: model, producing stage, and
        product name.

        Raises ProductNotFoundError when the dependency does not identify
        a product present in the catalog.
        """

        return self.product(
            model_name=dependency.model,
            stage_name=dependency.stage,
            product_name=dependency.product,
        )


# =========================================================
# Catalog construction
# =========================================================


def build_product_catalog(
    graph: DefinedGraph,
) -> ProductCatalog:
    """
    Build the complete product catalog from a Defined Graph.
    """

    products: list[CatalogProduct] = []

    for model_name in graph.models:
        model = graph.model(
            model_name,
        )

        for stage in model.stages:
            for product in stage.products:
                products.append(
                    CatalogProduct(
                        model_name=model.name,
                        stage_name=stage.name,
                        spec=product,
                    )
                )

    return ProductCatalog(
        products=tuple(products),
    )


# =========================================================
# Exports
# =========================================================

__all__ = [
    "CatalogProduct",
    "ProductCatalog",
    "ProductCatalogError",
    "ProductNotFoundError",
    "build_product_catalog",
]
