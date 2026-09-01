"""
Tests for Artwork model configuration validation.

Artwork owns the semantic invariants governing its configured palette,
fill color, envelope mode, and color availability.
"""
# File: tests/model/artwork/test_validation.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path

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
from lowkey_artifact_builder.model.models.artwork import MODEL
from lowkey_artifact_builder.model.validation import (
    get_named_model_validators,
    validate_configuration,
)


class StubResolver:
    """
    Minimal resolved-configuration source for Artwork validation tests.
    """

    def __init__(
        self,
        values: dict[str, object],
        *,
        colors: dict[str, object] | None = None,
    ) -> None:
        self._values = values
        self._colors = colors or {}

    def __call__(
        self,
        name: str,
    ) -> object:
        return self._values[name]

    def has_color(
        self,
        name: str,
    ) -> bool:
        """
        Return whether the test color catalog contains a color.
        """

        return name in self._colors


def _validate_artwork(
    *,
    colors: object,
    fill_color: object,
    envelope_mode: object = "alpha",
    printer_colors: object = (),
    library_colors: object = (),
    catalog_colors: tuple[str, ...] = (),
) -> None:
    """
    Apply the Artwork model's declared configuration validators.
    """

    resolver = StubResolver(
        {
            "artwork_colors": colors,
            "artwork_fill_color": fill_color,
            "artwork_envelope_mode": envelope_mode,
            "printer_colors": printer_colors,
            "library_colors": library_colors,
        },
        colors={name: {} for name in catalog_colors},
    )

    validate_configuration(
        resolver,
        validators=get_named_model_validators(
            "artwork",
        ),
    )


def _artwork_execution_plan(
    *,
    resolver: StubResolver,
    prepare_state: ProductState,
) -> tuple[
    BuildPlan,
    ExecutionPlan,
]:
    """
    Construct an Artwork execution plan with the requested persistent
    state for every prepare product.
    """

    prepare_spec = next(stage for stage in MODEL.stages if stage.name == "prepare")

    prepare = PlannedStage(
        spec=prepare_spec,
        inputs=(),
        products=tuple(
            PlannedProduct(
                spec=product,
                path=(Path("/project/artifacts/example/artwork/default/10-prepare") / product.path),
            )
            for product in prepare_spec.products
        ),
    )

    build_plan = BuildPlan(
        artifact_id="example",
        model=MODEL,
        realization_name="default",
        resolver=resolver,  # type: ignore[arg-type]
        project_root=Path("/project"),
        artifact_dir=Path("/project/artifacts/example"),
        stages=(prepare,),
    )

    execution_plan = ExecutionPlan(
        artifact_id="example",
        model_name="artwork",
        realization="default",
        stages=(
            PlannedStageExecution(
                stage_name="prepare",
                product_states=tuple(prepare_state for _ in prepare.products),
            ),
        ),
    )

    return (
        build_plan,
        execution_plan,
    )


# =========================================================
# Artwork configuration validation
# =========================================================


def test_artwork_declares_configuration_validators() -> None:
    """
    Artwork owns validators governing its model-specific configuration
    invariants.
    """

    validators = get_named_model_validators(
        "artwork",
    )

    assert tuple(validator.parameters for validator in validators) == (
        (
            "artwork_colors",
            "artwork_fill_color",
        ),
        ("artwork_envelope_mode",),
        ("printer_colors",),
        ("library_colors",),
    )


def test_artwork_fill_color_may_be_non_white_palette_member() -> None:
    """
    Artwork accepts an explicitly configured non-white fill color when
    that color belongs to the configured palette.
    """

    _validate_artwork(
        colors=(
            "red",
            "blue",
        ),
        fill_color="red",
    )


def test_artwork_palette_does_not_require_white() -> None:
    """
    White has no special membership requirement in the Artwork palette.
    """

    _validate_artwork(
        colors=(
            "red",
            "blue",
        ),
        fill_color="blue",
    )


def test_artwork_fill_color_must_belong_to_palette() -> None:
    """
    Artwork rejects a resolved fill color absent from artwork_colors.
    """

    with pytest.raises(
        ConfigError,
        match="artwork_fill_color",
    ):
        _validate_artwork(
            colors=(
                "red",
                "blue",
            ),
            fill_color="green",
        )


def test_artwork_default_white_fill_color_is_valid_palette_member() -> None:
    """
    Artwork accepts the default white fill color when white belongs to
    the configured palette.
    """

    _validate_artwork(
        colors=(
            "white",
            "black",
        ),
        fill_color="white",
    )


def test_artwork_fill_color_membership_uses_semantic_color_name() -> None:
    """
    Artwork fill-color membership is determined by semantic color identity.
    """

    with pytest.raises(
        ConfigError,
        match="artwork_fill_color",
    ):
        _validate_artwork(
            colors=(
                "white",
                "black",
            ),
            fill_color="test-white",
        )


def test_artwork_alpha_envelope_mode_is_valid() -> None:
    """
    Artwork accepts alpha envelope derivation.
    """

    _validate_artwork(
        colors=(
            "white",
            "black",
        ),
        fill_color="white",
        envelope_mode="alpha",
    )


def test_artwork_shrink_wrap_envelope_mode_is_valid() -> None:
    """
    Artwork accepts shrink-wrap envelope derivation.
    """

    _validate_artwork(
        colors=(
            "white",
            "black",
        ),
        fill_color="white",
        envelope_mode="shrink-wrap",
    )


def test_artwork_rejects_unsupported_envelope_mode() -> None:
    """
    Artwork rejects envelope modes outside its defined model semantics.
    """

    with pytest.raises(
        ConfigError,
        match="artwork_envelope_mode",
    ):
        _validate_artwork(
            colors=(
                "white",
                "black",
            ),
            fill_color="white",
            envelope_mode="aggressive",
        )


def test_artwork_rejects_non_string_envelope_mode() -> None:
    """
    Artwork envelope mode must be a semantic mode name.
    """

    with pytest.raises(
        ConfigError,
        match="artwork_envelope_mode",
    ):
        _validate_artwork(
            colors=(
                "white",
                "black",
            ),
            fill_color="white",
            envelope_mode=42,
        )


# =========================================================
# Artwork color-availability validation
# =========================================================


def test_artwork_accepts_known_printer_colors() -> None:
    """
    Artwork accepts printer colors that reference known catalog colors.
    """

    _validate_artwork(
        colors=(
            "white",
            "black",
        ),
        fill_color="white",
        printer_colors=(
            "red",
            "blue",
        ),
        catalog_colors=(
            "red",
            "blue",
        ),
    )


def test_artwork_rejects_unknown_printer_color() -> None:
    """
    Artwork rejects printer colors absent from the shared color catalog.
    """

    with pytest.raises(
        ConfigError,
        match="printer_colors",
    ):
        _validate_artwork(
            colors=(
                "white",
                "black",
            ),
            fill_color="white",
            printer_colors=(
                "red",
                "unknown",
            ),
            catalog_colors=(
                "red",
                "blue",
            ),
        )


def test_artwork_accepts_known_library_colors() -> None:
    """
    Artwork accepts library colors that reference known catalog colors.
    """

    _validate_artwork(
        colors=(
            "white",
            "black",
        ),
        fill_color="white",
        library_colors=(
            "green",
            "gold",
        ),
        catalog_colors=(
            "green",
            "gold",
        ),
    )


def test_artwork_rejects_unknown_library_color() -> None:
    """
    Artwork rejects library colors absent from the shared color catalog.
    """

    with pytest.raises(
        ConfigError,
        match="library_colors",
    ):
        _validate_artwork(
            colors=(
                "white",
                "black",
            ),
            fill_color="white",
            library_colors=(
                "green",
                "unknown",
            ),
            catalog_colors=(
                "green",
                "gold",
            ),
        )


# =========================================================
# Execution-scoped Artwork validation
# =========================================================


def test_invalid_artwork_fill_color_fails_when_prepare_requires_execution() -> None:
    """
    Artwork fill-color membership is validated when preparation must
    execute.
    """

    resolver = StubResolver(
        {
            "artwork_colors": (
                "red",
                "blue",
            ),
            "artwork_fill_color": "green",
        }
    )

    build_plan, execution_plan = _artwork_execution_plan(
        resolver=resolver,
        prepare_state=ProductState.ABSENT,
    )

    with pytest.raises(
        ConfigError,
        match="artwork_fill_color",
    ):
        validate_execution(
            build_plan,
            execution_plan,
        )


def test_invalid_historical_artwork_fill_color_does_not_block_current_prepare() -> None:
    """
    Invalid historical Artwork configuration is not revalidated when
    preparation is already current and therefore does not execute.
    """

    resolver = StubResolver(
        {
            "artwork_colors": (
                "red",
                "blue",
            ),
            "artwork_fill_color": "green",
        }
    )

    build_plan, execution_plan = _artwork_execution_plan(
        resolver=resolver,
        prepare_state=ProductState.CURRENT,
    )

    validate_execution(
        build_plan,
        execution_plan,
    )


def test_artwork_rejects_non_sequence_printer_colors() -> None:
    """
    Artwork printer_colors must be a sequence of semantic color names.
    """

    with pytest.raises(
        ConfigError,
        match="printer_colors",
    ):
        _validate_artwork(
            colors=(
                "white",
                "black",
            ),
            fill_color="white",
            printer_colors="red",
            catalog_colors=("red",),
        )


def test_artwork_rejects_non_string_printer_color() -> None:
    """
    Every printer_colors entry must be a semantic color name.
    """

    with pytest.raises(
        ConfigError,
        match="printer_colors",
    ):
        _validate_artwork(
            colors=(
                "white",
                "black",
            ),
            fill_color="white",
            printer_colors=(
                "red",
                42,
            ),
            catalog_colors=("red",),
        )


def test_artwork_rejects_non_sequence_library_colors() -> None:
    """
    Artwork library_colors must be a sequence of semantic color names.
    """

    with pytest.raises(
        ConfigError,
        match="library_colors",
    ):
        _validate_artwork(
            colors=(
                "white",
                "black",
            ),
            fill_color="white",
            library_colors="red",
            catalog_colors=("red",),
        )


def test_artwork_rejects_non_string_library_color() -> None:
    """
    Every library_colors entry must be a semantic color name.
    """

    with pytest.raises(
        ConfigError,
        match="library_colors",
    ):
        _validate_artwork(
            colors=(
                "white",
                "black",
            ),
            fill_color="white",
            library_colors=(
                "red",
                42,
            ),
            catalog_colors=("red",),
        )
