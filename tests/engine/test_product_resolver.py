"""
Tests for logical product filesystem resolution.
"""

from __future__ import annotations

from pathlib import Path

from lowkey_artifact_builder.engine.product_resolver import ProductResolver
from lowkey_artifact_builder.model.specs import StageSpec


def test_product_resolver_resolves_artifact_directory(
    tmp_path: Path,
) -> None:
    resolver = ProductResolver(
        project_root=tmp_path,
    )

    assert resolver.artifact_dir("nydeli") == (tmp_path / "artifacts" / "nydeli")


def test_product_resolver_resolves_model_directory(
    tmp_path: Path,
) -> None:
    resolver = ProductResolver(
        project_root=tmp_path,
    )

    assert resolver.model_dir(
        artifact="nydeli",
        model="artwork",
    ) == (tmp_path / "artifacts" / "nydeli" / "artwork")


def test_product_resolver_resolves_realization_directory(
    tmp_path: Path,
) -> None:
    resolver = ProductResolver(
        project_root=tmp_path,
    )

    assert resolver.realization_dir(
        artifact="nydeli",
        model="artwork",
        realization="default",
    ) == (tmp_path / "artifacts" / "nydeli" / "artwork" / "default")


def test_product_resolver_resolves_stage_directory(
    tmp_path: Path,
) -> None:
    resolver = ProductResolver(
        project_root=tmp_path,
    )

    stage = StageSpec(
        id=30,
        name="vector",
    )

    assert resolver.stage_dir(
        artifact="nydeli",
        model="artwork",
        realization="default",
        stage=stage,
    ) == (tmp_path / "artifacts" / "nydeli" / "artwork" / "default" / "30-vector")
