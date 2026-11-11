"""SVG-only manufacturing publication through the artifact-build API.

An explicitly requested SHAPE SVG is published independently of
3MF manufacturing and without invalidating canonical Products.
"""

# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path

import pytest

from lowkey_artifact_builder.config import write_artifact_config
from lowkey_artifact_builder.engine import execute_artifact_build

ARTIFACT_ID = "svg-target-publication"


def _configure(
    root: Path,
    *,
    svg_enabled: bool = False,
) -> None:
    write_artifact_config(
        ARTIFACT_ID,
        {
            "model": "shape",
            "shape_svg_enabled": svg_enabled,
            "realizations": {
                "front": {"variant": "shape.coaster"},
                "back": {"variant": "shape.coaster"},
            },
        },
        project_root=root,
    )


def _canonical(root: Path, realization: str) -> Path:
    return root / "artifacts" / ARTIFACT_ID / "shape" / realization / "20-compose" / "artifact.svg"


def _published(root: Path, realization: str) -> Path:
    return root / "artifacts" / ARTIFACT_ID / f"{realization}.svg"


def _realization_root(root: Path, realization: str) -> Path:
    return root / "artifacts" / ARTIFACT_ID / "shape" / realization


def _build(root: Path, realization: str = "front") -> None:
    execute_artifact_build(
        ARTIFACT_ID,
        realization=realization,
        product="svg",
        project_root=root,
    )


@pytest.mark.parametrize("svg_enabled", [False, True])
def test_explicit_svg_build_publishes_requested_product(
    tmp_path: Path,
    svg_enabled: bool,
) -> None:
    """
    Explicit SVG selection publishes the requested Product regardless
    of the optional SVG publication flag used by legacy 3MF builds.
    """
    _configure(tmp_path, svg_enabled=svg_enabled)

    _build(tmp_path)

    canonical = _canonical(tmp_path, "front")
    published = _published(tmp_path, "front")

    assert canonical.is_file()
    assert published.is_file()
    assert published.read_bytes() == canonical.read_bytes()

    realization_root = _realization_root(tmp_path, "front")

    assert not (realization_root / "30-extrude").exists()
    assert not (realization_root / "40-package").exists()
    assert not (tmp_path / "artifacts" / ARTIFACT_ID / "front.3mf").exists()


def test_svg_republication_does_not_recompose(
    tmp_path: Path,
) -> None:
    """
    Missing convenience publication is restored without changing
    an already-current canonical Compose Product.
    """
    _configure(tmp_path)

    _build(tmp_path)

    canonical = _canonical(tmp_path, "front")
    published = _published(tmp_path, "front")

    original_bytes = canonical.read_bytes()
    original_mtime = canonical.stat().st_mtime_ns

    published.unlink()

    _build(tmp_path)

    assert published.read_bytes() == original_bytes
    assert canonical.read_bytes() == original_bytes
    assert canonical.stat().st_mtime_ns == original_mtime

    assert not (_realization_root(tmp_path, "front") / "30-extrude").exists()
    assert not (_realization_root(tmp_path, "front") / "40-package").exists()


def test_svg_publication_is_realization_isolated(
    tmp_path: Path,
) -> None:
    """
    Publishing another Realization must not overwrite or rebuild
    the previously manufactured Realization.
    """
    _configure(tmp_path)

    _build(tmp_path, "front")

    front_canonical = _canonical(tmp_path, "front")
    front_published = _published(tmp_path, "front")

    front_bytes = front_published.read_bytes()
    front_mtime = front_canonical.stat().st_mtime_ns

    assert not _published(tmp_path, "back").exists()

    _build(tmp_path, "back")

    back_canonical = _canonical(tmp_path, "back")
    back_published = _published(tmp_path, "back")

    assert back_canonical.is_file()
    assert back_published.is_file()
    assert back_published.read_bytes() == back_canonical.read_bytes()

    assert front_published.read_bytes() == front_bytes
    assert front_canonical.stat().st_mtime_ns == front_mtime

    assert not (_realization_root(tmp_path, "back") / "30-extrude").exists()
    assert not (_realization_root(tmp_path, "back") / "40-package").exists()


def test_repeated_svg_build_preserves_canonical_product(
    tmp_path: Path,
) -> None:
    """
    Repeated publication must not rewrite a current canonical SVG.
    """
    _configure(tmp_path)

    _build(tmp_path)

    canonical = _canonical(tmp_path, "front")
    published = _published(tmp_path, "front")

    original_bytes = canonical.read_bytes()
    original_mtime = canonical.stat().st_mtime_ns

    _build(tmp_path)

    assert canonical.read_bytes() == original_bytes
    assert canonical.stat().st_mtime_ns == original_mtime
    assert published.read_bytes() == original_bytes

    assert not (_realization_root(tmp_path, "front") / "40-package").exists()
