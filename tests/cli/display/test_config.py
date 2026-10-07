"""
Tests for artifact configuration display.
"""
# File: tests/cli/display/test_config.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from unittest.mock import Mock

from lowkey_artifact_builder.cli.display.config import (
    display_artifact_config,
    display_artifact_definition,
    display_realization_configuration,
)
from lowkey_artifact_builder.model import ModelSpec, StageSpec


def test_artifact_config_display_contains_only_resolved_configuration(
    capsys: object,
) -> None:
    """
    Artifact configuration display contains only resolved configuration
    and does not manufacture an Artwork-color section.
    """

    model = ModelSpec(
        name="example",
        title="Example",
        stages=(
            StageSpec(
                id=10,
                name="example",
                parameters=(
                    "artifact_color_count",
                    "printer_colors",
                ),
            ),
        ),
    )

    resolver = Mock()

    resolver.side_effect = lambda name: {
        "artifact_color_count": 3,
        "printer_colors": [
            "red",
            "green",
            "blue",
        ],
    }[name]

    resolver.source.side_effect = lambda name: {
        "artifact_color_count": "artifact",
        "printer_colors": "workspace",
    }[name]

    display_artifact_config(
        "example",
        model,
        resolver,
    )

    captured = capsys.readouterr()  # type: ignore[attr-defined]

    assert "Resolved parameters" in captured.out
    assert "artifact_color_count" in captured.out
    assert "printer_colors" in captured.out
    assert "Artwork colors" not in captured.out


def test_artifact_definition_display_contains_authored_configuration_and_realizations(
    capsys: object,
) -> None:
    """
    Artifact definition display shows authored Artifact configuration and
    the effective Realization catalog.
    """

    display_artifact_definition(
        "skippy",
        {
            "source": "skippy.png",
        },
        (
            "artwork_default",
            "shape_default",
            "shape_ornament",
        ),
    )

    captured = capsys.readouterr()  # type: ignore[attr-defined]

    assert "skippy" in captured.out
    assert "source" in captured.out
    assert "skippy.png" in captured.out
    assert "artwork_default" in captured.out
    assert "shape_default" in captured.out
    assert "shape_ornament" in captured.out


def test_realization_configuration_display_shows_effective_parameters_and_sources(
    capsys,
) -> None:
    """
    Realization configuration display presents application-resolved
    construction parameters without reconstructing configuration semantics.
    """

    from lowkey_artifact_builder.application.configuration import (
        ConfigurationParameter,
        RealizationConfiguration,
    )

    configuration = RealizationConfiguration(
        artifact_id="skippy",
        realization="shape_ornament",
        model="shape",
        parameters=(
            ConfigurationParameter(
                name="shape_size",
                value=120.0,
                source="artifact",
            ),
            ConfigurationParameter(
                name="shape_base_height",
                value=2.0,
                source="model",
            ),
            ConfigurationParameter(
                name="shape_outer_ridge_width",
                value=1.0,
                source="variant 'ornament'",
            ),
        ),
    )

    display_realization_configuration(
        configuration,
    )

    captured = capsys.readouterr()

    assert "skippy" in captured.out
    assert "shape_ornament" in captured.out
    assert "shape" in captured.out

    assert "shape_size" in captured.out
    assert "120" in captured.out
    assert "artifact" in captured.out

    assert "shape_base_height" in captured.out
    assert "2" in captured.out
    assert "model" in captured.out

    assert "shape_outer_ridge_width" in captured.out
    assert "1" in captured.out
    assert "variant 'ornament'" in captured.out
