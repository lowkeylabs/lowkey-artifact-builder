"""
Tests for the artifact config command.
"""
# File: tests/cli/test_config.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path
from typing import Any

from click.testing import CliRunner

import lowkey_artifact_builder.cli.cmd_config as cmd_config
from lowkey_artifact_builder.cli._main import cli

# =========================================================
# Helpers
# =========================================================


def _invoke(
    *args: str,
) -> Any:
    """
    Invoke the artifact config command.
    """

    runner = CliRunner()

    return runner.invoke(
        cli,
        [
            "config",
            *args,
        ],
    )


# =========================================================
# Argument validation
# =========================================================


def test_config_requires_artifact_id() -> None:
    """
    Artifact configuration requires an artifact ID unless performing
    model inspection.
    """

    result = _invoke()

    assert result.exit_code != 0
    assert "artifact" in result.output.lower()


def test_config_rejects_multiple_artifact_ids() -> None:
    """
    Artifact configuration operates on exactly one artifact at a time.
    """

    result = _invoke(
        "skippy",
        "scooby",
    )

    assert result.exit_code != 0


# =========================================================
# Existing artifact
# =========================================================


def test_config_displays_existing_artifact(
    monkeypatch,
) -> None:
    """
    Supplying an existing artifact ID displays its configuration.
    """

    displayed: list[str] = []

    monkeypatch.setattr(
        cmd_config,
        "load_artifact_config",
        lambda *args, **kwargs: {
            "source": "skippy.png",
        },
    )

    monkeypatch.setattr(
        cmd_config,
        "_display_artifact",
        lambda artifact_id, **kwargs: displayed.append(
            artifact_id,
        ),
    )

    result = _invoke(
        "skippy",
    )

    assert result.exit_code == 0
    assert displayed == ["skippy"]


def test_config_displays_source_only_artifact_without_singular_model(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    Artifact configuration inspection does not require the Artifact to
    select one Model.

    Effective Realizations are derived from the registered Model Variant
    catalog.
    """

    displayed: list[
        tuple[
            str,
            dict[str, str],
            tuple[str, ...],
        ]
    ] = []

    artifact = {
        "source": "skippy.png",
    }

    monkeypatch.setattr(
        cmd_config,
        "load_artifact_config",
        lambda *args, **kwargs: artifact,
    )

    monkeypatch.setattr(
        cmd_config,
        "get_realization_names",
        lambda *args, **kwargs: (
            "artwork_default",
            "shape_default",
            "shape_ornament",
        ),
    )

    monkeypatch.setattr(
        cmd_config,
        "display_artifact_definition",
        lambda artifact_id, configuration, realizations: displayed.append(
            (
                artifact_id,
                configuration,
                realizations,
            )
        ),
    )

    cmd_config._display_artifact(
        "skippy",
        project_root=tmp_path,
    )

    assert displayed == [
        (
            "skippy",
            artifact,
            (
                "artwork_default",
                "shape_default",
                "shape_ornament",
            ),
        )
    ]


# =========================================================
# Undefined artifact
# =========================================================


def test_config_rejects_undefined_artifact(
    monkeypatch,
) -> None:
    """
    Configuration does not implicitly create an undefined artifact.

    Artifact creation is a distinct lifecycle operation owned by
    `artifact create`.
    """

    monkeypatch.setattr(
        cmd_config,
        "load_artifact_config",
        lambda *args, **kwargs: {},
    )

    result = _invoke(
        "skippy",
    )

    assert result.exit_code != 0
    assert "not defined" in result.output.lower()
