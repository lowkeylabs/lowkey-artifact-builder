"""
Tests for the common stage execution contract.

These tests verify that graph-driven builds and explicit independent
stage execution converge on the same StageContext-based execution
boundary.

They intentionally test the relationship between the two execution
modes rather than duplicating the detailed behavior already covered by
test_build.py, test_stage_operation.py, and test_stage.py.
"""
# File: tests/engine/test_stage_contract.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path

import pytest

from lowkey_artifact_builder.config import Resolver
from lowkey_artifact_builder.engine import (
    BuildError,
    StageContext,
    create_stage_context,
    execute_artifact_stage,
    execute_build,
)

# =========================================================
# Helpers
# =========================================================


def _create_source(
    project_root: Path,
) -> Path:
    """
    Create the standard external artwork source.
    """

    source = project_root / "source.png"

    source.write_bytes(
        b"source artwork",
    )

    return source


def _create_declared_outputs(
    context: StageContext,
) -> None:
    """
    Materialize every output declared by one StageContext.
    """

    for path in context.outputs.values():
        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        path.write_bytes(
            b"product",
        )


def _create_inputs(
    context: StageContext,
) -> None:
    """
    Materialize every input required by one StageContext.
    """

    for path in context.inputs.values():
        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        path.write_bytes(
            b"input",
        )


def _prepare_independent_stage(
    context: StageContext,
) -> None:
    """
    Prepare the filesystem required for independent stage execution.

    Independent context resolution is read-only and does not create the
    stage working directory or materialize dependency products. Tests
    exercising real independent execution therefore prepare those
    resources explicitly.
    """

    context.working_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    _create_inputs(
        context,
    )


def _install_implementation(
    monkeypatch: pytest.MonkeyPatch,
    implementation,
) -> None:
    """
    Install one implementation for every artwork stage.

    execute_stage() obtains a fresh registry through build_stage_registry(),
    so replacing that registry factory exercises the real common execution
    boundary without invoking model-specific artwork transformations.
    """

    from lowkey_artifact_builder.engine.registry import (
        StageRegistry,
    )

    registry = StageRegistry()

    for stage_name in (
        "prepare",
        "raster",
        "vector",
        "extrude",
        "package",
    ):
        registry.register(
            "artwork",
            stage_name,
            implementation,
        )

    monkeypatch.setattr(
        "lowkey_artifact_builder.engine.stage.build_stage_registry",
        lambda: registry,
    )


def _install_context_resolver(
    monkeypatch: pytest.MonkeyPatch,
    *,
    project_root: Path,
    resolver: Resolver,
) -> None:
    """
    Install the resolver used by independent context resolution.
    """

    project_root_value = project_root

    def get_resolver(
        artifact_id: str,
        *,
        realization: str | None = None,
        project_root: Path,
    ) -> Resolver:
        assert artifact_id == "example"
        assert realization is None
        assert project_root == project_root_value

        return resolver

    monkeypatch.setattr(
        "lowkey_artifact_builder.engine.context.get_resolver",
        get_resolver,
    )


# =========================================================
# Common implementation contract
# =========================================================


def test_graph_and_independent_execution_use_stage_context(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    artwork_plan,
    test_resolver: Resolver,
) -> None:
    """
    Both execution modes invoke implementations with StageContext.
    """

    _create_source(
        tmp_path,
    )

    plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    _install_context_resolver(
        monkeypatch,
        project_root=tmp_path,
        resolver=test_resolver,
    )

    observed: list[
        tuple[
            str,
            StageContext,
        ]
    ] = []

    mode = "graph"

    def implementation(
        context: StageContext,
    ) -> None:
        assert isinstance(
            context,
            StageContext,
        )

        observed.append(
            (
                mode,
                context,
            )
        )

        _create_declared_outputs(
            context,
        )

    _install_implementation(
        monkeypatch,
        implementation,
    )

    execute_build(
        plan,
    )

    vector_context = next(
        context
        for observed_mode, context in observed
        if (observed_mode == "graph" and context.stage_name == "vector")
    )

    mode = "independent"

    execute_artifact_stage(
        "example",
        stage_name="vector",
        project_root=tmp_path,
    )

    independent_contexts = [
        context for observed_mode, context in observed if observed_mode == "independent"
    ]

    assert len(independent_contexts) == 1

    independent_context = independent_contexts[0]

    assert vector_context.artifact_id == (independent_context.artifact_id)

    assert vector_context.model_name == (independent_context.model_name)

    assert vector_context.stage_name == (independent_context.stage_name)

    assert vector_context.project_root == (independent_context.project_root)

    assert vector_context.artifact_dir == (independent_context.artifact_dir)

    assert vector_context.working_dir == (independent_context.working_dir)

    assert vector_context.inputs == (independent_context.inputs)

    assert vector_context.outputs == (independent_context.outputs)


def test_graph_and_independent_execution_use_same_registry_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    artwork_plan,
    test_resolver: Resolver,
) -> None:
    """
    Both execution modes dispatch through the registered implementation.
    """

    _create_source(
        tmp_path,
    )

    plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    _install_context_resolver(
        monkeypatch,
        project_root=tmp_path,
        resolver=test_resolver,
    )

    executed: list[str] = []

    def implementation(
        context: StageContext,
    ) -> None:
        executed.append(
            context.stage_name,
        )

        _create_declared_outputs(
            context,
        )

    _install_implementation(
        monkeypatch,
        implementation,
    )

    execute_build(
        plan,
    )

    assert executed == [
        "prepare",
        "raster",
        "vector",
        "extrude",
        "package",
    ]

    executed.clear()

    execute_artifact_stage(
        "example",
        stage_name="vector",
        project_root=tmp_path,
    )

    assert executed == [
        "vector",
    ]


# =========================================================
# Dependency independence
# =========================================================


def test_independent_execution_uses_existing_dependency_products(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    test_resolver: Resolver,
) -> None:
    """
    Existing dependency products permit execution of only the target stage.
    """

    _install_context_resolver(
        monkeypatch,
        project_root=tmp_path,
        resolver=test_resolver,
    )

    executed: list[str] = []

    def implementation(
        context: StageContext,
    ) -> None:
        executed.append(
            context.stage_name,
        )

        _create_declared_outputs(
            context,
        )

    _install_implementation(
        monkeypatch,
        implementation,
    )

    context = create_stage_context(
        "example",
        stage_name="vector",
        project_root=tmp_path,
    )

    _prepare_independent_stage(
        context,
    )

    execute_artifact_stage(
        "example",
        stage_name="vector",
        project_root=tmp_path,
    )

    assert executed == [
        "vector",
    ]


def test_independent_execution_does_not_realize_missing_dependency(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    test_resolver: Resolver,
) -> None:
    """
    A missing dependency product fails without executing any stage.
    """

    _install_context_resolver(
        monkeypatch,
        project_root=tmp_path,
        resolver=test_resolver,
    )

    executed: list[str] = []

    def implementation(
        context: StageContext,
    ) -> None:
        executed.append(
            context.stage_name,
        )

        _create_declared_outputs(
            context,
        )

    _install_implementation(
        monkeypatch,
        implementation,
    )

    with pytest.raises(
        BuildError,
        match="does not exist",
    ):
        execute_artifact_stage(
            "example",
            stage_name="vector",
            project_root=tmp_path,
        )

    assert executed == []


# =========================================================
# Explicit execution bindings
# =========================================================


def test_independent_execution_uses_explicit_dependency_input(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    test_resolver: Resolver,
) -> None:
    """
    A bound dependency product is supplied directly to the implementation.

    Other declared dependency products remain required at their resolved
    paths.
    """

    _install_context_resolver(
        monkeypatch,
        project_root=tmp_path,
        resolver=test_resolver,
    )

    prepare_dir = tmp_path / "artifacts" / "example" / "artwork" / "default" / "10-prepare"

    prepare_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    (prepare_dir / "trace.svg").write_text(
        "<svg/>",
        encoding="utf-8",
    )

    (prepare_dir / "envelope.svg").write_text(
        "<svg/>",
        encoding="utf-8",
    )

    explicit_input = tmp_path / "external" / "raster-products.json"

    explicit_input.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    explicit_input.write_text(
        "{}",
        encoding="utf-8",
    )

    observed: Path | None = None

    def implementation(
        context: StageContext,
    ) -> None:
        nonlocal observed

        observed = context.inputs["raster.manifest"]

        _create_declared_outputs(
            context,
        )

    _install_implementation(
        monkeypatch,
        implementation,
    )

    context = create_stage_context(
        "example",
        stage_name="vector",
        project_root=tmp_path,
        input_paths={
            "raster.manifest": explicit_input,
        },
    )

    context.working_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    execute_artifact_stage(
        "example",
        stage_name="vector",
        project_root=tmp_path,
        input_paths={
            "raster.manifest": explicit_input,
        },
    )

    assert observed == explicit_input


def test_independent_execution_exposes_parameter_override(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    test_resolver: Resolver,
) -> None:
    """
    Explicit parameter values are visible through the stage resolver.
    """

    _install_context_resolver(
        monkeypatch,
        project_root=tmp_path,
        resolver=test_resolver,
    )

    observed: int | None = None

    def implementation(
        context: StageContext,
    ) -> None:
        nonlocal observed

        observed = context.resolver("artwork_pixels")

        _create_declared_outputs(
            context,
        )

    _install_implementation(
        monkeypatch,
        implementation,
    )

    context = create_stage_context(
        "example",
        stage_name="raster",
        project_root=tmp_path,
        parameter_values={
            "artwork_pixels": 2048,
        },
    )

    _prepare_independent_stage(
        context,
    )

    execute_artifact_stage(
        "example",
        stage_name="raster",
        project_root=tmp_path,
        parameter_values={
            "artwork_pixels": 2048,
        },
    )

    assert observed == 2048


def test_independent_execution_uses_explicit_output_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    test_resolver: Resolver,
) -> None:
    """
    Explicit output bindings become the implementation's declared outputs.
    """

    _install_context_resolver(
        monkeypatch,
        project_root=tmp_path,
        resolver=test_resolver,
    )

    explicit_output = tmp_path / "external" / "vector-products.json"

    observed: Path | None = None

    def implementation(
        context: StageContext,
    ) -> None:
        nonlocal observed

        observed = context.outputs["manifest"]

        _create_declared_outputs(
            context,
        )

    _install_implementation(
        monkeypatch,
        implementation,
    )

    context = create_stage_context(
        "example",
        stage_name="vector",
        project_root=tmp_path,
        output_paths={
            "manifest": explicit_output,
        },
    )

    _prepare_independent_stage(
        context,
    )

    execute_artifact_stage(
        "example",
        stage_name="vector",
        project_root=tmp_path,
        output_paths={
            "manifest": explicit_output,
        },
    )

    assert observed == explicit_output
    assert explicit_output.is_file()


def test_independent_execution_verifies_explicit_output_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    test_resolver: Resolver,
) -> None:
    """
    Product verification applies to an explicitly bound output location.
    """

    _install_context_resolver(
        monkeypatch,
        project_root=tmp_path,
        resolver=test_resolver,
    )

    explicit_output = tmp_path / "external" / "vector-products.json"

    def implementation(
        context: StageContext,
    ) -> None:
        # Deliberately produce nothing.
        pass

    _install_implementation(
        monkeypatch,
        implementation,
    )

    context = create_stage_context(
        "example",
        stage_name="vector",
        project_root=tmp_path,
        output_paths={
            "manifest": explicit_output,
        },
    )

    _prepare_independent_stage(
        context,
    )

    with pytest.raises(
        BuildError,
        match="did not produce declared product",
    ):
        execute_artifact_stage(
            "example",
            stage_name="vector",
            project_root=tmp_path,
            output_paths={
                "manifest": explicit_output,
            },
        )

    assert not explicit_output.exists()
