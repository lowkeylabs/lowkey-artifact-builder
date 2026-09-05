"""
Tests for the artifact show command.
"""
# File: tests/cli/test_show.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path
from typing import Any

from click.testing import CliRunner

import lowkey_artifact_builder.cli.cmd_show as cmd_show
from lowkey_artifact_builder.cli._main import cli
from lowkey_artifact_builder.config import (
    write_artifact_config,
)

# =========================================================
# Helpers
# =========================================================


def _invoke(
    *args: str,
) -> Any:
    """
    Invoke the artifact show command.
    """

    runner = CliRunner()

    return runner.invoke(
        cli,
        [
            "show",
            *args,
        ],
    )


# =========================================================
# Argument validation
# =========================================================


def test_show_requires_artifact_id() -> None:
    """
    Artifact inspection requires exactly one artifact ID.
    """

    result = _invoke()

    assert result.exit_code != 0
    assert "artifact" in result.output.lower()


def test_show_rejects_multiple_artifact_ids() -> None:
    """
    Artifact inspection operates on one artifact at a time.
    """

    result = _invoke(
        "skippy",
        "scooby",
    )

    assert result.exit_code != 0


# =========================================================
# Artifact existence
# =========================================================


def test_show_rejects_undefined_artifact(
    monkeypatch,
) -> None:
    """
    Artifact inspection requires an existing artifact definition.
    """

    monkeypatch.setattr(
        cmd_show,
        "load_artifact_config",
        lambda *args, **kwargs: {},
    )

    result = _invoke(
        "skippy",
    )

    assert result.exit_code != 0
    assert "not defined" in result.output.lower()


# =========================================================
# Artifact inspection
# =========================================================


def test_show_displays_existing_artifact(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    Show displays resolved configuration for an existing artifact.
    """

    displayed: list[tuple[str, Path]] = []

    monkeypatch.chdir(tmp_path)

    monkeypatch.setattr(
        cmd_show,
        "load_artifact_config",
        lambda *args, **kwargs: {
            "model": "artwork",
        },
    )

    monkeypatch.setattr(
        cmd_show,
        "_display_artifact",
        lambda artifact_id, *, project_root: displayed.append(
            (
                artifact_id,
                project_root,
            )
        ),
    )

    result = _invoke(
        "skippy",
    )

    assert result.exit_code == 0
    assert displayed == [
        (
            "skippy",
            tmp_path,
        ),
    ]


def test_show_qualified_variant_selects_model_and_local_variant(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    A qualified Variant selects its Model and local Variant name for
    artifact inspection.
    """

    displayed: list[
        tuple[
            str,
            str | None,
            str | None,
            Path,
        ]
    ] = []

    monkeypatch.chdir(tmp_path)

    monkeypatch.setattr(
        cmd_show,
        "load_artifact_config",
        lambda *args, **kwargs: {
            "model": "shape",
        },
    )

    def display_artifact(
        artifact_id: str,
        *,
        model_name: str | None = None,
        variant_name: str | None = None,
        project_root: Path,
    ) -> None:
        displayed.append(
            (
                artifact_id,
                model_name,
                variant_name,
                project_root,
            )
        )

    monkeypatch.setattr(
        cmd_show,
        "_display_artifact",
        display_artifact,
    )

    result = _invoke(
        "skippy",
        "--variant",
        "shape.ornament",
    )

    assert result.exit_code == 0

    assert displayed == [
        (
            "skippy",
            "shape",
            "ornament",
            tmp_path,
        )
    ]


def test_show_resolves_qualified_variant_configuration(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    Artifact inspection resolves a qualified Variant using its Model
    and local Variant name.
    """

    resolved: list[
        tuple[
            str,
            str | None,
            str | None,
            str | None,
            Path,
        ]
    ] = []

    class Resolver:
        def __call__(
            self,
            name: str,
        ) -> str:
            if name == "model":
                return "shape"

            raise KeyError(name)

    resolver = Resolver()

    def get_resolver(
        artifact_id: str,
        *,
        model: str | None = None,
        variant: str | None = None,
        realization: str | None = None,
        project_root: Path,
    ) -> Resolver:
        resolved.append(
            (
                artifact_id,
                model,
                variant,
                realization,
                project_root,
            )
        )

        return resolver

    class Registry:
        def get_model(
            self,
            model_name: str,
        ) -> object:
            assert model_name == "shape"
            return object()

    monkeypatch.setattr(
        cmd_show,
        "get_resolver",
        get_resolver,
    )

    monkeypatch.setattr(
        cmd_show,
        "build_model_registry",
        lambda: Registry(),
    )

    monkeypatch.setattr(
        cmd_show,
        "display_artifact_config",
        lambda *args: None,
    )

    cmd_show._display_artifact(
        "skippy",
        model_name="shape",
        variant_name="ornament",
        project_root=tmp_path,
    )

    assert resolved == [
        (
            "skippy",
            "shape",
            "ornament",
            None,
            tmp_path,
        )
    ]


def test_show_qualified_variant_uses_effective_variant_configuration(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    Show displays the effective configuration of the selected qualified
    Variant rather than the Artifact's configured default Variant.
    """

    displayed: list[
        tuple[
            str,
            str,
            str,
            float,
            str,
        ]
    ] = []

    monkeypatch.chdir(tmp_path)

    write_artifact_config(
        "skippy",
        {
            "model": "shape",
        },
        project_root=tmp_path,
    )

    def display(
        artifact_id: str,
        model,
        resolver,
    ) -> None:
        displayed.append(
            (
                artifact_id,
                model.name,
                resolver("variant"),
                resolver("shape_outer_ridge_width"),
                resolver.source("shape_outer_ridge_width"),
            )
        )

    monkeypatch.setattr(
        cmd_show,
        "display_artifact_config",
        display,
    )

    result = _invoke(
        "skippy",
        "--variant",
        "shape.ornament",
    )

    assert result.exit_code == 0

    assert displayed == [
        (
            "skippy",
            "shape",
            "ornament",
            2.0,
            "variant 'ornament'",
        )
    ]
