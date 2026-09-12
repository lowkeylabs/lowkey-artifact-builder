"""
Tests for Artwork Loop Feature configuration and participation.

Loop is an optional standalone Artwork Feature. Its participation is
determined by the effective loop_inner_diameter rather than by a separate
boolean Feature-selection mechanism.
"""
# File: tests/model/artwork/test_loop.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path

import pytest

from lowkey_artifact_builder.config import (
    ConfigError,
    get_resolver,
    write_artifact_config,
)
from lowkey_artifact_builder.model.validation import (
    get_named_model_validators,
    validate_configuration,
)


class StubResolver:
    """
    Minimal resolved-configuration source for Loop validation tests.
    """

    def __init__(
        self,
        values: dict[str, object],
    ) -> None:
        self._values = values

    def __call__(
        self,
        name: str,
    ) -> object:
        return self._values[name]


def _validate_loop(
    *,
    inner_diameter: object = 0.0,
    width: object = 1.0,
    position: object = 0,
    raise_: object = 1.0,
    color: object = "white",
) -> None:
    """
    Apply Artwork validators relevant to Loop configuration.
    """

    resolver = StubResolver(
        {
            "loop_inner_diameter": inner_diameter,
            "loop_width": width,
            "loop_position": position,
            "loop_raise": raise_,
            "loop_color": color,
        }
    )

    validators = tuple(
        validator
        for validator in get_named_model_validators("artwork")
        if any(parameter.startswith("loop_") for parameter in validator.parameters)
    )

    validate_configuration(
        resolver,
        validators=validators,
    )


# =========================================================
# Configuration resolution
# =========================================================


def test_loop_parameters_are_artwork_parameters(
    tmp_path: Path,
) -> None:
    """
    Artwork provides ordinary resolved configuration for every Loop
    parameter.

    Loop does not require a specialized Variant or a separate Feature
    selection mechanism.
    """

    resolver = get_resolver(
        "example",
        model="artwork",
        project_root=tmp_path,
    )

    assert resolver("loop_inner_diameter") is not None
    assert resolver("loop_width") is not None
    assert resolver("loop_position") is not None
    assert resolver("loop_raise") is not None
    assert resolver("loop_color") is not None


def test_loop_is_disabled_by_default(
    tmp_path: Path,
) -> None:
    """
    Ordinary Artwork does not participate in the Loop Feature.

    Participation is disabled by an effective inner diameter of zero.
    """

    resolver = get_resolver(
        "example",
        model="artwork",
        project_root=tmp_path,
    )

    assert resolver("loop_inner_diameter") == 0.0


def test_ordinary_artwork_realization_may_customize_loop(
    tmp_path: Path,
) -> None:
    """
    An Artifact may enable and configure Loop directly on an ordinary
    Artwork Realization without requiring a specialized Variant.
    """

    write_artifact_config(
        "example",
        {
            "realizations": {
                "custom": {
                    "model": "artwork",
                    "variant": "default",
                    "parameters": {
                        "loop_inner_diameter": 6.0,
                        "loop_width": 2.0,
                        "loop_position": 90,
                        "loop_raise": 1.5,
                        "loop_color": "black",
                    },
                },
            },
        },
        project_root=tmp_path,
    )

    resolver = get_resolver(
        "example",
        realization="custom",
        project_root=tmp_path,
    )

    assert resolver("model") == "artwork"
    assert resolver("variant") == "default"

    assert resolver("loop_inner_diameter") == 6.0
    assert resolver("loop_width") == 2.0
    assert resolver("loop_position") == 90
    assert resolver("loop_raise") == 1.5
    assert resolver("loop_color") == "black"


# =========================================================
# Participation and validation
# =========================================================


def test_zero_loop_inner_diameter_is_valid_and_disables_loop() -> None:
    """
    Zero inner diameter is the defined disabled state for Loop.
    """

    _validate_loop(
        inner_diameter=0.0,
    )


@pytest.mark.parametrize(
    "inner_diameter",
    [
        -0.1,
        -1.0,
    ],
)
def test_negative_loop_inner_diameter_is_invalid(
    inner_diameter: float,
) -> None:
    """
    Loop inner diameter cannot be negative.
    """

    with pytest.raises(
        ConfigError,
        match="loop_inner_diameter",
    ):
        _validate_loop(
            inner_diameter=inner_diameter,
        )


@pytest.mark.parametrize(
    "inner_diameter",
    [
        0.01,
        0.25,
        0.49,
    ],
)
def test_participating_loop_requires_minimum_inner_diameter(
    inner_diameter: float,
) -> None:
    """
    A nonzero Loop inner diameter must be at least 0.5 mm.
    """

    with pytest.raises(
        ConfigError,
        match="loop_inner_diameter",
    ):
        _validate_loop(
            inner_diameter=inner_diameter,
        )


@pytest.mark.parametrize(
    "inner_diameter",
    [
        0.5,
        1.0,
        6.0,
    ],
)
def test_valid_participating_loop_inner_diameter(
    inner_diameter: float,
) -> None:
    """
    Loop participates for valid inner diameters of at least 0.5 mm.
    """

    _validate_loop(
        inner_diameter=inner_diameter,
    )


@pytest.mark.parametrize(
    "width",
    [
        0.0,
        -0.1,
        -2.0,
    ],
)
def test_participating_loop_requires_positive_width(
    width: float,
) -> None:
    """
    A participating Loop requires positive radial material width.
    """

    with pytest.raises(
        ConfigError,
        match="loop_width",
    ):
        _validate_loop(
            inner_diameter=6.0,
            width=width,
        )


def test_disabled_loop_does_not_require_positive_width() -> None:
    """
    Loop-specific participating geometry requirements do not apply when
    the Feature is disabled.
    """

    _validate_loop(
        inner_diameter=0.0,
        width=0.0,
    )


@pytest.mark.parametrize(
    "position",
    [
        0,
        90,
        180,
        -90,
    ],
)
def test_loop_accepts_defined_cardinal_positions(
    position: int,
) -> None:
    """
    Loop accepts each cardinal attachment position defined by Artwork.
    """

    _validate_loop(
        inner_diameter=6.0,
        position=position,
    )


@pytest.mark.parametrize(
    "position",
    [
        45,
        -45,
        270,
        "top",
    ],
)
def test_loop_rejects_unsupported_positions(
    position: object,
) -> None:
    """
    Loop position is restricted to Artwork's defined cardinal positions.
    """

    with pytest.raises(
        ConfigError,
        match="loop_position",
    ):
        _validate_loop(
            inner_diameter=6.0,
            position=position,
        )


def test_loop_raise_may_be_explicitly_configured() -> None:
    """
    Explicit physical Loop raise is valid Loop configuration.
    """

    _validate_loop(
        inner_diameter=6.0,
        raise_=2.5,
    )


def test_loop_color_may_be_explicitly_configured() -> None:
    """
    Explicit semantic Loop color is valid Loop configuration.
    """

    _validate_loop(
        inner_diameter=6.0,
        color="black",
    )
