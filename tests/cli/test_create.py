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


def _create_existing_batch_artifact(
    tmp_path: Path,
    artifact_id: str,
    *,
    content: bytes,
) -> None:
    """
    Establish an Artifact in the same state produced by successful batch
    intake.
    """

    source = tmp_path / f"{artifact_id}.png"
    source.write_bytes(content)

    result = _invoke()

    assert result.exit_code == 0
    assert not source.exists()


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


def test_create_batch_recognizes_verified_duplicate(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    Bare batch intake recognizes a verified duplicate and leaves it in the
    intake queue when the operator accepts the default No cleanup response.
    """

    monkeypatch.chdir(tmp_path)

    _create_existing_batch_artifact(
        tmp_path,
        "smith-cat",
        content=b"cat artwork",
    )

    duplicate = tmp_path / "smith-cat.png"
    duplicate.write_bytes(b"cat artwork")

    result = _invoke(
        input="\n",
    )

    assert result.exit_code == 0
    assert "duplicate" in result.output.lower()
    assert "smith-cat" in result.output.lower()
    assert duplicate.read_bytes() == b"cat artwork"


def test_create_batch_can_remove_verified_duplicate_interactively(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    Bare batch intake offers cleanup for a verified duplicate and removes the
    intake PNG when the operator explicitly approves.
    """

    monkeypatch.chdir(tmp_path)

    _create_existing_batch_artifact(
        tmp_path,
        "smith-cat",
        content=b"cat artwork",
    )

    duplicate = tmp_path / "smith-cat.png"
    duplicate.write_bytes(b"cat artwork")

    result = _invoke(
        input="y\n",
    )

    assert result.exit_code == 0

    assert "smith-cat" in result.output.lower()
    assert "remove" in result.output.lower()
    assert not duplicate.exists()

    assert (tmp_path / "originals" / "smith-cat.png").read_bytes() == b"cat artwork"

    assert (tmp_path / "artifacts" / "smith-cat" / "artifact.png").read_bytes() == b"cat artwork"


def test_create_batch_clean_removes_duplicate_without_prompt(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    --clean performs verified duplicate cleanup without requesting interactive
    approval.
    """

    monkeypatch.chdir(tmp_path)

    _create_existing_batch_artifact(
        tmp_path,
        "smith-cat",
        content=b"cat artwork",
    )

    duplicate = tmp_path / "smith-cat.png"
    duplicate.write_bytes(b"cat artwork")

    result = _invoke(
        "--clean",
    )

    assert result.exit_code == 0
    assert not duplicate.exists()

    assert "remove the duplicate" not in result.output.lower()


def test_create_batch_rejects_inconsistent_managed_source(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    Matching incoming and preserved-original bytes do not establish a
    duplicate when the managed Artifact source has diverged.
    """

    monkeypatch.chdir(tmp_path)

    _create_existing_batch_artifact(
        tmp_path,
        "smith-cat",
        content=b"cat artwork",
    )

    managed = tmp_path / "artifacts" / "smith-cat" / "artifact.png"
    managed.write_bytes(b"changed managed artwork")

    incoming = tmp_path / "smith-cat.png"
    incoming.write_bytes(b"cat artwork")

    result = _invoke()

    assert result.exit_code != 0
    assert "smith-cat" in result.output.lower()

    assert incoming.read_bytes() == b"cat artwork"


def test_create_batch_rejects_inconsistent_preserved_original(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    Matching incoming and managed-source bytes do not establish a duplicate
    when the preserved original has diverged.
    """

    monkeypatch.chdir(tmp_path)

    _create_existing_batch_artifact(
        tmp_path,
        "smith-cat",
        content=b"cat artwork",
    )

    original = tmp_path / "originals" / "smith-cat.png"
    original.write_bytes(b"changed original artwork")

    incoming = tmp_path / "smith-cat.png"
    incoming.write_bytes(b"cat artwork")

    result = _invoke()

    assert result.exit_code != 0
    assert "smith-cat" in result.output.lower()

    assert incoming.read_bytes() == b"cat artwork"


def test_create_batch_rejects_conflicting_input(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    A new incoming PNG for an existing Artifact is a conflict when it matches
    neither the preserved original nor the managed source.
    """

    monkeypatch.chdir(tmp_path)

    _create_existing_batch_artifact(
        tmp_path,
        "smith-cat",
        content=b"original cat artwork",
    )

    incoming = tmp_path / "smith-cat.png"
    incoming.write_bytes(b"different cat artwork")

    result = _invoke()

    assert result.exit_code != 0
    assert "smith-cat" in result.output.lower()

    assert incoming.read_bytes() == b"different cat artwork"


def test_create_batch_rejects_incomplete_existing_artifact(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    An existing Artifact cannot be classified as a duplicate when a required
    provenance file is missing.
    """

    monkeypatch.chdir(tmp_path)

    _create_existing_batch_artifact(
        tmp_path,
        "smith-cat",
        content=b"cat artwork",
    )

    original = tmp_path / "originals" / "smith-cat.png"
    original.unlink()

    incoming = tmp_path / "smith-cat.png"
    incoming.write_bytes(b"cat artwork")

    result = _invoke()

    assert result.exit_code != 0
    assert "smith-cat" in result.output.lower()

    assert incoming.read_bytes() == b"cat artwork"


def test_create_batch_duplicate_does_not_block_new_intake(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    A verified duplicate does not prevent independent NEW intake from being
    processed when the operator declines duplicate cleanup.
    """

    monkeypatch.chdir(tmp_path)

    _create_existing_batch_artifact(
        tmp_path,
        "smith-cat",
        content=b"cat artwork",
    )

    duplicate = tmp_path / "smith-cat.png"
    new_source = tmp_path / "jones-dog.png"

    duplicate.write_bytes(b"cat artwork")
    new_source.write_bytes(b"dog artwork")

    result = _invoke(
        input="\n",
    )

    assert result.exit_code == 0
    assert "duplicate" in result.output.lower()

    # Declining duplicate cleanup leaves the verified duplicate in the queue.
    assert duplicate.read_bytes() == b"cat artwork"

    # Independent NEW intake is still processed normally.
    assert not new_source.exists()

    assert (tmp_path / "artifacts" / "jones-dog" / "artifact.png").read_bytes() == b"dog artwork"

    assert (tmp_path / "originals" / "jones-dog.png").read_bytes() == b"dog artwork"


def test_create_batch_rejects_incomplete_existing_artifact_without_managed_source(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    An existing Artifact cannot be classified as a duplicate when its managed
    source is missing.
    """

    monkeypatch.chdir(tmp_path)

    _create_existing_batch_artifact(
        tmp_path,
        "smith-cat",
        content=b"cat artwork",
    )

    managed = tmp_path / "artifacts" / "smith-cat" / "artifact.png"
    managed.unlink()

    incoming = tmp_path / "smith-cat.png"
    incoming.write_bytes(b"cat artwork")

    result = _invoke()

    assert result.exit_code != 0
    assert "smith-cat" in result.output.lower()

    assert incoming.read_bytes() == b"cat artwork"


def test_create_batch_preflights_existing_artifact_before_mutation(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    A predictable Artifact collision aborts the complete intake batch before
    unrelated sources are mutated.
    """

    existing_source = tmp_path / "existing.png"
    existing_source.write_bytes(b"existing artwork")

    monkeypatch.chdir(tmp_path)

    existing_result = _invoke(
        "smith-cat",
        "--source",
        "existing.png",
    )

    assert existing_result.exit_code == 0

    # These are the batch intake queue. The first sorts before the collision,
    # proving that preflight occurs before normal batch mutation.
    new_source = tmp_path / "jones-dog.png"
    conflicting_source = tmp_path / "smith-cat.png"

    new_source.write_bytes(b"new dog")
    conflicting_source.write_bytes(b"different cat")

    result = _invoke()

    assert result.exit_code != 0
    assert "smith-cat" in result.output.lower()

    # The unrelated earlier-sorting intake item was not processed.
    assert new_source.read_bytes() == b"new dog"
    assert not (tmp_path / "artifacts" / "jones-dog").exists()
    assert not (tmp_path / "originals" / "jones-dog.png").exists()

    # The conflicting intake source was not consumed either.
    assert conflicting_source.read_bytes() == b"different cat"


def test_create_batch_artifact_id_collisions_are_case_insensitive(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    Artifact identity collisions are detected case-insensitively so project
    identity remains portable across filesystems.
    """

    existing_source = tmp_path / "existing.png"
    existing_source.write_bytes(b"existing artwork")

    monkeypatch.chdir(tmp_path)

    existing_result = _invoke(
        "smith-cat",
        "--source",
        "existing.png",
    )

    assert existing_result.exit_code == 0

    incoming = tmp_path / "SMITH-CAT.png"
    incoming.write_bytes(b"different artwork")

    result = _invoke()

    assert result.exit_code != 0
    assert "smith-cat" in result.output.lower()

    assert incoming.read_bytes() == b"different artwork"
    assert not (tmp_path / "artifacts" / "SMITH-CAT").exists()


def test_create_batch_preflights_original_destination_before_mutation(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    An unexpected preserved-original collision aborts the complete intake
    batch before any intake source is mutated.
    """

    originals = tmp_path / "originals"
    originals.mkdir()

    preserved = originals / "smith-cat.png"
    preserved.write_bytes(b"unrelated preserved artwork")

    new_source = tmp_path / "jones-dog.png"
    conflicting_source = tmp_path / "smith-cat.png"

    new_source.write_bytes(b"new dog")
    conflicting_source.write_bytes(b"new cat")

    monkeypatch.chdir(tmp_path)

    result = _invoke()

    assert result.exit_code != 0
    assert "smith-cat" in result.output.lower()

    # Whole-batch preflight prevents the earlier-sorting valid source from
    # being processed before the later collision is discovered.
    assert new_source.read_bytes() == b"new dog"
    assert conflicting_source.read_bytes() == b"new cat"

    assert not (tmp_path / "artifacts" / "jones-dog").exists()
    assert not (tmp_path / "artifacts" / "smith-cat").exists()

    # Existing project state is untouched.
    assert preserved.read_bytes() == b"unrelated preserved artwork"


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


def test_create_batch_clean_removes_verified_duplicate(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    --clean removes a root-level intake PNG only after it has been positively
    classified as a verified duplicate.
    """

    monkeypatch.chdir(tmp_path)

    _create_existing_batch_artifact(
        tmp_path,
        "smith-cat",
        content=b"cat artwork",
    )

    duplicate = tmp_path / "smith-cat.png"
    duplicate.write_bytes(b"cat artwork")

    result = _invoke(
        "--clean",
    )

    assert result.exit_code == 0
    assert "duplicate" in result.output.lower()
    assert not duplicate.exists()

    assert (tmp_path / "originals" / "smith-cat.png").read_bytes() == b"cat artwork"

    assert (tmp_path / "artifacts" / "smith-cat" / "artifact.png").read_bytes() == b"cat artwork"


def test_create_batch_clean_removes_duplicate_and_ingests_new_intake(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    Duplicate cleanup does not prevent independent NEW intake from being
    processed normally.
    """

    monkeypatch.chdir(tmp_path)

    _create_existing_batch_artifact(
        tmp_path,
        "smith-cat",
        content=b"cat artwork",
    )

    duplicate = tmp_path / "smith-cat.png"
    new_source = tmp_path / "jones-dog.png"

    duplicate.write_bytes(b"cat artwork")
    new_source.write_bytes(b"dog artwork")

    result = _invoke(
        "--clean",
    )

    assert result.exit_code == 0

    assert not duplicate.exists()
    assert not new_source.exists()

    assert (tmp_path / "artifacts" / "jones-dog" / "artifact.png").read_bytes() == b"dog artwork"

    assert (tmp_path / "originals" / "jones-dog.png").read_bytes() == b"dog artwork"


def test_create_batch_clean_does_not_mutate_when_batch_contains_conflict(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    --clean does not remove even a verified duplicate when another intake item
    causes whole-batch preflight to fail.
    """

    monkeypatch.chdir(tmp_path)

    _create_existing_batch_artifact(
        tmp_path,
        "smith-cat",
        content=b"cat artwork",
    )

    _create_existing_batch_artifact(
        tmp_path,
        "lee-house",
        content=b"house artwork",
    )

    duplicate = tmp_path / "smith-cat.png"
    conflicting = tmp_path / "lee-house.png"

    duplicate.write_bytes(b"cat artwork")
    conflicting.write_bytes(b"different house artwork")

    result = _invoke(
        "--clean",
    )

    assert result.exit_code != 0

    # Preflight failure prevents duplicate cleanup.
    assert duplicate.read_bytes() == b"cat artwork"

    # Genuine conflicting input is never removed.
    assert conflicting.read_bytes() == b"different house artwork"


def test_create_clean_requires_bare_batch_intake(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    --clean belongs to bare batch intake and is not an explicit-create
    overwrite or cleanup operation.
    """

    source = tmp_path / "customer-final.png"
    source.write_bytes(b"artwork")

    monkeypatch.chdir(tmp_path)

    result = _invoke(
        "dog",
        "--source",
        "customer-final.png",
        "--clean",
    )

    assert result.exit_code != 0

    # Explicit caller-owned input remains untouched.
    assert source.read_bytes() == b"artwork"
    assert not (tmp_path / "artifacts" / "dog").exists()
