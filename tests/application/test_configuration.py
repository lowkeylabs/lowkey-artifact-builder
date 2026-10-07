"""
Tests for reusable Realization configuration inspection.

Configuration inspection answers which construction parameters control an
effective Artifact Realization, their effective values, and the configuration
source responsible for each value.

This behavior belongs below the CLI so alternate interfaces can inspect the
same effective configuration without reconstructing Resolver or Model
semantics.
"""

# File: tests/application/test_configuration.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path

import lowkey_artifact_builder.application.configuration as configuration
from lowkey_artifact_builder.application.configuration import (
    ConfigurationParameter,
    RealizationConfiguration,
    inspect_realization_configuration,
)

# =========================================================
# Effective Realization configuration
# =========================================================


def test_configuration_inspection_reports_model_parameters_values_and_sources(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    Realization inspection exposes the selected Model's construction
    parameters with their effective Resolver values and provenance.

    Resolver owns effective-value and provenance semantics. Model owns the
    construction-parameter inventory. The application layer composes those
    capabilities without reconstructing either.
    """

    class Resolver:
        def __call__(
            self,
            name: str,
        ) -> object:
            values: dict[str, object] = {
                "model": "shape",
                "shape_size": 120.0,
                "shape_base_height": 2.0,
                "shape_outer_ridge_width": 1.0,
            }

            return values[name]

        def source(
            self,
            name: str,
        ) -> str:
            sources = {
                "shape_size": "artifact",
                "shape_base_height": "model",
                "shape_outer_ridge_width": "variant 'ornament'",
            }

            return sources[name]

    resolver = Resolver()

    class Model:
        parameters = (
            "shape_size",
            "shape_base_height",
            "shape_outer_ridge_width",
        )

    model = Model()

    class Registry:
        def get_model(
            self,
            name: str,
        ) -> object:
            assert name == "shape"
            return model

    resolver_requests: list[
        tuple[
            str,
            str,
            Path,
        ]
    ] = []

    monkeypatch.setattr(
        configuration,
        "get_realization_names",
        lambda artifact_id, *, project_root: (
            "artwork_default",
            "shape_default",
            "shape_ornament",
        ),
        raising=False,
    )

    def get_resolver(
        artifact_id: str,
        *,
        realization: str,
        project_root: Path,
    ) -> Resolver:
        resolver_requests.append(
            (
                artifact_id,
                realization,
                project_root,
            )
        )

        return resolver

    monkeypatch.setattr(
        configuration,
        "get_resolver",
        get_resolver,
        raising=False,
    )

    monkeypatch.setattr(
        configuration,
        "build_model_registry",
        lambda: Registry(),
        raising=False,
    )

    result = inspect_realization_configuration(
        "skippy",
        "shape_ornament",
        project_root=tmp_path,
    )

    assert resolver_requests == [
        (
            "skippy",
            "shape_ornament",
            tmp_path,
        )
    ]

    assert result == RealizationConfiguration(
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
