"""RED tests for Phase 3, Slice A: Artwork representation configuration.

These tests cover configuration semantics only. Product generation and stage
selection are addressed in subsequent slices.
"""
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path

import pytest

from lowkey_artifact_builder.config import ConfigError, get_resolver
from lowkey_artifact_builder.model.models.artwork import MODEL
from lowkey_artifact_builder.model.validation import (
    get_named_model_validators,
    validate_configuration,
)


def _resolver(tmp_path: Path):
    """Use the actual Artwork Model defaults and existing Resolver."""
    return get_resolver(
        "example",
        model="artwork",
        project_root=tmp_path,
    )


def _validate(tmp_path: Path, representation: object, processing: object) -> None:
    """Exercise model-owned validation using ordinary configuration overlays."""
    resolver = _resolver(tmp_path).with_values(
        {
            "artwork_representation": representation,
            "artwork_processing": processing,
        },
        provenance="test",
    )
    validate_configuration(
        resolver,
        validators=get_named_model_validators("artwork"),
    )


def test_artwork_default_remains_vector_auto(tmp_path: Path) -> None:
    """The existing default remains compatible with vector/3MF consumers."""
    resolver = _resolver(tmp_path)
    assert resolver("artwork_representation") == "vector"
    assert resolver("artwork_processing") == "auto"


@pytest.mark.parametrize(
    ("representation", "processing"),
    [
        ("source", "none"),
        ("raster", "none"),
        ("vector", "auto"),
    ],
)
def test_artwork_accepts_initial_representation_processing_pairs(
    tmp_path: Path,
    representation: str,
    processing: str,
) -> None:
    """The selected representation and strategy are independent values."""
    _validate(tmp_path, representation, processing)


@pytest.mark.parametrize(
    ("representation", "processing"),
    [
        ("source", "auto"),
        ("raster", "auto"),
        ("vector", "none"),
    ],
)
def test_artwork_rejects_unsupported_combinations(
    tmp_path: Path,
    representation: str,
    processing: str,
) -> None:
    """Unsupported combinations must not silently fall back."""
    with pytest.raises(
        ConfigError,
        match="artwork_representation|artwork_processing",
    ):
        _validate(tmp_path, representation, processing)


@pytest.mark.parametrize(
    ("representation", "processing"),
    [
        ("bitmap", "none"),
        ("source", "jarvis"),
        (None, "none"),
        ("raster", 42),
    ],
)
def test_artwork_rejects_invalid_parameter_values(
    tmp_path: Path,
    representation: object,
    processing: object,
) -> None:
    """Unknown or incorrectly typed values receive configuration errors."""
    with pytest.raises(
        ConfigError,
        match="artwork_representation|artwork_processing",
    ):
        _validate(tmp_path, representation, processing)


def test_artwork_configuration_overlays_are_independent(tmp_path: Path) -> None:
    """Distinct effective configurations must not mutate shared defaults."""
    default = _resolver(tmp_path)
    source = default.with_values(
        {"artwork_representation": "source", "artwork_processing": "none"},
        provenance="source-realization",
    )
    raster = default.with_values(
        {"artwork_representation": "raster", "artwork_processing": "none"},
        provenance="raster-realization",
    )

    assert (source("artwork_representation"), source("artwork_processing")) == ("source", "none")
    assert (raster("artwork_representation"), raster("artwork_processing")) == ("raster", "none")
    assert (default("artwork_representation"), default("artwork_processing")) == ("vector", "auto")
    assert source.source("artwork_representation") == "source-realization"
    assert raster.source("artwork_representation") == "raster-realization"


def test_artwork_declares_representation_validation() -> None:
    """Validation is owned by Artwork rather than the generic engine."""
    parameters = {
        parameter
        for validator in get_named_model_validators("artwork")
        for parameter in validator.parameters
    }
    assert "artwork_representation" in parameters
    assert "artwork_processing" in parameters


def test_existing_vector_manufacturing_stages_remain_declared() -> None:
    """Configuration introduction must not remove legacy vector products."""
    stages = {stage.name: stage for stage in MODEL.stages}
    assert {"prepare", "raster", "vector", "extrude", "package"} <= set(stages)
    assert any(product.name == "manifest" for product in stages["vector"].products)
    assert any(product.name == "artifact" for product in stages["package"].products)
