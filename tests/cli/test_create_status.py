"""
Tests for the artifact create operator surface.

Bare CREATE is a read-only intake overview that helps the operator decide
what source artwork should be ingested next.

Mutating CREATE forms explicitly register one source-less Artifact, ingest
one selected PNG, or ingest all eligible root-level PNGs. Source ingestion
consumes intake material into the authoritative originals/ registry.

CREATE registers Artifact identity and source material. It does not
materialize Artifact workspaces or realize Products.
"""

# File: tests/cli/test_create_status.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path
from typing import Any

from click.testing import CliRunner

import lowkey_artifact_builder.cli.cmd_create as cmd_create
from lowkey_artifact_builder.cli._main import cli

# =========================================================
# Helpers
# =========================================================


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
    Establish one already-ingested source-backed Artifact.
    """

    originals = project_root / "originals"
    originals.mkdir(
        parents=True,
        exist_ok=True,
    )

    original = originals / f"{artifact_id}.png"
    original.write_bytes(content)

    return original


def _register_sourceless_artifact(
    project_root: Path,
    artifact_id: str,
) -> Path:
    """
    Establish one already-registered source-less Artifact.
    """

    originals = project_root / "originals"
    originals.mkdir(
        parents=True,
        exist_ok=True,
    )

    marker = originals / f"{artifact_id}.artifact"
    marker.write_bytes(b"")

    return marker


# =========================================================
# Bare create
# =========================================================


def test_bare_create_shows_existing_artifacts_without_ingesting(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    Bare create is a read-only intake overview.

    An operator preparing to ingest new artwork is reminded of already
    registered Artifact identities without the command consuming incoming
    source material.
    """

    monkeypatch.chdir(tmp_path)

    incoming = tmp_path / "new-dog.png"
    incoming.write_bytes(b"new artwork")

    _preserve_original(
        tmp_path,
        "smith-cat",
        content=b"existing artwork",
    )

    result = _invoke()

    assert result.exit_code == 0

    assert "smith-cat" in result.output
    assert "new-dog.png" in result.output

    # Bare CREATE is situational awareness only.
    assert incoming.read_bytes() == b"new artwork"
    assert not (tmp_path / "originals" / "new-dog.png").exists()

    # Existing managed state is unchanged.
    assert (tmp_path / "originals" / "smith-cat.png").read_bytes() == b"existing artwork"


def test_bare_create_discovers_existing_artifacts_from_project_root(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    Bare create uses the shared Artifact discovery API.

    CREATE and LIST therefore share the same definition of an existing
    Artifact rather than independently inspecting persistent project state.
    """

    roots: list[Path] = []

    monkeypatch.chdir(tmp_path)

    def discover(
        *,
        project_root: Path,
    ) -> tuple[str, ...]:
        roots.append(project_root)

        return (
            "smith-cat",
            "jones-dog",
        )

    monkeypatch.setattr(
        cmd_create,
        "list_artifacts",
        discover,
    )

    result = _invoke()

    assert result.exit_code == 0

    assert roots == [tmp_path]

    assert "smith-cat" in result.output
    assert "jones-dog" in result.output


def test_bare_create_discovers_incoming_pngs_without_mutating_them(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    Bare create presents the root-level PNG intake queue without consuming it.

    Only root-level PNG files participate in source intake discovery.
    """

    monkeypatch.chdir(tmp_path)

    dog = tmp_path / "smith-dog.png"
    cat = tmp_path / "jones-cat.PNG"
    notes = tmp_path / "notes.txt"

    dog.write_bytes(b"dog artwork")
    cat.write_bytes(b"cat artwork")
    notes.write_text("notes")

    nested = tmp_path / "incoming"
    nested.mkdir()

    nested_png = nested / "lee-house.png"
    nested_png.write_bytes(b"house artwork")

    result = _invoke()

    assert result.exit_code == 0

    assert "smith-dog.png" in result.output
    assert "jones-cat.PNG" in result.output

    assert "notes.txt" not in result.output
    assert "lee-house.png" not in result.output

    # Bare CREATE is read-only.
    assert dog.read_bytes() == b"dog artwork"
    assert cat.read_bytes() == b"cat artwork"
    assert notes.read_text() == "notes"
    assert nested_png.read_bytes() == b"house artwork"

    assert not (tmp_path / "originals").exists()
    assert not (tmp_path / "artifacts").exists()


# =========================================================
# Public create surface
# =========================================================


def test_create_help_exposes_explicit_creation_surface() -> None:
    """
    CREATE exposes explicit, script-friendly creation controls.

    Artifact identity and source selection are named options. Historical
    import terminology is not part of the intended interface.
    """

    result = _invoke(
        "--help",
    )

    assert result.exit_code == 0

    assert "--artifact-id" in result.output
    assert "--source" in result.output
    assert "--all-sources" in result.output

    assert "--import" not in result.output
    assert "--import-all" not in result.output


def test_create_rejects_positional_artifact_id(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    Artifact identity is supplied with --artifact-id rather than positionally.
    """

    monkeypatch.chdir(tmp_path)

    result = _invoke(
        "dog",
    )

    assert result.exit_code != 0

    assert not (tmp_path / "originals").exists()
    assert not (tmp_path / "artifacts").exists()


# =========================================================
# Source-less creation
# =========================================================


def test_create_artifact_id_registers_sourceless_artifact(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    --artifact-id registers an Artifact without requiring source artwork.

    A source-less Artifact is represented by a zero-content .artifact marker
    in the authoritative originals registry. CREATE does not materialize an
    Artifact workspace.
    """

    monkeypatch.chdir(tmp_path)

    result = _invoke(
        "--artifact-id=dog",
    )

    assert result.exit_code == 0

    marker = tmp_path / "originals" / "dog.artifact"

    assert marker.is_file()
    assert marker.read_bytes() == b""

    assert not (tmp_path / "originals" / "dog.png").exists()
    assert not (tmp_path / "artifacts").exists()


def test_create_artifact_id_is_noninteractive(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    Explicit source-less creation is deterministic and noninteractive.

    Optional artwork is not requested when --artifact-id completely
    describes the requested creation operation.
    """

    monkeypatch.chdir(tmp_path)

    result = _invoke(
        "--artifact-id=dog",
    )

    assert result.exit_code == 0

    assert (tmp_path / "originals" / "dog.artifact").is_file()

    assert "available png" not in result.output.lower()
    assert "source:" not in result.output.lower()


# =========================================================
# Single-source creation
# =========================================================


def test_create_source_derives_artifact_id_from_source_stem(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    --source creates one source-backed Artifact.

    When --artifact-id is omitted, the source filename stem determines the
    Artifact identity. Successfully ingested intake artwork is consumed into
    the authoritative originals registry.
    """

    monkeypatch.chdir(tmp_path)

    source = tmp_path / "smith-dog.png"
    source.write_bytes(b"dog artwork")

    result = _invoke(
        "--source=smith-dog.png",
    )

    assert result.exit_code == 0

    assert (tmp_path / "originals" / "smith-dog.png").read_bytes() == b"dog artwork"

    assert not source.exists()

    assert not (tmp_path / "originals" / "smith-dog.artifact").exists()

    assert not (tmp_path / "artifacts").exists()


def test_create_artifact_id_overrides_source_stem(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    --artifact-id explicitly determines Artifact identity when --source is
    also supplied.

    The selected source is consumed into originals/ under the explicitly
    assigned Artifact identity.
    """

    monkeypatch.chdir(tmp_path)

    source = tmp_path / "dog.png"
    source.write_bytes(b"dog artwork")

    result = _invoke(
        "--artifact-id=skippy",
        "--source=dog.png",
    )

    assert result.exit_code == 0

    assert (tmp_path / "originals" / "skippy.png").read_bytes() == b"dog artwork"

    assert not source.exists()

    assert not (tmp_path / "originals" / "dog.png").exists()
    assert not (tmp_path / "originals" / "skippy.artifact").exists()

    assert not (tmp_path / "artifacts").exists()


def test_create_source_is_noninteractive(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    --source completely specifies singleton source selection.

    Other available PNGs do not cause CREATE to ask the operator to select
    artwork. The selected intake source is consumed while unrelated intake
    sources remain untouched.
    """

    monkeypatch.chdir(tmp_path)

    dog = tmp_path / "dog.png"
    cat = tmp_path / "cat.png"

    dog.write_bytes(b"dog artwork")
    cat.write_bytes(b"cat artwork")

    result = _invoke(
        "--source=dog.png",
    )

    assert result.exit_code == 0

    assert (tmp_path / "originals" / "dog.png").read_bytes() == b"dog artwork"

    assert not dog.exists()

    assert cat.read_bytes() == b"cat artwork"

    assert "available png" not in result.output.lower()
    assert "source:" not in result.output.lower()


def test_create_source_rejects_missing_png_without_mutation(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    --source requires an existing PNG.
    """

    monkeypatch.chdir(tmp_path)

    result = _invoke(
        "--source=missing.png",
    )

    assert result.exit_code != 0
    assert "png" in result.output.lower()

    assert not (tmp_path / "originals").exists()
    assert not (tmp_path / "artifacts").exists()


def test_create_source_rejects_non_png_without_mutation(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    --source accepts PNG source artwork only.
    """

    monkeypatch.chdir(tmp_path)

    source = tmp_path / "dog.jpg"
    source.write_bytes(b"dog artwork")

    result = _invoke(
        "--source=dog.jpg",
    )

    assert result.exit_code != 0
    assert "png" in result.output.lower()

    assert source.read_bytes() == b"dog artwork"
    assert not (tmp_path / "originals").exists()
    assert not (tmp_path / "artifacts").exists()


# =========================================================
# All-source creation
# =========================================================


def test_create_all_sources_registers_each_root_png(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    --all-sources registers every eligible root-level PNG.

    Artifact identities derive from source filename stems. Successfully
    ingested intake artwork is consumed into originals/. Non-PNG and nested
    files do not participate.
    """

    monkeypatch.chdir(tmp_path)

    dog = tmp_path / "smith-dog.png"
    cat = tmp_path / "jones-cat.PNG"
    notes = tmp_path / "notes.txt"

    dog.write_bytes(b"dog artwork")
    cat.write_bytes(b"cat artwork")
    notes.write_text("notes")

    nested = tmp_path / "incoming"
    nested.mkdir()

    nested_png = nested / "lee-house.png"
    nested_png.write_bytes(b"house artwork")

    result = _invoke(
        "--all-sources",
    )

    assert result.exit_code == 0

    assert (tmp_path / "originals" / "smith-dog.png").read_bytes() == b"dog artwork"

    assert (tmp_path / "originals" / "jones-cat.png").read_bytes() == b"cat artwork"

    assert not dog.exists()
    assert not cat.exists()

    assert not (tmp_path / "originals" / "lee-house.png").exists()

    assert notes.read_text() == "notes"
    assert nested_png.read_bytes() == b"house artwork"

    assert not (tmp_path / "artifacts").exists()


def test_create_all_sources_with_empty_intake_succeeds(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    --all-sources against an empty intake queue is a successful no-op.
    """

    monkeypatch.chdir(tmp_path)

    result = _invoke(
        "--all-sources",
    )

    assert result.exit_code == 0

    assert not (tmp_path / "originals").exists()
    assert not (tmp_path / "artifacts").exists()


def test_create_all_sources_is_noninteractive(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    --all-sources is deterministic and suitable for scripting and Make.
    """

    monkeypatch.chdir(tmp_path)

    dog = tmp_path / "dog.png"
    cat = tmp_path / "cat.png"

    dog.write_bytes(b"dog artwork")
    cat.write_bytes(b"cat artwork")

    result = _invoke(
        "--all-sources",
    )

    assert result.exit_code == 0

    assert (tmp_path / "originals" / "dog.png").read_bytes() == b"dog artwork"

    assert (tmp_path / "originals" / "cat.png").read_bytes() == b"cat artwork"

    assert not dog.exists()
    assert not cat.exists()

    assert "remove the duplicate" not in result.output.lower()
    assert "source:" not in result.output.lower()


# =========================================================
# Option compatibility
# =========================================================


def test_create_all_sources_rejects_source_without_mutation(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    --all-sources and --source are mutually exclusive source scopes.
    """

    monkeypatch.chdir(tmp_path)

    source = tmp_path / "dog.png"
    source.write_bytes(b"dog artwork")

    result = _invoke(
        "--all-sources",
        "--source=dog.png",
    )

    assert result.exit_code != 0

    assert source.read_bytes() == b"dog artwork"
    assert not (tmp_path / "originals").exists()
    assert not (tmp_path / "artifacts").exists()


def test_create_all_sources_rejects_artifact_id_without_mutation(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    --all-sources cannot be combined with one explicit Artifact identity.
    """

    monkeypatch.chdir(tmp_path)

    source = tmp_path / "dog.png"
    source.write_bytes(b"dog artwork")

    result = _invoke(
        "--all-sources",
        "--artifact-id=skippy",
    )

    assert result.exit_code != 0

    assert source.read_bytes() == b"dog artwork"
    assert not (tmp_path / "originals").exists()
    assert not (tmp_path / "artifacts").exists()


# =========================================================
# Artifact identity
# =========================================================


def test_create_artifact_id_rejects_existing_sourceless_artifact(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    A source-less registration reserves its Artifact identity.
    """

    monkeypatch.chdir(tmp_path)

    marker = _register_sourceless_artifact(
        tmp_path,
        "dog",
    )

    result = _invoke(
        "--artifact-id=dog",
    )

    assert result.exit_code != 0

    assert marker.read_bytes() == b""
    assert not (tmp_path / "artifacts").exists()


def test_create_artifact_id_rejects_existing_source_backed_artifact(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    A preserved source and a source-less marker participate in the same
    Artifact identity namespace.
    """

    monkeypatch.chdir(tmp_path)

    original = _preserve_original(
        tmp_path,
        "dog",
        content=b"existing artwork",
    )

    result = _invoke(
        "--artifact-id=dog",
    )

    assert result.exit_code != 0

    assert original.read_bytes() == b"existing artwork"

    assert not (tmp_path / "originals" / "dog.artifact").exists()
    assert not (tmp_path / "artifacts").exists()


def test_create_source_rejects_existing_sourceless_artifact_identity(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    Source-backed creation cannot silently replace an existing source-less
    Artifact registration.
    """

    monkeypatch.chdir(tmp_path)

    marker = _register_sourceless_artifact(
        tmp_path,
        "dog",
    )

    source = tmp_path / "dog.png"
    source.write_bytes(b"new artwork")

    result = _invoke(
        "--source=dog.png",
    )

    assert result.exit_code != 0

    assert marker.read_bytes() == b""
    assert source.read_bytes() == b"new artwork"

    assert not (tmp_path / "originals" / "dog.png").exists()
    assert not (tmp_path / "artifacts").exists()


def test_create_identity_collisions_are_case_insensitive(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """
    Artifact identity remains case-insensitive across registration forms.
    """

    monkeypatch.chdir(tmp_path)

    marker = _register_sourceless_artifact(
        tmp_path,
        "Dog",
    )

    source = tmp_path / "dog.png"
    source.write_bytes(b"new artwork")

    result = _invoke(
        "--source=dog.png",
    )

    assert result.exit_code != 0

    assert marker.read_bytes() == b""
    assert source.read_bytes() == b"new artwork"

    assert not (tmp_path / "originals" / "dog.png").exists()
    assert not (tmp_path / "artifacts").exists()
