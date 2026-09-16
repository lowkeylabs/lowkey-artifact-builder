"""
Tests for the artifact create command.
"""
# File: tests/cli/test_create.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path
from typing import Any

from click.testing import CliRunner

import lowkey_artifact_builder.cli.cmd_create as cmd_create
from lowkey_artifact_builder.cli._main import cli
from lowkey_artifact_builder.config import (
    load_artifact_config,
)


def _invoke(
    *args: str,
    input: str | None = None,
) -> Any:
    """
    Invoke the artifact create command.
    """

    runner = CliRunner()

    return runner.invoke(
        cli,
        [
            "create",
            *args,
        ],
        input=input,
    )


# =========================================================
# Command
# =========================================================


def test_create_is_a_top_level_command() -> None:
    """
    Artifact creation is exposed as a distinct lifecycle operation.
    """

    runner = CliRunner()

    result = runner.invoke(
        cli,
        ["--help"],
    )

    assert result.exit_code == 0
    assert "create" in result.output


def test_create_without_artifact_id_ingests_root_pngs(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    Bare create treats root-level PNG files as the Artifact intake queue.

    Each PNG filename stem supplies the Artifact ID.
    """

    dog = tmp_path / "smith-dog.png"
    cat = tmp_path / "jones-cat.PNG"

    dog.write_bytes(b"dog")
    cat.write_bytes(b"cat")

    # Files outside the root PNG intake queue are ignored.
    (tmp_path / "notes.txt").write_text("notes")
    nested = tmp_path / "incoming"
    nested.mkdir()
    (nested / "lee-house.png").write_bytes(b"house")

    monkeypatch.chdir(tmp_path)

    configured: list[
        tuple[
            str,
            dict[str, Any],
            dict[str, Path],
            Path,
        ]
    ] = []

    def configure(
        artifact_id: str,
        *,
        values: dict[str, Any],
        input_files: dict[str, Path],
        project_root: Path,
    ) -> None:
        configured.append(
            (
                artifact_id,
                values,
                input_files,
                project_root,
            )
        )

    monkeypatch.setattr(
        cmd_create,
        "configure_artifact",
        configure,
    )

    monkeypatch.setattr(
        cmd_create,
        "_display_artifact",
        lambda *args, **kwargs: None,
    )

    result = _invoke()

    assert result.exit_code == 0

    assert configured == [
        (
            "jones-cat",
            {},
            {
                "artwork": cat,
            },
            tmp_path,
        ),
        (
            "smith-dog",
            {},
            {
                "artwork": dog,
            },
            tmp_path,
        ),
    ]


def test_create_rejects_multiple_explicit_artifact_ids() -> None:
    """
    Explicit creation addresses at most one named Artifact.

    Multiple positional Artifact IDs do not become an alternate batch syntax;
    bare create owns batch intake.
    """

    result = _invoke(
        "skippy",
        "scooby",
    )

    assert result.exit_code != 0


# =========================================================
# Lifecycle
# =========================================================


def test_create_rejects_existing_artifact(
    monkeypatch,
) -> None:
    """
    Creation does not silently become configuration of an existing artifact.
    """

    monkeypatch.setattr(
        cmd_create,
        "load_artifact_config",
        lambda *args, **kwargs: {
            "source": "artwork.png",
        },
    )

    result = _invoke(
        "skippy",
    )

    assert result.exit_code != 0
    assert "already" in result.output.lower()
    assert "defined" in result.output.lower()


# =========================================================
# Source
# =========================================================


def test_create_prompts_only_for_png_source(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    Artifact creation collects only the source artwork.

    Model configuration and Variant configuration are registered reusable
    configuration and are not reproduced interactively during creation.
    """

    source = tmp_path / "skippy.png"
    source.write_bytes(b"artwork")

    monkeypatch.chdir(tmp_path)

    configured: list[
        tuple[
            dict[str, Any],
            dict[str, Path],
        ]
    ] = []

    def configure(
        artifact_id: str,
        *,
        values: dict[str, Any],
        input_files: dict[str, Path],
        project_root: Path,
    ) -> None:
        configured.append(
            (
                values,
                input_files,
            )
        )

    monkeypatch.setattr(
        cmd_create,
        "configure_artifact",
        configure,
    )

    monkeypatch.setattr(
        cmd_create,
        "_display_artifact",
        lambda *args, **kwargs: None,
    )

    result = _invoke(
        "skippy",
        input="1\n",
    )

    assert result.exit_code == 0

    assert configured == [
        (
            {},
            {
                "artwork": source,
            },
        ),
    ]


def test_create_source_can_be_supplied_noninteractively(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    A source supplied on the command line avoids interactive source
    selection without exposing general Model parameter configuration.
    """

    source = tmp_path / "skippy.png"
    source.write_bytes(b"artwork")

    monkeypatch.chdir(tmp_path)

    configured: list[
        tuple[
            dict[str, Any],
            dict[str, Path],
        ]
    ] = []

    def configure(
        artifact_id: str,
        *,
        values: dict[str, Any],
        input_files: dict[str, Path],
        project_root: Path,
    ) -> None:
        configured.append(
            (
                values,
                input_files,
            )
        )

    monkeypatch.setattr(
        cmd_create,
        "configure_artifact",
        configure,
    )

    monkeypatch.setattr(
        cmd_create,
        "_display_artifact",
        lambda *args, **kwargs: None,
    )

    result = _invoke(
        "skippy",
        "--source",
        "skippy.png",
    )

    assert result.exit_code == 0

    assert configured == [
        (
            {},
            {
                "artwork": source,
            },
        ),
    ]


def test_create_rejects_missing_source_png(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    Artifact creation requires source artwork.
    """

    monkeypatch.chdir(tmp_path)

    result = _invoke(
        "skippy",
    )

    assert result.exit_code != 0
    assert "png" in result.output.lower()


def test_create_rejects_non_png_source(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    Artifact creation accepts PNG source artwork only.
    """

    source = tmp_path / "skippy.jpg"
    source.write_bytes(b"artwork")

    monkeypatch.chdir(tmp_path)

    result = _invoke(
        "skippy",
        "--source",
        "skippy.jpg",
    )

    assert result.exit_code != 0
    assert "png" in result.output.lower()


def test_create_does_not_expose_general_parameter_configuration() -> None:
    """
    Artifact creation accepts source artwork, not arbitrary configuration.

    Model defaults and Variant parameter assignments own reusable
    configuration; Artifact creation does not reproduce that configuration
    through generic parameter bindings.
    """

    result = _invoke(
        "--help",
    )

    assert result.exit_code == 0

    assert "--source" in result.output
    assert "--param" not in result.output


def test_create_persists_source_only_artifact_definition(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    Creating an Artifact persists only its Artifact-owned source.

    Ingesting artwork does not select a Model or serialize derived default
    Realizations. Model and Variant configuration remain registered reusable
    configuration.
    """

    source = tmp_path / "skippy.png"
    source.write_bytes(b"artwork")

    monkeypatch.chdir(tmp_path)

    result = _invoke(
        "skippy",
        "--source",
        "skippy.png",
    )

    assert result.exit_code == 0

    artifact_dir = tmp_path / "artifacts" / "skippy"

    assert (artifact_dir / "artifact.png").read_bytes() == b"artwork"

    assert load_artifact_config(
        "skippy",
        project_root=tmp_path,
    ) == {
        "source": str((artifact_dir / "artifact.png").resolve()),
    }


def test_create_batch_ingests_root_png_into_artifact_and_originals(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    Bare create owns root-level intake PNGs.

    Successful intake preserves the original, creates the Artifact-managed
    source, and removes the PNG from the root intake queue.
    """

    source = tmp_path / "smith-dog.png"
    source.write_bytes(b"dog artwork")

    monkeypatch.chdir(tmp_path)

    result = _invoke()

    assert result.exit_code == 0

    artifact_source = tmp_path / "artifacts" / "smith-dog" / "artifact.png"
    preserved_original = tmp_path / "originals" / "smith-dog.png"

    assert artifact_source.read_bytes() == b"dog artwork"
    assert preserved_original.read_bytes() == b"dog artwork"

    assert not source.exists()


def test_create_batch_with_empty_intake_is_successful_no_op(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    An empty root PNG intake queue is not an error.
    """

    monkeypatch.chdir(tmp_path)

    result = _invoke()

    assert result.exit_code == 0
    assert not (tmp_path / "artifacts").exists()
    assert not (tmp_path / "originals").exists()
