"""
Tests for manufacturing-oriented Artifact inspection through SHOW.

SHOW presents reusable manufacturing inspection results to the operator.
It does not reconstruct configuration, planning, Product state, or
filesystem state in the CLI layer.
"""

# File: tests/cli/test_show_manufacturing.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path
from typing import Any

from click.testing import CliRunner

import lowkey_artifact_builder.cli.cmd_show as cmd_show
from lowkey_artifact_builder.application.manufacturing import (
    ArtifactManufacturingStatus,
    ManufacturingState,
    RealizationManufacturingStatus,
    RealizationType,
)
from lowkey_artifact_builder.cli._main import cli

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


def _realization(
    name: str,
    *,
    realization_type: RealizationType,
    state: ManufacturingState,
    product: Path | None = None,
) -> RealizationManufacturingStatus:
    """
    Construct one reusable manufacturing-inspection result.
    """

    return RealizationManufacturingStatus(
        realization=name,
        realization_type=realization_type,
        state=state,
        product=product,
    )


def _status(
    *realizations: RealizationManufacturingStatus,
) -> ArtifactManufacturingStatus:
    """
    Construct one Artifact manufacturing-inspection result.
    """

    return ArtifactManufacturingStatus(
        artifact_id="skippy",
        realizations=realizations,
    )


# =========================================================
# Application delegation
# =========================================================


def test_show_requests_artifact_manufacturing_status(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    SHOW delegates manufacturing inspection to the reusable application
    operation using the current project root.
    """

    calls: list[
        tuple[
            str,
            str | None,
            Path,
        ]
    ] = []

    monkeypatch.chdir(
        tmp_path,
    )

    def inspect(
        artifact_id: str,
        *,
        realization: str | None = None,
        project_root: Path,
    ) -> ArtifactManufacturingStatus:
        calls.append(
            (
                artifact_id,
                realization,
                project_root,
            )
        )

        return _status()

    monkeypatch.setattr(
        cmd_show,
        "inspect_artifact_manufacturing",
        inspect,
    )

    result = _invoke(
        "skippy",
    )

    assert result.exit_code == 0, result.output

    assert calls == [
        (
            "skippy",
            None,
            tmp_path,
        )
    ]


def test_show_realization_requests_selected_manufacturing_status(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    --realization selects one Artifact Realization for manufacturing
    inspection.
    """

    calls: list[
        tuple[
            str,
            str | None,
            Path,
        ]
    ] = []

    monkeypatch.chdir(
        tmp_path,
    )

    def inspect(
        artifact_id: str,
        *,
        realization: str | None = None,
        project_root: Path,
    ) -> ArtifactManufacturingStatus:
        calls.append(
            (
                artifact_id,
                realization,
                project_root,
            )
        )

        return _status(
            _realization(
                "shape_ornament",
                realization_type=RealizationType.BUILT_IN,
                state=ManufacturingState.NOT_BUILT,
            )
        )

    monkeypatch.setattr(
        cmd_show,
        "inspect_artifact_manufacturing",
        inspect,
    )

    result = _invoke(
        "skippy",
        "--realization",
        "shape_ornament",
    )

    assert result.exit_code == 0, result.output

    assert calls == [
        (
            "skippy",
            "shape_ornament",
            tmp_path,
        )
    ]


# =========================================================
# Manufacturing overview
# =========================================================


def test_show_displays_manufacturing_overview(
    monkeypatch,
) -> None:
    """
    SHOW presents the operator-relevant manufacturing dimensions:
    Realization, type, state, and accessible 3MF.

    Published manufacturing results are presented by operator-facing
    filename rather than exposing or depending on long internal paths.
    """

    monkeypatch.setattr(
        cmd_show,
        "inspect_artifact_manufacturing",
        lambda *args, **kwargs: _status(
            _realization(
                "artwork_default",
                realization_type=RealizationType.BUILT_IN,
                state=ManufacturingState.CURRENT,
                product=Path("artwork_default.3mf"),
            ),
            _realization(
                "shape_default",
                realization_type=RealizationType.BUILT_IN,
                state=ManufacturingState.NOT_BUILT,
            ),
            _realization(
                "shape_ornament",
                realization_type=RealizationType.BUILT_IN,
                state=ManufacturingState.NOT_BUILT,
            ),
            _realization(
                "large-ornament",
                realization_type=RealizationType.CUSTOM,
                state=ManufacturingState.STALE,
                product=Path("large-ornament.3mf"),
            ),
        ),
    )

    result = _invoke(
        "skippy",
    )

    assert result.exit_code == 0, result.output

    assert "Realization" in result.output
    assert "Type" in result.output
    assert "State" in result.output
    assert "3MF" in result.output

    assert "artwork_default" in result.output
    assert "shape_default" in result.output
    assert "shape_ornament" in result.output
    assert "large-ornament" in result.output

    assert "built-in" in result.output
    assert "custom" in result.output

    assert "current" in result.output
    assert "not built" in result.output
    assert "stale" in result.output

    assert "artwork_default.3mf" in result.output
    assert "large-ornament.3mf" in result.output


def test_show_realization_displays_only_selected_realization(
    monkeypatch,
) -> None:
    """
    Focused SHOW presents only the selected Realization returned by the
    application operation.
    """

    monkeypatch.setattr(
        cmd_show,
        "inspect_artifact_manufacturing",
        lambda *args, **kwargs: _status(
            _realization(
                "shape_ornament",
                realization_type=RealizationType.BUILT_IN,
                state=ManufacturingState.CURRENT,
                product=Path("artifacts/skippy/shape_ornament.3mf"),
            )
        ),
    )

    result = _invoke(
        "skippy",
        "--realization",
        "shape_ornament",
    )

    assert result.exit_code == 0, result.output

    assert "shape_ornament" in result.output
    assert "current" in result.output
    assert "shape_ornament.3mf" in result.output

    assert "artwork_default" not in result.output
    assert "shape_default" not in result.output


# =========================================================
# Operator abstraction
# =========================================================


def test_show_does_not_display_internal_manufacturing_details(
    monkeypatch,
) -> None:
    """
    Routine SHOW output does not expose Stage, resolver, dependency, or
    internal canonical Product details.
    """

    monkeypatch.setattr(
        cmd_show,
        "inspect_artifact_manufacturing",
        lambda *args, **kwargs: _status(
            _realization(
                "shape_ornament",
                realization_type=RealizationType.BUILT_IN,
                state=ManufacturingState.CURRENT,
                product=Path("artifacts/skippy/shape_ornament.3mf"),
            )
        ),
    )

    result = _invoke(
        "skippy",
    )

    assert result.exit_code == 0, result.output

    output = result.output.lower()

    assert "shape_ornament" in output
    assert "current" in output

    assert "stage" not in output
    assert "resolver" not in output
    assert "dependency" not in output
    assert "40-package" not in output
    assert "artifact.3mf" not in output


# =========================================================
# Errors
# =========================================================


def test_show_translates_expected_inspection_error(
    monkeypatch,
) -> None:
    """
    Expected application/configuration inspection errors become concise
    operator-facing CLI errors without a traceback.
    """

    from lowkey_artifact_builder.config import ConfigError

    def inspect(*args, **kwargs):
        raise ConfigError("Realization 'does-not-exist' is not available for artifact 'skippy'.")

    monkeypatch.setattr(
        cmd_show,
        "inspect_artifact_manufacturing",
        inspect,
    )

    result = _invoke(
        "skippy",
        "--realization",
        "does-not-exist",
    )

    assert result.exit_code != 0

    assert "does-not-exist" in result.output
    assert "skippy" in result.output
    assert "traceback" not in result.output.lower()
