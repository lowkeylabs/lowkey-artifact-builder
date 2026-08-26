"""
Tests for build-plan fingerprint resolution.

Build-plan fingerprint resolution derives the fingerprint required by each
realized stage from that stage's operation identity, resolved parameters,
external input contents, and required fingerprints of its realized
dependency stages.

Stage parameters are declared by StageSpec and resolved through the
BuildPlan's authoritative realization Resolver.

Tests focused on parameter and dependency provenance materialize stable
external input content so external-input provenance remains constant while
the behavior under test varies.
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
    PlannedProductDependency,
    PlannedStage,
    ProductFingerprint,
    create_required_fingerprints,
)
from lowkey_artifact_builder.model import (
    ModelSpec,
    ProductDependencyBinding,
    ProductDependencySpec,
    StageSpec,
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
) -> PlannedStage:
    """
    Return the first realized stage declaring at least one parameter.
    """

    for stage in build_plan.stages:
        if stage.spec.parameters:
            return stage

    raise AssertionError("Artwork build plan contains no stage declaring parameters.")


def _dependency_stage(
    build_plan: BuildPlan,
) -> PlannedStage:
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


def _materialize_external_inputs(
    build_plan: BuildPlan,
) -> None:
    """
    Materialize deterministic content for all declared external inputs.

    Build-plan fingerprint construction includes external input contents,
    so tests exercising parameter and dependency provenance must provide
    those required inputs.

    Identical content is used for every plan so workspace location cannot
    affect provenance.
    """

    for stage in build_plan.stages:
        for planned_input in stage.inputs:
            planned_input.path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            planned_input.path.write_bytes(
                b"fingerprint-planning-test-input",
            )


def _product_dependency_plan(
    *,
    tmp_path: Path,
    resolver,
    dependency_path: Path,
) -> BuildPlan:
    """
    Construct a minimal consumer build plan with one cross-artifact
    product dependency.
    """

    dependency = ProductDependencySpec(
        model="producer",
        stage="prepare",
        product="geometry",
    )

    binding = ProductDependencyBinding(
        dependency=dependency,
        artifact="producer-artifact",
        realization="default",
    )

    planned_dependency = PlannedProductDependency(
        binding=binding,
        path=dependency_path,
    )

    stage_spec = StageSpec(
        id=10,
        name="consume",
        product_dependencies=(dependency,),
    )

    stage = PlannedStage(
        spec=stage_spec,
    )

    return BuildPlan(
        artifact_id="consumer-artifact",
        model=ModelSpec(
            name="consumer",
            title="Consumer",
            stages=(stage_spec,),
        ),
        realization_name="default",
        resolver=resolver,
        project_root=tmp_path,
        artifact_dir=tmp_path / "artifacts" / "consumer-artifact",
        stages=(stage,),
        product_dependencies=(dependency,),
        product_dependency_bindings=(binding,),
        planned_product_dependencies=(planned_dependency,),
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

    _materialize_external_inputs(
        build_plan,
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

    _materialize_external_inputs(
        build_plan,
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

    _materialize_external_inputs(
        build_plan,
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

    _materialize_external_inputs(
        build_plan,
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

    _materialize_external_inputs(
        build_plan,
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

    _materialize_external_inputs(
        build_plan,
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

    _materialize_external_inputs(
        build_plan,
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

    _materialize_external_inputs(
        build_plan,
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

    _materialize_external_inputs(
        build_plan,
    )

    fingerprints = create_required_fingerprints(
        build_plan,
    )

    values = tuple(fingerprint.value for fingerprint in fingerprints.values())

    assert len(
        set(values),
    ) == len(
        values,
    )


# =========================================================
# Cross-artifact product dependency provenance
# =========================================================


def test_stage_fingerprint_depends_on_product_dependency_content(
    tmp_path: Path,
    test_resolver,
) -> None:
    """
    A consumer stage fingerprint includes the content of a required
    cross-artifact product.
    """

    dependency_path = tmp_path / "producer" / "geometry.dat"

    dependency_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    dependency_path.write_bytes(
        b"first-producer-product",
    )

    build_plan = _product_dependency_plan(
        tmp_path=tmp_path,
        resolver=test_resolver,
        dependency_path=dependency_path,
    )

    first = create_required_fingerprints(
        build_plan,
    )

    dependency_path.write_bytes(
        b"second-producer-product",
    )

    second = create_required_fingerprints(
        build_plan,
    )

    assert first["consume"] != second["consume"]


def test_identical_product_dependency_content_has_identical_fingerprint(
    tmp_path: Path,
    test_resolver,
) -> None:
    """
    Equivalent cross-artifact product content contributes equivalent
    provenance independently of its filesystem location.
    """

    first_path = tmp_path / "first" / "geometry.dat"
    second_path = tmp_path / "second" / "geometry.dat"

    first_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    second_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    first_path.write_bytes(
        b"same-producer-product",
    )

    second_path.write_bytes(
        b"same-producer-product",
    )

    first_plan = _product_dependency_plan(
        tmp_path=tmp_path / "first-plan",
        resolver=test_resolver,
        dependency_path=first_path,
    )

    second_plan = _product_dependency_plan(
        tmp_path=tmp_path / "second-plan",
        resolver=test_resolver,
        dependency_path=second_path,
    )

    first = create_required_fingerprints(
        first_plan,
    )

    second = create_required_fingerprints(
        second_plan,
    )

    assert first["consume"] == second["consume"]


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

    _materialize_external_inputs(
        first_plan,
    )

    _materialize_external_inputs(
        second_plan,
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
