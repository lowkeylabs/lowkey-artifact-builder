"""
Complete defined product graph.

The defined graph represents the complete set of models, variants,
stages, dependencies, and products known to the artifact builder.

It is derived from the model registry independently of any configured
artifact or realization. Artifact-specific product selection and
dependency closure belong to later realization planning.
"""
# File: src/lowkey_artifact_builder/engine/graph.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from dataclasses import dataclass

from lowkey_artifact_builder.model import (
    ModelRegistry,
    ModelSpec,
    ProductSpec,
    StageSpec,
    VariantSpec,
)

# =========================================================
# Errors
# =========================================================


class DefinedGraphError(RuntimeError):
    """
    Raised when registered model definitions cannot form a valid graph.
    """


# =========================================================
# Defined variants
# =========================================================


@dataclass(
    frozen=True,
    slots=True,
)
class DefinedVariant:
    """
    One model-scoped variant in the complete defined graph.

    The variant retains its declarative VariantSpec as the authoritative
    model definition.
    """

    spec: VariantSpec

    @property
    def name(
        self,
    ) -> str:
        """
        Return the model-scoped variant name.
        """

        return self.spec.name


# =========================================================
# Defined stages
# =========================================================


@dataclass(
    frozen=True,
    slots=True,
)
class DefinedStage:
    """
    One stage in the complete defined graph.

    The stage retains its declarative StageSpec as the authoritative
    model definition while exposing graph-relevant properties directly.
    """

    spec: StageSpec

    @property
    def name(
        self,
    ) -> str:
        """
        Return the semantic stage name.
        """

        return self.spec.name

    @property
    def dependencies(
        self,
    ) -> tuple[str, ...]:
        """
        Return semantic names of stages required by this stage.
        """

        return self.spec.dependencies

    @property
    def products(
        self,
    ) -> tuple[ProductSpec, ...]:
        """
        Return products declared by this stage.
        """

        return self.spec.products


# =========================================================
# Defined models
# =========================================================


@dataclass(
    frozen=True,
    slots=True,
)
class DefinedModel:
    """
    One model in the complete defined graph.

    Variants and stages preserve their declarative model order.
    """

    spec: ModelSpec
    variants: tuple[DefinedVariant, ...]
    stages: tuple[DefinedStage, ...]

    @property
    def name(
        self,
    ) -> str:
        """
        Return the model name.
        """

        return self.spec.name

    def stage(
        self,
        name: str,
    ) -> DefinedStage:
        """
        Return the defined stage with the requested semantic name.

        Raises KeyError when the model does not define the requested
        stage.
        """

        for stage in self.stages:
            if stage.name == name:
                return stage

        raise KeyError(name)


# =========================================================
# Defined graph
# =========================================================


@dataclass(
    frozen=True,
    slots=True,
)
class DefinedGraph:
    """
    Complete graph of registered model definitions.

    Models, variants, and stages preserve registry and model declaration
    order.
    """

    _models: tuple[DefinedModel, ...]

    @property
    def models(
        self,
    ) -> tuple[str, ...]:
        """
        Return registered model names in graph order.
        """

        return tuple(model.name for model in self._models)

    def model(
        self,
        name: str,
    ) -> DefinedModel:
        """
        Return the defined model with the requested name.

        Raises KeyError when the graph does not contain the requested
        model.
        """

        for model in self._models:
            if model.name == name:
                return model

        raise KeyError(name)


# =========================================================
# Graph validation
# =========================================================


def _validate_stage_dependencies(
    model: ModelSpec,
    stage: StageSpec,
    stage_names: set[str],
) -> None:
    """
    Validate dependency targets declared by one stage.

    Dependencies are model-local semantic stage names. Every dependency
    must identify another stage defined by the same model.
    """

    for dependency in stage.dependencies:
        if dependency not in stage_names:
            raise DefinedGraphError(
                f"Stage {stage.name!r} in model {model.name!r} "
                f"depends on unknown stage {dependency!r}."
            )


def _validate_product_identities(
    model: ModelSpec,
) -> None:
    """
    Validate product identities defined by a model.

    A definition-level product identity consists of the model name,
    producing stage name, and product name. Each such identity must be
    unique within the Defined Graph.
    """

    identities: set[tuple[str, str, str]] = set()

    for stage in model.stages:
        for product in stage.products:
            identity = (
                model.name,
                stage.name,
                product.name,
            )

            if identity in identities:
                product_identity = f"{model.name}/{stage.name}/{product.name}"

                raise DefinedGraphError(f"Duplicate product identity {product_identity!r}")

            identities.add(
                identity,
            )


def _validate_acyclic(
    model: ModelSpec,
) -> None:
    """
    Validate that stage dependencies in a model are acyclic.

    Dependency traversal uses semantic stage names. A stage encountered
    while it is already on the active traversal path identifies a
    dependency cycle.
    """

    stages = {stage.name: stage for stage in model.stages}

    visited: set[str] = set()
    active: set[str] = set()

    def visit(
        stage_name: str,
    ) -> None:
        if stage_name in active:
            raise DefinedGraphError(
                f"Dependency cycle detected in model {model.name!r} at stage {stage_name!r}."
            )

        if stage_name in visited:
            return

        active.add(
            stage_name,
        )

        stage = stages[stage_name]

        for dependency in stage.dependencies:
            visit(
                dependency,
            )

        active.remove(
            stage_name,
        )

        visited.add(
            stage_name,
        )

    for stage in model.stages:
        visit(
            stage.name,
        )


# =========================================================
# Graph construction
# =========================================================


def build_defined_graph(
    registry: ModelRegistry,
) -> DefinedGraph:
    """
    Construct and validate the complete Defined Graph.

    The graph contains the registered models, model-scoped variants,
    stages, products, and stage dependencies known to the artifact
    builder. It contains no artifact- or realization-specific state.

    Graph construction validates dependency targets and rejects cyclic
    stage dependencies before returning the completed graph.
    """

    models = tuple(_build_defined_model(model) for model in registry.all_models())

    return DefinedGraph(
        _models=models,
    )


def _build_defined_model(
    model: ModelSpec,
) -> DefinedModel:
    """
    Construct the defined graph representation of one model.

    Every dependency declared by a stage must identify another stage
    defined by the same model. Stage dependencies must form an acyclic
    graph.
    """

    stage_names = {stage.name for stage in model.stages}

    for stage in model.stages:
        _validate_stage_dependencies(
            model,
            stage,
            stage_names,
        )

    _validate_product_identities(
        model,
    )

    _validate_acyclic(
        model,
    )

    variants = tuple(
        DefinedVariant(
            spec=variant,
        )
        for variant in model.variants
    )

    stages = tuple(
        DefinedStage(
            spec=stage,
        )
        for stage in model.stages
    )

    return DefinedModel(
        spec=model,
        variants=variants,
        stages=stages,
    )


# =========================================================
# Exports
# =========================================================


__all__ = [
    "DefinedGraph",
    "DefinedGraphError",
    "DefinedModel",
    "DefinedStage",
    "DefinedVariant",
    "build_defined_graph",
]
