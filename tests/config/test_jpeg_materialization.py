"""Regression tests for preserving JPEG Artifact source files."""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from lowkey_artifact_builder.config import (
    ConfigError,
    configure_artifact,
    discover_artifacts,
    load_artifact_config,
    materialize_artifact,
)


def _jpeg(path: Path) -> bytes:
    """Create a small JPEG and return its original bytes."""
    path.parent.mkdir(parents=True, exist_ok=True)

    image = Image.new("RGB", (32, 24), (40, 100, 180))
    try:
        image.save(path, format="JPEG", quality=95)
    finally:
        image.close()

    return path.read_bytes()


@pytest.mark.parametrize("suffix", [".jpg", ".jpeg"])
def test_jpeg_ingestion_preserves_original_bytes_and_extension(
    tmp_path: Path,
    suffix: str,
) -> None:
    source = tmp_path / "customer" / f"house{suffix}"
    original_bytes = _jpeg(source)

    configure_artifact(
        "house",
        input_files={"artwork": source},
        project_root=tmp_path,
    )

    artifact_dir = tmp_path / "artifacts" / "house"
    ingested = artifact_dir / f"artifact{suffix}"

    assert ingested.is_file()
    assert ingested.read_bytes() == original_bytes
    assert source.read_bytes() == original_bytes
    assert not (artifact_dir / "artifact.png").exists()

    config = load_artifact_config("house", project_root=tmp_path)

    assert Path(config["source"]) == Path("artifacts/house") / f"artifact{suffix}"


@pytest.mark.parametrize("suffix", [".jpg", ".jpeg"])
def test_jpeg_original_materializes_without_conversion(
    tmp_path: Path,
    suffix: str,
) -> None:
    original = tmp_path / "originals" / f"house{suffix}"
    original_bytes = _jpeg(original)

    materialize_artifact("house", project_root=tmp_path)

    artifact_dir = tmp_path / "artifacts" / "house"
    materialized = artifact_dir / f"artifact{suffix}"

    assert (artifact_dir / "artifact.toml").is_file()
    assert materialized.is_file()
    assert materialized.read_bytes() == original_bytes
    assert original.read_bytes() == original_bytes
    assert not (artifact_dir / "artifact.png").exists()

    config = load_artifact_config("house", project_root=tmp_path)

    assert Path(config["source"]) == Path("artifacts/house") / f"artifact{suffix}"

    assert Path(config["original"]) == Path("originals") / f"house{suffix}"


def test_jpeg_materialization_is_idempotent(
    tmp_path: Path,
) -> None:
    original = tmp_path / "originals" / "house.jpg"
    original_bytes = _jpeg(original)

    materialize_artifact("house", project_root=tmp_path)

    artifact_dir = tmp_path / "artifacts" / "house"
    materialized = artifact_dir / "artifact.jpg"
    config_path = artifact_dir / "artifact.toml"

    before = (
        materialized.read_bytes(),
        materialized.stat().st_mtime_ns,
        config_path.read_bytes(),
        config_path.stat().st_mtime_ns,
    )

    materialize_artifact("house", project_root=tmp_path)

    after = (
        materialized.read_bytes(),
        materialized.stat().st_mtime_ns,
        config_path.read_bytes(),
        config_path.stat().st_mtime_ns,
    )

    assert before == after
    assert original.read_bytes() == original_bytes


def test_jpeg_original_is_discoverable(
    tmp_path: Path,
) -> None:
    original = tmp_path / "originals" / "house.jpg"
    _jpeg(original)

    discovered = discover_artifacts(project_root=tmp_path)

    house = next(artifact for artifact in discovered if artifact.artifact_id == "house")

    assert house.original_path == original
    assert not house.materialized


def test_conflicting_jpeg_and_png_originals_are_rejected(
    tmp_path: Path,
) -> None:
    _jpeg(tmp_path / "originals" / "house.jpg")

    png = tmp_path / "originals" / "house.png"
    image = Image.new("RGB", (16, 16), "white")
    try:
        image.save(png)
    finally:
        image.close()

    with pytest.raises(ConfigError, match="conflicting preserved originals"):
        materialize_artifact("house", project_root=tmp_path)

    assert not (tmp_path / "artifacts" / "house").exists()
