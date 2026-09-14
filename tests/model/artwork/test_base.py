"""
Tests for Artwork Base Feature configuration and participation.

Base is an optional standalone Artwork Feature. Its participation is
determined by the effective artwork_base_raise rather than by a separate
boolean Feature-selection mechanism.
"""
# File: tests/model/artwork/test_base.py
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
    Minimal resolved-configuration source for Base validation tests.
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


def _validate_base(
    *,
    raise_: object = 0.0,
) -> None:
    """
    Apply Artwork validators relevant to Base configuration.
    """

    resolver = StubResolver(
        {
            "artwork_base_raise": raise_,
        }
    )

    validators = tuple(
        validator
        for validator in get_named_model_validators("artwork")
        if "artwork_base_raise" in validator.parameters
    )

    validate_configuration(
        resolver,
        validators=validators,
    )


# =========================================================
# Configuration resolution
# =========================================================


def test_base_parameters_are_artwork_parameters(
    tmp_path: Path,
) -> None:
    """
    Base configuration uses ordinary Artwork parameters.

    Base raise has a Model default. Base color may instead be supplied
    explicitly or resolved later from Registered Artwork and Loop state.
    """

    resolver = get_resolver(
        "example",
        model="artwork",
        project_root=tmp_path,
    )

    assert resolver("artwork_base_raise") is not None
    assert not resolver.has("artwork_base_color")


def test_base_is_disabled_by_default(
    tmp_path: Path,
) -> None:
    """
    Ordinary Artwork does not participate in the Base Feature.

    Participation is disabled by an effective Base raise of zero.
    """

    resolver = get_resolver(
        "example",
        model="artwork",
        project_root=tmp_path,
    )

    assert resolver("artwork_base_raise") == 0.0


def test_ordinary_artwork_realization_may_customize_base(
    tmp_path: Path,
) -> None:
    """
    An Artifact may enable and configure Base directly on an ordinary
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
                        "artwork_base_raise": 1.5,
                        "artwork_base_color": "black",
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

    assert resolver("artwork_base_raise") == 1.5
    assert resolver("artwork_base_color") == "black"


# =========================================================
# Participation and validation
# =========================================================


def test_zero_base_raise_is_valid_and_disables_base() -> None:
    """
    Zero Base raise is the defined disabled state for Base.
    """

    _validate_base(
        raise_=0.0,
    )


@pytest.mark.parametrize(
    "raise_",
    [
        0.1,
        1.0,
        2.5,
    ],
)
def test_positive_base_raise_is_valid_and_enables_base(
    raise_: float,
) -> None:
    """
    Base participates for any positive physical Base raise.
    """

    _validate_base(
        raise_=raise_,
    )


@pytest.mark.parametrize(
    "raise_",
    [
        -0.1,
        -1.0,
    ],
)
def test_negative_base_raise_is_invalid(
    raise_: float,
) -> None:
    """
    Base physical raise cannot be negative.
    """

    with pytest.raises(
        ConfigError,
        match="artwork_base_raise",
    ):
        _validate_base(
            raise_=raise_,
        )


# =========================================================
# Planar geometry
# =========================================================


def test_base_uses_registered_artwork_envelope(
    tmp_path: Path,
) -> None:
    """
    Base planar geometry is derived from the registered Artwork envelope.

    The Base imports the envelope itself rather than any individual Artwork
    color layer.
    """

    from lowkey_artifact_builder.model.models.artwork.stages.extrude import (
        _build_base_scad,
    )

    envelope = tmp_path / "envelope.svg"
    envelope.write_text(
        "<svg/>",
        encoding="utf-8",
    )

    source = _build_base_scad(
        envelope,
        registered_extent=1024,
        envelope_bounds=(
            100.0,
            200.0,
            900.0,
            700.0,
        ),
        artwork_size=100.0,
        base_raise=1.0,
    )

    assert str(envelope.resolve()) in source


def test_base_uses_artwork_envelope_for_physical_scale(
    tmp_path: Path,
) -> None:
    """
    Base uses the same size-controlled envelope dimensionalization as
    standalone Artwork.

    The maximum registered envelope extent therefore determines the common
    physical scale.
    """

    from lowkey_artifact_builder.model.models.artwork.stages.extrude import (
        _build_base_scad,
    )

    envelope = tmp_path / "envelope.svg"
    envelope.write_text(
        "<svg/>",
        encoding="utf-8",
    )

    source = _build_base_scad(
        envelope,
        registered_extent=1024,
        envelope_bounds=(
            100.0,
            200.0,
            900.0,
            700.0,
        ),
        artwork_size=100.0,
        base_raise=1.0,
    )

    assert "envelope_width = 800;" in source
    assert "envelope_height = 500;" in source
    assert "envelope_extent = 800;" in source
    assert "artwork_size = 100;" in source

    assert "artwork_size / envelope_extent" in source


def test_base_uses_artwork_envelope_for_physical_centering(
    tmp_path: Path,
) -> None:
    """
    Base uses the registered Artwork envelope center when dimensionalizing
    into standalone physical coordinates.

    This preserves registration between Base and Artwork proper.
    """

    from lowkey_artifact_builder.model.models.artwork.stages.extrude import (
        _build_base_scad,
    )

    envelope = tmp_path / "envelope.svg"
    envelope.write_text(
        "<svg/>",
        encoding="utf-8",
    )

    source = _build_base_scad(
        envelope,
        registered_extent=1024,
        envelope_bounds=(
            100.0,
            200.0,
            900.0,
            700.0,
        ),
        artwork_size=100.0,
        base_raise=1.0,
    )

    # Registered envelope center:
    #
    #     x = (100 + 900) / 2 = 500
    #     y = (200 + 700) / 2 = 450
    #
    # SVG Y coordinates point downward. OpenSCAD's imported SVG coordinate
    # system therefore uses:
    #
    #     1024 - 450 = 574
    #
    # for the physical centering translation.

    assert "envelope_center_x = 500;" in source
    assert "envelope_openscad_center_y = 574;" in source

    assert "-envelope_center_x" in source
    assert "-envelope_openscad_center_y" in source


def test_base_does_not_independently_fit_artwork_color_layers(
    tmp_path: Path,
) -> None:
    """
    Base dimensionalization depends only on the registered Artwork envelope.

    Individual Artwork color-layer bounds are not inputs to Base geometry and
    therefore cannot independently fit, scale, or recenter the Base.
    """

    from lowkey_artifact_builder.model.models.artwork.stages.extrude import (
        _build_base_scad,
    )

    envelope = tmp_path / "envelope.svg"
    envelope.write_text(
        "<svg/>",
        encoding="utf-8",
    )

    source = _build_base_scad(
        envelope,
        registered_extent=1024,
        envelope_bounds=(
            100.0,
            200.0,
            900.0,
            700.0,
        ),
        artwork_size=100.0,
        base_raise=1.0,
    )

    assert source.count("import(") == 1
    assert str(envelope.resolve()) in source


def test_base_raise_does_not_change_planar_dimensionalization(
    tmp_path: Path,
) -> None:
    """
    Base raise controls extrusion height rather than planar geometry.

    Changing only artwork_base_raise leaves the Base's X/Y dimensionalization
    unchanged.
    """

    from lowkey_artifact_builder.model.models.artwork.stages.extrude import (
        _build_base_scad,
    )

    envelope = tmp_path / "envelope.svg"
    envelope.write_text(
        "<svg/>",
        encoding="utf-8",
    )

    low_source = _build_base_scad(
        envelope,
        registered_extent=1024,
        envelope_bounds=(
            100.0,
            200.0,
            900.0,
            700.0,
        ),
        artwork_size=100.0,
        base_raise=0.5,
    )

    high_source = _build_base_scad(
        envelope,
        registered_extent=1024,
        envelope_bounds=(
            100.0,
            200.0,
            900.0,
            700.0,
        ),
        artwork_size=100.0,
        base_raise=3.0,
    )

    def planar_source(
        source: str,
    ) -> str:
        return "\n".join(
            line
            for line in source.splitlines()
            if "base_raise" not in line and "height =" not in line
        )

    assert planar_source(low_source) == planar_source(
        high_source,
    )
