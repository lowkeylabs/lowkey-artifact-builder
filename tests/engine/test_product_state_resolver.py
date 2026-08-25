"""
Tests for persistent product-state resolution.

Product-state resolution combines expected product locations, persistent
completion metadata, and required build-context fingerprints into semantic
ProductState values suitable for execution planning.

These tests exercise the bridge between evidence gathering, freshness,
and execution planning. They do not execute stages or mutate completion
metadata except where required to establish persistent test evidence.
"""
# File: tests/engine/test_product_state_resolver.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path

from lowkey_artifact_builder.engine import (
    ProductFingerprint,
    ProductState,
    StageCompletion,
    create_product_state_resolver,
    write_stage_completion,
)

# =========================================================
# Helpers
# =========================================================


def _fingerprint(
    value: str = "required",
) -> ProductFingerprint:
    """
    Create one representative product fingerprint.
    """

    return ProductFingerprint(
        algorithm="sha256",
        value=value,
    )


def _completion(
    *,
    product_name: str = "trace.svg",
    fingerprint: ProductFingerprint | None = None,
) -> StageCompletion:
    """
    Create representative stage completion metadata.
    """

    return StageCompletion(
        artifact_id="example",
        model_name="artwork",
        realization="default",
        stage_name="prepare",
        products=(product_name,),
        fingerprint=fingerprint,
    )


def _working_dir(
    tmp_path: Path,
) -> Path:
    """
    Create one representative stage working directory.
    """

    working_dir = tmp_path / "10-prepare"
    working_dir.mkdir()

    return working_dir


# =========================================================
# Product-state resolution
# =========================================================


def test_missing_product_resolves_absent(
    tmp_path: Path,
) -> None:
    """
    Missing persistent materialization resolves to ABSENT.
    """

    working_dir = _working_dir(
        tmp_path,
    )

    resolve = create_product_state_resolver(
        working_dir=working_dir,
        required_fingerprints={
            "trace.svg": _fingerprint(),
        },
    )

    assert (
        resolve(
            "trace.svg",
            Path("trace.svg"),
        )
        is ProductState.ABSENT
    )


def test_product_without_completion_resolves_incomplete(
    tmp_path: Path,
) -> None:
    """
    Existing materialization without completion evidence is INCOMPLETE.
    """

    working_dir = _working_dir(
        tmp_path,
    )

    (working_dir / "trace.svg").write_text(
        "<svg/>",
        encoding="utf-8",
    )

    resolve = create_product_state_resolver(
        working_dir=working_dir,
        required_fingerprints={
            "trace.svg": _fingerprint(),
        },
    )

    assert (
        resolve(
            "trace.svg",
            Path("trace.svg"),
        )
        is ProductState.INCOMPLETE
    )


def test_nonfile_product_resolves_invalid(
    tmp_path: Path,
) -> None:
    """
    A completed product whose materialization is not a file is INVALID.
    """

    working_dir = _working_dir(
        tmp_path,
    )

    (working_dir / "trace.svg").mkdir()

    write_stage_completion(
        working_dir,
        _completion(
            fingerprint=_fingerprint(),
        ),
    )

    resolve = create_product_state_resolver(
        working_dir=working_dir,
        required_fingerprints={
            "trace.svg": _fingerprint(),
        },
    )

    assert (
        resolve(
            "trace.svg",
            Path("trace.svg"),
        )
        is ProductState.INVALID
    )


def test_completed_product_without_recorded_fingerprint_resolves_stale(
    tmp_path: Path,
) -> None:
    """
    Completion without provenance cannot prove the product CURRENT.
    """

    working_dir = _working_dir(
        tmp_path,
    )

    (working_dir / "trace.svg").write_text(
        "<svg/>",
        encoding="utf-8",
    )

    write_stage_completion(
        working_dir,
        _completion(),
    )

    resolve = create_product_state_resolver(
        working_dir=working_dir,
        required_fingerprints={
            "trace.svg": _fingerprint(),
        },
    )

    assert (
        resolve(
            "trace.svg",
            Path("trace.svg"),
        )
        is ProductState.STALE
    )


def test_mismatched_fingerprint_resolves_stale(
    tmp_path: Path,
) -> None:
    """
    A valid completed product with old provenance is STALE.
    """

    working_dir = _working_dir(
        tmp_path,
    )

    (working_dir / "trace.svg").write_text(
        "<svg/>",
        encoding="utf-8",
    )

    write_stage_completion(
        working_dir,
        _completion(
            fingerprint=_fingerprint(
                "recorded",
            ),
        ),
    )

    resolve = create_product_state_resolver(
        working_dir=working_dir,
        required_fingerprints={
            "trace.svg": _fingerprint(
                "required",
            ),
        },
    )

    assert (
        resolve(
            "trace.svg",
            Path("trace.svg"),
        )
        is ProductState.STALE
    )


def test_matching_fingerprint_resolves_current(
    tmp_path: Path,
) -> None:
    """
    Matching recorded and required provenance proves CURRENT.
    """

    working_dir = _working_dir(
        tmp_path,
    )

    fingerprint = _fingerprint()

    (working_dir / "trace.svg").write_text(
        "<svg/>",
        encoding="utf-8",
    )

    write_stage_completion(
        working_dir,
        _completion(
            fingerprint=fingerprint,
        ),
    )

    resolve = create_product_state_resolver(
        working_dir=working_dir,
        required_fingerprints={
            "trace.svg": fingerprint,
        },
    )

    assert (
        resolve(
            "trace.svg",
            Path("trace.svg"),
        )
        is ProductState.CURRENT
    )


def test_missing_required_fingerprint_cannot_prove_current(
    tmp_path: Path,
) -> None:
    """
    Recorded provenance alone cannot prove current build-context freshness.
    """

    working_dir = _working_dir(
        tmp_path,
    )

    fingerprint = _fingerprint()

    (working_dir / "trace.svg").write_text(
        "<svg/>",
        encoding="utf-8",
    )

    write_stage_completion(
        working_dir,
        _completion(
            fingerprint=fingerprint,
        ),
    )

    resolve = create_product_state_resolver(
        working_dir=working_dir,
        required_fingerprints={},
    )

    assert (
        resolve(
            "trace.svg",
            Path("trace.svg"),
        )
        is ProductState.STALE
    )


def test_completion_for_different_product_does_not_apply(
    tmp_path: Path,
) -> None:
    """
    Stage completion proves completion only for explicitly listed products.
    """

    working_dir = _working_dir(
        tmp_path,
    )

    (working_dir / "mask.svg").write_text(
        "<svg/>",
        encoding="utf-8",
    )

    write_stage_completion(
        working_dir,
        _completion(
            product_name="trace.svg",
            fingerprint=_fingerprint(),
        ),
    )

    resolve = create_product_state_resolver(
        working_dir=working_dir,
        required_fingerprints={
            "mask.svg": _fingerprint(),
        },
    )

    assert (
        resolve(
            "mask.svg",
            Path("mask.svg"),
        )
        is ProductState.INCOMPLETE
    )


# =========================================================
# Resolver independence
# =========================================================


def test_resolver_evaluates_products_independently(
    tmp_path: Path,
) -> None:
    """
    One resolver may produce different states for different products.
    """

    working_dir = _working_dir(
        tmp_path,
    )

    fingerprint = _fingerprint()

    (working_dir / "trace.svg").write_text(
        "<svg/>",
        encoding="utf-8",
    )

    write_stage_completion(
        working_dir,
        _completion(
            product_name="trace.svg",
            fingerprint=fingerprint,
        ),
    )

    resolve = create_product_state_resolver(
        working_dir=working_dir,
        required_fingerprints={
            "trace.svg": fingerprint,
            "mask.svg": fingerprint,
        },
    )

    assert (
        resolve(
            "trace.svg",
            Path("trace.svg"),
        )
        is ProductState.CURRENT
    )

    assert (
        resolve(
            "mask.svg",
            Path("mask.svg"),
        )
        is ProductState.ABSENT
    )
