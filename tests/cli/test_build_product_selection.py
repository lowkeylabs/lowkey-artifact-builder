"""CLI selection of first-class SHAPE manufacturing Products.

Phase 2, Slice C: explicit SVG selection reaches the application
build boundary without changing the legacy 3MF default.
"""

# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from lowkey_artifact_builder.cli._main import cli
from lowkey_artifact_builder.config import write_artifact_config

ARTIFACT_ID = "cli-svg-target"
REALIZATION = "coaster_front"


def _configure(root: Path) -> None:
    write_artifact_config(
        ARTIFACT_ID,
        {
            "model": "shape",
            "realizations": {
                REALIZATION: {
                    "variant": "shape.coaster",
                },
            },
        },
        project_root=root,
    )


def _invoke(*args: str):
    return CliRunner().invoke(
        cli,
        ["build", *args],
    )


def _artifact_dir(root: Path) -> Path:
    return root / "artifacts" / ARTIFACT_ID


def test_cli_explicit_svg_build_publishes_without_3mf(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """An operator can request a standalone SHAPE SVG."""
    _configure(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = _invoke(
        ARTIFACT_ID,
        "--realization",
        REALIZATION,
        "--product",
        "svg",
    )

    assert result.exit_code == 0, result.output

    artifact_dir = _artifact_dir(tmp_path)
    realization_dir = artifact_dir / "shape" / REALIZATION

    canonical_svg = realization_dir / "20-compose" / "artifact.svg"
    published_svg = artifact_dir / f"{REALIZATION}.svg"

    assert canonical_svg.is_file()
    assert published_svg.is_file()
    assert published_svg.read_bytes() == canonical_svg.read_bytes()

    assert not (realization_dir / "30-extrude").exists()
    assert not (realization_dir / "40-package").exists()
    assert not (artifact_dir / f"{REALIZATION}.3mf").exists()


def test_cli_svg_dry_run_selects_compose_without_execution(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Dry-run uses the same requested Product as execution."""
    _configure(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = _invoke(
        ARTIFACT_ID,
        "--realization",
        REALIZATION,
        "--product",
        "svg",
        "--dry-run",
    )

    assert result.exit_code == 0, result.output

    # Planning may inspect configuration but must not manufacture.
    realization_dir = _artifact_dir(tmp_path) / "shape" / REALIZATION

    assert not (realization_dir / "20-compose" / "artifact.svg").exists()
    assert not (realization_dir / "40-package" / "artifact.3mf").exists()
    assert not (_artifact_dir(tmp_path) / f"{REALIZATION}.svg").exists()


def test_cli_rejects_product_selection_with_independent_stage(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Manufacturing Product selection is not Stage execution."""
    _configure(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = _invoke(
        ARTIFACT_ID,
        "--realization",
        REALIZATION,
        "--stage",
        "compose",
        "--product",
        "svg",
    )

    assert result.exit_code != 0
    assert "--product" in result.output
    assert "--stage" in result.output
