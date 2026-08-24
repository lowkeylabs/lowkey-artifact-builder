"""
Tests for logical product filesystem resolution.
"""
# File: tests/engine/test_product_resolver.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path

import pytest

from lowkey_artifact_builder.engine.product_resolver import ProductResolver
from lowkey_artifact_builder.model.specs import (
    ProductRef,
    ProductSpec,
    StageSpec,
)


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


def test_product_resolver_resolves_product_path(
    tmp_path: Path,
) -> None:
    resolver = ProductResolver(
        project_root=tmp_path,
    )

    stage = StageSpec(
        id=30,
        name="vector",
    )

    product = ProductSpec(
        name="colors",
        path="colors.svg",
    )

    assert resolver.product_path(
        artifact="nydeli",
        model="artwork",
        realization="default",
        stage=stage,
        product=product,
    ) == (tmp_path / "artifacts" / "nydeli" / "artwork" / "default" / "30-vector" / "colors.svg")


def test_product_resolver_resolves_product_reference(
    tmp_path: Path,
) -> None:
    resolver = ProductResolver(
        project_root=tmp_path,
    )

    ref = ProductRef(
        artifact="nydeli",
        model="artwork",
        realization="default",
        stage="vector",
        product="colors",
    )

    stage = StageSpec(
        id=30,
        name="vector",
    )

    product = ProductSpec(
        name="colors",
        path="colors.svg",
    )

    assert resolver.resolve(
        ref,
        stage=stage,
        product=product,
    ) == (tmp_path / "artifacts" / "nydeli" / "artwork" / "default" / "30-vector" / "colors.svg")


def test_product_resolver_rejects_mismatched_stage(
    tmp_path: Path,
) -> None:
    resolver = ProductResolver(
        project_root=tmp_path,
    )

    ref = ProductRef(
        artifact="nydeli",
        model="artwork",
        realization="default",
        stage="vector",
        product="colors",
    )

    stage = StageSpec(
        id=20,
        name="raster",
    )

    product = ProductSpec(
        name="colors",
        path="colors.svg",
    )

    with pytest.raises(
        ValueError,
        match="stage",
    ):
        resolver.resolve(
            ref,
            stage=stage,
            product=product,
        )


def test_product_resolver_rejects_mismatched_product(
    tmp_path: Path,
) -> None:
    resolver = ProductResolver(
        project_root=tmp_path,
    )

    ref = ProductRef(
        artifact="nydeli",
        model="artwork",
        realization="default",
        stage="vector",
        product="colors",
    )

    stage = StageSpec(
        id=30,
        name="vector",
    )

    product = ProductSpec(
        name="geometry",
        path="geometry.svg",
    )

    with pytest.raises(
        ValueError,
        match="product",
    ):
        resolver.resolve(
            ref,
            stage=stage,
            product=product,
        )
