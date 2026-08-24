"""
Tests for model-scoped variant configuration resolution.

Variants are reusable parameter presets defined by a model.

These tests establish how variant selection participates in artifact
configuration resolution. Realization identity, realization naming,
filesystem placement, and planning belong to later Phase 5 changes.
"""
# File: tests/config/test_variants.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path

import pytest

import lowkey_artifact_builder.config.config as config_module
from lowkey_artifact_builder.config import (
    ConfigError,
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


def _model_with_variants() -> ModelSpec:
    """
    Return a minimal model containing default and named variants.
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
                },
            ),
            VariantSpec(
                name="ridged",
                parameters={
                    "ridge": True,
                    "ridge_width": 3.0,
                },
            ),
        ),
    )


def _write_workspace(
    project_root: Path,
    *,
    parameters: dict[str, object] | None = None,
) -> None:
    """
    Write a minimal workspace configuration.
    """

    values = parameters or {}

    lines = [
        "[parameters]",
    ]

    for name, value in values.items():
        if isinstance(value, bool):
            rendered = "true" if value else "false"

        elif isinstance(value, str):
            rendered = f'"{value}"'

        else:
            rendered = str(value)

        lines.append(f"{name} = {rendered}")

    (project_root / "workspace.toml").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def _install_models(
    monkeypatch: pytest.MonkeyPatch,
    models: dict[str, ModelSpec],
) -> None:
    """
    Install deterministic model definitions for resolver tests.

    Configuration currently obtains model parameter defaults and derived
    values by importing the model implementation package while model
    declarations are obtained through the model registry.

    These tests are concerned with variant resolution rather than model
    package discovery, so those legacy package-loading boundaries are
    isolated here.
    """

    class StubRegistry:
        def get_model(
            self,
            name: str,
        ) -> ModelSpec:
            try:
                return models[name]

            except KeyError as exc:
                raise AssertionError(f"unexpected model lookup: {name!r}") from exc

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
def variant_model(
    monkeypatch: pytest.MonkeyPatch,
) -> ModelSpec:
    """
    Install a model containing deterministic variant definitions.

    Variant lookup is expected to occur through the model registry rather
    than through a separate global variant registry.
    """

    model = _model_with_variants()

    _install_models(
        monkeypatch,
        {
            model.name: model,
        },
    )

    return model


# =========================================================
# Default variant
# =========================================================


def test_resolver_uses_default_variant_when_none_is_configured(
    tmp_path: Path,
    variant_model: ModelSpec,
) -> None:
    """
    An artifact that does not select a variant uses the model's default
    variant.
    """

    _write_workspace(
        tmp_path,
    )

    write_artifact_config(
        "example",
        {
            "model": variant_model.name,
        },
        project_root=tmp_path,
    )

    resolver = get_resolver(
        "example",
        project_root=tmp_path,
    )

    assert resolver("variant") == "default"

    assert resolver("ridge") is False
    assert resolver("ridge_width") == 1.0


def test_implicit_empty_default_variant_preserves_existing_resolution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    A model relying on its implicit empty default variant does not alter
    existing parameter resolution.
    """

    model = ModelSpec(
        name="example-model",
        title="Example Model",
    )

    _install_models(
        monkeypatch,
        {
            model.name: model,
        },
    )

    _write_workspace(
        tmp_path,
        parameters={
            "ridge": True,
            "ridge_width": 7.0,
        },
    )

    write_artifact_config(
        "example",
        {
            "model": model.name,
        },
        project_root=tmp_path,
    )

    resolver = get_resolver(
        "example",
        project_root=tmp_path,
    )

    assert resolver("variant") == "default"

    assert resolver("ridge") is True
    assert resolver("ridge_width") == 7.0


# =========================================================
# Named variant selection
# =========================================================


def test_resolver_applies_selected_variant_parameters(
    tmp_path: Path,
    variant_model: ModelSpec,
) -> None:
    """
    Selecting a named variant contributes that variant's parameter preset.
    """

    _write_workspace(
        tmp_path,
    )

    write_artifact_config(
        "example",
        {
            "model": variant_model.name,
            "variant": "ridged",
        },
        project_root=tmp_path,
    )

    resolver = get_resolver(
        "example",
        project_root=tmp_path,
    )

    assert resolver("variant") == "ridged"

    assert resolver("ridge") is True
    assert resolver("ridge_width") == 3.0


# =========================================================
# Configuration precedence
# =========================================================


def test_workspace_parameters_override_variant_parameters(
    tmp_path: Path,
    variant_model: ModelSpec,
) -> None:
    """
    Workspace configuration has higher precedence than a variant preset.
    """

    _write_workspace(
        tmp_path,
        parameters={
            "ridge_width": 4.0,
        },
    )

    write_artifact_config(
        "example",
        {
            "model": variant_model.name,
            "variant": "ridged",
        },
        project_root=tmp_path,
    )

    resolver = get_resolver(
        "example",
        project_root=tmp_path,
    )

    assert resolver("variant") == "ridged"

    assert resolver("ridge") is True
    assert resolver("ridge_width") == 4.0


def test_artifact_parameters_override_variant_parameters(
    tmp_path: Path,
    variant_model: ModelSpec,
) -> None:
    """
    Artifact configuration has higher precedence than a variant preset.
    """

    _write_workspace(
        tmp_path,
    )

    write_artifact_config(
        "example",
        {
            "model": variant_model.name,
            "variant": "ridged",
            "ridge": False,
            "ridge_width": 5.0,
        },
        project_root=tmp_path,
    )

    resolver = get_resolver(
        "example",
        project_root=tmp_path,
    )

    assert resolver("variant") == "ridged"

    assert resolver("ridge") is False
    assert resolver("ridge_width") == 5.0


# =========================================================
# Validation
# =========================================================


def test_resolver_rejects_unknown_variant(
    tmp_path: Path,
    variant_model: ModelSpec,
) -> None:
    """
    A configured variant must exist in the selected model.
    """

    _write_workspace(
        tmp_path,
    )

    write_artifact_config(
        "example",
        {
            "model": variant_model.name,
            "variant": "missing",
        },
        project_root=tmp_path,
    )

    with pytest.raises(
        ConfigError,
        match="unknown variant",
    ):
        get_resolver(
            "example",
            project_root=tmp_path,
        )


def test_variant_selection_is_model_scoped(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    A variant is resolved only within the artifact's selected model.

    The existence of the same variant name in another model must not make
    that variant available to the selected model.
    """

    selected_model = ModelSpec(
        name="plain-model",
        title="Plain Model",
    )

    other_model = ModelSpec(
        name="other-model",
        title="Other Model",
        variants=(
            VariantSpec(
                name="ridged",
                parameters={
                    "ridge": True,
                },
            ),
        ),
    )

    _install_models(
        monkeypatch,
        {
            selected_model.name: selected_model,
            other_model.name: other_model,
        },
    )

    _write_workspace(
        tmp_path,
    )

    write_artifact_config(
        "example",
        {
            "model": selected_model.name,
            "variant": "ridged",
        },
        project_root=tmp_path,
    )

    with pytest.raises(
        ConfigError,
        match="unknown variant",
    ):
        get_resolver(
            "example",
            project_root=tmp_path,
        )
