"""
Tests for the Artwork package stage.

The package stage consumes dimensionalized Artwork components through the
extrusion manifest and packages them through the shared 3MF component
representation.

Filesystem layout remains a build-engine responsibility. Artifact color
information and physical printer assignments are established upstream.
Packaging must use the printer assignment for the physical 3MF component
while preserving the distinction between Artifact and printer color
semantics at its input boundary.
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
    Return extrusion-manifest RGB metadata.
    """

    return {
        "red": red,
        "green": green,
        "blue": blue,
    }


def _product(
    *,
    index: int,
    path: str,
    artifact_color_index: int,
    artifact_rgb: tuple[int, int, int],
    printer_color_name: str,
    printer_rgb: tuple[int, int, int],
    distance: float,
) -> dict[str, Any]:
    """
    Return one dimensionalized Artwork product.

    Artifact color describes the color discovered from the Artwork.
    Printer color describes the physical assignment used for packaging.
    """

    return {
        "index": index,
        "path": path,
        "artifact_color": {
            "index": artifact_color_index,
            "rgb": _color(
                *artifact_rgb,
            ),
        },
        "printer_color": {
            "name": printer_color_name,
            "rgb": _color(
                *printer_rgb,
            ),
        },
        "distance": distance,
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
            _product(
                index=1,
                path=stl.name,
                artifact_color_index=1,
                artifact_rgb=(
                    250,
                    250,
                    250,
                ),
                printer_color_name="white",
                printer_rgb=(
                    255,
                    255,
                    255,
                ),
                distance=1.25,
            ),
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
            _product(
                index=2,
                path=second_stl.name,
                artifact_color_index=2,
                artifact_rgb=(
                    8,
                    245,
                    14,
                ),
                printer_color_name="green",
                printer_rgb=(
                    0,
                    255,
                    0,
                ),
                distance=2.5,
            ),
            _product(
                index=1,
                path=first_stl.name,
                artifact_color_index=1,
                artifact_rgb=(
                    250,
                    250,
                    250,
                ),
                printer_color_name="white",
                printer_rgb=(
                    255,
                    255,
                    255,
                ),
                distance=1.25,
            ),
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


def test_package_uses_printer_assignment_for_component_metadata(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Packaging uses the physical printer assignment for 3MF component
    identity and RGB.

    Artifact RGB remains distinct input information and must not replace
    the printer RGB selected during rasterization.
    """

    extrude_directory = tmp_path / "extrude"

    first_stl = extrude_directory / "color-1.stl"
    second_stl = extrude_directory / "color-2.stl"

    extrude_directory.mkdir(
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

    manifest = extrude_directory / "products.json"

    _write_extrude_manifest(
        manifest,
        [
            _product(
                index=1,
                path=first_stl.name,
                artifact_color_index=1,
                artifact_rgb=(
                    17,
                    43,
                    91,
                ),
                printer_color_name="physical-blue",
                printer_rgb=(
                    20,
                    40,
                    90,
                ),
                distance=1.25,
            ),
            _product(
                index=2,
                path=second_stl.name,
                artifact_color_index=2,
                artifact_rgb=(
                    214,
                    31,
                    42,
                ),
                printer_color_name="physical-red",
                printer_rgb=(
                    220,
                    38,
                    38,
                ),
                distance=2.75,
            ),
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
        "portrait-physical-blue",
        "portrait-physical-red",
    )

    assert tuple(component.color for component in captured_components) == (
        PaletteColor(
            name="physical-blue",
            rgb=(
                20,
                40,
                90,
            ),
        ),
        PaletteColor(
            name="physical-red",
            rgb=(
                220,
                38,
                38,
            ),
        ),
    )


def test_package_does_not_use_artifact_rgb_as_physical_component_color(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Artifact RGB is not substituted for the assigned printer RGB when
    constructing the physical 3MF component.
    """

    extrude_directory = tmp_path / "extrude"

    stl = extrude_directory / "color-1.stl"

    extrude_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    stl.write_text(
        "component",
        encoding="utf-8",
    )

    manifest = extrude_directory / "products.json"

    artifact_rgb = (
        17,
        43,
        91,
    )

    printer_rgb = (
        20,
        40,
        90,
    )

    _write_extrude_manifest(
        manifest,
        [
            _product(
                index=1,
                path=stl.name,
                artifact_color_index=1,
                artifact_rgb=artifact_rgb,
                printer_color_name="physical-blue",
                printer_rgb=printer_rgb,
                distance=1.25,
            ),
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
    assert len(captured_components) == 1

    component = captured_components[0]

    assert component.color == PaletteColor(
        name="physical-blue",
        rgb=printer_rgb,
    )

    assert component.color.rgb != artifact_rgb


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
            _product(
                index=1,
                path=stl.name,
                artifact_color_index=1,
                artifact_rgb=(
                    250,
                    205,
                    10,
                ),
                printer_color_name="gold",
                printer_rgb=(
                    255,
                    215,
                    0,
                ),
                distance=3.5,
            ),
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
