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

from lowkey_artifact_builder.config import ConfigError, Resolver, get_resolver
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


@pytest.fixture
def shape_resolver(
    tmp_path: Path,
) -> Resolver:
    """
    Construct a production Shape resolver for direct configuration tests.

    Broad configuration-validation tests inherit the Shape model's actual
    defaults and derivations so unrelated new parameters do not require
    maintenance of a duplicate test parameter inventory.

    Execution-boundary tests intentionally continue to use StubResolver so
    unexpected stage parameter resolution remains visible.
    """

    return get_resolver(
        "validation-test",
        model="shape",
        project_root=tmp_path,
    )


def _validate_shape(
    resolver: Resolver,
    values: dict[str, Any],
) -> None:
    """
    Validate explicit Shape values over authoritative production defaults.
    """

    from lowkey_artifact_builder.model.models.shape.validation import (
        VALIDATORS,
    )

    validate_configuration(
        resolver.with_values(
            values,
            provenance="test",
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


def _shape_package_execution_plan(
    *,
    resolver: StubResolver,
    package_state: ProductState,
) -> tuple[
    BuildPlan,
    ExecutionPlan,
]:
    """
    Construct a Shape execution plan with the requested persistent
    state for every package product.
    """

    package_spec = next(stage for stage in MODEL.stages if stage.name == "package")

    package = PlannedStage(
        spec=package_spec,
        inputs=(),
        products=tuple(
            PlannedProduct(
                spec=product,
                path=(Path("/project/artifacts/example/shape/default/40-package") / product.path),
            )
            for product in package_spec.products
        ),
    )

    build_plan = BuildPlan(
        artifact_id="example",
        model=MODEL,
        realization_name="default",
        resolver=resolver,  # type: ignore[arg-type]
        project_root=Path("/project"),
        artifact_dir=Path("/project/artifacts/example"),
        stages=(package,),
    )

    execution_plan = ExecutionPlan(
        artifact_id="example",
        model_name="shape",
        realization="default",
        stages=(
            PlannedStageExecution(
                stage_name="package",
                product_states=tuple(package_state for _ in package.products),
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


def test_shape_outer_ridge_raise_may_equal_negative_base_raise(
    shape_resolver: Resolver,
) -> None:
    """
    A ridge top may be exactly flush with the physical bottom of the base.
    """

    _validate_shape(
        shape_resolver,
        {
            "shape_base_raise": 2.0,
            "shape_outer_ridge_raise": -2.0,
        },
    )


def test_shape_outer_ridge_raise_may_be_above_negative_base_raise(
    shape_resolver: Resolver,
) -> None:
    """
    A ridge top above the physical bottom of the base is valid.
    """

    _validate_shape(
        shape_resolver,
        {
            "shape_base_raise": 2.0,
            "shape_outer_ridge_raise": -1.5,
        },
    )


def test_shape_outer_ridge_raise_cannot_extend_below_base(
    shape_resolver: Resolver,
) -> None:
    """
    A ridge top cannot lie below the physical bottom of the Shape base.
    """

    with pytest.raises(
        ConfigError,
        match="shape_outer_ridge_raise",
    ):
        _validate_shape(
            shape_resolver,
            {
                "shape_base_raise": 2.0,
                "shape_outer_ridge_raise": -2.1,
            },
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


def test_shape_polygon_accepts_three_sides(
    shape_resolver: Resolver,
) -> None:
    """
    A regular polygon may use the minimum supported side count.
    """

    _validate_shape(
        shape_resolver,
        {
            "shape_geometry": "polygon",
            "shape_sides": 3,
            "shape_base_raise": 2.0,
            "shape_outer_ridge_raise": 1.0,
        },
    )


def test_shape_polygon_accepts_more_than_three_sides(
    shape_resolver: Resolver,
) -> None:
    """
    A regular polygon may use any integer side count above the minimum.
    """

    _validate_shape(
        shape_resolver,
        {
            "shape_geometry": "polygon",
            "shape_sides": 8,
            "shape_base_raise": 2.0,
            "shape_outer_ridge_raise": 1.0,
        },
    )


def test_shape_polygon_rejects_fewer_than_three_sides(
    shape_resolver: Resolver,
) -> None:
    """
    Polygon geometry requires at least three sides.
    """

    with pytest.raises(
        ConfigError,
        match="shape_sides",
    ):
        _validate_shape(
            shape_resolver,
            {
                "shape_geometry": "polygon",
                "shape_sides": 2,
                "shape_base_raise": 2.0,
                "shape_outer_ridge_raise": 1.0,
            },
        )


def test_shape_polygon_rejects_non_integer_side_count(
    shape_resolver: Resolver,
) -> None:
    """
    Polygon side count is an integer semantic property.
    """

    with pytest.raises(
        ConfigError,
        match="shape_sides",
    ):
        _validate_shape(
            shape_resolver,
            {
                "shape_geometry": "polygon",
                "shape_sides": 3.5,
                "shape_base_raise": 2.0,
                "shape_outer_ridge_raise": 1.0,
            },
        )


def test_shape_non_polygon_does_not_require_valid_polygon_side_count(
    shape_resolver: Resolver,
) -> None:
    """
    Polygon side-count policy does not constrain non-polygon geometry.
    """

    _validate_shape(
        shape_resolver,
        {
            "shape_geometry": "circle",
            "shape_sides": 2,
            "shape_base_raise": 2.0,
            "shape_outer_ridge_raise": 1.0,
        },
    )


def test_shape_outer_ridge_width_may_be_zero(
    shape_resolver: Resolver,
) -> None:
    """
    Zero ridge width validly disables the outer ridge.
    """

    _validate_shape(
        shape_resolver,
        {
            "shape_outer_ridge_width": 0.0,
        },
    )


def test_shape_outer_ridge_width_may_be_positive(
    shape_resolver: Resolver,
) -> None:
    """
    Positive ridge width validly enables the outer ridge.
    """

    _validate_shape(
        shape_resolver,
        {
            "shape_outer_ridge_width": 2.0,
        },
    )


def test_shape_outer_ridge_width_cannot_be_negative(
    shape_resolver: Resolver,
) -> None:
    """
    Negative outer-ridge width is invalid Shape configuration.
    """

    with pytest.raises(
        ConfigError,
        match="shape_outer_ridge_width",
    ):
        _validate_shape(
            shape_resolver,
            {
                "shape_outer_ridge_width": -0.1,
            },
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
    shape_resolver: Resolver,
    geometry: str,
) -> None:
    """
    Shape accepts every geometry defined by the model contract.
    """

    _validate_shape(
        shape_resolver,
        {
            "shape_geometry": geometry,
        },
    )


def test_shape_rejects_unsupported_geometry(
    shape_resolver: Resolver,
) -> None:
    """
    Shape geometry must be one of the model-defined geometry types.
    """

    with pytest.raises(
        ConfigError,
        match="shape_geometry",
    ):
        _validate_shape(
            shape_resolver,
            {
                "shape_geometry": "triangle",
            },
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


@pytest.mark.parametrize(
    "ridge_style",
    (
        "integrated",
        "separate",
    ),
)
def test_shape_accepts_supported_outer_ridge_style(
    shape_resolver: Resolver,
    ridge_style: str,
) -> None:
    """
    Shape accepts every outer-ridge style defined by the model contract.
    """

    _validate_shape(
        shape_resolver,
        {
            "shape_outer_ridge_style": ridge_style,
        },
    )


def test_shape_rejects_unsupported_outer_ridge_style(
    shape_resolver: Resolver,
) -> None:
    """
    Outer-ridge style must be one of the model-defined styles.
    """

    with pytest.raises(
        ConfigError,
        match="shape_outer_ridge_style",
    ):
        _validate_shape(
            shape_resolver,
            {
                "shape_outer_ridge_style": "detached",
            },
        )


def test_invalid_shape_ridge_style_fails_when_compose_requires_execution() -> None:
    """
    Invalid ridge style is validated when compose must execute.
    """

    resolver = StubResolver(
        {
            "shape_outer_ridge_width": 1.0,
            "shape_outer_ridge_style": "detached",
            "shape_inner_ridge_width": 0.0,
            "shape_inner_to_outer_ridge_dist": 10.0,
        }
    )

    build_plan, execution_plan = _shape_compose_execution_plan(
        resolver=resolver,
        compose_state=ProductState.ABSENT,
    )

    with pytest.raises(
        ConfigError,
        match="shape_outer_ridge_style",
    ):
        validate_execution(
            build_plan,
            execution_plan,
        )


def test_invalid_historical_shape_ridge_style_does_not_block_current_compose() -> None:
    """
    Invalid historical ridge style is irrelevant when compose is current.
    """

    resolver = StubResolver(
        {
            "shape_outer_ridge_width": 1.0,
            "shape_outer_ridge_style": "detached",
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


def test_shape_accepts_nonempty_base_color(
    shape_resolver: Resolver,
) -> None:
    """
    Shape base color may be any nonempty semantic color name.
    """

    _validate_shape(
        shape_resolver,
        {
            "shape_base_color": "test-red",
        },
    )


@pytest.mark.parametrize(
    "base_color",
    (
        "",
        "   ",
        None,
    ),
)
def test_shape_rejects_invalid_base_color(
    shape_resolver: Resolver,
    base_color: object,
) -> None:
    """
    Shape base color must be a nonempty semantic color name.
    """

    with pytest.raises(
        ConfigError,
        match="shape_base_color",
    ):
        _validate_shape(
            shape_resolver,
            {
                "shape_base_color": base_color,
            },
        )


def test_invalid_shape_base_color_fails_when_package_requires_execution() -> None:
    """
    Invalid base color is validated when packaging must execute.
    """

    resolver = StubResolver(
        {
            "shape_raise_style": "raised",
            "shape_base_color": "",
        }
    )

    build_plan, execution_plan = _shape_package_execution_plan(
        resolver=resolver,
        package_state=ProductState.ABSENT,
    )

    with pytest.raises(
        ConfigError,
        match="shape_base_color",
    ):
        validate_execution(
            build_plan,
            execution_plan,
        )


def test_invalid_historical_shape_base_color_does_not_block_current_package() -> None:
    """
    Invalid historical base color is irrelevant when packaging is current.
    """

    resolver = StubResolver(
        {
            "shape_base_color": "",
        }
    )

    build_plan, execution_plan = _shape_package_execution_plan(
        resolver=resolver,
        package_state=ProductState.CURRENT,
    )

    validate_execution(
        build_plan,
        execution_plan,
    )


def test_shape_accepts_nonempty_outer_ridge_color(
    shape_resolver: Resolver,
) -> None:
    """
    Shape outer-ridge color may be any nonempty semantic color name.
    """

    _validate_shape(
        shape_resolver,
        {
            "shape_outer_ridge_color": "test-red",
        },
    )


@pytest.mark.parametrize(
    "ridge_color",
    (
        "",
        "   ",
        None,
    ),
)
def test_shape_rejects_invalid_outer_ridge_color(
    shape_resolver: Resolver,
    ridge_color: object,
) -> None:
    """
    Shape outer-ridge color must be a nonempty semantic color name.
    """

    with pytest.raises(
        ConfigError,
        match="shape_outer_ridge_color",
    ):
        _validate_shape(
            shape_resolver,
            {
                "shape_outer_ridge_color": ridge_color,
            },
        )


def test_invalid_shape_ridge_color_fails_when_package_requires_execution() -> None:
    """
    Invalid outer-ridge color is validated when packaging must execute.
    """
    resolver = StubResolver(
        {
            "shape_raise_style": "raised",
            "shape_base_color": "white",
            "shape_outer_ridge_color": "",
        }
    )

    build_plan, execution_plan = _shape_package_execution_plan(
        resolver=resolver,
        package_state=ProductState.ABSENT,
    )

    with pytest.raises(
        ConfigError,
        match="shape_outer_ridge_color",
    ):
        validate_execution(
            build_plan,
            execution_plan,
        )


def test_invalid_historical_shape_ridge_color_does_not_block_current_package() -> None:
    """
    Invalid historical outer-ridge color is irrelevant when packaging is current.
    """

    resolver = StubResolver(
        {
            "shape_outer_ridge_color": "",
        }
    )

    build_plan, execution_plan = _shape_package_execution_plan(
        resolver=resolver,
        package_state=ProductState.CURRENT,
    )

    validate_execution(
        build_plan,
        execution_plan,
    )


def test_shape_inner_ridge_raise_must_be_nonnegative(
    shape_resolver: Resolver,
) -> None:
    """
    Inner Ridge layers on top of the Base and cannot have negative raise.
    """

    with pytest.raises(
        ConfigError,
        match="shape_inner_ridge_raise must be greater than or equal to zero",
    ):
        _validate_shape(
            shape_resolver,
            {
                "shape_inner_ridge_raise": -0.5,
            },
        )


@pytest.mark.parametrize(
    "text",
    [
        "RICHMOND",
        " RICHMOND ",
    ],
)
def test_border_label_glyph_height_must_be_positive_when_label_participates(
    shape_resolver: Resolver,
    text: str,
) -> None:
    """
    Non-whitespace Border Label text requires a positive maximum glyph height.
    """

    with pytest.raises(
        ConfigError,
        match="shape_border_label_max_glyph_height must be greater than zero",
    ):
        _validate_shape(
            shape_resolver,
            {
                "shape_top_border_label_text": text,
                "shape_border_label_max_glyph_height": 0.0,
            },
        )


@pytest.mark.parametrize(
    "text",
    [
        "",
        "   ",
    ],
)
def test_border_label_glyph_height_not_required_when_label_does_not_participate(
    shape_resolver: Resolver,
    text: str,
) -> None:
    """
    Empty or whitespace-only Border Label text does not cause participation.
    """

    _validate_shape(
        shape_resolver,
        {
            "shape_top_border_label_text": text,
            "shape_bottom_border_label_text": "",
            "shape_border_label_max_glyph_height": 0.0,
        },
    )


@pytest.mark.parametrize(
    ("values", "message"),
    [
        (
            {"shape_border_label_width": -0.1},
            "shape_border_label_width must be greater than or equal to zero",
        ),
        (
            {"shape_border_label_arc_degrees": 0.0},
            "shape_border_label_arc_degrees must be greater than zero and less than 180",
        ),
        (
            {"shape_border_label_arc_degrees": 180.0},
            "shape_border_label_arc_degrees must be greater than zero and less than 180",
        ),
        (
            {"shape_border_label_end_margin": -0.1},
            "shape_border_label_end_margin must be greater than or equal to zero",
        ),
    ],
)
def test_border_label_shared_geometry_parameters_are_valid(
    shape_resolver: Resolver,
    values: dict[str, Any],
    message: str,
) -> None:
    """
    Shared Border Label geometry parameters obey their normative ranges.
    """

    with pytest.raises(
        ConfigError,
        match=message,
    ):
        _validate_shape(shape_resolver, values)


@pytest.mark.parametrize(
    "raise_style",
    (
        "raised",
        "inlaid",
    ),
)
def test_shape_accepts_supported_raise_style(
    shape_resolver: Resolver,
    raise_style: str,
) -> None:
    """
    Shape accepts every raise style defined by the model contract.
    """

    _validate_shape(
        shape_resolver,
        {
            "shape_raise_style": raise_style,
        },
    )


def test_shape_rejects_unsupported_raise_style(
    shape_resolver: Resolver,
) -> None:
    """
    Shape raise style must be one of the model-defined styles.
    """

    with pytest.raises(
        ConfigError,
        match="shape_raise_style",
    ):
        _validate_shape(
            shape_resolver,
            {
                "shape_raise_style": "embedded",
            },
        )


# =========================================================
# Shape Loop validation
# =========================================================


@pytest.mark.parametrize(
    "diameter",
    (
        0.0,
        4.0,
    ),
)
def test_shape_loop_inner_diameter_may_disable_or_enable_loop(
    shape_resolver: Resolver,
    diameter: float,
) -> None:
    """
    Zero Loop inner diameter disables participation; positive enables it.
    """

    _validate_shape(
        shape_resolver,
        {
            "shape_loop_inner_diameter": diameter,
        },
    )


def test_shape_loop_inner_diameter_cannot_be_negative(
    shape_resolver: Resolver,
) -> None:
    """
    Negative Loop inner diameter is invalid.
    """

    with pytest.raises(
        ConfigError,
        match="shape_loop_inner_diameter",
    ):
        _validate_shape(
            shape_resolver,
            {
                "shape_loop_inner_diameter": -0.1,
            },
        )


def test_shape_loop_requires_positive_width_when_participating(
    shape_resolver: Resolver,
) -> None:
    """
    A participating Loop requires positive radial material width.
    """

    with pytest.raises(
        ConfigError,
        match="shape_loop_width",
    ):
        _validate_shape(
            shape_resolver,
            {
                "shape_loop_inner_diameter": 4.0,
                "shape_loop_width": 0.0,
            },
        )


@pytest.mark.parametrize(
    "position",
    (
        0,
        90,
        180,
        -90,
    ),
)
def test_shape_loop_accepts_cardinal_positions_when_participating(
    shape_resolver: Resolver,
    position: int,
) -> None:
    """
    Participating Loop uses the Shape cardinal-position convention.
    """

    _validate_shape(
        shape_resolver,
        {
            "shape_loop_inner_diameter": 4.0,
            "shape_loop_width": 1.0,
            "shape_loop_position": position,
        },
    )


def test_shape_loop_rejects_noncardinal_position_when_participating(
    shape_resolver: Resolver,
) -> None:
    """
    A participating Loop requires one of the defined cardinal positions.
    """

    with pytest.raises(
        ConfigError,
        match="shape_loop_position",
    ):
        _validate_shape(
            shape_resolver,
            {
                "shape_loop_inner_diameter": 4.0,
                "shape_loop_width": 1.0,
                "shape_loop_position": 45,
            },
        )


@pytest.mark.parametrize(
    "raise_value",
    (
        0.0,
        -0.1,
    ),
)
def test_shape_loop_requires_positive_raise_when_participating(
    shape_resolver: Resolver,
    raise_value: float,
) -> None:
    """
    A participating Loop requires a positive resolved Loop raise.

    The resolved raise remains valid configuration under both Shape
    raise styles even though inlaid dimensionalization uses the Base
    thickness as the manufactured Loop height.
    """

    with pytest.raises(
        ConfigError,
        match="shape_loop_raise",
    ):
        _validate_shape(
            shape_resolver,
            {
                "shape_loop_inner_diameter": 4.0,
                "shape_loop_raise": raise_value,
            },
        )


def test_shape_loop_raise_does_not_require_positive_value_when_not_participating(
    shape_resolver: Resolver,
) -> None:
    """
    Loop raise does not constrain configuration when Loop does not participate.
    """

    _validate_shape(
        shape_resolver,
        {
            "shape_loop_inner_diameter": 0.0,
            "shape_loop_raise": 0.0,
        },
    )
