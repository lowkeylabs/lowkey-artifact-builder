"""
Tests for the Artwork package stage.

The package stage consumes dimensionalized Artwork components through the
extrusion manifest and packages them through the shared 3MF component
representation.

Filesystem layout remains a build-engine responsibility. Component membership,
semantic color identity, and RGB metadata are established upstream and must be
preserved by packaging.
"""
# File: tests/model/artwork/test_package.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from lowkey_artifact_builder.colors import PaletteColor
from lowkey_artifact_builder.formats.threemf import Component, Mesh
from lowkey_artifact_builder.model.models.artwork.stages import package

# =========================================================
# Test support
# =========================================================


class StubContext:
    """
    Minimal StageContext-compatible object for package-stage tests.
    """

    def __init__(
        self,
        *,
        artifact_id: str,
        inputs: dict[str, Path],
        outputs: dict[str, Path],
    ) -> None:
        self.artifact_id = artifact_id
        self._inputs = inputs
        self._outputs = outputs

    def input(
        self,
        name: str,
    ) -> Path:
        return self._inputs[name]

    def output(
        self,
        name: str,
    ) -> Path:
        return self._outputs[name]


def _write_extrude_manifest(
    path: Path,
    products: list[dict[str, Any]],
) -> None:
    """
    Write a minimal Artwork extrusion manifest.
    """

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        json.dumps(
            {
                "products": products,
            }
        ),
        encoding="utf-8",
    )


def _color(
    red: int,
    green: int,
    blue: int,
) -> dict[str, int]:
    """
    Return Artwork extrusion-manifest RGB metadata.
    """

    return {
        "red": red,
        "green": green,
        "blue": blue,
    }


def _mesh() -> Mesh:
    """
    Return a minimal valid mesh for package-stage tests.
    """

    return Mesh(
        vertices=(
            (0.0, 0.0, 0.0),
            (1.0, 0.0, 0.0),
            (0.0, 1.0, 0.0),
        ),
        triangles=((0, 1, 2),),
    )


# =========================================================
# Packaging-contract tests
# =========================================================


def test_package_uses_declared_artifact_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Artwork packaging writes only to the output supplied by StageContext.
    """

    extrude_directory = tmp_path / "somewhere" / "extrusion"

    stl = extrude_directory / "color-1.stl"

    stl.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    stl.write_text(
        "component",
        encoding="utf-8",
    )

    manifest = extrude_directory / "products.json"

    _write_extrude_manifest(
        manifest,
        [
            {
                "index": 1,
                "path": stl.name,
                "name": "white",
                "color": _color(
                    255,
                    255,
                    255,
                ),
            },
        ],
    )

    artifact = tmp_path / "deliberately" / "unrelated" / "output" / "location" / "finished.3mf"

    context = StubContext(
        artifact_id="example",
        inputs={
            "extrude.manifest": manifest,
        },
        outputs={
            "artifact": artifact,
        },
    )

    monkeypatch.setattr(
        package,
        "load_stl",
        lambda path: _mesh(),
        raising=False,
    )

    received_output: Path | None = None

    def fake_write(
        components,
        output: Path,
    ) -> None:
        nonlocal received_output

        received_output = output

        output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        output.write_bytes(b"3mf")

    monkeypatch.setattr(
        package,
        "write",
        fake_write,
        raising=False,
    )

    package.execute(context)  # type: ignore[arg-type]

    assert received_output == artifact
    assert artifact.is_file()


def test_package_resolves_dynamic_stls_relative_to_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Artwork component paths are resolved relative to their manifest.
    """

    manifest_directory = tmp_path / "dynamic-products"

    first_stl = manifest_directory / "color-1.stl"
    second_stl = manifest_directory / "color-2.stl"

    manifest_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    first_stl.write_text(
        "first",
        encoding="utf-8",
    )

    second_stl.write_text(
        "second",
        encoding="utf-8",
    )

    manifest = manifest_directory / "manifest.json"

    _write_extrude_manifest(
        manifest,
        [
            {
                "index": 2,
                "path": second_stl.name,
                "name": "green",
                "color": _color(
                    0,
                    255,
                    0,
                ),
            },
            {
                "index": 1,
                "path": first_stl.name,
                "name": "white",
                "color": _color(
                    255,
                    255,
                    255,
                ),
            },
        ],
    )

    artifact = tmp_path / "other-place" / "artifact.3mf"

    context = StubContext(
        artifact_id="portrait",
        inputs={
            "extrude.manifest": manifest,
        },
        outputs={
            "artifact": artifact,
        },
    )

    loaded_paths: list[Path] = []

    def fake_load_stl(
        path: Path,
    ) -> Mesh:
        loaded_paths.append(path)
        return _mesh()

    monkeypatch.setattr(
        package,
        "load_stl",
        fake_load_stl,
        raising=False,
    )

    def fake_write(
        components,
        output: Path,
    ) -> None:
        output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        output.write_bytes(b"3mf")

    monkeypatch.setattr(
        package,
        "write",
        fake_write,
        raising=False,
    )

    package.execute(context)  # type: ignore[arg-type]

    assert loaded_paths == [
        first_stl,
        second_stl,
    ]


def test_package_preserves_semantic_color_metadata(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Artwork packaging preserves semantic color identity and RGB metadata.

    The extrusion manifest is authoritative for Artwork component colors.
    Packaging transfers that metadata into the shared 3MF component contract
    rather than discarding it or re-resolving model color policy.
    """

    extrude_directory = tmp_path / "extrude"

    white_stl = extrude_directory / "color-1.stl"
    red_stl = extrude_directory / "color-2.stl"

    extrude_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    white_stl.write_text(
        "white",
        encoding="utf-8",
    )

    red_stl.write_text(
        "red",
        encoding="utf-8",
    )

    manifest = extrude_directory / "products.json"

    _write_extrude_manifest(
        manifest,
        [
            {
                "index": 1,
                "path": white_stl.name,
                "name": "white",
                "color": _color(
                    255,
                    255,
                    255,
                ),
            },
            {
                "index": 2,
                "path": red_stl.name,
                "name": "red",
                "color": _color(
                    220,
                    38,
                    38,
                ),
            },
        ],
    )

    artifact = tmp_path / "artifact.3mf"

    context = StubContext(
        artifact_id="portrait",
        inputs={
            "extrude.manifest": manifest,
        },
        outputs={
            "artifact": artifact,
        },
    )

    monkeypatch.setattr(
        package,
        "load_stl",
        lambda path: _mesh(),
        raising=False,
    )

    captured_components: tuple[Component, ...] | None = None

    def fake_write(
        components,
        output: Path,
    ) -> None:
        nonlocal captured_components

        captured_components = tuple(components)

        output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        output.write_bytes(b"3mf")

    monkeypatch.setattr(
        package,
        "write",
        fake_write,
        raising=False,
    )

    package.execute(context)  # type: ignore[arg-type]

    assert captured_components is not None

    assert tuple(component.name for component in captured_components) == (
        "portrait-white",
        "portrait-red",
    )

    assert tuple(component.color for component in captured_components) == (
        PaletteColor(
            name="white",
            rgb=(
                255,
                255,
                255,
            ),
        ),
        PaletteColor(
            name="red",
            rgb=(
                220,
                38,
                38,
            ),
        ),
    )


def test_package_does_not_require_canonical_artifact_directories(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Artwork packaging remains independent of workspace filesystem policy.
    """

    manifest_directory = tmp_path / "input"

    stl = manifest_directory / "component.stl"

    manifest_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    stl.write_text(
        "component",
        encoding="utf-8",
    )

    manifest = manifest_directory / "manifest.json"

    _write_extrude_manifest(
        manifest,
        [
            {
                "index": 1,
                "path": stl.name,
                "name": "gold",
                "color": _color(
                    255,
                    215,
                    0,
                ),
            },
        ],
    )

    artifact = tmp_path / "result" / "whatever-name-we-want.bin"

    context = StubContext(
        artifact_id="not-a-directory-name",
        inputs={
            "extrude.manifest": manifest,
        },
        outputs={
            "artifact": artifact,
        },
    )

    monkeypatch.setattr(
        package,
        "load_stl",
        lambda path: _mesh(),
        raising=False,
    )

    def fake_write(
        components,
        output: Path,
    ) -> None:
        output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        output.write_bytes(b"3mf")

    monkeypatch.setattr(
        package,
        "write",
        fake_write,
        raising=False,
    )

    package.execute(context)  # type: ignore[arg-type]

    assert artifact.is_file()
