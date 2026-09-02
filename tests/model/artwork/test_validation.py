"""
Tests for Artwork model configuration validation.

Artwork owns the semantic invariants governing its configured color count,
envelope mode, and physical color availability.
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
    artifact_color_count: object = 2,
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
            "artifact_color_count": artifact_color_count,
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
    state for every Prepare product.
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
        ("artifact_color_count",),
        ("artwork_envelope_mode",),
        ("printer_colors",),
        ("library_colors",),
    )


@pytest.mark.parametrize(
    "artifact_color_count",
    [
        1,
        3,
        5,
    ],
)
def test_artwork_accepts_positive_artifact_color_count(
    artifact_color_count: int,
) -> None:
    """
    Artwork accepts any positive integer Artifact color count.
    """

    _validate_artwork(
        artifact_color_count=artifact_color_count,
    )


def test_artwork_color_count_may_be_smaller_than_printer_capacity() -> None:
    """
    Artifact color count is independent of printer capacity once
    explicitly resolved.

    A printer may provide more physical colors than the Artwork requests.
    """

    _validate_artwork(
        artifact_color_count=3,
        printer_colors=(
            "red",
            "green",
            "blue",
            "black",
            "white",
        ),
        catalog_colors=(
            "red",
            "green",
            "blue",
            "black",
            "white",
        ),
    )


@pytest.mark.parametrize(
    "artifact_color_count",
    [
        0,
        -1,
        1.5,
        "3",
        True,
    ],
)
def test_artwork_rejects_invalid_artifact_color_count(
    artifact_color_count: object,
) -> None:
    """
    Artifact color count must be a positive integer.

    Boolean values are rejected even though bool is an int subclass.
    """

    with pytest.raises(
        ConfigError,
        match="artifact_color_count",
    ):
        _validate_artwork(
            artifact_color_count=artifact_color_count,
        )


def test_artwork_alpha_envelope_mode_is_valid() -> None:
    """
    Artwork accepts alpha envelope derivation.
    """

    _validate_artwork(
        envelope_mode="alpha",
    )


def test_artwork_shrink_wrap_envelope_mode_is_valid() -> None:
    """
    Artwork accepts shrink-wrap envelope derivation.
    """

    _validate_artwork(
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
            library_colors=(
                "green",
                "unknown",
            ),
            catalog_colors=(
                "green",
                "gold",
            ),
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
            library_colors=(
                "red",
                42,
            ),
            catalog_colors=("red",),
        )


# =========================================================
# Execution-scoped Artwork validation
# =========================================================


def test_invalid_artifact_color_count_fails_when_prepare_requires_execution() -> None:
    """
    Artifact color count is validated when Prepare must execute.
    """

    resolver = StubResolver(
        {
            "artifact_color_count": 0,
            "artwork_envelope_mode": "alpha",
        }
    )

    build_plan, execution_plan = _artwork_execution_plan(
        resolver=resolver,
        prepare_state=ProductState.ABSENT,
    )

    with pytest.raises(
        ConfigError,
        match="artifact_color_count",
    ):
        validate_execution(
            build_plan,
            execution_plan,
        )


def test_invalid_historical_artifact_color_count_does_not_block_current_prepare() -> None:
    """
    Invalid historical Artwork configuration is not revalidated when
    Prepare is already current and therefore does not execute.
    """

    resolver = StubResolver(
        {
            "artifact_color_count": 0,
            "artwork_envelope_mode": "alpha",
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


def test_invalid_printer_colors_do_not_block_prepare_execution() -> None:
    """
    Invalid printer availability does not block Prepare.

    Printer colors belong to Raster execution rather than source
    preparation.
    """

    resolver = StubResolver(
        {
            "artifact_color_count": 3,
            "artwork_envelope_mode": "alpha",
            "printer_colors": ("unknown",),
            "library_colors": (),
        },
        colors={},
    )

    build_plan, execution_plan = _artwork_execution_plan(
        resolver=resolver,
        prepare_state=ProductState.ABSENT,
    )

    validate_execution(
        build_plan,
        execution_plan,
    )


def test_invalid_library_colors_do_not_block_prepare_execution() -> None:
    """
    Invalid library availability does not block Prepare.

    Library colors are not required to prepare registered Artwork.
    """

    resolver = StubResolver(
        {
            "artifact_color_count": 3,
            "artwork_envelope_mode": "alpha",
            "printer_colors": (),
            "library_colors": ("unknown",),
        },
        colors={},
    )

    build_plan, execution_plan = _artwork_execution_plan(
        resolver=resolver,
        prepare_state=ProductState.ABSENT,
    )

    validate_execution(
        build_plan,
        execution_plan,
    )
