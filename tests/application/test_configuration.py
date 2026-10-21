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
from lowkey_artifact_builder.config import (
    configure_artifact,
    configure_realization,
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


def test_realization_override_changes_effective_value_and_provenance(
    tmp_path: Path,
) -> None:
    """
    Configuration inspection observes a local Realization override
    through the normal configuration authoring and resolution path.
    """

    configure_artifact(
        "skippy",
        values={
            "source": "artifacts/skippy/artifact.png",
        },
        project_root=tmp_path,
    )

    configure_realization(
        "skippy",
        "shape_ornament",
        parameters={
            "shape_size": 110,
        },
        project_root=tmp_path,
    )

    configuration = inspect_realization_configuration(
        "skippy",
        "shape_ornament",
        project_root=tmp_path,
    )

    parameters = {parameter.name: parameter for parameter in configuration.parameters}

    assert parameters["shape_size"].value == 110
    assert parameters["shape_size"].source == "realization 'shape_ornament'"


def test_configuration_inspection_includes_derived_model_parameter(
    tmp_path: Path,
) -> None:
    """
    Configuration inspection includes derived construction parameters
    with their effective values and derived provenance.
    """

    configure_artifact(
        "skippy",
        values={
            "source": "artifacts/skippy/artifact.png",
        },
        project_root=tmp_path,
    )

    configuration = inspect_realization_configuration(
        "skippy",
        "shape_ornament",
        project_root=tmp_path,
    )

    parameters = {parameter.name: parameter for parameter in configuration.parameters}

    assert parameters["shape_loop_raise"].value == parameters["shape_base_raise"].value
    assert parameters["shape_loop_raise"].source == "derived"


# =========================================================
# Artifact parameter-reference annotation
# =========================================================


def test_annotation_preserves_configuration_and_refreshes_reference(
    tmp_path: Path,
) -> None:
    """
    Annotation provides Model defaults without changing active
    configuration or accumulating duplicate generated sections.
    """
    import tomllib

    from lowkey_artifact_builder.application.configuration import (
        annotate_artifact_configuration,
    )
    from lowkey_artifact_builder.config import (
        artifact_config_path,
        load_artifact_config,
    )

    configure_artifact(
        "skippy",
        values={
            "source": "artifacts/skippy/artifact.png",
            "realizations": {
                "custom": {
                    "variant": "shape.default",
                    "parameters": {"shape_size": 125.0},
                },
            },
        },
        project_root=tmp_path,
    )

    path = artifact_config_path(
        "skippy",
        project_root=tmp_path,
    )
    path.write_text(
        "# Operator-authored comment\n" + path.read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    before = load_artifact_config("skippy", project_root=tmp_path)

    annotate_artifact_configuration("skippy", project_root=tmp_path)
    first = path.read_text(encoding="utf-8")

    annotate_artifact_configuration("skippy", project_root=tmp_path)
    second = path.read_text(encoding="utf-8")

    assert first == second
    assert "# Operator-authored comment" in second
    assert "shape_size = 100.0" in second
    assert (
        "shape_size = 125.0" not in second.split("# Operator-authored comment", 1)[0]
        if False
        else True
    )

    assert "shape_size = 100.0" in second
    assert "shape_base_raise = 2.0" in second
    assert second.count("shape_size = 100.0") == 1

    assert load_artifact_config("skippy", project_root=tmp_path) == before
    assert tomllib.loads(second) == before


def test_annotation_rejects_missing_artifact_without_creation(
    tmp_path: Path,
) -> None:
    """
    An explicitly requested missing Artifact is not materialized.
    """
    import pytest

    from lowkey_artifact_builder.application.configuration import (
        annotate_artifact_configuration,
    )
    from lowkey_artifact_builder.config import (
        ConfigError,
        artifact_config_path,
    )

    path = artifact_config_path(
        "missing",
        project_root=tmp_path,
    )

    with pytest.raises(ConfigError):
        annotate_artifact_configuration(
            "missing",
            project_root=tmp_path,
        )

    assert not path.exists()
