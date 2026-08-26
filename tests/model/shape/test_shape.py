"""Tests for the shape model."""
# File: tests/model/shape/test_shape.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from lowkey_artifact_builder.model import build_model_registry
from lowkey_artifact_builder.model.models.shape import MODEL


def test_shape_model_identity() -> None:
    """The shape model has the expected identity."""

    assert MODEL.name == "shape"
    assert MODEL.title == "Shape"


def test_shape_model_is_discovered() -> None:
    """The shape model participates in normal model discovery."""

    registry = build_model_registry()

    names = [model.name for model in registry.all_models()]

    assert "shape" in names
