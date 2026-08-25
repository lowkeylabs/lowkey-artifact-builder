"""
Tests for build-plan fingerprint resolution.

Build-plan fingerprint resolution derives the fingerprint required by each
realized stage from that stage's operation identity, resolved parameters,
and required fingerprints of its realized dependency stages.

Stage parameters are declared by StageSpec and resolved through the
BuildPlan's authoritative realization Resolver.

External filesystem input content provenance is intentionally outside this
slice and is introduced separately.
"""
# File: tests/engine/test_fingerprint_planning.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from lowkey_artifact_builder.engine import (
    BuildPlan,
    ProductFingerprint,
    create_required_fingerprints,
)

type ArtworkPlanFactory = Callable[..., BuildPlan]


# =========================================================
# Helpers
# =========================================================


def _fingerprint_values(
    fingerprints: dict[str, ProductFingerprint],
) -> dict[str, str]:
    """
    Return fingerprint values keyed by realized stage name.
    """

    return {stage_name: fingerprint.value for stage_name, fingerprint in fingerprints.items()}


def _parameter_stage(
    build_plan: BuildPlan,
):
    """
    Return the first realized stage declaring at least one parameter.
    """

    for stage in build_plan.stages:
        if stage.spec.parameters:
            return stage

    raise AssertionError("Artwork build plan contains no stage declaring parameters.")


def _dependency_stage(
    build_plan: BuildPlan,
):
    """
    Return the first realized stage declaring at least one dependency.
    """

    for stage in build_plan.stages:
        if stage.spec.dependencies:
            return stage

    raise AssertionError("Artwork build plan contains no stage declaring dependencies.")


def _descendant_stage_names(
    build_plan: BuildPlan,
    stage_name: str,
) -> tuple[str, ...]:
    """
    Return realized stages transitively depending on stage_name.
    """

    descendants: list[str] = []
    reached = {stage_name}

    for stage in build_plan.stages:
        if any(dependency in reached for dependency in stage.spec.dependencies):
            reached.add(
                stage.name,
            )
            descendants.append(
                stage.name,
            )

    return tuple(
        descendants,
    )


# =========================================================
# Required fingerprint construction
# =========================================================


def test_required_fingerprints_include_every_realized_stage(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Required provenance is derived for every realized stage.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    fingerprints = create_required_fingerprints(
        build_plan,
    )

    assert tuple(
        fingerprints,
    ) == tuple(stage.name for stage in build_plan.stages)


def test_required_fingerprints_use_sha256(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Build-plan provenance uses the established fingerprint algorithm.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    fingerprints = create_required_fingerprints(
        build_plan,
    )

    assert all(fingerprint.algorithm == "sha256" for fingerprint in fingerprints.values())


def test_required_fingerprints_are_deterministic(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Identical realized build context produces identical provenance.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    first = create_required_fingerprints(
        build_plan,
    )

    second = create_required_fingerprints(
        build_plan,
    )

    assert first == second


def test_required_fingerprints_preserve_stage_order(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Fingerprint results preserve realized build-plan stage order.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    fingerprints = create_required_fingerprints(
        build_plan,
    )

    assert tuple(
        fingerprints,
    ) == tuple(stage.name for stage in build_plan.stages)


# =========================================================
# Resolved parameters
# =========================================================


def test_stage_fingerprint_depends_on_declared_resolved_parameters(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    A stage fingerprint depends on values of its declared parameters.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    stage = _parameter_stage(
        build_plan,
    )

    parameter = stage.spec.parameters[0]

    original_resolver = build_plan.resolver
    original_value = original_resolver(
        parameter,
    )

    first = create_required_fingerprints(
        build_plan,
    )

    def changed_resolver(
        name: str,
    ):
        if name == parameter:
            return {
                "original": original_value,
                "changed": True,
            }

        return original_resolver(
            name,
        )

    object.__setattr__(
        build_plan,
        "resolver",
        changed_resolver,
    )

    second = create_required_fingerprints(
        build_plan,
    )

    assert first[stage.name] != second[stage.name]


def test_stage_fingerprint_ignores_undeclared_parameter(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Resolver values not declared by a stage do not affect its fingerprint.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    stage = _parameter_stage(
        build_plan,
    )

    original_resolver = build_plan.resolver

    first = create_required_fingerprints(
        build_plan,
    )

    def changed_resolver(
        name: str,
    ):
        if name == "__undeclared_test_parameter__":
            return "changed"

        return original_resolver(
            name,
        )

    object.__setattr__(
        build_plan,
        "resolver",
        changed_resolver,
    )

    second = create_required_fingerprints(
        build_plan,
    )

    assert first[stage.name] == second[stage.name]


# =========================================================
# Dependency propagation
# =========================================================


def test_dependency_stage_has_required_fingerprint(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Every dependency referenced by a realized stage has provenance.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    stage = _dependency_stage(
        build_plan,
    )

    fingerprints = create_required_fingerprints(
        build_plan,
    )

    assert all(dependency in fingerprints for dependency in stage.spec.dependencies)


def test_changed_stage_parameter_propagates_to_descendants(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Changed stage context changes provenance of dependent descendants.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    stage = _parameter_stage(
        build_plan,
    )

    descendants = _descendant_stage_names(
        build_plan,
        stage.name,
    )

    if not descendants:
        pytest.skip("Selected parameter-consuming stage has no realized descendants.")

    parameter = stage.spec.parameters[0]

    original_resolver = build_plan.resolver
    original_value = original_resolver(
        parameter,
    )

    first = create_required_fingerprints(
        build_plan,
    )

    def changed_resolver(
        name: str,
    ):
        if name == parameter:
            return {
                "original": original_value,
                "changed": True,
            }

        return original_resolver(
            name,
        )

    object.__setattr__(
        build_plan,
        "resolver",
        changed_resolver,
    )

    second = create_required_fingerprints(
        build_plan,
    )

    assert first[stage.name] != second[stage.name]

    for descendant in descendants:
        assert first[descendant] != second[descendant]


def test_dependency_fingerprints_distinguish_stage_contexts(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Different realized stage contexts do not collapse to one fingerprint.
    """

    build_plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    fingerprints = create_required_fingerprints(
        build_plan,
    )

    values = tuple(fingerprint.value for fingerprint in fingerprints.values())

    assert len(
        set(values),
    ) == len(values)


# =========================================================
# Workspace independence
# =========================================================


def test_required_fingerprints_do_not_depend_on_workspace_location(
    artwork_plan: ArtworkPlanFactory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Equivalent realized configuration has location-independent provenance.
    """

    first_plan = artwork_plan(
        tmp_path / "first",
        monkeypatch,
    )

    second_plan = artwork_plan(
        tmp_path / "second",
        monkeypatch,
    )

    first = create_required_fingerprints(
        first_plan,
    )

    second = create_required_fingerprints(
        second_plan,
    )

    assert _fingerprint_values(
        first,
    ) == _fingerprint_values(
        second,
    )
