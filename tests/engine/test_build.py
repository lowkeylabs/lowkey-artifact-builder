"""
Tests for artifact build execution.

These tests verify workspace creation, external input materialization,
stage execution order, execution contexts, stage dispatch, failure
handling, and declared product verification.
"""
# File: tests/engine/test_build.py
# Copyright 2026 LowKeyLabs LLC
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path

import pytest

from lowkey_artifact_builder.engine import (
    BuildError,
    BuildPlan,
    StageContext,
    execute_artifact_stage,
    execute_build,
    execute_builds,
)
from lowkey_artifact_builder.engine.registry import StageRegistry
from lowkey_artifact_builder.engine.stage import (
    StageInputError,
)
from lowkey_artifact_builder.model import ProductRef

# =========================================================
# Build workspace
# =========================================================


def test_execute_build_creates_declared_workspace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    artwork_plan,
) -> None:
    """
    Execution creates the complete declared workspace before the first
    stage implementation runs.
    """

    _create_source(tmp_path)

    plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    expected = {
        plan.artifact_dir,
        plan.artifact_dir / "artwork",
        plan.artifact_dir / "artwork" / "default",
        plan.artifact_dir / "artwork" / "default" / "10-prepare",
        plan.artifact_dir / "artwork" / "default" / "20-raster",
        plan.artifact_dir / "artwork" / "default" / "30-vector",
        plan.artifact_dir / "artwork" / "default" / "40-extrude",
        plan.artifact_dir / "artwork" / "default" / "50-package",
    }

    observed: set[Path] = set()

    def implementation(
        context: StageContext,
    ) -> None:
        if context.stage_name == "prepare":
            observed.update(path for path in expected if path.is_dir())

        _create_declared_outputs(context)

    _install_stage_implementation(
        monkeypatch,
        implementation,
    )

    execute_build(plan)

    assert observed == expected


# =========================================================
# External input materialization
# =========================================================


def test_execute_build_materializes_external_input(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    artwork_plan,
) -> None:
    """
    Execution copies the configured external source into the
    artifact-owned materialization path before stage execution.
    """

    source = tmp_path / "source.png"
    source.write_bytes(b"source artwork")

    plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    materialized = plan.artifact_dir / "artifact.png"

    def implementation(
        context: StageContext,
    ) -> None:
        if context.stage_name == "prepare":
            assert materialized.is_file()

            assert materialized.read_bytes() == (b"source artwork")

        _create_declared_outputs(context)

    _install_stage_implementation(
        monkeypatch,
        implementation,
    )

    execute_build(plan)

    assert materialized.is_file()
    assert materialized.read_bytes() == b"source artwork"


def test_execute_build_prepare_receives_materialized_input(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    artwork_plan,
) -> None:
    """
    The prepare implementation receives the artifact-owned source path
    rather than the original project source path.
    """

    source = tmp_path / "source.png"
    source.touch()

    plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    observed: Path | None = None

    def implementation(
        context: StageContext,
    ) -> None:
        nonlocal observed

        if context.stage_name == "prepare":
            observed = context.input("source")

        _create_declared_outputs(context)

    _install_stage_implementation(
        monkeypatch,
        implementation,
    )

    execute_build(plan)

    assert observed == (plan.artifact_dir / "artifact.png")

    assert observed != source


def test_execute_build_rejects_missing_external_input(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    artwork_plan,
) -> None:
    """
    Execution fails before any stage runs when a required external
    filesystem input does not exist.
    """

    plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    executed: list[str] = []

    def implementation(
        context: StageContext,
    ) -> None:
        executed.append(context.stage_name)

        _create_declared_outputs(context)

    _install_stage_implementation(
        monkeypatch,
        implementation,
    )

    with pytest.raises(
        BuildError,
        match="does not exist",
    ):
        execute_build(plan)

    assert executed == []


# =========================================================
# Build execution order
# =========================================================


def test_execute_build_runs_stages_in_plan_order(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    artwork_plan,
) -> None:
    """
    Execution invokes model stages in the order established by the
    build plan.
    """

    _create_source(tmp_path)

    plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    executed: list[str] = []

    def implementation(
        context: StageContext,
    ) -> None:
        executed.append(context.stage_name)

        _create_declared_outputs(context)

    _install_stage_implementation(
        monkeypatch,
        implementation,
    )

    execute_build(plan)

    assert executed == [
        "prepare",
        "raster",
        "vector",
        "extrude",
        "package",
    ]


# =========================================================
# Product-targeted execution
# =========================================================


def test_execute_build_runs_only_target_dependency_closure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    artwork_plan,
) -> None:
    """
    Product-targeted execution runs only stages required by the target.

    Targeting vector/manifest executes prepare, raster, and vector.
    Downstream extrude and package stages do not execute.
    """

    _create_source(tmp_path)

    target = ProductRef(
        artifact="example",
        model="artwork",
        realization="default",
        stage="vector",
        product="manifest",
    )

    plan = artwork_plan(
        tmp_path,
        monkeypatch,
        targets=(target,),
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

    _install_stage_implementation(
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
    ]


def test_execute_build_target_does_not_create_downstream_workspace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    artwork_plan,
) -> None:
    """
    Product-targeted execution creates no workspace for omitted stages.

    Workspace materialization follows the realized BuildPlan rather than
    the complete Defined Graph.
    """

    _create_source(tmp_path)

    target = ProductRef(
        artifact="example",
        model="artwork",
        realization="default",
        stage="vector",
        product="manifest",
    )

    plan = artwork_plan(
        tmp_path,
        monkeypatch,
        targets=(target,),
    )

    def implementation(
        context: StageContext,
    ) -> None:
        _create_declared_outputs(
            context,
        )

    _install_stage_implementation(
        monkeypatch,
        implementation,
    )

    execute_build(
        plan,
    )

    realization_dir = plan.artifact_dir / "artwork" / "default"

    assert (realization_dir / "10-prepare").is_dir()

    assert (realization_dir / "20-raster").is_dir()

    assert (realization_dir / "30-vector").is_dir()

    assert not (realization_dir / "40-extrude").exists()

    assert not (realization_dir / "50-package").exists()


def test_execute_build_target_creates_target_and_dependency_products(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    artwork_plan,
) -> None:
    """
    Product-targeted execution produces the selected dependency closure.

    Required upstream products and the requested target product exist
    after execution, while products of omitted downstream stages do not.
    """

    _create_source(tmp_path)

    target = ProductRef(
        artifact="example",
        model="artwork",
        realization="default",
        stage="vector",
        product="manifest",
    )

    plan = artwork_plan(
        tmp_path,
        monkeypatch,
        targets=(target,),
    )

    def implementation(
        context: StageContext,
    ) -> None:
        _create_declared_outputs(
            context,
        )

    _install_stage_implementation(
        monkeypatch,
        implementation,
    )

    execute_build(
        plan,
    )

    realization_dir = plan.artifact_dir / "artwork" / "default"

    assert (realization_dir / "10-prepare" / "trace.svg").is_file()

    assert (realization_dir / "10-prepare" / "envelope.svg").is_file()

    assert (realization_dir / "20-raster" / "products.json").is_file()

    assert (realization_dir / "30-vector" / "products.json").is_file()

    assert not (realization_dir / "40-extrude" / "products.json").exists()

    assert not (realization_dir / "50-package" / "artifact.3mf").exists()


# =========================================================
# Stage working directories
# =========================================================


def test_execute_build_sets_stage_working_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    artwork_plan,
) -> None:
    """
    Each implementation executes from the directory containing its
    declared products.
    """

    _create_source(tmp_path)

    plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    observed: dict[
        str,
        Path,
    ] = {}

    def implementation(
        context: StageContext,
    ) -> None:
        observed[context.stage_name] = Path.cwd()

        assert Path.cwd() == context.working_dir

        _create_declared_outputs(context)

    _install_stage_implementation(
        monkeypatch,
        implementation,
    )

    execute_build(plan)

    assert observed == {
        "prepare": (plan.artifact_dir / "artwork" / "default" / "10-prepare"),
        "raster": (plan.artifact_dir / "artwork" / "default" / "20-raster"),
        "vector": (plan.artifact_dir / "artwork" / "default" / "30-vector"),
        "extrude": (plan.artifact_dir / "artwork" / "default" / "40-extrude"),
        "package": (plan.artifact_dir / "artwork" / "default" / "50-package"),
    }


def test_execute_build_restores_working_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    artwork_plan,
) -> None:
    """
    Execution restores the caller's working directory after a
    successful build.
    """

    _create_source(tmp_path)

    plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    original = Path.cwd()

    def implementation(
        context: StageContext,
    ) -> None:
        _create_declared_outputs(context)

    _install_stage_implementation(
        monkeypatch,
        implementation,
    )

    execute_build(plan)

    assert Path.cwd() == original


def test_execute_build_restores_working_directory_after_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    artwork_plan,
) -> None:
    """
    A failing implementation does not leave the process inside the
    artifact workspace.
    """

    _create_source(tmp_path)

    plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    original = Path.cwd()

    def implementation(
        context: StageContext,
    ) -> None:
        raise ValueError("boom")

    _install_stage_implementation(
        monkeypatch,
        implementation,
    )

    with pytest.raises(
        BuildError,
    ):
        execute_build(plan)

    assert Path.cwd() == original


# =========================================================
# Stage configuration
# =========================================================


def test_execute_build_context_uses_plan_resolver(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    artwork_plan,
) -> None:
    """
    Every stage receives the exact artifact resolver retained by the
    build plan.
    """

    _create_source(tmp_path)

    plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    observed: dict[
        str,
        object,
    ] = {}

    def implementation(
        context: StageContext,
    ) -> None:
        observed[context.stage_name] = context.resolver

        _create_declared_outputs(context)

    _install_stage_implementation(
        monkeypatch,
        implementation,
    )

    execute_build(plan)

    assert set(observed) == {
        "prepare",
        "raster",
        "vector",
        "extrude",
        "package",
    }

    assert all(resolver is plan.resolver for resolver in observed.values())


def test_execute_build_context_has_full_configuration_visibility(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    artwork_plan,
) -> None:
    """
    Stage parameter declarations describe normal dependencies but do
    not restrict access to the complete artifact configuration.
    """

    _create_source(tmp_path)

    plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    observed: dict[
        str,
        float,
    ] = {}

    def implementation(
        context: StageContext,
    ) -> None:
        observed[context.stage_name] = context.resolver("artwork_size")

        _create_declared_outputs(context)

    _install_stage_implementation(
        monkeypatch,
        implementation,
    )

    execute_build(plan)

    assert observed == {
        "prepare": 150.0,
        "raster": 150.0,
        "vector": 150.0,
        "extrude": 150.0,
        "package": 150.0,
    }


# =========================================================
# Stage inputs
# =========================================================


def test_execute_build_context_contains_external_input(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    artwork_plan,
) -> None:
    """
    Explicit external inputs are exposed using their declarative names
    and artifact-owned paths.
    """

    _create_source(tmp_path)

    plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    observed: dict[
        str,
        dict[str, Path],
    ] = {}

    def implementation(
        context: StageContext,
    ) -> None:
        observed[context.stage_name] = dict(context.inputs)

        _create_declared_outputs(context)

    _install_stage_implementation(
        monkeypatch,
        implementation,
    )

    execute_build(plan)

    assert observed["prepare"] == {
        "source": (plan.artifact_dir / "artifact.png"),
    }


def test_execute_build_context_contains_dependency_products(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    artwork_plan,
) -> None:
    """
    Stage contexts expose products from direct dependencies using
    qualified input names.
    """

    _create_source(tmp_path)

    plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    observed: dict[
        str,
        dict[str, Path],
    ] = {}

    def implementation(
        context: StageContext,
    ) -> None:
        observed[context.stage_name] = dict(context.inputs)

        _create_declared_outputs(context)

    _install_stage_implementation(
        monkeypatch,
        implementation,
    )

    execute_build(plan)

    assert observed["prepare"] == {
        "source": (plan.artifact_dir / "artifact.png"),
    }

    assert observed["raster"] == {
        "prepare.trace": (plan.artifact_dir / "artwork" / "default" / "10-prepare" / "trace.svg"),
        "prepare.envelope": (
            plan.artifact_dir / "artwork" / "default" / "10-prepare" / "envelope.svg"
        ),
    }

    assert observed["vector"] == {
        "raster.manifest": (
            plan.artifact_dir / "artwork" / "default" / "20-raster" / "products.json"
        ),
    }

    assert observed["extrude"] == {
        "vector.manifest": (
            plan.artifact_dir / "artwork" / "default" / "30-vector" / "products.json"
        ),
    }

    assert observed["package"] == {
        "extrude.manifest": (
            plan.artifact_dir / "artwork" / "default" / "40-extrude" / "products.json"
        ),
    }


# =========================================================
# Stage outputs
# =========================================================


def test_execute_build_context_contains_declared_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    artwork_plan,
) -> None:
    """
    Stage contexts expose current-stage products by declarative product
    name.
    """

    _create_source(tmp_path)

    plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    observed: dict[
        str,
        dict[str, Path],
    ] = {}

    def implementation(
        context: StageContext,
    ) -> None:
        observed[context.stage_name] = dict(context.outputs)

        _create_declared_outputs(context)

    _install_stage_implementation(
        monkeypatch,
        implementation,
    )

    execute_build(plan)

    assert observed["prepare"] == {
        "trace": (plan.artifact_dir / "artwork" / "default" / "10-prepare" / "trace.svg"),
        "envelope": (plan.artifact_dir / "artwork" / "default" / "10-prepare" / "envelope.svg"),
    }

    assert observed["raster"] == {
        "manifest": (plan.artifact_dir / "artwork" / "default" / "20-raster" / "products.json"),
    }

    assert observed["vector"] == {
        "manifest": (plan.artifact_dir / "artwork" / "default" / "30-vector" / "products.json"),
    }

    assert observed["extrude"] == {
        "manifest": (plan.artifact_dir / "artwork" / "default" / "40-extrude" / "products.json"),
    }

    assert observed["package"] == {
        "artifact": (plan.artifact_dir / "artwork" / "default" / "50-package" / "artifact.3mf"),
    }


# =========================================================
# Product verification
# =========================================================


def test_execute_build_rejects_missing_declared_product(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    artwork_plan,
) -> None:
    """
    A stage that returns without creating its declared product causes
    the build to fail immediately.
    """

    _create_source(tmp_path)

    plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    executed: list[str] = []

    def implementation(
        context: StageContext,
    ) -> None:
        executed.append(context.stage_name)

        if context.stage_name != "raster":
            _create_declared_outputs(context)

    _install_stage_implementation(
        monkeypatch,
        implementation,
    )

    with pytest.raises(
        BuildError,
        match="did not produce declared product",
    ):
        execute_build(plan)

    assert executed == [
        "prepare",
        "raster",
    ]


# =========================================================
# Stage failures
# =========================================================


def test_execute_build_stops_after_stage_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    artwork_plan,
) -> None:
    """
    An exception from a stage implementation stops the build and
    prevents later stages from executing.
    """

    _create_source(tmp_path)

    plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    executed: list[str] = []

    def implementation(
        context: StageContext,
    ) -> None:
        executed.append(context.stage_name)

        if context.stage_name == "vector":
            raise ValueError("vector failed")

        _create_declared_outputs(context)

    _install_stage_implementation(
        monkeypatch,
        implementation,
    )

    with pytest.raises(
        BuildError,
        match="vector failed",
    ):
        execute_build(plan)

    assert executed == [
        "prepare",
        "raster",
        "vector",
    ]


def test_execute_build_wraps_stage_failure_with_context(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    artwork_plan,
) -> None:
    """
    Exceptions from model-specific implementations are exposed as
    BuildError with artifact, model, and stage context.
    """

    _create_source(tmp_path)

    plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    def implementation(
        context: StageContext,
    ) -> None:
        raise ValueError("boom")

    _install_stage_implementation(
        monkeypatch,
        implementation,
    )

    with pytest.raises(
        BuildError,
    ) as exc_info:
        execute_build(plan)

    message = str(exc_info.value)

    assert "example" in message
    assert "artwork" in message
    assert "prepare" in message
    assert "boom" in message


# =========================================================
# Stage dispatch
# =========================================================


def test_execute_build_rejects_unregistered_stage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    artwork_plan,
) -> None:
    """
    Execution fails cleanly when no model-specific implementation is
    registered for a planned stage.
    """

    _create_source(tmp_path)

    plan = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    monkeypatch.setattr(
        "lowkey_artifact_builder.engine.stage.build_stage_registry",
        lambda: StageRegistry(),
    )

    with pytest.raises(
        BuildError,
        match="No implementation is registered",
    ):
        execute_build(plan)


# =========================================================
# Test helpers
# =========================================================


def _create_source(
    tmp_path: Path,
) -> Path:
    """
    Create the standard external source image used by execution tests.
    """

    source = tmp_path / "source.png"

    source.write_bytes(b"source artwork")

    return source


def _install_stage_implementation(
    monkeypatch: pytest.MonkeyPatch,
    implementation,
) -> None:
    """
    Install one implementation for every artwork stage.

    Stage implementation discovery belongs to the independent stage
    execution boundary, so tests replace the registry constructed by
    engine.stage rather than engine.build.
    """

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


def _create_declared_outputs(
    context: StageContext,
) -> None:
    """
    Create placeholder files for every declared output of a test stage.

    Workspace directories are expected to have already been created by
    the engine.
    """

    for path in context.outputs.values():
        assert path.parent.is_dir()

        path.touch()


# =========================================================
# Multiple build execution
# =========================================================


def test_execute_builds_executes_plans_in_order(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    artwork_plan,
) -> None:
    """
    Multiple build plans execute sequentially in supplied order.

    Multi-build execution is orchestration over the existing
    single-plan execution boundary.
    """

    first = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    second = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    third = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    observed: list[BuildPlan] = []

    def fake_execute_build(
        plan: BuildPlan,
    ) -> None:
        observed.append(plan)

    monkeypatch.setattr(
        "lowkey_artifact_builder.engine.build.execute_build",
        fake_execute_build,
    )

    execute_builds(
        (
            first,
            second,
            third,
        )
    )

    assert observed == [
        first,
        second,
        third,
    ]


def test_execute_builds_accepts_empty_iterable() -> None:
    """
    Executing an empty collection of build plans is a successful no-op.
    """

    execute_builds(())


def test_execute_builds_stops_after_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    artwork_plan,
) -> None:
    """
    Multi-build execution stops when one build fails.

    Later plans are not executed after execute_build raises BuildError.
    """

    first = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    second = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    third = artwork_plan(
        tmp_path,
        monkeypatch,
    )

    observed: list[BuildPlan] = []

    def fake_execute_build(
        plan: BuildPlan,
    ) -> None:
        observed.append(plan)

        if plan is second:
            raise BuildError("second build failed")

    monkeypatch.setattr(
        "lowkey_artifact_builder.engine.build.execute_build",
        fake_execute_build,
    )

    with pytest.raises(
        BuildError,
        match="second build failed",
    ):
        execute_builds(
            (
                first,
                second,
                third,
            )
        )

    assert observed == [
        first,
        second,
    ]


def test_execute_artifact_stage_translates_stage_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Independent stage failures cross the build boundary as BuildError.
    """

    def fail(
        *args,
        **kwargs,
    ) -> None:
        raise StageInputError("required input is missing")

    monkeypatch.setattr(
        "lowkey_artifact_builder.engine.build._execute_artifact_stage",
        fail,
    )

    with pytest.raises(
        BuildError,
        match="required input is missing",
    ):
        execute_artifact_stage(
            "example",
            stage_name="vector",
        )


def test_execute_artifact_stage_forwards_explicit_inputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    The public build boundary preserves explicit stage input bindings.
    """

    received = None

    def execute(
        artifact_id: str,
        *,
        stage_name: str,
        realization: str | None = None,
        project_root: Path | None = None,
        input_paths=None,
        parameter_values=None,
        output_paths=None,
    ) -> None:
        nonlocal received

        assert parameter_values is None
        assert output_paths is None

        received = input_paths

    monkeypatch.setattr(
        "lowkey_artifact_builder.engine.build._execute_artifact_stage",
        execute,
    )

    explicit = {
        "raster.manifest": (tmp_path / "products.json"),
    }

    execute_artifact_stage(
        "example",
        stage_name="vector",
        project_root=tmp_path,
        input_paths=explicit,
    )

    assert received == explicit


def test_execute_artifact_stage_forwards_parameter_and_output_bindings(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    The build boundary preserves parameter and output bindings.
    """

    received_parameters = None
    received_outputs = None

    def execute(
        artifact_id: str,
        *,
        stage_name: str,
        realization: str | None = None,
        project_root: Path | None = None,
        input_paths=None,
        parameter_values=None,
        output_paths=None,
    ) -> None:
        nonlocal received_parameters
        nonlocal received_outputs

        received_parameters = parameter_values
        received_outputs = output_paths

    monkeypatch.setattr(
        "lowkey_artifact_builder.engine.build._execute_artifact_stage",
        execute,
    )

    parameters = {
        "artwork_size": 90.0,
    }

    outputs = {
        "manifest": (tmp_path / "products.json"),
    }

    execute_artifact_stage(
        "example",
        stage_name="vector",
        project_root=tmp_path,
        parameter_values=parameters,
        output_paths=outputs,
    )

    assert received_parameters == parameters
    assert received_outputs == outputs


def test_execute_targeted_artwork_vector_build_stops_before_physical_stages(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    artwork_plan,
) -> None:
    """
    Executing an Artwork vector target stops at registered vector geometry.

    The build executes the prerequisite prepare and raster stages and the
    vector producer, but it does not execute extrusion or packaging.
    """

    _create_source(tmp_path)

    target = ProductRef(
        artifact="example",
        model="artwork",
        realization="default",
        stage="vector",
        product="manifest",
    )

    plan = artwork_plan(
        tmp_path,
        monkeypatch,
        targets=(target,),
    )

    executed: list[str] = []

    def implementation(
        context: StageContext,
    ) -> None:
        executed.append(context.stage_name)

        _create_declared_outputs(context)

    _install_stage_implementation(
        monkeypatch,
        implementation,
    )

    execute_build(plan)

    assert executed == [
        "prepare",
        "raster",
        "vector",
    ]

    realization = plan.artifact_dir / "artwork" / "default"

    assert (realization / "30-vector" / "products.json").is_file()

    assert not (realization / "40-extrude").exists()

    assert not (realization / "50-package").exists()
