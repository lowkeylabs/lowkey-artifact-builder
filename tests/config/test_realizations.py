"""
Tests for Artifact-scoped Realization configuration.

Every Model Variant available to an Artifact provides a corresponding
default Realization. Default Realizations exist independently of whether
they are explicitly declared in artifact.toml.

Artifacts may additionally customize Realizations or declare additional
Artifact-scoped Realizations selecting Model Variants.

These tests establish Realization discovery, resolution, configuration
precedence, isolation, and compatibility behavior while the canonical
Artifact configuration grammar is introduced incrementally.
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


def _secondary_model() -> ModelSpec:
    """
    Return a second deterministic model for realization discovery tests.
    """

    return ModelSpec(
        name="secondary-model",
        title="Secondary Model",
        variants=(
            VariantSpec(
                name="default",
                parameters={
                    "mode": "ordinary",
                },
            ),
        ),
    )


def _install_models(
    monkeypatch: pytest.MonkeyPatch,
    *models: ModelSpec,
) -> None:
    """
    Install deterministic models for configuration tests.

    These tests isolate model package discovery because realization
    configuration is the behavior under test.
    """

    import lowkey_artifact_builder.config.config as config_module

    model_by_name = {model.name: model for model in models}

    class StubRegistry:
        def get_model(
            self,
            name: str,
        ) -> ModelSpec:
            return model_by_name[name]

        def all_models(
            self,
        ) -> list[ModelSpec]:
            return sorted(
                model_by_name.values(),
                key=lambda model: model.name,
            )

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


def _install_model(
    monkeypatch: pytest.MonkeyPatch,
    model: ModelSpec,
) -> None:
    """
    Install one deterministic model for configuration tests.
    """

    _install_models(
        monkeypatch,
        model,
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


def test_get_realization_names_appends_additional_realizations_in_declaration_order(
    tmp_path: Path,
    example_model: ModelSpec,
) -> None:
    """
    Additional Artifact-defined Realizations follow the derived default
    Realization catalog in artifact.toml declaration order.

    Explicit Realizations augment rather than replace the default
    Realizations derived from registered Model Variants.
    """

    write_artifact_config(
        "example",
        {
            "realizations": {
                "ornament": {
                    "model": example_model.name,
                },
                "coaster": {
                    "model": example_model.name,
                },
                "keychain": {
                    "model": example_model.name,
                },
            },
        },
        project_root=tmp_path,
    )

    assert get_realization_names(
        "example",
        project_root=tmp_path,
    ) == (
        "example-model_default",
        "example-model_ridged",
        "ornament",
        "coaster",
        "keychain",
    )


def test_direct_variant_selection_preserves_explicit_named_realization(
    tmp_path: Path,
    example_model: ModelSpec,
) -> None:
    """
    Direct Variant selection may override the Variant selected by an explicit
    historical realization without changing that realization's identity.
    """

    _write_workspace(tmp_path)

    write_artifact_config(
        "example",
        {
            "realizations": {
                "holiday": {
                    "model": example_model.name,
                    "variant": "default",
                },
            },
        },
        project_root=tmp_path,
    )

    resolver = get_resolver(
        "example",
        variant="ridged",
        realization="holiday",
        project_root=tmp_path,
    )

    assert resolver("model") == example_model.name
    assert resolver("realization") == "holiday"
    assert resolver("variant") == "ridged"

    assert resolver.source("realization") == "artifact"
    assert resolver.source("variant") == "selection"


# =========================================================
# Default realization discovery
# =========================================================


def test_artifact_without_realizations_discovers_default_realization_for_each_variant(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Every registered Model Variant contributes one default Realization.

    Artifact configuration does not need to enumerate the Model-owned
    Variant catalog merely to make those Realizations available.
    """

    _write_workspace(tmp_path)

    primary = _example_model()
    secondary = _secondary_model()

    _install_models(
        monkeypatch,
        primary,
        secondary,
    )

    write_artifact_config(
        "example",
        {
            "source": "source.png",
        },
        project_root=tmp_path,
    )

    realization_names = get_realization_names(
        "example",
        project_root=tmp_path,
    )

    assert realization_names == (
        "example-model_default",
        "example-model_ridged",
        "secondary-model_default",
    )


def test_default_realization_resolves_its_originating_model_and_variant(
    tmp_path: Path,
    example_model: ModelSpec,
) -> None:
    """
    A canonical default Realization identifies the Model Variant from
    which that Realization is derived.
    """

    _write_workspace(tmp_path)

    write_artifact_config(
        "example",
        {
            "source": "source.png",
        },
        project_root=tmp_path,
    )

    resolver = get_resolver(
        "example",
        realization="example-model_ridged",
        project_root=tmp_path,
    )

    assert resolver("artifact_id") == "example"
    assert resolver("realization") == "example-model_ridged"
    assert resolver("model") == example_model.name
    assert resolver("variant") == "ridged"


def test_default_realization_inherits_variant_configuration(
    tmp_path: Path,
    example_model: ModelSpec,
) -> None:
    """
    A derived default Realization uses ordinary Variant configuration
    resolution without requiring Artifact-specific customization.
    """

    _write_workspace(tmp_path)

    write_artifact_config(
        "example",
        {
            "source": "source.png",
        },
        project_root=tmp_path,
    )

    resolver = get_resolver(
        "example",
        realization="example-model_ridged",
        project_root=tmp_path,
    )

    assert resolver("ridge") is True
    assert resolver("ridge_width") == 3.0
    assert resolver("ridge_raise") == 1.0


# =========================================================
# Default realization customization
# =========================================================


def test_customized_default_realization_remains_single_effective_realization(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Customizing a derived default Realization does not replace the default
    catalog or create a second Realization with the same identity.

    Effective Realization discovery remains the union of the registered
    Model Variant defaults and Artifact-specific Realization configuration.
    """

    _write_workspace(tmp_path)

    primary = _example_model()
    secondary = _secondary_model()

    _install_models(
        monkeypatch,
        primary,
        secondary,
    )

    write_artifact_config(
        "example",
        {
            "source": "source.png",
            "realizations": {
                "example-model_ridged": {
                    "ridge_width": 7.0,
                },
            },
        },
        project_root=tmp_path,
    )

    assert get_realization_names(
        "example",
        project_root=tmp_path,
    ) == (
        "example-model_default",
        "example-model_ridged",
        "secondary-model_default",
    )


def test_customized_default_realization_implies_model_and_variant(
    tmp_path: Path,
    example_model: ModelSpec,
) -> None:
    """
    A canonical default Realization customization need not restate its
    originating Model or Variant.

    Canonical Realization identity continues to select both.
    """

    _write_workspace(tmp_path)

    write_artifact_config(
        "example",
        {
            "source": "source.png",
            "realizations": {
                "example-model_ridged": {
                    "ridge_width": 7.0,
                },
            },
        },
        project_root=tmp_path,
    )

    resolver = get_resolver(
        "example",
        realization="example-model_ridged",
        project_root=tmp_path,
    )

    assert resolver("artifact_id") == "example"
    assert resolver("realization") == "example-model_ridged"
    assert resolver("model") == example_model.name
    assert resolver("variant") == "ridged"


def test_customized_default_realization_overrides_variant_configuration(
    tmp_path: Path,
    example_model: ModelSpec,
) -> None:
    """
    Artifact customization of a default Realization has higher precedence
    than the configuration supplied by its originating Variant.

    Values not customized by the Artifact continue to come from the Variant.
    """

    _write_workspace(tmp_path)

    write_artifact_config(
        "example",
        {
            "source": "source.png",
            "realizations": {
                "example-model_ridged": {
                    "ridge_width": 7.0,
                },
            },
        },
        project_root=tmp_path,
    )

    resolver = get_resolver(
        "example",
        realization="example-model_ridged",
        project_root=tmp_path,
    )

    assert resolver("ridge") is True
    assert resolver("ridge_width") == 7.0
    assert resolver("ridge_raise") == 1.0

    assert resolver.source("ridge") == "variant 'ridged'"
    assert resolver.source("ridge_width") == ("realization 'example-model_ridged'")
    assert resolver.source("ridge_raise") == "variant 'ridged'"
