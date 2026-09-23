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
from lowkey_artifact_builder.config import ConfigError

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


# =========================================================
# Realization configuration inspection
# =========================================================


def test_config_accepts_realization_for_existing_artifact(
    monkeypatch,
) -> None:
    """
    Configuration may inspect one effective Artifact Realization.
    """

    displayed: list[tuple[str, str]] = []

    monkeypatch.setattr(
        cmd_config,
        "load_artifact_config",
        lambda *args, **kwargs: {
            "source": "artifacts/skippy/artifact.png",
        },
    )

    monkeypatch.setattr(
        cmd_config,
        "_display_realization",
        lambda artifact_id, realization, **kwargs: displayed.append(
            (
                artifact_id,
                realization,
            )
        ),
        raising=False,
    )

    result = _invoke(
        "skippy",
        "--realization",
        "shape_ornament",
    )

    assert result.exit_code == 0
    assert displayed == [
        (
            "skippy",
            "shape_ornament",
        )
    ]


def test_config_rejects_unknown_realization(
    monkeypatch,
) -> None:
    """
    Configuration inspection does not silently interpret an unknown
    Realization name as a new Realization.
    """

    monkeypatch.setattr(
        cmd_config,
        "load_artifact_config",
        lambda *args, **kwargs: {
            "source": "artifacts/skippy/artifact.png",
        },
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

    result = _invoke(
        "skippy",
        "--realization",
        "shape_typo",
    )

    assert result.exit_code != 0
    assert "shape_typo" in result.output
    assert "realization" in result.output.lower()


# =========================================================
# Realization customization
# =========================================================


def test_config_updates_existing_realization_parameters(
    monkeypatch,
) -> None:
    """
    Configuration may customize parameters of an existing effective
    Artifact Realization.
    """

    configured: list[
        tuple[
            str,
            str,
            dict[str, object],
        ]
    ] = []

    monkeypatch.setattr(
        cmd_config,
        "load_artifact_config",
        lambda *args, **kwargs: {
            "source": "artifacts/skippy/artifact.png",
        },
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
        "_configure_realization",
        lambda artifact_id, realization, parameters, **kwargs: configured.append(
            (
                artifact_id,
                realization,
                parameters,
            )
        ),
        raising=False,
    )

    result = _invoke(
        "skippy",
        "--realization",
        "shape_ornament",
        "--parameters",
        "shape_size=110",
    )

    assert result.exit_code == 0
    assert configured == [
        (
            "skippy",
            "shape_ornament",
            {
                "shape_size": 110,
            },
        )
    ]


def test_config_realization_parameters_require_realization() -> None:
    """
    Realization parameter customization requires an explicit
    Realization coordinate.
    """

    result = _invoke(
        "skippy",
        "--parameters",
        "shape_size=110",
    )

    assert result.exit_code != 0
    assert "realization" in result.output.lower()


def test_config_parameters_do_not_create_unknown_realization(
    monkeypatch,
) -> None:
    """
    Parameter customization reports configuration-layer rejection of a
    misspelled or otherwise unknown Realization.
    """

    monkeypatch.setattr(
        cmd_config,
        "load_artifact_config",
        lambda *args, **kwargs: {
            "source": "artifacts/skippy/artifact.png",
        },
    )

    def reject_unknown_realization(
        artifact_id: str,
        realization: str,
        *,
        parameters: dict[str, object],
        **kwargs,
    ) -> None:
        raise ConfigError(
            f"Realization {realization!r} is not defined for Artifact {artifact_id!r}."
        )

    monkeypatch.setattr(
        cmd_config,
        "configure_realization",
        reject_unknown_realization,
    )

    result = _invoke(
        "skippy",
        "--realization",
        "shape_typo",
        "--parameters",
        "shape_size=110",
    )

    assert result.exit_code != 0
    assert "shape_typo" in result.output
    assert "realization" in result.output.lower()


def test_config_create_named_realization(
    monkeypatch,
) -> None:
    """
    --create permits definition of an additional named Realization.
    """

    created: list[
        tuple[
            str,
            str,
            str,
            dict[str, object],
        ]
    ] = []

    monkeypatch.setattr(
        cmd_config,
        "load_artifact_config",
        lambda *args, **kwargs: {
            "source": "artifacts/skippy/artifact.png",
        },
    )

    monkeypatch.setattr(
        cmd_config,
        "_create_realization",
        lambda artifact_id, realization, variant, parameters, **kwargs: created.append(
            (
                artifact_id,
                realization,
                variant,
                parameters,
            )
        ),
        raising=False,
    )

    result = _invoke(
        "skippy",
        "--realization",
        "large-ornament",
        "--create",
        "--parameters",
        "variant=shape.ornament",
        "--parameters",
        "shape_size=125",
    )

    assert result.exit_code == 0
    assert created == [
        (
            "skippy",
            "large-ornament",
            "shape.ornament",
            {
                "shape_size": 125,
            },
        )
    ]


def test_config_create_realization_requires_variant(
    monkeypatch,
) -> None:
    """
    Creating an additional named Realization requires an originating
    qualified Variant.
    """

    monkeypatch.setattr(
        cmd_config,
        "load_artifact_config",
        lambda *args, **kwargs: {
            "source": "artifacts/skippy/artifact.png",
        },
    )

    result = _invoke(
        "skippy",
        "--realization",
        "large-ornament",
        "--create",
        "--parameters",
        "shape_size=125",
    )

    assert result.exit_code != 0
    assert "variant" in result.output.lower()


def test_config_create_realization_across_all_artifacts(
    monkeypatch,
) -> None:
    """
    Omitting Artifact IDs selects all Artifacts for bulk Realization
    creation.
    """

    created: list[
        tuple[
            tuple[str, ...],
            str,
            str,
            dict[str, object],
        ]
    ] = []

    monkeypatch.setattr(
        cmd_config,
        "_create_realization_scope",
        lambda artifact_ids, realization, variant, parameters, **kwargs: created.append(
            (
                artifact_ids,
                realization,
                variant,
                parameters,
            )
        ),
        raising=False,
    )

    result = _invoke(
        "--realization",
        "large-ornament",
        "--create",
        "--parameters",
        "variant=shape.ornament",
        "--parameters",
        "shape_size=125",
    )

    assert result.exit_code == 0
    assert created == [
        (
            (),
            "large-ornament",
            "shape.ornament",
            {
                "shape_size": 125,
            },
        )
    ]
