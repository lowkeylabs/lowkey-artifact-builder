"""
Tests for Artwork Outer Ridge Feature configuration and participation.

Outer Ridge is an optional standalone Artwork Feature. Its participation is
determined by the effective artwork_outer_ridge_width rather than by a
separate boolean Feature-selection mechanism.
"""
# File: tests/model/artwork/test_outer_ridge.py
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
from lowkey_artifact_builder.model.models.artwork.outer_ridge import (
    artwork_scale_for_outer_ridge,
)
from lowkey_artifact_builder.model.validation import (
    get_named_model_validators,
    validate_configuration,
)


class StubResolver:
    """
    Minimal resolved-configuration source for Outer Ridge validation tests.
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


def _validate_outer_ridge(
    *,
    width: object = 0.0,
) -> None:
    """
    Apply Artwork validators relevant to Outer Ridge configuration.
    """

    resolver = StubResolver(
        {
            "artwork_outer_ridge_width": width,
        }
    )

    validators = tuple(
        validator
        for validator in get_named_model_validators("artwork")
        if "artwork_outer_ridge_width" in validator.parameters
    )

    validate_configuration(
        resolver,
        validators=validators,
    )


# =========================================================
# Configuration resolution
# =========================================================


def test_outer_ridge_parameters_are_artwork_parameters(
    tmp_path: Path,
) -> None:
    """
    Outer Ridge configuration uses ordinary Artwork parameters.

    Width has a Model default. Raise is a derived configuration value.
    Color may be supplied explicitly or resolved later according to
    Outer Ridge color semantics.
    """

    resolver = get_resolver(
        "example",
        model="artwork",
        project_root=tmp_path,
    )

    assert resolver("artwork_outer_ridge_width") is not None
    assert resolver.has("artwork_outer_ridge_raise")
    assert not resolver.has("artwork_outer_ridge_color")


def test_outer_ridge_is_disabled_by_default(
    tmp_path: Path,
) -> None:
    """
    Ordinary Artwork does not participate in the Outer Ridge Feature.

    Participation is disabled by an effective width of zero.
    """

    resolver = get_resolver(
        "example",
        model="artwork",
        project_root=tmp_path,
    )

    assert resolver("artwork_outer_ridge_width") == 0.0


def test_ordinary_artwork_realization_may_customize_outer_ridge(
    tmp_path: Path,
) -> None:
    """
    An Artifact may enable and configure Outer Ridge directly on an
    ordinary Artwork Realization without requiring a specialized Variant.
    """

    write_artifact_config(
        "example",
        {
            "realizations": {
                "custom": {
                    "model": "artwork",
                    "variant": "default",
                    "parameters": {
                        "artwork_outer_ridge_width": 2.0,
                        "artwork_outer_ridge_raise": 1.5,
                        "artwork_outer_ridge_color": "black",
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

    assert resolver("artwork_outer_ridge_width") == 2.0
    assert resolver("artwork_outer_ridge_raise") == 1.5
    assert resolver("artwork_outer_ridge_color") == "black"


# =========================================================
# Participation and validation
# =========================================================


def test_zero_outer_ridge_width_is_valid_and_disables_outer_ridge() -> None:
    """
    Zero width is the defined disabled state for Outer Ridge.
    """

    _validate_outer_ridge(
        width=0.0,
    )


@pytest.mark.parametrize(
    "width",
    [
        0.1,
        1.0,
        2.5,
    ],
)
def test_positive_outer_ridge_width_is_valid_and_enables_outer_ridge(
    width: float,
) -> None:
    """
    Outer Ridge participates for any positive physical width.
    """

    _validate_outer_ridge(
        width=width,
    )


@pytest.mark.parametrize(
    "width",
    [
        -0.1,
        -1.0,
    ],
)
def test_negative_outer_ridge_width_is_invalid(
    width: float,
) -> None:
    """
    Outer Ridge physical width cannot be negative.
    """

    with pytest.raises(
        ConfigError,
        match="artwork_outer_ridge_width",
    ):
        _validate_outer_ridge(
            width=width,
        )


# =========================================================
# Raise resolution
# =========================================================


def test_outer_ridge_raise_defaults_to_artwork_raise(
    tmp_path: Path,
) -> None:
    """
    Outer Ridge raise derives from the effective Artwork raise when no
    explicit Outer Ridge raise is configured.
    """

    resolver = get_resolver(
        "example",
        model="artwork",
        project_root=tmp_path,
    ).with_values(
        {
            "artwork_raise": 2.25,
        },
        provenance="test",
    )

    assert resolver("artwork_outer_ridge_raise") == 2.25


def test_explicit_outer_ridge_raise_overrides_artwork_raise(
    tmp_path: Path,
) -> None:
    """
    An explicit Outer Ridge raise is independent of Artwork raise.
    """

    resolver = get_resolver(
        "example",
        model="artwork",
        project_root=tmp_path,
    ).with_values(
        {
            "artwork_raise": 2.25,
            "artwork_outer_ridge_raise": 3.5,
        },
        provenance="test",
    )

    assert resolver("artwork_raise") == 2.25
    assert resolver("artwork_outer_ridge_raise") == 3.5


def test_outer_ridge_uniformly_scales_artwork_inside_reserved_perimeter() -> None:
    """
    Outer Ridge width reserves physical space around the size-controlling
    Artwork extent.

    The remaining Artwork is uniformly scaled in X and Y rather than
    independently subtracting ridge width from each occupied dimension.
    """

    scale = artwork_scale_for_outer_ridge(
        artwork_size=40.0,
        outer_ridge_width=2.0,
    )

    assert scale == pytest.approx(0.9)


def test_outer_ridge_uniform_scaling_preserves_artwork_aspect_ratio() -> None:
    """
    Outer Ridge scaling preserves the aspect ratio of a non-square Artwork
    envelope.

    A 40 x 30 mm envelope with a 2 mm Outer Ridge becomes 36 x 27 mm,
    rather than 36 x 26 mm.
    """

    scale = artwork_scale_for_outer_ridge(
        artwork_size=40.0,
        outer_ridge_width=2.0,
    )

    width = 40.0 * scale
    height = 30.0 * scale

    assert width == pytest.approx(36.0)
    assert height == pytest.approx(27.0)
    assert width / height == pytest.approx(40.0 / 30.0)


def test_disabled_outer_ridge_does_not_scale_artwork() -> None:
    """
    Disabled Outer Ridge leaves standalone Artwork at its ordinary size.
    """

    scale = artwork_scale_for_outer_ridge(
        artwork_size=40.0,
        outer_ridge_width=0.0,
    )

    assert scale == pytest.approx(1.0)
