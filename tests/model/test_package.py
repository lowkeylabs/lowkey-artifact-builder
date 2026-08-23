"""
Tests for the artwork package stage.

These tests characterize the storage boundary between the build engine
and the package-stage implementation.

The package stage must consume only the paths supplied through
StageContext. In particular, it must not reconstruct artifact storage
paths from the artifact identifier or from knowledge of the canonical
workspace hierarchy.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

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
    Write a minimal extrusion manifest.
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
    Return an extrusion-manifest RGB color.
    """

    return {
        "red": red,
        "green": green,
        "blue": blue,
    }


# =========================================================
# Storage-boundary tests
# =========================================================


def test_package_uses_declared_artifact_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    The package stage writes to the artifact path supplied by StageContext.

    The output path is deliberately unrelated to the canonical artifact
    hierarchy. This prevents the test from passing if the stage happens
    to reconstruct the normal filesystem layout itself.
    """

    extrude_directory = tmp_path / "somewhere" / "extrusion"

    first_stl = extrude_directory / "color-1.stl"
    second_stl = extrude_directory / "color-2.stl"

    first_stl.parent.mkdir(
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
            {
                "index": 2,
                "path": second_stl.name,
                "name": "red",
                "color": _color(
                    255,
                    0,
                    0,
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

    calls: list[
        tuple[
            tuple[tuple[str, Path], ...],
            Path,
        ]
    ] = []

    def fake_write_stls(
        stls: tuple[tuple[str, Path], ...],
        output: Path,
    ) -> None:
        calls.append(
            (
                tuple(stls),
                output,
            )
        )

        output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        output.write_bytes(b"3mf")

    monkeypatch.setattr(
        package,
        "write_stls",
        fake_write_stls,
    )

    package.execute(context)  # type: ignore[arg-type]

    assert artifact.is_file()

    assert calls == [
        (
            (
                (
                    "example-white",
                    first_stl,
                ),
                (
                    "example-red",
                    second_stl,
                ),
            ),
            artifact,
        )
    ]


def test_package_resolves_dynamic_stls_relative_to_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Dynamic STL product paths are resolved relative to their manifest.

    Their location must not depend on the location of the final artifact.
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

    captured_stls: tuple[tuple[str, Path], ...] | None = None

    def fake_write_stls(
        stls: tuple[tuple[str, Path], ...],
        output: Path,
    ) -> None:
        nonlocal captured_stls

        captured_stls = tuple(stls)

        output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        output.write_bytes(b"3mf")

    monkeypatch.setattr(
        package,
        "write_stls",
        fake_write_stls,
    )

    package.execute(context)  # type: ignore[arg-type]

    assert captured_stls == (
        (
            "portrait-white",
            first_stl,
        ),
        (
            "portrait-green",
            second_stl,
        ),
    )


def test_package_does_not_require_canonical_artifact_directories(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Packaging does not depend on a canonical artifacts/<id>/... hierarchy.
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
            }
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

    received_output: Path | None = None

    def fake_write_stls(
        stls: tuple[tuple[str, Path], ...],
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
        "write_stls",
        fake_write_stls,
    )

    package.execute(context)  # type: ignore[arg-type]

    assert received_output == artifact
    assert artifact.is_file()
