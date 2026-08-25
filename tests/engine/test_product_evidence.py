"""
Tests for persistent product evidence gathering.

Product evidence gathering inspects one expected persistent product and
the completion metadata of its producing stage.

Freshness is established only when valid completion metadata records a
fingerprint matching the fingerprint required by the current build
context.

These tests keep evidence gathering separate from semantic ProductState
evaluation, execution planning, and stage execution.
"""
# File: tests/engine/test_product_evidence.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path

import pytest

from lowkey_artifact_builder.engine import (
    ProductEvidence,
    ProductFingerprint,
    StageCompletion,
    completion_path,
    gather_product_evidence,
    write_stage_completion,
)

# =========================================================
# Helpers
# =========================================================


def _fingerprint(
    value: str = "abc123",
) -> ProductFingerprint:
    """
    Create representative product provenance.
    """

    return ProductFingerprint(
        algorithm="sha256",
        value=value,
    )


def _write_completion(
    working_dir: Path,
    *,
    products: tuple[str, ...] = ("layers",),
    fingerprint: ProductFingerprint | None = None,
) -> None:
    """
    Write representative completion metadata.
    """

    write_stage_completion(
        working_dir,
        StageCompletion(
            artifact_id="example",
            model_name="artwork",
            realization="default",
            stage_name="vector",
            products=products,
            fingerprint=fingerprint,
        ),
    )


def _gather(
    working_dir: Path,
    *,
    required_fingerprint: ProductFingerprint | None = None,
) -> ProductEvidence:
    """
    Gather evidence for the representative layers product.
    """

    return gather_product_evidence(
        working_dir=working_dir,
        product_name="layers",
        product_path=Path(
            "layers.svg",
        ),
        required_fingerprint=required_fingerprint,
    )


# =========================================================
# Materialization evidence
# =========================================================


def test_missing_product_is_absent(
    tmp_path: Path,
) -> None:
    """
    A missing persistent product has neither existence nor validity.
    """

    evidence = _gather(
        tmp_path,
        required_fingerprint=_fingerprint(),
    )

    assert not evidence.exists
    assert not evidence.valid


def test_existing_regular_file_is_valid(
    tmp_path: Path,
) -> None:
    """
    A regular file at the expected product path is baseline valid.
    """

    (tmp_path / "layers.svg").write_text(
        "product",
        encoding="utf-8",
    )

    evidence = _gather(
        tmp_path,
        required_fingerprint=_fingerprint(),
    )

    assert evidence.exists
    assert evidence.valid


def test_existing_directory_is_not_valid_product(
    tmp_path: Path,
) -> None:
    """
    Filesystem existence alone does not establish product validity.
    """

    (tmp_path / "layers.svg").mkdir()

    evidence = _gather(
        tmp_path,
        required_fingerprint=_fingerprint(),
    )

    assert evidence.exists
    assert not evidence.valid


# =========================================================
# Completion evidence
# =========================================================


def test_missing_completion_is_not_completion_evidence(
    tmp_path: Path,
) -> None:
    """
    A materialized product without completion metadata is incomplete.
    """

    (tmp_path / "layers.svg").write_text(
        "product",
        encoding="utf-8",
    )

    evidence = _gather(
        tmp_path,
        required_fingerprint=_fingerprint(),
    )

    assert not evidence.completion_exists


def test_completion_listing_product_is_completion_evidence(
    tmp_path: Path,
) -> None:
    """
    Completion metadata applies when it lists the requested product.
    """

    (tmp_path / "layers.svg").write_text(
        "product",
        encoding="utf-8",
    )

    _write_completion(
        tmp_path,
        fingerprint=_fingerprint(),
    )

    evidence = _gather(
        tmp_path,
        required_fingerprint=_fingerprint(),
    )

    assert evidence.completion_exists


def test_completion_not_listing_product_is_not_completion_evidence(
    tmp_path: Path,
) -> None:
    """
    Stage completion does not imply completion for an unlisted product.
    """

    (tmp_path / "layers.svg").write_text(
        "product",
        encoding="utf-8",
    )

    _write_completion(
        tmp_path,
        products=("manifest",),
        fingerprint=_fingerprint(),
    )

    evidence = _gather(
        tmp_path,
        required_fingerprint=_fingerprint(),
    )

    assert not evidence.completion_exists


# =========================================================
# Freshness evidence
# =========================================================


def test_matching_completion_fingerprint_is_fresh(
    tmp_path: Path,
) -> None:
    """
    Matching recorded and required fingerprints prove freshness.
    """

    (tmp_path / "layers.svg").write_text(
        "product",
        encoding="utf-8",
    )

    fingerprint = _fingerprint(
        "same",
    )

    _write_completion(
        tmp_path,
        fingerprint=fingerprint,
    )

    evidence = _gather(
        tmp_path,
        required_fingerprint=fingerprint,
    )

    assert evidence.fresh


def test_different_completion_fingerprint_is_not_fresh(
    tmp_path: Path,
) -> None:
    """
    Changed build context makes a completed product stale.
    """

    (tmp_path / "layers.svg").write_text(
        "product",
        encoding="utf-8",
    )

    _write_completion(
        tmp_path,
        fingerprint=_fingerprint(
            "old",
        ),
    )

    evidence = _gather(
        tmp_path,
        required_fingerprint=_fingerprint(
            "new",
        ),
    )

    assert not evidence.fresh


def test_missing_recorded_fingerprint_is_not_fresh(
    tmp_path: Path,
) -> None:
    """
    Legacy completion metadata cannot prove freshness.
    """

    (tmp_path / "layers.svg").write_text(
        "product",
        encoding="utf-8",
    )

    _write_completion(
        tmp_path,
        fingerprint=None,
    )

    evidence = _gather(
        tmp_path,
        required_fingerprint=_fingerprint(),
    )

    assert not evidence.fresh


def test_missing_required_fingerprint_is_not_fresh(
    tmp_path: Path,
) -> None:
    """
    Freshness cannot be established without the current build context.
    """

    (tmp_path / "layers.svg").write_text(
        "product",
        encoding="utf-8",
    )

    _write_completion(
        tmp_path,
        fingerprint=_fingerprint(),
    )

    evidence = _gather(
        tmp_path,
        required_fingerprint=None,
    )

    assert not evidence.fresh


def test_missing_both_fingerprints_is_not_fresh(
    tmp_path: Path,
) -> None:
    """
    Absence of provenance never implies freshness.
    """

    (tmp_path / "layers.svg").write_text(
        "product",
        encoding="utf-8",
    )

    _write_completion(
        tmp_path,
        fingerprint=None,
    )

    evidence = _gather(
        tmp_path,
        required_fingerprint=None,
    )

    assert not evidence.fresh


def test_matching_fingerprint_without_completion_for_product_is_not_fresh(
    tmp_path: Path,
) -> None:
    """
    Stage provenance cannot establish freshness for an unlisted product.
    """

    (tmp_path / "layers.svg").write_text(
        "product",
        encoding="utf-8",
    )

    fingerprint = _fingerprint()

    _write_completion(
        tmp_path,
        products=("manifest",),
        fingerprint=fingerprint,
    )

    evidence = _gather(
        tmp_path,
        required_fingerprint=fingerprint,
    )

    assert not evidence.completion_exists
    assert not evidence.fresh


def test_matching_fingerprint_for_invalid_product_is_not_fresh(
    tmp_path: Path,
) -> None:
    """
    Provenance cannot make an invalid materialization fresh.
    """

    (tmp_path / "layers.svg").mkdir()

    fingerprint = _fingerprint()

    _write_completion(
        tmp_path,
        fingerprint=fingerprint,
    )

    evidence = _gather(
        tmp_path,
        required_fingerprint=fingerprint,
    )

    assert evidence.exists
    assert not evidence.valid
    assert evidence.completion_exists
    assert not evidence.fresh


def test_matching_fingerprint_for_missing_product_is_not_fresh(
    tmp_path: Path,
) -> None:
    """
    Provenance cannot make an absent materialization fresh.
    """

    fingerprint = _fingerprint()

    _write_completion(
        tmp_path,
        fingerprint=fingerprint,
    )

    evidence = _gather(
        tmp_path,
        required_fingerprint=fingerprint,
    )

    assert not evidence.exists
    assert not evidence.valid
    assert evidence.completion_exists
    assert not evidence.fresh


# =========================================================
# Complete evidence
# =========================================================


def test_current_product_evidence(
    tmp_path: Path,
) -> None:
    """
    A valid completed product with matching provenance is fully current.
    """

    (tmp_path / "layers.svg").write_text(
        "product",
        encoding="utf-8",
    )

    fingerprint = _fingerprint()

    _write_completion(
        tmp_path,
        fingerprint=fingerprint,
    )

    assert _gather(
        tmp_path,
        required_fingerprint=fingerprint,
    ) == ProductEvidence(
        exists=True,
        completion_exists=True,
        valid=True,
        fresh=True,
    )


def test_stale_product_evidence(
    tmp_path: Path,
) -> None:
    """
    A valid completed product with changed provenance is stale evidence.
    """

    (tmp_path / "layers.svg").write_text(
        "product",
        encoding="utf-8",
    )

    _write_completion(
        tmp_path,
        fingerprint=_fingerprint(
            "old",
        ),
    )

    assert _gather(
        tmp_path,
        required_fingerprint=_fingerprint(
            "new",
        ),
    ) == ProductEvidence(
        exists=True,
        completion_exists=True,
        valid=True,
        fresh=False,
    )


# =========================================================
# Invalid completion metadata
# =========================================================


def test_corrupt_completion_metadata_is_not_treated_as_absent(
    tmp_path: Path,
) -> None:
    """
    Corrupt persistent metadata remains distinguishable from absence.
    """

    (tmp_path / "layers.svg").write_text(
        "product",
        encoding="utf-8",
    )

    completion_path(
        tmp_path,
    ).write_text(
        "{not valid json",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
    ):
        _gather(
            tmp_path,
            required_fingerprint=_fingerprint(),
        )
