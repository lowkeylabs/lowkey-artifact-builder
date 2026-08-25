"""
Tests for execution product-state resolution.

Execution product-state resolution adapts realized build-plan stages and
products to persistent product-state evaluation.

The resolver determines the producing stage working directory, resolves
the declared product path, obtains the fingerprint required by the current
build context, and delegates persistent state evaluation to the evidence
layer.

These tests exercise execution-planning orchestration only. They do not
execute stages, emit execution events, or modify build products except
where persistent evidence is required by the test.
"""
# File: tests/engine/test_execution_state_resolver.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from lowkey_artifact_builder.engine import (
    BuildPlan,
    PlannedStage,
    ProductFingerprint,
    ProductState,
    StageCompletion,
    create_execution_state_resolver,
    write_stage_completion,
)

type ArtworkPlanFactory = Callable[..., BuildPlan]


# =========================================================
# Helpers
# =========================================================


def _fingerprint(
    value: str = "required",
) -> ProductFingerprint:
    """
    Create one representative build-context fingerprint.
    """

    return ProductFingerprint(
        algorithm="sha256",
        value=value,
    )


def _first_product_stage(
    build_plan: BuildPlan,
) -> PlannedStage:
    """
    Return the first realized stage declaring a persistent product.
    """

    return next(stage for stage in build_plan.stages if stage.products)


def _stage_working_dir(
    build_plan: BuildPlan,
    stage: PlannedStage,
) -> Path:
    """
    Return the expected working directory for one realized stage.

    Build-plan products already carry their realized filesystem locations,
    so use the parent of the first declared product as the authoritative
    stage working directory.
    """

    return stage.products[0].path.parent


def _completion(
    build_plan: BuildPlan,
    stage: PlannedStage,
    *,
    fingerprint: ProductFingerprint | None,
) -> StageCompletion:
    """
    Create completion metadata matching one realized stage.
    """

    return StageCompletion(
        artifact_id=build_plan.artifact_id,
        model_name=build_plan.model_name,
        realization=build_plan.realization_name,
        stage_name=stage.name,
        products=tuple(product.name for product in stage.products),
        fingerprint=fingerprint,
    )


# =========================================================
# Resolver construction
# =========================================================


def test_execution_state_resolver_returns_callable(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Execution state resolution is exposed through a reusable resolver.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    resolve = create_execution_state_resolver(
        build_plan,
        required_fingerprint=lambda stage: _fingerprint(
            stage.name,
        ),
    )

    assert callable(resolve)


# =========================================================
# Product resolution
# =========================================================


def test_missing_product_resolves_absent(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    A declared product without persistent materialization is ABSENT.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    stage = _first_product_stage(
        build_plan,
    )
    product = stage.products[0]

    resolve = create_execution_state_resolver(
        build_plan,
        required_fingerprint=lambda stage: _fingerprint(
            stage.name,
        ),
    )

    assert (
        resolve(
            stage,
            product.name,
        )
        is ProductState.ABSENT
    )


def test_current_product_resolves_current(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Matching persistent completion provenance resolves CURRENT.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    stage = _first_product_stage(
        build_plan,
    )
    product = stage.products[0]

    fingerprint = _fingerprint(
        stage.name,
    )

    working_dir = _stage_working_dir(
        build_plan,
        stage,
    )
    working_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    product.path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    product.path.write_text(
        "product",
        encoding="utf-8",
    )

    write_stage_completion(
        working_dir,
        _completion(
            build_plan,
            stage,
            fingerprint=fingerprint,
        ),
    )

    resolve = create_execution_state_resolver(
        build_plan,
        required_fingerprint=lambda candidate: _fingerprint(
            candidate.name,
        ),
    )

    assert (
        resolve(
            stage,
            product.name,
        )
        is ProductState.CURRENT
    )


def test_changed_required_fingerprint_resolves_stale(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Changed current build context makes completed persistent work STALE.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    stage = _first_product_stage(
        build_plan,
    )
    product = stage.products[0]

    working_dir = _stage_working_dir(
        build_plan,
        stage,
    )
    working_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    product.path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    product.path.write_text(
        "product",
        encoding="utf-8",
    )

    write_stage_completion(
        working_dir,
        _completion(
            build_plan,
            stage,
            fingerprint=_fingerprint(
                "recorded",
            ),
        ),
    )

    resolve = create_execution_state_resolver(
        build_plan,
        required_fingerprint=lambda stage: _fingerprint(
            "required",
        ),
    )

    assert (
        resolve(
            stage,
            product.name,
        )
        is ProductState.STALE
    )


def test_product_without_completion_resolves_incomplete(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Existing materialization without successful completion is INCOMPLETE.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    stage = _first_product_stage(
        build_plan,
    )
    product = stage.products[0]

    product.path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    product.path.write_text(
        "product",
        encoding="utf-8",
    )

    resolve = create_execution_state_resolver(
        build_plan,
        required_fingerprint=lambda stage: _fingerprint(
            stage.name,
        ),
    )

    assert (
        resolve(
            stage,
            product.name,
        )
        is ProductState.INCOMPLETE
    )


# =========================================================
# Product identity
# =========================================================


def test_unknown_product_is_rejected(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Resolution is limited to products declared by the realized stage.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    stage = _first_product_stage(
        build_plan,
    )

    resolve = create_execution_state_resolver(
        build_plan,
        required_fingerprint=lambda stage: _fingerprint(
            stage.name,
        ),
    )

    with pytest.raises(
        ValueError,
        match="product",
    ):
        resolve(
            stage,
            "not-a-product",
        )


def test_stage_outside_build_plan_is_rejected(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Resolution is limited to stages belonging to the supplied BuildPlan.
    """

    first_plan = artwork_plan(
        tmp_path / "first",
        monkeypatch,
    )

    second_plan = artwork_plan(
        tmp_path / "second",
        monkeypatch,
    )

    foreign_stage = _first_product_stage(
        second_plan,
    )

    resolve = create_execution_state_resolver(
        first_plan,
        required_fingerprint=lambda stage: _fingerprint(
            stage.name,
        ),
    )

    with pytest.raises(
        ValueError,
        match="Stage does not belong to build plan",
    ):
        resolve(
            foreign_stage,
            foreign_stage.products[0].name,
        )


# =========================================================
# Fingerprint resolution
# =========================================================


def test_required_fingerprint_is_resolved_for_stage(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Required provenance is resolved from the realized producing stage.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    stage = _first_product_stage(
        build_plan,
    )
    product = stage.products[0]

    calls: list[PlannedStage] = []

    def required_fingerprint(
        candidate: PlannedStage,
    ) -> ProductFingerprint:
        calls.append(
            candidate,
        )

        return _fingerprint(
            candidate.name,
        )

    resolve = create_execution_state_resolver(
        build_plan,
        required_fingerprint=required_fingerprint,
    )

    resolve(
        stage,
        product.name,
    )

    assert calls == [
        stage,
    ]


def test_missing_required_fingerprint_cannot_prove_current(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Completion provenance cannot prove CURRENT without required provenance.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    stage = _first_product_stage(
        build_plan,
    )
    product = stage.products[0]

    fingerprint = _fingerprint(
        stage.name,
    )

    working_dir = _stage_working_dir(
        build_plan,
        stage,
    )
    working_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    product.path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    product.path.write_text(
        "product",
        encoding="utf-8",
    )

    write_stage_completion(
        working_dir,
        _completion(
            build_plan,
            stage,
            fingerprint=fingerprint,
        ),
    )

    resolve = create_execution_state_resolver(
        build_plan,
        required_fingerprint=lambda stage: None,
    )

    assert (
        resolve(
            stage,
            product.name,
        )
        is ProductState.STALE
    )
