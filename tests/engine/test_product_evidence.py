"""
Tests for persistent product evidence gathering.

Product evidence gathering inspects one expected persistent product and
the completion metadata of its producing stage.

These tests establish filesystem and completion evidence independently
of freshness evaluation, execution-plan construction, dependency
invalidation, event emission, and stage execution.
"""
# File: tests/engine/test_product_evidence.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path

import pytest

from lowkey_artifact_builder.engine import (
    StageCompletion,
    gather_product_evidence,
    write_stage_completion,
)

# =========================================================
# Helpers
# =========================================================


def _working_dir(
    tmp_path: Path,
) -> Path:
    """
    Create a representative stage working directory.
    """

    path = tmp_path / "artifacts" / "example" / "artwork" / "default" / "30-vector"

    path.mkdir(
        parents=True,
    )

    return path


def _completion(
    *products: str,
) -> StageCompletion:
    """
    Create representative completion metadata.
    """

    return StageCompletion(
        artifact_id="example",
        model_name="artwork",
        realization="default",
        stage_name="vector",
        products=products,
    )


def _write_product(
    working_dir: Path,
    relative_path: str = "layers.svg",
) -> Path:
    """
    Create a representative persistent product.
    """

    path = working_dir / relative_path

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        "<svg/>",
        encoding="utf-8",
    )

    return path


# =========================================================
# Absent products
# =========================================================


def test_missing_product_without_completion_is_absent_evidence(
    tmp_path: Path,
) -> None:
    """
    Missing materialization and missing completion metadata indicate absence.
    """

    working_dir = _working_dir(
        tmp_path,
    )

    evidence = gather_product_evidence(
        working_dir=working_dir,
        product_name="layers",
        product_path=Path("layers.svg"),
    )

    assert not evidence.exists
    assert not evidence.completion_exists


def test_absent_evidence_does_not_claim_validity(
    tmp_path: Path,
) -> None:
    """
    A missing product is not reported as valid.
    """

    working_dir = _working_dir(
        tmp_path,
    )

    evidence = gather_product_evidence(
        working_dir=working_dir,
        product_name="layers",
        product_path=Path("layers.svg"),
    )

    assert not evidence.valid


# =========================================================
# Incomplete products
# =========================================================


def test_existing_product_without_completion_is_incomplete_evidence(
    tmp_path: Path,
) -> None:
    """
    Materialization without completion metadata records unfinished work.
    """

    working_dir = _working_dir(
        tmp_path,
    )

    _write_product(
        working_dir,
    )

    evidence = gather_product_evidence(
        working_dir=working_dir,
        product_name="layers",
        product_path=Path("layers.svg"),
    )

    assert evidence.exists
    assert not evidence.completion_exists


def test_existing_product_without_completion_may_be_valid(
    tmp_path: Path,
) -> None:
    """
    Physical validity is independent of successful completion evidence.
    """

    working_dir = _working_dir(
        tmp_path,
    )

    _write_product(
        working_dir,
    )

    evidence = gather_product_evidence(
        working_dir=working_dir,
        product_name="layers",
        product_path=Path("layers.svg"),
    )

    assert evidence.valid


# =========================================================
# Completion evidence
# =========================================================


def test_completion_listing_product_is_completion_evidence(
    tmp_path: Path,
) -> None:
    """
    Completion metadata applies when it explicitly lists the product.
    """

    working_dir = _working_dir(
        tmp_path,
    )

    _write_product(
        working_dir,
    )

    write_stage_completion(
        working_dir,
        _completion(
            "layers",
        ),
    )

    evidence = gather_product_evidence(
        working_dir=working_dir,
        product_name="layers",
        product_path=Path("layers.svg"),
    )

    assert evidence.exists
    assert evidence.completion_exists
    assert evidence.valid


def test_completion_not_listing_product_is_not_completion_evidence(
    tmp_path: Path,
) -> None:
    """
    Stage completion does not prove completion of an unlisted product.
    """

    working_dir = _working_dir(
        tmp_path,
    )

    _write_product(
        working_dir,
    )

    write_stage_completion(
        working_dir,
        _completion(
            "manifest",
        ),
    )

    evidence = gather_product_evidence(
        working_dir=working_dir,
        product_name="layers",
        product_path=Path("layers.svg"),
    )

    assert evidence.exists
    assert not evidence.completion_exists
    assert evidence.valid


def test_completion_listing_missing_product_preserves_completion_evidence(
    tmp_path: Path,
) -> None:
    """
    Completion metadata may claim a product whose materialization is missing.

    State evaluation will classify this combination as INVALID.
    """

    working_dir = _working_dir(
        tmp_path,
    )

    write_stage_completion(
        working_dir,
        _completion(
            "layers",
        ),
    )

    evidence = gather_product_evidence(
        working_dir=working_dir,
        product_name="layers",
        product_path=Path("layers.svg"),
    )

    assert not evidence.exists
    assert evidence.completion_exists
    assert not evidence.valid


# =========================================================
# Physical validity
# =========================================================


def test_regular_file_is_valid_materialization(
    tmp_path: Path,
) -> None:
    """
    A regular persistent product file satisfies baseline validity.
    """

    working_dir = _working_dir(
        tmp_path,
    )

    _write_product(
        working_dir,
    )

    evidence = gather_product_evidence(
        working_dir=working_dir,
        product_name="layers",
        product_path=Path("layers.svg"),
    )

    assert evidence.valid


def test_directory_at_product_path_is_invalid_materialization(
    tmp_path: Path,
) -> None:
    """
    A directory does not satisfy a declared persistent file product.
    """

    working_dir = _working_dir(
        tmp_path,
    )

    (working_dir / "layers.svg").mkdir()

    write_stage_completion(
        working_dir,
        _completion(
            "layers",
        ),
    )

    evidence = gather_product_evidence(
        working_dir=working_dir,
        product_name="layers",
        product_path=Path("layers.svg"),
    )

    assert evidence.exists
    assert evidence.completion_exists
    assert not evidence.valid


# =========================================================
# Completion corruption
# =========================================================


def test_corrupt_completion_metadata_is_invalid_evidence(
    tmp_path: Path,
) -> None:
    """
    Corrupt completion metadata is not silently treated as absent.
    """

    working_dir = _working_dir(
        tmp_path,
    )

    _write_product(
        working_dir,
    )

    (working_dir / ".completion.json").write_text(
        "{not valid json",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
    ):
        gather_product_evidence(
            working_dir=working_dir,
            product_name="layers",
            product_path=Path("layers.svg"),
        )


# =========================================================
# Freshness boundary
# =========================================================


def test_gathered_evidence_does_not_claim_freshness(
    tmp_path: Path,
) -> None:
    """
    Filesystem and completion evidence alone cannot prove freshness.
    """

    working_dir = _working_dir(
        tmp_path,
    )

    _write_product(
        working_dir,
    )

    write_stage_completion(
        working_dir,
        _completion(
            "layers",
        ),
    )

    evidence = gather_product_evidence(
        working_dir=working_dir,
        product_name="layers",
        product_path=Path("layers.svg"),
    )

    assert not evidence.fresh
