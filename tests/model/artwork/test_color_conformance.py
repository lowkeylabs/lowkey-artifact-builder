"""
Conformance tests for the permanent Artwork color model.
"""
# File: tests/model/artwork/test_color_conformance.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path

import lowkey_artifact_builder.model.models.artwork as artwork_model

# =========================================================
# Test support
# =========================================================


def _artwork_source_files() -> tuple[Path, ...]:
    """
    Return executable Python source files owned by the Artwork model.
    """

    root = Path(artwork_model.__file__).parent

    return tuple(path for path in root.rglob("*.py") if "__pycache__" not in path.parts)


def _artwork_source() -> str:
    """
    Return executable Artwork model source as searchable text.
    """

    return "\n".join(
        path.read_text(
            encoding="utf-8",
        )
        for path in _artwork_source_files()
    )


# =========================================================
# Obsolete configuration semantics
# =========================================================


def test_artwork_execution_does_not_reference_obsolete_artwork_colors() -> None:
    """
    Executable Artwork model code does not depend on configured artwork_colors.
    """

    source = _artwork_source()

    assert '"artwork_colors"' not in source
    assert "'artwork_colors'" not in source


def test_artwork_execution_does_not_reference_obsolete_fill_color() -> None:
    """
    Executable Artwork model code does not depend on artwork_fill_color.
    """

    source = _artwork_source()

    assert "artwork_fill_color" not in source


# =========================================================
# Obsolete recommendation semantics
# =========================================================


def test_artwork_execution_does_not_reference_five_tool_recommendation() -> None:
    """
    Executable Artwork model code has no fixed five-tool recommendation path.
    """

    source = _artwork_source()

    assert "recommend_five_tool_artwork_palettes" not in source
    assert "ArtworkPaletteRecommendations" not in source


def test_artwork_execution_does_not_reference_independent_color_matches() -> None:
    """
    Artwork analysis no longer exposes obsolete independent match semantics.
    """

    source = _artwork_source()

    assert "ArtworkColorMatch" not in source
    assert "analyze_color_matches" not in source


# =========================================================
# Permanent color semantics
# =========================================================


def test_artwork_execution_references_artifact_color_count() -> None:
    """
    Executable Artwork model code expresses trace cardinality as artifact_color_count.
    """

    source = _artwork_source()

    assert "artifact_color_count" in source


def test_artwork_execution_references_distinct_artifact_and_printer_colors() -> None:
    """
    Executable Artwork code distinguishes Artifact RGB from printer assignment.
    """

    source = _artwork_source()

    assert "artifact_color" in source
    assert "printer_color" in source


def test_configuration_display_does_not_reference_obsolete_artwork_colors() -> None:
    """
    Generic configuration presentation does not interpret obsolete
    Artwork-specific color configuration.
    """

    from lowkey_artifact_builder.cli.display import config

    source = Path(config.__file__).read_text(
        encoding="utf-8",
    )

    assert "artwork_colors" not in source
    assert "_display_artwork_colors" not in source


def test_generic_infrastructure_does_not_reference_obsolete_artwork_colors() -> None:
    """
    Generic infrastructure and its generic tests do not encode the obsolete
    Artwork-specific color configuration parameter.
    """

    paths = (
        Path("src/lowkey_artifact_builder/engine/specs.py"),
        Path("tests/model/test_specs.py"),
        Path("tests/cli/test_bindings.py"),
        Path("tests/engine/test_fingerprint_generation.py"),
    )

    for path in paths:
        source = path.read_text(
            encoding="utf-8",
        )

        assert "artwork_colors" not in source, path
