"""
Tests for Artwork Hole Feature configuration and participation.

Hole is an optional subtractive standalone Artwork Feature. Its participation
is determined by the effective artwork_hole_diameter rather than by a separate
boolean Feature-selection mechanism.
"""
# File: tests/model/artwork/test_hole.py
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
    Minimal resolved-configuration source for Hole validation tests.
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


def _validate_hole(
    *,
    diameter: object = 0.0,
    position: object = 0,
    edge_distance: object = 0.4,
) -> None:
    """
    Apply Artwork validators relevant to Hole configuration.
    """

    resolver = StubResolver(
        {
            "artwork_hole_diameter": diameter,
            "artwork_hole_position": position,
            "artwork_hole_edge_distance": edge_distance,
        }
    )

    validators = tuple(
        validator
        for validator in get_named_model_validators("artwork")
        if any(parameter.startswith("artwork_hole_") for parameter in validator.parameters)
    )

    validate_configuration(
        resolver,
        validators=validators,
    )


# =========================================================
# Configuration resolution
# =========================================================


def test_hole_parameters_are_artwork_parameters(
    tmp_path: Path,
) -> None:
    """
    Hole configuration uses ordinary Artwork parameters.
    """

    resolver = get_resolver(
        "example",
        model="artwork",
        project_root=tmp_path,
    )

    assert resolver("artwork_hole_diameter") is not None
    assert resolver("artwork_hole_position") is not None
    assert resolver("artwork_hole_edge_distance") is not None


def test_hole_is_disabled_by_default(
    tmp_path: Path,
) -> None:
    """
    Ordinary Artwork does not participate in the Hole Feature.

    Participation is disabled by an effective diameter of zero.
    """

    resolver = get_resolver(
        "example",
        model="artwork",
        project_root=tmp_path,
    )

    assert resolver("artwork_hole_diameter") == 0.0


def test_ordinary_artwork_realization_may_customize_hole(
    tmp_path: Path,
) -> None:
    """
    An Artifact may enable and configure Hole directly on an ordinary
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
                        "artwork_hole_diameter": 6.0,
                        "artwork_hole_position": 90,
                        "artwork_hole_edge_distance": 1.5,
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

    assert resolver("artwork_hole_diameter") == 6.0
    assert resolver("artwork_hole_position") == 90
    assert resolver("artwork_hole_edge_distance") == 1.5


# =========================================================
# Participation and validation
# =========================================================


def test_zero_hole_diameter_is_valid_and_disables_hole() -> None:
    """
    Zero diameter is the defined disabled state for Hole.
    """

    _validate_hole(
        diameter=0.0,
    )


@pytest.mark.parametrize(
    "diameter",
    [
        -0.1,
        -1.0,
    ],
)
def test_negative_hole_diameter_is_invalid(
    diameter: float,
) -> None:
    """
    Hole diameter cannot be negative.
    """

    with pytest.raises(
        ConfigError,
        match="artwork_hole_diameter",
    ):
        _validate_hole(
            diameter=diameter,
        )


@pytest.mark.parametrize(
    "diameter",
    [
        0.01,
        0.5,
        1.0,
        6.0,
    ],
)
def test_positive_hole_diameter_participates(
    diameter: float,
) -> None:
    """
    Every positive Hole diameter enables participation.

    Hole does not impose an independent minimum positive diameter.
    """

    _validate_hole(
        diameter=diameter,
    )


@pytest.mark.parametrize(
    "edge_distance",
    [
        0.0,
        0.1,
        0.39,
    ],
)
def test_participating_hole_requires_minimum_edge_distance(
    edge_distance: float,
) -> None:
    """
    A participating Hole must leave at least 0.4 mm between the Hole
    edge and the applicable outer Artwork boundary.
    """

    with pytest.raises(
        ConfigError,
        match="artwork_hole_edge_distance",
    ):
        _validate_hole(
            diameter=6.0,
            edge_distance=edge_distance,
        )


def test_participating_hole_accepts_minimum_edge_distance() -> None:
    """
    Exactly 0.4 mm of remaining material is valid.
    """

    _validate_hole(
        diameter=6.0,
        edge_distance=0.4,
    )


def test_disabled_hole_does_not_require_minimum_edge_distance() -> None:
    """
    Hole-specific participating geometry requirements do not apply when
    the Feature is disabled.
    """

    _validate_hole(
        diameter=0.0,
        edge_distance=0.0,
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
def test_hole_accepts_defined_cardinal_positions(
    position: int,
) -> None:
    """
    Hole accepts each cardinal position defined by Artwork.
    """

    _validate_hole(
        diameter=6.0,
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
def test_hole_rejects_unsupported_positions(
    position: object,
) -> None:
    """
    Hole position is restricted to Artwork's defined cardinal positions.
    """

    with pytest.raises(
        ConfigError,
        match="artwork_hole_position",
    ):
        _validate_hole(
            diameter=6.0,
            position=position,
        )
