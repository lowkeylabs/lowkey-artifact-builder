"""
Artifact realization graph construction.

A Realization Graph selects the portion of the complete Defined Graph
required to produce one or more requested logical products for a single
artifact realization.

ProductRef supplies concrete artifact, model, realization, stage, and
product identity. The Product Catalog validates definition-level product
identity, while the Defined Graph supplies dependency relationships.

The resulting graph contains only stages required by the requested
products. Downstream stages that are not required by any target are not
included.
"""
# File: src/lowkey_artifact_builder/engine/realization_graph.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from dataclasses import dataclass

from lowkey_artifact_builder.engine.catalog import (
    ProductCatalog,
    ProductNotFoundError,
)
from lowkey_artifact_builder.engine.graph import (
    DefinedGraph,
    DefinedModel,
    DefinedStage,
)
from lowkey_artifact_builder.model import (
    ProductRef,
)

# =========================================================
# Errors
# =========================================================


class RealizationGraphError(RuntimeError):
    """
    Raised when requested products cannot form one realization graph.
    """


# =========================================================
# Realization graph
# =========================================================


@dataclass(
    frozen=True,
    slots=True,
)
class RealizationGraph:
    """
    Required graph for one configured artifact realization.

    Targets are the logical products requested by the caller.

    Stages contain the producing stages of those targets and the union
    of their complete transitive dependency closures. Dependencies
    always precede their dependents.

    A Realization Graph is scoped to exactly one artifact, model, and
    realization.
    """

    artifact_id: str
    model_name: str
    realization_name: str
    targets: tuple[ProductRef, ...]
    stages: tuple[DefinedStage, ...]


# =========================================================
# Graph construction
# =========================================================


def build_realization_graph(
    defined_graph: DefinedGraph,
    catalog: ProductCatalog,
    *,
    targets: tuple[ProductRef, ...],
) -> RealizationGraph:
    """
    Construct the graph required to produce requested logical products.

    Every target must belong to the same artifact, model, and
    realization. Each target is validated against the Product Catalog.

    The returned graph contains the union of the target producers and
    their complete transitive stage dependency closures.
    """

    if not targets:
        raise RealizationGraphError("Realization Graph requires at least one target product.")

    unique_targets = _deduplicate_targets(
        targets,
    )

    artifact_id = unique_targets[0].artifact
    model_name = unique_targets[0].model
    realization_name = unique_targets[0].realization

    _validate_target_scope(
        unique_targets,
        artifact_id=artifact_id,
        model_name=model_name,
        realization_name=realization_name,
    )

    try:
        model = defined_graph.model(
            model_name,
        )

    except KeyError as exc:
        raise RealizationGraphError(f"Unknown target model {model_name!r}.") from exc

    for target in unique_targets:
        _validate_target_product(
            catalog,
            target,
        )

    stages = _dependency_closure(
        model,
        unique_targets,
    )

    return RealizationGraph(
        artifact_id=artifact_id,
        model_name=model_name,
        realization_name=realization_name,
        targets=unique_targets,
        stages=stages,
    )


# =========================================================
# Target validation
# =========================================================


def _deduplicate_targets(
    targets: tuple[ProductRef, ...],
) -> tuple[ProductRef, ...]:
    """
    Deduplicate targets while preserving request order.
    """

    unique: list[ProductRef] = []
    seen: set[ProductRef] = set()

    for target in targets:
        if target in seen:
            continue

        seen.add(
            target,
        )

        unique.append(
            target,
        )

    return tuple(
        unique,
    )


def _validate_target_scope(
    targets: tuple[ProductRef, ...],
    *,
    artifact_id: str,
    model_name: str,
    realization_name: str,
) -> None:
    """
    Validate that all targets belong to one artifact realization.
    """

    for target in targets:
        if target.artifact != artifact_id:
            raise RealizationGraphError(
                "Realization Graph targets must belong to the same artifact."
            )

        if target.model != model_name:
            raise RealizationGraphError("Realization Graph targets must belong to the same model.")

        if target.realization != realization_name:
            raise RealizationGraphError(
                "Realization Graph targets must belong to the same realization."
            )


def _validate_target_product(
    catalog: ProductCatalog,
    target: ProductRef,
) -> None:
    """
    Validate that one target identifies a defined catalog product.
    """

    try:
        catalog.product(
            model_name=target.model,
            stage_name=target.stage,
            product_name=target.product,
        )

    except ProductNotFoundError as exc:
        target_identity = f"{target.model}/{target.stage}/{target.product}"

        raise RealizationGraphError(f"Unknown target product {target_identity!r}") from exc


# =========================================================
# Dependency closure
# =========================================================


def _dependency_closure(
    model: DefinedModel,
    targets: tuple[ProductRef, ...],
) -> tuple[DefinedStage, ...]:
    """
    Return the ordered union of target stage dependency closures.

    Traversal begins at every target producer. Shared dependencies are
    emitted once. Depth-first traversal guarantees dependencies precede
    their dependents.

    Defined Graph validation guarantees that every dependency exists
    and that the stage dependency graph is acyclic.
    """

    required: list[DefinedStage] = []
    visited: set[str] = set()

    def visit(
        stage: DefinedStage,
    ) -> None:
        if stage.name in visited:
            return

        for dependency_name in stage.dependencies:
            visit(
                model.stage(
                    dependency_name,
                )
            )

        visited.add(
            stage.name,
        )

        required.append(
            stage,
        )

    for target in targets:
        try:
            stage = model.stage(
                target.stage,
            )

        except KeyError as exc:
            raise RealizationGraphError(
                f"Unknown target stage {target.stage!r} in model {model.name!r}."
            ) from exc

        visit(
            stage,
        )

    return tuple(
        required,
    )


# =========================================================
# Exports
# =========================================================


__all__ = [
    "RealizationGraph",
    "RealizationGraphError",
    "build_realization_graph",
]
