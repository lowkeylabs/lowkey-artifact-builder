"""
Behavioral tests for optional SHAPE SVG manufacturing publication.

Canonical Compose SVG generation is independent of publication.
Publication belongs to artifact-level build orchestration and must
not invalidate or unnecessarily rebuild canonical manufacturing Products.
"""

# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path

from lowkey_artifact_builder.config import (
    get_resolver,
    write_artifact_config,
)
from lowkey_artifact_builder.engine import execute_artifact_build

ARTIFACT_ID = "svg-publication"


def _configure(
    project_root: Path,
    *,
    enabled: bool | None = None,
    realization_overrides: dict[str, bool] | None = None,
) -> None:
    configuration: dict[str, object] = {
        "model": "shape",
    }

    if enabled is not None:
        configuration["shape_svg_enabled"] = enabled

    if realization_overrides is not None:
        configuration["realizations"] = {
            name: {
                "variant": "shape.ornament",
                "shape_svg_enabled": value,
            }
            for name, value in realization_overrides.items()
        }

    write_artifact_config(
        ARTIFACT_ID,
        configuration,
        project_root=project_root,
    )


def _artifact_dir(project_root: Path) -> Path:
    return project_root / "artifacts" / ARTIFACT_ID


def _canonical_svg(
    project_root: Path,
    realization: str = "shape_default",
) -> Path:
    return _artifact_dir(project_root) / "shape" / realization / "20-compose" / "artifact.svg"


def _canonical_3mf(
    project_root: Path,
    realization: str = "shape_default",
) -> Path:
    return _artifact_dir(project_root) / "shape" / realization / "40-package" / "artifact.3mf"


def _published(
    project_root: Path,
    realization: str,
    extension: str,
) -> Path:
    return _artifact_dir(project_root) / f"{realization}.{extension}"


def _build(
    project_root: Path,
    realization: str = "shape_default",
) -> None:
    execute_artifact_build(
        ARTIFACT_ID,
        realization=realization,
        project_root=project_root,
    )


def test_shape_svg_publication_disabled_by_default(
    tmp_path: Path,
) -> None:
    """Ordinary SHAPE manufacturing produces canonical SVG but publishes only 3MF."""
    _configure(tmp_path)

    resolver = get_resolver(
        ARTIFACT_ID,
        realization="shape_default",
        project_root=tmp_path,
    )

    assert resolver("shape_svg_enabled") is False

    _build(tmp_path)

    canonical_svg = _canonical_svg(tmp_path)
    canonical_3mf = _canonical_3mf(tmp_path)

    assert canonical_svg.is_file()
    assert canonical_3mf.is_file()

    assert _published(tmp_path, "shape_default", "3mf").read_bytes() == (canonical_3mf.read_bytes())

    assert not _published(tmp_path, "shape_default", "svg").exists()


def test_shape_svg_publication_enabled(
    tmp_path: Path,
) -> None:
    """Enabled publication creates a faithful Realization-named SVG copy."""
    _configure(tmp_path, enabled=True)

    _build(tmp_path)

    canonical_svg = _canonical_svg(tmp_path)
    canonical_3mf = _canonical_3mf(tmp_path)

    published_svg = _published(tmp_path, "shape_default", "svg")
    published_3mf = _published(tmp_path, "shape_default", "3mf")

    assert canonical_svg.is_file()
    assert canonical_3mf.is_file()

    assert published_svg.is_file()
    assert published_3mf.is_file()

    assert published_svg.read_bytes() == canonical_svg.read_bytes()
    assert published_3mf.read_bytes() == canonical_3mf.read_bytes()


def test_shape_svg_publication_respects_realization_override(
    tmp_path: Path,
) -> None:
    """A Realization may disable an Artifact-wide publication default."""
    _configure(
        tmp_path,
        enabled=True,
        realization_overrides={
            "enabled": True,
            "disabled": False,
        },
    )

    for name, expected in (("enabled", True), ("disabled", False)):
        resolver = get_resolver(
            ARTIFACT_ID,
            realization=name,
            project_root=tmp_path,
        )
        assert resolver("shape_svg_enabled") is expected

        _build(tmp_path, realization=name)

        assert _canonical_svg(tmp_path, name).is_file()
        assert _canonical_3mf(tmp_path, name).is_file()
        assert _published(tmp_path, name, "3mf").is_file()

        assert _published(tmp_path, name, "svg").exists() is expected


def test_shape_svg_republication_without_recomposition(
    tmp_path: Path,
) -> None:
    """Restore missing SVG publication from current canonical Compose Product."""
    _configure(tmp_path, enabled=True)

    _build(tmp_path)

    canonical_svg = _canonical_svg(tmp_path)
    canonical_3mf = _canonical_3mf(tmp_path)
    published_svg = _published(tmp_path, "shape_default", "svg")

    original_svg = canonical_svg.read_bytes()
    original_3mf = canonical_3mf.read_bytes()

    original_svg_mtime = canonical_svg.stat().st_mtime_ns
    original_3mf_mtime = canonical_3mf.stat().st_mtime_ns

    published_svg.unlink()

    assert not published_svg.exists()

    _build(tmp_path)

    assert published_svg.read_bytes() == original_svg
    assert canonical_svg.read_bytes() == original_svg
    assert canonical_3mf.read_bytes() == original_3mf

    # Current canonical Products must not be rewritten simply to
    # restore a missing convenience publication.
    assert canonical_svg.stat().st_mtime_ns == original_svg_mtime
    assert canonical_3mf.stat().st_mtime_ns == original_3mf_mtime


def test_shape_svg_flag_does_not_invalidate_manufacturing(
    tmp_path: Path,
) -> None:
    """Changing publication policy does not regenerate Shape geometry or 3MF."""
    _configure(tmp_path, enabled=False)
    _build(tmp_path)

    canonical_svg = _canonical_svg(tmp_path)
    canonical_3mf = _canonical_3mf(tmp_path)

    svg_mtime = canonical_svg.stat().st_mtime_ns
    package_mtime = canonical_3mf.stat().st_mtime_ns

    _configure(tmp_path, enabled=True)
    _build(tmp_path)

    assert _published(tmp_path, "shape_default", "svg").is_file()
    assert canonical_svg.stat().st_mtime_ns == svg_mtime
    assert canonical_3mf.stat().st_mtime_ns == package_mtime


def test_shape_svg_disable_preserves_canonical_product(
    tmp_path: Path,
) -> None:
    """Disabling publication does not delete canonical Products or the 3MF."""
    _configure(tmp_path, enabled=True)
    _build(tmp_path)

    canonical_svg = _canonical_svg(tmp_path)
    canonical_3mf = _canonical_3mf(tmp_path)
    published_svg = _published(tmp_path, "shape_default", "svg")

    assert published_svg.is_file()

    original_svg = canonical_svg.read_bytes()
    original_3mf = canonical_3mf.read_bytes()

    _configure(tmp_path, enabled=False)
    _build(tmp_path)

    assert canonical_svg.read_bytes() == original_svg
    assert canonical_3mf.read_bytes() == original_3mf
    assert _published(tmp_path, "shape_default", "3mf").is_file()

    # Disabling publication does not require deleting an already
    # published convenience file.
    assert published_svg.read_bytes() == original_svg
