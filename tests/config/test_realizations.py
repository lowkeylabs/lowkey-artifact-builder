"""
Tests for artifact realization configuration.

A realization is one configured invocation of a model. Realizations are
artifact-scoped and select a model, a model-scoped variant, and optional
parameter overrides.

These tests establish realization configuration semantics only.
Planning, filesystem placement, and execution belong to later Phase 5
changes.
"""
# File: tests/config/test_realizations.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path

import pytest

from lowkey_artifact_builder.config import (
    ConfigError,
    get_realization_names,
    get_resolver,
    write_artifact_config,
)
from lowkey_artifact_builder.model import (
    ModelSpec,
    VariantSpec,
)

# =========================================================
# Test support
# =========================================================


def _example_model() -> ModelSpec:
    """
    Return a deterministic model for realization tests.
    """

    return ModelSpec(
        name="example-model",
        title="Example Model",
        variants=(
            VariantSpec(
                name="default",
                parameters={
                    "ridge": False,
                    "ridge_width": 1.0,
                    "ridge_raise": 0.5,
                },
            ),
            VariantSpec(
                name="ridged",
                parameters={
                    "ridge": True,
                    "ridge_width": 3.0,
                    "ridge_raise": 1.0,
                },
            ),
        ),
    )


def _write_workspace(
    project_root: Path,
) -> None:
    """
    Write a minimal workspace configuration.
    """

    (project_root / "workspace.toml").write_text(
        "[parameters]\n",
        encoding="utf-8",
    )


def _install_model(
    monkeypatch: pytest.MonkeyPatch,
    model: ModelSpec,
) -> None:
    """
    Install one deterministic model for configuration tests.

    These tests isolate model package discovery because realization
    configuration is the behavior under test.
    """

    import lowkey_artifact_builder.config.config as config_module

    class StubRegistry:
        def get_model(
            self,
            name: str,
        ) -> ModelSpec:
            assert name == model.name

            return model

    monkeypatch.setattr(
        config_module,
        "build_model_registry",
        lambda: StubRegistry(),
    )

    monkeypatch.setattr(
        config_module,
        "_load_model_parameters",
        lambda name: {},
    )

    monkeypatch.setattr(
        config_module,
        "_load_model_derivations",
        lambda name: {},
    )


@pytest.fixture
def example_model(
    monkeypatch: pytest.MonkeyPatch,
) -> ModelSpec:
    """
    Install the example realization model.
    """

    model = _example_model()

    _install_model(
        monkeypatch,
        model,
    )

    return model


# =========================================================
# Backward-compatible default realization
# =========================================================


def test_artifact_without_realizations_uses_implicit_default_realization(
    tmp_path: Path,
    example_model: ModelSpec,
) -> None:
    """
    Existing single-model artifact configuration remains valid.

    An artifact without explicit realization configuration represents
    one realization named "default".
    """

    _write_workspace(tmp_path)

    write_artifact_config(
        "example",
        {
            "model": example_model.name,
            "variant": "ridged",
            "ridge_width": 4.0,
            "ridge_raise": 1.25,
        },
        project_root=tmp_path,
    )

    resolver = get_resolver(
        "example",
        realization="default",
        project_root=tmp_path,
    )

    assert resolver("model") == example_model.name
    assert resolver("variant") == "ridged"

    assert resolver("ridge") is True
    assert resolver("ridge_width") == 4.0
    assert resolver("ridge_raise") == 1.25


# =========================================================
# Named realizations
# =========================================================


def test_named_realization_selects_model_and_variant(
    tmp_path: Path,
    example_model: ModelSpec,
) -> None:
    """
    A named realization selects its model and model-scoped variant.
    """

    _write_workspace(tmp_path)

    write_artifact_config(
        "example",
        {
            "realizations": {
                "ornament": {
                    "model": example_model.name,
                    "variant": "ridged",
                },
            },
        },
        project_root=tmp_path,
    )

    resolver = get_resolver(
        "example",
        realization="ornament",
        project_root=tmp_path,
    )

    assert resolver("model") == example_model.name
    assert resolver("variant") == "ridged"

    assert resolver("ridge") is True
    assert resolver("ridge_width") == 3.0
    assert resolver("ridge_raise") == 1.0


def test_realization_parameters_override_variant_parameters(
    tmp_path: Path,
    example_model: ModelSpec,
) -> None:
    """
    Realization parameters override the selected variant preset.
    """

    _write_workspace(tmp_path)

    write_artifact_config(
        "example",
        {
            "realizations": {
                "small": {
                    "model": example_model.name,
                    "variant": "ridged",
                    "parameters": {
                        "ridge_width": 2.0,
                        "ridge_raise": 0.75,
                    },
                },
            },
        },
        project_root=tmp_path,
    )

    resolver = get_resolver(
        "example",
        realization="small",
        project_root=tmp_path,
    )

    assert resolver("ridge") is True
    assert resolver("ridge_width") == 2.0
    assert resolver("ridge_raise") == 0.75


# =========================================================
# Realization isolation
# =========================================================


def test_same_model_and_variant_support_distinct_realizations(
    tmp_path: Path,
    example_model: ModelSpec,
) -> None:
    """
    Two realizations may use the same model and variant while resolving
    different parameter values.
    """

    _write_workspace(tmp_path)

    write_artifact_config(
        "example",
        {
            "realizations": {
                "small": {
                    "model": example_model.name,
                    "variant": "ridged",
                    "parameters": {
                        "ridge_width": 2.0,
                        "ridge_raise": 0.75,
                    },
                },
                "large": {
                    "model": example_model.name,
                    "variant": "ridged",
                    "parameters": {
                        "ridge_width": 6.0,
                        "ridge_raise": 1.5,
                    },
                },
            },
        },
        project_root=tmp_path,
    )

    small = get_resolver(
        "example",
        realization="small",
        project_root=tmp_path,
    )

    large = get_resolver(
        "example",
        realization="large",
        project_root=tmp_path,
    )

    assert small("model") == large("model") == example_model.name

    assert small("variant") == large("variant") == "ridged"

    assert small("ridge") is True
    assert small("ridge_width") == 2.0
    assert small("ridge_raise") == 0.75

    assert large("ridge") is True
    assert large("ridge_width") == 6.0
    assert large("ridge_raise") == 1.5


def test_realization_parameters_do_not_leak_between_realizations(
    tmp_path: Path,
    example_model: ModelSpec,
) -> None:
    """
    Parameter overrides belonging to one realization do not affect
    another realization of the same model.
    """

    _write_workspace(tmp_path)

    write_artifact_config(
        "example",
        {
            "realizations": {
                "custom": {
                    "model": example_model.name,
                    "variant": "ridged",
                    "parameters": {
                        "ridge": False,
                        "ridge_width": 9.0,
                        "ridge_raise": 2.0,
                    },
                },
                "standard": {
                    "model": example_model.name,
                    "variant": "ridged",
                },
            },
        },
        project_root=tmp_path,
    )

    custom = get_resolver(
        "example",
        realization="custom",
        project_root=tmp_path,
    )

    standard = get_resolver(
        "example",
        realization="standard",
        project_root=tmp_path,
    )

    assert custom("ridge") is False
    assert custom("ridge_width") == 9.0
    assert custom("ridge_raise") == 2.0

    assert standard("ridge") is True
    assert standard("ridge_width") == 3.0
    assert standard("ridge_raise") == 1.0


# =========================================================
# Validation
# =========================================================


def test_resolver_rejects_unknown_realization(
    tmp_path: Path,
    example_model: ModelSpec,
) -> None:
    """
    An explicitly requested realization must exist for the artifact.
    """

    _write_workspace(tmp_path)

    write_artifact_config(
        "example",
        {
            "realizations": {
                "ornament": {
                    "model": example_model.name,
                },
            },
        },
        project_root=tmp_path,
    )

    with pytest.raises(
        ConfigError,
        match="unknown realization",
    ):
        get_resolver(
            "example",
            realization="missing",
            project_root=tmp_path,
        )


def test_realization_rejects_unknown_variant(
    tmp_path: Path,
    example_model: ModelSpec,
) -> None:
    """
    A realization's variant must exist within its selected model.
    """

    _write_workspace(tmp_path)

    write_artifact_config(
        "example",
        {
            "realizations": {
                "ornament": {
                    "model": example_model.name,
                    "variant": "missing",
                },
            },
        },
        project_root=tmp_path,
    )

    with pytest.raises(
        ConfigError,
        match="unknown variant",
    ):
        get_resolver(
            "example",
            realization="ornament",
            project_root=tmp_path,
        )


# =========================================================
# Structural validation
# =========================================================


def test_write_artifact_config_rejects_non_table_realizations(
    tmp_path: Path,
) -> None:
    """
    The artifact realizations section must be a mapping of named
    realization configurations.
    """

    _write_workspace(tmp_path)

    with pytest.raises(
        ConfigError,
        match="realizations.*must be a TOML table",
    ):
        write_artifact_config(
            "example",
            {
                "realizations": "invalid",
            },
            project_root=tmp_path,
        )


def test_write_artifact_config_rejects_non_table_realization(
    tmp_path: Path,
) -> None:
    """
    Each named realization must itself be a configuration table.
    """

    _write_workspace(tmp_path)

    with pytest.raises(
        ConfigError,
        match="Realization 'ornament' must be a TOML table",
    ):
        write_artifact_config(
            "example",
            {
                "realizations": {
                    "ornament": "invalid",
                },
            },
            project_root=tmp_path,
        )


def test_write_artifact_config_rejects_invalid_realization_parameters(
    tmp_path: Path,
) -> None:
    """
    A realization's parameters section must be a TOML table.
    """

    _write_workspace(tmp_path)

    with pytest.raises(
        ConfigError,
        match="parameters.*realization 'ornament'.*must be a TOML table",
    ):
        write_artifact_config(
            "example",
            {
                "realizations": {
                    "ornament": {
                        "model": "example-model",
                        "parameters": "invalid",
                    },
                },
            },
            project_root=tmp_path,
        )


def test_realizations_are_not_exposed_as_resolved_parameters(
    tmp_path: Path,
    example_model: ModelSpec,
) -> None:
    """
    The realizations table is artifact structure, not a configuration
    parameter exposed through Resolver.

    This also protects legacy artifact parameter extraction from treating
    realization configuration as an ordinary top-level parameter.
    """

    _write_workspace(tmp_path)

    write_artifact_config(
        "example",
        {
            "realizations": {
                "ornament": {
                    "model": example_model.name,
                    "variant": "ridged",
                },
            },
        },
        project_root=tmp_path,
    )

    resolver = get_resolver(
        "example",
        realization="ornament",
        project_root=tmp_path,
    )

    assert not resolver.has("realizations")

    with pytest.raises(
        ConfigError,
        match="Unknown configuration value 'realizations'",
    ):
        resolver("realizations")


def test_named_realization_inherits_artifact_configuration(
    tmp_path: Path,
) -> None:
    """
    A named realization inherits configuration declared at artifact scope.

    Artifact-scoped values describe choices shared by the artifact's
    realizations and do not need to be repeated in every realization.
    """

    _write_workspace(
        tmp_path,
    )

    write_artifact_config(
        "example",
        {
            "source": "source.png",
            "realizations": {
                "ornament": {
                    "model": "artwork",
                    "variant": "default",
                },
                "coaster": {
                    "model": "artwork",
                    "variant": "default",
                },
            },
        },
        project_root=tmp_path,
    )

    ornament = get_resolver(
        "example",
        realization="ornament",
        project_root=tmp_path,
    )

    coaster = get_resolver(
        "example",
        realization="coaster",
        project_root=tmp_path,
    )

    assert ornament("source") == "source.png"
    assert coaster("source") == "source.png"

    assert ornament.source("source") == "artifact"
    assert coaster.source("source") == "artifact"


def test_realization_configuration_overrides_artifact_configuration(
    tmp_path: Path,
) -> None:
    """
    Realization configuration has higher precedence than artifact
    configuration inherited by that realization.
    """

    _write_workspace(
        tmp_path,
    )

    write_artifact_config(
        "example",
        {
            "source": "shared.png",
            "artwork_size": 80.0,
            "realizations": {
                "ornament": {
                    "model": "artwork",
                    "variant": "default",
                    "source": "ornament.png",
                    "parameters": {
                        "artwork_size": 100.0,
                    },
                },
            },
        },
        project_root=tmp_path,
    )

    resolver = get_resolver(
        "example",
        realization="ornament",
        project_root=tmp_path,
    )

    assert resolver("source") == "ornament.png"
    assert resolver.source("source") == "realization 'ornament'"

    assert resolver("artwork_size") == 100.0
    assert resolver.source("artwork_size") == "realization 'ornament'"


def test_get_realization_names_preserves_declaration_order(
    tmp_path: Path,
) -> None:
    """
    Explicit realization names are returned in artifact.toml
    declaration order.
    """

    write_artifact_config(
        "example",
        {
            "realizations": {
                "ornament": {
                    "model": "artwork",
                },
                "coaster": {
                    "model": "artwork",
                },
                "keychain": {
                    "model": "artwork",
                },
            },
        },
        project_root=tmp_path,
    )

    assert get_realization_names(
        "example",
        project_root=tmp_path,
    ) == (
        "ornament",
        "coaster",
        "keychain",
    )


def test_get_realization_names_returns_implicit_default(
    tmp_path: Path,
) -> None:
    """
    Legacy artifact configuration exposes its implicit default
    realization through realization discovery.
    """

    write_artifact_config(
        "example",
        {
            "model": "artwork",
        },
        project_root=tmp_path,
    )

    assert get_realization_names(
        "example",
        project_root=tmp_path,
    ) == ("default",)
