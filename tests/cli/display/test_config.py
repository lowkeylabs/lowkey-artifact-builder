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
