"""
Tests for Shape model configuration validation.

Shape owns semantic invariants relating its resolved physical
configuration. Validation follows the execution plan so historical
configuration is not revalidated when its persistent product is
already current.
"""
# File: tests/model/shape/test_validation.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from lowkey_artifact_builder.config import ConfigError
from lowkey_artifact_builder.engine import (
    BuildPlan,
    ExecutionPlan,
    PlannedProduct,
    PlannedStage,
    PlannedStageExecution,
    ProductState,
)
from lowkey_artifact_builder.engine.validation import validate_execution
from lowkey_artifact_builder.model.models.shape import MODEL
from lowkey_artifact_builder.model.validation import (
    validate_configuration,
)

# =========================================================
# Test support
# =========================================================


class StubResolver:
    """
    Minimal resolved configuration for Shape validation tests.
    """

    def __init__(
        self,
        values: dict[str, Any],
    ) -> None:
        self._values = values

    def __call__(
        self,
        name: str,
    ) -> Any:
        return self._values[name]


def _validate_shape(
    values: dict[str, Any],
) -> None:
    """
    Validate resolved Shape configuration using the model validators.
    """

    from lowkey_artifact_builder.model.models.shape.validation import (
        VALIDATORS,
    )

    validate_configuration(
        StubResolver(
            values,
        ),
        validators=VALIDATORS,
    )


def _shape_execution_plan(
    *,
    resolver: StubResolver,
    extrude_state: ProductState,
) -> tuple[
    BuildPlan,
    ExecutionPlan,
]:
    """
    Construct a Shape execution plan with the requested persistent
    state for every extrude product.
    """

    extrude_spec = next(stage for stage in MODEL.stages if stage.name == "extrude")

    extrude = PlannedStage(
        spec=extrude_spec,
        inputs=(),
        products=tuple(
            PlannedProduct(
                spec=product,
                path=(Path("/project/artifacts/example/shape/default/30-extrude") / product.path),
            )
            for product in extrude_spec.products
        ),
    )

    build_plan = BuildPlan(
        artifact_id="example",
        model=MODEL,
        realization_name="default",
        resolver=resolver,  # type: ignore[arg-type]
        project_root=Path("/project"),
        artifact_dir=Path("/project/artifacts/example"),
        stages=(extrude,),
    )

    execution_plan = ExecutionPlan(
        artifact_id="example",
        model_name="shape",
        realization="default",
        stages=(
            PlannedStageExecution(
                stage_name="extrude",
                product_states=tuple(extrude_state for _ in extrude.products),
            ),
        ),
    )

    return (
        build_plan,
        execution_plan,
    )


# =========================================================
# Shape configuration validation
# =========================================================


def test_shape_outer_ridge_raise_may_equal_negative_base_raise() -> None:
    """
    A ridge top may be exactly flush with the physical bottom of the base.
    """

    _validate_shape(
        {
            "shape_base_raise": 2.0,
            "shape_outer_ridge_raise": -2.0,
        }
    )


def test_shape_outer_ridge_raise_may_be_above_negative_base_raise() -> None:
    """
    A ridge top above the physical bottom of the base is valid.
    """

    _validate_shape(
        {
            "shape_base_raise": 2.0,
            "shape_outer_ridge_raise": -1.5,
        }
    )


def test_shape_outer_ridge_raise_cannot_extend_below_base() -> None:
    """
    A ridge top cannot lie below the physical bottom of the Shape base.
    """

    with pytest.raises(
        ConfigError,
        match="shape_outer_ridge_raise",
    ):
        _validate_shape(
            {
                "shape_base_raise": 2.0,
                "shape_outer_ridge_raise": -2.1,
            }
        )


# =========================================================
# Execution-scoped Shape validation
# =========================================================


def test_invalid_shape_ridge_raise_fails_when_extrude_requires_execution() -> None:
    """
    Shape ridge/base configuration is validated when extrusion must
    execute.
    """

    resolver = StubResolver(
        {
            "shape_base_raise": 2.0,
            "shape_outer_ridge_raise": -2.1,
        }
    )

    build_plan, execution_plan = _shape_execution_plan(
        resolver=resolver,
        extrude_state=ProductState.ABSENT,
    )

    with pytest.raises(
        ConfigError,
        match="shape_outer_ridge_raise",
    ):
        validate_execution(
            build_plan,
            execution_plan,
        )


def test_invalid_historical_shape_ridge_raise_does_not_block_current_extrude() -> None:
    """
    Invalid historical Shape ridge/base configuration is not
    revalidated when extrusion is already current.
    """

    resolver = StubResolver(
        {
            "shape_base_raise": 2.0,
            "shape_outer_ridge_raise": -2.1,
        }
    )

    build_plan, execution_plan = _shape_execution_plan(
        resolver=resolver,
        extrude_state=ProductState.CURRENT,
    )

    validate_execution(
        build_plan,
        execution_plan,
    )
