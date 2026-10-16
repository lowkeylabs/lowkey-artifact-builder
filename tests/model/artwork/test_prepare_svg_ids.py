"""Regression tests for deterministic native SVG path IDs during Prepare."""
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from lowkey_artifact_builder.model.models.artwork.stages import prepare

SVG_NS = "http://www.w3.org/2000/svg"
FAN_SHELL = Path(__file__).resolve().parents[2] / "assets" / "fan-shell.svg"


def _prepare(
    source: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    name: str = "trace.svg",
) -> Path:
    """Run native SVG preparation, isolating ID behavior from Inkscape rendering."""
    trace = tmp_path / name
    envelope = tmp_path / f"{name}.envelope.svg"

    def fake_envelope(source_path: Path, output: Path, *, mode: str) -> None:
        assert source_path == source
        assert mode == "alpha"
        output.write_text('<svg xmlns="http://www.w3.org/2000/svg"/>', encoding="utf-8")

    monkeypatch.setattr(prepare, "_derive_svg_envelope", fake_envelope)
    prepare._prepare_svg_source(source, trace, envelope, envelope_mode="alpha")
    assert envelope.is_file()
    return trace


def _paths(svg: Path) -> list[ET.Element]:
    return list(ET.parse(svg).getroot().iter(f"{{{SVG_NS}}}path"))


def test_fan_shell_assigns_unique_ids_to_all_unnamed_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The real fan fixture has eleven unnamed spines, all requiring IDs."""
    assert FAN_SHELL.is_file()
    source_paths = _paths(FAN_SHELL)
    assert len(source_paths) == 11
    assert all(path.get("id") is None for path in source_paths)

    trace = _prepare(FAN_SHELL, tmp_path, monkeypatch)
    output_paths = _paths(trace)
    ids = [path.get("id") for path in output_paths]

    assert len(ids) == 11
    assert all(ids)
    assert len(set(ids)) == 11
    assert [path.get("d") for path in output_paths] == [path.get("d") for path in source_paths]
    assert [path.get("fill") for path in output_paths] == [
        path.get("fill") for path in source_paths
    ]
    # The unrelated circle remains unchanged; primitive conversion is out of scope.
    original_circle = ET.parse(FAN_SHELL).getroot().find(f".//{{{SVG_NS}}}circle")
    trace_circle = ET.parse(trace).getroot().find(f".//{{{SVG_NS}}}circle")
    assert original_circle is not None and trace_circle is not None
    assert trace_circle.attrib == original_circle.attrib


def test_fan_shell_generated_ids_are_repeatable_and_source_is_unchanged(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Reprocessing the same native SVG produces deterministic, unique,
    nonempty path IDs without modifying the authored source.
    """

    before = FAN_SHELL.read_bytes()

    source_paths = _paths(FAN_SHELL)

    assert len(source_paths) == 11
    assert all(path.get("id") is None for path in source_paths)

    first = _prepare(
        FAN_SHELL,
        tmp_path,
        monkeypatch,
        name="first.svg",
    )

    second = _prepare(
        FAN_SHELL,
        tmp_path,
        monkeypatch,
        name="second.svg",
    )

    first_ids = [path.get("id") for path in _paths(first)]

    second_ids = [path.get("id") for path in _paths(second)]

    assert len(first_ids) == 11
    assert len(second_ids) == 11

    # Missing IDs must actually be generated.
    assert all(first_ids)
    assert all(second_ids)

    # Every path must have a distinct identity.
    assert len(set(first_ids)) == 11
    assert len(set(second_ids)) == 11

    # Repeated preparation must assign the same identities.
    assert first_ids == second_ids

    # Normalization must never modify the original source.
    assert FAN_SHELL.read_bytes() == before


def test_authored_ids_survive_and_generated_ids_avoid_collisions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Preserve authored IDs and assign unique IDs to unnamed paths,
    avoiding collisions with IDs on any SVG element.
    """

    source = tmp_path / "mixed.svg"

    source.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 30 30">'
        '<g id="path-001">'
        '<path id="authored" d="M 0 0 H 10 V 10 Z"/>'
        '<path d="M 10 0 H 20 V 10 Z"/>'
        '<path id="path-002" d="M 20 0 H 30 V 10 Z"/>'
        '<path d="M 0 10 H 10 V 20 Z"/>'
        "</g></svg>",
        encoding="utf-8",
    )

    before = source.read_bytes()

    trace = _prepare(
        source,
        tmp_path,
        monkeypatch,
    )

    source_root = ET.parse(source).getroot()
    trace_root = ET.parse(trace).getroot()

    source_paths = list(source_root.iter(f"{{{SVG_NS}}}path"))

    paths = list(trace_root.iter(f"{{{SVG_NS}}}path"))

    assert len(paths) == 4

    path_ids = [path.get("id") for path in paths]

    # Every path, including previously unnamed paths, must have an ID.
    assert all(path_ids)
    assert len(set(path_ids)) == 4

    # Existing authored IDs must remain unchanged.
    assert paths[0].get("id") == "authored"
    assert paths[2].get("id") == "path-002"

    # Existing group IDs must also remain unchanged.
    group = trace_root.find(f".//{{{SVG_NS}}}g")

    assert group is not None
    assert group.get("id") == "path-001"

    # Generated IDs must be present and distinct.
    generated_ids = [
        paths[1].get("id"),
        paths[3].get("id"),
    ]

    assert all(generated_ids)
    assert len(set(generated_ids)) == 2

    reserved_ids = {
        "path-001",
        "path-002",
        "authored",
    }

    assert all(generated_id not in reserved_ids for generated_id in generated_ids)

    # IDs must be globally unique across all SVG elements.
    all_ids = [element.get("id") for element in trace_root.iter() if element.get("id") is not None]

    assert len(all_ids) == 5
    assert len(set(all_ids)) == len(all_ids)

    # ID normalization must not alter authored path geometry.
    assert [path.get("d") for path in paths] == [path.get("d") for path in source_paths]

    # The source remains byte-for-byte unchanged.
    assert source.read_bytes() == before


def test_duplicate_authored_ids_are_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "duplicates.svg"
    source.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20">'
        '<path id="duplicate" d="M 0 0 H 10 V 10 Z"/>'
        '<path id="duplicate" d="M 10 0 H 20 V 10 Z"/>'
        "</svg>",
        encoding="utf-8",
    )
    with pytest.raises(
        prepare.PrepareError, match=r"(?i)(duplicate|unique).*id|id.*(duplicate|unique)"
    ):
        _prepare(source, tmp_path, monkeypatch)
