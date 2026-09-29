"""
Tests for the Artwork package stage.

The package stage consumes dimensionalized Artwork components through the
extrusion manifest and packages them through the shared 3MF component
representation.

Filesystem layout remains a build-engine responsibility. Extrusion preserves
Artifact-color identity and logical feature attachment, while Package resolves
physical printer assignments and feature-color overrides for the final 3MF.
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
from lowkey_artifact_builder.formats.threemf import Component, Mesh, component_name
from lowkey_artifact_builder.model.models.artwork.stages import package


class StubResolver:
    """Minimal configuration resolver for package-stage tests."""

    def __init__(
        self,
        values: dict[str, Any],
        *,
        colors: dict[str, dict[str, Any]],
    ) -> None:
        self._values = values
        self.colors = colors

    def __call__(self, name: str) -> Any:
        return self._values.get(name)

    def has(
        self,
        name: str,
    ) -> bool:
        """
        Return whether a configured value exists.
        """

        return name in self._values


class StubContext:
    """Minimal StageContext-compatible object for package-stage tests."""

    def __init__(
        self,
        *,
        artifact_id: str,
        inputs: dict[str, Path],
        outputs: dict[str, Path],
        resolver: StubResolver | None = None,
    ) -> None:
        self.artifact_id = artifact_id
        self._inputs = inputs
        self._outputs = outputs
        self.resolver = resolver

    def input(self, name: str) -> Path:
        return self._inputs[name]

    def output(self, name: str) -> Path:
        return self._outputs[name]


def _write_extrude_manifest(path: Path, products: list[dict[str, Any]]) -> None:
    """Write a minimal Artwork extrusion manifest."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"products": products}), encoding="utf-8")


def _color(red: int, green: int, blue: int) -> dict[str, int]:
    """Return manifest RGB metadata."""
    return {"red": red, "green": green, "blue": blue}


def _product(
    *,
    index: int,
    path: str,
    artifact_color_index: int,
    artifact_rgb: tuple[int, int, int],
) -> dict[str, Any]:
    """Return one dimensionalized registered Artwork product."""
    return {
        "index": index,
        "path": path,
        "artifact_color": {
            "index": artifact_color_index,
            "rgb": _color(*artifact_rgb),
        },
    }


def _mesh() -> Mesh:
    """Return a minimal valid mesh for package-stage tests."""
    return Mesh(
        vertices=((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
        triangles=((0, 1, 2),),
    )


def _capture_write(monkeypatch: pytest.MonkeyPatch):
    """Install test doubles and return a mutable component capture."""
    captured: list[tuple[Component, ...]] = []
    monkeypatch.setattr(package, "load_stl", lambda path: _mesh(), raising=False)

    def fake_write(components, output: Path) -> None:
        captured.append(tuple(components))
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"3mf")

    monkeypatch.setattr(package, "write", fake_write, raising=False)
    return captured


def test_package_uses_declared_artifact_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Artwork packaging writes only to the output supplied by StageContext."""
    directory = tmp_path / "somewhere" / "extrusion"
    stl = directory / "color-1.stl"
    stl.parent.mkdir(parents=True, exist_ok=True)
    stl.write_text("component", encoding="utf-8")
    manifest = directory / "products.json"
    _write_extrude_manifest(
        manifest,
        [_product(index=1, path=stl.name, artifact_color_index=1, artifact_rgb=(250, 250, 250))],
    )
    artifact = tmp_path / "deliberately" / "unrelated" / "finished.3mf"
    context = StubContext(
        artifact_id="example",
        inputs={"extrude.manifest": manifest},
        outputs={"artifact": artifact},
        resolver=StubResolver(
            {"printer_colors": ["white"]},
            colors={"white": {"rgb": [255, 255, 255]}},
        ),
    )
    _capture_write(monkeypatch)
    package.execute(context)  # type: ignore[arg-type]
    assert artifact.is_file()


def test_package_resolves_dynamic_stls_relative_to_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Artwork component paths are resolved relative to their manifest."""
    directory = tmp_path / "dynamic-products"
    directory.mkdir(parents=True, exist_ok=True)
    first_stl = directory / "color-1.stl"
    second_stl = directory / "color-2.stl"
    first_stl.write_text("first", encoding="utf-8")
    second_stl.write_text("second", encoding="utf-8")
    manifest = directory / "manifest.json"
    _write_extrude_manifest(
        manifest,
        [
            _product(
                index=2, path=second_stl.name, artifact_color_index=2, artifact_rgb=(8, 245, 14)
            ),
            _product(
                index=1, path=first_stl.name, artifact_color_index=1, artifact_rgb=(250, 250, 250)
            ),
        ],
    )
    artifact = tmp_path / "other-place" / "artifact.3mf"
    context = StubContext(
        artifact_id="portrait",
        inputs={"extrude.manifest": manifest},
        outputs={"artifact": artifact},
        resolver=StubResolver(
            {"printer_colors": ["green", "white"]},
            colors={
                "green": {"rgb": [0, 255, 0]},
                "white": {"rgb": [255, 255, 255]},
            },
        ),
    )
    loaded: list[Path] = []
    monkeypatch.setattr(
        package, "load_stl", lambda path: loaded.append(path) or _mesh(), raising=False
    )
    monkeypatch.setattr(
        package,
        "write",
        lambda components, output: (
            output.parent.mkdir(parents=True, exist_ok=True),
            output.write_bytes(b"3mf"),
        ),
        raising=False,
    )
    package.execute(context)  # type: ignore[arg-type]
    assert loaded == [first_stl, second_stl]


def test_package_preserves_component_identity_and_resolves_printer_assignment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Package gives registered Artwork layers their shared Artwork identity.

    Extrusion products retain their stage-local color-N filenames. Package
    translates registered Artwork layers to the model-independent artwork-N
    semantic component identity while resolving their physical printer colors.
    """

    directory = tmp_path / "extrude"
    directory.mkdir(parents=True, exist_ok=True)

    first = directory / "color-1.stl"
    second = directory / "color-2.stl"

    first.write_text("first", encoding="utf-8")
    second.write_text("second", encoding="utf-8")

    manifest = directory / "products.json"

    _write_extrude_manifest(
        manifest,
        [
            _product(
                index=1,
                path=first.name,
                artifact_color_index=1,
                artifact_rgb=(17, 43, 91),
            ),
            _product(
                index=2,
                path=second.name,
                artifact_color_index=2,
                artifact_rgb=(214, 31, 42),
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
        resolver=StubResolver(
            {
                "printer_colors": [
                    "physical-blue",
                    "physical-red",
                ],
            },
            colors={
                "physical-blue": {
                    "rgb": [20, 40, 90],
                },
                "physical-red": {
                    "rgb": [220, 38, 38],
                },
            },
        ),
    )

    captured = _capture_write(monkeypatch)

    package.execute(context)  # type: ignore[arg-type]

    assert len(captured) == 1

    assert tuple(component.name for component in captured[0]) == (
        component_name(
            "portrait",
            "artwork-1",
            "physical-blue",
        ),
        component_name(
            "portrait",
            "artwork-2",
            "physical-red",
        ),
    )

    assert tuple(component.color for component in captured[0]) == (
        PaletteColor(
            name="physical-blue",
            rgb=(20, 40, 90),
        ),
        PaletteColor(
            name="physical-red",
            rgb=(220, 38, 38),
        ),
    )


def test_package_does_not_use_artifact_rgb_as_physical_component_color(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Artifact RGB is not substituted for Package's assigned printer RGB."""
    directory = tmp_path / "extrude"
    directory.mkdir(parents=True, exist_ok=True)
    stl = directory / "color-1.stl"
    stl.write_text("component", encoding="utf-8")
    artifact_rgb = (17, 43, 91)
    printer_rgb = (20, 40, 90)
    manifest = directory / "products.json"
    _write_extrude_manifest(
        manifest,
        [_product(index=1, path=stl.name, artifact_color_index=1, artifact_rgb=artifact_rgb)],
    )
    artifact = tmp_path / "artifact.3mf"
    context = StubContext(
        artifact_id="portrait",
        inputs={"extrude.manifest": manifest},
        outputs={"artifact": artifact},
        resolver=StubResolver(
            {"printer_colors": ["physical-blue"]},
            colors={"physical-blue": {"rgb": list(printer_rgb)}},
        ),
    )
    captured = _capture_write(monkeypatch)
    package.execute(context)  # type: ignore[arg-type]
    assert len(captured[0]) == 1
    assert captured[0][0].color == PaletteColor(name="physical-blue", rgb=printer_rgb)

    component_color = captured[0][0].color
    assert component_color == PaletteColor(
        name="physical-blue",
        rgb=printer_rgb,
    )
    assert component_color is not None
    assert component_color.rgb != artifact_rgb


def test_package_does_not_require_canonical_artifact_directories(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Artwork packaging remains independent of workspace filesystem policy."""
    directory = tmp_path / "input"
    directory.mkdir(parents=True, exist_ok=True)
    stl = directory / "component.stl"
    stl.write_text("component", encoding="utf-8")
    manifest = directory / "manifest.json"
    _write_extrude_manifest(
        manifest,
        [_product(index=1, path=stl.name, artifact_color_index=1, artifact_rgb=(250, 205, 10))],
    )
    artifact = tmp_path / "result" / "whatever-name-we-want.bin"
    context = StubContext(
        artifact_id="not-a-directory-name",
        inputs={"extrude.manifest": manifest},
        outputs={"artifact": artifact},
        resolver=StubResolver(
            {"printer_colors": ["gold"]},
            colors={"gold": {"rgb": [255, 215, 0]}},
        ),
    )
    _capture_write(monkeypatch)
    package.execute(context)  # type: ignore[arg-type]
    assert artifact.is_file()


# =========================================================
# Physical printer assignment and feature-color boundary
# =========================================================


def test_package_assigns_printer_colors_to_artifact_layers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Package assigns physical printer colors to ordinary Artwork layers.


    Extrusion supplies Artifact-color identity and printable geometry but no
    physical printer assignment. Package resolves the Artifact colors against
    printer_colors and uses those assignments for the final 3MF components.
    """

    extrude_directory = tmp_path / "extrude"
    extrude_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    red_stl = extrude_directory / "color-1.stl"
    blue_stl = extrude_directory / "color-2.stl"

    red_stl.write_text(
        "red",
        encoding="utf-8",
    )

    blue_stl.write_text(
        "blue",
        encoding="utf-8",
    )

    extrude_manifest = extrude_directory / "products.json"

    _write_extrude_manifest(
        extrude_manifest,
        [
            {
                "index": 1,
                "path": red_stl.name,
                "artifact_color": {
                    "index": 1,
                    "rgb": _color(
                        250,
                        10,
                        10,
                    ),
                },
            },
            {
                "index": 2,
                "path": blue_stl.name,
                "artifact_color": {
                    "index": 2,
                    "rgb": _color(
                        10,
                        10,
                        250,
                    ),
                },
            },
        ],
    )

    artifact = tmp_path / "artifact.3mf"

    context = StubContext(
        artifact_id="portrait",
        inputs={
            "extrude.manifest": extrude_manifest,
        },
        outputs={
            "artifact": artifact,
        },
        resolver=StubResolver(
            {
                "printer_colors": [
                    "red",
                    "blue",
                ],
            },
            colors={
                "red": {
                    "rgb": [
                        255,
                        0,
                        0,
                    ],
                },
                "blue": {
                    "rgb": [
                        0,
                        0,
                        255,
                    ],
                },
            },
        ),
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

        captured_components = tuple(
            components,
        )

        output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        output.write_bytes(
            b"3mf",
        )

    monkeypatch.setattr(
        package,
        "write",
        fake_write,
        raising=False,
    )

    package.execute(context)  # type: ignore[arg-type]

    assert captured_components is not None

    assert tuple(component.color for component in captured_components) == (
        PaletteColor(
            name="red",
            rgb=(
                255,
                0,
                0,
            ),
        ),
        PaletteColor(
            name="blue",
            rgb=(
                0,
                0,
                255,
            ),
        ),
    )

    assert artifact.is_file()


def test_package_assigns_printer_colors_globally_one_to_one(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Package assigns printer colors globally and one-to-one.


    Two Artifact colors may both be closest to the same physical printer
    color independently. Packaging must nevertheless assign each selected
    printer color to at most one registered Artwork layer.
    """

    extrude_directory = tmp_path / "extrude"
    extrude_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    first_stl = extrude_directory / "color-1.stl"
    second_stl = extrude_directory / "color-2.stl"

    first_stl.write_text(
        "first",
        encoding="utf-8",
    )

    second_stl.write_text(
        "second",
        encoding="utf-8",
    )

    extrude_manifest = extrude_directory / "products.json"

    _write_extrude_manifest(
        extrude_manifest,
        [
            {
                "index": 1,
                "path": first_stl.name,
                "artifact_color": {
                    "index": 1,
                    "rgb": _color(
                        250,
                        0,
                        0,
                    ),
                },
            },
            {
                "index": 2,
                "path": second_stl.name,
                "artifact_color": {
                    "index": 2,
                    "rgb": _color(
                        245,
                        0,
                        0,
                    ),
                },
            },
        ],
    )

    artifact = tmp_path / "artifact.3mf"

    context = StubContext(
        artifact_id="portrait",
        inputs={
            "extrude.manifest": extrude_manifest,
        },
        outputs={
            "artifact": artifact,
        },
        resolver=StubResolver(
            {
                "printer_colors": [
                    "red",
                    "blue",
                ],
            },
            colors={
                "red": {
                    "rgb": [
                        255,
                        0,
                        0,
                    ],
                },
                "blue": {
                    "rgb": [
                        0,
                        0,
                        255,
                    ],
                },
            },
        ),
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

        captured_components = tuple(
            components,
        )

        output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        output.write_bytes(
            b"3mf",
        )

    monkeypatch.setattr(
        package,
        "write",
        fake_write,
        raising=False,
    )

    package.execute(context)  # type: ignore[arg-type]

    assert captured_components is not None
    assert len(captured_components) == 2

    assert {component.color.name for component in captured_components} == {
        "red",
        "blue",
    }


def test_package_loop_inherits_attached_artifact_layer_printer_color(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    A Loop without an explicit physical color inherits the printer color
    assigned to its attached Artifact-color layer.

    Registered Artwork receives the shared artwork-N component identity while
    the Loop retains its semantic feature identity.
    """

    extrude_directory = tmp_path / "extrude"
    extrude_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    artwork_stl = extrude_directory / "color-1.stl"
    loop_stl = extrude_directory / "loop.stl"

    artwork_stl.write_text(
        "artwork",
        encoding="utf-8",
    )
    loop_stl.write_text(
        "loop",
        encoding="utf-8",
    )

    extrude_manifest = extrude_directory / "products.json"

    _write_extrude_manifest(
        extrude_manifest,
        [
            {
                "index": 1,
                "path": artwork_stl.name,
                "artifact_color": {
                    "index": 7,
                    "rgb": _color(
                        250,
                        250,
                        250,
                    ),
                },
            },
            {
                "path": loop_stl.name,
                "artifact_color_index": 7,
            },
        ],
    )

    artifact = tmp_path / "artifact.3mf"

    resolver = StubResolver(
        {
            "printer_colors": [
                "white",
            ],
        },
        colors={
            "white": {
                "rgb": [
                    255,
                    255,
                    255,
                ],
            },
        },
    )

    context = StubContext(
        artifact_id="ornament",
        inputs={
            "extrude.manifest": extrude_manifest,
        },
        outputs={
            "artifact": artifact,
        },
        resolver=resolver,
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

    assert loaded_paths == [
        artwork_stl,
        loop_stl,
    ]

    assert captured_components is not None
    assert len(captured_components) == 2

    assert tuple(component.name for component in captured_components) == (
        component_name(
            "ornament",
            "artwork-1",
            "white",
        ),
        component_name(
            "ornament",
            "loop",
            "white",
        ),
    )

    assert tuple(component.color for component in captured_components) == (
        PaletteColor(
            name="white",
            rgb=(255, 255, 255),
        ),
        PaletteColor(
            name="white",
            rgb=(255, 255, 255),
        ),
    )

    assert artifact.is_file()


def test_package_base_inherits_attached_artifact_layer_printer_color(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Base inherits the physical printer color assigned to the Artifact-color
    layer referenced by its artifact_color_index.

    Registered Artwork receives the shared artwork-N component identity while
    Base retains its semantic feature identity.
    """

    extrude_directory = tmp_path / "extrude"
    extrude_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    artwork_stl = extrude_directory / "color-1.stl"
    base_stl = extrude_directory / "base.stl"

    artwork_stl.write_text(
        "artwork",
        encoding="utf-8",
    )
    base_stl.write_text(
        "base",
        encoding="utf-8",
    )

    extrude_manifest = extrude_directory / "products.json"

    _write_extrude_manifest(
        extrude_manifest,
        [
            {
                "index": 1,
                "path": artwork_stl.name,
                "artifact_color": {
                    "index": 7,
                    "rgb": _color(
                        250,
                        250,
                        250,
                    ),
                },
            },
            {
                "path": base_stl.name,
                "artifact_color_index": 7,
            },
        ],
    )

    artifact = tmp_path / "artifact.3mf"

    context = StubContext(
        artifact_id="ornament",
        inputs={
            "extrude.manifest": extrude_manifest,
        },
        outputs={
            "artifact": artifact,
        },
        resolver=StubResolver(
            {
                "printer_colors": [
                    "white",
                ],
            },
            colors={
                "white": {
                    "rgb": [
                        255,
                        255,
                        255,
                    ],
                },
            },
        ),
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
        component_name(
            "ornament",
            "artwork-1",
            "white",
        ),
        component_name(
            "ornament",
            "base",
            "white",
        ),
    )

    assert tuple(component.color.name for component in captured_components) == (
        "white",
        "white",
    )


def test_package_outer_ridge_inherits_attached_artifact_layer_printer_color(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Outer Ridge inherits the physical printer color assigned to the
    Artifact-color layer referenced by its artifact_color_index.

    Registered Artwork receives the shared artwork-N component identity while
    Outer Ridge retains its semantic feature identity.
    """

    extrude_directory = tmp_path / "extrude"
    extrude_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    artwork_stl = extrude_directory / "color-1.stl"
    outer_ridge_stl = extrude_directory / "outer-ridge.stl"

    artwork_stl.write_text(
        "artwork",
        encoding="utf-8",
    )
    outer_ridge_stl.write_text(
        "outer ridge",
        encoding="utf-8",
    )

    extrude_manifest = extrude_directory / "products.json"

    _write_extrude_manifest(
        extrude_manifest,
        [
            {
                "index": 1,
                "path": artwork_stl.name,
                "artifact_color": {
                    "index": 7,
                    "rgb": _color(
                        250,
                        250,
                        250,
                    ),
                },
            },
            {
                "path": outer_ridge_stl.name,
                "artifact_color_index": 7,
            },
        ],
    )

    artifact = tmp_path / "artifact.3mf"

    context = StubContext(
        artifact_id="ornament",
        inputs={
            "extrude.manifest": extrude_manifest,
        },
        outputs={
            "artifact": artifact,
        },
        resolver=StubResolver(
            {
                "printer_colors": [
                    "white",
                ],
            },
            colors={
                "white": {
                    "rgb": [
                        255,
                        255,
                        255,
                    ],
                },
            },
        ),
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
        component_name(
            "ornament",
            "artwork-1",
            "white",
        ),
        component_name(
            "ornament",
            "outer-ridge",
            "white",
        ),
    )

    assert tuple(component.color.name for component in captured_components) == (
        "white",
        "white",
    )


def test_package_explicit_feature_colors_override_inherited_printer_color(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Explicit feature-color parameters override inherited physical color.

    Feature geometry continues to reference its attached Artifact color through
    artifact_color_index, but Package owns physical feature-color overrides.

    Registered Artwork uses the shared artwork-N component identity. Loop,
    Base, and Outer Ridge retain their semantic feature identities and may each
    override the physical printer color they would otherwise inherit.
    """

    extrude_directory = tmp_path / "extrude"
    extrude_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    artwork_stl = extrude_directory / "color-1.stl"
    loop_stl = extrude_directory / "loop.stl"
    base_stl = extrude_directory / "base.stl"
    outer_ridge_stl = extrude_directory / "outer-ridge.stl"

    for path in (
        artwork_stl,
        loop_stl,
        base_stl,
        outer_ridge_stl,
    ):
        path.write_text(
            path.stem,
            encoding="utf-8",
        )

    extrude_manifest = extrude_directory / "products.json"

    _write_extrude_manifest(
        extrude_manifest,
        [
            {
                "index": 1,
                "path": artwork_stl.name,
                "artifact_color": {
                    "index": 7,
                    "rgb": _color(
                        250,
                        250,
                        250,
                    ),
                },
            },
            {
                "path": loop_stl.name,
                "artifact_color_index": 7,
            },
            {
                "path": base_stl.name,
                "artifact_color_index": 7,
            },
            {
                "path": outer_ridge_stl.name,
                "artifact_color_index": 7,
            },
        ],
    )

    artifact = tmp_path / "artifact.3mf"

    context = StubContext(
        artifact_id="ornament",
        inputs={
            "extrude.manifest": extrude_manifest,
        },
        outputs={
            "artifact": artifact,
        },
        resolver=StubResolver(
            {
                "printer_colors": [
                    "white",
                ],
                "loop_color": "red",
                "artwork_base_color": "black",
                "artwork_outer_ridge_color": "blue",
            },
            colors={
                "white": {
                    "rgb": [
                        255,
                        255,
                        255,
                    ],
                },
                "red": {
                    "rgb": [
                        255,
                        0,
                        0,
                    ],
                },
                "black": {
                    "rgb": [
                        0,
                        0,
                        0,
                    ],
                },
                "blue": {
                    "rgb": [
                        0,
                        0,
                        255,
                    ],
                },
            },
        ),
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

        captured_components = tuple(
            components,
        )

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
    assert len(captured_components) == 4

    colors_by_component = {component.name: component.color for component in captured_components}

    assert colors_by_component[
        component_name(
            "ornament",
            "artwork-1",
            "white",
        )
    ] == PaletteColor(
        name="white",
        rgb=(
            255,
            255,
            255,
        ),
    )

    assert colors_by_component[
        component_name(
            "ornament",
            "loop",
            "red",
        )
    ] == PaletteColor(
        name="red",
        rgb=(
            255,
            0,
            0,
        ),
    )

    assert colors_by_component[
        component_name(
            "ornament",
            "base",
            "black",
        )
    ] == PaletteColor(
        name="black",
        rgb=(
            0,
            0,
            0,
        ),
    )

    assert colors_by_component[
        component_name(
            "ornament",
            "outer-ridge",
            "blue",
        )
    ] == PaletteColor(
        name="blue",
        rgb=(
            0,
            0,
            255,
        ),
    )
