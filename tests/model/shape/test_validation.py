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

    resolved_values: dict[str, Any] = {
        "shape_geometry": "circle",
        "shape_sides": 8,
        "shape_base_raise": 2.0,
        "shape_outer_ridge_width": 0.0,
        "shape_outer_ridge_raise": 1.0,
    }

    resolved_values.update(
        values,
    )

    validate_configuration(
        StubResolver(
            resolved_values,
        ),
        validators=VALIDATORS,
    )


def _shape_compose_execution_plan(
    *,
    resolver: StubResolver,
    compose_state: ProductState,
) -> tuple[
    BuildPlan,
    ExecutionPlan,
]:
    """
    Construct a Shape execution plan with the requested persistent
    state for every compose product.
    """

    compose_spec = next(stage for stage in MODEL.stages if stage.name == "compose")

    compose = PlannedStage(
        spec=compose_spec,
        inputs=(),
        products=tuple(
            PlannedProduct(
                spec=product,
                path=(Path("/project/artifacts/example/shape/default/20-compose") / product.path),
            )
            for product in compose_spec.products
        ),
    )

    build_plan = BuildPlan(
        artifact_id="example",
        model=MODEL,
        realization_name="default",
        resolver=resolver,  # type: ignore[arg-type]
        project_root=Path("/project"),
        artifact_dir=Path("/project/artifacts/example"),
        stages=(compose,),
    )

    execution_plan = ExecutionPlan(
        artifact_id="example",
        model_name="shape",
        realization="default",
        stages=(
            PlannedStageExecution(
                stage_name="compose",
                product_states=tuple(compose_state for _ in compose.products),
            ),
        ),
    )

    return (
        build_plan,
        execution_plan,
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


def _shape_structure_execution_plan(
    *,
    resolver: StubResolver,
    structure_state: ProductState,
) -> tuple[
    BuildPlan,
    ExecutionPlan,
]:
    """
    Construct a Shape execution plan with the requested persistent
    state for every structure product.
    """

    structure_spec = next(stage for stage in MODEL.stages if stage.name == "structure")

    structure = PlannedStage(
        spec=structure_spec,
        inputs=(),
        products=tuple(
            PlannedProduct(
                spec=product,
                path=(Path("/project/artifacts/example/shape/default/10-structure") / product.path),
            )
            for product in structure_spec.products
        ),
    )

    build_plan = BuildPlan(
        artifact_id="example",
        model=MODEL,
        realization_name="default",
        resolver=resolver,  # type: ignore[arg-type]
        project_root=Path("/project"),
        artifact_dir=Path("/project/artifacts/example"),
        stages=(structure,),
    )

    execution_plan = ExecutionPlan(
        artifact_id="example",
        model_name="shape",
        realization="default",
        stages=(
            PlannedStageExecution(
                stage_name="structure",
                product_states=tuple(structure_state for _ in structure.products),
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


def test_invalid_polygon_sides_fail_when_structure_requires_execution() -> None:
    """
    Polygon side-count configuration is validated when structural
    geometry must be produced.
    """

    resolver = StubResolver(
        {
            "shape_geometry": "polygon",
            "shape_sides": 2,
        }
    )

    build_plan, execution_plan = _shape_structure_execution_plan(
        resolver=resolver,
        structure_state=ProductState.ABSENT,
    )

    with pytest.raises(
        ConfigError,
        match="shape_sides",
    ):
        validate_execution(
            build_plan,
            execution_plan,
        )


def test_invalid_historical_polygon_sides_do_not_block_current_structure() -> None:
    """
    Invalid historical polygon configuration is not revalidated when
    structural geometry is already current.
    """

    resolver = StubResolver(
        {
            "shape_geometry": "polygon",
            "shape_sides": 2,
        }
    )

    build_plan, execution_plan = _shape_structure_execution_plan(
        resolver=resolver,
        structure_state=ProductState.CURRENT,
    )

    validate_execution(
        build_plan,
        execution_plan,
    )


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


def test_shape_polygon_accepts_three_sides() -> None:
    """
    A regular polygon may use the minimum supported side count.
    """

    _validate_shape(
        {
            "shape_geometry": "polygon",
            "shape_sides": 3,
            "shape_base_raise": 2.0,
            "shape_outer_ridge_raise": 1.0,
        }
    )


def test_shape_polygon_accepts_more_than_three_sides() -> None:
    """
    A regular polygon may use any integer side count above the minimum.
    """

    _validate_shape(
        {
            "shape_geometry": "polygon",
            "shape_sides": 8,
            "shape_base_raise": 2.0,
            "shape_outer_ridge_raise": 1.0,
        }
    )


def test_shape_polygon_rejects_fewer_than_three_sides() -> None:
    """
    Polygon geometry requires at least three sides.
    """

    with pytest.raises(
        ConfigError,
        match="shape_sides",
    ):
        _validate_shape(
            {
                "shape_geometry": "polygon",
                "shape_sides": 2,
                "shape_base_raise": 2.0,
                "shape_outer_ridge_raise": 1.0,
            }
        )


def test_shape_polygon_rejects_non_integer_side_count() -> None:
    """
    Polygon side count is an integer semantic property.
    """

    with pytest.raises(
        ConfigError,
        match="shape_sides",
    ):
        _validate_shape(
            {
                "shape_geometry": "polygon",
                "shape_sides": 3.5,
                "shape_base_raise": 2.0,
                "shape_outer_ridge_raise": 1.0,
            }
        )


def test_shape_non_polygon_does_not_require_valid_polygon_side_count() -> None:
    """
    Polygon side-count policy does not constrain non-polygon geometry.
    """

    _validate_shape(
        {
            "shape_geometry": "circle",
            "shape_sides": 2,
            "shape_base_raise": 2.0,
            "shape_outer_ridge_raise": 1.0,
        }
    )


def test_shape_outer_ridge_width_may_be_zero() -> None:
    """
    Zero ridge width validly disables the outer ridge.
    """

    _validate_shape(
        {
            "shape_outer_ridge_width": 0.0,
        }
    )


def test_shape_outer_ridge_width_may_be_positive() -> None:
    """
    Positive ridge width validly enables the outer ridge.
    """

    _validate_shape(
        {
            "shape_outer_ridge_width": 2.0,
        }
    )


def test_shape_outer_ridge_width_cannot_be_negative() -> None:
    """
    Negative outer-ridge width is invalid Shape configuration.
    """

    with pytest.raises(
        ConfigError,
        match="shape_outer_ridge_width",
    ):
        _validate_shape(
            {
                "shape_outer_ridge_width": -0.1,
            }
        )


def test_invalid_shape_ridge_width_fails_when_compose_requires_execution() -> None:
    """
    Invalid ridge width is validated when composition must execute.
    """

    resolver = StubResolver(
        {
            "shape_outer_ridge_width": -0.1,
        }
    )

    build_plan, execution_plan = _shape_compose_execution_plan(
        resolver=resolver,
        compose_state=ProductState.ABSENT,
    )

    with pytest.raises(
        ConfigError,
        match="shape_outer_ridge_width",
    ):
        validate_execution(
            build_plan,
            execution_plan,
        )


def test_invalid_historical_shape_ridge_width_does_not_block_current_compose() -> None:
    """
    Invalid historical ridge width is not revalidated when composition
    products are already current.
    """

    resolver = StubResolver(
        {
            "shape_outer_ridge_width": -0.1,
        }
    )

    build_plan, execution_plan = _shape_compose_execution_plan(
        resolver=resolver,
        compose_state=ProductState.CURRENT,
    )

    validate_execution(
        build_plan,
        execution_plan,
    )


@pytest.mark.parametrize(
    "geometry",
    (
        "circle",
        "square",
        "polygon",
    ),
)
def test_shape_accepts_supported_geometry(
    geometry: str,
) -> None:
    """
    Shape accepts every geometry defined by the model contract.
    """

    _validate_shape(
        {
            "shape_geometry": geometry,
        }
    )


def test_shape_rejects_unsupported_geometry() -> None:
    """
    Shape geometry must be one of the model-defined geometry types.
    """

    with pytest.raises(
        ConfigError,
        match="shape_geometry",
    ):
        _validate_shape(
            {
                "shape_geometry": "triangle",
            }
        )


def test_invalid_shape_geometry_fails_when_structure_requires_execution() -> None:
    """
    Invalid Shape geometry is validated when structure must execute.
    """

    resolver = StubResolver(
        {
            "shape_geometry": "triangle",
            "shape_sides": 8,
            "shape_rotation": 0.0,
        }
    )

    build_plan, execution_plan = _shape_structure_execution_plan(
        resolver=resolver,
        structure_state=ProductState.ABSENT,
    )

    with pytest.raises(
        ConfigError,
        match="shape_geometry",
    ):
        validate_execution(
            build_plan,
            execution_plan,
        )


def test_invalid_historical_shape_geometry_does_not_block_current_structure() -> None:
    """
    Invalid historical geometry is irrelevant when structure is current.
    """

    resolver = StubResolver(
        {
            "shape_geometry": "triangle",
            "shape_sides": 8,
            "shape_rotation": 0.0,
        }
    )

    build_plan, execution_plan = _shape_structure_execution_plan(
        resolver=resolver,
        structure_state=ProductState.CURRENT,
    )

    validate_execution(
        build_plan,
        execution_plan,
    )
