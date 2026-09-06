"""
Tests for model-scoped Variant configuration resolution.

Variants are reusable named Model-scoped configurations expressed as
sparse parameter overrides over Model defaults.

These tests establish how Variant selection participates in configuration
resolution. Runtime Realization identity, filesystem placement, planning,
and public Variant selection belong to later phases.
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
    Return a minimal model with default and specialized Variants.

    Ordinary behavior belongs to Model defaults. The specialized Variant
    overrides only the value that distinguishes it from that behavior.
    """

    return ModelSpec(
        name="example-model",
        title="Example Model",
        variants=(
            VariantSpec(
                name="default",
            ),
            VariantSpec(
                name="ridged",
                parameters={
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
    *,
    model_parameters: dict[str, dict[str, object]] | None = None,
) -> None:
    """
    Install deterministic Model definitions and parameter defaults.

    Variant lookup occurs through the Model registry. Model parameter
    defaults remain a separate configuration layer beneath sparse
    Variant overrides.
    """

    parameters = model_parameters or {}

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
        lambda name: dict(parameters.get(name, {})),
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
    Install a Model with ordinary defaults and one sparse Variant.
    """

    model = _model_with_variants()

    _install_models(
        monkeypatch,
        {
            model.name: model,
        },
        model_parameters={
            model.name: {
                "ridge": False,
                "ridge_width": 1.0,
                "material": "pla",
            },
        },
    )

    return model


# =========================================================
# Default Variant
# =========================================================


def test_resolver_uses_empty_default_variant_with_model_defaults(
    tmp_path: Path,
    variant_model: ModelSpec,
) -> None:
    """
    The empty default Variant preserves ordinary Model behavior.
    """

    _write_workspace(tmp_path)

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
    assert resolver("material") == "pla"

    assert resolver.source("ridge") == "model"
    assert resolver.source("ridge_width") == "model"
    assert resolver.source("material") == "model"


def test_implicit_empty_default_variant_preserves_existing_resolution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    A Model needing no explicit Variant declaration still receives an
    empty default Variant without changing Model parameter resolution.
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
        model_parameters={
            model.name: {
                "ridge": False,
                "ridge_width": 1.0,
            },
        },
    )

    _write_workspace(tmp_path)

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

    assert resolver("ridge") is False
    assert resolver("ridge_width") == 1.0

    assert resolver.source("ridge") == "model"
    assert resolver.source("ridge_width") == "model"


# =========================================================
# Sparse specialized Variant
# =========================================================


def test_resolver_applies_sparse_variant_over_model_defaults(
    tmp_path: Path,
    variant_model: ModelSpec,
) -> None:
    """
    A specialized Variant overrides only the parameters it names.

    Parameters omitted by the Variant continue to resolve from Model
    defaults.
    """

    _write_workspace(tmp_path)

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

    assert resolver("ridge") is False
    assert resolver("ridge_width") == 3.0
    assert resolver("material") == "pla"

    assert resolver.source("ridge") == "model"
    assert resolver.source("ridge_width") == "variant 'ridged'"
    assert resolver.source("material") == "model"


def test_new_model_default_does_not_require_variant_change(
    tmp_path: Path,
    variant_model: ModelSpec,
) -> None:
    """
    A specialized Variant automatically inherits usable Model defaults
    for parameters it does not override.
    """

    _write_workspace(tmp_path)

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

    ridged = next(variant for variant in variant_model.variants if variant.name == "ridged")

    assert "material" not in ridged.parameters

    assert resolver("material") == "pla"
    assert resolver.source("material") == "model"


# =========================================================
# Later configuration scopes
# =========================================================


def test_workspace_parameters_override_sparse_variant_parameters(
    tmp_path: Path,
    variant_model: ModelSpec,
) -> None:
    """
    Workspace configuration retains its existing precedence over Variant
    overrides.
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

    assert resolver("ridge_width") == 4.0
    assert resolver.source("ridge_width") == "workspace"


def test_artifact_customization_overrides_variant_without_changing_identity(
    tmp_path: Path,
    variant_model: ModelSpec,
) -> None:
    """
    Artifact-specific customization changes effective configuration
    without changing the originating Variant.
    """

    _write_workspace(tmp_path)

    write_artifact_config(
        "example",
        {
            "model": variant_model.name,
            "variant": "ridged",
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
    assert resolver("material") == "pla"

    assert resolver.source("ridge") == "model"
    assert resolver.source("ridge_width") == "artifact"
    assert resolver.source("material") == "model"


# =========================================================
# Validation
# =========================================================


def test_resolver_rejects_unknown_variant(
    tmp_path: Path,
    variant_model: ModelSpec,
) -> None:
    """
    A configured Variant must exist in the selected Model.
    """

    _write_workspace(tmp_path)

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
    A Variant is resolved only within the selected Model.
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
                    "ridge_width": 3.0,
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

    _write_workspace(tmp_path)

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


def test_resolver_may_select_variant_through_realization_local_name(
    tmp_path: Path,
) -> None:
    """
    Historical realization carries the local-name component of Variant identity.

    Selecting realization "ornament" for the Shape Model therefore resolves
    the shape.ornament Variant rather than an independent Artifact Realization.
    """

    write_artifact_config(
        "example",
        {
            "model": "shape",
        },
        project_root=tmp_path,
    )

    resolver = get_resolver(
        "example",
        model="shape",
        realization="ornament",
        project_root=tmp_path,
    )

    assert resolver("model") == "shape"
    assert resolver("variant") == "ornament"
    assert resolver("realization") == "ornament"

    assert resolver("shape_outer_ridge_width") == 2.0
    assert resolver.source("shape_outer_ridge_width") == "variant 'ornament'"
