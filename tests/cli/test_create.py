"""
Tests for the artifact create command.

CREATE owns source ingestion into the project's preserved-original registry.
It does not materialize Artifact workspaces or realize Products.
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


def _preserve_original(
    project_root: Path,
    artifact_id: str,
    *,
    content: bytes,
) -> Path:
    """
    Establish one already-ingested Artifact source directly in originals/.
    """

    originals = project_root / "originals"
    originals.mkdir(
        parents=True,
        exist_ok=True,
    )

    original = originals / f"{artifact_id}.png"
    original.write_bytes(content)

    return original


# =========================================================
# Command
# =========================================================


def test_create_is_a_top_level_command() -> None:
    """
    Artifact source ingestion is exposed as a distinct lifecycle operation.
    """

    runner = CliRunner()

    result = runner.invoke(
        cli,
        ["--help"],
    )

    assert result.exit_code == 0
    assert "create" in result.output


def test_create_without_artifact_id_ingests_root_pngs_only(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    Bare create ingests the root-level PNG queue into originals/.

    Filename stems establish Artifact identities. CREATE consumes successfully
    ingested batch-owned sources but does not materialize Artifact workspaces.
    """

    dog = tmp_path / "smith-dog.png"
    cat = tmp_path / "jones-cat.PNG"

    dog.write_bytes(b"dog")
    cat.write_bytes(b"cat")

    notes = tmp_path / "notes.txt"
    notes.write_text("notes")

    nested = tmp_path / "incoming"
    nested.mkdir()

    nested_png = nested / "lee-house.png"
    nested_png.write_bytes(b"house")

    monkeypatch.chdir(tmp_path)

    result = _invoke()

    assert result.exit_code == 0

    assert not dog.exists()
    assert not cat.exists()

    assert (tmp_path / "originals" / "smith-dog.png").read_bytes() == b"dog"
    assert (tmp_path / "originals" / "jones-cat.png").read_bytes() == b"cat"

    assert notes.read_text() == "notes"
    assert nested_png.read_bytes() == b"house"

    assert not (tmp_path / "artifacts").exists()


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


def test_create_source_requires_explicit_artifact_id(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    --source belongs to explicitly named ingestion, not bare batch intake.
    """

    source = tmp_path / "dog.png"
    source.write_bytes(b"dog artwork")

    monkeypatch.chdir(tmp_path)

    result = _invoke(
        "--source",
        "dog.png",
    )

    assert result.exit_code != 0
    assert "--source" in result.output

    assert source.read_bytes() == b"dog artwork"
    assert not (tmp_path / "originals").exists()


def test_create_clean_requires_bare_batch_intake(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    --clean applies only to the bare root-level intake workflow.
    """

    source = tmp_path / "dog.png"
    source.write_bytes(b"dog artwork")

    monkeypatch.chdir(tmp_path)

    result = _invoke(
        "dog",
        "--source",
        "dog.png",
        "--clean",
    )

    assert result.exit_code != 0
    assert "--clean" in result.output

    assert source.read_bytes() == b"dog artwork"
    assert not (tmp_path / "originals").exists()


def test_create_does_not_expose_general_parameter_configuration() -> None:
    """
    CREATE accepts source artwork, not arbitrary Model configuration.

    Model defaults and Variant parameter assignments remain registered reusable
    configuration rather than CREATE command-line configuration.
    """

    result = _invoke(
        "--help",
    )

    assert result.exit_code == 0

    assert "--source" in result.output
    assert "--clean" in result.output
    assert "--param" not in result.output


# =========================================================
# Explicit ingestion
# =========================================================


def test_create_explicit_artifact_uses_artifact_id_for_preserved_original_only(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    Explicit ingestion establishes originals/<artifact_id>.png.

    The caller-owned source remains in place, and CREATE does not materialize
    an Artifact workspace.
    """

    monkeypatch.chdir(tmp_path)

    source = tmp_path / "dog.png"
    source.write_bytes(b"dog artwork")

    result = _invoke(
        "smith-dog",
        "--source",
        "dog.png",
    )

    assert result.exit_code == 0

    assert source.read_bytes() == b"dog artwork"

    assert (tmp_path / "originals" / "smith-dog.png").read_bytes() == b"dog artwork"

    assert not (tmp_path / "originals" / "dog.png").exists()

    assert not (tmp_path / "artifacts" / "smith-dog").exists()


def test_create_explicit_source_preserves_without_consuming_source(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    An explicitly supplied source is caller-owned and is copied, not consumed.
    """

    monkeypatch.chdir(tmp_path)

    source = tmp_path / "customer-final.png"
    source.write_bytes(b"customer artwork")

    result = _invoke(
        "dog",
        "--source",
        "customer-final.png",
    )

    assert result.exit_code == 0

    assert source.read_bytes() == b"customer artwork"

    assert (tmp_path / "originals" / "dog.png").read_bytes() == b"customer artwork"

    assert not (tmp_path / "originals" / "customer-final.png").exists()

    assert not (tmp_path / "artifacts" / "dog").exists()


def test_create_interactive_source_preserves_without_consuming_source(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    Interactive explicit source selection has the same ownership semantics as
    --source: the selected source remains caller-owned.
    """

    monkeypatch.chdir(tmp_path)

    source = tmp_path / "customer-final.png"
    source.write_bytes(b"customer artwork")

    result = _invoke(
        "dog",
        input="1\n",
    )

    assert result.exit_code == 0

    assert source.read_bytes() == b"customer artwork"

    assert (tmp_path / "originals" / "dog.png").read_bytes() == b"customer artwork"

    assert not (tmp_path / "originals" / "customer-final.png").exists()

    assert not (tmp_path / "artifacts" / "dog").exists()


def test_create_prompts_only_for_png_source(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    Interactive explicit ingestion asks only which root-level PNG to ingest.

    CREATE does not enter Model, Variant, or Artifact configuration.
    """

    monkeypatch.chdir(tmp_path)

    first = tmp_path / "alpha.png"
    second = tmp_path / "beta.PNG"
    ignored = tmp_path / "notes.txt"

    first.write_bytes(b"alpha artwork")
    second.write_bytes(b"beta artwork")
    ignored.write_text("notes")

    result = _invoke(
        "dog",
        input="2\n",
    )

    assert result.exit_code == 0

    assert "alpha.png" in result.output
    assert "beta.PNG" in result.output
    assert "notes.txt" not in result.output

    assert first.read_bytes() == b"alpha artwork"
    assert second.read_bytes() == b"beta artwork"

    assert (tmp_path / "originals" / "dog.png").read_bytes() == b"beta artwork"

    assert not (tmp_path / "artifacts" / "dog").exists()


def test_create_source_can_be_supplied_noninteractively(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    --source avoids interactive source selection and ingests that PNG directly.
    """

    monkeypatch.chdir(tmp_path)

    source = tmp_path / "skippy.png"
    source.write_bytes(b"artwork")

    result = _invoke(
        "dog",
        "--source",
        "skippy.png",
    )

    assert result.exit_code == 0

    assert "Available PNG sources" not in result.output

    assert source.read_bytes() == b"artwork"

    assert (tmp_path / "originals" / "dog.png").read_bytes() == b"artwork"

    assert not (tmp_path / "artifacts" / "dog").exists()


def test_create_rejects_missing_source_png(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    Explicit ingestion requires an existing PNG source.
    """

    monkeypatch.chdir(tmp_path)

    result = _invoke(
        "skippy",
        "--source",
        "missing.png",
    )

    assert result.exit_code != 0
    assert "png" in result.output.lower()

    assert not (tmp_path / "originals").exists()


def test_create_rejects_non_png_source(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    Explicit ingestion accepts PNG source artwork only.
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

    assert source.read_bytes() == b"artwork"
    assert not (tmp_path / "originals").exists()


def test_create_rejects_existing_artifact_identity(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    Explicit CREATE does not replace an already-ingested Artifact identity.
    """

    monkeypatch.chdir(tmp_path)

    existing_source = tmp_path / "existing.png"
    existing_source.write_bytes(b"existing artwork")

    first = _invoke(
        "skippy",
        "--source",
        "existing.png",
    )

    assert first.exit_code == 0

    original = tmp_path / "originals" / "skippy.png"

    assert original.read_bytes() == b"existing artwork"

    new_source = tmp_path / "new.png"
    new_source.write_bytes(b"new artwork")

    result = _invoke(
        "skippy",
        "--source",
        "new.png",
    )

    assert result.exit_code != 0
    assert "skippy" in result.output.lower()

    assert original.read_bytes() == b"existing artwork"
    assert new_source.read_bytes() == b"new artwork"

    assert not (tmp_path / "artifacts" / "skippy").exists()


def test_create_explicit_artifact_id_collision_is_case_insensitive(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    Explicit Artifact identity collisions are case-insensitive.
    """

    monkeypatch.chdir(tmp_path)

    original = _preserve_original(
        tmp_path,
        "dog",
        content=b"existing artwork",
    )

    source = tmp_path / "new.png"
    source.write_bytes(b"new artwork")

    result = _invoke(
        "DOG",
        "--source",
        "new.png",
    )

    assert result.exit_code != 0
    assert "dog" in result.output.lower()

    assert original.read_bytes() == b"existing artwork"
    assert source.read_bytes() == b"new artwork"

    assert not (tmp_path / "originals" / "DOG.png").exists()

    assert not (tmp_path / "artifacts").exists()


def test_create_explicit_artifacts_with_identical_content_remain_distinct(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    Explicit Artifact identity is authoritative.

    Equal source content does not collapse two explicitly named Artifacts into
    one identity.
    """

    monkeypatch.chdir(tmp_path)

    first_source = tmp_path / "first.png"
    second_source = tmp_path / "second.png"

    first_source.write_bytes(b"shared artwork")
    second_source.write_bytes(b"shared artwork")

    first = _invoke(
        "dog",
        "--source",
        "first.png",
    )
    second = _invoke(
        "smith-dog",
        "--source",
        "second.png",
    )

    assert first.exit_code == 0
    assert second.exit_code == 0

    assert (tmp_path / "originals" / "dog.png").read_bytes() == b"shared artwork"

    assert (tmp_path / "originals" / "smith-dog.png").read_bytes() == b"shared artwork"

    assert first_source.read_bytes() == b"shared artwork"
    assert second_source.read_bytes() == b"shared artwork"

    assert not (tmp_path / "artifacts").exists()


# =========================================================
# Bare batch intake
# =========================================================


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
    assert not (tmp_path / "originals").exists()
    assert not (tmp_path / "artifacts").exists()


def test_create_batch_recognizes_verified_duplicate_from_originals(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    Bare intake recognizes content already preserved for one ingested Artifact.

    Duplicate classification depends on originals/, not on materialized
    Artifact state.
    """

    monkeypatch.chdir(tmp_path)

    original = _preserve_original(
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
    assert original.read_bytes() == b"cat artwork"

    assert not (tmp_path / "artifacts").exists()


def test_create_batch_recognizes_duplicate_under_different_filename(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    A unique fingerprint match may identify an existing ingested Artifact even
    when the incoming filename proposes a different Artifact ID.
    """

    monkeypatch.chdir(tmp_path)

    original = _preserve_original(
        tmp_path,
        "smith-cat",
        content=b"cat artwork",
    )

    incoming = tmp_path / "customer-cat.png"
    incoming.write_bytes(b"cat artwork")

    result = _invoke(
        input="\n",
    )

    assert result.exit_code == 0
    assert "duplicate" in result.output.lower()
    assert "smith-cat" in result.output.lower()

    assert incoming.read_bytes() == b"cat artwork"
    assert original.read_bytes() == b"cat artwork"

    assert not (tmp_path / "originals" / "customer-cat.png").exists()

    assert not (tmp_path / "artifacts").exists()


def test_create_batch_duplicate_does_not_block_new_intake(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    A verified duplicate does not prevent independent NEW intake from being
    processed when duplicate cleanup is declined.
    """

    monkeypatch.chdir(tmp_path)

    _preserve_original(
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

    # Declining duplicate cleanup retains the verified duplicate.
    assert duplicate.read_bytes() == b"cat artwork"

    # Independent NEW intake is consumed into originals/.
    assert not new_source.exists()

    assert (tmp_path / "originals" / "jones-dog.png").read_bytes() == b"dog artwork"

    assert not (tmp_path / "artifacts").exists()


def test_create_batch_can_remove_verified_duplicate_interactively(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    Bare intake may remove a verified duplicate when explicitly approved.
    """

    monkeypatch.chdir(tmp_path)

    original = _preserve_original(
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

    assert "duplicate" in result.output.lower()
    assert "remove" in result.output.lower()

    assert not duplicate.exists()
    assert original.read_bytes() == b"cat artwork"

    assert not (tmp_path / "artifacts").exists()


def test_create_batch_clean_removes_duplicate_without_prompt(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    --clean removes a verified duplicate without interactive approval.
    """

    monkeypatch.chdir(tmp_path)

    original = _preserve_original(
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
    assert original.read_bytes() == b"cat artwork"

    assert not (tmp_path / "artifacts").exists()


def test_create_batch_clean_removes_duplicate_and_ingests_new_intake(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    Duplicate cleanup does not prevent independent NEW intake.
    """

    monkeypatch.chdir(tmp_path)

    _preserve_original(
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

    assert (tmp_path / "originals" / "smith-cat.png").read_bytes() == b"cat artwork"

    assert (tmp_path / "originals" / "jones-dog.png").read_bytes() == b"dog artwork"

    assert not (tmp_path / "artifacts").exists()


# =========================================================
# Registry conflicts and ambiguity
# =========================================================


def test_create_batch_rejects_conflicting_original_identity(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    Bare intake cannot replace an existing Artifact original with new content.
    """

    monkeypatch.chdir(tmp_path)

    original = _preserve_original(
        tmp_path,
        "smith-cat",
        content=b"existing artwork",
    )

    incoming = tmp_path / "smith-cat.png"
    incoming.write_bytes(b"different artwork")

    result = _invoke()

    assert result.exit_code != 0
    assert "smith-cat" in result.output.lower()

    assert original.read_bytes() == b"existing artwork"
    assert incoming.read_bytes() == b"different artwork"

    assert not (tmp_path / "artifacts").exists()


def test_create_batch_rejects_case_insensitive_original_identity_collision(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    Preserved Artifact identities collide case-insensitively.

    Different incoming content must not overwrite or establish another spelling
    of an already-ingested Artifact identity.
    """

    monkeypatch.chdir(tmp_path)

    original = _preserve_original(
        tmp_path,
        "smith-cat",
        content=b"existing artwork",
    )

    incoming = tmp_path / "SMITH-CAT.png"
    incoming.write_bytes(b"different artwork")

    result = _invoke()

    assert result.exit_code != 0
    assert "smith-cat" in result.output.lower()

    assert original.read_bytes() == b"existing artwork"
    assert incoming.read_bytes() == b"different artwork"

    assert not (tmp_path / "originals" / "SMITH-CAT.png").exists()

    assert not (tmp_path / "artifacts").exists()


def test_create_batch_rejects_case_insensitive_conflict_between_intake_ids(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    The root intake queue may not propose two Artifact IDs differing only by
    case.
    """

    monkeypatch.chdir(tmp_path)

    first = tmp_path / "dog.png"
    second = tmp_path / "DOG.PNG"

    first.write_bytes(b"first artwork")
    second.write_bytes(b"second artwork")

    result = _invoke()

    assert result.exit_code != 0
    assert "dog" in result.output.lower()

    # Complete preflight occurs before either source is consumed.
    assert first.read_bytes() == b"first artwork"
    assert second.read_bytes() == b"second artwork"

    assert not (tmp_path / "originals").exists()
    assert not (tmp_path / "artifacts").exists()


def test_create_batch_preflights_conflict_before_mutation(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    A predictable registry conflict aborts the complete intake batch before
    unrelated sources are mutated.
    """

    monkeypatch.chdir(tmp_path)

    original = _preserve_original(
        tmp_path,
        "smith-cat",
        content=b"existing cat",
    )

    new_source = tmp_path / "jones-dog.png"
    conflicting_source = tmp_path / "smith-cat.png"

    new_source.write_bytes(b"new dog")
    conflicting_source.write_bytes(b"different cat")

    result = _invoke()

    assert result.exit_code != 0
    assert "smith-cat" in result.output.lower()

    # jones-dog sorts first, so these assertions prove complete preflight.
    assert new_source.read_bytes() == b"new dog"
    assert conflicting_source.read_bytes() == b"different cat"

    assert original.read_bytes() == b"existing cat"

    assert not (tmp_path / "originals" / "jones-dog.png").exists()

    assert not (tmp_path / "artifacts").exists()


def test_create_batch_clean_does_not_mutate_when_batch_contains_conflict(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    --clean does not make predictable conflicts destructive.

    Even a verified duplicate remains untouched when another intake item makes
    the complete batch preflight fail.
    """

    monkeypatch.chdir(tmp_path)

    _preserve_original(
        tmp_path,
        "smith-cat",
        content=b"cat artwork",
    )
    original_dog = _preserve_original(
        tmp_path,
        "smith-dog",
        content=b"existing dog",
    )

    duplicate = tmp_path / "smith-cat.png"
    conflict = tmp_path / "smith-dog.png"

    duplicate.write_bytes(b"cat artwork")
    conflict.write_bytes(b"different dog")

    result = _invoke(
        "--clean",
    )

    assert result.exit_code != 0
    assert "smith-dog" in result.output.lower()

    # Cleanup occurs only after successful complete-batch preflight.
    assert duplicate.read_bytes() == b"cat artwork"
    assert conflict.read_bytes() == b"different dog"

    assert original_dog.read_bytes() == b"existing dog"

    assert not (tmp_path / "artifacts").exists()


def test_create_batch_retains_intake_matching_multiple_originals(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    Matching multiple preserved originals is ambiguous.

    Equal content does not collapse distinct Artifact identities, so bare
    intake cannot infer which existing Artifact owns the incoming PNG.
    """

    monkeypatch.chdir(tmp_path)

    _preserve_original(
        tmp_path,
        "dog",
        content=b"shared artwork",
    )
    _preserve_original(
        tmp_path,
        "smith-dog",
        content=b"shared artwork",
    )

    incoming = tmp_path / "customer-dog.png"
    incoming.write_bytes(b"shared artwork")

    result = _invoke(
        "--clean",
    )

    assert result.exit_code != 0

    assert "ambiguous" in result.output.lower()
    assert "dog" in result.output.lower()
    assert "smith-dog" in result.output.lower()

    # Ambiguous content is never consumed or cleaned.
    assert incoming.read_bytes() == b"shared artwork"

    # Existing Artifact identities remain independent and unchanged.
    assert (tmp_path / "originals" / "dog.png").read_bytes() == b"shared artwork"

    assert (tmp_path / "originals" / "smith-dog.png").read_bytes() == b"shared artwork"

    # No identity is inferred from ambiguous content.
    assert not (tmp_path / "originals" / "customer-dog.png").exists()

    assert not (tmp_path / "artifacts").exists()


def test_create_batch_same_identity_is_not_ambiguous_when_content_is_shared(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    Exact Artifact identity is stronger evidence than fingerprint inference.

    If an incoming filename names an existing Artifact and has the same bytes
    as that Artifact's original, it is that Artifact's duplicate even when
    another preserved Artifact happens to contain the same bytes.
    """

    monkeypatch.chdir(tmp_path)

    _preserve_original(
        tmp_path,
        "dog",
        content=b"shared artwork",
    )
    _preserve_original(
        tmp_path,
        "smith-dog",
        content=b"shared artwork",
    )

    incoming = tmp_path / "dog.png"
    incoming.write_bytes(b"shared artwork")

    result = _invoke(
        input="\n",
    )

    assert result.exit_code == 0
    assert "duplicate" in result.output.lower()
    assert "dog" in result.output.lower()

    # Declining cleanup retains the duplicate intake item.
    assert incoming.read_bytes() == b"shared artwork"

    assert not (tmp_path / "artifacts").exists()


def test_create_batch_rejects_case_insensitive_conflict_inside_originals_registry(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    originals/ itself may not define two Artifact identities differing only by
    case.
    """

    monkeypatch.chdir(tmp_path)

    originals = tmp_path / "originals"
    originals.mkdir()

    lower = originals / "dog.png"
    upper = originals / "DOG.PNG"

    lower.write_bytes(b"lower artwork")
    upper.write_bytes(b"upper artwork")

    incoming = tmp_path / "cat.png"
    incoming.write_bytes(b"cat artwork")

    result = _invoke()

    assert result.exit_code != 0
    assert "dog" in result.output.lower()

    assert lower.read_bytes() == b"lower artwork"
    assert upper.read_bytes() == b"upper artwork"
    assert incoming.read_bytes() == b"cat artwork"

    assert not (originals / "cat.png").exists()

    assert not (tmp_path / "artifacts").exists()


# =========================================================
# Failure safety
# =========================================================


def test_create_batch_preserves_intake_source_when_original_preservation_fails(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    A runtime failure while preserving an original must not destroy the
    batch-owned intake PNG.
    """

    source = tmp_path / "dog.png"
    content = b"dog artwork"

    source.write_bytes(content)

    monkeypatch.chdir(tmp_path)

    def fail_move(
        src: Path,
        dst: Path,
    ) -> None:
        raise OSError("simulated preservation failure")

    monkeypatch.setattr(
        cmd_create.shutil,
        "move",
        fail_move,
    )

    result = _invoke()

    assert result.exit_code != 0
    assert "dog.png" in result.output
    assert "simulated preservation failure" in result.output

    # The only known input copy remains available.
    assert source.read_bytes() == content

    assert not (tmp_path / "originals" / "dog.png").exists()

    assert not (tmp_path / "artifacts").exists()
